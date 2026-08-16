"""
ENGINE A 业务分摊（Business Plan Allocation）v2

算法变更（修复 bug）：
  原 v1：直接保留 plan_balance_i（不树形分摊） ❌
  现 v2：按"当前余额比例"自顶向下分摊父级计划值到子节点 ✓

原系统公式（Excel "业务计划-规模分摊"）：
  子节点 Q1 增量 = 父级计划值 × (子节点余额 / 父级所有子节点余额之和)
  父节点自身不再保留值（已被分摊）

参考：MEASUREMENT_MANUAL.md 第 2 章
"""
from calculate_engine.core.coa_tree import build_coa_tree, flatten_tree
from calculate_engine.core.loader import load_all_params
import pandas as pd


def _get_balance_map(df_current_position: pd.DataFrame) -> dict:
    """从存量数据构建 coa_lvl → balance 字典（单位：亿元）"""
    grouped = df_current_position.groupby('coa_lvl')['balance'].sum()
    return grouped.to_dict()


def _allocate_one_period(
    plan_values: dict,    # {coa_cd: plan_value}  原始计划输入
    balance_map: dict,    # {coa_cd: balance}
    nodes_flat: list      # 树形节点的扁平列表（CoaNode）
) -> dict:
    """
    单期分摊算法（核心递归）。

    规则：
      - 对每个非叶节点 N，如果 N 有 plan_value：
          把 plan_value 按 N 的所有子节点的余额比例分摊
      - 叶节点累加所有"收到的"分摊值

    Args:
        plan_values: 输入的原始计划值（顶级账户册的 plan_balance_i 等）
        balance_map: 每个账户册的当前余额
        nodes_flat:  CoaNode 扁平列表

    Returns:
        dict: {coa_cd: allocated_value} 每个账户册最终的计划增量
    """
    # 初始化所有账户册的分配值为 0
    allocated = {n.coa_cd: 0.0 for n in nodes_flat}

    # 自顶向下递归
    def walk(node, incoming_plan):
        """node: 当前节点，incoming_plan: 该节点收到的计划值"""
        if node.children:
            # 非叶节点：把 incoming_plan 按子节点余额比例分摊
            children_with_balance = []
            for c in node.children:
                bal = balance_map.get(c.coa_cd, 0)
                children_with_balance.append((c, bal))

            sum_bal = sum(b for _, b in children_with_balance)

            if sum_bal > 0:
                for c, bal in children_with_balance:
                    share = incoming_plan * bal / sum_bal
                    walk(c, share)
            else:
                # 所有子节点余额为 0，无法分摊，丢掉
                pass
        else:
            # 叶节点：累加分配值
            allocated[node.coa_cd] += incoming_plan

    # 从 ROOT 出发，ROOT 不分配自己（它是逻辑根）
    for root in nodes_flat:
        if root.coa_cd == 'ROOT':
            for c in root.children:
                # 顶级账户册的初始计划值
                initial = plan_values.get(c.coa_cd, 0)
                walk(c, initial)
        elif root.parent_cd is None:
            # 兜底：其他无父节点的根
            initial = plan_values.get(root.coa_cd, 0)
            walk(root, initial)

    return allocated


def allocate_business_plan(
    df_coa_info: pd.DataFrame,
    df_business_plan: pd.DataFrame,
    df_current_position: pd.DataFrame,
    df_coa_attribute: pd.DataFrame = None
) -> pd.DataFrame:
    """
    业务计划分摊主函数（v2：按余额比例树形分摊）。

    Args:
        df_coa_info:         账户册树形
        df_business_plan:    业务计划 24 期
        df_current_position: 当前存量（用于余额比例分摊）
        df_coa_attribute:    账户册属性（可选，目前未使用）

    Returns:
        pd.DataFrame: 索引 coa_cd，列：
            - bp_balance_1 ~ bp_balance_24: 24 期余额增量（亿元，已分摊到叶节点）
            - bp_average_1 ~ bp_average_24: 24 期日均增量（亿元，已分摊到叶节点）
    """
    # 1. 构建树
    roots = build_coa_tree(df_coa_info)
    nodes_flat = flatten_tree(roots)

    # 2. 余额字典
    balance_map = _get_balance_map(df_current_position)

    # 3. 业务计划按 coa_cd 索引（原始）
    bp_indexed = df_business_plan.set_index('coa_cd')

    # 4. 准备结果
    all_coa_cds = [n.coa_cd for n in nodes_flat]
    result = pd.DataFrame(index=all_coa_cds)
    result.index.name = 'coa_cd'

    # 5. 对每期做分摊
    for i in range(1, 25):
        bal_col = f'plan_balance{i}'
        avg_col = f'plan_average{i}'

        # 取原始输入（顶级账户册可能有值）
        plan_bal_input = {}
        plan_avg_input = {}
        if bal_col in bp_indexed.columns:
            for cd in all_coa_cds:
                v = bp_indexed.loc[cd, bal_col] if cd in bp_indexed.index else 0
                if pd.notna(v):
                    plan_bal_input[cd] = float(v)
        if avg_col in bp_indexed.columns:
            for cd in all_coa_cds:
                v = bp_indexed.loc[cd, avg_col] if cd in bp_indexed.index else 0
                if pd.notna(v):
                    plan_avg_input[cd] = float(v)

        # 分摊
        if plan_bal_input:
            allocated_bal = _allocate_one_period(plan_bal_input, balance_map, nodes_flat)
        else:
            allocated_bal = {cd: 0.0 for cd in all_coa_cds}
        if plan_avg_input:
            allocated_avg = _allocate_one_period(plan_avg_input, balance_map, nodes_flat)
        else:
            allocated_avg = {cd: 0.0 for cd in all_coa_cds}

        result[f'bp_balance_{i}'] = pd.Series(allocated_bal)
        result[f'bp_average_{i}'] = pd.Series(allocated_avg)

    return result


def get_m0_baseline(
    df_current_position: pd.DataFrame,
    df_coa_info: pd.DataFrame
) -> pd.DataFrame:
    """
    从存量数据构建 M0 基线（每账户册的当前余额/日均/利率）。
    """
    result = pd.DataFrame(index=df_coa_info['coa_cd'].tolist())
    result.index.name = 'coa_cd'

    # 按 coa_lvl 汇总存量
    pos = df_current_position.groupby('coa_lvl').agg(
        m0_balance=('balance', 'sum'),
        m0_average=('average_balance', 'sum'),
        m0_interest=('rate', 'sum')  # 月度利息金额
    )

    # 重新索引到所有账户册（存量只覆盖叶节点）
    result = result.join(pos, how='left').fillna(0)

    # 计算 m0_rate = (月度利息 × 12) / 平均余额（年化利率%）
    result['m0_rate'] = result.apply(
        lambda r: round((r['m0_interest'] * 12) / r['m0_average'] * 100, 4)
        if r['m0_average'] else 0,
        axis=1
    )
    result = result.drop(columns=['m0_interest'])

    return result


def get_bp_with_baseline(
    df_coa_info: pd.DataFrame,
    df_business_plan: pd.DataFrame,
    df_current_position: pd.DataFrame,
    df_coa_attribute: pd.DataFrame = None
) -> pd.DataFrame:
    """
    业务计划 + M0 基线合并版（25 期 M0~M24 完整序列）。
    """
    bp = allocate_business_plan(df_coa_info, df_business_plan, df_current_position, df_coa_attribute)
    m0 = get_m0_baseline(df_current_position, df_coa_info)
    merged = bp.join(m0, how='left').fillna(0)

    cum_balance = [merged['m0_balance']]
    cum_average = [merged['m0_average']]
    for i in range(1, 25):
        cum_balance.append(cum_balance[-1] + merged[f'bp_balance_{i}'])
        cum_average.append(cum_average[-1] + merged[f'bp_average_{i}'])

    for i in range(1, 25):
        merged[f'cum_balance_{i}'] = cum_balance[i]
        merged[f'cum_average_{i}'] = cum_average[i]

    return merged


if __name__ == '__main__':
    """冒烟测试"""
    data = load_all_params()

    result = allocate_business_plan(
        data.coa_info,
        data.business_plan,
        data.current_position,
        data.coa_attribute
    )

    print(f"=== ENGINE A v2 业务分摊结果 ===")
    print(f"账户册数: {len(result)}")
    print(f"列数: {len(result.columns)} (48 = 2×24)")

    print(f"\n=== 关键节点 M1 数据（已按余额比例分摊到叶节点） ===")
    for cd in ['1_1', '1_1_1', '1_1_2', '1_1_3', '1_2', '2_1', '2_1_1', '2_1_3']:
        if cd in result.index:
            row = result.loc[cd]
            b = row['bp_balance_1']
            a = row['bp_average_1']
            print(f"  {cd}: M1余额={b:>15.4f}  M1日均={a:>15.4f}")