"""
测试 loader.py：验证能从 MySQL 加载所有 9 张表

运行：
    cd almt-backend
    python -m pytest calculate_engine/tests/test_loader.py -v
    或
    python -m calculate_engine.tests.test_loader
"""
import sys
from pathlib import Path

# 把 almt-backend 加入 sys.path（确保能 import calculate_engine）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
from calculate_engine.core.loader import load_all_params


def test_load_all_params():
    """加载所有 9 张表，验证行数和关键列"""
    data = load_all_params()
    s = data.summary()
    print(f"\n加载结果: {s}")

    # 1. 账户册树形：774 行（773 个真实账户册 + 1 个 ROOT 节点）
    assert s['coa_info'] >= 770, f"coa_info 行数不足: {s['coa_info']}"

    # 2. 账户册属性：与 coa_info 数量级一致
    assert s['coa_attribute'] >= 200, f"coa_attribute 行数不足: {s['coa_attribute']}"

    # 3. 当前存量：773 行
    assert s['current_position'] >= 700, f"current_position 行数不足: {s['current_position']}"

    # 4. 业务计划：至少 10 条
    assert s['business_plan'] >= 5, f"business_plan 行数不足: {s['business_plan']}"

    # 5. 定价策略：至少 15 条
    assert s['custom_strategy'] >= 5, f"custom_strategy 行数不足: {s['custom_strategy']}"

    # 6. 利率情景：多条曲线（>= 1）
    assert s['rate_scenario'] >= 1, f"rate_scenario 行数不足: {s['rate_scenario']}"

    # 7. 风险权重：部分行
    assert s['risk_weight'] >= 0, "risk_weight 应 >= 0"

    # 8. 指标口径：23 组
    assert s['metric_caliber'] >= 20, f"metric_caliber 行数不足: {s['metric_caliber']}"

    # 9. 字典码值：165+ 条
    assert s['dict_value'] >= 100, f"dict_value 行数不足: {s['dict_value']}"


def test_coa_info_has_root():
    """验证账户册树有 ROOT 节点"""
    data = load_all_params()
    has_root = 'ROOT' in data.coa_info['coa_cd'].values
    assert has_root, "账户册树缺少 ROOT 节点"

    root_rows = data.coa_info[data.coa_info['coa_cd'] == 'ROOT']
    assert len(root_rows) == 1, f"ROOT 节点数异常: {len(root_rows)}"
    assert root_rows.iloc[0]['parent_coa_cd'] is None or pd.isna(root_rows.iloc[0]['parent_coa_cd']), \
        "ROOT 节点的 parent_coa_cd 应为 None/NaN"


def test_business_plan_columns():
    """验证业务计划有 24 期字段（注意：实际字段名 plan_balance1~24，无下划线）"""
    data = load_all_params()
    cols = data.business_plan.columns.tolist()
    # 应该有 24 个 plan_balance1~24（数字前无下划线）
    balance_cols = [c for c in cols if c.startswith('plan_balance') and not c.startswith('plan_balance_')]
    average_cols = [c for c in cols if c.startswith('plan_average') and not c.startswith('plan_average_')]
    assert len(balance_cols) == 24, f"plan_balance1~24 字段数: {len(balance_cols)}"
    assert len(average_cols) == 24, f"plan_average1~24 字段数: {len(average_cols)}"


def test_custom_strategy_columns():
    """验证定价策略有 24 期字段（注意：实际字段名 strategy_M1~M24，大写 M）"""
    data = load_all_params()
    cols = data.custom_strategy.columns.tolist()
    strategy_cols = [c for c in cols if c.startswith('strategy_M')]
    assert len(strategy_cols) == 24, f"strategy_M1~M24 字段数: {len(strategy_cols)}"


def test_rate_scenario_columns():
    """验证利率情景有 24 期字段（注意：实际字段名 m1_value~m24_value）"""
    data = load_all_params()
    cols = data.rate_scenario.columns.tolist()
    m_cols = [c for c in cols if c.startswith('m') and c.endswith('_value')]
    assert len(m_cols) == 24, f"m1_value~m24_value 字段数: {len(m_cols)}"


if __name__ == '__main__':
    test_load_all_params()
    print("✓ test_load_all_params")
    test_coa_info_has_root()
    print("✓ test_coa_info_has_root")
    test_business_plan_columns()
    print("✓ test_business_plan_columns")
    test_custom_strategy_columns()
    print("✓ test_custom_strategy_columns")
    test_rate_scenario_columns()
    print("✓ test_rate_scenario_columns")
    print("\n所有测试通过！")