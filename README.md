<p align="center">
  <img src="assets/logo.svg" alt="Claude AI Developer" width="700">
</p>

<h1 align="center">Fotios Claude System</h1>

<p align="center">
  <strong>Not an AI that answers questions. An AI that builds software.</strong>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License"></a>
  <a href="CHANGELOG.md"><img src="https://img.shields.io/badge/version-2.52.0-green.svg" alt="Version"></a>
  <img src="https://img.shields.io/badge/Ubuntu-22.04%20|%2024.04-orange.svg" alt="Ubuntu">
  <a href="https://anthropic.com"><img src="https://img.shields.io/badge/Powered%20by-Claude%20AI-blueviolet.svg" alt="Claude AI"></a>
  <a href="https://github.com/fotsakir/Claude-AI-developer/stargazers"><img src="https://img.shields.io/github/stars/fotsakir/Claude-AI-developer?style=social" alt="Stars"></a>
</p>

> **This is not an AI that answers questions. It builds software.**

Instead of chatting back and forth, this AI works inside a real development environment. Describe what you want, and it plans the project, writes code, and tracks its own progress — like a developer on your team.

What makes it different is **control**. It understands your whole project, uses only the files it needs, avoids loops, and stops itself when something goes wrong.

For beginners, it removes complexity.
For developers, it removes noise.

**Download it. Let it build.**

### True Autonomy - Works While You Sleep

Unlike chat-based AI tools that require constant prompting, this system runs **unattended for hours or even days**. Create your tickets, describe what you want, and walk away. Come back to find completed features, fixed bugs, and working code.

- Queue multiple tasks across projects
- AI works through them one by one
- Built-in failsafe prevents runaway sessions
- Wake up to progress, not prompts

### Control Everything from Your Phone

Work from anywhere with **two-way Telegram integration**. No need to open a laptop.

- **Get instant alerts** when Claude needs your input or something fails
- **Reply to continue** - just reply to any notification to give Claude new instructions
- **Ask quick questions** - start with `?` to get status updates without triggering work
- **Never lose time** - respond from the bus, the coffee shop, or your bed

```
📱 Notification: "Task completed - awaiting review"
     ↓
💬 You reply: "add error handling too"
     ↓
🤖 Claude continues working
```

---

## Screenshots

![Dashboard](screenshots/dashboard.png)
*Dashboard - Real-time overview of projects, tickets, and usage statistics*

![Tickets](screenshots/tickets.png)
*Tickets - Track all development tasks across projects*

![Projects](screenshots/projects.png)
*Projects - Manage multiple projects with isolated environments*

![Ticket Detail](screenshots/ticket-detail.png)
*Ticket Detail - Claude's response with code and conversation history*

![Console](screenshots/console.png)
*Console - Real-time view of Claude working on tickets*

---

## Why Fotios Claude System?

| Challenge | Solution |
|-----------|----------|
| "AI tools need constant prompting" | **Set it and forget it** - Claude works for hours unattended |
| "I want to code more, but time is limited" | **Multiply your output** - wake up to completed features |
| "Chat-based AI feels like extra work" | **True autonomy** - describe once, Claude figures out the rest |
| "I need my code to stay private" | **Self-hosted** - your code never leaves your infrastructure |
| "I want to think bigger, not type more" | **Master from above** - architect solutions, let AI build them |

## Key Features

### Intelligent AI Features

#### SmartContext - Intelligent Context Management
Claude automatically understands your project structure without being told:
- **Auto-detects** framework, language, and architecture
- **Finds relevant files** based on the task at hand
- **Builds minimal context** - only includes what's needed
- **Learns patterns** from your codebase conventions
- **Reduces token usage** by up to 70% vs. sending entire codebase

#### AI Failsafe (Watchdog)
Built-in protection against runaway AI sessions:
- **Monitors all active tickets** every 30 minutes
- **Detects stuck patterns**: repeated errors, circular behavior, no progress
- **Auto-pauses problematic tickets** before excessive token usage
- **Telegram notifications** when issues detected
- **Explains why** it stopped in the conversation

#### AI Project Manager (Blueprint Planner)
Let Claude help you design your project before coding:
- **"Plan with AI"** button on Projects page
- **Guided questionnaire** - Claude asks about requirements
- **Generates complete blueprint**: tech stack, database schema, API design, file structure
- **Feature breakdown** with milestones
- **Copy directly** to new project description

#### Claude Assistant
Interactive Claude terminal with full control:
- **AI Model Selection**: Choose Opus, Sonnet, or Haiku per session
- **Popup Window**: Open in separate window for multi-monitor setups
- **Direct Access**: Chat with Claude outside of ticket workflow
- **Full Terminal**: Real PTY with color support

#### Visual Verification - "See With Your Eyes"
Claude can see exactly what you see:
- **Screenshot capture** - Claude takes screenshots using Playwright
- **Visual analysis** - Describes layout, styling, and UI issues
- **No more explaining** - Just click "👁️ See" and Claude sees the problem
- **Automatic when needed** - Mention visual issues and Claude uses Playwright automatically

#### Telegram - Work from Your Phone
Full two-way communication via Telegram. Control your AI developer from anywhere:
- **Instant Notifications** - Get alerts when tasks complete, fail, or get stuck
- **Reply to Execute** - Reply to any notification and Claude starts working
- **Quick Questions** - Add `?` to get instant status updates via AI
- **Never Wait** - Respond immediately from your phone, no laptop needed
- **Easy Setup** - One-click configuration from Settings panel (⚙️)

### Core AI Features
- **Autonomous AI Agent** - Claude AI works on tickets independently, writing real code
- **Multi-Project Management** - Handle multiple projects with isolated databases
- **Parallel Execution** - Process tickets from different projects simultaneously
- **Real-Time Console** - Watch Claude write code live in your browser
- **Interactive Chat** - Guide Claude or ask questions during execution

### Ticket Management
- **Ticket Workflow** - Structured flow: Open → In Progress → Awaiting Input → Done
- **Kill Switch Commands** - Instant control while Claude is working:
  - `/stop` - Pause and wait for correction (shows immediately)
  - `/skip` - Stop and reopen ticket (shows immediately)
  - `/done` - Force complete ticket (shows immediately)
- **Message Queue** - Messages sent during execution are read when Claude finishes
- **Auto-Close** - Tickets auto-close after 7 days in awaiting input
- **Search** - Search across tickets, projects, and history

### Web Terminal
Full Linux terminal in your browser:
- **Real shell access** via WebSocket
- **Popup support** for multi-monitor setups
- **Full sudo access** for system administration
- **256-color support** with xterm.js

### Backup & Restore
- **Auto Backup on Open** - Project automatically backed up when ticket starts
- **Auto Backup on Close** - Project backed up when ticket completes
- **Manual Backup** - Create backup anytime from project page
- **Restore** - Restore project to any previous backup point
- **Export Project** - Download complete project as ZIP

### File Management
- **File Upload** - Upload files directly to project via web interface
- **File Editor** - Edit project files in browser with syntax highlighting
- **File Browser** - Navigate project directory structure

### Project Features
- **Auto Database Provisioning** - MySQL database auto-created per project
- **Project Archive/Reopen** - Archive completed projects, reopen when needed
- **Global Context** - Server environment info shared with all projects
- **Tech Stack Detection** - Knows installed tools (Node.js, PHP, Java, etc.)

### Monitoring & Analytics
- **Real-Time Usage Tracking** - Tokens, API requests, and work duration tracked in real-time
- **Per-Project Stats** - See exactly how much each project costs
- **Per-Ticket Stats** - Know the cost of every feature or fix
- **Time-Based Reports** - Daily, weekly, and monthly usage summaries
- **Session History** - View all Claude sessions with full output
- **Daemon Status** - Monitor background worker status

### Infrastructure
- **Web Dashboard** - Beautiful dark-theme admin panel
- **SSL Encryption** - All traffic encrypted via OpenLiteSpeed
- **Self-Hosted** - Complete control over your data
- **CLI Tool** - Manage projects and tickets from terminal

## Perfect For

- **Solo Developers** - Multiply your productivity with an AI coding partner
- **Small Teams** - Offload routine development tasks to AI
- **Agencies** - Manage multiple client projects efficiently
- **Startups** - Ship faster with AI-assisted development
- **Learning** - See how AI approaches coding problems

## Quick Start

### One-Click Install (Recommended)

**No technical knowledge required!** Works on Windows, macOS, and Linux.

**🪟 Windows** - Open PowerShell as Admin, paste:
```powershell
irm https://raw.githubusercontent.com/fotsakir/Claude-AI-developer/main/multipass/install-windows.ps1 | iex
```

**🍎 macOS** - Open Terminal, paste:
```bash
curl -sL https://raw.githubusercontent.com/fotsakir/Claude-AI-developer/main/multipass/install-macos.command | bash
```

**🐧 Linux** - Open Terminal, paste:
```bash
curl -sL https://raw.githubusercontent.com/fotsakir/Claude-AI-developer/main/multipass/install-linux.sh | bash
```

Paste → Enter → Wait 15 minutes → Done! [Full guide →](docs/MULTIPASS_INSTALL.md)

**After installation:**
- Dashboard: `https://VM_IP:9453` (login: admin / admin123)
- Change passwords: `sudo /opt/fotios-claude/scripts/change-passwords.sh`

---

### Manual Install (Ubuntu Server)

#### Requirements

- Ubuntu 22.04 or 24.04 LTS (server or desktop)
- 2GB+ RAM recommended
- Root/sudo access
- Internet connection

#### One-Command Install

```bash
# Install required tools
apt-get update && apt-get install -y unzip wget net-tools

# Download and extract
cd /root
wget https://github.com/fotsakir/Claude-AI-developer/releases/latest/download/fotios-claude-system-2.47.0.zip
unzip fotios-claude-system-2.47.0.zip
cd fotios-claude-system

# Run setup
chmod +x setup.sh && ./setup.sh

# Find your IP address
ifconfig

# Then install Claude Code CLI
/opt/fotios-claude/scripts/install-claude-code.sh
```

The installer automatically sets up:
- MySQL 8.0 database
- OpenLiteSpeed web server with SSL
- Python Flask application
- Background daemon service
- All required dependencies

### Upgrading from Previous Version

```bash
# Download new version
cd /root
unzip fotios-claude-system-2.47.0.zip
cd fotios-claude-system

# Preview changes (recommended)
sudo ./upgrade.sh --dry-run

# Run upgrade
sudo ./upgrade.sh

# Or auto-confirm all prompts
sudo ./upgrade.sh -y
```

The upgrade script will:
- Create automatic backup of current installation
- Apply any database migrations
- Update all application files
- Restart services
- Show what changed in the new version

### Access Your Dashboard

| Service | URL | Default Login |
|---------|-----|---------------|
| **Admin Panel** | `https://YOUR_IP:9453` | admin / admin123 |
| Web Projects | `https://YOUR_IP:9867` | - |
| OLS WebAdmin | `https://YOUR_IP:7080` | admin / 123456 |

## How It Works

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Create    │     │   Daemon    │     │  Claude AI  │     │    Code     │
│   Ticket    │ ──► │   Picks Up  │ ──► │   Works     │ ──► │  Delivered  │
│             │     │   Ticket    │     │   On Task   │     │             │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                                       │
       │            ┌─────────────┐            │
       └───────────►│  You Watch  │◄───────────┘
                    │  Real-Time  │
                    └─────────────┘
```

1. **Create a ticket** - Describe what you need built
2. **Daemon assigns it** - Background service picks up open tickets
3. **Claude works** - AI writes code, creates files, runs commands
4. **You review** - Watch in real-time or review when complete
5. **Iterate** - Send messages to refine, or close when satisfied

## Ticket Workflow

```
┌──────┐     ┌─────────────┐     ┌─────────────────┐     ┌──────┐
│ open │ ──► │ in_progress │ ──► │ awaiting_input  │ ──► │ done │
└──────┘     └─────────────┘     └────────┬────────┘     └──────┘
                                          │
                              Send Message │ (refine/continue)
                                          ▼
                                    ┌──────────┐
                                    │   open   │
                                    └──────────┘
```

Tickets auto-close after 7 days in `awaiting_input` if no action taken.

## Architecture

```
                    ┌────────────────────────────────┐
                    │           INTERNET             │
                    └───────┬───────────┬────────────┘
                            │           │
                       Port 9453   Port 9867
                      Admin Panel  Web Projects
                            │           │
                    ┌───────┴───────────┴────────┐
                    │      OpenLiteSpeed         │
                    │    (SSL Termination)       │
                    └───────┬───────────┬────────┘
                            │           │
                    ┌───────┴───┐ ┌─────┴───────┐
                    │   Flask   │ │   LSPHP     │
                    │  Web App  │ │  Projects   │
                    └───────┬───┘ └─────────────┘
                            │
                    ┌───────┴───────┐
                    │    Daemon     │──── Claude Code CLI
                    │  (Background) │
                    └───────┬───────┘
                            │
                    ┌───────┴───────┐
                    │    MySQL      │
                    │   Database    │
                    └───────────────┘
```

## CLI Commands

```bash
# Create a project
claude-cli project add --name "My E-Commerce" --code SHOP

# Create a ticket
claude-cli ticket add --project SHOP --title "Build user authentication" --priority high

# Check system status
claude-cli status

# Control daemon
claude-cli daemon start|stop|status
```

## Configuration

Edit `/etc/fotios-claude/system.conf`:

```bash
# Database connection
DB_HOST=localhost
DB_NAME=claude_knowledge
DB_USER=claude_user
DB_PASSWORD=your-secure-password

# Parallel processing (how many tickets at once)
MAX_PARALLEL_PROJECTS=3

# Auto-close tickets after N days
REVIEW_DEADLINE_DAYS=7
```

## Tech Stack

- **Backend**: Python 3, Flask, Flask-SocketIO
- **Database**: MySQL 8.0
- **Web Server**: OpenLiteSpeed with LSPHP
- **AI**: Claude AI via Claude Code CLI
- **OS**: Ubuntu 22.04 / 24.04 LTS

## Documentation

| Document | Description |
|----------|-------------|
| [One-Click Install](docs/MULTIPASS_INSTALL.md) | Easiest install for Windows, macOS, Linux |
| [User Guide](docs/USER_GUIDE.md) | How to use the admin panel (with screenshots) |
| [Telegram Setup](docs/TELEGRAM_SETUP.md) | Get instant alerts on your phone |
| [VM Installation](docs/VM_INSTALLATION.md) | Install on VMware, Hyper-V, VirtualBox, UTM, Parallels |
| [Installed Packages](docs/INSTALLED_PACKAGES.md) | All tools & packages (ffmpeg, ImageMagick, OCR, etc.) |
| [INSTALL.md](INSTALL.md) | Detailed installation guide |
| [CLAUDE_OPERATIONS.md](CLAUDE_OPERATIONS.md) | System management & troubleshooting |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [CLAUDE.md](CLAUDE.md) | Development workflow for contributors |

## Important Notice

> **Warning**: This system runs Claude AI with **unrestricted access** to your server. Claude can execute commands, create/modify/delete files, access databases, and perform any operation the system user can do.
>
> **Use at your own risk.** The authors and contributors are not responsible for any damage, data loss, security issues, or other consequences resulting from the use of this software. Always run on isolated/dedicated servers and maintain proper backups.

## Security

- **Self-hosted**: Your code stays on your server
- **SSL encryption**: All web traffic encrypted
- **Isolated databases**: Each project gets its own MySQL database
- **Configurable access**: Restrict admin panel to trusted IPs

After installation, change default passwords:
```bash
sudo /opt/fotios-claude/scripts/change-passwords.sh
```

## Contributing

Contributions are welcome!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [CLAUDE.md](CLAUDE.md) for development guidelines.

## Support

- **Issues**: [GitHub Issues](../../issues)
- **Discussions**: [GitHub Discussions](../../discussions)

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  <b>Built with Claude AI</b><br>
  <sub>If you find this useful, please star the repository!</sub>
</p>

## Author

**Fotios Tsakiridis** ([@fotsakir](https://github.com/fotsakir))

[Smartnav Telematic Services Cyprus Ltd](https://smartnav.eu)

## Keywords

`claude-ai` `anthropic` `ai-coding-assistant` `autonomous-agent` `code-generation` `ai-developer` `self-hosted` `ticket-system` `project-management` `flask` `mysql` `openlitespeed` `ubuntu` `devops` `automation` `open-source` `php` `python` `human-ai-collaboration` `future-of-programming` `proof-of-concept` `ai-pair-programming` `agentic-ai`
