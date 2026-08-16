import pymysql
import hashlib

# 连接MySQL
conn = pymysql.connect(host='localhost', user='almt', password='almt', database='almt_db', port=3306)
cursor = conn.cursor()

# 创建表SQL
tables = [
    '''CREATE TABLE IF NOT EXISTS sys_user (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        username VARCHAR(50) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        email VARCHAR(100),
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',

    '''CREATE TABLE IF NOT EXISTS almt_coa_info (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        uuid VARCHAR(36) NOT NULL UNIQUE,
        order_number VARCHAR(50),
        parent_coa_cd VARCHAR(50),
        coa_cd VARCHAR(50) NOT NULL,
        coa_name VARCHAR(200),
        leaf_desc VARCHAR(200),
        leaf_flag CHAR(1),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )''',

    '''CREATE TABLE IF NOT EXISTS almt_coa_attribute (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        uuid VARCHAR(36) NOT NULL UNIQUE,
        coa_cd VARCHAR(50),
        coa_name VARCHAR(200),
        term VARCHAR(50),
        accrule_base VARCHAR(50),
        curve_name VARCHAR(100),
        curve_id VARCHAR(50),
        business_line VARCHAR(100),
        float_ratio DECIMAL(10,4),
        replace_type VARCHAR(50),
        reprice_freq VARCHAR(50)
    )''',

    '''CREATE TABLE IF NOT EXISTS almt_current_position (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        uuid VARCHAR(36) NOT NULL UNIQUE,
        coa_lvl VARCHAR(50),
        coa_name VARCHAR(200),
        balance DECIMAL(20,2),
        average_balance DECIMAL(20,2),
        rate DECIMAL(10,6)
    )''',

    '''CREATE TABLE IF NOT EXISTS almt_param_rate_scenario (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        uuid VARCHAR(36) NOT NULL UNIQUE,
        order_number VARCHAR(50),
        curve_name VARCHAR(100),
        curve_id VARCHAR(50),
        current_curve_value DECIMAL(10,6)
    )''',

    '''CREATE TABLE IF NOT EXISTS almt_param_risk_weight (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        uuid VARCHAR(36) NOT NULL UNIQUE,
        coa_cd VARCHAR(50),
        coa_name VARCHAR(200),
        weight DECIMAL(10,6)
    )''',

    '''CREATE TABLE IF NOT EXISTS almt_calculate_task (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        task_id VARCHAR(36) NOT NULL UNIQUE,
        data_date DATE,
        status VARCHAR(20) DEFAULT 'pending',
        progress INT DEFAULT 0,
        error_message TEXT,
        started_at TIMESTAMP NULL,
        completed_at TIMESTAMP NULL,
        created_by BIGINT
    )''',

    # ENGINE C 完全对标 Excel "标准化剩余本金表"——手工录入现金流调度
    # 每行：某个账户册在某个期限 term 下的某期 period(0-24) 本金剩余/还本比例 + 'x' 标记
    '''CREATE TABLE IF NOT EXISTS almt_param_cashflow_schedule (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        uuid VARCHAR(36) NOT NULL UNIQUE,
        coa_cd VARCHAR(50) NOT NULL,
        term VARCHAR(20) NOT NULL,
        period TINYINT NOT NULL COMMENT "期数 0-24，0=M0 基线",
        principal_ratio DECIMAL(10,6) COMMENT "本期本金占比（占原余额的比例）",
        is_x_marker TINYINT DEFAULT 0 COMMENT "Excel 标记位 x：本期还清 + 计息",
        remark VARCHAR(200) COMMENT "备注",
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uk_coa_term_period (coa_cd, term, period),
        INDEX idx_coa_cd (coa_cd),
        INDEX idx_term (term)
    )'''
]

for sql in tables:
    cursor.execute(sql)
    print(f'[OK] 表创建成功')

# 插入默认管理员账号 (密码: admin123)
password_hash = hashlib.sha256('admin123'.encode('utf-8')).hexdigest()

try:
    cursor.execute("INSERT INTO sys_user (username, password_hash) VALUES ('admin', %s)", (password_hash,))
    print('[OK] 默认管理员账号创建成功 (admin/admin123)')
except Exception as e:
    print(f'[INFO] 管理员账号可能已存在: {e}')

conn.commit()
cursor.close()
conn.close()
print('\n数据库初始化完成!')
