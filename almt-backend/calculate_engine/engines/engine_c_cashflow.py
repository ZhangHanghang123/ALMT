"""
ENGINE C 现金流计量（Cash Flow Measurement）

职责：按期限生成 25 期动态现金流（本金 + 利息）。

详见 MEASUREMENT_MANUAL.md 第 4 章

核心算法：
  - 现金流模式矩阵（cf_pattern.py）：12 种期限 × 25 期的摊销矩阵
      - 1D/7D/1M：M1 还清（[1, 0, 0, ...]）
      - 3M：M1~3 还本（[1, 1, 1, 0, ...]）
      - 6M：M1~5 还本，M6 还清（[1,1,1,1,1,x,0,...]）
      - 1Y：M1~11 还本，M12 还清
      - 2Y~30Y：M1~23/24 还本，M24 还清（30Y 25 期全还）
  - 每个底层账户册：
      - principal[i] = balance_i × pattern[i]   # 本金
      - interest[i] = balance_{i-1} × rate       # 利息（基于上期余额）
      - cumulative[i] = principal + interest      # 现金流
"""
from calculate_engine.core.coa_tree import build_coa_tree
from calculate_engine.core.loader import load_all_params
from calculate_engine.engines import get_bp_with_baseline
import pandas as pd
import numpy as np


# ============= 现金流模式矩阵 =============
# 12 种期限 × 25 期摊销矩阵
# 1 = 还本/付息, x = 还清(最后一期), 0 = 不操作

CF_PATTERN = {
    '1D':  [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    '7D':  [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    '1M':  [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    '3M':  [1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    '6M':  [1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    '1Y':  [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    '2Y':  [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
    '3Y':  [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    '5Y':  [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    '10Y': [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    '20Y': [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    '30Y': [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
}


def get_cf_pattern(term: str) -> list:
    """根据原始期限取现金流模式（找不到则默认 30Y 全期）"""
    return CF_PATTERN.get(term, CF_PATTERN['30Y'])


def simulate_cashflow_for_node(
    balance_seq: list,    # 25 期余额 [M0, M1, ..., M24]
    rate_seq: list,        # 24 期利率 [M1, ..., M24]
    term: str,             # 原始期限
    avg_seq: list = None   # 24 期日均（可选，用于更精确的利息）
) -> dict:
    """
    计算单个账户册节点的 25 期现金流。

    算法：
      - 现金流模式 pattern[i] 表示该期还本的比例（1 = 1/N，x = 最后一期）
      - 实际还本 = balance[i] × pattern[i] / pattern_sum（确保还本总和 = 余额）

    Returns:
        dict: 包含 principal_0~24, interest_0~24, total_0~24 三个 25 期数组
    """
    pattern = get_cf_pattern(term)
    pattern_sum = sum(pattern) if sum(pattern) > 0 else 1  # 避免除 0
    principal = [0.0] * 25
    interest = [0.0] * 25
    total = [0.0] * 25

    # 本金：principal[0] = 0（M0 无现金流）
    # principal[i] = balance_seq[i-1] × pattern[i-1] / pattern_sum
    # pattern[i-1] 是 M_i 的还本比例（与上期余额对应）
    # 对于 30Y（25 期全还），M1~M24 共 24 期还 2400/24 = 100
    # 对于 1D，M1 还清全部本金，M2+ = 0
    # 这样保证所有期本金之和 ≈ m0_balance
    principal[0] = 0
    for i in range(1, 25):
        principal[i] = balance_seq[i-1] * pattern[i-1] / pattern_sum

    # 利息：interest[i] = balance[i-1] × rate[i] / 12（月化）
    # M0 没有利息（从 M1 开始）
    for i in range(1, 25):
        prev_bal = balance_seq[i-1]
        rate = rate_seq[i-1] if i-1 < len(rate_seq) else 0
        interest[i] = prev_bal * rate / 12

    # 总现金流
    for i in range(25):
        total[i] = principal[i] + interest[i]

    return {
        'principal': principal,
        'interest': interest,
        'total': total
    }


def run_engine_c(
    df_coa_info: pd.DataFrame,
    df_coa_attribute: pd.DataFrame,
    df_business_plan: pd.DataFrame,
    df_current_position: pd.DataFrame,
    df_rate_scenario: pd.DataFrame = None,
    df_custom_strategy: pd.DataFrame = None,
    df_cashflow_schedule: pd.DataFrame = None
) -> pd.DataFrame:
    """
    ENGINE C 主入口：现金流计量完整流程。

    Args:
        df_coa_info:          账户册树形
        df_coa_attribute:      账户册属性（含 term 原始期限）
        df_business_plan:     业务计划 24 期
        df_current_position:  当前存量
        df_rate_scenario:     利率情景（可选；提供则用曲线基础利率，否则用存量利率）
        df_custom_strategy:   定价策略（可选；提供则叠加 BP）
        df_cashflow_schedule: 手工录入的现金流调度（可选；提供则覆盖默认 CF_PATTERN 算法）

    Returns:
        pd.DataFrame: 索引 coa_cd，列：
            - principal_0~24: 25 期本金
            - interest_0~24:  25 期利息
            - total_0~24:     25 期现金流（本金+利息）
    """
    # 1. 阶段 A：获取分摊后余额/日均（含 M0 基线）
    bp_full = get_bp_with_baseline(df_coa_info, df_business_plan, df_current_position, df_coa_attribute)

    # 1.5 准备 schedule 查找表（如果提供）
    #    结构：{ (coa_cd, term): { period: principal_ratio } }
    schedule_map = {}
    if df_cashflow_schedule is not None and len(df_cashflow_schedule) > 0:
        for _, row in df_cashflow_schedule.iterrows():
            key = (row['coa_cd'], row['term'])
            if key not in schedule_map:
                schedule_map[key] = {}
            schedule_map[key][int(row['period'])] = float(row['principal_ratio'] or 0)

    # 2. 准备每个节点的 25 期余额 [M0, M1, ..., M24]
    balance_matrix = pd.DataFrame(index=bp_full.index)
    balance_matrix['m0'] = bp_full['m0_balance']
    for i in range(1, 25):
        balance_matrix[f'm{i}'] = bp_full[f'cum_balance_{i}']

    # 3. 准备每个节点的 24 期利率（M0 没有利率）
    # 默认利率：基于存量 rate（月度利息）+ 12 / 平均余额
    rate_matrix = pd.DataFrame(index=bp_full.index)
    for i in range(1, 25):
        rate_matrix[f'm{i}'] = bp_full['m0_rate'] / 100  # 转为小数

    # 如果有利率情景和定价策略，叠加
    if df_rate_scenario is not None and df_custom_strategy is not None:
        from calculate_engine.engines.engine_b_pricing import run_engine_b
        pricing_result = run_engine_b(
            df_coa_info=df_coa_info,
            df_coa_attribute=df_coa_attribute,
            df_custom_strategy=df_custom_strategy,
            df_rate_scenario=df_rate_scenario,
            df_business_plan=df_business_plan,
            df_current_position=df_current_position
        )
        for i in range(1, 25):
            rate_matrix[f'm{i}'] = pricing_result[f'pricing_rate_{i}'].reindex(rate_matrix.index).fillna(0)

    # 4. 准备每个节点的期限映射（coa_cd → term）
    if 'term' in df_coa_attribute.columns:
        term_map = dict(zip(df_coa_attribute['coa_cd'], df_coa_attribute['term']))
    else:
        term_map = {}

    # 5. 结果 DataFrame：每个账户册 75 列（principal/interest/total × 25 期）
    all_coa_cds = list(bp_full.index)
    result = pd.DataFrame(index=all_coa_cds)
    result.index.name = 'coa_cd'

    # 预创建列
    for prefix in ['principal', 'interest', 'total']:
        for i in range(25):
            result[f'{prefix}_{i}'] = 0.0

    # 6. 逐节点计算（向量化：用 numpy 加速）
    # 把 balance_matrix 转成 numpy [N x 25]
    balance_arr = balance_matrix.values.astype(np.float64)  # shape (N, 25)
    rate_arr = rate_matrix.values.astype(np.float64)  # shape (N, 24)

    # 对每个节点计算
    n = len(all_coa_cds)
    for idx in range(n):
        cd = all_coa_cds[idx]
        term = term_map.get(cd, '30Y')

        bal_seq = list(balance_arr[idx])  # 25 期
        rate_seq = list(rate_arr[idx])    # 24 期

        # 优先使用 schedule_map（手工录入），回退到 CF_PATTERN
        if schedule_map:
            schedule_key = (cd, term)
            if schedule_key in schedule_map:
                # 用手工录入的 principal_ratio 计算本金
                principal_list = [0.0] * 25
                for p, ratio in schedule_map[schedule_key].items():
                    if 1 <= p <= 24:
                        principal_list[p] = bal_seq[p] * ratio
                # 利息仍按"上期余额 × 利率/12"计算
                cf_principal = [0.0] + principal_list[1:]
                cf_interest = [0.0]
                for i in range(1, 25):
                    cf_interest.append(bal_seq[i - 1] * rate_seq[i - 1] / 12)
                cf_total = [p + inte for p, inte in zip(cf_principal, cf_interest)]
                cf = {
                    'principal': cf_principal,
                    'interest': cf_interest,
                    'total': cf_total,
                }
            else:
                # 该 (coa_cd, term) 没有 schedule 行，回退
                cf = simulate_cashflow_for_node(bal_seq, rate_seq, term)
        else:
            pattern = get_cf_pattern(term)
            cf = simulate_cashflow_for_node(bal_seq, rate_seq, term)

        for i in range(25):
            result.at[cd, f'principal_{i}'] = cf['principal'][i]
            result.at[cd, f'interest_{i}'] = cf['interest'][i]
            result.at[cd, f'total_{i}'] = cf['total'][i]

    return result


if __name__ == '__main__':
    """冒烟测试"""
    data = load_all_params()

    result = run_engine_c(
        df_coa_info=data.coa_info,
        df_coa_attribute=data.coa_attribute,
        df_business_plan=data.business_plan,
        df_current_position=data.current_position,
        df_rate_scenario=data.rate_scenario,
        df_custom_strategy=data.custom_strategy
    )

    print(f"=== ENGINE C 现金流计量结果 ===")
    print(f"账户册数: {len(result)}")
    print(f"列数: {len(result.columns)} (75 = 25×3: 本金/利息/总)")

    # 看一个有数据的叶节点
    print(f"\n=== 典型账户册现金流（1_1_2 存放央行法定准备金_30Y）===")
    cd = '1_1_2'
    if cd in result.index:
        for i in [0, 1, 2, 12, 24]:
            p = float(result.loc[cd, f'principal_{i}'])
            inte = float(result.loc[cd, f'interest_{i}'])
            t = float(result.loc[cd, f'total_{i}'])
            print(f"  M{i:>2}: 本金={p:>15.2f}  利息={inte:>12.2f}  总={t:>15.2f}")