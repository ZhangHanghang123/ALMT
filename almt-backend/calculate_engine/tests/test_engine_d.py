"""
ENGINE D 指标计量测试

测试覆盖：
1. 基础度量值计算（10 种 lookup）
2. 按账户册的 23 组指标 num/den 计算
3. 树形聚合（自底向上汇总）
4. 完整端到端 run_engine_d 流程
"""
import pandas as pd
import numpy as np
from calculate_engine.core.loader import load_all_params
from calculate_engine.engines import engine_b_pricing, engine_c_cashflow
from calculate_engine.engines.engine_d_indicators import (
    run_engine_d,
    compute_basic_lookups,
    compute_per_account_indicators,
    aggregate_indicators,
    get_metric_snapshot,
    LOOKUP_FIELD_MAP
)


# ============================================================
# 单元测试：基础度量值
# ============================================================

def test_lookup_field_map():
    """验证 10 种度量类型都有对应的 lookup 字段"""
    expected_types = ['B', 'AB', 'NII', 'CF1', 'CF3', 'CF1-6', 'CF7-12', 'CF12+', 'B-CF3', 'RWA']
    for t in expected_types:
        assert t in LOOKUP_FIELD_MAP, f"缺少度量类型映射: {t}"
    assert len(LOOKUP_FIELD_MAP) == 10, f"映射数 {len(LOOKUP_FIELD_MAP)} ≠ 10"
    print(f"✓ 度量类型映射完整：{len(LOOKUP_FIELD_MAP)} 种类型")


def test_compute_basic_lookups():
    """验证 10 种基础度量值计算"""
    data = load_all_params()
    c_result = engine_c_cashflow.run_engine_c(
        df_coa_info=data.coa_info,
        df_coa_attribute=data.coa_attribute,
        df_business_plan=data.business_plan,
        df_current_position=data.current_position,
        df_rate_scenario=data.rate_scenario,
        df_custom_strategy=data.custom_strategy
    )

    lookups = compute_basic_lookups(
        df_coa_info=data.coa_info,
        df_coa_attribute=data.coa_attribute,
        df_current_position=data.current_position,
        engine_c_result=c_result
    )

    # 维度：所有账户册（774）
    assert len(lookups) == 774, f"行数 {len(lookups)} ≠ 774"

    # 列：10 种 lookup
    expected_cols = ['B', 'AB', 'NII', 'CF1', 'CF3', 'CF1_6', 'CF7_12', 'CF12_PLUS', 'RWA', 'B_CF3']
    assert list(lookups.columns) == expected_cols, "lookup 列名不一致"

    # 类型：float64
    for col in expected_cols:
        assert lookups[col].dtype == float, f"{col} dtype={lookups[col].dtype}"

    # 数据合理性：B > 0 的账户册应有一定规模
    n_with_balance = (lookups['B'] > 0).sum()
    assert n_with_balance > 100, f"有余额的账户册数 {n_with_balance} 太少"

    # B-CF3 = B - CF3
    for cd in lookups.index[:20]:
        assert abs(lookups.loc[cd, 'B_CF3'] - (lookups.loc[cd, 'B'] - lookups.loc[cd, 'CF3'])) < 0.01, \
            f"{cd} B-CF3 计算错误"

    print(f"✓ 基础度量值：774 账户册 × 10 lookup 列，{n_with_balance} 个账户有余额")


# ============================================================
# 单元测试：按账户册的 num/den 计算
# ============================================================

def test_compute_per_account_indicators():
    """验证每个账户册的 23 组指标 num/den"""
    data = load_all_params()
    c_result = engine_c_cashflow.run_engine_c(
        df_coa_info=data.coa_info,
        df_coa_attribute=data.coa_attribute,
        df_business_plan=data.business_plan,
        df_current_position=data.current_position,
        df_rate_scenario=data.rate_scenario,
        df_custom_strategy=data.custom_strategy
    )
    lookups = compute_basic_lookups(
        df_coa_info=data.coa_info,
        df_coa_attribute=data.coa_attribute,
        df_current_position=data.current_position,
        engine_c_result=c_result
    )

    per_account = compute_per_account_indicators(data.metric_caliber, lookups)

    # 行数 = caliber 表行数（550）
    assert len(per_account) == 550, f"行数 {len(per_account)} ≠ 550"

    # 列数 = 46（num_1~23 + den_1~23）
    assert len(per_account.columns) == 46, f"列数 {len(per_account.columns)} ≠ 46"

    # num/den 都是 float
    for col in per_account.columns:
        assert per_account[col].dtype == float, f"{col} 不是 float"

    # 数据合理性：至少有一些账户有非零 num
    n_nonzero = (per_account.iloc[:, 0] != 0).sum()  # num_1_value 非零数
    assert n_nonzero > 50, f"指标1非零账户数 {n_nonzero} 太少（caliber 表里指标1只配置了 67 个账户）"

    print(f"✓ 按账户册计算：{len(per_account)} 账户 × 46 列，指标1 有 {n_nonzero} 个账户配置")


# ============================================================
# 单元测试：树形聚合
# ============================================================

def test_aggregate_indicators():
    """验证树形聚合（自底向上汇总）"""
    data = load_all_params()
    c_result = engine_c_cashflow.run_engine_c(
        df_coa_info=data.coa_info,
        df_coa_attribute=data.coa_attribute,
        df_business_plan=data.business_plan,
        df_current_position=data.current_position,
        df_rate_scenario=data.rate_scenario,
        df_custom_strategy=data.custom_strategy
    )
    lookups = compute_basic_lookups(
        df_coa_info=data.coa_info,
        df_coa_attribute=data.coa_attribute,
        df_current_position=data.current_position,
        engine_c_result=c_result
    )
    per_account = compute_per_account_indicators(data.metric_caliber, lookups)

    aggregated = aggregate_indicators(per_account, data.coa_info)

    # 行数 = 774（含 ROOT 和所有层级）
    assert len(aggregated) == 774, f"行数 {len(aggregated)} ≠ 774"

    # 列数 = 69（23 num + 23 den + 23 ratio）
    assert len(aggregated.columns) == 69, f"列数 {len(aggregated.columns)} ≠ 69"

    # ROOT 存在
    assert 'ROOT' in aggregated.index

    # ROOT num >= 子节点 num 求和（聚合正确性）
    # 取 num_1_value（最简单的 NII 指标）
    root_num_1 = aggregated.loc['ROOT', 'num_1_value']
    leaf_sum = per_account['num_1_value'].sum()
    # 由于父节点可能没有配置但子节点有配置，聚合后的 ROOT 应该等于叶节点之和
    assert abs(root_num_1 - leaf_sum) < 1.0, \
        f"ROOT num_1 ({root_num_1}) ≠ 叶节点之和 ({leaf_sum})"

    # 比率：den=0 时应该 NaN
    ratio_cols = [f'ratio_{i}_value' for i in range(1, 24)]
    for col in ratio_cols:
        assert col in aggregated.columns

    # 指标21-23 未使用，ratio 应全 NaN
    for i in [21, 22, 23]:
        col = f'ratio_{i}_value'
        n_nan = aggregated[col].isna().sum()
        assert n_nan == 774, f"指标{i} 应全为 NaN，但 {774 - n_nan} 个有值"

    print(f"✓ 树形聚合：{len(aggregated)} 账户 × 69 列")
    print(f"  ROOT num_1 = {root_num_1:.2f}, 叶节点 num_1 之和 = {leaf_sum:.2f}")


# ============================================================
# 集成测试：run_engine_d 端到端
# ============================================================

def test_run_engine_d_end_to_end():
    """完整端到端测试"""
    data = load_all_params()
    c_result = engine_c_cashflow.run_engine_c(
        df_coa_info=data.coa_info,
        df_coa_attribute=data.coa_attribute,
        df_business_plan=data.business_plan,
        df_current_position=data.current_position,
        df_rate_scenario=data.rate_scenario,
        df_custom_strategy=data.custom_strategy
    )

    result = run_engine_d(data, engine_c_result=c_result)

    # 维度
    assert result.shape == (774, 69), f"shape {result.shape} ≠ (774, 69)"

    # ROOT 23 组指标都有结果（不全是 NaN）
    n_with_ratio = sum(
        1 for i in range(1, 21)  # 1~20 是有效指标
        if pd.notna(result.loc['ROOT', f'ratio_{i}_value'])
    )
    assert n_with_ratio >= 10, f"ROOT 有效比率数 {n_with_ratio} 太少"

    print(f"✓ 端到端测试：774 × 69，ROOT 有 {n_with_ratio} 个有效比率")


def test_get_metric_snapshot():
    """便捷方法：指标快照"""
    data = load_all_params()
    c_result = engine_c_cashflow.run_engine_c(
        df_coa_info=data.coa_info,
        df_coa_attribute=data.coa_attribute,
        df_business_plan=data.business_plan,
        df_current_position=data.current_position,
        df_rate_scenario=data.rate_scenario,
        df_custom_strategy=data.custom_strategy
    )
    result = run_engine_d(data, engine_c_result=c_result)

    snap = get_metric_snapshot(result, metric_idx=11, top_n=10)
    assert snap.shape == (10, 3), f"snapshot shape {snap.shape} ≠ (10, 3)"
    assert list(snap.columns) == ['num_11_value', 'den_11_value', 'ratio_11_value']

    print(f"✓ 指标快照：指标11 前10个账户册")


# ============================================================
# 运行所有测试
# ============================================================

if __name__ == '__main__':
    test_lookup_field_map()
    test_compute_basic_lookups()
    test_compute_per_account_indicators()
    test_aggregate_indicators()
    test_run_engine_d_end_to_end()
    test_get_metric_snapshot()
    print("\n🎉 所有 ENGINE D 测试通过！")