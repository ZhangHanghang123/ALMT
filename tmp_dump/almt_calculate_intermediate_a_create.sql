CREATE TABLE `almt_calculate_intermediate_a` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `task_id` varchar(36) NOT NULL,
  `data_date` date DEFAULT NULL,
  `coa_cd` varchar(50) NOT NULL,
  `coa_name` varchar(200) DEFAULT NULL,
  `period` tinyint NOT NULL COMMENT '期数 0-24，0=M0',
  `bp_balance` decimal(20,4) DEFAULT NULL COMMENT '本期业务计划余额增量',
  `bp_average` decimal(20,4) DEFAULT NULL COMMENT '本期业务计划日均增量',
  `cum_balance` decimal(20,4) DEFAULT NULL COMMENT '累计余额',
  `cum_average` decimal(20,4) DEFAULT NULL COMMENT '累计日均',
  `m0_rate` decimal(20,6) DEFAULT NULL COMMENT 'M0 利率（仅 period=0 填）',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_task_coa_period` (`task_id`,`coa_cd`,`period`),
  KEY `idx_task` (`task_id`),
  KEY `idx_coa` (`coa_cd`)
) ENGINE=InnoDB AUTO_INCREMENT=212851 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
