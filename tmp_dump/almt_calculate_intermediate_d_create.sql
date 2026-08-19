CREATE TABLE `almt_calculate_intermediate_d` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `task_id` varchar(36) NOT NULL,
  `data_date` date DEFAULT NULL,
  `coa_cd` varchar(50) NOT NULL,
  `coa_name` varchar(200) DEFAULT NULL,
  `metric_idx` tinyint NOT NULL COMMENT '指标序号 1-23',
  `metric_name` varchar(100) DEFAULT NULL COMMENT '指标名称',
  `num_value` decimal(20,4) DEFAULT NULL COMMENT '分子',
  `den_value` decimal(20,4) DEFAULT NULL COMMENT '分母',
  `ratio_value` decimal(20,6) DEFAULT NULL COMMENT '比率值',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_task_coa_metric` (`task_id`,`coa_cd`,`metric_idx`),
  KEY `idx_task` (`task_id`),
  KEY `idx_coa` (`coa_cd`),
  KEY `idx_metric` (`metric_idx`)
) ENGINE=InnoDB AUTO_INCREMENT=178021 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
