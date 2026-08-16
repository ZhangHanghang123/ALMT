"""
结果落库服务（saver.py）

把 4 个引擎的输出结果保存到 MySQL：
  - almt_result_index          基础指标汇总（每账户册：余额/日均/利率）
  - almt_result_plan           业务计划结果（每账户册 + item_name + item_value）
  - almt_calculate_intermediate_a  ENGINE A 完整输出（25 期 × 余额+日均）
  - almt_calculate_intermediate_b  ENGINE B 完整输出（24 期 × base/pricing/ftp）
  - almt_calculate_intermediate_c  ENGINE C 完整输出（25 期 × principal/interest/total）
  - almt_calculate_intermediate_d  ENGINE D 完整输出（23 组 × num/den/ratio）

使用：
    from calculate_engine.saver import save_calc_result
    save_calc_result(task_id, data_date, calc_result)
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

import pandas as pd
import pymysql

from calculate_engine.runner import CalcResult


DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'almt',
    'password': 'almt',
    'database': 'almt_db',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
}


# 23 组指标的名称（与指标编号对应）
INDICATOR_NAMES = {
    1: '利息净收入', 2: '资产余额', 3: '负债余额', 4: '所有者权益',
    5: '生息资产余额', 6: '付息负债余额', 7: '净利息收入',
    8: 'FTP收入合计', 9: '总规模', 10: '风险加权资产', 11: '流动性资产',
    12: '一级资产', 13: '稳定资金', 14: '短期现金流',
    15: '中期现金流', 16: '长期现金流', 17: '总资产规模',
    18: '扣减3月内现金', 19: '总余额规模', 20: '3月现金流占比',
    21: '6月现金流占比', 22: '12月现金流占比', 23: '24月现金流占比',
}


def _to_float(v):
    """Decimal/np.float64 转 Python float（NaN/inf 转 None，避免 pymysql 报错）"""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    try:
        f = float(v)
        # NaN / inf → None
        import math
        if not math.isfinite(f):
            return None
        return f
    except Exception:
        return None


def _to_date(d) -> Optional[date]:
    if d is None:
        return None
    if isinstance(d, date):
        return d
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, str):
        try:
            return datetime.strptime(d[:10], '%Y-%m-%d').date()
        except Exception:
            return None
    return None


def _get_conn():
    return pymysql.connect(**DB_CONFIG)


def _get_coa_name_map() -> dict:
    """加载 coa_cd → coa_name 映射（避免每条都关联查询）"""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT coa_cd, coa_name FROM almt_coa_info")
            rows = cur.fetchall()
        return {r['coa_cd']: r['coa_name'] for r in rows}
    finally:
        conn.close()


def _get_term_map() -> dict:
    """加载 coa_cd → term 映射（ENGINE C 需要）"""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT coa_cd, term FROM almt_coa_attribute WHERE term IS NOT NULL")
            rows = cur.fetchall()
        return {r['coa_cd']: r['term'] for r in rows}
    finally:
        conn.close()


def _get_position_map() -> dict:
    """
    加载 coa_cd → {balance, average_balance, rate} 映射（基线数据）
    用于 saver 构造 total_balance / avg_rate（因为 ENGINE A 输出不含 M0 基线）
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT coa_lvl,
                       SUM(balance) AS balance,
                       SUM(average_balance) AS average_balance,
                       AVG(rate) AS rate
                FROM almt_current_position
                GROUP BY coa_lvl
            """)
            rows = cur.fetchall()
        return {
            r['coa_lvl']: {
                'balance': _to_float(r['balance']) or 0.0,
                'average_balance': _to_float(r['average_balance']) or 0.0,
                'rate': _to_float(r['rate']) or 0.0,
            }
            for r in rows
        }
    finally:
        conn.close()


def _compute_cum(a_out: pd.DataFrame, base_col: str) -> pd.Series:
    """计算 ENGINE A 的累计值：sum(bp_X_1 .. bp_X_i)"""
    series_cum = pd.Series([0.0] * len(a_out), index=a_out.index)
    for i in range(1, 25):
        col = f'{base_col}_{i}'
        if col in a_out.columns:
            series_cum = series_cum.add(a_out[col].fillna(0.0), fill_value=0.0)
    return series_cum


def _clear_existing(conn, task_id: str):
    """清除 task_id 的旧结果（用于重新计算场景）"""
    tables = [
        'almt_result_index', 'almt_result_plan',
        'almt_calculate_intermediate_a', 'almt_calculate_intermediate_b',
        'almt_calculate_intermediate_c', 'almt_calculate_intermediate_d',
    ]
    with conn.cursor() as cur:
        for tbl in tables:
            cur.execute(f"DELETE FROM {tbl} WHERE task_id = %s", (task_id,))


# ============================================================
# almt_result_index（基础指标汇总）
# ============================================================

def _is_liability(coa_cd: str) -> bool:
    """负债账户册判断：coa_cd 以 2 开头（如 2_1, 2_1_1）"""
    return coa_cd.startswith('2_') or coa_cd == '2'


def save_result_index(conn, task_id: str, data_date, a_out: pd.DataFrame):
    """
    从 ENGINE A 输出 + current_position 构造 almt_result_index
    字段：coa_cd, coa_name, total_balance, average_balance, avg_rate

    total_balance    = current_position.balance + M1~M24 累计业务计划余额
                       （负债账户册取负数，使 result/summary 能区分资产/负债）
    average_balance  = 同上规则
    avg_rate         = current_position.rate（当前年化利率%）
    """
    if a_out is None or len(a_out) == 0:
        return 0

    coa_names = _get_coa_name_map()
    pos_map = _get_position_map()

    # 计算累计值（在 saver 里从 bp_X_i 累加）
    cum_bp_balance = _compute_cum(a_out, 'bp_balance')
    cum_bp_average = _compute_cum(a_out, 'bp_average')

    rows = []
    for coa_cd, row in a_out.iterrows():
        coa_cd_str = str(coa_cd)
        pos = pos_map.get(coa_cd_str, {'balance': 0.0, 'average_balance': 0.0, 'rate': 0.0})

        # 累计业务计划
        cum_bp_bal = _to_float(cum_bp_balance.get(coa_cd)) or 0.0
        cum_bp_avg = _to_float(cum_bp_average.get(coa_cd)) or 0.0

        # total = 基础余额 + 累计业务计划
        total_bal = pos['balance'] + cum_bp_bal
        avg_bal = pos['average_balance'] + cum_bp_avg

        # 负债类账户册取负（便于 result/summary 用 total_balance>0/<0 区分）
        if _is_liability(coa_cd_str):
            total_bal = -abs(total_bal)
            avg_bal = -abs(avg_bal)

        m0_rate = pos['rate']

        rows.append({
            'task_id': task_id,
            'data_date': data_date,
            'coa_cd': coa_cd_str,
            'coa_name': coa_names.get(coa_cd_str, ''),
            'total_balance': round(total_bal, 2),
            'average_balance': round(avg_bal, 2),
            'avg_rate': round(m0_rate, 4),
        })

    if not rows:
        return 0

    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO almt_result_index
            (task_id, data_date, coa_cd, coa_name, total_balance, average_balance, avg_rate)
            VALUES (%(task_id)s, %(data_date)s, %(coa_cd)s, %(coa_name)s,
                    %(total_balance)s, %(average_balance)s, %(avg_rate)s)""",
            rows
        )
    return len(rows)


# ============================================================
# almt_result_plan（业务计划结果）
# ============================================================

def save_result_plan(conn, task_id: str, data_date, a_out: pd.DataFrame):
    """
    从 ENGINE A 输出构造 almt_result_plan
    每账户册写入多条记录：M1~M24 累计业务计划余额/日均
    """
    if a_out is None or len(a_out) == 0:
        return 0

    coa_names = _get_coa_name_map()
    rows = []
    for coa_cd, row in a_out.iterrows():
        coa_cd_str = str(coa_cd)
        coa_name = coa_names.get(coa_cd_str, '')

        # 写入"规划增量合计"（M1~M24 累加）
        bp_total = sum(_to_float(row.get(f'bp_balance_{i}')) or 0 for i in range(1, 25))
        avg_total = sum(_to_float(row.get(f'bp_average_{i}')) or 0 for i in range(1, 25))
        rows.append({
            'task_id': task_id, 'data_date': data_date,
            'coa_cd': coa_cd_str, 'coa_name': coa_name,
            'item_name': 'avg_plan_balance', 'item_value': round(bp_total / 24, 2),
        })
        rows.append({
            'task_id': task_id, 'data_date': data_date,
            'coa_cd': coa_cd_str, 'coa_name': coa_name,
            'item_name': 'avg_plan_average', 'item_value': round(avg_total / 24, 2),
        })
        rows.append({
            'task_id': task_id, 'data_date': data_date,
            'coa_cd': coa_cd_str, 'coa_name': coa_name,
            'item_name': 'sum_plan_balance', 'item_value': round(bp_total, 2),
        })

    if not rows:
        return 0

    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO almt_result_plan
            (task_id, data_date, coa_cd, coa_name, item_name, item_value)
            VALUES (%(task_id)s, %(data_date)s, %(coa_cd)s, %(coa_name)s,
                    %(item_name)s, %(item_value)s)""",
            rows
        )
    return len(rows)


# ============================================================
# almt_calculate_intermediate_a（ENGINE A 完整）
# ============================================================

def save_intermediate_a(conn, task_id: str, data_date, a_out: pd.DataFrame):
    """保存 ENGINE A 完整 25 期数据

    ENGINE A 实际输出列：bp_balance_1~24 / bp_average_1~24（24 期业务计划）
    M0 基线和累计值在 saver 里通过 current_position + 累加计算补齐。
    """
    if a_out is None or len(a_out) == 0:
        return 0

    coa_names = _get_coa_name_map()
    pos_map = _get_position_map()

    rows = []
    is_neg = _is_liability  # 负债账户册取负
    for coa_cd, row in a_out.iterrows():
        coa_cd_str = str(coa_cd)
        coa_name = coa_names.get(coa_cd_str, '')
        pos = pos_map.get(coa_cd_str, {'balance': 0.0, 'average_balance': 0.0, 'rate': 0.0})

        # 负债类账户册取负
        sign = -1 if is_neg(coa_cd_str) else 1
        m0_bal = pos['balance'] * sign
        m0_avg = pos['average_balance'] * sign

        # M0（基线 = current_position）
        rows.append({
            'task_id': task_id, 'data_date': data_date,
            'coa_cd': coa_cd_str, 'coa_name': coa_name, 'period': 0,
            'bp_balance': None, 'bp_average': None,
            'cum_balance': m0_bal,
            'cum_average': m0_avg,
            'm0_rate': pos['rate'],
        })

        # M1~M24（bp 是当月增量，cum 是累加到当月；负债累加按负号延续）
        cum_bal = m0_bal
        cum_avg = m0_avg
        for i in range(1, 25):
            bp_b = (_to_float(row.get(f'bp_balance_{i}')) or 0.0) * sign
            bp_a = (_to_float(row.get(f'bp_average_{i}')) or 0.0) * sign
            cum_bal += bp_b
            cum_avg += bp_a

            rows.append({
                'task_id': task_id, 'data_date': data_date,
                'coa_cd': coa_cd_str, 'coa_name': coa_name, 'period': i,
                'bp_balance': round(bp_b, 2),
                'bp_average': round(bp_a, 2),
                'cum_balance': round(cum_bal, 2),
                'cum_average': round(cum_avg, 2),
                'm0_rate': None,
            })

    if not rows:
        return 0

    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO almt_calculate_intermediate_a
            (task_id, data_date, coa_cd, coa_name, period,
             bp_balance, bp_average, cum_balance, cum_average, m0_rate)
            VALUES (%(task_id)s, %(data_date)s, %(coa_cd)s, %(coa_name)s, %(period)s,
                    %(bp_balance)s, %(bp_average)s, %(cum_balance)s, %(cum_average)s, %(m0_rate)s)""",
            rows
        )
    return len(rows)


# ============================================================
# almt_calculate_intermediate_b（ENGINE B 完整）
# ============================================================

def save_intermediate_b(conn, task_id: str, data_date, b_out: pd.DataFrame):
    """保存 ENGINE B 完整 24 期数据"""
    if b_out is None or len(b_out) == 0:
        return 0

    coa_names = _get_coa_name_map()
    rows = []
    for coa_cd, row in b_out.iterrows():
        coa_cd_str = str(coa_cd)
        coa_name = coa_names.get(coa_cd_str, '')

        for i in range(1, 25):
            rows.append({
                'task_id': task_id, 'data_date': data_date,
                'coa_cd': coa_cd_str, 'coa_name': coa_name, 'period': i,
                'base_rate': _to_float(row.get(f'base_rate_{i}')),
                'pricing_rate': _to_float(row.get(f'pricing_rate_{i}')),
                'ftp_income': _to_float(row.get(f'ftp_income_{i}')),
                'delta_ftp': _to_float(row.get(f'delta_ftp_{i}')),
            })

    if not rows:
        return 0

    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO almt_calculate_intermediate_b
            (task_id, data_date, coa_cd, coa_name, period,
             base_rate, pricing_rate, ftp_income, delta_ftp)
            VALUES (%(task_id)s, %(data_date)s, %(coa_cd)s, %(coa_name)s, %(period)s,
                    %(base_rate)s, %(pricing_rate)s, %(ftp_income)s, %(delta_ftp)s)""",
            rows
        )
    return len(rows)


# ============================================================
# almt_calculate_intermediate_c（ENGINE C 完整）
# ============================================================

def save_intermediate_c(conn, task_id: str, data_date, c_out: pd.DataFrame):
    """保存 ENGINE C 完整 25 期现金流"""
    if c_out is None or len(c_out) == 0:
        return 0

    coa_names = _get_coa_name_map()
    term_map = _get_term_map()
    rows = []
    for coa_cd, row in c_out.iterrows():
        coa_cd_str = str(coa_cd)
        coa_name = coa_names.get(coa_cd_str, '')
        term = term_map.get(coa_cd_str)

        for i in range(25):
            rows.append({
                'task_id': task_id, 'data_date': data_date,
                'coa_cd': coa_cd_str, 'coa_name': coa_name,
                'term': term, 'period': i,
                'principal': _to_float(row.get(f'principal_{i}')),
                'interest': _to_float(row.get(f'interest_{i}')),
                'total_cf': _to_float(row.get(f'total_{i}')),
            })

    if not rows:
        return 0

    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO almt_calculate_intermediate_c
            (task_id, data_date, coa_cd, coa_name, term, period,
             principal, interest, total_cf)
            VALUES (%(task_id)s, %(data_date)s, %(coa_cd)s, %(coa_name)s,
                    %(term)s, %(period)s, %(principal)s, %(interest)s, %(total_cf)s)""",
            rows
        )
    return len(rows)


# ============================================================
# almt_calculate_intermediate_d（ENGINE D 完整）
# ============================================================

def save_intermediate_d(conn, task_id: str, data_date, d_out: pd.DataFrame):
    """保存 ENGINE D 完整 23 组指标"""
    if d_out is None or len(d_out) == 0:
        return 0

    coa_names = _get_coa_name_map()
    rows = []
    for coa_cd, row in d_out.iterrows():
        coa_cd_str = str(coa_cd)
        coa_name = coa_names.get(coa_cd_str, '')

        for i in range(1, 24):
            rows.append({
                'task_id': task_id, 'data_date': data_date,
                'coa_cd': coa_cd_str, 'coa_name': coa_name,
                'metric_idx': i,
                'metric_name': INDICATOR_NAMES.get(i, f'指标{i}'),
                'num_value': _to_float(row.get(f'num_{i}_value')),
                'den_value': _to_float(row.get(f'den_{i}_value')),
                'ratio_value': _to_float(row.get(f'ratio_{i}_value')),
            })

    if not rows:
        return 0

    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO almt_calculate_intermediate_d
            (task_id, data_date, coa_cd, coa_name, metric_idx, metric_name,
             num_value, den_value, ratio_value)
            VALUES (%(task_id)s, %(data_date)s, %(coa_cd)s, %(coa_name)s,
                    %(metric_idx)s, %(metric_name)s,
                    %(num_value)s, %(den_value)s, %(ratio_value)s)""",
            rows
        )
    return len(rows)


# ============================================================
# 主入口
# ============================================================

def save_calc_result(
    task_id: str,
    data_date,
    calc_result: CalcResult,
    clear_existing: bool = True
) -> dict:
    """
    把 CalcResult 落库到 6 张结果表

    Args:
        task_id:       任务 ID
        data_date:     数据日期（str / date / datetime）
        calc_result:   CalcResult（含 a_out, b_out, c_out, d_out）
        clear_existing: 是否清除 task_id 的旧结果（默认 True）

    Returns:
        dict: 各表写入行数
    """
    data_date_obj = _to_date(data_date)
    conn = _get_conn()
    stats = {}
    try:
        if clear_existing:
            _clear_existing(conn, task_id)

        stats['result_index'] = save_result_index(conn, task_id, data_date_obj, calc_result.a_out)
        stats['result_plan'] = save_result_plan(conn, task_id, data_date_obj, calc_result.a_out)
        stats['intermediate_a'] = save_intermediate_a(conn, task_id, data_date_obj, calc_result.a_out)
        stats['intermediate_b'] = save_intermediate_b(conn, task_id, data_date_obj, calc_result.b_out)
        stats['intermediate_c'] = save_intermediate_c(conn, task_id, data_date_obj, calc_result.c_out)
        stats['intermediate_d'] = save_intermediate_d(conn, task_id, data_date_obj, calc_result.d_out)

        conn.commit()
        return stats
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    """冒烟测试"""
    from calculate_engine.runner import run_full_calculate
    res = run_full_calculate(task_id='saver-smoke-test', data_date='2026-08-15')
    if res.error:
        print(f'计算失败: {res.error}')
    else:
        stats = save_calc_result('saver-smoke-test', '2026-08-15', res)
        print('=== 落库统计 ===')
        for tbl, cnt in stats.items():
            print(f'  {tbl}: {cnt} 行')