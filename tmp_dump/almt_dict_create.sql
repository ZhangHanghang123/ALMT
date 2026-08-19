CREATE TABLE `almt_dict` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `dict_id` varchar(10) NOT NULL,
  `dict_name` varchar(100) DEFAULT NULL,
  `dict_type` varchar(20) DEFAULT NULL,
  `description` varchar(200) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `dict_id` (`dict_id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
