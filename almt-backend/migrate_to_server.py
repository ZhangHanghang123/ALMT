"""
ALMT 数据迁移脚本：本地 MySQL → 服务器 MySQL
导出本地 21 张表的完整结构 + 数据 → 在服务器上重建

用法：
  python migrate_to_server.py --remote-only   # 默认（只迁移到服务器）
  python migrate_to_server.py --local  3306 almt almt almt_db   # 自定义本地
  python migrate_to_server.py --remote 127.0.0.1 almd Almd@2026 almt_db  # 自定义服务器
"""
import argparse
import sys
from urllib.parse import quote

import pymysql


LOCAL_CFG = dict(host='localhost', port=3306, user='almt', password='almt', database='almt_db', charset='utf8mb4')
REMOTE_CFG = dict(host='127.0.0.1', port=3306, user='almd', password='Almd@2026', database='almt_db', charset='utf8mb4')


def _map_type(decl: str) -> str:
    """MySQL → MySQL 类型映射（保持一致即可）"""
    return decl


def _fetch_tables(cur):
    cur.execute('SHOW TABLES')
    return [r[0] for r in cur.fetchall()]


def _fetch_create_sql(cur, table):
    cur.execute(f"SHOW CREATE TABLE `{table}`")
    return cur.fetchone()[1]


def _fetch_count(cur, table):
    cur.execute(f"SELECT COUNT(*) FROM `{table}`")
    return cur.fetchone()[0]


def _fetch_rows(cur, table, batch=500):
    cur.execute(f"SELECT * FROM `{table}`")
    cols = [d[0] for d in cur.description]
    while True:
        rows = cur.fetchmany(batch)
        if not rows:
            break
        yield cols, rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--local-host', default=LOCAL_CFG['host'])
    parser.add_argument('--local-port', type=int, default=LOCAL_CFG['port'])
    parser.add_argument('--local-user', default=LOCAL_CFG['user'])
    parser.add_argument('--local-pass', default=LOCAL_CFG['password'])
    parser.add_argument('--local-db', default=LOCAL_CFG['database'])
    parser.add_argument('--remote-host', default=REMOTE_CFG['host'])
    parser.add_argument('--remote-port', type=int, default=REMOTE_CFG['port'])
    parser.add_argument('--remote-user', default=REMOTE_CFG['user'])
    parser.add_argument('--remote-pass', default=REMOTE_CFG['password'])
    parser.add_argument('--remote-db', default=REMOTE_CFG['database'])
    parser.add_argument('--dry-run', action='store_true', help='只显示不执行')
    args = parser.parse_args()

    local_cfg = dict(host=args.local_host, port=args.local_port, user=args.local_user,
                     password=args.local_pass, database=args.local_db, charset='utf8mb4')
    remote_cfg = dict(host=args.remote_host, port=args.remote_port, user=args.remote_user,
                      password=args.remote_pass, database=args.remote_db, charset='utf8mb4')

    print(f"=== 连接本地 {local_cfg['host']}:{local_cfg['port']} ===")
    local = pymysql.connect(**local_cfg)
    lc = local.cursor()
    print(f"=== 连接服务器 {remote_cfg['host']}:{remote_cfg['port']} ===")
    remote = pymysql.connect(**remote_cfg)
    rc = remote.cursor()

    # 关闭外键检查，加快迁移
    rc.execute('SET FOREIGN_KEY_CHECKS=0')

    tables = _fetch_tables(lc)
    print(f"=== 本地表数: {len(tables)} ===")

    for tbl in tables:
        # 跳过 sys_user（已在服务器创建 admin）
        if tbl == 'sys_user':
            print(f"  ⏭ 跳过 sys_user（保留服务器现有 admin）")
            continue

        count = _fetch_count(lc, tbl)
        print(f"  [{tbl}] {count} 行")

        if args.dry_run:
            continue

        # 1. 获取建表 SQL
        create_sql = _fetch_create_sql(lc, tbl)

        # 2. 在服务器上 DROP + CREATE
        rc.execute(f"DROP TABLE IF EXISTS `{tbl}`")
        rc.execute(create_sql)
        remote.commit()
        print(f"    → 重建表结构完成")

        # 3. 复制数据
        if count > 0:
            for cols, rows in _fetch_rows(lc, tbl):
                col_list = ', '.join(f'`{c}`' for c in cols)
                placeholders = ', '.join(['%s'] * len(cols))
                insert_sql = f"INSERT INTO `{tbl}` ({col_list}) VALUES ({placeholders})"
                # 把没法序列化的字段（datetime, Decimal, bytes）转为原生
                rows_clean = []
                for row in rows:
                    row = list(row)
                    for i, v in enumerate(row):
                        if hasattr(v, 'isoformat'):
                            row[i] = v.strftime('%Y-%m-%d %H:%M:%S')
                        elif hasattr(v, 'as_tuple'):  # Decimal
                            row[i] = float(v)
                        elif isinstance(v, bytes):
                            row[i] = v.decode('utf-8', errors='ignore')
                    rows_clean.append(tuple(row))
                rc.executemany(insert_sql, rows_clean)
                remote.commit()
            print(f"    → 复制 {count} 行数据")

    rc.execute('SET FOREIGN_KEY_CHECKS=1')
    local.close()
    remote.close()
    print("=== 迁移完成 ===")


if __name__ == '__main__':
    main()
