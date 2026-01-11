# Changelog

All notable changes to the Fotios Claude System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
