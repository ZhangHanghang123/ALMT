CREATE TABLE `almt_param_ftp_spread` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `uuid` varchar(36) NOT NULL,
  `coa_cd` varchar(50) DEFAULT NULL,
  `coa_name` varchar(200) DEFAULT NULL,
  `spread` decimal(10,6) DEFAULT NULL,
  `curve_name` varchar(100) DEFAULT NULL,
  `term` varchar(50) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uuid` (`uuid`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
