CREATE TABLE `almt_calculate_intermediate_c` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `task_id` varchar(36) NOT NULL,
  `data_date` date DEFAULT NULL,
  `coa_cd` varchar(50) NOT NULL,
  `coa_name` varchar(200) DEFAULT NULL,
  `term` varchar(20) DEFAULT NULL COMMENT '原始期限',
  `period` tinyint NOT NULL COMMENT '期数 0-24',
  `principal` decimal(20,4) DEFAULT NULL COMMENT '本期本金还本',
  `interest` decimal(20,4) DEFAULT NULL COMMENT '本期利息',
  `total_cf` decimal(20,4) DEFAULT NULL COMMENT '本期总现金流',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_task_coa_period` (`task_id`,`coa_cd`,`period`),
  KEY `idx_task` (`task_id`),
  KEY `idx_coa` (`coa_cd`),
  KEY `idx_term` (`term`)
) ENGINE=InnoDB AUTO_INCREMENT=212851 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
