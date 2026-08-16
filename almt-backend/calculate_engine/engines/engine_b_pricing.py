"""
ENGINE B 定价策略分摊（Pricing Strategy Allocation）

职责：把每个账户册的 24 期定价策略 BP 叠加到基础利率上，并计算 FTP 收入。

详见 MEASUREMENT_MANUAL.md 第 3 章

核心算法：
  - 输入：
      - 阶段 A 输出的分摊后余额/日均（24 期）
      - almt_param_custom_strategy（每账户册 24 期 BP）
      - almt_param_rate_scenario（曲线 24 期值）
      - almt_coa_attribute（每账户册 curve_id）
  - 计算：
      - new_rate_i = base_rate_i + strategy_M_i / 10000   # BP 转小数
      - ftp_income_i = average_balance_i × new_rate_i / 12  # 月化 FTP
      - delta_ftp_i = average_balance_i × strategy_M_i / 10000 / 12  # 策略增量 FTP
  - 输出：每账户册 24 期定价后利率 + FTP 收入 + ΔFTP
"""
from calculate_engine.core.coa_tree import build_coa_tree, aggregate_bottom_up
from calculate_engine.core.loader import load_all_params
from calculate_engine.engines import get_bp_with_baseline
import pandas as pd


def get_base_rates(
    df_coa_attribute: pd.DataFrame,
    df_rate_scenario: pd.DataFrame,
    default_curve_id: str = None
) -> pd.DataFrame:
    """
    根据 curve_id 查每账户册的 24 期基础利率。

    Args:
        df_coa_attribute: 账户册属性（含 curve_id）
        df_rate_scenario: 利率情景（含 m1_value~m24_value）
        default_curve_id: 默认曲线 ID（账户册没有 curve_id 时使用）

    Returns:
        pd.DataFrame: 索引 coa_cd，列 base_rate_1~24
    """
    # 1. 整理利率情景：curve_id → {m1: rate1, m2: rate2, ...}
    rate_map = {}  # curve_id -> {m_i: rate}
    for _, row in df_rate_scenario.iterrows():
        cid = row['curve_id']
        if pd.notna(cid):
            rates = {i: row.get(f'm{i}_value', 0) or 0 for i in range(1, 25)}
            rate_map[cid] = rates

    # 2. 给每账户册查基础利率
    result = pd.DataFrame(index=df_coa_attribute['coa_cd'].tolist())
    result.index.name = 'coa_cd'

    for _, row in df_coa_attribute.iterrows():
        cd = row['coa_cd']
        cid = row.get('curve_id', default_curve_id)
        rates = rate_map.get(cid, {i: 0 for i in range(1, 25)})
        for i in range(1, 25):
            result.loc[cd, f'base_rate_{i}'] = rates.get(i, 0)

    result = result.fillna(0)
    return result


def apply_pricing_strategy(
    df_base_rates: pd.DataFrame,
    df_custom_strategy: pd.DataFrame
) -> pd.DataFrame:
    """
    把定价策略 BP 叠加到基础利率（只返回 pricing_rate_X，不返回 base_rate_X）。

    Args:
        df_base_rates:        基础利率（base_rate_1~24）
        df_custom_strategy:   定价策略（strategy_M1~M24，单位 BP）

    Returns:
        pd.DataFrame: 索引 coa_cd，列 pricing_rate_1~24（叠加后利率）
    """
    if 'coa_cd' in df_custom_strategy.columns:
        strategy_indexed = df_custom_strategy.set_index('coa_cd')
    else:
        strategy_indexed = df_custom_strategy.copy()
    strategy_indexed.index.name = 'coa_cd'

    pricing = pd.DataFrame(index=df_base_rates.index)
    pricing.index.name = 'coa_cd'

    for i in range(1, 25):
        strat_col = f'strategy_M{i}'
        if strat_col in strategy_indexed.columns:
            bp_values = strategy_indexed[strat_col].reindex(pricing.index).fillna(0)
            pricing[f'pricing_rate_{i}'] = df_base_rates[f'base_rate_{i}'].values + bp_values.values * 0.0001
        else:
            pricing[f'pricing_rate_{i}'] = df_base_rates[f'base_rate_{i}'].values

    return pricing


def calculate_ftp_income(
    df_bp_full: pd.DataFrame,
    df_pricing_rates: pd.DataFrame
) -> pd.DataFrame:
    """
    计算 FTP 收入和 ΔFTP。

    ftp_income_i = average_balance_i × pricing_rate_i / 12
    delta_ftp_i = average_balance_i × strategy_bp_i / 10000 / 12

    Args:
        df_bp_full:        阶段 A 输出（含 cum_average_1~24, m0_rate 等）
        df_pricing_rates:  ENGINE B 输出（含 pricing_rate_1~24）

    Returns:
        pd.DataFrame: 索引 coa_cd，列 ftp_income_1~24, delta_ftp_1~24
    """
    result = pd.DataFrame(index=df_pricing_rates.index.copy())
    result.index.name = 'coa_cd'

    for i in range(1, 25):
        # 平均余额 = M0 平均 + Σ M1~Mi 平均增量
        avg_col = f'cum_average_{i}'
        rate_col = f'pricing_rate_{i}'

        if avg_col in df_bp_full.columns and rate_col in df_pricing_rates.columns:
            avg = df_bp_full[avg_col].reindex(result.index).fillna(0)
            rate = df_pricing_rates[rate_col].reindex(result.index).fillna(0)
            # FTP 收入（年化利率×平均余额/12 = 月度 FTP 收入）
            result[f'ftp_income_{i}'] = avg * rate / 12

            # ΔFTP = (pricing_rate - base_rate) × avg / 12
            base_col = f'base_rate_{i}'
            if base_col in df_pricing_rates.columns:
                base = df_pricing_rates[base_col].reindex(result.index).fillna(0)
                result[f'delta_ftp_{i}'] = avg * (rate - base) / 12
            else:
                result[f'delta_ftp_{i}'] = 0

    result = result.fillna(0)
    return result


def run_engine_b(
    df_coa_info: pd.DataFrame,
    df_coa_attribute: pd.DataFrame,
    df_custom_strategy: pd.DataFrame,
    df_rate_scenario: pd.DataFrame,
    df_business_plan: pd.DataFrame,
    df_current_position: pd.DataFrame
) -> pd.DataFrame:
    """
    ENGINE B 主入口：定价策略分摊完整流程。

    Returns:
        pd.DataFrame: 索引 coa_cd（所有账户册），列：
            - base_rate_1~24: 基础利率（来自利率情景）
            - pricing_rate_1~24: 叠加定价策略后的利率
            - ftp_income_1~24: FTP 月度收入
            - delta_ftp_1~24: 策略增量的 FTP 收入
    """
    # 1. 阶段 A：获取分摊后余额/日均（索引 = 所有账户册）
    bp_full = get_bp_with_baseline(df_coa_info, df_business_plan, df_current_position, df_coa_attribute)

    # 2. 查基础利率（按 curve_id；用 coa_attribute 才能拿到 curve_id）
    base_rates = get_base_rates(df_coa_attribute, df_rate_scenario)
    # 重索引到所有账户册（没配属性的账户册基础利率=0）
    all_coa_cds = df_coa_info['coa_cd'].tolist()
    base_rates = base_rates.reindex(all_coa_cds).fillna(0)

    # 3. 叠加定价策略 BP
    pricing_rates = apply_pricing_strategy(base_rates, df_custom_strategy)

    # 4. 计算 FTP 收入
    ftp = calculate_ftp_income(bp_full, pricing_rates)

    # 5. 合并输出
    result = pd.concat([base_rates, pricing_rates, ftp], axis=1)
    return result


if __name__ == '__main__':
    """冒烟测试"""
    data = load_all_params()

    result = run_engine_b(
        df_coa_info=data.coa_info,
        df_coa_attribute=data.coa_attribute,
        df_custom_strategy=data.custom_strategy,
        df_rate_scenario=data.rate_scenario,
        df_business_plan=data.business_plan,
        df_current_position=data.current_position
    )

    print(f"=== ENGINE B 定价策略分摊结果 ===")
    print(f"账户册数: {len(result)}")
    print(f"列数: {len(result.columns)} (96 = 24×4: 基础/定价/FTP/ΔFTP)")

    # 看几个有定价策略的账户册
    strategy_cds = data.custom_strategy['coa_cd'].tolist()
    print(f"\n=== 有定价策略的账户册（{len(strategy_cds)} 个）前 5 个 ===")
    for cd in strategy_cds[:5]:
        if cd in result.index:
            row = result.loc[cd]
            m1_base = row['base_rate_1']
            m1_pricing = row['pricing_rate_1']
            m1_ftp = row['ftp_income_1']
            m1_delta = row['delta_ftp_1']
            print(f"  {cd}: M1基础={m1_base:.4%}  定价后={m1_pricing:.4%}  FTP={m1_ftp:>12.2f}  ΔFTP={m1_delta:>12.2f}")