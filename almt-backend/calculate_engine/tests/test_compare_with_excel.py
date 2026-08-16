"""
对拍测试：Python 重写引擎 vs 原系统 Excel data_only 结果

对拍范围（按复杂度递增）：
  1. 业务计划-规模分摊.列5（期末余额）  vs  ENGINE A m0_balance
  2. 业务计划-规模分摊.列8（Q1增量规模）  vs  ENGINE A（需要按比例分摊修正）
  3. 动态现金流.列5~28（M1~M24）         vs  ENGINE C principal_1~24
"""
import openpyxl
import pandas as pd
import numpy as np
from calculate_engine.core.loader import load_all_params
from calculate_engine.engines import (
    get_m0_baseline,
    get_bp_with_baseline
)
from calculate_engine.engines.engine_c_cashflow import run_engine_c


def load_excel_data(xlsm_path, sheet_name, key_col=2, skip_top_rows=2):
    """从原 xlsm 中加载一个 sheet 的 data_only 结果"""
    wb = openpyxl.load_workbook(xlsm_path, data_only=True)
    ws = wb[sheet_name]
    rows = []
    for row_idx, row in enumerate(ws.iter_rows(values_only=True), 1):
        if row_idx <= skip_top_rows:
            continue
        rows.append(row)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    if key_col > len(df.columns):
        return pd.DataFrame()
    df = df.set_index(df.columns[key_col - 1])
    df.index.name = 'key'
    return df


def to_float(v):
    try:
        return float(v) if pd.notna(v) else None
    except (ValueError, TypeError):
        return None


def compare_series(py_series, xl_df, py_col_name, xl_col_idx, key_filter=None, tolerance=0.01):
    """对比两个序列，返回对拍结果"""
    common = py_series.index.intersection(xl_df.index)
    if key_filter:
        common = common.intersection(key_filter)

    match = 0
    mismatch = 0
    missing = 0
    max_diff = 0
    examples = []

    for cd in common:
        py_v = to_float(py_series.get(cd, None)) or 0
        xl_v = to_float(xl_df.iloc[xl_df.index.get_loc(cd), xl_col_idx - 1]) if cd in xl_df.index else None

        if py_v == 0 and xl_v in (None, 0):
            match += 1
            continue
        if py_v == 0 or xl_v is None:
            missing += 1
            continue

        diff = abs(py_v - xl_v)
        max_diff = max(max_diff, diff)
        if diff <= tolerance:
            match += 1
        else:
            mismatch += 1
            if len(examples) < 10:
                examples.append(f'    {cd}: py={py_v:.4f}, xl={xl_v:.4f}, diff={diff:.4f}')

    total = match + mismatch + missing
    return {
        'total': total,
        'match': match,
        'mismatch': mismatch,
        'missing': missing,
        'match_rate': match / total if total else 0,
        'max_diff': max_diff,
        'examples': examples
    }


def print_result(name, result):
    print(f'\n{"=" * 70}')
    print(f'【{name}】')
    print(f'{"=" * 70}')
    print(f'  对比 cell 总数: {result["total"]}')
    print(f'  ✓ 一致: {result["match"]} ({result["match_rate"] * 100:.2f}%)')
    print(f'  ✗ 不一致: {result["mismatch"]}')
    print(f'  ? 缺失: {result["missing"]}')
    print(f'  最大差值: {result["max_diff"]:.6f} 元')
    if result['examples']:
        print(f'  不一致示例:')
        for e in result['examples']:
            print(e)


# ============================================================
# 对拍 1：期末余额
# ============================================================

def test_compare_m0_balance():
    print('\n' + '=' * 70)
    print('【对拍 1】ENGINE A m0_balance  vs  Excel 业务计划-规模分摊 列 5（期末余额）')
    print('=' * 70)

    data = load_all_params()
    py_m0 = get_m0_baseline(data.current_position, data.coa_info)

    df_xl = load_excel_data(
        xlsm_path='C:/tmp/engine.xlsm',
        sheet_name='业务计划-规模分摊',
        key_col=3,           # C 列（层级编码）
        skip_top_rows=2,
    )

    print(f'  Python 账户册数: {len(py_m0)}')
    print(f'  Excel 账户册数: {len(df_xl)}')

    result = compare_series(py_m0['m0_balance'], df_xl, 'm0_balance', xl_col_idx=5)
    print_result('M0 余额对拍', result)


# ============================================================
# 对拍 2：业务计划分摊 Q1 增量规模
# ============================================================

def test_compare_q1_balance_alloc():
    """对拍：业务计划-规模分摊 列 8（Q1增量规模）vs Python 引擎 A"""
    print('\n' + '=' * 70)
    print('【对拍 2】ENGINE A bp_balance_1  vs  Excel 业务计划-规模分摊 列 8（Q1增量规模）')
    print('=' * 70)

    data = load_all_params()
    bp_full = get_bp_with_baseline(
        data.coa_info, data.business_plan, data.current_position, data.coa_attribute
    )

    df_xl = load_excel_data(
        xlsm_path='C:/tmp/engine.xlsm',
        sheet_name='业务计划-规模分摊',
        key_col=3,
        skip_top_rows=2,
    )

    print(f'  Python 账户册数: {len(bp_full)}')
    print(f'  Excel 账户册数: {len(df_xl)}')

    result = compare_series(bp_full['bp_balance_1'], df_xl, 'bp_balance_1', xl_col_idx=8)
    print_result('Q1 增量规模对拍', result)


# ============================================================
# 对拍 3：动态现金流 M1~M24 本金 vs ENGINE C
# ============================================================

def test_compare_cashflow():
    print('\n' + '=' * 70)
    print('【对拍 3】ENGINE C principal_M  vs  Excel 动态现金流 M1~M24')
    print('=' * 70)

    data = load_all_params()
    c_result = run_engine_c(
        df_coa_info=data.coa_info,
        df_coa_attribute=data.coa_attribute,
        df_business_plan=data.business_plan,
        df_current_position=data.current_position,
        df_rate_scenario=data.rate_scenario,
        df_custom_strategy=data.custom_strategy
    )

    df_xl = load_excel_data(
        xlsm_path='C:/tmp/engine.xlsm',
        sheet_name='动态现金流',
        key_col=1,
        skip_top_rows=2,
    )

    print(f'  Python 账户册数: {len(c_result)}')
    print(f'  Excel 账户册数: {len(df_xl)}')

    sample_months = [1, 3, 6, 12, 24]
    total_match = 0
    total_diff = 0
    total_missing = 0
    max_diff = 0
    examples = []

    for month in sample_months:
        py_col = f'principal_{month}'
        xl_col_idx = month + 4  # Excel 列 5 起是 M1
        result = compare_series(c_result[py_col], df_xl, py_col, xl_col_idx=xl_col_idx)
        total_match += result['match']
        total_diff += result['mismatch']
        total_missing += result['missing']
        max_diff = max(max_diff, result['max_diff'])
        print(f'  M{month:>2}: ✓{result["match"]} ✗{result["mismatch"]} ?{result["missing"]} max_diff={result["max_diff"]:.4f}')
        for e in result['examples'][:3]:
            print(f'      {e}')

    total = total_match + total_diff + total_missing
    print(f'\n  采样点合计: ✓ {total_match}/{total} = {total_match / total * 100:.2f}%')
    print(f'  最大差值: {max_diff:.6f} 元')


# ============================================================
# 主入口
# ============================================================

if __name__ == '__main__':
    test_compare_m0_balance()
    print()
    test_compare_q1_balance_alloc()
    print()
    test_compare_cashflow()
    print()
    print('🎉 对拍完成！')