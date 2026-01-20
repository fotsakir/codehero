-- Migration: 2.79.0 - Semi-Autonomous Execution Mode
-- Date: 2025-01-20
-- Description: Adds 'semi-autonomous' option to execution_mode ENUM

-- Update projects table
ALTER TABLE projects
MODIFY COLUMN default_execution_mode ENUM('autonomous', 'semi-autonomous', 'supervised') DEFAULT 'autonomous';

-- Update tickets table
ALTER TABLE tickets
MODIFY COLUMN execution_mode ENUM('autonomous', 'semi-autonomous', 'supervised') DEFAULT NULL;

-- Verify changes
SELECT 'Migration 2.79.0 completed - semi-autonomous mode added' AS status;
