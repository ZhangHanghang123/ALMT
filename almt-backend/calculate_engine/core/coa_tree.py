"""
账户册树形模型

数据来源：almt_coa_info（含 ROOT 节点）+ almt_coa_attribute（含 is_locked 锁定标记）

关键算法：
  1. build_coa_tree() - 从扁平 DataFrame 构建树形结构
  2. aggregate_bottom_up() - 自底向上聚合（核心算法，所有 4 个引擎都会用到）
  3. override_locked() - 用锁定值覆盖聚合值

详见 MEASUREMENT_MANUAL.md 第 1.4 节
"""
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd


@dataclass
class CoaNode:
    """
    账户册节点（树形结构）

    字段：
        coa_cd       账户册编码（如 "1_1_1"）
        coa_name     账户册名称
        parent_cd    父节点编码（ROOT 节点的 parent_cd 为 None）
        leaf_flag    是否叶节点（1=叶, 0=非叶）
        is_locked    是否锁定（阶段 A 用）
        depth        层级深度（ROOT=0, 一级=1, ...）
        children     子节点列表
    """
    coa_cd: str
    coa_name: str
    parent_cd: Optional[str]
    leaf_flag: int
    is_locked: bool = False
    depth: int = 0
    children: list = field(default_factory=list)

    def walk(self, fn):
        """深度优先遍历，对每个节点执行 fn(node)"""
        fn(self)
        for child in self.children:
            child.walk(fn)


def build_coa_tree(
    df_coa_info: pd.DataFrame,
    df_coa_attribute: Optional[pd.DataFrame] = None
) -> list:
    """
    从 almt_coa_info + almt_coa_attribute 构建账户册树。

    返回：
        list[CoaNode]  - ROOT 节点列表（理论上只有一个 ROOT）

    叶节点判定：
        当前数据库 almt_coa_info.leaf_flag 全部为 '0'，没有真实标记。
        因此用"是否没有子节点"作为叶节点判定（构造树之后回填 leaf_flag）。

    示例：
        >>> roots = build_coa_tree(df_coa_info)
        >>> print(roots[0].coa_name)  # "资产负债账户册"
        >>> print(len(roots[0].children))  # 12  (1_1~1_5, 2_1~2_6, 3_1)
    """
    # 1. 建立 coa_cd → CoaNode 映射
    nodes: dict[str, CoaNode] = {}
    for _, row in df_coa_info.iterrows():
        # 处理空值（pandas 把 None 变成 NaN）
        parent_cd = row['parent_coa_cd'] if pd.notna(row['parent_coa_cd']) else None
        nodes[row['coa_cd']] = CoaNode(
            coa_cd=row['coa_cd'],
            coa_name=row['coa_name'],
            parent_cd=parent_cd,
            leaf_flag=int(row['leaf_flag']),
            depth=0
        )

    # 2. 合并锁定标记（如果提供）
    #    注意：当前数据库 almt_coa_attribute 没有 is_locked 字段
    #    如果未来加上了这个字段，需要在这里读取
    if df_coa_attribute is not None and 'is_locked' in df_coa_attribute.columns:
        locked_map = dict(zip(
            df_coa_attribute['coa_cd'],
            df_coa_attribute['is_locked'].fillna(0).astype(int)
        ))
        for cd, node in nodes.items():
            node.is_locked = bool(locked_map.get(cd, 0))
    # 否则所有节点默认 is_locked=False（业务计划增量按层级分摊）

    # 3. 构建父子关系
    roots: list[CoaNode] = []
    for cd, node in nodes.items():
        if node.parent_cd is None or node.parent_cd not in nodes:
            # ROOT 节点（parent_cd 为 None 或 父节点不在 nodes 中）
            roots.append(node)
        else:
            nodes[node.parent_cd].children.append(node)

    # 4. 计算 depth（自顶向下）
    def assign_depth(node: CoaNode, depth: int):
        node.depth = depth
        for child in node.children:
            assign_depth(child, depth + 1)

    for root in roots:
        assign_depth(root, 0 if root.coa_cd == 'ROOT' else 1)

    # 5. 回填 leaf_flag：当前数据库 leaf_flag 字段全为 0，用"是否有子节点"重新判定
    def reassign_leaf(node: CoaNode):
        if not node.children:
            node.leaf_flag = 1  # 没有子节点 = 叶节点
        else:
            node.leaf_flag = 0  # 有子节点 = 非叶节点
            for child in node.children:
                reassign_leaf(child)

    for root in roots:
        reassign_leaf(root)

    return roots


def flatten_tree(roots: list) -> list[CoaNode]:
    """
    把树展平成节点列表（DFS 顺序），便于遍历所有节点。

    返回：
        list[CoaNode]  - 全部节点（包含 ROOT）
    """
    result = []
    for root in roots:
        root.walk(lambda n: result.append(n))
    return result


def aggregate_bottom_up(
    values: pd.Series,
    roots: list,
    locked_overrides: Optional[pd.Series] = None
) -> pd.Series:
    """
    自底向上聚合 + 锁定覆盖。

    核心算法（阶段 A/B/C/D 都会用到）：
      1. 对每个节点：聚合值 = SUM(子节点的本期值)
      2. 如果节点被锁定：用 locked_overrides 中的值覆盖聚合值
      3. 锁定节点的子节点**仍然正常聚合**（锁定不影响子节点）

    Args:
        values: pd.Series, 索引是 coa_cd，值是每个节点的"原始值"（如 M1 增量）。
                对于没有数据的节点，值应为 0 或 NaN（会被当作 0 处理）。
        roots: list[CoaNode], build_coa_tree() 返回的根节点列表。
        locked_overrides: pd.Series, 索引是 coa_cd，值是锁定值。
                         如果 None 或某 coa_cd 不在序列中，则该节点不锁定。

    Returns:
        pd.Series, 索引是 coa_cd，值是聚合后的值。

    示例：
        >>> values = pd.Series({'1_1_1': 100, '1_1_2': 200, '1_1': 0})
        >>> roots = build_coa_tree(df)
        >>> result = aggregate_bottom_up(values, roots)
        >>> print(result['1_1'])  # 300 (= 100 + 200)
        >>> print(result['1_1_1'])  # 100
    """
    # 1. 展平树为有序列表（保证父节点在子节点之后处理）
    #    由于 CoaNode 是自顶向下构建的，需要先收集叶节点，再逐级向上
    flat = flatten_tree(roots)
    # 按 depth 降序（叶节点先聚合）
    flat_sorted = sorted(flat, key=lambda n: -n.depth)

    # 2. 准备输入值（缺失填 0）
    input_values = values.fillna(0)

    # 3. 自底向上聚合
    aggregated = input_values.copy()
    # 用 dict 缓存中间结果（key=coa_cd, value=聚合值）
    result = {}
    for node in flat_sorted:
        if node.leaf_flag == 1:
            # 叶节点：直接取输入值
            val = float(input_values.get(node.coa_cd, 0))
        else:
            # 非叶节点：聚合所有子节点
            val = 0.0
            for child in node.children:
                # 子节点的聚合值 = 它自己 + 它所有后代叶节点的输入值之和
                # 这里我们用累积的方式：先看 child 是否已经有聚合值
                val += result.get(child.coa_cd, float(input_values.get(child.coa_cd, 0)))
        # 检查是否锁定（如果有覆盖值且非 NaN）
        if locked_overrides is not None and node.coa_cd in locked_overrides.index:
            override = locked_overrides[node.coa_cd]
            if pd.notna(override) and bool(node.is_locked):
                val = float(override)
        result[node.coa_cd] = val

    return pd.Series(result)


def coa_cd_to_depth_map(roots: list) -> dict[str, int]:
    """
    生成 coa_cd → depth 的字典。

    用于阶段 A 锁定判断时筛选特定层级的节点。
    """
    flat = flatten_tree(roots)
    return {n.coa_cd: n.depth for n in flat}


if __name__ == '__main__':
    """快速冒烟测试"""
    from .loader import load_all_params

    data = load_all_params()
    roots = build_coa_tree(data.coa_info, data.coa_attribute)

    print(f"=== 账户册树 ===")
    print(f"根节点数: {len(roots)}")
    for r in roots:
        print(f"  {r.coa_cd:8s} | {r.coa_name} | depth={r.depth} | 子节点数={len(r.children)}")

    # 聚合测试
    flat = flatten_tree(roots)
    print(f"\n总节点数: {len(flat)}")

    # 模拟 M1 业务计划：只给 1_1_1 设值
    test_values = pd.Series({'1_1_1': 1000.0})
    result = aggregate_bottom_up(test_values, roots)
    print(f"\n=== 聚合测试（1_1_1=1000, 其他=0）===")
    print(f"  1_1_1: {result.get('1_1_1', 'N/A')}")
    print(f"  1_1: {result.get('1_1', 'N/A')}")  # 应等于 1000
    print(f"  ROOT: {result.get('ROOT', 'N/A')}")  # 应等于 1000