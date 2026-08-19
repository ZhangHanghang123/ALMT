CREATE TABLE `almt_time_step` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `step_no` int NOT NULL,
  `month_label` varchar(20) DEFAULT NULL,
  `month_end_date` date DEFAULT NULL,
  `month_days` int DEFAULT NULL,
  `year_days` int DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_step` (`step_no`)
) ENGINE=InnoDB AUTO_INCREMENT=73 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
