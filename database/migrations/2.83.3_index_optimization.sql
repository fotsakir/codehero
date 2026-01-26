-- Migration: 2.83.3 - SQL Index Optimization
-- Date: 2026-01-26
-- Description: Add missing indexes and remove redundant ones for better query performance

-- ============================================
-- STEP 1: Remove redundant index
-- ============================================

-- projects: idx_code is redundant because UNIQUE KEY `code` already exists
-- Note: This will error if index doesn't exist - safe to ignore
DROP INDEX idx_code ON projects;

-- ============================================
-- STEP 2: Add CRITICAL indexes (High-volume queries)
-- ============================================

-- TICKETS: Dashboard & status queries (status + updated_at for sorting)
CREATE INDEX idx_tickets_status_updated ON tickets(status, updated_at DESC);

-- TICKETS: Project-specific queries with ordering
CREATE INDEX idx_tickets_project_updated ON tickets(project_id, updated_at DESC);

-- CONVERSATION_MESSAGES: High-volume table - optimize ticket message retrieval
CREATE INDEX idx_messages_ticket_created ON conversation_messages(ticket_id, created_at);

-- CONVERSATION_MESSAGES: Filter by role (user/assistant/system)
CREATE INDEX idx_messages_ticket_role ON conversation_messages(ticket_id, role);

-- ============================================
-- STEP 3: Add HIGH PRIORITY indexes
-- ============================================

-- EXECUTION_SESSIONS: Status tracking for daemon
CREATE INDEX idx_sessions_status ON execution_sessions(status);

-- EXECUTION_SESSIONS: Combined ticket + status lookup
CREATE INDEX idx_sessions_ticket_status ON execution_sessions(ticket_id, status);

-- PROJECTS: Dashboard ordering (status + updated_at)
CREATE INDEX idx_projects_status_updated ON projects(status, updated_at DESC);

-- ============================================
-- STEP 4: Add MEDIUM PRIORITY indexes
-- ============================================

-- EXECUTION_LOGS: Log retrieval with ordering
CREATE INDEX idx_logs_session_created ON execution_logs(session_id, created_at DESC);

-- CONVERSATION_MESSAGES: Pagination optimization (newest first)
CREATE INDEX idx_messages_ticket_id_desc ON conversation_messages(ticket_id, id DESC);
