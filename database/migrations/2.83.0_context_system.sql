-- Migration: 2.83.0 - Context System Refactoring
-- Adds global_context and project_context columns to projects table
-- for per-project customizable AI context

-- Add context columns to projects table (if they don't exist)
SET @dbname = DATABASE();

SELECT COUNT(*) INTO @col_exists FROM information_schema.columns
WHERE table_schema = @dbname AND table_name = 'projects' AND column_name = 'global_context';
SET @sql = IF(@col_exists = 0,
    'ALTER TABLE projects ADD COLUMN global_context TEXT COMMENT ''Customized global context for this project'' AFTER context',
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT COUNT(*) INTO @col_exists FROM information_schema.columns
WHERE table_schema = @dbname AND table_name = 'projects' AND column_name = 'project_context';
SET @sql = IF(@col_exists = 0,
    'ALTER TABLE projects ADD COLUMN project_context TEXT COMMENT ''Language-specific context for this project'' AFTER global_context',
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Update schema_migrations
INSERT INTO schema_migrations (version) VALUES ('2.83.0')
ON DUPLICATE KEY UPDATE applied_at = CURRENT_TIMESTAMP;
