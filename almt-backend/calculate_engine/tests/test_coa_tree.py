"""
测试 coa_tree.py：验证账户册树形构建和聚合算法

运行：
    cd almt-backend
    python -m calculate_engine.tests.test_coa_tree
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
from calculate_engine.core.coa_tree import (
    build_coa_tree,
    flatten_tree,
    aggregate_bottom_up,
    coa_cd_to_depth_map
)
from calculate_engine.core.loader import load_all_params


def test_build_coa_tree():
    """验证能正确构建账户册树"""
    data = load_all_params()
    roots = build_coa_tree(data.coa_info, data.coa_attribute)

    # 应该有 1 个 ROOT 节点
    assert len(roots) == 1, f"根节点数: {len(roots)}（期望 1 个 ROOT）"
    assert roots[0].coa_cd == 'ROOT', f"根节点编码: {roots[0].coa_cd}"

    # ROOT 节点应有 12 个子节点（1_1~1_5, 2_1~2_6, 3_1）
    assert len(roots[0].children) == 12, \
        f"ROOT 子节点数: {len(roots[0].children)}（期望 12）"

    print(f"✓ ROOT 节点 + 12 个一级账户")


def test_flatten_tree():
    """验证树形展平包含所有节点"""
    data = load_all_params()
    roots = build_coa_tree(data.coa_info)
    flat = flatten_tree(roots)

    # 总节点数应等于 almt_coa_info 行数
    assert len(flat) == len(data.coa_info), \
        f"展平节点数 {len(flat)} != coa_info 行数 {len(data.coa_info)}"

    # 至少有一个叶节点
    leaf_nodes = [n for n in flat if n.leaf_flag == 1]
    assert len(leaf_nodes) > 100, f"叶节点数: {len(leaf_nodes)}"

    print(f"✓ 展平 {len(flat)} 个节点（{len(leaf_nodes)} 个叶节点）")


def test_aggregate_simple():
    """测试简单聚合：单节点值 → 父节点汇总"""
    data = load_all_params()
    roots = build_coa_tree(data.coa_info)

    # 测试场景：1_1_1 设 1000，其他都是 0
    values = pd.Series({'1_1_1': 1000.0})
    result = aggregate_bottom_up(values, roots)

    # 1_1_1 自身 = 1000
    assert result['1_1_1'] == 1000.0, f"1_1_1 = {result['1_1_1']}"

    # 1_1（1_1_1 的父） = 1000
    assert result['1_1'] == 1000.0, f"1_1 应 = 1000, 实际 = {result['1_1']}"

    # ROOT = 1000（所有 12 个一级账户的和，这里只有 1_1 有值）
    assert result['ROOT'] == 1000.0, f"ROOT 应 = 1000, 实际 = {result['ROOT']}"

    print("✓ 简单聚合：1_1_1=1000 正确传播到 ROOT")


def test_aggregate_multiple_children():
    """测试多子节点聚合"""
    data = load_all_params()
    roots = build_coa_tree(data.coa_info)

    # 找到 1_2_1_1_1 的兄弟节点
    parent_cd = '1_2_1_1'  # 存放同业款项_金融市场部
    df = data.coa_info
    children = df[df['parent_coa_cd'] == parent_cd]['coa_cd'].tolist()
    assert len(children) >= 2, f"{parent_cd} 应有 ≥2 个子节点, 实际 {len(children)}"

    # 给两个子节点分别赋值
    values = pd.Series({
        children[0]: 100.0,
        children[1]: 200.0
    })
    result = aggregate_bottom_up(values, roots)

    # 父节点 = 子节点之和
    expected = 300.0
    actual = result[parent_cd]
    assert abs(actual - expected) < 0.01, \
        f"{parent_cd} 应 = {expected}, 实际 = {actual}"

    print(f"✓ 多子节点聚合：{children[0]}+{children[1]} = {actual}（父节点 {parent_cd}）")


def test_aggregate_with_locked():
    """测试锁定覆盖逻辑"""
    data = load_all_params()
    roots = build_coa_tree(data.coa_info, data.coa_attribute)

    # 找一个锁定节点（如果有的话）
    locked_nodes = [n for n in flatten_tree(roots) if n.is_locked]
    if not locked_nodes:
        print("⚠ 当前数据库无锁定节点，跳过锁定测试")
        return

    target = locked_nodes[0]
    print(f"  测试锁定节点: {target.coa_cd}")

    # 给它的子节点设值 100
    values = pd.Series({c.coa_cd: 100.0 for c in target.children if c.leaf_flag == 1})
    if values.empty:
        # 如果锁定节点没有叶子节点，用它的直接子节点
        values = pd.Series({c.coa_cd: 100.0 for c in target.children})
    if values.empty:
        print("⚠ 锁定节点无子节点，跳过")
        return

    # 锁定覆盖值 = 9999
    overrides = pd.Series({target.coa_cd: 9999.0})

    result = aggregate_bottom_up(values, roots, locked_overrides=overrides)

    # 锁定节点应 = 9999（覆盖）
    assert result[target.coa_cd] == 9999.0, \
        f"锁定节点 {target.coa_cd} 应 = 9999, 实际 = {result[target.coa_cd]}"

    # 但其子节点的聚合值仍存在（不影响子节点）
    print(f"✓ 锁定覆盖：{target.coa_cd} 用 9999 覆盖聚合值")


def test_depth_map():
    """测试层级深度映射"""
    data = load_all_params()
    roots = build_coa_tree(data.coa_info)
    depth_map = coa_cd_to_depth_map(roots)

    # ROOT 应该是 0
    assert depth_map.get('ROOT') == 0, f"ROOT 深度: {depth_map.get('ROOT')}"

    # 一级账户（如 1_1）应该是 1
    assert depth_map.get('1_1') == 1, f"1_1 深度: {depth_map.get('1_1')}"

    print(f"✓ 层级深度: ROOT=0, 1_1=1")


if __name__ == '__main__':
    test_build_coa_tree()
    test_flatten_tree()
    test_aggregate_simple()
    test_aggregate_multiple_children()
    test_aggregate_with_locked()
    test_depth_map()
    print("\n所有测试通过！")