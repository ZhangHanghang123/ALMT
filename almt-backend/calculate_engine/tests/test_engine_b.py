"""
ENGINE B 定价策略分摊测试

运行：
    cd almt-backend
    python -m calculate_engine.tests.test_engine_b
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
from calculate_engine.core.loader import load_all_params
from calculate_engine.engines.engine_b_pricing import (
    get_base_rates,
    apply_pricing_strategy,
    calculate_ftp_income,
    run_engine_b
)


def test_get_base_rates():
    """基础利率：按 curve_id 查利率情景"""
    data = load_all_params()
    base_rates = get_base_rates(data.coa_attribute, data.rate_scenario)

    # 至少应包含所有有属性的账户册
    assert len(base_rates) == len(data.coa_attribute)

    # 24 期基础利率列
    for i in range(1, 25):
        assert f'base_rate_{i}' in base_rates.columns

    print(f"✓ 基础利率: {len(base_rates)} 行 × 24 期")


def test_apply_pricing_strategy():
    """叠加定价策略：BP → 利率"""
    data = load_all_params()
    base_rates = get_base_rates(data.coa_attribute, data.rate_scenario)
    pricing_rates = apply_pricing_strategy(base_rates, data.custom_strategy)

    # 列数 = 24（只有 pricing_rate，不含 base_rate）
    assert len(pricing_rates.columns) == 24

    # 验证 BP 叠加正确
    for cd in data.custom_strategy['coa_cd']:
        if cd in pricing_rates.index:
            base_m1 = float(base_rates.loc[cd, 'base_rate_1'])
            strat_m1 = float(data.custom_strategy[data.custom_strategy['coa_cd'] == cd].iloc[0]['strategy_M1'] or 0)
            pricing_m1 = float(pricing_rates.loc[cd, 'pricing_rate_1'])
            expected = base_m1 + strat_m1 * 0.0001
            assert abs(pricing_m1 - expected) < 1e-6, \
                f"{cd}: pricing_rate={pricing_m1}, expected={expected}"

    print(f"✓ 定价策略叠加: BP → 利率")


def test_calculate_ftp_income():
    """FTP 收入 = 平均余额 × 利率 / 12"""
    data = load_all_params()
    base_rates = get_base_rates(data.coa_attribute, data.rate_scenario)
    pricing_rates = apply_pricing_strategy(base_rates, data.custom_strategy)

    # 用 ENGINE A 的全量数据
    from calculate_engine.engines import get_bp_with_baseline
    bp_full = get_bp_with_baseline(data.coa_info, data.business_plan, data.current_position)

    ftp = calculate_ftp_income(bp_full, pricing_rates)

    # 24 + 24 = 48 列
    assert len(ftp.columns) == 48

    # FTP 公式：ftp_income_1 = cum_average_1 × pricing_rate_1 / 12
    for cd in ['1_1', '1_4', '2_5']:
        if cd in ftp.index and cd in pricing_rates.index:
            avg = float(bp_full.loc[cd, 'cum_average_1']) if 'cum_average_1' in bp_full.columns else 0
            rate = float(pricing_rates.loc[cd, 'pricing_rate_1'])
            expected_ftp = avg * rate / 12
            actual_ftp = float(ftp.loc[cd, 'ftp_income_1'])
            assert abs(actual_ftp - expected_ftp) < 0.01, \
                f"{cd}: FTP={actual_ftp}, expected={expected_ftp}"

    print(f"✓ FTP 收入: 公式正确")


def test_run_engine_b():
    """完整 ENGINE B 流程"""
    data = load_all_params()
    result = run_engine_b(
        df_coa_info=data.coa_info,
        df_coa_attribute=data.coa_attribute,
        df_custom_strategy=data.custom_strategy,
        df_rate_scenario=data.rate_scenario,
        df_business_plan=data.business_plan,
        df_current_position=data.current_position
    )

    # 行数 = 账户册数
    assert len(result) == len(data.coa_info)

    # 列数 = 96（4 类 × 24 期：基础/定价/FTP/ΔFTP）
    assert len(result.columns) == 96, f"列数 {len(result.columns)} != 96"

    # 关键列都存在
    expected_cols = []
    for prefix in ['base_rate', 'pricing_rate']:
        for i in range(1, 25):
            expected_cols.append(f'{prefix}_{i}')
    # ftp 和 delta 是交错排列（calculate_ftp_income 同时输出两者）
    for i in range(1, 25):
        expected_cols.append(f'ftp_income_{i}')
        expected_cols.append(f'delta_ftp_{i}')
    assert list(result.columns) == expected_cols, f"列名/顺序不一致\n实际: {list(result.columns)}"

    print(f"✓ 完整 ENGINE B: {len(result)} 行 × {len(result.columns)} 列")


if __name__ == '__main__':
    test_get_base_rates()
    test_apply_pricing_strategy()
    test_calculate_ftp_income()
    test_run_engine_b()
    print("\n所有 ENGINE B 测试通过！")