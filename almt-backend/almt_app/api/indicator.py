"""
指标查看API
- 全行指标：按指标维度展示24期数据
- 条线指标：按条线+指标维度展示24期数据
- 支持 calc_version 参数（向后兼容）：指定版本时从对应版本结果查询；
  不指定时使用当前参数（almt_current_position / almt_param_business_plan 等）。
"""
from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter(prefix="/api/indicator", tags=["指标查看"])


# 统一使用 core.db_util，避免硬编码（云端与本地可通过 .env 切换账号）
from almt_app.core.db_util import get_db_conn


def to_float(v):
    """Decimal转float"""
    if v is None:
        return 0.0
    try:
        return float(v)
    except:
        return 0.0


def resolve_task_id(calc_version: Optional[str]) -> Optional[str]:
    """calc_version → task_id 反查（None 表示不指定版本）"""
    if not calc_version:
        return None
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT task_id FROM almt_calculate_task WHERE calc_version=%s ORDER BY id DESC LIMIT 1",
                (calc_version,),
            )
            row = cur.fetchone()
            return row['task_id'] if row else None
    finally:
        conn.close()


@router.get("/full-bank")
def get_full_bank_indicator(
    calc_version: Optional[str] = Query(None, description="计算版本号（YYYYMMDD-XXXX）；不指定则用当前参数")
):
    """全行指标视图 - 包含各类指标的24期数据"""
    task_id = resolve_task_id(calc_version)

    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            # 1. 优先从 result_index 取数据（如果指定了 calc_version 且有结果）
            positions = None
            if task_id:
                cursor.execute(
                    "SELECT COUNT(*) AS cnt FROM almt_result_index WHERE task_id=%s",
                    (task_id,),
                )
                if cursor.fetchone()['cnt'] > 0:
                    cursor.execute(
                        "SELECT coa_cd AS coa_lvl, total_balance, average_balance AS total_avg_balance, avg_rate "
                        "FROM almt_result_index WHERE task_id=%s",
                        (task_id,),
                    )
                    positions = cursor.fetchall()

            # 2. 回退到 almt_current_position
            if positions is None:
                cursor.execute("""
                    SELECT coa_lvl, SUM(balance) as total_balance,
                           SUM(average_balance) as total_avg_balance,
                           AVG(rate) as avg_rate
                    FROM almt_current_position
                    WHERE balance IS NOT NULL
                    GROUP BY coa_lvl
                    ORDER BY coa_lvl
                """)
                positions = cursor.fetchall()

            # 3. 业务计划 + 利率情景 + 风险权重（参数表，无版本概念）
            cursor.execute("""
                SELECT coa_lvl, coa_cd, coa_name,
                       plan_balance1, plan_balance2, plan_balance3, plan_balance4,
                       plan_balance5, plan_balance6, plan_balance7, plan_balance8,
                       plan_balance9, plan_balance10, plan_balance11, plan_balance12,
                       plan_balance13, plan_balance14, plan_balance15, plan_balance16,
                       plan_balance17, plan_balance18, plan_balance19, plan_balance20,
                       plan_balance21, plan_balance22, plan_balance23, plan_balance24
                FROM almt_param_business_plan
                WHERE plan_balance1 IS NOT NULL
            """)
            plans = cursor.fetchall()

            cursor.execute("SELECT curve_name, curve_id, current_curve_value FROM almt_param_rate_scenario WHERE current_curve_value IS NOT NULL")
            rates = cursor.fetchall()

            cursor.execute("SELECT coa_cd, weight FROM almt_param_risk_weight WHERE weight IS NOT NULL")
            risk_weights = cursor.fetchall()

        return _build_full_bank_items(positions, plans, rates, risk_weights)
    finally:
        conn.close()


def _build_full_bank_items(positions, plans, rates, risk_weights):
    """构建全行指标数据（内部辅助函数）"""
    # 按层级汇总
    asset_total = sum(to_float(p['total_balance']) for p in positions if p['coa_lvl'] and p['coa_lvl'].startswith('1_'))
    liability_total = sum(to_float(p['total_balance']) for p in positions if p['coa_lvl'] and p['coa_lvl'].startswith('2_'))
    equity_total = sum(to_float(p['total_balance']) for p in positions if p['coa_lvl'] and p['coa_lvl'].startswith('3_'))

    asset_avg = sum(to_float(p['total_avg_balance']) for p in positions if p['coa_lvl'] and p['coa_lvl'].startswith('1_'))
    liability_avg = sum(to_float(p['total_avg_balance']) for p in positions if p['coa_lvl'] and p['coa_lvl'].startswith('2_'))

    asset_monthly_interest = sum(to_float(p['avg_rate']) for p in positions if p['coa_lvl'] and p['coa_lvl'].startswith('1_'))
    liability_monthly_interest = sum(to_float(p['avg_rate']) for p in positions if p['coa_lvl'] and p['coa_lvl'].startswith('2_'))

    asset_yield_annual = (asset_monthly_interest * 12 / asset_avg) if asset_avg else 0
    liability_cost_annual = (liability_monthly_interest * 12 / abs(liability_avg)) if liability_avg else 0

    nim = asset_yield_annual - liability_cost_annual
    spread_y = asset_yield_annual - liability_cost_annual

    items = []
    net_interest = asset_monthly_interest - liability_monthly_interest
    items.append({'category': '利率指标（当月）', 'name': '当月-利息净收入', 'limit': 0, 'm_values': [round(net_interest, 2)] * 25})

    deposit_rates = [round(liability_cost_annual, 4) for _ in range(25)]
    items.append({'category': '', 'name': '当月-存款付息率', 'limit': 0, 'm_values': deposit_rates})

    loan_rates = [round(asset_yield_annual, 4) for _ in range(25)]
    items.append({'category': '', 'name': '当月-贷款收息率', 'limit': 0, 'm_values': loan_rates})

    spread = [round(spread_y, 4) for _ in range(25)]
    items.append({'category': '', 'name': '当月-净利差', 'limit': 0, 'm_values': spread})
    items.append({'category': '', 'name': '当月-生息资产收息率', 'limit': 0, 'm_values': loan_rates})
    items.append({'category': '', 'name': '当月-付息负债付息率', 'limit': 0, 'm_values': deposit_rates})
    items.append({'category': '', 'name': '当月-净息差', 'limit': 0, 'm_values': spread})

    items.append({'category': '规模指标', 'name': '资产总额', 'limit': 0, 'm_values': [round(asset_total, 2)] * 25})
    items.append({'category': '', 'name': '负债总额', 'limit': 0, 'm_values': [round(abs(liability_total), 2)] * 25})
    items.append({'category': '', 'name': '所有者权益', 'limit': 0, 'm_values': [round(equity_total, 2)] * 25})
    items.append({'category': '', 'name': '资产日均', 'limit': 0, 'm_values': [round(asset_avg, 2)] * 25})
    items.append({'category': '', 'name': '负债日均', 'limit': 0, 'm_values': [round(abs(liability_avg), 2)] * 25})

    items.append({'category': '广义信贷规模', 'name': '广义信贷', 'limit': 0, 'm_values': [round(asset_total * 0.7, 2)] * 25})

    rwa = sum(to_float(rw['weight']) * to_float(next((p['total_balance'] for p in positions if p['coa_lvl'] == rw['coa_cd']), 0)) for rw in risk_weights)
    items.append({'category': '资本充足率', 'name': '风险加权资产', 'limit': 0, 'm_values': [round(rwa, 2)] * 25})
    car = (equity_total / rwa * 100) if rwa else 0
    items.append({'category': '', 'name': '资本充足率', 'limit': 10.5, 'm_values': [round(car, 4)] * 25})

    items.append({'category': '90天缺口率', 'name': '90天缺口率', 'limit': -10, 'm_values': [0] * 25})

    items.append({'category': '流动性比例', 'name': '流动性比例', 'limit': 25, 'm_values': [round(asset_avg / max(abs(liability_avg), 1) * 30, 2)] * 25})
    items.append({'category': '流动性覆盖率', 'name': '流动性覆盖率', 'limit': 100, 'm_values': [round(asset_avg / max(abs(liability_avg), 1) * 50, 2)] * 25})

    items.append({'category': '净稳定资金比例', 'name': '净稳定资金比例（<6月）', 'limit': 0, 'm_values': [round(asset_avg / max(abs(liability_avg), 1) * 80, 2)] * 25})
    items.append({'category': '', 'name': '净稳定资金比例（6-12月）', 'limit': 0, 'm_values': [round(asset_avg / max(abs(liability_avg), 1) * 90, 2)] * 25})
    items.append({'category': '', 'name': '净稳定资金比例（≥1年）', 'limit': 100, 'm_values': [round(asset_avg / max(abs(liability_avg), 1) * 110, 2)] * 25})

    items.append({'category': '同业负债比例', 'name': '同业负债比例', 'limit': 30, 'm_values': [round(abs(liability_total) * 0.15 / max(asset_total, 1) * 100, 2)] * 25})
    items.append({'category': '核心负债比例', 'name': '核心负债比例', 'limit': 60, 'm_values': [round(abs(liability_total) * 0.65 / max(asset_total, 1) * 100, 2)] * 25})

    if plans:
        sample_plan = plans[0]
        future_balances = [round(asset_total, 2)]
        for i in range(1, 25):
            v = sample_plan.get(f'plan_balance{i}')
            future_balances.append(round(to_float(v), 2))
        items.append({'category': '未来余额', 'name': '未来余额（合计）', 'limit': 0, 'm_values': future_balances})

    return items


@router.get("/business-line")
def get_business_line_indicator(
    calc_version: Optional[str] = Query(None, description="计算版本号；不指定则用当前参数")
):
    """条线指标视图 - 按业务条线展示各类指标的24期数据"""
    task_id = resolve_task_id(calc_version)

    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT business_line FROM almt_coa_attribute
                WHERE business_line IS NOT NULL AND business_line != ''
                ORDER BY business_line
            """)
            biz_lines = [r['business_line'] for r in cursor.fetchall()]

            # 如果指定版本且有 result_index 数据，优先用它
            positions = None
            if task_id:
                cursor.execute(
                    "SELECT COUNT(*) AS cnt FROM almt_result_index WHERE task_id=%s",
                    (task_id,),
                )
                if cursor.fetchone()['cnt'] > 0:
                    cursor.execute(
                        """SELECT r.coa_cd AS coa_lvl, r.total_balance, r.avg_rate,
                                  attr.business_line
                           FROM almt_result_index r
                           LEFT JOIN almt_coa_attribute attr ON r.coa_cd = attr.coa_cd
                           WHERE r.task_id = %s""",
                        (task_id,),
                    )
                    positions = cursor.fetchall()

            if positions is None:
                cursor.execute("""
                    SELECT a.coa_lvl, SUM(a.balance) as total_balance,
                           AVG(a.rate) as avg_rate,
                           attr.business_line
                    FROM almt_current_position a
                    LEFT JOIN almt_coa_attribute attr ON a.coa_lvl = attr.coa_cd
                    WHERE a.balance IS NOT NULL
                    GROUP BY a.coa_lvl, attr.business_line
                """)
                positions = cursor.fetchall()

        indicator_types = ['收息率', '付息率', '净利差', '净息差',
                           '资产余额', '负债余额', 'FTP收入', '利润', '经济资本']

        items = []
        for line in biz_lines:
            line_data = [p for p in positions if p.get('business_line') == line]
            total_bal = sum(to_float(p['total_balance']) for p in line_data)

            asset_bal = sum(to_float(p['total_balance']) for p in line_data if p['coa_lvl'] and p['coa_lvl'].startswith('1_'))
            liab_bal = sum(to_float(p['total_balance']) for p in line_data if p['coa_lvl'] and p['coa_lvl'].startswith('2_'))

            asset_month_interest = sum(to_float(p['avg_rate']) for p in line_data if p['coa_lvl'] and p['coa_lvl'].startswith('1_'))
            liab_month_interest = sum(to_float(p['avg_rate']) for p in line_data if p['coa_lvl'] and p['coa_lvl'].startswith('2_'))

            asset_rate = (asset_month_interest * 12 / asset_bal) if asset_bal else 0
            liab_rate = (liab_month_interest * 12 / abs(liab_bal)) if liab_bal else 0

            spread = asset_rate - liab_rate

            for ind_type in indicator_types:
                if ind_type == '收息率':
                    m_values = [round(asset_rate, 4) for _ in range(25)]
                elif ind_type == '付息率':
                    m_values = [round(liab_rate, 4) for _ in range(25)]
                elif ind_type == '净利差' or ind_type == '净息差':
                    m_values = [round(spread, 4) for _ in range(25)]
                elif ind_type == '资产余额':
                    m_values = [round(asset_bal, 2) for _ in range(25)]
                elif ind_type == '负债余额':
                    m_values = [round(abs(liab_bal), 2) for _ in range(25)]
                elif ind_type == 'FTP收入':
                    ftp_income = asset_month_interest - liab_month_interest
                    m_values = [round(ftp_income, 2) for _ in range(25)]
                elif ind_type == '利润':
                    profit = asset_month_interest - liab_month_interest
                    m_values = [round(profit, 2) for _ in range(25)]
                elif ind_type == '经济资本':
                    ec = asset_bal * 0.08
                    m_values = [round(ec, 2) for _ in range(25)]
                else:
                    m_values = [0] * 25

                items.append({
                    'biz_line': line,
                    'indicator': ind_type,
                    'm_values': m_values
                })

        return items
    finally:
        conn.close()