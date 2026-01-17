-- Migration: 2.70.0 - Execution Modes (Autonomous/Supervised)
-- Date: 2026-01-17
-- Description: Adds execution mode support for tickets
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

DELIMITER ;

-- =============================================================================
-- PROJECTS TABLE - Default execution mode
-- =============================================================================

CALL add_column_if_not_exists('projects', 'default_execution_mode', "ENUM('autonomous', 'supervised') DEFAULT 'autonomous'");

-- =============================================================================
-- TICKETS TABLE - Execution mode and permission handling
-- =============================================================================

-- Execution mode (NULL = inherit from project, autonomous = full access, supervised = asks for permissions)
CALL add_column_if_not_exists('tickets', 'execution_mode', "ENUM('autonomous', 'supervised') DEFAULT NULL");

-- Pending permission request (JSON with tool, command, context)
CALL add_column_if_not_exists('tickets', 'pending_permission', 'JSON DEFAULT NULL');

-- Approved permissions for this ticket (JSON array of patterns)
CALL add_column_if_not_exists('tickets', 'approved_permissions', 'JSON DEFAULT NULL');

-- Relaxed mode: treat awaiting_input dependencies as completed
CALL add_column_if_not_exists('tickets', 'deps_include_awaiting', 'BOOLEAN DEFAULT FALSE');

-- =============================================================================
-- CLEANUP
-- =============================================================================

DROP PROCEDURE IF EXISTS add_column_if_not_exists;

-- =============================================================================
-- MIGRATION RECORD
-- =============================================================================

INSERT INTO schema_migrations (version, applied_at)
VALUES ('2.70.0', NOW())
ON DUPLICATE KEY UPDATE applied_at = NOW();
