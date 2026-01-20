-- Migration: 2.77.0 - Add 2FA and account lockout
-- Date: 2026-01-20

-- Auth settings table for single user
CREATE TABLE IF NOT EXISTS auth_settings (
    id INT PRIMARY KEY DEFAULT 1,
    failed_attempts INT DEFAULT 0,
    locked_until TIMESTAMP NULL,
    totp_secret VARCHAR(32) NULL,
    totp_enabled BOOLEAN DEFAULT FALSE,
    remember_token_hash VARCHAR(64) NULL,
    remember_token_expires TIMESTAMP NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Insert default row if not exists
INSERT IGNORE INTO auth_settings (id) VALUES (1);

-- Add columns if table already exists (for upgrades)
-- Note: These will fail silently if columns already exist
SET @query = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
     WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'auth_settings' AND COLUMN_NAME = 'remember_token_hash') = 0,
    'ALTER TABLE auth_settings ADD COLUMN remember_token_hash VARCHAR(64) NULL',
    'SELECT 1'
));
PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @query = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
     WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'auth_settings' AND COLUMN_NAME = 'remember_token_expires') = 0,
    'ALTER TABLE auth_settings ADD COLUMN remember_token_expires TIMESTAMP NULL',
    'SELECT 1'
));
PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
