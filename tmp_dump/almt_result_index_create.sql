CREATE TABLE `almt_result_index` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `task_id` varchar(36) NOT NULL,
  `data_date` date DEFAULT NULL,
  `coa_cd` varchar(50) DEFAULT NULL,
  `coa_name` varchar(200) DEFAULT NULL,
  `total_balance` decimal(20,2) DEFAULT NULL,
  `average_balance` decimal(20,2) DEFAULT NULL,
  `avg_rate` decimal(20,6) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_task` (`task_id`),
  KEY `idx_almt_result_index_task` (`task_id`)
) ENGINE=InnoDB AUTO_INCREMENT=10030 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
