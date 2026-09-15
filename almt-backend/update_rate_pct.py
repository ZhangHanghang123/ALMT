#!/usr/bin/env python3
"""
从 Excel '接收表-存量数据情况表' 的"存量平均利率"列（列 4）批量更新到
almt_current_position.rate_pct 字段。

用法：
    python3 update_rate_pct.py [xlsx_path]

默认 xlsx 路径：C:/中电金信/产品资料/ALMT/ALMT/ALMT.DATA.xlsx
"""
import sys
import os
import pymysql
import openpyxl

DB_CFG = dict(
    host='127.0.0.1',
    port=3306,
    user='almd',
    password='Almd@2026',
    database='almt_db',
    charset='utf8mb4',
)

DEFAULT_XLSX = 'C:/中电金信/产品资料/ALMT/ALMT/ALMT.DATA.xlsx'


def main():
    xlsx_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_XLSX
    print(f'XLSX: {xlsx_path}')

    # 1. 读取 Excel 的"存量平均利率"列（列 4）和层级编码（列 0）
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb['接收表-存量数据情况表']

    updates = {}  # coa_lvl -> rate_pct
    skipped = 0
    for r in ws.iter_rows(min_row=3, values_only=True):
        coa_lvl = r[0]
        rate_pct = r[4]
        if not coa_lvl:
            continue
        if rate_pct is None:
            skipped += 1
            continue
        # 转 float，截断到 6 位小数
        try:
            updates[str(coa_lvl).strip()] = round(float(rate_pct), 6)
        except (ValueError, TypeError):
            skipped += 1

    print(f'从 Excel 读取到 {len(updates)} 条利率记录，跳过 {skipped} 条空值')

    # 2. 写入数据库
    conn = pymysql.connect(**DB_CFG)
    cur = conn.cursor()
    updated = 0
    not_matched = []
    try:
        for coa_lvl, rate_pct in updates.items():
            n = cur.execute(
                'UPDATE almt_current_position SET rate_pct=%s WHERE coa_lvl=%s',
                (rate_pct, coa_lvl)
            )
            if n == 0:
                not_matched.append(coa_lvl)
            else:
                updated += n
        conn.commit()
    finally:
        cur.close()
        conn.close()

    print(f'已更新 {updated} 行；未匹配到数据库的 coa_lvl：{len(not_matched)} 个')
    if not_matched:
        print('未匹配示例（前 10 个）：', not_matched[:10])

    # 3. 抽样验证
    conn = pymysql.connect(**DB_CFG)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT coa_lvl, coa_name, rate, rate_pct
                FROM almt_current_position
                WHERE rate_pct IS NOT NULL
                ORDER BY coa_lvl LIMIT 10
            """)
            for row in cur.fetchall():
                print(f'  {row[0]:<15} {row[1]:<35} rate(月息)={row[2]}  rate_pct={row[3]}')
    finally:
        conn.close()


if __name__ == '__main__':
    main()
