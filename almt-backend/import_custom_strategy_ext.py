"""
从 SQLite param_custom_stretagy 补充导入自定义策略

param_stretagy_line（773行）是计算引擎输出的"分摊结果"，中间段全 0 是正常的；
param_custom_stretagy（236行）是业务人员手工录入的真实策略，本表数据更完整。

合并策略：以 param_custom_stretagy 为准（同 coa_cd 覆盖）；
        没有的自定义策略的账户册保留 param_stretagy_line 数据。
"""
import sqlite3
import pymysql

SQLITE_PATH = 'C:/中电金信/产品资料/ALMT/ALMT/ALMT.db'
DB_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'almt', 'password': 'almt',
    'database': 'almt_db', 'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
}


def merge():
    sconn = sqlite3.connect(SQLITE_PATH)
    scur = sconn.cursor()

    # 1. param_custom_stretagy（手工录入的真实策略）
    scur.execute('SELECT * FROM param_custom_stretagy')
    custom_rows = scur.fetchall()
    custom_cols = [d[0] for d in scur.description]

    # 2. param_stretagy_line（计算引擎的分摊结果，773 行）
    scur.execute('SELECT * FROM param_stretagy_line')
    line_rows = scur.fetchall()
    line_cols = [d[0] for d in scur.description]

    sconn.close()

    # 合并：以 param_custom_stretagy 优先（同 coa_cd 覆盖）
    custom_map = {}
    for r in custom_rows:
        d = dict(zip(custom_cols, r))
        custom_map[d['coa_cd']] = d

    merged = []
    seen = set()
    # 先 line 表（更多账户册）
    for r in line_rows:
        d = dict(zip(line_cols, r))
        d_aligned = {k: d.get(k) for k in custom_cols}
        cd = d_aligned['coa_cd']
        line_name = d_aligned['coa_name']
        # 同 coa_cd 且同 coa_name：用 custom（更完整）
        if cd in custom_map and custom_map[cd]['coa_name'] == line_name:
            merged.append(custom_map[cd])
        else:
            merged.append(d_aligned)
        seen.add(cd)
    # 添加 line 没有但 custom 独有的
    for cd, d in custom_map.items():
        if cd not in seen:
            merged.append(d)

    print(f'param_custom_stretagy: {len(custom_rows)} 行')
    print(f'param_stretagy_line:   {len(line_rows)} 行')
    print(f'合并后: {len(merged)} 行')

    # 统计合并后非零分布
    nonzero = [0] * 24
    for d in merged:
        for i in range(24):
            v = d.get(f'stretagy_M{i+1}')
            if v and float(v) != 0:
                nonzero[i] += 1
    print()
    print('合并后各期非零行数:')
    for i, c in enumerate(nonzero):
        print(f'  M{i+1:2d}: {c:3d}')

    # 写 MySQL
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute('TRUNCATE TABLE almt_param_custom_strategy')
            print('\n✓ 清空 almt_param_custom_strategy')

            insert_sql = """
                INSERT INTO almt_param_custom_strategy
                (uuid, coa_cd, coa_name,
                 strategy_M1, strategy_M2, strategy_M3, strategy_M4, strategy_M5, strategy_M6,
                 strategy_M7, strategy_M8, strategy_M9, strategy_M10, strategy_M11, strategy_M12,
                 strategy_M13, strategy_M14, strategy_M15, strategy_M16, strategy_M17, strategy_M18,
                 strategy_M19, strategy_M20, strategy_M21, strategy_M22, strategy_M23, strategy_M24,
                 remark)
                VALUES (%s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s)
            """
            batch = []
            import uuid as uuidlib
            for d in merged:
                batch.append((
                    d.get('uuid') or str(uuidlib.uuid4()),
                    d['coa_cd'],
                    d['coa_name'],
                    *(float(d.get(f'stretagy_M{i+1}') or 0) for i in range(24)),
                    f"源: {'custom' if d['coa_cd'] in custom_map else 'line'} | {d.get('remark', '')}",
                ))
            cur.executemany(insert_sql, batch)
            print(f'✓ 写入 {len(batch)} 行')
            conn.commit()
    finally:
        conn.close()


if __name__ == '__main__':
    merge()