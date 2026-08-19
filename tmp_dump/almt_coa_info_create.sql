CREATE TABLE `almt_coa_info` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `uuid` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `order_number` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `parent_coa_cd` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `coa_cd` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `coa_name` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `leaf_desc` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `leaf_flag` char(1) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uuid` (`uuid`)
) ENGINE=InnoDB AUTO_INCREMENT=775 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
