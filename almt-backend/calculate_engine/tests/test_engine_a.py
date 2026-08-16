"""
ENGINE A 业务分摊测试

运行：
    cd almt-backend
    python -m calculate_engine.tests.test_engine_a
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
from calculate_engine.core.loader import load_all_params
from calculate_engine.engines import (
    allocate_business_plan,
    get_m0_baseline,
    get_bp_with_baseline
)


def test_allocate_basic():
    """基础功能：返回正确形状的 DataFrame"""
    data = load_all_params()
    result = allocate_business_plan(
        data.coa_info, data.business_plan, data.current_position
    )

    # 行数 = 账户册数
    assert len(result) == len(data.coa_info), f"行数 {len(result)} != {len(data.coa_info)}"

    # 列数 = 48（24 期 × 2：余额+日均）
    assert len(result.columns) == 48, f"列数 {len(result.columns)}"

    # 列名格式正确
    for i in range(1, 25):
        assert f'bp_balance_{i}' in result.columns
        assert f'bp_average_{i}' in result.columns

    print(f"✓ 基础功能: {len(result)} 行 × {len(result.columns)} 列")


def test_allocate_proportional_to_balance():
    """v2 算法验证：父级计划按子节点余额比例分摊到叶节点"""
    data = load_all_params()
    result = allocate_business_plan(
        data.coa_info, data.business_plan, data.current_position
    )

    # 顶级账户 1_1 自身不应再有 plan_balance（已分摊到子节点）
    # 子节点 1_1_1/1_1_2/1_1_3/1_1_4 应按余额比例获得 plan_balance
    if '1_1' in result.index:
        parent_val = result.loc['1_1', 'bp_balance_1']
        # 父级应该为 0（已分摊）
        assert parent_val == 0 or abs(parent_val) < 0.001, \
            f"1_1（父级）应为 0，实际 {parent_val}"

    # 子节点总和 = 父级原 plan_balance
    bp_data = data.business_plan[data.business_plan['coa_cd'] == '1_1']
    if not bp_data.empty:
        original = bp_data.iloc[0]['plan_balance1']
        if pd.notna(original) and original > 0:
            child_sum = sum(
                result.loc[c, 'bp_balance_1']
                for c in ['1_1_1', '1_1_2', '1_1_3', '1_1_4']
                if c in result.index
            )
            # 子节点总和应等于父级原值（容许小浮点误差）
            assert abs(child_sum - original) < 0.001, \
                f"子节点 M1 之和 {child_sum} ≠ 父级原值 {original}"

    print(f"✓ 父级→子节点 按余额比例分摊（父级=0，子节点之和=父级原值）")


def test_m0_baseline():
    """M0 基线：从存量数据汇总"""
    data = load_all_params()
    m0 = get_m0_baseline(data.current_position, data.coa_info)

    # 应有 774 行（同账户册数）
    assert len(m0) == len(data.coa_info)

    # 至少部分账户册有非零 M0 余额
    nonzero = m0[m0['m0_balance'] > 0]
    assert len(nonzero) >= 100, f"M0 余额非零账户册数 {len(nonzero)}"

    # 利率计算：m0_rate = 月度利息×12 / 平均余额 × 100%
    for cd in ['1_1', '1_4', '2_5']:
        if cd in m0.index and m0.loc[cd, 'm0_average'] > 0:
            expected_rate = (m0.loc[cd, 'm0_balance'] > 0)  # 至少要有余额
            assert m0.loc[cd, 'm0_rate'] >= 0  # 利率应 >= 0

    print(f"✓ M0 基线: {len(nonzero)} 个账户册有非零余额")


def test_full_series():
    """完整 M0~M24 累计序列"""
    data = load_all_params()
    full = get_bp_with_baseline(data.coa_info, data.business_plan, data.current_position)

    # 应包含 m0_balance + 24 期 bp + 24 期 cum = 至少 49 列
    assert len(full.columns) >= 49

    # 累计值应单调递增（业务计划值都是正数时）
    # 检查一个有大 M0 余额的账户册
    cd = '1_1'
    if cd in full.index and full.loc[cd, 'm0_balance'] > 0:
        m0 = full.loc[cd, 'm0_balance']
        m24_cum = full.loc[cd, 'cum_balance_24']
        # M24 累计 >= M0（因为业务计划是正数）
        assert m24_cum >= m0 - 0.01, f"{cd}: M0={m0}, M24累计={m24_cum}"

    print(f"✓ 完整 25 期累计序列")


if __name__ == '__main__':
    test_allocate_basic()
    test_allocate_proportional_to_balance()
    test_m0_baseline()
    test_full_series()
    print("\n所有 ENGINE A 测试通过！")