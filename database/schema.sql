-- MySQL dump 10.13  Distrib 8.0.44, for Linux (x86_64)
--
-- Host: localhost    Database: claude_knowledge
-- ------------------------------------------------------
-- Server version	8.0.44-0ubuntu0.24.04.2

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `conversation_extractions`
--

DROP TABLE IF EXISTS `conversation_extractions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `conversation_extractions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `ticket_id` int NOT NULL,
  `decisions` json DEFAULT NULL COMMENT '[{"decision": "Use JWT", "reason": "Stateless auth"}]',
  `problems_solved` json DEFAULT NULL COMMENT '[{"problem": "Race condition", "solution": "Added lock"}]',
  `files_modified` json DEFAULT NULL COMMENT '["auth.py", "models/user.py", "tests/test_auth.py"]',
  `current_status` text COLLATE utf8mb4_unicode_ci COMMENT 'Brief summary of where we left off',
  `blocking_issues` json DEFAULT NULL COMMENT '["Waiting for API key", "Need DB access"]',
  `waiting_for_user` json DEFAULT NULL COMMENT '["Clarification on requirements", "Approval to proceed"]',
  `external_dependencies` json DEFAULT NULL COMMENT '["Third-party API", "Database migration"]',
  `key_code_snippets` json DEFAULT NULL COMMENT '[{"file": "auth.py", "function": "login", "code": "..."}]',
  `important_variables` json DEFAULT NULL COMMENT '{"JWT_SECRET": "from env", "TOKEN_EXPIRY": "24h"}',
  `tests_status` json DEFAULT NULL COMMENT '{\n        "files": ["test_auth.py"],\n        "total": 15,\n        "passing": 13,\n        "failing": 2,\n        "failing_tests": ["test_timeout", "test_refresh"]\n    }',
  `error_patterns` json DEFAULT NULL COMMENT '[\n        {"error": "ConnectionTimeout", "context": "Cold start", "solution": "Retry logic"},\n        {"error": "JWT invalid", "context": "RS256", "solution": "Switch to HS256"}\n    ]',
  `important_notes` json DEFAULT NULL,
  `covers_msg_from_id` int DEFAULT NULL COMMENT 'First message ID covered by this extraction',
  `covers_msg_to_id` int DEFAULT NULL COMMENT 'Last message ID covered by this extraction',
  `messages_summarized` int DEFAULT '0' COMMENT 'Number of messages compressed',
  `tokens_before` int DEFAULT '0' COMMENT 'Tokens in original messages',
  `tokens_after` int DEFAULT '0' COMMENT 'Tokens in extraction',
  `compression_ratio` decimal(5,2) GENERATED ALWAYS AS ((case when (`tokens_before` > 0) then ((1 - (`tokens_after` / `tokens_before`)) * 100) else 0 end)) STORED COMMENT 'Percentage of tokens saved',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `extraction_model` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Model used for extraction',
  PRIMARY KEY (`id`),
  KEY `idx_ticket` (`ticket_id`),
  KEY `idx_coverage` (`ticket_id`,`covers_msg_to_id`),
  CONSTRAINT `conversation_extractions_ibfk_1` FOREIGN KEY (`ticket_id`) REFERENCES `tickets` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Extracted knowledge from older conversation messages';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `conversation_messages`
--

DROP TABLE IF EXISTS `conversation_messages`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `conversation_messages` (
  `id` int NOT NULL AUTO_INCREMENT,
  `ticket_id` int NOT NULL,
  `session_id` int DEFAULT NULL,
  `role` enum('user','assistant','system','tool_use','tool_result') NOT NULL,
  `content` text,
  `tool_name` varchar(100) DEFAULT NULL,
  `tool_input` json DEFAULT NULL,
  `tokens_used` int DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `token_count` int DEFAULT '0',
  `is_summarized` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `idx_ticket` (`ticket_id`),
  CONSTRAINT `conversation_messages_ibfk_1` FOREIGN KEY (`ticket_id`) REFERENCES `tickets` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `daemon_status`
--

DROP TABLE IF EXISTS `daemon_status`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `daemon_status` (
  `id` int NOT NULL DEFAULT '1',
  `status` enum('running','stopped','error') DEFAULT 'stopped',
  `current_ticket_id` int DEFAULT NULL,
  `current_session_id` int DEFAULT NULL,
  `last_heartbeat` timestamp NULL DEFAULT NULL,
  `started_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `developers`
--

DROP TABLE IF EXISTS `developers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `developers` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `email` varchar(100) DEFAULT NULL,
  `role` enum('admin','developer','viewer') DEFAULT 'developer',
  `is_active` tinyint(1) DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `last_login` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `execution_logs`
--

DROP TABLE IF EXISTS `execution_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `execution_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `session_id` int NOT NULL,
  `log_type` enum('info','output','error','warning','user') DEFAULT 'output',
  `message` text,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_session` (`session_id`),
  CONSTRAINT `execution_logs_ibfk_1` FOREIGN KEY (`session_id`) REFERENCES `execution_sessions` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `execution_sessions`
--

DROP TABLE IF EXISTS `execution_sessions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `execution_sessions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `ticket_id` int DEFAULT NULL,
  `status` enum('running','completed','failed','stuck','stopped','skipped') DEFAULT 'running',
  `tokens_used` int DEFAULT '0',
  `started_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `ended_at` timestamp NULL DEFAULT NULL,
  `api_calls` int DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `ticket_id` (`ticket_id`),
  CONSTRAINT `execution_sessions_ibfk_1` FOREIGN KEY (`ticket_id`) REFERENCES `tickets` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `project_knowledge`
--

DROP TABLE IF EXISTS `project_knowledge`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `project_knowledge` (
  `id` int NOT NULL AUTO_INCREMENT,
  `project_id` int NOT NULL,
  `coding_patterns` json DEFAULT NULL COMMENT '["Always use async/await", "Type hints required"]',
  `naming_conventions` json DEFAULT NULL COMMENT '{"functions": "snake_case", "classes": "PascalCase"}',
  `file_organization` json DEFAULT NULL COMMENT '{"tests": "tests/", "models": "src/models/"}',
  `known_gotchas` json DEFAULT NULL COMMENT '["MySQL drops connection after 30s idle"]',
  `error_solutions` json DEFAULT NULL COMMENT '[{"error": "JWT decode", "solution": "Use HS256"}]',
  `performance_notes` json DEFAULT NULL COMMENT '["Cache user queries", "Avoid N+1 in orders"]',
  `architecture_decisions` json DEFAULT NULL COMMENT '[{"decision": "Use events", "reason": "Decoupling"}]',
  `api_conventions` json DEFAULT NULL COMMENT '{"versioning": "/v1/", "auth": "Bearer token"}',
  `testing_patterns` json DEFAULT NULL COMMENT '{"framework": "pytest", "fixtures": true, "mocking": "unittest.mock"}',
  `ci_cd_notes` json DEFAULT NULL COMMENT '["Run migrations first", "Clear cache after deploy"]',
  `environment_notes` json DEFAULT NULL COMMENT '{"dev": "sqlite", "prod": "mysql"}',
  `security_considerations` json DEFAULT NULL COMMENT '["Sanitize all inputs", "Rate limit auth endpoints"]',
  `sensitive_files` json DEFAULT NULL COMMENT '[".env", "secrets.yaml"]',
  `last_updated` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `learned_from_tickets` json DEFAULT NULL COMMENT '[1, 5, 12] - ticket IDs we learned from',
  `knowledge_version` int DEFAULT '1' COMMENT 'Increment on major updates',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_project` (`project_id`),
  CONSTRAINT `project_knowledge_ibfk_1` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Learned knowledge from working on the project - grows over time';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `project_maps`
--

DROP TABLE IF EXISTS `project_maps`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `project_maps` (
  `id` int NOT NULL AUTO_INCREMENT,
  `project_id` int NOT NULL,
  `structure_summary` text COLLATE utf8mb4_unicode_ci COMMENT 'Folder structure with descriptions',
  `entry_points` json DEFAULT NULL COMMENT '[{"file": "app.py", "purpose": "Main entry"}]',
  `key_files` json DEFAULT NULL COMMENT '[{"file": "auth.py", "purpose": "Authentication"}]',
  `tech_stack` json DEFAULT NULL COMMENT '["Python 3.11", "Flask", "SQLAlchemy", "MySQL"]',
  `dependencies` json DEFAULT NULL COMMENT 'Key dependencies with versions',
  `architecture_type` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'MVC, microservices, monolith, etc',
  `design_patterns` json DEFAULT NULL COMMENT '["repository", "factory", "singleton"]',
  `file_count` int DEFAULT '0',
  `total_size_kb` int DEFAULT '0',
  `primary_language` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `generated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `expires_at` timestamp NULL DEFAULT NULL COMMENT 'Auto-refresh after this',
  `generation_tokens_used` int DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_project` (`project_id`),
  KEY `idx_expires` (`expires_at`),
  CONSTRAINT `project_maps_ibfk_1` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Static project structure map - generated once, refreshed periodically';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `projects`
--

DROP TABLE IF EXISTS `projects`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `projects` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(200) NOT NULL,
  `code` varchar(10) NOT NULL,
  `description` text,
  `project_type` enum('web','app','hybrid','api','other','capacitor_ionic_vue','react_native','flutter','kotlin_multiplatform','android_java_xml','android_kotlin_xml','android_kotlin_compose') DEFAULT 'web',
  `tech_stack` varchar(255) DEFAULT NULL,
  `web_path` varchar(500) DEFAULT NULL,
  `preview_url` varchar(500) DEFAULT NULL,
  `app_path` varchar(500) DEFAULT NULL,
  `context` text,
  `status` enum('active','archived','paused') DEFAULT 'active',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `db_name` varchar(100) DEFAULT NULL,
  `db_user` varchar(100) DEFAULT NULL,
  `db_password` varchar(255) DEFAULT NULL,
  `db_host` varchar(255) DEFAULT 'localhost',
  `total_tokens` int DEFAULT '0',
  `total_duration_seconds` int DEFAULT '0',
  `map_generated_at` timestamp NULL DEFAULT NULL,
  `knowledge_updated_at` timestamp NULL DEFAULT NULL,
  `ai_model` enum('opus','sonnet','haiku') DEFAULT 'sonnet',
  `android_device_type` enum('none','server','remote') DEFAULT 'none',
  `android_remote_host` varchar(255) DEFAULT NULL,
  `android_remote_port` int DEFAULT '5555',
  `android_screen_size` enum('phone','phone_small','tablet_7','tablet_10') DEFAULT 'phone',
  `dotnet_port` int DEFAULT NULL,
  `git_enabled` tinyint(1) DEFAULT '1' COMMENT 'Whether Git is enabled for this project',
  PRIMARY KEY (`id`),
  UNIQUE KEY `code` (`code`),
  KEY `idx_status` (`status`),
  KEY `idx_code` (`code`),
  KEY `idx_db_name` (`db_name`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `project_git_repos`
--

DROP TABLE IF EXISTS `project_git_repos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `project_git_repos` (
  `id` int NOT NULL AUTO_INCREMENT,
  `project_id` int NOT NULL,
  `repo_path` varchar(500) NOT NULL COMMENT 'Path to the repository directory',
  `path_type` enum('web','app') DEFAULT 'web' COMMENT 'Which path this repo tracks',
  `initialized_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `last_commit_hash` varchar(40) DEFAULT NULL COMMENT 'Hash of the last commit',
  `last_commit_at` timestamp NULL DEFAULT NULL,
  `total_commits` int DEFAULT '0',
  `status` enum('active','error','disabled') DEFAULT 'active',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_project_path` (`project_id`,`path_type`),
  KEY `idx_project` (`project_id`),
  CONSTRAINT `fk_git_repo_project` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `project_git_commits`
--

DROP TABLE IF EXISTS `project_git_commits`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `project_git_commits` (
  `id` int NOT NULL AUTO_INCREMENT,
  `project_id` int NOT NULL,
  `repo_id` int NOT NULL,
  `ticket_id` int DEFAULT NULL COMMENT 'Ticket that triggered this commit',
  `session_id` int DEFAULT NULL COMMENT 'Session that triggered this commit',
  `commit_hash` varchar(40) NOT NULL,
  `short_hash` varchar(7) NOT NULL,
  `message` text NOT NULL,
  `author` varchar(255) DEFAULT 'CodeHero',
  `files_changed` int DEFAULT '0',
  `insertions` int DEFAULT '0',
  `deletions` int DEFAULT '0',
  `is_rollback` tinyint(1) DEFAULT '0' COMMENT 'Whether this is a rollback commit',
  `rollback_to_hash` varchar(40) DEFAULT NULL COMMENT 'If rollback, which commit was reverted to',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_commit_hash` (`repo_id`,`commit_hash`),
  KEY `idx_project` (`project_id`),
  KEY `idx_ticket` (`ticket_id`),
  KEY `idx_session` (`session_id`),
  KEY `idx_created` (`created_at`),
  CONSTRAINT `fk_commit_project` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_commit_repo` FOREIGN KEY (`repo_id`) REFERENCES `project_git_repos` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `schema_migrations`
--

DROP TABLE IF EXISTS `schema_migrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `schema_migrations` (
  `version` varchar(50) NOT NULL,
  `applied_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tickets`
--

DROP TABLE IF EXISTS `tickets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tickets` (
  `id` int NOT NULL AUTO_INCREMENT,
  `project_id` int NOT NULL,
  `ticket_number` varchar(20) NOT NULL,
  `title` varchar(500) NOT NULL,
  `description` text,
  `context` text,
  `priority` enum('low','medium','high','critical') DEFAULT 'medium',
  `tag` enum('bugfix','hotfix','feature','test','custom') DEFAULT 'feature',
  `status` enum('new','open','pending','in_progress','awaiting_input','done','failed','stuck','skipped') DEFAULT 'open',
  `result_summary` text,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `closed_at` timestamp NULL DEFAULT NULL,
  `closed_by` varchar(50) DEFAULT NULL,
  `close_reason` enum('completed','manual','timeout','skipped','failed','approved','auto_approved_7days') DEFAULT NULL,
  `review_deadline` datetime DEFAULT NULL,
  `total_tokens` int DEFAULT '0',
  `total_duration_seconds` int DEFAULT '0',
  `ai_model` enum('opus','sonnet','haiku') DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ticket_number` (`ticket_number`),
  KEY `idx_project_status` (`project_id`,`status`),
  KEY `idx_status` (`status`),
  CONSTRAINT `tickets_ibfk_1` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `usage_stats`
--

DROP TABLE IF EXISTS `usage_stats`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `usage_stats` (
  `id` int NOT NULL AUTO_INCREMENT,
  `ticket_id` int NOT NULL,
  `project_id` int NOT NULL,
  `session_id` int DEFAULT NULL,
  `input_tokens` int DEFAULT '0',
  `output_tokens` int DEFAULT '0',
  `total_tokens` int DEFAULT '0',
  `cache_read_tokens` int DEFAULT '0',
  `cache_creation_tokens` int DEFAULT '0',
  `duration_seconds` int DEFAULT '0',
  `api_calls` int DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `session_id` (`session_id`),
  KEY `idx_usage_project` (`project_id`),
  KEY `idx_usage_ticket` (`ticket_id`),
  KEY `idx_usage_created` (`created_at`),
  KEY `idx_usage_project_created` (`project_id`,`created_at`),
  CONSTRAINT `usage_stats_ibfk_1` FOREIGN KEY (`ticket_id`) REFERENCES `tickets` (`id`) ON DELETE CASCADE,
  CONSTRAINT `usage_stats_ibfk_2` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE CASCADE,
  CONSTRAINT `usage_stats_ibfk_3` FOREIGN KEY (`session_id`) REFERENCES `execution_sessions` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_messages`
--

DROP TABLE IF EXISTS `user_messages`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_messages` (
  `id` int NOT NULL AUTO_INCREMENT,
  `ticket_id` int DEFAULT NULL,
  `user_id` int DEFAULT NULL,
  `content` text NOT NULL,
  `message_type` enum('command','message','input') DEFAULT 'message',
  `processed` tinyint(1) DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_ticket` (`ticket_id`),
  KEY `idx_processed` (`processed`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_preferences`
--

DROP TABLE IF EXISTS `user_preferences`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_preferences` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `language` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT 'el' COMMENT 'el, en, etc',
  `response_style` enum('concise','detailed','explain_first') COLLATE utf8mb4_unicode_ci DEFAULT 'detailed',
  `ask_before_changes` tinyint(1) DEFAULT '1' COMMENT 'Ask confirmation before making changes',
  `show_reasoning` tinyint(1) DEFAULT '1' COMMENT 'Explain the logic behind decisions',
  `programming_style` json DEFAULT NULL COMMENT '["functional", "OOP", "pragmatic", "clean_code"]',
  `code_verbosity` enum('minimal','balanced','verbose') COLLATE utf8mb4_unicode_ci DEFAULT 'balanced',
  `comment_style` json DEFAULT NULL COMMENT '["docstrings", "inline", "minimal", "jsdoc"]',
  `error_handling` json DEFAULT NULL COMMENT '["defensive", "fail_fast", "graceful", "log_everything"]',
  `type_hints` enum('always','public_only','never') COLLATE utf8mb4_unicode_ci DEFAULT 'always',
  `preferred_tools` json DEFAULT NULL COMMENT '{\n        "testing": "pytest",\n        "linting": "ruff",\n        "formatting": "black",\n        "package_manager": "pip",\n        "db_client": "mysql"\n    }',
  `git_style` json DEFAULT NULL COMMENT '{\n        "commit_style": "conventional",\n        "commit_language": "en",\n        "branch_naming": "feature/xxx",\n        "always_review_diff": true\n    }',
  `editor_config` json DEFAULT NULL COMMENT '{\n        "indent_size": 4,\n        "indent_style": "spaces",\n        "line_length": 100,\n        "trailing_newline": true\n    }',
  `review_before_commit` tinyint(1) DEFAULT '1',
  `test_after_changes` tinyint(1) DEFAULT '1',
  `explain_complex_code` tinyint(1) DEFAULT '1',
  `prefer_small_commits` tinyint(1) DEFAULT '1',
  `skill_level` enum('junior','mid','senior','expert') COLLATE utf8mb4_unicode_ci DEFAULT 'mid',
  `teach_mode` tinyint(1) DEFAULT '0' COMMENT 'Explain like teaching',
  `show_alternatives` tinyint(1) DEFAULT '0' COMMENT 'Show alternative solutions',
  `custom_instructions` text COLLATE utf8mb4_unicode_ci COMMENT 'Free text instructions from user',
  `learned_quirks` json DEFAULT NULL COMMENT 'Things learned about this user over time',
  `topics_of_interest` json DEFAULT NULL COMMENT '["performance", "security", "clean_code"]',
  `things_to_avoid` json DEFAULT NULL COMMENT '["over_engineering", "premature_optimization"]',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='User-level preferences that apply across all projects';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `daemon_logs`
--

DROP TABLE IF EXISTS `daemon_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `daemon_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `ticket_id` int DEFAULT NULL,
  `log_type` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT 'info',
  `message` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_ticket_id` (`ticket_id`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Daemon activity logs';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Temporary view structure for view `v_projects_needing_map`
--

DROP TABLE IF EXISTS `v_projects_needing_map`;
/*!50001 DROP VIEW IF EXISTS `v_projects_needing_map`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `v_projects_needing_map` AS SELECT 
 1 AS `project_id`,
 1 AS `name`,
 1 AS `project_path`,
 1 AS `generated_at`,
 1 AS `expires_at`,
 1 AS `map_status`*/;
SET character_set_client = @saved_cs_client;

--
-- Temporary view structure for view `v_ticket_context`
--

DROP TABLE IF EXISTS `v_ticket_context`;
/*!50001 DROP VIEW IF EXISTS `v_ticket_context`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `v_ticket_context` AS SELECT 
 1 AS `ticket_id`,
 1 AS `ticket_number`,
 1 AS `title`,
 1 AS `project_id`,
 1 AS `project_name`,
 1 AS `project_path`,
 1 AS `total_message_tokens`,
 1 AS `message_count`,
 1 AS `extracted_until_msg_id`,
 1 AS `has_project_map`,
 1 AS `has_project_knowledge`*/;
SET character_set_client = @saved_cs_client;

--
-- Temporary view structure for view `v_tickets_needing_extraction`
--

DROP TABLE IF EXISTS `v_tickets_needing_extraction`;
/*!50001 DROP VIEW IF EXISTS `v_tickets_needing_extraction`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `v_tickets_needing_extraction` AS SELECT 
 1 AS `ticket_id`,
 1 AS `ticket_number`,
 1 AS `total_messages`,
 1 AS `total_tokens`,
 1 AS `unsummarized_messages`,
 1 AS `unsummarized_tokens`*/;
SET character_set_client = @saved_cs_client;

--
-- Dumping routines for database 'claude_knowledge'
--

--
-- Final view structure for view `v_projects_needing_map`
--

/*!50001 DROP VIEW IF EXISTS `v_projects_needing_map`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_0900_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`claude_user`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_projects_needing_map` AS select `p`.`id` AS `project_id`,`p`.`name` AS `name`,coalesce(`p`.`web_path`,`p`.`app_path`) AS `project_path`,`pm`.`generated_at` AS `generated_at`,`pm`.`expires_at` AS `expires_at`,(case when (`pm`.`id` is null) then 'missing' when (`pm`.`expires_at` < now()) then 'expired' else 'ok' end) AS `map_status` from (`projects` `p` left join `project_maps` `pm` on((`p`.`id` = `pm`.`project_id`))) where ((`pm`.`id` is null) or (`pm`.`expires_at` < now())) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `v_ticket_context`
--

/*!50001 DROP VIEW IF EXISTS `v_ticket_context`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_0900_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`claude_user`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_ticket_context` AS select `t`.`id` AS `ticket_id`,`t`.`ticket_number` AS `ticket_number`,`t`.`title` AS `title`,`t`.`project_id` AS `project_id`,`p`.`name` AS `project_name`,coalesce(`p`.`web_path`,`p`.`app_path`) AS `project_path`,(select sum(`conversation_messages`.`token_count`) from `conversation_messages` where (`conversation_messages`.`ticket_id` = `t`.`id`)) AS `total_message_tokens`,(select count(0) from `conversation_messages` where (`conversation_messages`.`ticket_id` = `t`.`id`)) AS `message_count`,(select max(`conversation_extractions`.`covers_msg_to_id`) from `conversation_extractions` where (`conversation_extractions`.`ticket_id` = `t`.`id`)) AS `extracted_until_msg_id`,((select `project_maps`.`id` from `project_maps` where (`project_maps`.`project_id` = `t`.`project_id`)) is not null) AS `has_project_map`,((select `project_knowledge`.`id` from `project_knowledge` where (`project_knowledge`.`project_id` = `t`.`project_id`)) is not null) AS `has_project_knowledge` from (`tickets` `t` join `projects` `p` on((`t`.`project_id` = `p`.`id`))) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `v_tickets_needing_extraction`
--

/*!50001 DROP VIEW IF EXISTS `v_tickets_needing_extraction`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_0900_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`claude_user`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_tickets_needing_extraction` AS select `t`.`id` AS `ticket_id`,`t`.`ticket_number` AS `ticket_number`,count(`cm`.`id`) AS `total_messages`,coalesce(sum(`cm`.`token_count`),0) AS `total_tokens`,sum((case when (`cm`.`is_summarized` = false) then 1 else 0 end)) AS `unsummarized_messages`,coalesce(sum((case when (`cm`.`is_summarized` = false) then `cm`.`token_count` else 0 end)),0) AS `unsummarized_tokens` from (`tickets` `t` left join `conversation_messages` `cm` on((`cm`.`ticket_id` = `t`.`id`))) where (`t`.`status` not in ('closed','completed','archived')) group by `t`.`id`,`t`.`ticket_number` having (`unsummarized_tokens` > 50000) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-01-10 16:50:27

--
-- Default data for daemon_status
--

INSERT INTO `daemon_status` (`id`, `status`, `current_ticket_id`, `current_session_id`, `last_heartbeat`, `started_at`)
VALUES (1, 'stopped', NULL, NULL, NULL, NULL);

--
-- Default admin user (password: admin123)
--

INSERT INTO `developers` (`username`, `password_hash`, `role`, `is_active`)
VALUES ('admin', '$2b$12$szAIZl2ejy.Y5Bj98prT3eZ2/ruBWlHqpwPtBhHj3pPC1Rk3PZsKO', 'admin', 1);

--
-- Default user preferences
--

INSERT INTO `user_preferences` (`user_id`, `language`, `response_style`, `programming_style`, `custom_instructions`)
VALUES ('_default', 'en', 'detailed', '["pragmatic"]', 'Default preferences template')
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

