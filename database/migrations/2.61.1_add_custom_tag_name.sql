-- Migration: 2.61.1_add_custom_tag_name
-- Description: Add tag_custom_name field to tickets table for custom tag labels
-- Date: 2026-01-15

-- Check if column exists before adding (idempotent migration)
SET @exist := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
               WHERE TABLE_SCHEMA = DATABASE()
               AND TABLE_NAME = 'tickets'
               AND COLUMN_NAME = 'tag_custom_name');

SET @query := IF(@exist = 0,
    "ALTER TABLE tickets ADD COLUMN tag_custom_name VARCHAR(50) NULL AFTER tag",
    'SELECT "Column tag_custom_name already exists" AS message');

PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
