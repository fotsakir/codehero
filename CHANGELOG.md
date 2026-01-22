# Changelog

All notable changes to CodeHero will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.80.10] - 2026-01-22

### Improved
- **Upgrade Disconnect Handling** - Dashboard now handles server disconnect during upgrade
  - Detects when services restart (expected during upgrade)
  - Automatically polls server until it comes back online
  - Shows "Server restarting..." status with progress
  - Auto-reloads page when server is available again
  - No more "connection lost" errors during successful upgrades

---

## [2.80.9] - 2026-01-22

### Fixed
- **Config Inline Comments** - Daemon now correctly parses config values with inline comments
  - `VALUE=30 # comment` now correctly parses as `30`
  - Preserves `#` in passwords (only strips ` #` with space)
  - Fixes daemon startup failure on fresh installs with commented configs

---

## [2.80.8] - 2026-01-22

### Added
- **Message Pagination** - Ticket detail now loads last 100 messages by default
  - "Load earlier" button to fetch older messages
  - Prevents HTTP/2 protocol errors on tickets with many messages
  - Shows "Showing last X of Y messages" banner

### Fixed
- **Tool Call Display** - Fixed "Loading..." showing for all tool calls on large tickets
  - Root cause was HTTP/2 error when page exceeded size limits
- **Ticket Dependency Order** - Fixed `deps_include_awaiting` flag being ignored
  - Tickets now correctly wait for dependencies in relaxed/strict mode
- **Daemon Startup** - Added retry logic (10 attempts, 5 seconds apart)
  - Prevents startup failure when MySQL isn't ready after VM reboot
- **Dashboard Auto-Refresh** - No longer interrupts upgrade modal

### Changed
- **Systemd Service** - Changed `Wants=mysql.service` to `Requires=mysql.service`
- **Upgrade Script** - Added STEP 7 to update systemd service files

---

## [2.80.7] - 2026-01-22

### Fixed
- **Setup Script Config Files** - Fixed missing `assistant_settings.json` on fresh install
  - Setup now copies `*.json` and `*.conf` files from config directory
  - Upgrade script also copies to both INSTALL_DIR and CONFIG_DIR

---

## [2.80.6] - 2026-01-22

### Added
- **Direct Production Editing Philosophy** - New guidelines in global-context.md
  - Code must be directly editable on production servers
  - Source code format (NOT minified, bundled, or compressed)
  - JavaScript by default, TypeScript only when explicitly requested
  - Readability prioritized over performance

### Changed
- **Default Tech Stack** - Aligned with "no build step" philosophy
  - Dashboards/Admin: PHP + Alpine.js + Tailwind CSS (NOT Vue + Vite)
  - No build tools by default - all code directly editable
  - Libraries: Download locally with curl (NOT CDN)
  - Vue/React only when user explicitly requests (with warning about build step)
- **HeroAgent System Prompt** - Updated PART 4 with same tech stack changes
- **Contexts Consistency** - Both global-context.md and heroagent.py now have identical rules

### Improved
- **HeroAgent Multi-Provider Support** - Enhanced provider configuration
  - Per-provider model aliases (anthropic, gemini, grok, openai, ollama)
  - Updated model mappings: claude-opus-4-5, claude-sonnet-4-5, claude-haiku-4-5
  - Gemini models: gemini-3-pro, gemini-3-flash, gemini-2.5-flash
  - Grok models: grok-4, grok-3, grok-3-mini
  - OpenAI models: gpt-5.2-pro, gpt-5.1, gpt-5-mini
  - Ollama models: llama3.3, qwen2.5-coder
- **Provider Implementations** - Major updates to Gemini and OpenAI providers

---

## [2.80.5] - 2026-01-21

### Improved
- **PrimeVue 4 Instructions** - Updated global-context.md with correct PrimeVue 4 setup
  - Use `@primeuix/themes` package (NOT deprecated `@primevue/themes`)
  - Dark mode with `darkModeSelector: '.p-dark'`
  - Available themes: Aura, Lara, Nora
- **Code Quality Rules** - New section 2.5 in global-context.md
  - Human-readable naming conventions with good/bad examples
  - No obfuscation, proper formatting, meaningful comments
  - Variable, function, class, file, and folder naming guidelines
- **HeroAgent Updates** - System prompt updated with all global context rules

---

## [2.80.4] - 2026-01-21

### Improved
- **AI Link Handling Guidelines** - New section 5.8 in global-context.md
  - Explains relative vs absolute paths for project subfolders
  - Covers HTML links, images, CSS, JS, forms, fetch/AJAX
  - Includes subfolder navigation with `../`
  - Provides `<base>` tag and PHP `$base` alternatives
  - Quick reference table for common scenarios
  - Playwright link verification script
  - Mandatory checklist before completing page tasks

---

## [2.80.3] - 2026-01-21

### Security
- **Command Injection Fix** - Replaced `shell=True` subprocess calls with safe alternatives
  - Use list arguments instead of f-strings for subprocess.run
  - Use `shutil.copytree/copy2` instead of subprocess cp
  - Use subprocess with stdin pipe for mysql imports
  - Fixes 10 critical-severity CodeQL alerts
- **Upload Security** - Added `secure_filename` for all file uploads
  - Prevents path traversal via malicious filenames

---

## [2.80.2] - 2026-01-21

### Security
- **Stack Trace Exposure Fix** - `sanitize_error()` now returns generic messages
  - Error details logged server-side only, not exposed to users
  - Fixes 12 medium-severity CodeQL alerts
- **Path Injection Fix** - Added `validate_project_path()` for all file operations
  - Validates paths are within allowed directories (`/var/www/projects`, `/opt/apps`, `/var/backups/codehero`)
  - Protected endpoints: import, restore, editor, migration backups
  - Fixes 18 high-severity CodeQL alerts

---

## [2.80.1] - 2026-01-21

### Fixed
- **WAF API Bypass** - Full bypass for `/api/` endpoints to prevent false positives
  - Fixes "unexpected token <" error when creating projects via GUI
  - All internal API endpoints now bypass ModSecurity rules
- **Auto-Backup on AI Close** - Fixed `create_backup` method missing from `ClaudeDaemon` class
  - Backups now correctly created when AI reviewer auto-closes tickets

---

## [2.80.0] - 2026-01-21

### Added
- **Project Migration** - Move projects between servers with all data intact
  - Export Full: includes files, database, tickets, and conversations
  - Export Light: same but without conversation history (smaller file)
  - Import Migration: restore on any CodeHero server
  - Simple Import: files + database only (no tickets)
  - Migration backups list with download/delete in project settings
- **Migration Documentation** - New `docs/MIGRATION.md` guide
- **Domain & SSL Documentation** - New `docs/DOMAIN_SETUP.md` guide for Let's Encrypt setup
- **Auto Backup on Ticket Close** - Backup created when AI reviewer auto-closes tickets

### Added
- **WAF Relaxed Rules for Web Projects** - Separate ModSecurity config for port 9867
  - Blocks critical attacks (SQLi, XSS, Command Injection)
  - Allows WordPress, CMS, forms, file uploads without false positives
  - Admin panel (9453) keeps strict rules

### Fixed
- **WAF DELETE Requests** - ModSecurity now allows DELETE method for API endpoints
  - Backup delete, migration backup delete, project delete all work correctly
- **Migration Import Database** - Uses `get_db()` (claude_user) instead of mysql.conf
  - Works on all servers without needing root MySQL password

### Changed
- **Restore Behavior** - Regular backup restore now only restores files, not database
  - Database snapshot kept in backup for reference
  - Prevents accidental data loss from restore operations

---

## [2.79.11] - 2026-01-21

### Fixed
- **Firefox Dashboard Flickering** - Fixed screen flickering every ~5 seconds in Firefox browser
  - Added GPU acceleration CSS to matrix rain background effect
  - Uses `transform: translateZ(0)`, `will-change`, and `backface-visibility: hidden`
  - Forces hardware rendering to prevent software rendering glitches

---

## [2.79.10] - 2026-01-21

### Fixed
- **ModSecurity Optional in Domain Setup** - Fixed `setup_domain.sh` failing on servers without ModSecurity
  - Script now detects if ModSecurity is installed before adding it to nginx config
  - Works on both servers with and without WAF installed

---

## [2.79.9] - 2026-01-21

### Fixed
- **Domain Setup Script apt-get Fix** - Fixed `setup_domain.sh` failing on systems with expired GPG keys
  - Script now ignores apt-get update errors (e.g., expired MySQL repo keys)
  - Continues with package installation even if some repos fail

---

## [2.79.8] - 2026-01-21

### Fixed
- **2FA Management Script Path Fix** - Fixed `manage_2fa.py` failing on production servers
  - Script now checks `/etc/codehero/mysql.conf` first (production path)
  - Falls back to `install.conf` locations if needed
  - No longer crashes with FileNotFoundError on remote servers

---

## [2.79.7] - 2026-01-21

### Added
- **Domain & SSL Setup Script** (`setup_domain.sh`) - Configure domains with Let's Encrypt SSL
  - Interactive menu and CLI mode
  - Admin Panel and Web Apps domain configuration
  - Let's Encrypt certificate management (get, renew, auto-renew)
  - Password protection for Web Apps (external IPs only, localhost/LAN bypass)
  - Both IP and domain access work simultaneously (`server_name _ domain`)
  - Automatic backup before changes
  - Revert to self-signed certificates option
- **Services Restart Script** (`restart_codehero_services.sh`) - Manage all CodeHero services
  - Restart/stop/start all services with one command
  - Status overview of mysql, php-fpm, nginx, codehero-web, codehero-daemon

---

## [2.79.6] - 2026-01-21

### Fixed
- **XSS Security Fix in Ticket Messages** - Fixed HTML injection vulnerability in ticket detail page
  - Messages containing HTML tags (like `<style>`) were being rendered as actual HTML
  - Added `|e` (escape) filter before `|replace` to properly escape HTML entities
  - Prevents unclosed HTML tags from breaking page layout (e.g., sidebar disappearing)

---

## [2.79.5] - 2026-01-21

### Fixed
- **Ticket Detail Sidebar Layout (v2)** - Simplified CSS fix for sidebar appearing below conversation
  - Removed overly complex flex properties that caused rendering issues
  - Simplified `.main` to basic `display: flex`
  - Simplified `.chat-panel` to `flex: 1` without max-width constraint
  - Simplified `.sidebar` to `width: 320px; flex-shrink: 0;`
  - More reliable cross-browser layout behavior

---

## [2.79.4] - 2026-01-21

### Fixed
- **Ticket Detail Sidebar Layout** - Fixed sidebar sometimes appearing below conversation
  - Enforced strict flexbox layout with `flex: 0 0 320px` for sidebar
  - Added `max-width` constraints to prevent layout shifts
  - Chat panel now properly constrained with `calc(100% - 320px)`

---

## [2.79.3] - 2026-01-20

### Fixed
- **Upgrade Script Config Copy** - Fixed upgrade.sh to copy `.json` and `.conf` files from config directory
  - Previously only copied `.md` files, missing `assistant_settings.json`
  - Now properly copies all config file types during upgrade

---

## [2.79.2] - 2026-01-20

### Added
- **Claude Assistant Security Hook** - Protection layer for Claude Assistant sessions
  - Allows system-wide navigation (read access everywhere except sensitive paths)
  - Asks permission for file edits outside safe paths (/home/claude, /var/www/projects, /opt/apps)
  - Blocks access to credentials, SSH keys, database files, and system files
  - Protects backup zip files and .git folders from modification

### Improved
- **Semi-Autonomous Hook Protections** - Enhanced security for ticket execution
  - Added protection for /var/lib/mysql/ (database data directory)
  - Added protection for /var/backups/ directory
  - Blocks backup zip file deletion (codehero-*.zip)
  - Blocks .git folder deletion (rm .git)
  - Blocks destructive database commands (DROP DATABASE, TRUNCATE)
  - Blocks remote code execution patterns (curl|sh, wget|bash)
  - Blocks rm -rf on critical directories (/root, all projects, all apps, backups)

---

## [2.79.1] - 2026-01-20

### Improved
- **Claude Assistant Auto-Load Context** - Context templates now load automatically from backend
  - Dashboard opens with General Assistant context
  - "Plan with AI" opens with Project Planner context
  - "AI Project Assistant" opens with Project Progress context
  - Uses `--system-prompt` flag (loads silently in background)
  - Auto-greets user on session start (no manual "Load Context" needed)

---

## [2.79.0] - 2026-01-20

### Added
- **Semi-Autonomous Execution Mode** - New smart sandbox between autonomous and supervised
  - Auto-approves safe operations (file edits within project, tests, builds, linting)
  - Asks permission for risky operations (package installs, git commits, database migrations)
  - Blocks dangerous operations (system files, .git folder, sudo commands)
  - Real-time permission banner via WebSocket (no page refresh needed)
- **"Approve All Similar" Feature** - One-click approval for similar future operations
  - Approve `npm install express` → auto-approves all future `npm install` commands
  - Pattern-based matching stored in database per ticket
  - Hook reads approved patterns and auto-allows matching operations
- **PreToolUse Hook System** - Claude Code hooks for intelligent permission filtering
  - `semi_autonomous_hook.py` - Evaluates each tool request
  - Returns allow/deny/ask decisions based on safety rules
  - Environment variables for project path and ticket ID

### Improved
- **Execution Mode Selection** - Now offers 3 modes: autonomous, semi-autonomous, supervised
- **Documentation** - Comprehensive execution modes guide in USER_GUIDE.md
- **Claude Assistant Context** - Updated with semi-autonomous mode instructions

---

## [2.78.0] - 2026-01-20

### Added
- **ModSecurity WAF** - Web Application Firewall with OWASP Core Rule Set
  - New `setup_waf.sh` script for easy installation
  - Protection against SQL injection, XSS, command injection
  - OWASP Top 10 attack prevention
  - Custom exclusions for CodeHero (WebSocket, Terminal, Editor, API)
- **WAF Setup in Package Manager** - Install WAF from web UI
  - New card in Configuration Scripts section
  - One-click installation with status tracking

### Security
- ModSecurity 3.x with OWASP CRS 3.3.5 (~2,800 rules)
- Automatic blocking mode enabled
- Protects Admin Panel (9453), Projects (9867), phpMyAdmin (9454)

---

## [2.77.0] - 2026-01-20

### Added
- **Two-Factor Authentication (2FA)** - Optional TOTP-based 2FA with Google Authenticator
  - Enable/disable via command line: `sudo manage-2fa.sh`
  - QR code generation for easy setup
  - Works with any TOTP app (Authy, Microsoft Authenticator, etc.)
- **Account Lockout Protection** - Automatic account lockout after failed login attempts
  - Locks after 5 failed attempts
  - 30-minute lockout period
  - Unlock via script: `sudo manage-2fa.sh unlock`
- **Remember Device** - Skip 2FA on trusted devices
  - Check "Remember this device" when verifying 2FA
  - Valid until end of current month
  - Secure cookie-based with SHA-256 hashed tokens
- **2FA Management Script** - New `manage-2fa.sh` for terminal-based 2FA management
  - Interactive menu or direct commands
  - Commands: enable, disable, reset, unlock, status
- **2FA Documentation** - New `docs/2FA_SETUP.md` with setup guide and troubleshooting

### Security
- Added `auth_settings` table for authentication state
- TOTP secrets stored securely in database
- Failed attempt tracking prevents brute force attacks
- Secure remember token with hash comparison

---

## [2.76.3] - 2026-01-20

### Improved
- **GitHub Default Code Scanning** - Switched to GitHub's default CodeQL setup for simpler maintenance
- **Security Documentation** - Added SECURITY.md with vulnerability reporting guidelines
- **Dependabot** - Added automated dependency update checks

### Fixed
- **README Version URLs** - Fixed outdated download URLs in installation instructions

---

## [2.76.2] - 2026-01-20

### Security
- **Stack Trace Exposure Protection** - Prevent sensitive info leakage in error messages
  - Added `sanitize_error()` helper that logs full errors but returns sanitized messages
  - Scrubs file paths, passwords, and API keys from user-facing error messages
  - All 84 stack trace exposure alerts resolved
- **Path Injection Protection** - Prevent directory traversal attacks
  - Added `safe_join_path()` helper for secure path joining
  - Validates user paths stay within allowed project directories
  - Blocks `..` traversal attempts

---

## [2.76.1] - 2026-01-20

### Security
- **SQL Injection Protection** - Fixed potential SQL injection vulnerabilities in database editor
  - Added `validate_table_name()` and `validate_column_names()` helper functions
  - Table/column names validated against regex and database existence
  - Affects: `get_table_structure`, `get_table_data`, `delete_table_row` endpoints
- **Command Injection Protection** - Fixed command injection vulnerabilities
  - Replaced `os.system()` with `subprocess.run()` using list arguments
  - Added input validation for project codes and file paths
  - Added `repo_path` validation in GitManager constructor

---

## [2.76.0] - 2026-01-20

### Added
- **Smart Retry Cooldown System** - Intelligent handling of API rate limits and errors
  - Rate limit errors (429, overloaded): Wait 30 minutes before retry, no retry count increment
  - Other errors: Wait 5 minutes between retries (max 3 retries)
  - New `retry_after` column tracks when ticket can be retried
  - Daemon automatically skips tickets in cooldown period
  - Prevents hammering the API during rate limit periods

---

## [2.75.1] - 2026-01-20

### Fixed
- **Duplicate Project Code Detection** - Prevents creating projects with existing codes
  - Web Panel: Shows error message with existing project name
  - MCP/Planner: Auto-generates unique code and warns user (e.g., `TEST` → `TEST1`)
  - Returns `code_was_changed` and `original_code` in response

---

## [2.75.0] - 2026-01-20

### Added
- **Delete Project Feature** - Safe project deletion with automatic backup
  - Confirmation modal requires typing project name to confirm
  - Backs up all project paths (web_path, app_path, reference_path)
  - Backs up project database using mysqldump
  - Verifies backup before proceeding with deletion
  - Backups stored in `/var/backups/codehero/deleted-projects/{CODE}_{timestamp}/`
  - Backup directory created automatically on install/upgrade

### Improved
- **Project Code Length** - Increased from 4 to 8 characters for auto-generated codes

---

## [2.74.0] - 2026-01-20

### Added
- **Project Import Feature** - Import existing/legacy projects into CodeHero
  - Support for 3 import methods: ZIP file, Git clone, local path
  - Two modes: "extend" (continue development) and "reference" (read-only template)
  - Reference projects stored at `/opt/codehero/references/{project_code}/`
- **New MCP Tools**
  - `codehero_import_project` - Import projects via ZIP/git/path with extend or reference mode
  - `codehero_analyze_project` - Analyze/re-analyze project to build context maps
- **Git Credentials Support** - Private repository authentication
  - GitHub: Personal Access Token (PAT)
  - GitLab: OAuth2 token
  - Bitbucket: App password with username
- **Combined Path Analysis** - Projects can have both web_path AND app_path
  - Smart analysis combines both paths with [web]/[app]/[reference] labels
  - Entry points and tech stack detected from all paths
- **Reference Path Context** - Daemon injects reference_path info into AI prompts
  - AI knows to READ from reference path, not modify it

- **Smart Context Tree Refresh** - Project maps refresh at ticket start/resume
  - Supports all 3 paths: web_path, app_path, reference_path
  - Fast refresh (~20-60ms) using tree command
  - New files automatically detected between sessions
- **Library Documentation System** - Per-project knowledge base for external libraries
  - AI creates mini-manuals in `.codehero/docs/{library}/`
  - Asks user for official documentation sources (no guessing)
  - Tags for easy search, grows over time
  - Works like "virtual MCP" for API knowledge

### Improved
- **Global Context** - Updated with reference_path documentation and Library Docs (PART 9)
- **Platform Knowledge** - Added new import/analyze tools
- **Project Template** - Added "Existing Code" section for imports
- **Assistant CLAUDE.md** - Added import workflow, git credentials guide, and project planning flow

---

## [2.73.3] - 2026-01-19

### Fixed
- **Git Auto-Init for Project Planner** - Projects created via MCP/Project Planner now automatically initialize Git repository with .gitignore

---

## [2.73.2] - 2026-01-19

### Added
- **UI Quality Enforcement** in global-context
  - Mandatory screenshots before completing UI tasks (desktop + mobile)
  - Common UI killers checklist (giant padding, oversized icons, etc.)
  - Good sizing reference table
  - Visual quality checklist (8 points)
  - Simple rule: UI change = test both viewports, no exceptions

---

## [2.73.1] - 2026-01-19

### Added
- **Default Tech Stack** in global-context
  - Vue 3 + PrimeVue for complex dashboards/admin panels
  - HTML + Tailwind + Alpine.js for landing pages
  - User preference always overrides defaults
- **Local Libraries Rule** - Download libraries locally, no CDN (except Google Maps, Fonts)
- **Upgrade Safety Check** - Prevents running upgrade.sh from /opt/codehero
- **ASK Behavior Clarified** - AI proceeds autonomously, asks only when truly stuck

---

## [2.73.0] - 2026-01-19

### Added
- **Production-Ready Global Context** - Comprehensive rewrite for autonomous AI coding
  - Reorganized into 7 logical parts (Critical Rules → Writing Code → Finishing)
  - Reduced from 1800+ lines to 516 lines (70% smaller, same coverage)
  - All content in English for consistency
  - Clear ❌/✅ examples for every rule

### New Rules Added
- **Timeouts** - All external calls must have timeouts
- **Transactions** - All-or-nothing database operations
- **Idempotency** - Safe to run operations multiple times
- **Race Conditions** - Atomic operations to prevent data corruption
- **Null Checks** - Defensive programming patterns
- **Password Hashing** - Never plain text (bcrypt required)
- **Database Constraints** - FK, unique, not null enforcement
- **Atomic File Writes** - Prevent corrupted files
- **Resource Cleanup** - Context managers for connections/files
- **Retry Logic** - Exponential backoff for external services
- **Date/Time** - Always UTC internally
- **UTF-8** - Encoding everywhere
- **Pagination** - Never unlimited queries
- **Config Defaults** - Fail fast or use defaults

### Removed
- Git workflow section (handled automatically by daemon)

---

## [2.72.7] - 2026-01-19

### Fixed
- **Missing Messages Fix** - Drain stdout buffer after process ends to capture final messages

### Added
- **Enhanced Global Context** - Comprehensive coding guidelines for AI
  - Code Comments & Search Tags (@TODO, @FIXME, #hashtags)
  - Error Handling rules (no silent failures)
  - Verify Before Completing checklist
  - Naming Conventions
  - Debug Workflow
  - Visual Consistency (UI Polish)
  - Self-Documenting Modules with API docs

---

## [2.72.6] - 2026-01-19

### Fixed
- **Upgrade Script Reliability** - Removed `set -e` to prevent premature exit on minor errors
  - Script no longer fails on non-critical warnings
  - Better error handling for each step

### Improved
- **Smart Migration Logic** - Migrations now only run between current and target version
  - Skips migrations older than current version (no re-running old migrations)
  - Skips migrations newer than target version (future migrations)
  - Prevents duplicate migration attempts on repeated upgrades

---

## [2.72.5] - 2026-01-19

### Added
- **Protected Paths** - Added security rules to prevent tickets from modifying system files
  - Tickets cannot modify `/opt/codehero/`, `/etc/codehero/`, `/var/backups/codehero/`
  - Tickets cannot modify nginx, systemd, or Claude CLI configuration
  - Clear instructions for handling 403 errors and permission requests
  - Workspace limited to project directories only

### Improved
- **Playwright Testing URLs** - Fixed documentation for web project testing
  - Correct URL format: `https://127.0.0.1:9867/{folder_name}/`
  - Added `ignore_https_errors=True` requirement for self-signed certificates
  - Example code for both Python and playwright.config.js

---

## [2.72.4] - 2026-01-19

### Fixed
- **STUCK Detection Delay** - Fixed bug where STUCK detection was delayed by up to 57+ minutes
  - Root cause: `readline()` blocks indefinitely waiting for newline character
  - When Claude writes partial data without `\n`, stuck check never executes
  - Now properly continues loop to check stuck timeout when no complete line available
  - STUCK should now be detected within the configured 30-minute timeout

---

## [2.72.3] - 2026-01-18

### Fixed
- **Ticket Detail Sidebar Layout** - Fixed sidebar sometimes appearing below conversation
  - Added `flex-shrink: 0` and `min-width: 320px` to sidebar
  - Added `flex-wrap: nowrap` to main container
  - Sidebar now stays fixed on the right side

---

## [2.72.2] - 2026-01-18

### Fixed
- **Watchdog Process Kill** - Fixed bug where watchdog couldn't kill stuck Claude processes
  - Root cause: SQL query didn't include `project_id` in SELECT
  - Watchdog marked ticket as STUCK but process kept running
  - Now properly terminates Claude process when stuck detected

---

## [2.72.1] - 2026-01-18

### Added
- **MCP Auto-Configuration** - Setup now creates MCP config automatically
  - Creates `/home/claude/.claude.json` with MCP server config
  - Creates `/home/claude/CLAUDE.md` with assistant instructions
  - No manual MCP configuration needed after installation

### Improved
- **Assistant Templates** - Stronger emphasis on MCP tool usage
  - All 3 templates now explicitly require MCP tools
  - Clear examples of how to call each tool
  - "DO NOT use curl/HTTP" instruction added

---

## [2.72.0] - 2026-01-18

### Added
- **Auto-Review System** - Intelligent ticket progression for relaxed mode
  - Uses Claude Haiku (via CLI) to classify completed tickets
  - Auto-closes tickets when AI reports "Task completed"
  - Keeps tickets open when AI asks questions or reports errors
  - 5-minute delay before review (configurable via `AUTO_REVIEW_DELAY_MINUTES`)
  - No extra API key needed - uses same auth as Claude Code
- **Review Retry Logic** - Handles Haiku call failures
  - Retries up to 10 times with 5-minute intervals
  - Notifications on review failure after max retries
- **Awaiting Reason Tracking** - New `awaiting_reason` column
  - Values: completed, question, error, stopped, permission, deps_ready
  - Better visibility into why ticket is waiting

### Improved
- **Relaxed Mode** - Now waits for Haiku auto-close before starting next ticket
  - Previously started next ticket immediately on `awaiting_input`
  - Now waits for actual `done` status after Haiku review
- **Kill Switch** - Sets `awaiting_reason='stopped'` to prevent auto-review
- **User Messages** - Cancel pending review and reset retry counter

---

## [2.71.0] - 2026-01-18

### Added
- **Voice-to-Text** - Speech input for Claude Assistant
  - Click microphone button to start recording
  - Multi-language support with dropdown selector
  - Auto language detection or manual selection (EN, GR, DE, FR, ES, etc.)
  - Auto-stop after 10 seconds of silence
- **Context Templates** - Pre-configured assistant modes
  - General Assistant - Platform help, troubleshooting, admin tasks
  - Project Planner - Design projects with tickets and dependencies
  - Project Progress - Check project status, retry failed tickets
  - Auto-selects appropriate template based on entry point
- **File Upload** - Share files with Claude Assistant
  - Upload any file (zip, txt, xlsx, etc.) via paperclip button
  - Files saved to `/tmp/claude-uploads/`
  - Auto-sends message to Claude with file path
  - Claude reads and analyzes uploaded files

### Improved
- **Claude Assistant UI** - Better user guidance
  - Clear instructions for loading context
  - Warning message when context not loaded
  - Visual feedback for loaded context status
- **Input Area** - Enhanced controls
  - Text input with Send button
  - Voice recording with language selector
  - File upload button

---

## [2.70.0] - 2026-01-17

### Added
- **Execution Modes** - Control how tickets run
  - `autonomous` - Full access, no permission prompts (default)
  - `supervised` - Asks for user approval before write/edit/bash operations
  - Per-ticket or project-wide default setting
- **Relaxed Mode** - Control dependency behavior
  - `strict` (default) - Wait for dependencies to fully complete
  - `relaxed` - Continue even if dependency is awaiting user input
  - Ask "Relaxed or strict?" when creating multiple tickets

### Improved
- **Claude Assistant** - Now asks about execution mode and relaxed mode
- **Plan with AI** - Includes execution mode and relaxed mode options
- **MCP Tools** - Added `execution_mode` and `deps_include_awaiting` parameters

---

## [2.69.0] - 2026-01-17

### Added
- **Ticket Types** - Categorize work with color-coded badges
  - feature (purple), bug (red), debug (orange), rnd (violet)
  - task (gray), improvement (cyan), docs (green)
- **Ticket Sequencing** - Define execution order with sequence numbers
  - Lower numbers run first (1, 2, 3...)
  - Sequenced tickets run before non-sequenced
- **Ticket Dependencies** - Make tickets wait for others to complete
  - Multi-select dependencies in ticket form
  - Option to count "awaiting input" as completed (relaxed mode)
- **Sub-tickets** - Break complex tasks into smaller pieces
  - Parent/child ticket hierarchy
  - Parent tracks overall progress
- **Auto-Retry** - Failed tickets automatically retry up to 3 times
  - Configurable max_retries per ticket
  - retry_count tracking
- **Start Now Button** - Jump ticket to front of queue
  - Sets is_forced=TRUE for immediate processing
  - For sub-tickets, starts parent instead
- **Progress Dashboard** - Visual project progress at `/project/<id>/progress`
  - Completion percentage with progress bar
  - Ticket counts by status and type
  - Sequence flow visualization
  - Built-in AI Project Assistant
- **AI Project Assistant** - Context-aware help from progress page
  - Knows current project, can list tickets, retry failed, add new
  - Quick action buttons for common tasks
- **Bulk Ticket Creation** - MCP tool `codehero_bulk_create_tickets`
  - Create multiple tickets with sequence and dependencies
  - Used by "Plan with AI" for project planning
- **MCP Tools** - New tools for ticket management
  - `codehero_start_ticket` - Start ticket immediately
  - `codehero_retry_ticket` - Retry failed ticket
  - `codehero_delete_ticket` - Delete a ticket

### Improved
- **Package Manager** - Enhanced with collapsible categories
  - Configuration Scripts section at top (expanded by default)
  - All other categories collapsed by default
  - "Package Manager Guide" with detailed instructions
  - Documentation for each Configuration Script (Android, LSP, Windows)
  - Config file locations and setup explanations
- **New Ticket Form** - Redesigned with better UX
  - Wider modal (900px) with 2-column layout
  - Compact tips bar with link to documentation
  - 4-column row for Type, Priority, Sequence, AI Model
  - All options visible without scrolling
- **Edit Ticket Form** - Quick reference bar with hints
- **Documentation** - Comprehensive ticket guide in USER_GUIDE.md
  - Ticket types, sequencing, dependencies explained
  - Tips for writing good tickets with examples
- **Features Page** - New "Advanced Ticket System" section
  - 8 feature cards showcasing ticket capabilities
- **Auto-refresh** - Ticket list in split view refreshes every 15 seconds
- **WebSocket Support** - Fixed with eventlet for reliable connections

## [2.68.0] - 2026-01-17

### Added
- **Tickets Split View** - New multi-ticket workspace at `/project/<id>/tickets`
  - Compact ticket list on left panel (280px, resizable)
  - Full ticket detail view on right panel (iframe-based)
  - All ticket features work: chat, WebSocket updates, actions
  - Status filter dropdown (Active, All, Open, In Progress, etc.)
  - Keyboard navigation: Arrow keys to switch tickets, Enter to open in new tab
  - Visual status indicators with colored dots
- **View Tickets Button** - Quick access from project detail page header
- **View Tickets Link** - Added to project cards in projects list
- **API Endpoint** - New `/api/ticket/<id>` returns ticket details with messages

### Improved
- **Embedded Ticket View** - Compact header when viewed in split view
  - Shows ticket number, title, status
  - "Back to Project" navigates parent window correctly
- **New Ticket Flow** - Auto-opens modal when navigating with `#new-ticket` hash
- **iframe Communication** - postMessage for reliable parent-child navigation

## [2.67.0] - 2026-01-16

### Added
- **Modular Upgrade System** - Complete rewrite of upgrade.sh
  - Individual upgrade scripts per version (`upgrades/2.61.0.sh`, `2.63.0.sh`, etc.)
  - Automatic detection and execution of pending upgrades
  - Tracks applied upgrades in `/etc/codehero/applied_upgrades`
  - Skips already-applied migrations (safe to run multiple times)
- **Real-time Upgrade Console** - Live output streaming in admin panel
  - WebSocket-based streaming (no more fixed 45-second timeout)
  - Color-coded output ([OK] green, [INFO] blue, [WARN] yellow, [ERROR] red)
  - Auto-reload page on successful completion
- **AI-Powered Upgrade Troubleshooting** - "Ask AI to fix" button when upgrade fails
  - Sends error log to Claude for analysis
  - Shows problem description and fix commands
  - One-click execution of suggested fixes
  - "Run All Commands" for batch execution

### Improved
- **Upgrade Safety** - Better version mismatch detection
  - Warns if zip filename doesn't match VERSION file
  - Clear downgrade warnings with confirmation
- **Database Migrations** - Separate from system upgrades
  - SQL migrations in `database/migrations/`
  - System upgrades in `upgrades/` (bash scripts)

### Technical
- New API endpoints: `/api/ai-fix-upgrade`, `/api/run-fix-command`
- WebSocket events: `join_upgrade`, `start_upgrade`, `upgrade_output`, `upgrade_complete`
- Security: Blocked dangerous commands in fix execution

## [2.66.0] - 2026-01-15

### Added
- **Voice Input (Speech-to-Text)** - Microphone button for voice input
  - Ticket chat - speak instead of typing messages to Claude
  - Project creation - voice input for project name and description
  - New ticket - voice input for ticket description
  - Uses browser's Web Speech API (Chrome, Edge, Safari)
  - Visual feedback with red pulsing animation while recording
  - Tooltip hint "Recording... Click to stop"
  - Auto-stops after 10 seconds of silence

## [2.65.0] - 2026-01-15

### Added
- **phpMyAdmin Integration** - Database management tool alongside built-in editor
  - Auto-login with project database credentials (signon authentication)
  - phpMyAdmin button in Project Detail page
  - phpMyAdmin button in Ticket Detail page
  - Nginx reverse proxy on port 9454 (HTTPS)
  - Automatic installation in setup.sh and upgrade.sh
- **Git History in Ticket Page** - Access Git history directly from tickets

### Improved
- **Chat Auto-scroll** - Only auto-scrolls when user is at bottom of conversation
- **Live Preview Scroll** - Preserves scroll position when preview refreshes
- **Consistent Button Styling** - All action buttons now have uniform appearance

### Technical
- Safe phpMyAdmin installation (continues if fails with `|| true`)
- Conditional signon config (only if phpMyAdmin directory exists)

## [2.64.1] - 2026-01-15

### Fixed
- Prevent personal email leakage in composer.json/package.json (added global context rule)
- Set neutral git config (noreply@codehero.local) for project commits
- Fixed author URL in README (smartnav.eu → routeplanner.gr)

## [2.64.0] - 2026-01-15

### Added
- **MCP Server for Claude Assistant** - Claude can now manage projects and tickets directly
  - `codehero_list_projects` - List all projects with stats
  - `codehero_get_project` - Get project details and tickets
  - `codehero_create_project` - Create new projects
  - `codehero_list_tickets` - List tickets for a project
  - `codehero_get_ticket` - Get ticket details and conversation
  - `codehero_create_ticket` - Create new tickets
  - `codehero_update_ticket` - Update ticket status/priority, add replies
  - `codehero_dashboard_stats` - Get dashboard overview

### New Capability
- Claude Assistant can now autonomously manage the platform
- Create projects based on user conversations
- Create and assign tickets for work items
- Monitor project progress and status
- Respond to ticket updates programmatically

## [2.63.0] - 2026-01-15

### Added
- **Git Version Control** - Automatic version control for all projects
  - Auto-commit when AI completes work (ticket → awaiting_input)
  - Commit message format: `[TICKET-NUM] Title` with metadata
  - Git History page with commit timeline and diff viewer
  - Rollback to any previous commit with confirmation
  - Git context provided to Claude (recent commits, changed files)
  - Smart .gitignore based on project type (PHP, Python, Node, .NET, etc.)
- **New Database Tables**
  - `project_git_repos` - Track Git repositories per project
  - `project_git_commits` - Store commit history with ticket links
- **New API Endpoints**
  - `GET /project/<id>/git` - Git history page
  - `GET /api/project/<id>/git/commits` - List commits
  - `GET /api/project/<id>/git/diff/<hash>` - View commit diff
  - `POST /api/project/<id>/git/rollback` - Rollback to commit
  - `POST /api/project/<id>/git/init` - Initialize Git for existing projects
- **Project Integration**
  - Git initialized automatically on project creation
  - "Git History" button in project detail page
  - Git status shown in project overview

### Changed
- Projects now have `git_enabled` flag (default: true)
- Daemon includes Git context in Claude prompts for self-correction

## [2.61.2] - 2026-01-15

### Fixed
- **Setup Script** - Changed `systemctl start` to `systemctl restart` for nginx, php-fpm, and codehero services
  - Fixes issue where admin panel was not accessible after fresh install until reboot
  - Services now properly reload configs immediately after installation

## [2.61.1] - 2026-01-15

### Added
- **Path Tabs in Editor** - Switch between web_path and app_path in code editor
- **Path Tabs in Ticket** - File uploads support both paths with tab selection
- **Path Tabs in Project Settings** - File browser supports both paths

### Fixed
- **Migration Scripts** - Made 2.61.0 and 2.61.1 migrations idempotent (safe to run multiple times)
- **Schema Sync** - Updated schema.sql with all new fields for clean installs

## [2.61.0] - 2026-01-15

### Added
- **Android Emulator Support** - Full Android development environment
  - Server-based emulator using Redroid (Android 15 in Docker)
  - Web-based screen mirroring via ws-scrcpy (port 8443)
  - ADB integration for APK install, logs, screenshots
  - Remote ADB support for physical devices
  - Setup script: `setup_android.sh`
- **.NET / ASP.NET Core Support** - Windows development on Linux
  - .NET 8 SDK with auto Nginx reverse proxy
  - Systemd services for each .NET app with auto-restart
  - Automatic port allocation (5001+)
  - PowerShell 7, Wine 11, Mono 6.12 included
  - Setup script: `setup_windows.sh`
- **Mobile Frameworks** - New project types
  - Capacitor.js (Ionic)
  - React Native
  - Flutter (with SDK)
  - Native Android (Gradle)
- **Smart Context** - Framework-specific context for Claude
  - Android development commands and ADB usage
  - .NET commands and service management
- **Documentation** - Updated README, INSTALL.md, website
  - New "Supported Platforms" section
  - Setup instructions for Android and .NET environments

### Changed
- **Project Types** - Added 'dotnet' to project_type ENUM
- **Projects Table** - New fields: dotnet_port, android_device_type, android_remote_host, android_remote_port, android_screen_size

## [2.60.4] - 2026-01-14

### Added
- **PHP Extensions** - Added sqlite3, imap, apcu, igbinary, tidy, pgsql to setup.sh

### Fixed
- **OpenLiteSpeed Paths** - Fixed old fotios-claude paths to codehero in OLS configs
- **PID Directory Permissions** - Fixed /var/run/codehero ownership in upgrade.sh
- **PHP OPcache** - Disabled opcache for development in PHP 8.3 and 8.4

## [2.60.3] - 2026-01-13

### Added
- **Database Migration** - Added daemon_logs table for /stop, /skip, /done commands

### Fixed
- **Kill Switch Commands** - Fixed missing daemon_logs table error

## [2.60.2] - 2026-01-13

### Fixed
- **Website Download Link** - Updated to point to current version

## [2.60.1] - 2026-01-13

### Fixed
- **Website Download Link** - Updated manual install link to v2.60.0

## [2.60.0] - 2026-01-13

### Added
- **Favicon** - New superhero-themed favicon for admin panel and website
- **PWA Support** - Admin panel can now be installed as Progressive Web App
  - manifest.json with app icons (192x192, 512x512)
  - Service worker for offline support
  - Apple touch icon for iOS
- **CodeHero PRO Section** - Added "Coming Soon" PRO features section to landing page
  - Multi-Agent Orchestration
  - AI Code Review
  - Team Collaboration
  - Advanced Analytics
  - Enterprise SSO
  - AI Ecosystem (OpenAI, Gemini, local LLMs)
- **Claude Activation Guide** - Comprehensive documentation in README
  - Subscription activation (Pro/Max) via Web Terminal and Linux Terminal
  - API Key activation via Dashboard and Linux Terminal
  - Verification and deactivation instructions

### Changed
- **Activation Modal** - Simplified with clear instructions and "Open Terminal" button
- **Dashboard Auto-Refresh** - No longer closes modals when refreshing
- **License Status** - Improved detection for both subscription and API key methods

### Fixed
- **Token Sync** - OAuth tokens from .credentials.json now sync to .env for daemon

## [2.59.2] - 2026-01-13

### Changed
- **Stable Release** - Reverted to 2.58.0 codebase for stability
- Removed experimental activation popup and keyring features

## [2.58.0] - 2026-01-13

### Changed
- **Login Page Icon** - Replaced robot emoji with CodeHero hero icon on admin panel login

## [2.57.0] - 2026-01-13

### Changed
- **Website Mobile Layout** - Reordered hero section for mobile (CodeHero title first, animation below)
- **Website Desktop Layout** - Same order as mobile for consistency
- **Hero Icon Mobile** - Centered above title on mobile screens
- **Family Emoji Fix** - Changed to 🏠 for better cross-platform support
- **Multipass Scripts** - Simplified installation, removed background processes for stability
- **Install Commands** - Simplified to `curl | bash` format
- **Resources** - Reduced VM resources (4GB RAM, 2 CPUs) for better compatibility
- **Timeout** - Increased to 1 hour for slower connections

## [2.56.0] - 2026-01-12

### Changed
- **New Dual License** - Replaced MIT with Community + Commercial license
  - Free: Personal use, education, non-profits, startups < €100K revenue
  - Paid: Commercial use for organizations ≥ €100K revenue
  - Attribution required for all users

## [2.55.2] - 2026-01-12

### Changed
- **Website Install Box** - Added copy buttons to all installation code blocks
- **Multipass URLs** - Updated to download-then-execute format for better compatibility

## [2.55.1] - 2026-01-12

### Changed
- **README Branding** - Added CodeHero character icon (cape, mask, glowing eyes)
- Updated tagline from "Never Sleeps" to "Never Rests"

## [2.55.0] - 2026-01-12

### Changed
- **Website Hero Animation** - New 24-hour story animation showing CodeHero working while you do other things
  - Dynamic scenes: working together, coffee break, lunch, exercise, family time, sleep
  - Consistent layout width throughout all transitions
  - Smooth fade transitions between scenes
- **GitHub Pages Improvements**
  - Added `.nojekyll` file to fix sitemap processing
  - Fixed sitemap.xml format for Google Search Console

## [2.54.0] - 2026-01-12

### Changed
- **Complete Infrastructure Rebrand** - Full migration from `fotios-claude` to `codehero`
  - Renamed production path: `/opt/fotios-claude` → `/opt/codehero`
  - Renamed log path: `/var/log/fotios-claude` → `/var/log/codehero`
  - New service names: `codehero-web` and `codehero-daemon`
  - Updated all systemd service files
  - Services enabled for auto-start on boot

## [2.53.0] - 2026-01-12

### Changed
- **Admin Panel Rebrand** - All pages now show "CodeHero" instead of "CodeHero"
  - Updated page titles across all templates
  - Updated navigation headers
  - Updated login page branding
  - Updated Claude Assistant help text
- **Repository Rename** - Changed from "Claude-AI-developer" to "codehero"
  - Updated all GitHub URLs across documentation and scripts

## [2.52.0] - 2026-01-12

### Added
- **Rebrand to CodeHero** - New name and tagline: "The Developer That Never Sleeps"
- **Comprehensive Installation Guides**
  - WSL2 guide with full troubleshooting
  - Multipass guide for macOS/Linux
  - "How to Find Your VM's IP Address" section for all platforms
  - "Start, Stop & Delete VMs" section for all platforms
- **Live Installation Progress** - Multipass installers now show real-time installation output
- **Daemon Startup Check** - Installers wait for Multipass daemon to be ready

### Fixed
- **macOS Installer**: Start Multipass daemon after installation
- **Linux Installer**: Add daemon startup check
- **Cloud-init**: Install Claude Code without trying to run it (fixes non-interactive error)
- **Update Countdown**: Increased from 30 to 45 seconds for more reliable reload

### Changed
- **Website**: New branding with CodeHero name and improved tagline
- **Usage Analytics**: Added to Core Features on website and README

## [2.51.0] - 2026-01-12

### Fixed
- **WSL2 Installer**: Complete rewrite for reliable Windows installation
  - Uses `--exec` flag to bypass interactive OOBE user creation prompt
  - Enables systemd in WSL (required for services to run)
  - Sets root as default user automatically
  - All commands now work without interactive prompts

### Changed
- **Website**: Reorganized installation options
  - Windows: WSL2 as primary method
  - Linux/macOS: Multipass
  - Removed contact email from website

## [2.50.5] - 2026-01-12

### Changed
- **Multipass VM Specs**: Increased resources for better performance
  - RAM: 4GB → 6GB
  - Disk: 40GB → 64GB
  - CPUs: 2 → 4

## [2.50.4] - 2026-01-12

### Improved
- **Windows Batch File**: Now ensures services are running inside VM
  - Runs `systemctl start` for web and daemon services after VM boots
  - Increased boot wait time to 15 seconds
  - Guarantees dashboard is accessible when browser opens

## [2.50.3] - 2026-01-12

### Improved
- **Multipass Installers**: Added clear message that setup takes 10-15 minutes
  - Shows "VM Created Successfully" instead of "Installation Complete"
  - Explains that software is still installing inside the VM
  - Provides commands to check installation progress
  - Updated for Windows, macOS, and Linux installers

## [2.50.2] - 2026-01-12

### Fixed
- **Windows Multipass Installer**: Desktop shortcuts now work reliably
  - Smart batch file gets IP dynamically when run (doesn't depend on install-time IP)
  - Batch file auto-starts VM if not running, then opens dashboard
  - URL shortcut only created if valid IP detected at install time

## [2.50.1] - 2026-01-12

### Fixed
- **Auto-Update**: Fixed upgrade process killing itself during service restart
  - Upgrade now runs in background with nohup
  - Web service stays running during file copy (only daemon stops)
  - Services restart at the end instead of stop+start
  - 30-second countdown before auto-reload

### Improved
- **Update Badge**: More visible with emoji and gradient background

## [2.50.0] - 2026-01-12

### Added
- **Auto-Update System**: Check and install updates directly from the dashboard
  - Automatic update check on page load
  - Green "Update Available" badge in header when new version exists
  - One-click update installation with progress tracking
  - Downloads latest release from GitHub and runs upgrade.sh
  - Shows release notes before updating

## [2.49.0] - 2026-01-12

### Added
- **WSL2 Installer for Windows**: One-click PowerShell script for Windows users
  - `install-wsl.ps1` - Installs WSL2, Ubuntu 24.04, and runs setup automatically
  - Ideal for Windows users who prefer WSL2 over Multipass VM
  - Creates desktop shortcut to dashboard
- **Website Improvements**:
  - Added Enterprise Services section with consulting/support contact
  - Added Live Preview to features section
  - Reorganized installation sections (Manual, WSL2, Multipass)
  - Updated SEO meta tags and Open Graph descriptions

## [2.48.1] - 2026-01-12

### Fixed
- **Windows IP Detection**: Multiple fallback methods to get VM IP address
  - Method 1: `hostname -I`
  - Method 2: `multipass info` (IPv4 line)
  - Method 3: `multipass list --format csv`
  - Shows manual command if all methods fail

## [2.48.0] - 2026-01-12

### Added
- **Desktop Shortcuts**: Installers create convenient desktop shortcuts
  - Windows: `.url` shortcut + `Start Claude VM.bat` batch file
  - macOS: `.webloc` bookmark + `Start Claude VM.command` script
  - Linux: `.desktop` file + `start-claude-vm.sh` script
- **Windows Home Support**: Full VirtualBox backend for Windows Home edition
  - Auto-detects Windows Home (no Hyper-V)
  - Auto-installs VirtualBox via winget
  - Pre-configures VirtualBox driver before Multipass installation
  - Connection retry logic (5 attempts with 10-second waits)

### Fixed
- **Windows Installer**: Fixed "cannot connect to multipass socket" error
  - Root cause: Multipass started with Hyper-V driver on Windows Home
  - Fix: Write VirtualBox driver to config BEFORE installing Multipass
  - Added service stop/start sequence for proper driver application
- **Timeout Issues**: Increased VM launch timeout to 1800 seconds (30 min)
- **VirtualBox Initialization**: Added 30-second wait for VirtualBox initialization

## [2.47.0] - 2026-01-12

### Added
- **One-Click Multipass Installers**: Install with a single click on any platform
  - `install-windows.ps1` - PowerShell script for Windows
  - `install-macos.command` - Double-click installer for macOS
  - `install-linux.sh` - Shell script for Linux
  - `cloud-init.yaml` - Automatic VM configuration
  - Auto-installs Multipass if not present
  - Auto-detects latest release from GitHub API
- **MULTIPASS_INSTALL.md**: Complete documentation for one-click install

## [2.46.1] - 2026-01-12

### Fixed
- **Telegram Haiku API key**: Pass environment variables to Haiku subprocess
  - API key users: Loads from `~/.claude/.env` and passes via `env=`
  - Subscription users: Already worked (CLI reads credential files)
  - Fixes "Invalid API key" error for Telegram questions

## [2.46.0] - 2026-01-12

### Fixed
- **Ticket regex**: Support project codes with numbers (e.g., TEST30-0001)
  - Changed from `[A-Z]+-\d+` to `[A-Z]+\d*-\d+`
- **Telegram question handler**: Handle None content in conversation messages
- **Log file permissions**: Pre-create log files with correct ownership
  - setup.sh: Creates daemon.log and web.log before services start
  - upgrade.sh: Fixes permissions during upgrade
  - Prevents systemd from creating files as root

## [2.45.0] - 2026-01-12

### Added
- **Telegram Error Feedback**: User-friendly error messages for all scenarios
  - Direct message (not reply): Informs user to reply to notification
  - Invalid ticket number: Guides user to reply to valid notification
  - Ticket not found: Informs ticket may be deleted/archived
- **Question mark flexibility**: "?" works at start OR end of message
  - `?what's wrong` and `what's wrong?` both work as questions

### Changed
- **Documentation**: Prominent "Control from Your Phone" section in README and website
  - New phone control section on website with code example
  - Updated USER_GUIDE with two-way communication instructions

### Fixed
- **Claude CLI path**: Fixed Haiku not working (was missing full path to claude binary)

## [2.44.0] - 2026-01-12

### Added
- **Two-Way Telegram Communication**: Reply to notifications directly from Telegram
  - Reply to any notification to add a message to that ticket
  - Ticket automatically reopens if it was awaiting input
  - TelegramPoller thread polls for replies every 10 seconds
- **Telegram Questions**: Start reply with "?" for quick status checks
  - Get short summary via Claude Haiku without reopening ticket
  - Works in any language (e.g., "?τι δεν πάει καλά")
  - Low-cost, fast responses (~$0.001)
- **Updated TELEGRAM_SETUP.md**: Added two-way communication documentation

## [2.43.0] - 2026-01-12

### Added
- **Telegram Notifications**: Get instant alerts on your phone
  - Notified when Claude needs input (awaiting_input)
  - Notified when tasks fail
  - Notified on Watchdog alerts
  - Settings panel (⚙️) in dashboard for easy configuration
  - Test notification button before saving
  - Auto-restart daemon when settings saved
- **docs/TELEGRAM_SETUP.md**: Complete setup guide for Telegram notifications

## [2.42.0] - 2026-01-12

### Added
- **Multimedia Tools**: Full suite of image, audio, video, and PDF processing tools
  - ffmpeg, ImageMagick, tesseract-ocr (English + Greek), sox, poppler-utils
  - Python: Pillow, OpenCV, pytesseract, pdf2image, pydub
- **docs/INSTALLED_PACKAGES.md**: Complete reference for all installed tools with examples
- **Backup Notification**: UI message when backup is created before ticket processing
- **upgrade.sh**: Auto-installs missing packages during upgrade

### Changed
- **AI Knowledge Base**: Updated PLATFORM_KNOWLEDGE.md and global-context.md with multimedia tools
- **README.md**: Added link to Installed Packages documentation

### Fixed
- **Admin Password**: setup.sh now uses password from install.conf (was using hardcoded hash)

## [2.41.1] - 2026-01-11

### Fixed
- **env_file path**: Use `os.path.expanduser("~")` instead of hardcoded path

### Changed
- **Documentation**: Added remote server sync workflow and restart reminders
  - Always restart services after changes (changes won't be visible otherwise)
  - Remote server credentials provided by user when needed

## [2.41.0] - 2026-01-11

### Added
- **Message Queue**: Messages sent while AI is working are queued and combined
  - Multiple messages collected in visible queue box
  - Combined into single message when AI finishes
  - Delete button to clear queue before sending
  - No more lost messages during AI execution
- **Real-time Status Updates**: Ticket status changes broadcast via WebSocket
  - Status badge updates automatically
  - "Awaiting Input" banner appears when AI finishes
  - No manual refresh needed

### Changed
- **Visual Verification promoted**: Added to README and website as key feature
  - "Claude sees what you see" - screenshot analysis with Playwright

### Fixed
- **Duplicate messages**: Fixed messages appearing twice in conversation
- **Removed debug logging**: Cleaned up console.log and print statements

## [2.40.1] - 2026-01-11

### Added
- **Project Knowledge Auto-Update**: Summary now updates project_knowledge table
  - `important_notes` → `known_gotchas`
  - `problems_solved` → `error_solutions`
  - `decisions` → `architecture_decisions`
  - Learnings from one ticket help all future tickets in the same project

## [2.40.0] - 2026-01-11

### Added
- **"Create Summary" button**: Manually compress conversations to save tokens
  - Uses Haiku AI (~$0.01-0.05) to create intelligent summary
  - Keeps decisions, problems solved, and important notes
  - Reduces token usage on future requests
  - Button in ticket sidebar under Actions

## [2.39.0] - 2026-01-11

### Added
- **"See with your eyes" button**: New button in ticket detail page
  - Claude takes a screenshot using Playwright and analyzes the page visually
  - No need to describe visual issues - Claude sees them directly
- **AI Behavior Guidelines**: New section in global context
  - Claude asks clarifying questions before starting unclear tasks
  - Automatic Playwright usage when user mentions visual issues
  - Instructions for visual verification workflow

## [2.38.0] - 2026-01-11

### Changed
- **New Core Message**: "Not an AI that answers questions. An AI that builds software."
  - Clearer differentiation from chat-based AI tools
  - Focus on real development environment and control
  - "For beginners, it removes complexity. For developers, it removes noise."
- Updated README, website hero, and all meta tags

## [2.37.1] - 2026-01-11

### Fixed
- **Playwright**: Added missing system dependencies for fresh installations
  - Chromium now works out-of-the-box on new Ubuntu installs
  - Added libnss3, libgbm1, fonts, and other required libraries

## [2.37.0] - 2026-01-10

### Changed
- **New messaging**: Emphasize long-running unattended development
  - "Set it. Forget it. Wake up to working code."
  - "Master code from a new perspective"
  - Updated README, website, and all meta tags
- **Philosophy shift**: From "autonomous agent" to "unattended development"
  - Focus on Claude working for hours while you sleep
  - You architect, Claude builds

## [2.36.0] - 2026-01-10

### Added
- **Pop-out File Explorer**: New standalone window for browsing project files
  - Accessible from Project Detail page with "Pop Out" button
  - Full file browser functionality in a separate window
- **Pop-out Code Editor**: Button to open editor in new window
  - Opens from both Project Detail and Editor pages
  - Allows multi-window workflow

### Fixed
- **Daemon logs**: Fixed duplicate log entries (removed redundant print statements)

## [2.35.0] - 2026-01-10

### Changed
- **Screenshots**: Updated all screenshots with fresh data
  - Dashboard, Projects, Tickets, Console, Terminal
  - Project Detail, Ticket Detail, History
  - Claude Assistant, Code Editor
  - User Guide screenshots in docs/guide/

## [2.34.0] - 2026-01-10

### Changed
- **Database Schema**: Complete baseline schema.sql with all current features
  - Added `ai_model` column to projects and tickets tables
  - Added Smart Context tables (user_preferences, project_maps, project_knowledge, conversation_extractions)
  - Added all views (v_ticket_context, v_projects_needing_map, v_tickets_needing_extraction)
  - Removed user-created tables from schema
- **Migrations**: Cleaned up - this is the initial release baseline
  - Migrations only run via upgrade.sh for future updates
  - schema.sql is the complete database for fresh installs
- **Documentation**: Updated CLAUDE_DEV_NOTES.md with migration workflow

## [2.33.0] - 2026-01-10

### Added
- **Platform Help Mode**: Claude Assistant can now help with platform questions
  - New "Platform Help" button opens help mode
  - Auto-loads PLATFORM_KNOWLEDGE.md with full platform documentation
  - Claude can help with troubleshooting, code, and configuration
  - Knows file locations, services, database queries, and more
- **PLATFORM_KNOWLEDGE.md**: Comprehensive knowledge base for Claude Assistant
  - Platform architecture and components
  - File locations (source and production)
  - Service commands and database queries
  - All v2.32.0 features documented
  - Troubleshooting guides
  - Code architecture documentation
- **Blueprint Planner Improvements**: Updated paths for production deployment

### Changed
- **setup.sh**: Now copies all documentation files to /opt/codehero/
  - config/*.md files for Claude Assistant
  - CLAUDE_OPERATIONS.md, CLAUDE_DEV_NOTES.md, CLAUDE.md
  - Full docs/ directory with USER_GUIDE.md
- **upgrade.sh**: Same documentation copying as setup.sh
- **USER_GUIDE.md**: Added sections for Web Terminal, Claude Assistant, AI Project Manager
- **CLAUDE_OPERATIONS.md**: Added v2.32.0 features section

## [2.32.0] - 2026-01-10

### Added
- **Web Terminal**: Full Linux terminal in the browser
  - New "Terminal" menu item in navigation
  - Real-time shell access via WebSocket
  - xterm.js with 256-color support
  - Popup window support for multi-monitor setups
  - Runs as user `claude` with sudo access
  - Auto-cleanup on disconnect
- **Claude Assistant Enhancements**:
  - AI model selection (Opus/Sonnet/Haiku) with Sonnet as default
  - Popup window support ("New Window" button)
  - Model indicator in status bar
  - Model locked during active session

## [2.31.0] - 2026-01-10

### Added
- **Instant Command Feedback**: Commands (/stop, /skip, /done) show immediately
  - Messages appear instantly in both ticket chat and console
  - No more waiting for page refresh or polling
  - Log entries with emoji indicators (✅ ⏸️ ⏭️)
- **Console Real-time Updates**: Console now receives all messages live
  - Shows messages from all active tickets via WebSocket
  - Displays ticket number badge for each message
  - Raw log view shows command logs instantly
- **Duplicate Message Prevention**: Fixed message display issues
  - Prevents duplicate messages when commands are sent
  - Proper tracking of shown message IDs

### Fixed
- Messages no longer disappear after sending commands
- Console now properly receives broadcasts from ticket rooms

## [2.30.0] - 2026-01-10

### Added
- **AI Model Selection**: Choose between Opus, Sonnet, or Haiku per project/ticket
  - Projects have default AI model (defaults to Sonnet)
  - Tickets can override project's model or inherit it
  - Model selection available during creation and can be changed later
  - Changes take effect on the next AI request
- **Message Delete**: Ability to delete conversation messages
  - Removes message from history
  - Adjusts ticket token count accordingly
  - Useful for removing incorrect or confusing messages

### Database
- Added `ai_model` column to `projects` table (enum: opus/sonnet/haiku, default: sonnet)
- Added `ai_model` column to `tickets` table (nullable, inherits from project if null)

## [2.29.0] - 2026-01-10

### Added
- **Watchdog AI Monitor**: Background thread that detects stuck tickets
  - Uses Claude Haiku to analyze conversation patterns every 30 minutes
  - Detects: repeated errors, circular behavior, no progress, failed tests
  - Auto-marks tickets as 'stuck' when problems detected
  - Sends email notification and WebSocket broadcast to UI
  - Adds system message explaining why ticket was stopped
  - Prevents runaway token consumption on long-running projects

### Changed
- Watchdog checks tickets with 10+ messages only (avoids false positives)
- Analyzes last 30 messages for pattern detection

## [2.28.0] - 2026-01-10

### Added
- **Real-time Token Tracking**: Tokens now update during session execution
  - Dashboard shows running session tokens in Today/Week/Month/All Time stats
  - Ticket view shows live token count without waiting for session to end
  - API calls tracked in real-time via new `api_calls` column in `execution_sessions`
- **User Message Token Counting**: User messages now count toward ticket totals
  - UTF-8 byte-based estimation: `len(text.encode('utf-8')) // 4`
  - Accurate for Greek/Unicode text (2 bytes per Greek character)
  - Updates ticket total immediately when message is sent
- **Smart Context Important Notes**: Extract user instructions/warnings from conversations
  - Semantic extraction using Claude Haiku
  - Captures rules, warnings, preferences, and constraints
  - Persisted and shown in future sessions

### Fixed
- **Token Double-counting**: Removed duplicate ticket token updates
- **Dashboard Stats**: Now includes running sessions in all time periods

## [2.27.3] - 2026-01-10

### Fixed
- **Claude Assistant**: Auto-configure `.claude.json` to skip all interactive prompts
  - Automatically sets `hasCompletedOnboarding: true` (skips theme selection)
  - Automatically sets `bypassPermissionsModeAccepted: true` (skips warning)
  - Config patched on status check and before Claude starts
  - Works on fresh installs without manual configuration

## [2.27.2] - 2026-01-10

### Fixed
- **Navigation Header**: Standardized header navigation across all pages
  - Consistent menu order: Dashboard, Projects, Tickets, Console, History
  - Logout moved to fixed position on the right
  - Active page highlighting on all pages

## [2.27.1] - 2026-01-10

### Fixed
- **Claude Assistant**: Fixed interactive mode asking for activation/theme/trust
  - Added `--dangerously-skip-permissions` flag to bypass permission prompts
  - Now starts directly without setup wizard
  - Uses inherited environment from web process (`os.environ.copy()`)

## [2.27.0] - 2026-01-09

### Added
- **Upgrade Script** (`upgrade.sh`): New automated upgrade system
  - `--dry-run` mode to preview changes without applying them
  - `-y` flag for auto-confirm (non-interactive mode)
  - Automatic backup before upgrade
  - Database migrations support with version tracking
  - Service stop/start management
  - Changelog display after upgrade
- **Database Migrations**: New `migrations/` folder for schema updates
  - Version-tracked migrations via `schema_migrations` table
  - SQL migration files with naming convention: `VERSION_description.sql`
  - Example migration template included

### Fixed
- **Password Change Script**: Fixed admin panel password change not working
  - Changed from MySQL root to application user credentials
  - Now reads from `/etc/codehero/system.conf` (world-readable)
  - Properly generates and stores bcrypt password hashes

### Documentation
- Added upgrade instructions to README and INSTALL
- Migration README with examples and best practices

## [2.26.17] - 2026-01-09

### Added
- **Claude Activation via Web Panel**: New web-based terminal for activating Claude Code CLI
  - Supports both Anthropic Subscription (OAuth) and API Key authentication
  - Integrated activation modal in dashboard header
  - Real-time PTY terminal using xterm.js
  - Status indicator shows activation state (green=active, orange blinking=inactive)
- **Claude Assistant Page**: Full-page interactive Claude terminal at `/claude-assistant`
  - Direct access to Claude CLI through browser
  - Start/Stop session controls
  - Real-time terminal output
- **Tickets List Page**: New `/tickets` route with full ticket management
  - Filter by status (All, Open, In Progress, Awaiting Input, Done, Failed)
  - Search across ticket numbers, titles, and project names
  - Shows created date, updated date, project, priority, and token usage
  - Keyboard shortcut: Ctrl+K or / to focus search
- **Load Test Report**: Comprehensive system performance documentation
  - 10-ticket parallel processing test results
  - Memory, CPU, and resource usage metrics
  - Recommendations for production deployment

### Changed
- **Aurora Theme**: Updated UI across all pages with consistent dark theme
  - Login page: New aurora background with animated gradient blobs
  - Editor page: Matching glass-morphism design
  - Tickets list: Modern card-based layout with status colors
  - Dashboard: Added Claude activation buttons in header
- **setup.sh**: Now automatically installs Claude Code CLI during system setup
  - Runs `curl -fsSL https://claude.ai/install.sh | bash` for claude user
  - Adds `~/.local/bin` to PATH
  - Updated info message to reference web-based activation

### Fixed
- **Editor "Discard Changes" Bug**: Fixed false positive when closing unmodified files
  - Now compares content with original instead of tracking any change event
  - Properly handles undo (Ctrl+Z) returning to unmodified state

### Technical
- Added PTY-based terminal sessions for Claude activation
- Clean environment isolation for child processes (prevents credential leakage)
- New API endpoints:
  - `/api/claude/status` - Check activation status
  - `/api/claude/activate/*` - Terminal session management
  - `/api/claude/apikey` - Save API key
  - `/api/claude/chat/*` - Claude Assistant sessions

## [2.26.16] - 2026-01-08

### Previous Release
- See GitHub releases for full history

---

For more information, see the [README](README.md).
