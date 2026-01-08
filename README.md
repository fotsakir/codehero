# Fotios Claude System

### Self-hosted AI Coding Agent powered by Claude | Autonomous Development Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-2.26.5-green.svg)](CHANGELOG.md)
[![Ubuntu](https://img.shields.io/badge/Ubuntu-22.04%20|%2024.04-orange.svg)]()
[![Claude AI](https://img.shields.io/badge/Powered%20by-Claude%20AI-blueviolet.svg)](https://anthropic.com)

> **Transform your development workflow with an AI agent that writes code, manages projects, and works autonomously on your tickets.**

Fotios Claude System is a **self-hosted autonomous development platform** that uses [Claude AI](https://anthropic.com) (via Claude Code CLI) to process development tickets, write production-ready code, and manage multiple projects in parallel. Perfect for solo developers, small teams, or anyone who wants an AI coding assistant running on their own infrastructure.

---

## A Glimpse Into the Future

> **This project is a Proof of Concept** demonstrating the future of software development through human-AI collaboration.

We believe the next era of programming will not be humans writing code alone, but **humans and AI working together** - where developers describe what they need, and AI agents translate those ideas into working software. Fotios Claude System is an early experiment in this direction: a platform where you create tickets, and an AI agent autonomously writes the code.

This is not science fiction. This is happening now. And this project lets you experience it on your own infrastructure.

---

## Screenshots

![Dashboard](screenshots/dashboard.png)
*Dashboard - Real-time overview of projects, tickets, and usage statistics*

![Tickets](screenshots/tickets.png)
*Tickets - Track all development tasks across projects*

![Projects](screenshots/projects.png)
*Projects - Manage multiple projects with isolated environments*

---

## Why Fotios Claude System?

| Challenge | Solution |
|-----------|----------|
| "I have too many tasks and not enough time" | AI processes tickets autonomously while you focus on other work |
| "I want AI assistance but need data privacy" | Self-hosted on your own server - your code never leaves your infrastructure |
| "Managing multiple projects is overwhelming" | Parallel execution handles multiple projects simultaneously |
| "I need to track what the AI is doing" | Real-time monitoring shows exactly what Claude is writing |

## Key Features

- **Autonomous AI Agent** - Claude AI works on tickets independently, writing real code
- **Multi-Project Management** - Handle multiple projects with isolated databases
- **Parallel Execution** - Process tickets from different projects simultaneously
- **Real-Time Console** - Watch Claude write code live in your browser
- **Interactive Chat** - Guide Claude or ask questions during execution
- **Ticket Workflow** - Structured flow: Open → In Progress → Awaiting Input → Done
- **Auto Database Provisioning** - MySQL database auto-created per project
- **Usage Analytics** - Track token usage, execution time, and costs
- **Web Dashboard** - Beautiful admin panel with SSL encryption
- **Self-Hosted** - Complete control over your data and infrastructure

## Perfect For

- **Solo Developers** - Multiply your productivity with an AI coding partner
- **Small Teams** - Offload routine development tasks to AI
- **Agencies** - Manage multiple client projects efficiently
- **Startups** - Ship faster with AI-assisted development
- **Learning** - See how AI approaches coding problems

## Quick Start

### Requirements

- Ubuntu 22.04 or 24.04 LTS (server or desktop)
- 2GB+ RAM recommended
- Root/sudo access
- Internet connection

### One-Command Install

```bash
# Download, extract, and run
cd /root
unzip fotios-claude-system-2.26.5.zip
cd fotios-claude-system
chmod +x setup.sh && ./setup.sh

# Then install Claude Code CLI
/opt/fotios-claude/scripts/install-claude-code.sh
```

The installer automatically sets up:
- MySQL 8.0 database
- OpenLiteSpeed web server with SSL
- Python Flask application
- Background daemon service
- All required dependencies

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
