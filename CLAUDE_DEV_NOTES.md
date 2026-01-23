# Claude Development Notes

Notes for Claude when working on CodeHero. Reference this file for development workflow.

---

## Quick Reference

### File Locations

| Purpose | Source (edit here) | Production (deployed) |
|---------|-------------------|----------------------|
| Web App | `/home/claude/codehero/web/app.py` | `/opt/codehero/web/app.py` |
| Daemon | `/home/claude/codehero/scripts/claude-daemon.py` | `/opt/codehero/scripts/claude-daemon.py` |
| Templates | `/home/claude/codehero/web/templates/*.html` | `/opt/codehero/web/templates/*.html` |
| Config | `/home/claude/codehero/config/` | `/opt/codehero/config/` |
| Scripts | `/home/claude/codehero/scripts/` | `/opt/codehero/scripts/` |

### Remote Server (Optional)

```
Remote server is not always available.
User will provide IP and credentials when needed.
Production path: /opt/codehero/
```

**Sync to Remote:** (replace REMOTE_IP and PASSWORD with values from user)
```bash
sshpass -p 'PASSWORD' scp -o StrictHostKeyChecking=no /home/claude/codehero/web/app.py root@REMOTE_IP:/opt/codehero/web/
sshpass -p 'PASSWORD' scp -o StrictHostKeyChecking=no /home/claude/codehero/scripts/claude-daemon.py root@REMOTE_IP:/opt/codehero/scripts/
```

**Check Remote Sync:**
```bash
sshpass -p 'PASSWORD' ssh -o StrictHostKeyChecking=no root@REMOTE_IP "cat /opt/codehero/scripts/claude-daemon.py" | diff /home/claude/codehero/scripts/claude-daemon.py -
```

**Restart Remote Services:**
```bash
sshpass -p 'PASSWORD' ssh -o StrictHostKeyChecking=no root@REMOTE_IP "systemctl restart codehero-web codehero-daemon"
```

### Services

```bash
# Check status
systemctl status codehero-web codehero-daemon

# Restart after changes
sudo systemctl restart codehero-web    # Web interface
sudo systemctl restart codehero-daemon  # Background worker

# View logs
journalctl -u codehero-web -f
journalctl -u codehero-daemon -f
tail -f /var/log/codehero/daemon.log
tail -f /var/log/codehero/web.log
```

### Database

- **Type:** MySQL
- **Name:** `claude_knowledge`
- **Config:** `/etc/codehero/system.conf`
- **Schema:** `/home/claude/codehero/database/schema.sql`
- **Migrations:** `/home/claude/codehero/database/migrations/`

```bash
# Access database
mysql -u claude_user -p claude_knowledge

# Important tables
- projects          # Project definitions
- tickets           # Tasks/tickets
- conversation_messages  # Chat history
- execution_sessions     # Claude execution sessions
- execution_logs         # Daemon logs
- daemon_logs           # System logs
- user_messages         # User input queue for daemon
```

---

## Development Workflow

### 1. Make Changes

Always edit in SOURCE directory:
```
/home/claude/codehero/
```

### 2. Deploy to Production

```bash
# Copy app.py
sudo cp /home/claude/codehero/web/app.py /opt/codehero/web/

# Copy daemon
sudo cp /home/claude/codehero/scripts/claude-daemon.py /opt/codehero/scripts/

# Copy templates
sudo cp -r /home/claude/codehero/web/templates/* /opt/codehero/web/templates/

# Copy scripts
sudo cp /home/claude/codehero/scripts/*.sh /opt/codehero/scripts/
```

### 3. Restart Services (ALWAYS!)

**IMPORTANT:** Always restart services after ANY change - otherwise changes won't be visible!

```bash
sudo systemctl restart codehero-web codehero-daemon
```

### 4. Verify

```bash
systemctl status codehero-web --no-pager | head -10
```

---

## Creating New Versions

### Version Files to Update

1. **VERSION** - Single source of truth
   ```bash
   echo "X.Y.Z" > /home/claude/codehero/VERSION
   ```

2. **web/app.py** - VERSION constant at top
   ```python
   VERSION = "X.Y.Z"
   ```

3. **README.md** - Badge and zip filenames
   - Line ~13: version badge
   - Lines with `unzip codehero-X.Y.Z.zip`

4. **INSTALL.md** - Zip filename and footer
   - `unzip` commands
   - Footer: `**Version:** X.Y.Z`

5. **CHANGELOG.md** - New entry at TOP
   ```markdown
   ## [X.Y.Z] - YYYY-MM-DD

   ### Added
   - Feature 1
   - Feature 2

   ### Fixed
   - Bug fix 1
   ```

### Create Release Zip

```bash
cd /home/claude

# DON'T delete old zips - they are backups!
zip -r codehero-X.Y.Z.zip codehero \
    -x "*.pyc" -x "*__pycache__*" -x "*.git*"
```

### Git Commit, Tag, and Push

```bash
# Commit changes
git add -A
git commit -m "Release vX.Y.Z - Description"
git push origin main

# Create and push tag
git tag -a vX.Y.Z -m "Release vX.Y.Z - Description"
git push origin vX.Y.Z
```

### Create GitHub Release

```bash
gh release create vX.Y.Z /home/claude/codehero-X.Y.Z.zip \
    --title "vX.Y.Z - Description" \
    --notes "### Fixed
- Bug fix 1

### Changed
- Change 1"
```

### Version Numbering

- **Major (X):** Breaking changes, major rewrites
- **Minor (Y):** New features, significant improvements
- **Patch (Z):** Bug fixes, small improvements

---

## Key Components

### Web App (app.py)

- Flask + SocketIO
- Routes: `/dashboard`, `/projects`, `/tickets`, `/console`, `/terminal`, `/claude-assistant`
- WebSocket: Real-time updates, terminal sessions
- Auth: Session-based, bcrypt passwords

### Daemon (claude-daemon.py)

- Background worker that processes tickets
- Runs Claude CLI for each ticket
- Uses `select.select()` for non-blocking I/O (important for kill commands)
- Checks `user_messages` table for /stop command

### Templates

| Template | Purpose |
|----------|---------|
| dashboard.html | Main dashboard, stats |
| projects.html | Project list, create/edit |
| project_detail.html | Single project view |
| tickets_list.html | All tickets |
| ticket_detail.html | Ticket chat interface |
| console.html | Live console, all tickets |
| terminal.html | Linux terminal (xterm.js) |
| claude_assistant.html | Interactive Claude chat |
| history.html | Execution history |

### Important Patterns

**Broadcast to rooms:**
```python
socketio.emit('new_message', msg, room=f'ticket_{ticket_id}')
socketio.emit('new_message', msg, room='console')
```

**Non-blocking command check (daemon):**
```python
ready, _, _ = select.select([process.stdout], [], [], 1.0)
```

**Database query with dictionary cursor:**
```python
conn = get_db()
cursor = conn.cursor(dictionary=True)
cursor.execute("SELECT * FROM tickets WHERE id = %s", (ticket_id,))
ticket = cursor.fetchone()
cursor.close(); conn.close()
```

---

## Common Tasks

### Add New Page

1. Add route in `app.py`
2. Create template in `web/templates/`
3. Add to navigation in all templates (search for `<a href="/console">`)
4. Deploy and restart

### Add Database Column

**For new installations:** Update `database/schema.sql` directly (this is the baseline)

**For existing installations (upgrades):**
1. Create migration in `database/migrations/` (e.g., `001_add_column.sql`)
2. Migrations run ONLY via `upgrade.sh` - never manually
3. Update relevant queries in app.py/daemon

**Important:**
- `schema.sql` = complete database for fresh installs (setup.sh)
- `migrations/` = incremental changes for upgrades only (upgrade.sh)

### Add WebSocket Event

1. Add handler in app.py: `@socketio.on('event_name')`
2. Add client handler in template: `socket.on('event_name', ...)`
3. Emit from server: `socketio.emit('event_name', data, room='...')`

### Debug Issues

```bash
# Check web logs
tail -f /var/log/codehero/web.log

# Check daemon logs
tail -f /var/log/codehero/daemon.log

# Check systemd logs
journalctl -u codehero-web -f

# Test database
mysql -u claude_user -p claude_knowledge -e "SELECT * FROM tickets ORDER BY id DESC LIMIT 5"
```

---

## Ticket Execution Logic (v2.80.11+)

### Execution Order

Tickets are selected for execution based on:
1. **Status:** Must be `open`, `new`, or `pending`
2. **Parent:** If has `parent_ticket_id`, parent must be `done` or `skipped`
3. **Dependencies:** ALL dependencies must be `done` or `skipped`
4. **Sequence Order:** Lower `sequence_order` runs first
5. **Parallel:** Tickets with **same sequence_order** run in parallel (max 5)
6. **Forced Queue:** `is_forced=1` tickets get priority

### Parallel Execution

**Two levels of parallelism:**

| Level | Max Parallel | Scope |
|-------|--------------|-------|
| Projects | 10 | Different projects run simultaneously |
| Tickets | 5 | Same `sequence_order` within a project |

**Per Project - Tickets with same `sequence_order`:**
```
Project A:
  sequence_order=1: [Ticket 1, 2, 3]  → run in parallel (max 5)
  sequence_order=2: [Ticket 4]        → waits for 1,2,3 to finish
  sequence_order=3: [Ticket 5, 6]     → run in parallel after 4

Project B: (runs simultaneously with Project A)
  sequence_order=1: [Ticket 7]
  sequence_order=2: [Ticket 8, 9]
```

**Note:** `sequence_order` is **per project**, not global.

**Use cases:**
- Independent setup tasks (install deps, create folders)
- Multiple tests that don't conflict
- Parallel feature development in different files

### Key Concepts

| Concept | Purpose | Blocks Execution? |
|---------|---------|-------------------|
| `sequence_order` | Order + parallel grouping | NO - same seq runs parallel |
| `parent_ticket_id` | Context + implicit dependency | **YES** - parent must be done |
| `depends_on` (ticket_dependencies) | Explicit dependency | **YES** - must be done/skipped |
| `deps_include_awaiting` | Controls auto-review behavior | NO - affects review only |

### Parent Tickets (parent_ticket_id)

**BLOCKS execution.** Child ticket waits for parent to be `done` or `skipped`.

- Parent is an **implicit dependency** - no need to add explicit dependency
- Child inherits context from ALL ancestors (recursive)
- Child's summary includes ancestor summaries

```sql
-- Sub-ticket that waits for parent (automatic)
INSERT INTO tickets (parent_ticket_id, ...) VALUES (1, ...);
-- Child will NOT run until parent (ticket 1) is 'done' or 'skipped'

-- Sub-ticket with additional dependencies
INSERT INTO tickets (parent_ticket_id, ...) VALUES (1, ...);
INSERT INTO ticket_dependencies (ticket_id, depends_on_ticket_id) VALUES (child_id, other_ticket_id);
-- Child waits for BOTH parent AND other_ticket
```

### Dependencies (ticket_dependencies table)

**Explicit dependencies** for tickets that need to wait for non-parent tickets.

```sql
-- Ticket 2 depends on Ticket 1 (not a parent-child relationship)
INSERT INTO ticket_dependencies (ticket_id, depends_on_ticket_id) VALUES (2, 1);
```

### deps_include_awaiting (Relaxed vs Strict Mode)

**Does NOT affect execution order.** Only affects auto-review behavior.

| Value | Mode | Auto-Review Behavior |
|-------|------|---------------------|
| `0` | Strict | Waits for user to close `awaiting_input` tickets |
| `1` | Relaxed | Auto-closes `awaiting_input` tickets after delay |

### Auto-Review System

When a ticket completes (`completed` result), it goes to `awaiting_input` status.

**In Relaxed Mode (deps_include_awaiting=1):**
1. Haiku classifies the result (COMPLETED/QUESTION/ERROR)
2. If "COMPLETED" → auto-closes to `done`
3. If "QUESTION/ERROR" → stays `awaiting_input`
4. Delay: `AUTO_REVIEW_DELAY_SECONDS` (default: 10 seconds)
5. Summary NOT generated here (lazy generation when child starts)

**In Strict Mode (deps_include_awaiting=0):**
- No auto-review
- User must manually close tickets

**Manual Close (from web):**
- Just closes the ticket (no summary generation)

### Summary Generation (Lazy - On Demand)

Summaries are generated **only when needed** - when a child ticket starts:

1. Child ticket starts → checks if ancestors have `result_summary`
2. If ancestor has NO summary → Haiku generates it from last 50 messages
3. Summary saved to ancestor's `result_summary`
4. Child receives context with all ancestor summaries

**Haiku Summary Settings:**
- Last 50 messages from conversation
- Each message truncated to 500 chars
- Total context max 15,000 chars
- Output summary max 500 chars

**Context format for child:**
```
=== PARENT TICKET CONTEXT (2 levels) ===
[Root] PROJ-0001 - Setup database
  Description: Create MySQL schema...
  Result: Created users, products, orders tables with indexes...

[Level 1] PROJ-0002 - Build auth
  Description: Implement authentication...
  Result: JWT auth with login/logout, password reset via email...

This is a sub-task. Use the parent context to understand the overall goal.
==================================================
```

- Summary stored in `result_summary` field (max 2000 chars)
- Only generated once per ticket (cached)
- Tickets without children never generate summary (saves Haiku calls)

### Execution Flow Example

```
Project with deps_include_awaiting=1 (relaxed):

Ticket 1 (seq=1): Setup      → runs first
Ticket 2 (seq=2): depends on 1  → waits for 1 to be 'done'
Ticket 3 (seq=3): no deps    → can run after 1 finishes

With sub-tickets (parent = implicit dependency):
Parent (seq=1): Main task     → runs first
Child (seq=2, parent_ticket_id=Parent):
  → waits for parent to be 'done' (automatic)
  → gets parent's context and summary
```

### SQL Query (get_next_ticket)

```sql
SELECT * FROM tickets t
WHERE t.project_id = ? AND t.status IN ('open', 'new', 'pending')
  AND NOT EXISTS (
    -- Skip if has unfinished dependencies
    SELECT 1 FROM ticket_dependencies td
    JOIN tickets dt ON dt.id = td.depends_on_ticket_id
    WHERE td.ticket_id = t.id
      AND dt.status NOT IN ('done', 'skipped')
  )
  AND (
    -- Parent must be done/skipped (implicit dependency)
    t.parent_ticket_id IS NULL
    OR EXISTS (
      SELECT 1 FROM tickets pt
      WHERE pt.id = t.parent_ticket_id
        AND pt.status IN ('done', 'skipped')
    )
  )
ORDER BY t.is_forced DESC, t.sequence_order ASC, t.id ASC
LIMIT 1
```

---

## Current Features (v2.80.11)

- Project & Ticket Management
- Real-time Chat with Claude
- AI Model Selection (Opus/Sonnet/Haiku)
- Kill Switch (/stop command)
- Web Terminal (full Linux shell)
- Claude Assistant with popup support
- Blueprint Planner for project design
- Console for monitoring all activity
- Execution History & Stats

---

## Files NOT to Delete

- `/home/claude/codehero-*.zip` - Version backups
- `/etc/codehero/system.conf` - Database credentials
- `/home/claude/.claude/` - Claude CLI config

---

## Tips

1. **ALWAYS restart services after changes** - changes won't be visible without restart!
2. Always read files before editing
3. Test changes locally before deploying
4. Check service status after restart
5. Keep old zip files as backups
6. Update CHANGELOG for every release
7. Broadcast to both ticket room AND console room for real-time updates
8. Use `select.select()` for non-blocking I/O in daemon

---

*Last Updated: 2026-01-22*
*Current Version: 2.80.10*
