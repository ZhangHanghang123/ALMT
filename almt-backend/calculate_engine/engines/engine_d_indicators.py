"""
ENGINE D 指标计量引擎

输入：
    - 9 张参数表（来自 core.loader.load_all_params）
    - ENGINE A 输出：M0 存量基线 + 24 期累计余额/日均
    - ENGINE B 输出：基础利率、定价后利率、FTP 收入
    - ENGINE C 输出：25 期本金/利息

输出：
    774 个账户册节点 × 23 组指标的 num_value + ratio

计量顺序（23 组指标的 num_t/den_t 度量类型映射）：

| 类型 t  | 度量字段                   | 数据来源                              |
|---------|----------------------------|---------------------------------------|
| B       | M0 余额                    | ENGINE A: m0_balance                  |
| AB      | M0 日均余额                | almt_current_position.average_balance |
| NII     | M0 月度利息收入            | almt_current_position.rate            |
| CF1     | M1 本金还本                | ENGINE C: principal_1                 |
| CF3     | M1~M3 累计本金还本         | ENGINE C: principal_1+2+3             |
| CF1-6   | M1~M6 累计本金还本         | ENGINE C: principal_1~6 之和          |
| CF7-12  | M7~M12 累计本金还本        | ENGINE C: principal_7~12 之和         |
| CF12+   | M13~M24 累计本金还本       | ENGINE C: principal_13~24 之和        |
| B-CF3   | M0 余额 - 3月内现金流      | B - CF3                               |
| RWA     | 风险加权资产               | M0 余额 × 风险权重                    |

计算步骤：
    1. 为每个叶节点账户册计算所有可能用到的"基础度量值"（lookups）
    2. 按 caliber 表 23 组指标配置，对每个账户册取 num/den 度量值 × 系数
    3. 树形聚合（自底向上）汇总所有层级的指标值
    4. 比率指标 = num_value / den_value（den=0 时为 None）
"""
import pandas as pd
import numpy as np
from typing import Optional
import pymysql

from . import (
    get_m0_baseline,
)
from ..core.coa_tree import build_coa_tree, aggregate_bottom_up
from ..core.loader import CalcInput


# ============================================================
# 1. 基础度量值计算
# ============================================================

def compute_basic_lookups(
    df_coa_info: pd.DataFrame,
    df_coa_attribute: pd.DataFrame,
    df_current_position: pd.DataFrame,
    engine_c_result: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """
    计算每个账户册的 10 种基础度量值（lookup）。

    Returns:
        pd.DataFrame: 索引 coa_cd，列：
            - B / AB / NII / CF1 / CF3 / CF1_6 / CF7_12 / CF12_PLUS / RWA / B_CF3
    """
    # 1. 存量基线（包含 B、AB、NII）
    m0 = get_m0_baseline(df_current_position, df_coa_info)
    result = m0.copy()

    # 重命名列
    result = result.rename(columns={
        'm0_balance': 'B',
        'm0_average': 'AB',
        'm0_rate': 'NII'
    })

    # 2. 现金流度量（来自 ENGINE C 输出）
    if engine_c_result is not None:
        cf = engine_c_result
        # CF1 = principal_1
        result['CF1'] = cf['principal_1'].reindex(result.index).fillna(0).astype(float)

        # CF3 = principal_1 + principal_2 + principal_3
        result['CF3'] = (
            cf['principal_1'].fillna(0).astype(float) +
            cf['principal_2'].fillna(0).astype(float) +
            cf['principal_3'].fillna(0).astype(float)
        ).reindex(result.index).fillna(0)

        # CF1-6 = principal_1~6 之和
        cf_cols_16 = [f'principal_{i}' for i in range(1, 7)]
        result['CF1_6'] = cf[cf_cols_16].fillna(0).astype(float).sum(axis=1).reindex(result.index).fillna(0)

        # CF7-12 = principal_7~12 之和
        cf_cols_712 = [f'principal_{i}' for i in range(7, 13)]
        result['CF7_12'] = cf[cf_cols_712].fillna(0).astype(float).sum(axis=1).reindex(result.index).fillna(0)

        # CF12+ = principal_13~24 之和
        cf_cols_12p = [f'principal_{i}' for i in range(13, 25)]
        result['CF12_PLUS'] = cf[cf_cols_12p].fillna(0).astype(float).sum(axis=1).reindex(result.index).fillna(0)
    else:
        # 没有 ENGINE C 输出时，全部置 0
        for col in ['CF1', 'CF3', 'CF1_6', 'CF7_12', 'CF12_PLUS']:
            result[col] = 0.0

    # 3. 风险加权资产 = M0 余额 × M1 风险权重（无 M0 权重字段）
    from calculate_engine.core.loader import DB_CONFIG
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT coa_cd, risk_weight_1 FROM almt_param_risk_weight')
            rows = cur.fetchall()
            if rows:
                rw_df = pd.DataFrame(rows)
                rw_map = rw_df.set_index('coa_cd')['risk_weight_1'].astype(float)
                # pandas 3.x 要求唯一索引：去重保留首个
                if rw_map.index.has_duplicates:
                    rw_map = rw_map[~rw_map.index.duplicated(keep='first')]
                rw0 = rw_map.reindex(result.index).fillna(0)
                result['RWA'] = result['B'].fillna(0).astype(float) * rw0
            else:
                result['RWA'] = 0.0
    finally:
        conn.close()

    # 4. B-CF3
    result['B_CF3'] = result['B'].fillna(0).astype(float) - result['CF3'].fillna(0).astype(float)

    # 5. 只保留 10 列
    result = result[['B', 'AB', 'NII', 'CF1', 'CF3', 'CF1_6', 'CF7_12', 'CF12_PLUS', 'RWA', 'B_CF3']]
    return result.astype(float)


# ============================================================
# 2. 度量类型映射表（t → lookup 列名）
# ============================================================

LOOKUP_FIELD_MAP = {
    'B': 'B',
    'AB': 'AB',
    'NII': 'NII',
    'CF1': 'CF1',
    'CF3': 'CF3',
    'CF1-6': 'CF1_6',
    'CF7-12': 'CF7_12',
    'CF12+': 'CF12_PLUS',
    'B-CF3': 'B_CF3',
    'RWA': 'RWA',
}


# ============================================================
# 3. 按账户册计算 23 组指标的 num/den 值
# ============================================================

def compute_per_account_indicators(
    df_metric_caliber: pd.DataFrame,
    df_lookups: pd.DataFrame
) -> pd.DataFrame:
    """
    对每个账户册，计算 23 组指标的 num_value 和 den_value。

    Args:
        df_metric_caliber: almt_metric_caliber 完整表（550 行叶节点）
        df_lookups:        基础度量值（774 账户册）

    Returns:
        pd.DataFrame: 索引 coa_cd（550 个），列 num_1~23_value + den_1~23_value（共 46 列）
    """
    records = []
    for _, row in df_metric_caliber.iterrows():
        cd = row['coa_cd']
        if cd not in df_lookups.index:
            continue

        record = {'coa_cd': cd}
        for i in range(1, 24):
            num_t = row.get(f'num{i}_t')
            num_c = float(row.get(f'num{i}_c') or 0)
            num_field = LOOKUP_FIELD_MAP.get(num_t)

            if num_field and num_c > 0:
                record[f'num_{i}_value'] = float(df_lookups.loc[cd, num_field]) * num_c
            else:
                record[f'num_{i}_value'] = 0.0

            den_t = row.get(f'den{i}_t')
            den_c = float(row.get(f'den{i}_c') or 0)
            den_field = LOOKUP_FIELD_MAP.get(den_t)

            if den_field and den_c > 0:
                record[f'den_{i}_value'] = float(df_lookups.loc[cd, den_field]) * den_c
            else:
                record[f'den_{i}_value'] = 0.0

        records.append(record)

    return pd.DataFrame(records).set_index('coa_cd')


# ============================================================
# 4. 树形聚合（自底向上）
# ============================================================

def aggregate_indicators(
    df_per_account: pd.DataFrame,
    df_coa_info: pd.DataFrame
) -> pd.DataFrame:
    """
    把叶节点的 num/den 值通过树形聚合汇总到所有层级。

    Args:
        df_per_account:  550 个叶节点的 num_1~23_value + den_1~23_value
        df_coa_info:     账户册完整树（774 行）

    Returns:
        pd.DataFrame: 774 个账户册（含 ROOT）的 num + den + ratio 列
    """
    all_cds = df_coa_info['coa_cd'].tolist()
    roots = build_coa_tree(df_coa_info)
    result = pd.DataFrame(index=all_cds)

    for i in range(1, 24):
        num_col = f'num_{i}_value'
        den_col = f'den_{i}_value'

        num_series = df_per_account[num_col].reindex(all_cds).fillna(0).astype(float)
        den_series = df_per_account[den_col].reindex(all_cds).fillna(0).astype(float)

        result[num_col] = aggregate_bottom_up(num_series, roots).reindex(all_cds).fillna(0)
        result[den_col] = aggregate_bottom_up(den_series, roots).reindex(all_cds).fillna(0)

        ratio = np.where(
            result[den_col] != 0,
            result[num_col] / result[den_col],
            np.nan
        )
        result[f'ratio_{i}_value'] = ratio

    return result


# ============================================================
# 5. ENGINE D 主入口
# ============================================================

def run_engine_d(
    data: CalcInput,
    engine_c_result: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """
    ENGINE D 主入口：23 组指标计量完整流程。

    返回：
        pd.DataFrame: 索引 coa_cd（774），列：
            - num_1_value ~ num_23_value（23 列）
            - den_1_value ~ den_23_value（23 列）
            - ratio_1_value ~ ratio_23_value（23 列）
        共计 69 列
    """
    # 1. 基础度量值
    lookups = compute_basic_lookups(
        df_coa_info=data.coa_info,
        df_coa_attribute=data.coa_attribute,
        df_current_position=data.current_position,
        engine_c_result=engine_c_result
    )

    # 2. 按账户册计算 num/den
    per_account = compute_per_account_indicators(data.metric_caliber, lookups)

    # 3. 树形聚合
    result = aggregate_indicators(per_account, data.coa_info)

    return result


# ============================================================
# 6. 便捷方法
# ============================================================

def get_metric_snapshot(
    result: pd.DataFrame,
    metric_idx: int,
    top_n: Optional[int] = None
) -> pd.DataFrame:
    """获取某指标的快照视图：num/den/ratio"""
    cols = [
        f'num_{metric_idx}_value',
        f'den_{metric_idx}_value',
        f'ratio_{metric_idx}_value'
    ]
    snapshot = result[cols].copy()
    if top_n:
        snapshot = snapshot.head(top_n)
    return snapshot