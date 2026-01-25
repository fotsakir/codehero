# CodeHero User Guide

This guide will walk you through using the CodeHero Admin Panel to manage your AI-powered development projects.

## Table of Contents

1. [Dashboard](#dashboard)
2. [Managing Projects](#managing-projects)
3. [Working with Tickets](#working-with-tickets)
4. [Console View](#console-view)
5. [Execution History](#execution-history)
6. [Kill Switch Commands](#kill-switch-commands)
7. [Web Terminal](#web-terminal)
8. [Claude Assistant](#claude-assistant)
9. [AI Project Manager](#ai-project-manager)
10. [Settings](#settings)
11. [System Updates](#system-updates)
12. [Tips & Best Practices](#tips--best-practices)
13. [Troubleshooting](#troubleshooting)

---

## Dashboard

The Dashboard is your main control center. It shows:

- **System Status**: Whether Claude daemon is running
- **Quick Stats**: Active projects, open tickets, sessions today
- **Recent Activity**: Latest ticket updates and completions

![Dashboard](guide/01-dashboard.png)

---

## Managing Projects

### Viewing Projects

The Projects page shows all your development projects. Each project card displays:

- Project name and description
- Working directory path
- Number of open tickets
- Quick action buttons

![Projects List](guide/02-projects.png)

### Creating a New Project

Click **"New Project"** to create a project:

1. **Name**: A descriptive name for your project
2. **Working Directory**: The full path where Claude will work (e.g., `/home/claude/my-app`)
3. **Description**: Brief description of what the project is about

![Create Project](guide/03-create-project.png)

### Project Details

Click on any project to see its details and all associated tickets.

![Project Detail](guide/04-project-detail.png)

---

## Working with Tickets

Tickets are the core of CodeHero. Each ticket represents a task for Claude to complete.

### Creating a Ticket

1. Go to a Project and click **"+ New Ticket"**
2. Fill in the form:
   - **Title**: Short description of the task
   - **Description**: Detailed instructions for Claude
   - **Type**: Category of work (see below)
   - **Priority**: low, medium, high, critical
   - **Sequence**: Execution order (optional)
   - **Dependencies**: Other tickets that must complete first (optional)

### Ticket Types

Color-coded categories to organize your work:

| Type | Color | Use For |
|------|-------|---------|
| 🟣 **feature** | Purple | New functionality |
| 🔴 **bug** | Red | Fix broken behavior |
| 🟠 **debug** | Orange | Investigation, troubleshooting |
| 🟣 **rnd** | Violet | Research & Development |
| ⚪ **task** | Gray | General work (default) |
| 🔵 **improvement** | Cyan | Refactoring, optimization |
| 🟢 **docs** | Green | Documentation |

**Tip**: Use the right type to help you filter and track different kinds of work.

### Ticket Priority

Priority affects processing order when no sequence is set:

| Priority | When to Use |
|----------|-------------|
| **critical** | Urgent, blocks other work |
| **high** | Important, do soon |
| **medium** | Normal priority (default) |
| **low** | Nice to have, do when time permits |

### Ticket Sequencing

Control the exact order tickets are processed:

1. **Sequence Number**: Assign a number (1, 2, 3...) to define execution order
2. Tickets with sequence numbers run **before** tickets without
3. Lower numbers run first: sequence 1 → 2 → 3 → (no sequence by priority)

**Example:**
```
Ticket A: sequence_order = 1  → Runs first
Ticket B: sequence_order = 2  → Runs second
Ticket C: sequence_order = 3  → Runs third
Ticket D: no sequence         → Runs after all sequenced tickets
```

### Dependencies

Make tickets wait for other tickets to complete:

1. When creating/editing a ticket, select **Dependencies**
2. Choose which tickets must be done first
3. Daemon will skip dependent tickets until dependencies are `done` or `awaiting_input`

**Example:**
```
"Shopping Cart" depends on "Product Catalog"
→ Cart ticket won't start until Catalog is complete
```

**Tip**: Dependencies work with `awaiting_input` by default - so if you're reviewing a ticket, dependent tickets can still run.

### Execution Modes

Control how much freedom Claude has when working on tickets:

| Mode | Description |
|------|-------------|
| **Autonomous** | Full access, no permission prompts. Claude works uninterrupted. |
| **Semi-Autonomous** | Smart sandbox (recommended). Auto-approves safe operations, asks for risky ones, blocks dangerous ones. |
| **Supervised** | Claude asks permission before every write/edit/bash operation. |

#### Semi-Autonomous Mode (Recommended)

The smart middle ground between full access and constant prompts:

**✅ Auto-Approved (No prompts):**
- File create/edit/delete within project folder
- Running tests (`npm test`, `pytest`, `phpunit`)
- Build commands (`npm run build`, `composer install`)
- Linting and formatting
- Git read operations (`git status`, `git log`, `git diff`)

**⚠️ Requires Approval:**
- Installing packages (`npm install <package>`, `pip install`, `composer require`)
- Git write operations (`git commit`, `git push`, `git checkout`)
- Database migrations (`php artisan migrate`)
- Network requests (`curl`, `wget` to external URLs)

**🚫 Blocked (Cannot execute):**
- System commands (`sudo`, `apt`, `systemctl`)
- Modifying `.git` folder (backup protection)
- Accessing system paths (`/etc`, `/opt/codehero`, `~/.ssh`)
- Dangerous commands (`rm -rf /`, `chmod 777`)

**"Approve Similar" Feature:**
When a permission prompt appears, click **"Approve All Similar"** to auto-approve future similar operations. For example, approving `npm install express` will auto-approve all future `npm install` commands.

#### Setting Execution Mode

1. **Per Project**: Set default when creating project
2. **Per Ticket**: Override project default when creating ticket
3. **Change Later**: Edit ticket settings anytime

### Sub-tickets

Break complex tasks into smaller pieces:

1. Create a main (parent) ticket
2. Create sub-tickets and set **Parent Ticket**
3. Sub-tickets inherit the project
4. Parent tracks overall progress

**How it works:**
- Sub-tickets run in their sequence order
- Parent completes when all children complete
- Use for large features with multiple steps

### Start Now / Force Queue

Jump a ticket to the front of the queue:

1. Open the ticket detail page
2. Click **"▶️ Start Now"** button
3. Ticket gets `is_forced = TRUE` and `status = open`
4. Daemon will process it next (after current ticket finishes)

**Note**: If clicking Start Now on a sub-ticket, the parent ticket starts instead.

### Auto-Retry

Failed tickets can automatically retry:

- Each ticket has `retry_count` (starts at 0) and `max_retries` (default 3)
- When a ticket fails: retry_count increments
- If retry_count < max_retries: ticket resets to `open` and tries again
- If retry_count >= max_retries: ticket stays `failed`

**Configure per ticket:**
- Increase max_retries for flaky tasks
- Set to 0 to disable auto-retry

### Ticket Lifecycle

Tickets flow through these statuses:

| Status | Description |
|--------|-------------|
| `open` | Waiting to be processed |
| `in_progress` | Claude is currently working on it |
| `awaiting_input` | Claude needs your response |
| `done` | Successfully completed |
| `failed` | Something went wrong (may auto-retry) |
| `skipped` | Manually skipped |
| `timeout` | Exceeded max duration |

### Ticket Actions

From the ticket detail page:

| Button | What it does |
|--------|--------------|
| **▶️ Start Now** | Jump to front of queue |
| **🔄 Retry** | Retry a failed ticket |
| **⏭️ Skip** | Skip this ticket |
| **🗑️ Delete** | Permanently delete ticket |
| **⏹ Stop** | Kill switch - stop Claude immediately |

### Progress Dashboard

Visual overview of project progress:

1. Go to Project → Click **"📈 Progress"** or the progress icon on the project card
2. See:
   - Overall completion percentage
   - Ticket counts by status
   - Ticket counts by type
   - Sequence flow visualization
   - AI Assistant for project-specific help

### Tips for Writing Good Tickets

**DO:**
- Be specific about what you want
- Include file paths when relevant
- Mention the programming language/framework
- Break large tasks into sub-tickets
- Use appropriate ticket types

**DON'T:**
- Vague instructions like "make it better"
- Multiple unrelated tasks in one ticket
- Assume Claude knows context from other tickets

**Good Example:**
```
Title: Add user authentication API

Description:
Create REST API endpoints in /api/auth/:
- POST /api/auth/login - Accept email/password, return JWT
- POST /api/auth/register - Create new user
- GET /api/auth/me - Return current user (requires auth)

Use the existing User model in models/user.py.
Use bcrypt for password hashing.
```

**Bad Example:**
```
Title: Auth

Description: Add login
```

---

## Console View

The Console provides a real-time view of Claude's execution output.

- **Live streaming**: See Claude's work as it happens
- **Scrollable history**: Review past output
- **Auto-scroll**: Stays at bottom for new content

![Console View](guide/07-console.png)

---

## Execution History

The History page shows all past execution sessions:

- Start and end times
- Duration
- Exit codes
- Associated tickets

![Execution History](guide/08-history.png)

---

## Kill Switch

When Claude is working on a ticket, you can instantly stop execution using the Kill Switch.

### How to Use Kill Switch

**Option 1: Kill Switch Button**
- When a ticket is `in_progress`, a red **⏹ Stop** button appears next to the Send button
- Click it to immediately stop Claude's execution
- The ticket will be paused and waiting for your new instructions

**Option 2: /stop Command**
- Type `/stop` in the chat field and click Send
- This works exactly like the button - instant stop

**Option 3: Via AI Assistant**
- You can ask the Claude Assistant to stop a ticket using the kill switch tool
- Example: "Stop ticket PROJ-0001" or "Activate kill switch for ticket 5"

### What Happens When You Stop

1. Claude's process receives SIGTERM and stops immediately
2. The ticket status changes to `awaiting_input`
3. A system message confirms the stop
4. You can then provide new instructions or corrections

---

## Web Terminal

The Web Terminal provides full Linux shell access directly in your browser.

### Accessing the Terminal

Click **Terminal** in the navigation menu to open the terminal.

### Features

- **Real shell access**: Full PTY terminal via WebSocket
- **Popup support**: Click "Open in Popup" for multi-monitor setups
- **Full sudo access**: Run administrative commands
- **256-color support**: Full terminal color support with xterm.js

### Tips

- The terminal runs as the `claude` user
- Use `sudo` for administrative commands
- Resize the browser window to adjust terminal size
- Open in popup to keep terminal visible while working

---

## Claude Assistant

Claude Assistant provides direct interactive access to Claude AI outside of the ticket workflow.

### Accessing the Assistant

Click **Claude Assistant** in the navigation menu.

### Features

- **AI Model Selection**: Choose your preferred model:
  - **Opus**: Most capable, best for complex tasks
  - **Sonnet** (default): Balanced performance and speed
  - **Haiku**: Fastest, good for quick questions

- **Popup Window**: Click "Open in Popup" for multi-monitor setups

- **Direct Access**: Chat with Claude without creating tickets

### Use Cases

- Quick questions about your code
- Getting help with platform issues
- Learning and exploration
- Prototyping ideas before creating tickets

---

## AI Project Manager

The AI Project Manager helps you design your project before coding by creating a comprehensive blueprint.

### How to Use

1. Go to the **Projects** page
2. Click the **"Plan with AI"** button
3. A new Claude Assistant window opens in blueprint mode
4. Claude automatically asks about your project requirements:
   - Project overview and goals
   - Technology stack preferences
   - Database requirements
   - API endpoints needed
   - File structure

### What You Get

After the conversation, Claude provides a complete blueprint including:

- **Tech Stack**: Recommended technologies
- **Database Schema**: Tables, relationships, indexes
- **API Design**: Endpoints with request/response formats
- **File Structure**: Organized directory layout
- **Feature Breakdown**: Implementation milestones
- **Coding Standards**: Naming conventions, best practices

### Tip

Copy the generated blueprint into your project's description field when creating a new project. This gives Claude all the context it needs when working on tickets.

---

## Settings

Access settings by clicking the **⚙️** button in the dashboard header.

### Telegram Notifications

Get instant alerts on your phone when Claude needs attention.

#### Setup Instructions

1. **Create a Telegram Bot**
   - Open Telegram on your phone and search for **@BotFather**
   - Send `/newbot`
   - Enter a name for your bot (e.g., `CodeHero Alerts`)
   - Enter a username for your bot (must end in `bot`, e.g., `codehero_bot`)
   - BotFather will give you the **token** - copy it (looks like `7123456789:AAHk5Jxxx...`)

2. **Start a Chat with Your Bot**
   - Click the link BotFather gave you, or search for your bot's username
   - Press **Start** or send `/start`
   - **Important:** Send one more message (e.g., "hello") - this is needed for the next step

3. **Get Your Chat ID**
   - Open this URL in your browser (replace `<TOKEN>` with your actual token):
     ```
     https://api.telegram.org/bot<TOKEN>/getUpdates
     ```
   - Look for `"chat":{"id":123456789}` - the number is your **Chat ID**

4. **Configure in Settings**
   - Go to Dashboard and click ⚙️ (Settings)
   - Paste your **Bot Token**
   - Paste your **Chat ID**
   - Select which notifications you want to receive
   - Click **Test Notification** to verify it works
   - If you receive the test message, click **Save Settings**

#### Available Notifications

| Event | Description |
|-------|-------------|
| ⏳ Awaiting Input | Claude completed a task and needs your review |
| ❌ Task Failed | Something went wrong during execution |
| ⚠️ Watchdog Alert | A ticket appears to be stuck |

#### Two-Way Communication

You can reply directly to notifications from your phone:

**Reply to Give Instructions:**
Simply reply to any notification with your message. The system will:
- Add your message to the ticket conversation
- Reopen the ticket if it was "awaiting input"
- Claude will start working on your new instructions

**Ask Quick Questions:**
Start your reply with `?` to get a quick status update without reopening the ticket:
- `?what's the status` - Get a summary
- `?τι γίνεται` - Works in any language
- `?what went wrong` - Quick error info

The system uses Claude Haiku for fast, low-cost answers.

| Your Reply | What Happens |
|------------|--------------|
| `fix the login bug` | Message added, ticket reopens, Claude works |
| `?what's wrong` | Get summary, ticket stays as-is |
| `looks good, continue` | Message added, ticket reopens |

---

## System Updates

CodeHero checks for updates automatically and shows a green badge when a new version is available.

### Updating via Dashboard (Recommended)

1. **Check for Updates**: A green "🚀 vX.Y.Z Available" badge appears in the dashboard header when an update is ready

2. **Click the Badge**: Opens the update modal showing:
   - Current version → New version
   - Release notes
   - "Install Update" button

3. **Install Update**: Click to start the upgrade:
   - Downloads the new version from GitHub
   - Shows real-time console output
   - Runs upgrade scripts automatically
   - Restarts services
   - Auto-reloads page on success

### Real-time Console Output

During upgrade, you'll see live output with color-coded status:

| Color | Meaning |
|-------|---------|
| 🟢 Green `[OK]` | Step completed successfully |
| 🔵 Blue `[INFO]` | Information message |
| 🟡 Yellow `[WARN]` | Warning (non-fatal) |
| 🔴 Red `[ERROR]` | Error occurred |

### AI-Powered Troubleshooting

If an upgrade fails, click **"🤖 Ask AI to fix the problem"**:

1. AI analyzes the error log
2. Shows the problem and explanation
3. Provides fix commands with one-click execution
4. Run commands individually or all at once

**Example:**
```
Problem: MySQL migration syntax error

Fix:
┌─────────────────────────────────────────┬──────┐
│ mysql -e "ALTER TABLE projects..."      │ ▶ Run│
└─────────────────────────────────────────┴──────┘

[▶ Run All Commands]
```

### Updating via Command Line

```bash
cd /root
wget https://github.com/fotsakir/codehero/releases/latest/download/codehero-2.83.2.zip
unzip codehero-2.83.2.zip
cd codehero
sudo ./upgrade.sh
```

### How the Upgrade System Works

The upgrade system is modular - each version has its own upgrade script:

```
upgrades/
├── 2.42.0.sh    # Multimedia tools installation
├── 2.61.0.sh    # Claude CLI installation
├── 2.63.0.sh    # OpenLiteSpeed → Nginx migration
├── 2.65.0.sh    # phpMyAdmin setup
└── _always.sh   # Permission fixes (runs every time)
```

When upgrading (e.g., from 2.60.0 to 2.67.0):
1. Detects current and target versions
2. Finds all scripts between those versions
3. Runs them in order: 2.61.0 → 2.63.0 → 2.65.0
4. Applies database migrations
5. Restarts services

**Safe to run multiple times** - already-applied upgrades are tracked and skipped.

---

## Tips & Best Practices

### Writing Good Prompts

- Be specific about what you want
- Include file paths when relevant
- Mention the programming language/framework
- Specify any constraints or requirements

**Good Example:**
```
Create a REST API endpoint in /home/claude/my-app/api/users.py
that handles GET /users/{id} and returns user data from the
MySQL database. Use the existing db_connection module.
```

**Bad Example:**
```
Make a user API
```

### Project Organization

- One project per codebase
- Use descriptive project names
- Keep working directories organized

### Monitoring Execution

- Check the Console for real-time progress
- Review ticket output after completion
- Use History to track patterns and issues

---

## Troubleshooting

### Ticket Stuck in "in_progress"

If a ticket seems stuck:
1. Check Console for errors
2. Use `/stop` kill switch if needed
3. Reopen the ticket to retry

### Claude Not Processing Tickets

1. Check if daemon is running: `systemctl status codehero-daemon`
2. Review daemon logs: `journalctl -u codehero-daemon -f`
3. Verify MySQL is running: `systemctl status mysql`

### Permission Errors

Ensure the `claude` user has:
- Read/write access to project directories
- Proper ownership of working files

---

## Need Help?

- **Documentation**: Check `CLAUDE_OPERATIONS.md` for technical details
- **Issues**: Report bugs at [GitHub Issues](https://github.com/fotsakir/codehero/issues)
- **Updates**: Check [Releases](https://github.com/fotsakir/codehero/releases) for new versions

---

*CodeHero v2.69.0*
