"""
迁移脚本：新增 almt_param_cashflow_schedule 表

对应 ENGINE C 完全对标 Excel "标准化剩余本金表"。

执行：
    python migrate_add_cashflow_schedule.py
"""
import pymysql


def main():
    conn = pymysql.connect(
        host='localhost', user='almt', password='almt',
        database='almt_db', port=3306
    )
    cursor = conn.cursor()

    sql = """
    CREATE TABLE IF NOT EXISTS almt_param_cashflow_schedule (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        uuid VARCHAR(36) NOT NULL UNIQUE,
        coa_cd VARCHAR(50) NOT NULL,
        term VARCHAR(20) NOT NULL,
        period TINYINT NOT NULL COMMENT '期数 0-24，0=M0 基线',
        principal_ratio DECIMAL(10,6) COMMENT '本期本金占比',
        is_x_marker TINYINT DEFAULT 0 COMMENT 'Excel x 标记位',
        remark VARCHAR(200) COMMENT '备注',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uk_coa_term_period (coa_cd, term, period),
        INDEX idx_coa_cd (coa_cd),
        INDEX idx_term (term)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """

    try:
        cursor.execute(sql)
        conn.commit()
        print('[OK] almt_param_cashflow_schedule 表创建成功')

        # 检查是否已有数据
        cursor.execute("SELECT COUNT(*) FROM almt_param_cashflow_schedule")
        cnt = cursor.fetchone()[0]
        print(f'[INFO] 当前表行数: {cnt}')

        if cnt == 0:
            print('[HINT] 表为空，ENGINE C 会自动回退到 CF_PATTERN 等比例分摊算法。')
            print('       如需完全对标 Excel，请从原 xlsm 的"标准化剩余本金表"导入数据。')
    except Exception as e:
        print(f'[FAIL] {e}')
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    main()
