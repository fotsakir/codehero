-- Migration: 2.63.0 - Add Git Version Control
-- Description: Add tables for tracking Git repositories and commits per project

-- Track Git repositories per project
CREATE TABLE IF NOT EXISTS `project_git_repos` (
  `id` int NOT NULL AUTO_INCREMENT,
  `project_id` int NOT NULL,
  `repo_path` varchar(500) NOT NULL COMMENT 'Path to the repository directory',
  `path_type` enum('web', 'app') DEFAULT 'web' COMMENT 'Which path this repo tracks',
  `initialized_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `last_commit_hash` varchar(40) DEFAULT NULL COMMENT 'Hash of the last commit',
  `last_commit_at` timestamp NULL DEFAULT NULL,
  `total_commits` int DEFAULT 0,
  `status` enum('active', 'error', 'disabled') DEFAULT 'active',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_project_path` (`project_id`, `path_type`),
  KEY `idx_project` (`project_id`),
  CONSTRAINT `fk_git_repo_project` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Track commits for history and linking to tickets
CREATE TABLE IF NOT EXISTS `project_git_commits` (
  `id` int NOT NULL AUTO_INCREMENT,
  `project_id` int NOT NULL,
  `repo_id` int NOT NULL,
  `ticket_id` int DEFAULT NULL COMMENT 'Ticket that triggered this commit',
  `session_id` int DEFAULT NULL COMMENT 'Session that triggered this commit',
  `commit_hash` varchar(40) NOT NULL,
  `short_hash` varchar(7) NOT NULL,
  `message` text NOT NULL,
  `author` varchar(255) DEFAULT 'CodeHero',
  `files_changed` int DEFAULT 0,
  `insertions` int DEFAULT 0,
  `deletions` int DEFAULT 0,
  `is_rollback` tinyint(1) DEFAULT 0 COMMENT 'Whether this is a rollback commit',
  `rollback_to_hash` varchar(40) DEFAULT NULL COMMENT 'If rollback, which commit was reverted to',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_commit_hash` (`repo_id`, `commit_hash`),
  KEY `idx_project` (`project_id`),
  KEY `idx_ticket` (`ticket_id`),
  KEY `idx_session` (`session_id`),
  KEY `idx_created` (`created_at`),
  CONSTRAINT `fk_commit_project` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_commit_repo` FOREIGN KEY (`repo_id`) REFERENCES `project_git_repos` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Add git_enabled flag to projects table (ignore error if already exists)
SET @column_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'projects'
    AND COLUMN_NAME = 'git_enabled');

SET @query = IF(@column_exists = 0,
    'ALTER TABLE `projects` ADD COLUMN `git_enabled` tinyint(1) DEFAULT 1 COMMENT \'Whether Git is enabled for this project\'',
    'SELECT 1');

PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
