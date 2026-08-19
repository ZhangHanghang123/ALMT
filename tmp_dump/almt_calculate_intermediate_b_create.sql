CREATE TABLE `almt_calculate_intermediate_b` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `task_id` varchar(36) NOT NULL,
  `data_date` date DEFAULT NULL,
  `coa_cd` varchar(50) NOT NULL,
  `coa_name` varchar(200) DEFAULT NULL,
  `period` tinyint NOT NULL COMMENT '期数 1-24',
  `base_rate` decimal(20,6) DEFAULT NULL COMMENT '基础利率（来自利率情景）',
  `pricing_rate` decimal(20,6) DEFAULT NULL COMMENT '叠加定价策略 BP 后的利率',
  `ftp_income` decimal(20,4) DEFAULT NULL COMMENT 'FTP 月度收入',
  `delta_ftp` decimal(20,4) DEFAULT NULL COMMENT '策略增量 FTP',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_task_coa_period` (`task_id`,`coa_cd`,`period`),
  KEY `idx_task` (`task_id`),
  KEY `idx_coa` (`coa_cd`)
) ENGINE=InnoDB AUTO_INCREMENT=204337 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
