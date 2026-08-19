CREATE TABLE `almt_result_plan` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `task_id` varchar(36) NOT NULL,
  `data_date` date DEFAULT NULL,
  `coa_cd` varchar(50) DEFAULT NULL,
  `coa_name` varchar(200) DEFAULT NULL,
  `item_name` varchar(100) DEFAULT NULL,
  `item_value` decimal(20,2) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_task` (`task_id`),
  KEY `idx_almt_result_plan_task` (`task_id`)
) ENGINE=InnoDB AUTO_INCREMENT=26077 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
