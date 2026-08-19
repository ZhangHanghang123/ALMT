#!/usr/bin/env python3
"""
ALMT 服务器端数据导入脚本（Python 批量 INSERT 版本）
读取 tmp_dump/ 目录中的 TSV + CREATE TABLE SQL，在服务器 MySQL 上重建表并导入数据
不依赖 MySQL local_infile，使用 pymysql executemany 批量插入

用法: python3 import_server.py
"""
import os
import sys
import glob
import csv
import pymysql
from decimal import Decimal
from datetime import datetime, date

DB_CFG = dict(
    host='127.0.0.1',
    port=3306,
    user='almd',
    password='Almd@2026',
    database='almt_db',
    charset='utf8mb4',
)

DUMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tmp_dump')
BATCH_SIZE = 1000


def parse_value(val, col_type):
    """将 TSV 字符串值转换为 Python 值"""
    if val == '\\N' or val == 'NULL' or val == '':
        return None

    col_lower = col_type.lower()

    # 整数类型
    if any(t in col_lower for t in ['int', 'bigint', 'tinyint', 'smallint', 'mediumint']):
        try:
            return int(val)
        except ValueError:
            return None

    # 小数类型
    if any(t in col_lower for t in ['decimal', 'float', 'double']):
        try:
            return float(val)
        except ValueError:
            return None

    # 日期时间类型
    if 'datetime' in col_lower or 'timestamp' in col_lower:
        if val == '0000-00-00 00:00:00':
            return None
        return val  # MySQL 接受字符串格式的 datetime

    if 'date' in col_lower:
        if val == '0000-00-00':
            return None
        return val

    # 其他类型（varchar, text 等）直接返回字符串
    return val


def main():
    if not os.path.isdir(DUMP_DIR):
        print(f"ERROR: dump directory not found: {DUMP_DIR}")
        sys.exit(1)

    # 收集所有表名
    tsv_files = sorted(glob.glob(os.path.join(DUMP_DIR, '*.tsv')))
    tables = []
    for tsv in tsv_files:
        basename = os.path.basename(tsv)
        table_name = basename[:-4]  # remove .tsv
        create_sql_file = os.path.join(DUMP_DIR, f'{table_name}_create.sql')
        if os.path.isfile(create_sql_file):
            tables.append((table_name, tsv, create_sql_file))
        else:
            print(f"  WARNING: no _create.sql for {table_name}, skipping")

    print(f"=== Found {len(tables)} tables to import ===")

    conn = pymysql.connect(**DB_CFG)
    cur = conn.cursor()

    # 关闭外键检查
    cur.execute('SET FOREIGN_KEY_CHECKS=0')
    cur.execute('SET UNIQUE_CHECKS=0')
    cur.execute('SET autocommit=0')

    total_rows = 0
    for table_name, tsv_path, create_sql_file in tables:
        print(f"\n--- {table_name} ---")

        # 1. 读取并执行 CREATE TABLE
        with open(create_sql_file, 'r', encoding='utf-8') as f:
            create_sql = f.read().strip()
        if create_sql.endswith(';'):
            create_sql = create_sql[:-1]

        cur.execute(f"DROP TABLE IF EXISTS `{table_name}`")
        cur.execute(create_sql)
        conn.commit()
        print(f"  table structure created")

        # 2. 获取列名和类型
        cur.execute(f"SHOW COLUMNS FROM `{table_name}`")
        col_info = [(row[0], row[1]) for row in cur.fetchall()]
        columns = [c[0] for c in col_info]
        col_types = [c[1] for c in col_info]
        col_list = ', '.join(f'`{c}`' for c in columns)
        placeholders = ', '.join(['%s'] * len(columns))
        insert_sql = f"INSERT INTO `{table_name}` ({col_list}) VALUES ({placeholders})"

        # 3. 读取 TSV 并批量插入
        row_count = 0
        batch = []

        with open(tsv_path, 'r', encoding='utf-8', newline='') as f:
            reader = csv.reader(f, delimiter='\t')
            header = next(reader)  # skip header row

            for line in reader:
                if not line:
                    continue

                # 确保列数匹配
                if len(line) != len(columns):
                    # 补齐或截断
                    if len(line) < len(columns):
                        line = line + [None] * (len(columns) - len(line))
                    else:
                        line = line[:len(columns)]

                # 转换值
                row = []
                for i, val in enumerate(line):
                    row.append(parse_value(val, col_types[i]))

                batch.append(tuple(row))

                if len(batch) >= BATCH_SIZE:
                    cur.executemany(insert_sql, batch)
                    conn.commit()
                    row_count += len(batch)
                    batch = []

            # 插入剩余
            if batch:
                cur.executemany(insert_sql, batch)
                conn.commit()
                row_count += len(batch)

        total_rows += row_count
        print(f"  imported {row_count} rows")

    # 恢复检查
    cur.execute('SET FOREIGN_KEY_CHECKS=1')
    cur.execute('SET UNIQUE_CHECKS=1')
    conn.commit()

    # 最终验证
    print(f"\n=== Import complete: {len(tables)} tables, {total_rows} total rows ===")
    print("\n=== Verification ===")
    cur.execute("SHOW TABLES")
    all_tables = [r[0] for r in cur.fetchall()]
    print(f"Total tables in almt_db: {len(all_tables)}")
    for tbl in sorted(all_tables):
        cur.execute(f"SELECT COUNT(*) FROM `{tbl}`")
        cnt = cur.fetchone()[0]
        print(f"  {tbl}: {cnt} rows")

    cur.close()
    conn.close()


if __name__ == '__main__':
    main()
