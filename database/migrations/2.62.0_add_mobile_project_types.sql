-- Migration: 2.62.0_add_mobile_project_types
-- Description: Add mobile-oriented project types to support hybrid, cross-platform native, and native Android development
-- Date: 2026-01-15
-- Note: iOS development requires macOS and is not included

-- Check if the new project types already exist in the enum
SET @column_type := (SELECT COLUMN_TYPE FROM INFORMATION_SCHEMA.COLUMNS
                     WHERE TABLE_SCHEMA = DATABASE()
                     AND TABLE_NAME = 'projects'
                     AND COLUMN_NAME = 'project_type');

-- Only alter if the new types don't exist
SET @need_update := IF(@column_type LIKE '%capacitor_ionic_vue%', 0, 1);

SET @query := IF(@need_update = 1,
    "ALTER TABLE projects MODIFY COLUMN project_type ENUM(
        'web',
        'app',
        'hybrid',
        'api',
        'other',
        'capacitor_ionic_vue',
        'react_native',
        'flutter',
        'kotlin_multiplatform',
        'android_java_xml',
        'android_kotlin_xml',
        'android_kotlin_compose'
    ) DEFAULT 'web'",
    'SELECT "Mobile project types already exist" AS message');

PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
