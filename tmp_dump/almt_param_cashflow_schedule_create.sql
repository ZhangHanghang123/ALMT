CREATE TABLE `almt_param_cashflow_schedule` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `uuid` varchar(36) NOT NULL,
  `coa_cd` varchar(50) NOT NULL,
  `term` varchar(20) NOT NULL,
  `period` tinyint NOT NULL COMMENT '期数 0-24，0=M0 基线',
  `principal_ratio` decimal(10,6) DEFAULT NULL COMMENT '本期本金占比',
  `is_x_marker` tinyint DEFAULT '0' COMMENT 'Excel x 标记位',
  `remark` varchar(200) DEFAULT NULL COMMENT '备注',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uuid` (`uuid`),
  UNIQUE KEY `uk_coa_term_period` (`coa_cd`,`term`,`period`),
  KEY `idx_coa_cd` (`coa_cd`),
  KEY `idx_term` (`term`)
) ENGINE=InnoDB AUTO_INCREMENT=51 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
