-- Migration: 2.69.0 - Ticket Sequencing & Autonomous Operation
-- Date: 2026-01-17
-- Description: Adds ticket types, sequencing, dependencies, retry logic, timeout, and test verification
-- Note: All statements are idempotent (safe to run multiple times)

-- =============================================================================
-- HELPER PROCEDURE FOR IDEMPOTENT COLUMN ADDITIONS
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
    IN p_index_columns VARCHAR(255)
)
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.statistics
        WHERE table_schema = DATABASE()
        AND table_name = p_table_name
        AND index_name = p_index_name
    ) THEN
        SET @sql = CONCAT('CREATE INDEX ', p_index_name, ' ON ', p_table_name, '(', p_index_columns, ')');
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END //

DELIMITER ;

-- =============================================================================
-- TICKETS TABLE ADDITIONS
-- =============================================================================

-- Ticket Type (feature, bug, debug, rnd, task, improvement, docs)
CALL add_column_if_not_exists('tickets', 'ticket_type', "ENUM('feature','bug','debug','rnd','task','improvement','docs') DEFAULT 'task'");

-- Sequence Order (for ordering tickets within a project)
CALL add_column_if_not_exists('tickets', 'sequence_order', 'INT DEFAULT NULL');

-- Force Next (jump to front of queue)
CALL add_column_if_not_exists('tickets', 'is_forced', 'BOOLEAN DEFAULT FALSE');

-- Retry Logic
CALL add_column_if_not_exists('tickets', 'retry_count', 'INT DEFAULT 0');
CALL add_column_if_not_exists('tickets', 'max_retries', 'INT DEFAULT 3');

-- Timeout per Ticket
CALL add_column_if_not_exists('tickets', 'max_duration_minutes', 'INT DEFAULT 60');

-- Parent Ticket (for sub-tickets)
CALL add_column_if_not_exists('tickets', 'parent_ticket_id', 'INT DEFAULT NULL');

-- Test Verification
CALL add_column_if_not_exists('tickets', 'test_command', 'VARCHAR(255) DEFAULT NULL');
CALL add_column_if_not_exists('tickets', 'require_tests_pass', 'BOOLEAN DEFAULT FALSE');

-- Auto-start after dependencies complete (FALSE = wait for user input)
CALL add_column_if_not_exists('tickets', 'start_when_ready', 'BOOLEAN DEFAULT TRUE');

-- Include awaiting_input as completed for dependency checks (relaxed mode)
CALL add_column_if_not_exists('tickets', 'deps_include_awaiting', 'BOOLEAN DEFAULT FALSE');

-- Add timeout status to enum (this will be ignored if already has it)
ALTER TABLE tickets MODIFY COLUMN status ENUM('new','open','pending','in_progress','awaiting_input','done','failed','stuck','skipped','timeout') DEFAULT 'open';

-- Add foreign key for parent ticket (ignore if exists)
SET @fk_exists = (SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
    WHERE CONSTRAINT_SCHEMA = DATABASE() AND CONSTRAINT_NAME = 'fk_parent_ticket');
SET @sql = IF(@fk_exists = 0,
    'ALTER TABLE tickets ADD CONSTRAINT fk_parent_ticket FOREIGN KEY (parent_ticket_id) REFERENCES tickets(id) ON DELETE SET NULL',
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Index for sequencing queries (ignore if exists)
CALL add_index_if_not_exists('tickets', 'idx_ticket_sequence', 'project_id, sequence_order, is_forced, priority');

-- Index for parent-child relationships (ignore if exists)
CALL add_index_if_not_exists('tickets', 'idx_parent_ticket', 'parent_ticket_id');

-- =============================================================================
-- PROJECTS TABLE ADDITIONS
-- =============================================================================

-- Default test command for project
CALL add_column_if_not_exists('projects', 'default_test_command', 'VARCHAR(255) DEFAULT NULL');

-- =============================================================================
-- TICKET DEPENDENCIES TABLE (Many-to-Many)
-- =============================================================================

CREATE TABLE IF NOT EXISTS ticket_dependencies (
    ticket_id INT NOT NULL,
    depends_on_ticket_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticket_id, depends_on_ticket_id),
    CONSTRAINT fk_dep_ticket FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
    CONSTRAINT fk_dep_depends_on FOREIGN KEY (depends_on_ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Index for dependency lookups (ignore if exists)
CALL add_index_if_not_exists('ticket_dependencies', 'idx_depends_on', 'depends_on_ticket_id');

-- =============================================================================
-- EXECUTION SESSIONS TABLE ADDITIONS
-- =============================================================================

-- Add timeout status to execution sessions
ALTER TABLE execution_sessions MODIFY COLUMN status ENUM('running','completed','failed','stuck','stopped','skipped','timeout') DEFAULT 'running';

-- Track when ticket processing started (for timeout calculation)
CALL add_column_if_not_exists('execution_sessions', 'processing_started_at', 'TIMESTAMP NULL');

-- =============================================================================
-- VIEWS FOR REPORTING
-- =============================================================================

-- View for project progress statistics
CREATE OR REPLACE VIEW v_project_progress AS
SELECT
    p.id as project_id,
    p.name as project_name,
    p.code as project_code,
    COUNT(t.id) as total_tickets,
    SUM(CASE WHEN t.status IN ('done', 'skipped') THEN 1 ELSE 0 END) as completed_tickets,
    SUM(CASE WHEN t.status = 'failed' THEN 1 ELSE 0 END) as failed_tickets,
    SUM(CASE WHEN t.status = 'timeout' THEN 1 ELSE 0 END) as timeout_tickets,
    SUM(CASE WHEN t.status = 'in_progress' THEN 1 ELSE 0 END) as in_progress_tickets,
    SUM(CASE WHEN t.status IN ('open', 'new', 'pending') THEN 1 ELSE 0 END) as pending_tickets,
    SUM(CASE WHEN t.status = 'awaiting_input' THEN 1 ELSE 0 END) as awaiting_input_tickets,
    ROUND(
        (SUM(CASE WHEN t.status IN ('done', 'skipped') THEN 1 ELSE 0 END) * 100.0) /
        NULLIF(COUNT(t.id), 0), 1
    ) as progress_percent,
    SUM(t.total_tokens) as total_tokens,
    SUM(t.total_duration_seconds) as total_duration_seconds
FROM projects p
LEFT JOIN tickets t ON t.project_id = p.id AND t.parent_ticket_id IS NULL
WHERE p.status = 'active'
GROUP BY p.id, p.name, p.code;

-- View for tickets by type statistics
CREATE OR REPLACE VIEW v_tickets_by_type AS
SELECT
    p.id as project_id,
    t.ticket_type,
    COUNT(t.id) as total,
    SUM(CASE WHEN t.status IN ('done', 'skipped') THEN 1 ELSE 0 END) as completed
FROM projects p
JOIN tickets t ON t.project_id = p.id
GROUP BY p.id, t.ticket_type;

-- View for blocked tickets (have unfinished dependencies)
CREATE OR REPLACE VIEW v_blocked_tickets AS
SELECT
    t.id as ticket_id,
    t.ticket_number,
    t.title,
    t.project_id,
    GROUP_CONCAT(dt.ticket_number SEPARATOR ', ') as blocked_by
FROM tickets t
JOIN ticket_dependencies td ON td.ticket_id = t.id
JOIN tickets dt ON dt.id = td.depends_on_ticket_id
WHERE t.status NOT IN ('done', 'skipped', 'failed')
  AND dt.status NOT IN ('done', 'skipped')
GROUP BY t.id, t.ticket_number, t.title, t.project_id;

-- =============================================================================
-- CLEANUP
-- =============================================================================

DROP PROCEDURE IF EXISTS add_column_if_not_exists;
DROP PROCEDURE IF EXISTS add_index_if_not_exists;

-- =============================================================================
-- MIGRATION RECORD
-- =============================================================================

INSERT INTO schema_migrations (version, applied_at)
VALUES ('2.69.0', NOW())
ON DUPLICATE KEY UPDATE applied_at = NOW();
