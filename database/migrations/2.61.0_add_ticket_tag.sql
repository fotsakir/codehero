-- Migration: 2.61.0_add_ticket_tag
-- Description: Add tag field to tickets table for categorizing tickets (bugfix, hotfix, feature, test, custom)
-- Date: 2026-01-15

-- Check if column exists before adding (idempotent migration)
SET @exist := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
               WHERE TABLE_SCHEMA = DATABASE()
               AND TABLE_NAME = 'tickets'
               AND COLUMN_NAME = 'tag');

SET @query := IF(@exist = 0,
    "ALTER TABLE tickets ADD COLUMN tag ENUM('bugfix','hotfix','feature','test','custom') DEFAULT 'feature' AFTER priority",
    'SELECT "Column tag already exists" AS message');

PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
