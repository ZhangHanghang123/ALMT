-- 曲线定义表
CREATE TABLE IF NOT EXISTS `almt_curve_definition` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `uuid` VARCHAR(36) NOT NULL,
  `curve_code` VARCHAR(50) NOT NULL COMMENT '曲线代码',
  `curve_name` VARCHAR(100) NOT NULL COMMENT '曲线名称',
  `curve_type` VARCHAR(50) DEFAULT NULL COMMENT '曲线类型: SHIBOR/国债/存贷/FTP等',
  `currency` VARCHAR(10) DEFAULT 'CNY' COMMENT '币种',
  `description` VARCHAR(500) DEFAULT NULL COMMENT '曲线描述',
  `is_active` INT DEFAULT 1 COMMENT '是否启用: 0-禁用 1-启用',
  `remark` TEXT COMMENT '备注',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_uuid` (`uuid`),
  UNIQUE KEY `uk_curve_code` (`curve_code`),
  KEY `idx_curve_type` (`curve_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='曲线定义表';

-- 曲线点定义表
CREATE TABLE IF NOT EXISTS `almt_curve_point` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `uuid` VARCHAR(36) NOT NULL,
  `curve_uuid` VARCHAR(36) NOT NULL COMMENT '曲线UUID',
  `term` VARCHAR(20) NOT NULL COMMENT '期限: 1D/7D/1M/3M/6M/1Y/2Y/3Y/5Y/7Y/10Y等',
  `term_days` INT DEFAULT NULL COMMENT '期限天数(用于排序)',
  `rate_value` DECIMAL(12,6) DEFAULT NULL COMMENT '利率值(小数形式,如0.0325表示3.25%)',
  `spread` DECIMAL(12,6) DEFAULT NULL COMMENT '利差(基点)',
  `is_active` INT DEFAULT 1 COMMENT '是否启用: 0-禁用 1-启用',
  `remark` VARCHAR(500) DEFAULT NULL COMMENT '备注',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_uuid` (`uuid`),
  KEY `idx_curve_uuid` (`curve_uuid`),
  KEY `idx_term_days` (`term_days`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='曲线点定义表';

-- 插入示例数据
INSERT INTO `almt_curve_definition` (`uuid`, `curve_code`, `curve_name`, `curve_type`, `currency`, `description`, `is_active`) VALUES
('c001', 'SHIBOR', '上海银行间同业拆借利率', 'SHIBOR', 'CNY', '银行间同业拆借利率曲线', 1),
('c002', 'GOV_BOND_1Y', '1年期国债收益率', '国债', 'CNY', '1年期国债收益率曲线', 1),
('c003', 'GOV_BOND_5Y', '5年期国债收益率', '国债', 'CNY', '5年期国债收益率曲线', 1),
('c004', 'GOV_BOND_10Y', '10年期国债收益率', '国债', 'CNY', '10年期国债收益率曲线', 1),
('c005', 'LPR', '贷款市场报价利率', 'LPR', 'CNY', '贷款市场报价利率曲线', 1);

INSERT INTO `almt_curve_point` (`uuid`, `curve_uuid`, `term`, `term_days`, `rate_value`, `spread`) VALUES
-- SHIBOR曲线点
('p001', 'c001', '1D', 1, 0.01820, 0),
('p002', 'c001', '1W', 7, 0.01950, 0),
('p003', 'c001', '2W', 14, 0.02000, 0),
('p004', 'c001', '1M', 30, 0.02150, 0),
('p005', 'c001', '3M', 90, 0.02250, 0),
('p006', 'c001', '6M', 180, 0.02300, 0),
('p007', 'c001', '1Y', 365, 0.02350, 0),
-- 1年期国债曲线点
('p101', 'c002', '3M', 90, 0.01950, 0),
('p102', 'c002', '6M', 180, 0.02000, 0),
('p103', 'c002', '1Y', 365, 0.02100, 0),
-- 5年期国债曲线点
('p201', 'c003', '1Y', 365, 0.02250, 0),
('p202', 'c003', '3Y', 1095, 0.02400, 0),
('p203', 'c003', '5Y', 1825, 0.02550, 0),
('p204', 'c003', '7Y', 2555, 0.02600, 0),
-- 10年期国债曲线点
('p301', 'c004', '1Y', 365, 0.02200, 0),
('p302', 'c004', '3Y', 1095, 0.02350, 0),
('p303', 'c004', '5Y', 1825, 0.02500, 0),
('p304', 'c004', '7Y', 2555, 0.02650, 0),
('p305', 'c004', '10Y', 3650, 0.02750, 0),
-- LPR曲线点
('p401', 'c005', '1Y', 365, 0.03550, 0),
('p402', 'c005', '5Y', 1825, 0.04500, 0);
