-- Migration: 2.74.0 - Project Import Feature
-- Adds reference_path column to projects for storing imported reference projects
-- Compatible with MySQL 5.7+ and 8.0+

-- Add reference_path column (idempotent - checks if exists first)
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'projects'
    AND COLUMN_NAME = 'reference_path');

SET @sql = IF(@col_exists = 0,
    'ALTER TABLE projects ADD COLUMN reference_path VARCHAR(500) DEFAULT NULL COMMENT ''Path to imported reference project (for template mode)''',
    'SELECT ''Column reference_path already exists''');

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add index (idempotent - checks if exists first)
SET @idx_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'projects'
    AND INDEX_NAME = 'idx_projects_reference_path');

SET @sql = IF(@idx_exists = 0,
    'CREATE INDEX idx_projects_reference_path ON projects(reference_path)',
    'SELECT ''Index idx_projects_reference_path already exists''');

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
