CREATE TABLE `almt_dict_value` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `dict_id` varchar(10) DEFAULT NULL,
  `value_code` varchar(6) NOT NULL,
  `value_name` varchar(100) NOT NULL,
  `sort_no` int DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_dict_code` (`dict_id`,`value_code`)
) ENGINE=InnoDB AUTO_INCREMENT=167 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
