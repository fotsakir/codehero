-- Migration: 2.83.0 - Context System Refactoring
-- Adds global_context and project_context columns to projects table
-- for per-project customizable AI context

-- Add context columns to projects table
ALTER TABLE projects
ADD COLUMN global_context TEXT COMMENT 'Customized global context for this project' AFTER context,
ADD COLUMN project_context TEXT COMMENT 'Language-specific context for this project' AFTER global_context;

-- Update schema_migrations
INSERT INTO schema_migrations (version) VALUES ('2.83.0')
ON DUPLICATE KEY UPDATE applied_at = CURRENT_TIMESTAMP;
