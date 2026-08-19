CREATE TABLE `almt_current_position` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `uuid` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `coa_lvl` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `coa_name` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `balance` decimal(20,2) DEFAULT NULL,
  `average_balance` decimal(20,2) DEFAULT NULL,
  `rate` decimal(20,6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uuid` (`uuid`)
) ENGINE=InnoDB AUTO_INCREMENT=1987 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
