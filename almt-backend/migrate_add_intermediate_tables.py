"""
迁移脚本：新增 4 张引擎中间结果表

存 ENGINE A/B/C/D 的完整输出：
  - almt_calculate_intermediate_a  ENGINE A 业务分摊（24 期 × 余额+日均）
  - almt_calculate_intermediate_b  ENGINE B 定价策略（24 期 × base/pricing/ftp/delta_ftp）
  - almt_calculate_intermediate_c  ENGINE C 现金流（25 期 × principal/interest/total）
  - almt_calculate_intermediate_d  ENGINE D 指标计量（23 组 × num/den/ratio）

设计原则：
  - 宽表存储：每张表一个 coa_cd 占多行（每行一个期数），用 field_name 标识
  - task_id 索引（按 calc_version 反查 task_id 后过滤）
  - 每张表带 (task_id, coa_cd, period, value) 结构化字段

执行：python migrate_add_intermediate_tables.py
"""
import pymysql


def main():
    conn = pymysql.connect(
        host='localhost', user='almt', password='almt',
        database='almt_db', port=3306
    )
    cursor = conn.cursor()

    tables = [
        # ENGINE A：M0~M24 共 25 期，每期 4 列（bp_balance / bp_average / cum_balance / cum_average）
        """CREATE TABLE IF NOT EXISTS almt_calculate_intermediate_a (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            task_id VARCHAR(36) NOT NULL,
            data_date DATE,
            coa_cd VARCHAR(50) NOT NULL,
            coa_name VARCHAR(200),
            period TINYINT NOT NULL COMMENT '期数 0-24，0=M0',
            bp_balance DECIMAL(20,4) COMMENT '本期业务计划余额增量',
            bp_average DECIMAL(20,4) COMMENT '本期业务计划日均增量',
            cum_balance DECIMAL(20,4) COMMENT '累计余额',
            cum_average DECIMAL(20,4) COMMENT '累计日均',
            m0_rate DECIMAL(20,6) COMMENT 'M0 利率（仅 period=0 填）',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_task (task_id),
            INDEX idx_coa (coa_cd),
            UNIQUE KEY uk_task_coa_period (task_id, coa_cd, period)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci""",

        # ENGINE B：M1~M24 共 24 期，每期 4 列（base_rate / pricing_rate / ftp_income / delta_ftp）
        """CREATE TABLE IF NOT EXISTS almt_calculate_intermediate_b (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            task_id VARCHAR(36) NOT NULL,
            data_date DATE,
            coa_cd VARCHAR(50) NOT NULL,
            coa_name VARCHAR(200),
            period TINYINT NOT NULL COMMENT '期数 1-24',
            base_rate DECIMAL(20,6) COMMENT '基础利率（来自利率情景）',
            pricing_rate DECIMAL(20,6) COMMENT '叠加定价策略 BP 后的利率',
            ftp_income DECIMAL(20,4) COMMENT 'FTP 月度收入',
            delta_ftp DECIMAL(20,4) COMMENT '策略增量 FTP',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_task (task_id),
            INDEX idx_coa (coa_cd),
            UNIQUE KEY uk_task_coa_period (task_id, coa_cd, period)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci""",

        # ENGINE C：M0~M24 共 25 期，每期 3 列（principal / interest / total）
        """CREATE TABLE IF NOT EXISTS almt_calculate_intermediate_c (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            task_id VARCHAR(36) NOT NULL,
            data_date DATE,
            coa_cd VARCHAR(50) NOT NULL,
            coa_name VARCHAR(200),
            term VARCHAR(20) COMMENT '原始期限',
            period TINYINT NOT NULL COMMENT '期数 0-24',
            principal DECIMAL(20,4) COMMENT '本期本金还本',
            interest DECIMAL(20,4) COMMENT '本期利息',
            total_cf DECIMAL(20,4) COMMENT '本期总现金流',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_task (task_id),
            INDEX idx_coa (coa_cd),
            INDEX idx_term (term),
            UNIQUE KEY uk_task_coa_period (task_id, coa_cd, period)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci""",

        # ENGINE D：23 组指标，每组 3 列（num / den / ratio）
        """CREATE TABLE IF NOT EXISTS almt_calculate_intermediate_d (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            task_id VARCHAR(36) NOT NULL,
            data_date DATE,
            coa_cd VARCHAR(50) NOT NULL,
            coa_name VARCHAR(200),
            metric_idx TINYINT NOT NULL COMMENT '指标序号 1-23',
            metric_name VARCHAR(100) COMMENT '指标名称',
            num_value DECIMAL(20,4) COMMENT '分子',
            den_value DECIMAL(20,4) COMMENT '分母',
            ratio_value DECIMAL(20,6) COMMENT '比率值',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_task (task_id),
            INDEX idx_coa (coa_cd),
            INDEX idx_metric (metric_idx),
            UNIQUE KEY uk_task_coa_metric (task_id, coa_cd, metric_idx)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci""",
    ]

    for sql in tables:
        try:
            cursor.execute(sql)
            tbl_name = sql.split('EXISTS ')[1].split(' ')[0]
            print(f'[OK] {tbl_name}')
        except Exception as e:
            print(f'[FAIL] {e}')

    conn.commit()
    cursor.close()
    conn.close()
    print('\n迁移完成！')


if __name__ == '__main__':
    main()