# Changelog

All notable changes to the Fotios Claude System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- **setup.sh**: Now copies all documentation files to /opt/fotios-claude/
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
  - Now reads from `/etc/fotios-claude/system.conf` (world-readable)
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
