-- Migration: 2.72.0 - Auto Review System
-- Date: 2026-01-18
-- Description: Adds auto-review columns for intelligent ticket progression in relaxed mode
-- Note: All statements are idempotent (safe to run multiple times)

-- =============================================================================
-- TICKETS TABLE - Auto-review columns
-- =============================================================================

-- Awaiting reason: why is ticket waiting for input?
-- Values: completed, question, error, stopped, permission, deps_ready
SET @col_exists = (SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE() AND table_name = 'tickets' AND column_name = 'awaiting_reason');
SET @sql = IF(@col_exists = 0,
    "ALTER TABLE tickets ADD COLUMN awaiting_reason ENUM('completed', 'question', 'error', 'stopped', 'permission', 'deps_ready') DEFAULT NULL",
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Scheduled review time (NULL = no review scheduled)
SET @col_exists = (SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE() AND table_name = 'tickets' AND column_name = 'review_scheduled_at');
SET @sql = IF(@col_exists = 0,
    'ALTER TABLE tickets ADD COLUMN review_scheduled_at DATETIME DEFAULT NULL',
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Review retry counter (max 10 retries on Haiku call failure)
SET @col_exists = (SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE() AND table_name = 'tickets' AND column_name = 'review_attempts');
SET @sql = IF(@col_exists = 0,
    'ALTER TABLE tickets ADD COLUMN review_attempts INT DEFAULT 0',
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- How was the ticket closed? (auto_reviewed, user_closed, etc.)
SET @col_exists = (SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE() AND table_name = 'tickets' AND column_name = 'close_reason');
SET @sql = IF(@col_exists = 0,
    'ALTER TABLE tickets ADD COLUMN close_reason VARCHAR(50) DEFAULT NULL',
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Index for finding tickets due for review
SET @idx_exists = (SELECT COUNT(*) FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = 'tickets' AND index_name = 'idx_tickets_review_scheduled');
SET @sql = IF(@idx_exists = 0,
    'CREATE INDEX idx_tickets_review_scheduled ON tickets (status, review_scheduled_at)',
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- =============================================================================
-- MIGRATION RECORD
-- =============================================================================

INSERT INTO schema_migrations (version, applied_at)
VALUES ('2.72.0_auto_review_system', NOW())
ON DUPLICATE KEY UPDATE applied_at = NOW();
