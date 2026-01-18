-- Migration: 2.72.0 - Auto Review System
-- Date: 2026-01-18
-- Description: Adds auto-review columns for intelligent ticket progression in relaxed mode
-- Note: All statements are idempotent (safe to run multiple times)

-- =============================================================================
-- HELPER PROCEDURES
-- =============================================================================

DROP PROCEDURE IF EXISTS add_column_if_not_exists;
DROP PROCEDURE IF EXISTS add_index_if_not_exists;

DELIMITER //

CREATE PROCEDURE add_column_if_not_exists(
    IN p_table_name VARCHAR(64),
    IN p_column_name VARCHAR(64),
    IN p_column_definition TEXT
)
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = DATABASE()
        AND table_name = p_table_name
        AND column_name = p_column_name
    ) THEN
        SET @sql = CONCAT('ALTER TABLE ', p_table_name, ' ADD COLUMN ', p_column_name, ' ', p_column_definition);
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END //

CREATE PROCEDURE add_index_if_not_exists(
    IN p_table_name VARCHAR(64),
    IN p_index_name VARCHAR(64),
    IN p_index_definition TEXT
)
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.statistics
        WHERE table_schema = DATABASE()
        AND table_name = p_table_name
        AND index_name = p_index_name
    ) THEN
        SET @sql = CONCAT('CREATE INDEX ', p_index_name, ' ON ', p_table_name, ' ', p_index_definition);
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END //

DELIMITER ;

-- =============================================================================
-- TICKETS TABLE - Auto-review columns
-- =============================================================================

-- Awaiting reason: why is ticket waiting for input?
-- completed = AI finished, question = AI asking something, error = AI hit error
-- stopped = user stopped, permission = needs permission, deps_ready = dependency done
CALL add_column_if_not_exists('tickets', 'awaiting_reason', "ENUM('completed', 'question', 'error', 'stopped', 'permission', 'deps_ready') DEFAULT NULL");

-- Scheduled review time (NULL = no review scheduled)
CALL add_column_if_not_exists('tickets', 'review_scheduled_at', 'DATETIME DEFAULT NULL');

-- Review retry counter (max 10 retries on Haiku call failure)
CALL add_column_if_not_exists('tickets', 'review_attempts', 'INT DEFAULT 0');

-- How was the ticket closed? (auto_reviewed, user_closed, etc.)
CALL add_column_if_not_exists('tickets', 'close_reason', 'VARCHAR(50) DEFAULT NULL');

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Index for finding tickets due for review
CALL add_index_if_not_exists('tickets', 'idx_tickets_review_scheduled', '(status, review_scheduled_at)');

-- =============================================================================
-- CLEANUP
-- =============================================================================

DROP PROCEDURE IF EXISTS add_column_if_not_exists;
DROP PROCEDURE IF EXISTS add_index_if_not_exists;

-- =============================================================================
-- MIGRATION RECORD
-- =============================================================================

INSERT INTO schema_migrations (version, applied_at)
VALUES ('2.72.0_auto_review_system', NOW())
ON DUPLICATE KEY UPDATE applied_at = NOW();
