"""
迁移脚本：为 almt_calculate_task 加 calc_version 字段

calc_version 格式：YYYYMMDD-XXXX
  - YYYYMMDD: 计算数据日期
  - XXXX: 4 位序列码（同一天内递增，从 0001 开始）

用于：
  - 计量结果版本管理
  - "创建空版本"：无需执行计算，只生成版本号占位
  - "清除历史结果"：按 calc_version 删除整批结果

执行：
    python migrate_add_calc_version.py
"""
import pymysql


def main():
    conn = pymysql.connect(
        host='localhost', user='almt', password='almt',
        database='almt_db', port=3306
    )
    cursor = conn.cursor()

    # 1. 加 calc_version 字段
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = 'almt_db'
              AND TABLE_NAME = 'almt_calculate_task'
              AND COLUMN_NAME = 'calc_version'
        """)
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                ALTER TABLE almt_calculate_task
                ADD COLUMN calc_version VARCHAR(20) DEFAULT NULL AFTER task_id,
                ADD INDEX idx_calc_version (calc_version)
            """)
            print('[OK] almt_calculate_task 加 calc_version 字段')
        else:
            print('[INFO] calc_version 字段已存在')
    except Exception as e:
        print(f'[FAIL] 加 calc_version: {e}')

    # 2. 给结果表加索引
    for tbl in ['almt_result_index', 'almt_result_plan']:
        try:
            cursor.execute(f"SHOW INDEX FROM {tbl} WHERE Key_name = %s", (f'idx_{tbl}_task',))
            if not cursor.fetchone():
                cursor.execute(f"CREATE INDEX idx_{tbl}_task ON {tbl}(task_id)")
                print(f'[OK] {tbl} 加 task_id 索引')
            else:
                print(f'[INFO] {tbl} task_id 索引已存在')
        except Exception as e:
            print(f'[FAIL] {tbl}: {e}')

    conn.commit()
    cursor.close()
    conn.close()
    print('\n迁移完成！')


if __name__ == '__main__':
    main()