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
11. [Tips & Best Practices](#tips--best-practices)
12. [Troubleshooting](#troubleshooting)

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

### Viewing Tickets

The Tickets page shows all tickets across all projects with filtering options.

![Tickets List](guide/05-tickets.png)

### Creating a Ticket

1. Go to a Project or click **"New Ticket"**
2. Select the target project
3. Enter your task description in the **Prompt** field
4. Set priority (optional)
5. Click **Submit**

### Ticket Lifecycle

Tickets flow through these statuses:

| Status | Description |
|--------|-------------|
| `open` | Waiting to be processed |
| `in_progress` | Claude is currently working on it |
| `awaiting_input` | Claude needs your response |
| `done` | Successfully completed |
| `failed` | Something went wrong |
| `cancelled` | Manually cancelled |

### Ticket Detail View

The ticket detail page shows:

- Full prompt and any responses
- Real-time execution output
- Status history
- Action buttons (Reopen, Cancel, etc.)

![Ticket Detail](guide/06-ticket-detail.png)

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

## Kill Switch Commands

When Claude is working on a ticket, you can control execution using kill switch commands. Enter these in the ticket's response field:

| Command | Description |
|---------|-------------|
| `/stop` | Pause execution and wait for your correction |
| `/skip` | Stop and reopen ticket for later |
| `/done` | Force complete ticket successfully |

### How to Use Kill Switch

1. Open the ticket that's currently `in_progress`
2. Type your command (e.g., `/stop`) in the chat field
3. Click **Send**
4. The command appears immediately in the conversation
5. Claude receives and acts on the command

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
   - Enter a name for your bot (e.g., `Fotios Claude Alerts`)
   - Enter a username for your bot (must end in `bot`, e.g., `fotios_claude_bot`)
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

1. Check if daemon is running: `systemctl status fotios-claude-daemon`
2. Review daemon logs: `journalctl -u fotios-claude-daemon -f`
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

*CodeHero v2.52.0*
