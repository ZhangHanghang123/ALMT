CREATE TABLE `almt_coa_attribute` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `uuid` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `coa_cd` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `coa_name` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `term` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `accrule_base` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `curve_name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `curve_id` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `business_line` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `float_ratio` decimal(10,4) DEFAULT NULL,
  `replace_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `reprice_freq` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uuid` (`uuid`)
) ENGINE=InnoDB AUTO_INCREMENT=551 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
