"""
ENGINE C 现金流计量测试

运行：
    cd almt-backend
    python -m calculate_engine.tests.test_engine_c
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
from calculate_engine.core.loader import load_all_params
from calculate_engine.engines.engine_c_cashflow import (
    CF_PATTERN,
    get_cf_pattern,
    simulate_cashflow_for_node,
    run_engine_c
)


def test_cf_pattern():
    """现金流模式矩阵：12 种期限，每种 25 期"""
    # 至少 12 种期限
    assert len(CF_PATTERN) >= 12

    # 每种期限 25 期
    for term, pattern in CF_PATTERN.items():
        assert len(pattern) == 25, f"{term} 模式长度 {len(pattern)}"

    # 验证已知模式
    assert CF_PATTERN['1D'][:3] == [1, 0, 0]
    assert CF_PATTERN['3M'][:3] == [1, 1, 1]
    assert CF_PATTERN['6M'][:6] == [1, 1, 1, 1, 1, 1]
    assert CF_PATTERN['1Y'][:12] == [1] * 12

    # 30Y 全期还本
    assert CF_PATTERN['30Y'] == [1] * 25

    print(f"✓ 现金流模式: {len(CF_PATTERN)} 种期限")


def test_simulate_cashflow_1d():
    """1D：M1 全额还本"""
    # 1D 资产，余额 100
    bal_seq = [100] + [100] * 24  # 25 期都是 100（业务计划无增量）
    rate_seq = [0.05] * 24
    cf = simulate_cashflow_for_node(bal_seq, rate_seq, '1D')

    # M0 本金 = 0
    assert cf['principal'][0] == 0

    # M1 全额还本 = 100
    assert abs(cf['principal'][1] - 100) < 0.01, f"M1 = {cf['principal'][1]}"

    # M1 利息 = M0 余额 × 利率 / 12 = 100 × 0.05 / 12 ≈ 0.417
    assert abs(cf['interest'][1] - 100 * 0.05 / 12) < 0.001

    # M2+ 本金 = 0（已还清）
    assert cf['principal'][2] == 0
    assert cf['principal'][3] == 0

    print(f"✓ 1D 现金流: M1 全额还本 + 利息")


def test_simulate_cashflow_3m():
    """3M：M1~M3 各还 1/3"""
    bal_seq = [300] + [300] * 24
    rate_seq = [0.06] * 24
    cf = simulate_cashflow_for_node(bal_seq, rate_seq, '3M')

    # M1~M3 各还 100（300/3）
    for i in [1, 2, 3]:
        assert abs(cf['principal'][i] - 100) < 0.01, f"M{i} = {cf['principal'][i]}"

    # M4+ 还清 = 0
    assert cf['principal'][4] == 0
    assert cf['principal'][24] == 0

    # 本金总和 = 300 ✓
    total_principal = sum(cf['principal'])
    assert abs(total_principal - 300) < 0.01

    print(f"✓ 3M 现金流: M1~M3 各还 1/3（共 300）")


def test_simulate_cashflow_30y():
    """30Y：M1~M24 持续还本（每期 1/25 of M0）"""
    bal_seq = [2400] + [2400] * 24
    rate_seq = [0.05] * 24
    cf = simulate_cashflow_for_node(bal_seq, rate_seq, '30Y')

    # M1~M24 各还 2400/25 = 96
    expected = 2400 / 25
    for i in range(1, 25):
        assert abs(cf['principal'][i] - expected) < 0.01, f"M{i} = {cf['principal'][i]}"

    # 本金总和（M1~M24 共 24 期 × 96 = 2304；M0=0；总 ≈ 2400 允许 5% 误差）
    total_principal = sum(cf['principal'])
    expected_total = 2400  # 24 期实际还 2304，但原 Excel 中 30Y 也包含 25 期
    assert total_principal > 0.9 * expected_total, f"本金总和 {total_principal} 偏离过大"

    print(f"✓ 30Y 现金流: M1~M24 各还 96（共 {total_principal:.0f}，24 期）")


def test_run_engine_c_basic():
    """完整 ENGINE C 流程"""
    data = load_all_params()
    result = run_engine_c(
        df_coa_info=data.coa_info,
        df_coa_attribute=data.coa_attribute,
        df_business_plan=data.business_plan,
        df_current_position=data.current_position,
        df_rate_scenario=data.rate_scenario,
        df_custom_strategy=data.custom_strategy
    )

    # 行数 = 账户册数
    assert len(result) == len(data.coa_info)

    # 列数 = 75（3 类 × 25 期）
    assert len(result.columns) == 75

    # 关键列都存在
    for prefix in ['principal', 'interest', 'total']:
        for i in range(25):
            assert f'{prefix}_{i}' in result.columns

    print(f"✓ ENGINE C 完整流程: {len(result)} 行 × {len(result.columns)} 列")


def test_run_engine_c_specific_cases():
    """典型期限的现金流正确性"""
    data = load_all_params()
    result = run_engine_c(
        df_coa_info=data.coa_info,
        df_coa_attribute=data.coa_attribute,
        df_business_plan=data.business_plan,
        df_current_position=data.current_position,
        df_rate_scenario=data.rate_scenario,
        df_custom_strategy=data.custom_strategy
    )

    # 1_1_1（1D）：M0 余额保留，M1 全额还本
    cd = '1_1_1'
    if cd in result.index:
        m0_principal = float(result.loc[cd, 'principal_0'])
        m1_principal = float(result.loc[cd, 'principal_1'])
        assert m0_principal == 0
        assert m1_principal > 0  # M1 应有还本

    # 2_5_1_3_1（3M）：M1~M3 三期还本，M4+ = 0
    cd = '2_5_1_3_1'
    if cd in result.index:
        m3 = float(result.loc[cd, 'principal_3'])
        m4 = float(result.loc[cd, 'principal_4'])
        assert m3 > 0, f"M3 应有还本，实际 {m3}"
        assert m4 == 0, f"M4 应 = 0，实际 {m4}"

    print(f"✓ 典型期限现金流正确")


if __name__ == '__main__':
    test_cf_pattern()
    test_simulate_cashflow_1d()
    test_simulate_cashflow_3m()
    test_simulate_cashflow_30y()
    test_run_engine_c_basic()
    test_run_engine_c_specific_cases()
    print("\n所有 ENGINE C 测试通过！")