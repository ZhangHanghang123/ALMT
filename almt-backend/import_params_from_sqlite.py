"""
从 SQLite 演示库导入完整参数数据（业务计划、定价策略、风险权重）

数据源：ALMT/ALMT.db（VBA 原系统导出）
目标库：MySQL almt_db（经营计划模拟系统）

数据补充：
  - almt_param_business_plan: SQLite 773 行全量覆盖（MySQL 当前只有父级有值）
  - almt_param_custom_strategy: SQLite 773 行全量覆盖（MySQL 当前只有 15 行）
  - almt_param_risk_weight: SQLite 639 行的 weight 值同步到 24 期

执行：
  python import_params_from_sqlite.py            # 预览
  python import_params_from_sqlite.py --execute  # 实际执行
"""
import sqlite3
import pymysql
import argparse
from datetime import datetime


SQLITE_PATH = 'C:/中电金信/产品资料/ALMT/ALMT/ALMT.db'

DB_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'almt', 'password': 'almt',
    'database': 'almt_db', 'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
}


def _fetch_all(sql, params=()):
    conn = sqlite3.connect(SQLITE_PATH)
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        conn.close()


def preview():
    """预览要导入的数据"""
    print('=== 1. 业务计划 param_business_planning ===')
    rows = _fetch_all('SELECT * FROM param_business_planning LIMIT 3')
    print(f'  总行数: 773（含 24 期余额 + 24 期日均）')
    print(f'  前 3 条 coa_cd: {[r["coa_cd"] for r in rows]}')
    print(f'  1_1 plan_balance1~6: {rows[0]["plan_balance1"]} ~ {rows[0]["plan_balance6"]}')

    print('\n=== 2. 定价策略 param_stretagy_line ===')
    rows = _fetch_all('SELECT * FROM param_stretagy_line LIMIT 3')
    print(f'  总行数: 773')
    print(f'  前 3 条 coa_cd: {[r["coa_cd"] for r in rows]}')
    print(f'  1_1 strategy_M1~3: {rows[0]["stretagy_M1"]} ~ {rows[0]["stretagy_M3"]}')

    print('\n=== 3. 风险权重 param_risk_weight ===')
    rows = _fetch_all('SELECT * FROM param_risk_weight')
    print(f'  总行数: {len(rows)}')
    print(f'  weight 字段分布（取前 10）:')
    for r in rows[:10]:
        print(f'    {r["coa_cd"]}: weight = {r["weight"]}')


def import_business_plan(cur):
    """全量覆盖导入业务计划"""
    rows = _fetch_all('SELECT * FROM param_business_planning ORDER BY coa_lvl, coa_cd')
    print(f'\n[1/3] 业务计划：SQLite 有 {len(rows)} 行')

    # 清空原表
    cur.execute('TRUNCATE TABLE almt_param_business_plan')
    print(f'  ✓ 清空 almt_param_business_plan')

    # 准备 INSERT（id 不传，让 MySQL 自增）
    insert_sql = """
        INSERT INTO almt_param_business_plan
        (uuid, coa_lvl, coa_cd, coa_name,
         plan_balance1, plan_balance2, plan_balance3, plan_balance4, plan_balance5, plan_balance6,
         plan_balance7, plan_balance8, plan_balance9, plan_balance10, plan_balance11, plan_balance12,
         plan_balance13, plan_balance14, plan_balance15, plan_balance16, plan_balance17, plan_balance18,
         plan_balance19, plan_balance20, plan_balance21, plan_balance22, plan_balance23, plan_balance24,
         plan_average1, plan_average2, plan_average3, plan_average4, plan_average5, plan_average6,
         plan_average7, plan_average8, plan_average9, plan_average10, plan_average11, plan_average12,
         plan_average13, plan_average14, plan_average15, plan_average16, plan_average17, plan_average18,
         plan_average19, plan_average20, plan_average21, plan_average22, plan_average23, plan_average24)
        VALUES (%s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    batch = []
    for r in rows:
        batch.append((
            r['uuid'], str(r.get('coa_lvl', '')), r['coa_cd'], r['coa_name'],
            *(float(r[f'plan_balance{i}'] or 0) for i in range(1, 25)),
            *(float(r[f'plan_average{i}'] or 0) for i in range(1, 25)),
        ))
    cur.executemany(insert_sql, batch)
    print(f'  ✓ 导入 {len(batch)} 行')


def import_custom_strategy(cur):
    """全量覆盖导入定价策略"""
    rows = _fetch_all('SELECT * FROM param_stretagy_line ORDER BY coa_lvl, coa_cd')
    print(f'\n[2/3] 定价策略：SQLite 有 {len(rows)} 行')

    cur.execute('TRUNCATE TABLE almt_param_custom_strategy')
    print(f'  ✓ 清空 almt_param_custom_strategy')

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
    for r in rows:
        batch.append((
            r['uuid'], r['coa_cd'], r['coa_name'],
            *(float(r[f'stretagy_M{i}'] or 0) for i in range(1, 25)),
            f"从源系统迁移（{r['coa_lvl']}={r['coa_name']}）",
        ))
    cur.executemany(insert_sql, batch)
    print(f'  ✓ 导入 {len(batch)} 行')


def import_risk_weight(cur):
    """同步风险权重：SQLite 的 weight → MySQL 24 期统一值"""
    rows = _fetch_all('SELECT * FROM param_risk_weight')
    print(f'\n[3/3] 风险权重：SQLite 有 {len(rows)} 行')

    def parse_weight(w):
        """解析 weight（可能是 "10", "10.00%", "10.50%"）"""
        if w is None:
            return 0.0
        s = str(w).rstrip('%').strip()
        try:
            return float(s)
        except Exception:
            return 0.0

    updated = 0
    for r in rows:
        w = parse_weight(r['weight'])
        # 用 weight 值覆盖所有 24 期 risk_weight_X（保持期内一致）
        sql = """UPDATE almt_param_risk_weight SET weight = %s,
                  risk_weight_1 = %s, risk_weight_2 = %s, risk_weight_3 = %s, risk_weight_4 = %s,
                  risk_weight_5 = %s, risk_weight_6 = %s, risk_weight_7 = %s, risk_weight_8 = %s,
                  risk_weight_9 = %s, risk_weight_10 = %s, risk_weight_11 = %s, risk_weight_12 = %s,
                  risk_weight_13 = %s, risk_weight_14 = %s, risk_weight_15 = %s, risk_weight_16 = %s,
                  risk_weight_17 = %s, risk_weight_18 = %s, risk_weight_19 = %s, risk_weight_20 = %s,
                  risk_weight_21 = %s, risk_weight_22 = %s, risk_weight_23 = %s, risk_weight_24 = %s
                  WHERE coa_cd = %s"""
        params = (w, w, w, w, w, w, w, w, w, w, w, w, w, w, w, w, w, w, w, w, w, w, w, w, w, r['coa_cd'])
        cur.execute(sql, params)
        if cur.rowcount > 0:
            updated += 1

    # 处理 SQLite 有但 MySQL 没有的 coa_cd（如有）
    cur.execute('SELECT coa_cd FROM almt_param_risk_weight')
    existing = {r['coa_cd'] for r in cur.fetchall()}
    new_count = 0
    for r in rows:
        if r['coa_cd'] not in existing:
            w = parse_weight(r['weight'])
            cur.execute("""
                INSERT INTO almt_param_risk_weight
                (uuid, coa_cd, coa_name, weight,
                 risk_weight_1, risk_weight_2, risk_weight_3, risk_weight_4,
                 risk_weight_5, risk_weight_6, risk_weight_7, risk_weight_8,
                 risk_weight_9, risk_weight_10, risk_weight_11, risk_weight_12,
                 risk_weight_13, risk_weight_14, risk_weight_15, risk_weight_16,
                 risk_weight_17, risk_weight_18, risk_weight_19, risk_weight_20,
                 risk_weight_21, risk_weight_22, risk_weight_23, risk_weight_24)
                VALUES (UUID(), %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s)
            """, (r['coa_cd'], r['coa_name'], w, *([w]*24)))
            new_count += 1

    print(f'  ✓ 更新 {updated} 行（同步 weight 到 24 期）')
    print(f'  ✓ 新增 {new_count} 行（SQLite 独有）')


def execute():
    """实际执行"""
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            import_business_plan(cur)
            import_custom_strategy(cur)
            import_risk_weight(cur)
            conn.commit()
            print('\n=== 已提交 ===')

            # 验证
            cur.execute('SELECT COUNT(*) AS c FROM almt_param_business_plan')
            print(f'  almt_param_business_plan: {cur.fetchone()["c"]} 行')
            cur.execute('SELECT COUNT(*) AS c FROM almt_param_custom_strategy')
            print(f'  almt_param_custom_strategy: {cur.fetchone()["c"]} 行')
            cur.execute('SELECT COUNT(*) AS c FROM almt_param_risk_weight')
            print(f'  almt_param_risk_weight: {cur.fetchone()["c"]} 行')
    finally:
        conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true', help='实际执行导入')
    args = parser.parse_args()

    print('=' * 60)
    print(f'从 SQLite 导入参数数据 → MySQL')
    print(f'时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 60)

    if args.execute:
        execute()
    else:
        print('预览模式（不修改数据库，加 --execute 实际执行）：\n')
        preview()
        print('\n提示: 加 --execute 执行导入')