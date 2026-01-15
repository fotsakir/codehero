# CodeHero - Platform Knowledge Base

**This file is automatically loaded by Claude Assistant to help users with platform questions, troubleshooting, and development.**

---

## Platform Overview

CodeHero is a self-hosted autonomous AI coding platform powered by Claude AI to process development tickets. The system consists of:

- **Web App** (Flask + SocketIO) - Admin panel at port 9453
- **Daemon** - Background worker that processes tickets using Claude Code CLI
- **Nginx** - Web server with SSL termination and PHP-FPM
- **MySQL** - Database for projects, tickets, conversations

---

## Your Tools - Project & Ticket Management

**IMPORTANT: You have access to special tools to manage the platform. Use them when users ask about projects or tickets!**

### Available Tools

| Tool | What it does | When to use |
|------|--------------|-------------|
| `codehero_list_projects` | Shows all projects | "What projects do I have?", "Show me my projects" |
| `codehero_get_project` | Gets project details | "Tell me about project X", "What tickets are in X?" |
| `codehero_create_project` | Creates a new project | "Create a new project called X", "I want to start a new project" |
| `codehero_list_tickets` | Shows tickets in a project | "What tickets are open?", "Show tickets for project X" |
| `codehero_get_ticket` | Gets ticket details | "What's the status of ticket X?", "Show me ticket details" |
| `codehero_create_ticket` | Creates a new ticket | "Create a ticket to do X", "Add a task for Y" |
| `codehero_update_ticket` | Updates a ticket | "Close ticket X", "Change priority of ticket" |
| `codehero_dashboard_stats` | Shows platform overview | "How many projects?", "Give me a summary" |

### Example Usage

When user says: "Θέλω να δω τα projects μου" (I want to see my projects)
→ Use `codehero_list_projects` tool

When user says: "Φτιάξε ένα project για e-shop" (Create an e-shop project)
→ Use `codehero_create_project` with name="E-Shop"

When user says: "Πρόσθεσε ένα ticket για login page" (Add a ticket for login page)
→ Use `codehero_create_ticket` with title="Create login page"

When user says: "Πόσα tickets έχω ανοιχτά;" (How many open tickets?)
→ Use `codehero_dashboard_stats` or `codehero_list_tickets`

### Tool Parameters

**codehero_create_project:**
- `name` (required): Project name
- `description`: What the project is about
- `project_type`: web, app, api, cli, library, other
- `tech_stack`: php, python, node, java, dotnet, other

**codehero_create_ticket:**
- `project_id` (required): The project ID (get from list_projects)
- `title` (required): What needs to be done
- `description`: Detailed instructions
- `priority`: low, medium, high, critical

---

## File Locations

### Source Code (Edit Here)
| Component | Path |
|-----------|------|
| Web App | `/home/claude/codehero/web/app.py` |
| Daemon | `/home/claude/codehero/scripts/claude-daemon.py` |
| Templates | `/home/claude/codehero/web/templates/*.html` |
| Config | `/home/claude/codehero/config/` |
| Scripts | `/home/claude/codehero/scripts/` |
| Database Schema | `/home/claude/codehero/database/schema.sql` |
| Migrations | `/home/claude/codehero/database/migrations/` |

### Production (Running)
| Component | Path |
|-----------|------|
| Web App | `/opt/codehero/web/app.py` |
| Daemon | `/opt/codehero/scripts/claude-daemon.py` |
| Templates | `/opt/codehero/web/templates/*.html` |
| Config | `/etc/codehero/system.conf` |
| SSL Certs | `/etc/codehero/ssl/` |
| Logs | `/var/log/codehero/` |

### Important Configuration Files
| File | Purpose |
|------|---------|
| `/etc/codehero/system.conf` | Database credentials, MAX_PARALLEL_PROJECTS |
| `/etc/codehero/global-context.md` | Global context sent to all projects |
| `/home/claude/codehero/config/project-template.md` | Blueprint planner template |

---

## Services

### Service Names (IMPORTANT!)
```bash
# Correct service names
codehero-web      # Flask web interface
codehero-daemon   # Background ticket processor
mysql             # Database
nginx             # Web server
php8.3-fpm        # PHP processor
```

### Commands
```bash
# Check status
systemctl status codehero-web codehero-daemon mysql nginx php8.3-fpm

# Restart after code changes
sudo systemctl restart codehero-web codehero-daemon

# View logs
journalctl -u codehero-web -f
journalctl -u codehero-daemon -f
tail -f /var/log/codehero/daemon.log
tail -f /var/log/codehero/web.log
```

### Ports
| Port | Service | Purpose |
|------|---------|---------|
| 5000 | Flask (internal) | Web app |
| 9453 | Nginx | Admin Panel (SSL) |
| 9867 | Nginx | Project websites (SSL) |
| 3306 | MySQL | Database |

---

## Database

### Connection
```bash
# Read credentials from config
source /etc/codehero/system.conf
mysql -u $DB_USER -p$DB_PASSWORD $DB_NAME

# Or directly
mysql -u claude_user -p claude_knowledge
```

### Important Tables
| Table | Purpose |
|-------|---------|
| `projects` | Project definitions with database credentials |
| `tickets` | Work items/tasks |
| `conversation_messages` | Claude chat history per ticket |
| `execution_sessions` | Daemon run sessions |
| `execution_logs` | Detailed execution logs |
| `daemon_status` | Current daemon state (id=1) |
| `daemon_logs` | System logs |
| `user_messages` | Messages from user to Claude (kill commands) |
| `developers` | Admin users |
| `project_backups` | Backup records |

### Common Queries
```sql
-- System status
SELECT * FROM daemon_status WHERE id=1;

-- Open tickets
SELECT id, ticket_number, title, status FROM tickets WHERE status='open';

-- Stuck tickets (in_progress for too long)
SELECT * FROM tickets WHERE status='in_progress' AND updated_at < DATE_SUB(NOW(), INTERVAL 2 HOUR);

-- Reset stuck tickets
UPDATE tickets SET status='open' WHERE status='in_progress' AND updated_at < DATE_SUB(NOW(), INTERVAL 2 HOUR);

-- View conversation for ticket
SELECT role, content, created_at FROM conversation_messages WHERE ticket_id=? ORDER BY created_at;
```

---

## Features (v2.33.0)

### 1. SmartContext
Intelligent context management that auto-detects project structure and sends only relevant files to Claude.

**How it works:**
- Detects framework (React, Flask, Laravel, etc.)
- Finds relevant files based on task
- Reduces token usage by up to 70%

### 2. AI Failsafe (Watchdog)
Protection against runaway AI sessions:
- Monitors tickets every 30 minutes
- Detects stuck patterns (repeated errors, circular behavior)
- Auto-pauses problematic tickets
- Email notifications when issues detected

### 3. AI Project Manager (Blueprint Planner)
- "Plan with AI" button on Projects page
- Reads `/home/claude/codehero/config/project-template.md`
- Guided questionnaire for requirements
- Generates complete blueprint: tech stack, database schema, API design

### 4. Claude Assistant
Interactive terminal for direct Claude access:
- **AI Model Selection**: Opus, Sonnet (default), Haiku
- **Popup Window**: Open in separate window for multi-monitor
- **Blueprint Mode**: Auto-loads project template

**File:** `web/templates/claude_assistant.html`

### 5. Web Terminal
Full Linux terminal in browser:
- Real PTY via WebSocket
- Popup support for multi-monitor
- Full sudo access (runs as user `claude`)
- 256-color support with xterm.js

**File:** `web/templates/terminal.html`

### 6. Kill Switch Commands
Instant control while Claude is working:
- `/stop` - Pause and wait for correction (shows immediately)
- `/skip` - Stop and reopen ticket (shows immediately)
- `/done` - Force complete ticket (shows immediately)

**Implementation:** Commands saved to `user_messages` table and broadcast via SocketIO

---

## Available Multimedia & Processing Tools

The platform includes powerful tools for image, audio, video, and document processing. Use these to help users with multimedia tasks.

### Image Processing
| Command | Description | Example |
|---------|-------------|---------|
| `convert` | ImageMagick - resize, crop, convert formats | `convert input.png -resize 50% output.jpg` |
| `identify` | Get image info | `identify image.png` |
| `optipng` | Optimize PNG | `optipng -o7 image.png` |
| `jpegoptim` | Optimize JPEG | `jpegoptim --max=85 image.jpg` |
| `cwebp` | Convert to WebP | `cwebp input.png -o output.webp` |
| `rsvg-convert` | SVG to PNG/PDF | `rsvg-convert -w 1024 input.svg -o output.png` |
| `vips` | Fast image processing | `vips resize input.jpg output.jpg 0.5` |

### OCR (Image to Text)
| Command | Description | Example |
|---------|-------------|---------|
| `tesseract` | Extract text from images | `tesseract image.png output -l eng` |
| `tesseract` | Greek OCR | `tesseract image.png output -l ell` |
| `tesseract` | Multiple languages | `tesseract image.png output -l eng+ell` |

### PDF Processing
| Command | Description | Example |
|---------|-------------|---------|
| `pdftotext` | PDF to text | `pdftotext input.pdf output.txt` |
| `pdftoppm` | PDF to images | `pdftoppm -png input.pdf output` |
| `gs` | Ghostscript - compress PDF | `gs -sDEVICE=pdfwrite -dPDFSETTINGS=/ebook -o out.pdf in.pdf` |
| `qpdf` | PDF transformations | `qpdf --rotate=90:1-5 input.pdf output.pdf` |

### Audio Processing
| Command | Description | Example |
|---------|-------------|---------|
| `ffmpeg` | Convert audio | `ffmpeg -i input.wav output.mp3` |
| `sox` | Audio effects | `sox input.wav output.wav reverse` |
| `sox` | Get audio info | `sox --info audio.mp3` |
| `sox` | Trim audio | `sox input.wav output.wav trim 0 30` |

### Video Processing
| Command | Description | Example |
|---------|-------------|---------|
| `ffmpeg` | Convert video | `ffmpeg -i input.mp4 output.webm` |
| `ffmpeg` | Extract audio | `ffmpeg -i video.mp4 -vn audio.mp3` |
| `ffmpeg` | Create thumbnail | `ffmpeg -i video.mp4 -ss 00:00:05 -frames:v 1 thumb.jpg` |
| `ffmpeg` | Resize video | `ffmpeg -i input.mp4 -vf scale=1280:720 output.mp4` |
| `mediainfo` | Get media info | `mediainfo video.mp4` |

### Python Libraries
```python
# Image processing
from PIL import Image
import cv2  # OpenCV

# OCR
import pytesseract
text = pytesseract.image_to_string(Image.open('image.png'), lang='eng+ell')

# PDF to images
from pdf2image import convert_from_path
images = convert_from_path('document.pdf')

# Audio
from pydub import AudioSegment
audio = AudioSegment.from_mp3("input.mp3")
```

---

## Development Workflow

### Making Changes

1. **Edit in source directory:**
   ```
   /home/claude/codehero/
   ```

2. **Deploy to production:**
   ```bash
   sudo cp /home/claude/codehero/web/app.py /opt/codehero/web/
   sudo cp /home/claude/codehero/scripts/claude-daemon.py /opt/codehero/scripts/
   sudo cp -r /home/claude/codehero/web/templates/* /opt/codehero/web/templates/
   ```

3. **Restart services:**
   ```bash
   sudo systemctl restart codehero-web codehero-daemon
   ```

4. **Verify:**
   ```bash
   systemctl status codehero-web --no-pager | head -10
   ```

### Creating New Versions

1. Update these files:
   - `VERSION` - Single source of truth
   - `web/app.py` - VERSION constant
   - `README.md` - Badge version and zip filename
   - `INSTALL.md` - Zip filename and footer
   - `CHANGELOG.md` - New entry at top

2. Create zip:
   ```bash
   cd /home/claude
   zip -r codehero-X.Y.Z.zip codehero -x "*.pyc" -x "*__pycache__*" -x "*.git*"
   ```

---

## Troubleshooting

### Quick Health Check
```bash
echo "=== Health Check ===" && \
systemctl is-active mysql > /dev/null && echo "MySQL: OK" || echo "MySQL: FAILED" && \
systemctl is-active codehero-web > /dev/null && echo "Web: OK" || echo "Web: FAILED" && \
systemctl is-active codehero-daemon > /dev/null && echo "Daemon: OK" || echo "Daemon: FAILED"
```

### Daemon Not Processing Tickets
```bash
# 1. Check if running
sudo systemctl status codehero-daemon

# 2. Check logs
journalctl -u codehero-daemon -n 50

# 3. Check daemon_status table
mysql -u $DB_USER -p$DB_PASSWORD $DB_NAME -e "SELECT * FROM daemon_status"

# 4. Restart
sudo systemctl restart codehero-daemon
```

### Web Panel Not Accessible
```bash
# 1. Check Flask
sudo systemctl status codehero-web

# 2. Check if listening
ss -tlnp | grep 5000

# 3. Check Nginx
sudo systemctl status nginx

# 4. Restart
sudo systemctl restart codehero-web nginx
```

### Tickets Stuck in in_progress
```sql
-- Find stuck tickets
SELECT id, ticket_number, updated_at FROM tickets WHERE status='in_progress';

-- Reset them
UPDATE tickets SET status='open' WHERE status='in_progress' AND updated_at < DATE_SUB(NOW(), INTERVAL 2 HOUR);

-- Mark sessions as stuck
UPDATE execution_sessions SET status='stuck', ended_at=NOW() WHERE status='running' AND started_at < DATE_SUB(NOW(), INTERVAL 2 HOUR);
```

### Claude Assistant Not Starting
```bash
# Check if Claude Code CLI is installed
which claude

# If not installed:
/opt/codehero/scripts/install-claude-code.sh

# Check API key
cat ~/.claude/.credentials.json
```

### WebSocket Connection Issues
```bash
# Check if Flask SocketIO is running
netstat -tlnp | grep 5000

# Check Nginx proxy config
cat /etc/nginx/sites-available/codehero-admin

# Restart services
sudo systemctl restart codehero-web nginx
```

---

## Code Architecture

### Web App (app.py)
- Flask + Flask-SocketIO
- Routes: `/dashboard`, `/projects`, `/tickets`, `/console`, `/terminal`, `/claude-assistant`
- WebSocket namespaces for real-time updates
- Session-based authentication with bcrypt

### Daemon (claude-daemon.py)
- Multi-worker ticket processor
- Uses `select.select()` for non-blocking I/O
- Checks `user_messages` table for kill commands
- Creates execution sessions and logs

### Key Patterns

**Broadcasting to rooms:**
```python
socketio.emit('new_message', msg, room=f'ticket_{ticket_id}')
socketio.emit('new_message', msg, room='console')
```

**Non-blocking I/O:**
```python
ready, _, _ = select.select([process.stdout], [], [], 1.0)
```

**Database cursor:**
```python
conn = get_db()
cursor = conn.cursor(dictionary=True)
cursor.execute("SELECT * FROM tickets WHERE id = %s", (ticket_id,))
ticket = cursor.fetchone()
cursor.close(); conn.close()
```

---

## Template Files

| Template | Purpose |
|----------|---------|
| `dashboard.html` | Main dashboard with stats |
| `projects.html` | Project list, create/edit, Plan with AI button |
| `project_detail.html` | Single project view with tickets |
| `tickets_list.html` | All tickets with filters |
| `ticket_detail.html` | Ticket chat interface |
| `console.html` | Live console for all tickets |
| `terminal.html` | Linux terminal (xterm.js) |
| `claude_assistant.html` | Interactive Claude chat with model selection |
| `history.html` | Execution history |
| `session_detail.html` | Session details with logs |

---

## API Endpoints

### Web Routes
| Method | Path | Description |
|--------|------|-------------|
| GET | `/login` | Login page |
| GET | `/dashboard` | Main dashboard |
| GET | `/tickets` | Tickets list |
| GET | `/ticket/<id>` | Ticket detail |
| GET | `/projects` | Projects list |
| GET | `/project/<id>` | Project detail |
| GET | `/console` | Live console |
| GET | `/terminal` | Web terminal |
| GET | `/claude-assistant` | Claude Assistant |
| GET | `/history` | Execution history |

### API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/projects` | Create project |
| PUT | `/api/project/<id>` | Update project |
| POST | `/api/tickets` | Create ticket |
| POST | `/api/ticket/<id>/approve` | Approve ticket |
| POST | `/api/ticket/<id>/reopen` | Reopen ticket |
| POST | `/api/send_message` | Send message to ticket |
| GET | `/api/daemon/status` | Daemon status |

---

## Emergency Procedures

### Stop All Processing
```bash
sudo systemctl stop codehero-daemon
```

### Reset Everything
```sql
UPDATE tickets SET status='open' WHERE status='in_progress';
UPDATE daemon_status SET status='stopped', current_ticket_id=NULL WHERE id=1;
UPDATE execution_sessions SET status='stopped', ended_at=NOW() WHERE status='running';
```

### Database Backup
```bash
source /etc/codehero/system.conf
mysqldump -u $DB_USER -p$DB_PASSWORD $DB_NAME > /tmp/backup_$(date +%Y%m%d_%H%M%S).sql
```

---

## Documentation Files

| File | Description |
|------|-------------|
| `README.md` | Main documentation, features, installation |
| `INSTALL.md` | Detailed installation guide |
| `CLAUDE_OPERATIONS.md` | Operations and troubleshooting guide |
| `CLAUDE_DEV_NOTES.md` | Development notes for Claude |
| `CLAUDE.md` | Development workflow instructions |
| `docs/USER_GUIDE.md` | User guide with screenshots |
| `docs/VM_INSTALLATION.md` | VM installation for all platforms |
| `CHANGELOG.md` | Version history |

---

## Getting Help

When users ask questions, check these files:

1. **Platform usage** - `docs/USER_GUIDE.md`
2. **Troubleshooting** - `CLAUDE_OPERATIONS.md`
3. **Development** - `CLAUDE_DEV_NOTES.md`, `CLAUDE.md`
4. **Installation** - `INSTALL.md`, `docs/VM_INSTALLATION.md`
5. **Features** - `README.md`, `CHANGELOG.md`

---

*Last Updated: 2026-01-12*
*Version: 2.53.0*
