# Semi-Autonomous Mode Specification

## Overview

A new execution mode that provides a smart sandbox - allowing Claude to work freely within the project while requiring approval for potentially risky operations.

```
┌─────────────────┬─────────────────┬─────────────────┐
│   autonomous    │ semi-autonomous │   supervised    │
├─────────────────┼─────────────────┼─────────────────┤
│ Όλα επιτρέπονται│ Smart sandbox   │ Ρωτάει για όλα  │
│ χωρίς ερώτηση   │ με rules        │                 │
└─────────────────┴─────────────────┴─────────────────┘
```

---

## Execution Modes Summary

| Mode | Description | Use Case |
|------|-------------|----------|
| `autonomous` | Full access, no prompts | Trusted tasks, experienced users |
| `semi-autonomous` | Smart sandbox with rules | **Default for most projects** |
| `supervised` | Asks for everything | Critical/sensitive projects |

---

## Semi-Autonomous Mode Rules

### ✅ Auto-Approve (No prompts)

#### File Operations (within project path)

| Operation | Allowed | Examples |
|-----------|---------|----------|
| Read files | ✅ | Any file in project |
| Create files | ✅ | `*.php`, `*.js`, `*.css`, configs |
| Edit files | ✅ | Any file in project |
| Delete files | ✅ | Any file in project |
| **EXCEPTION** | ❌ | `.git/` folder is PROTECTED |

#### Bash Commands - Safe Operations

| Category | Commands | Notes |
|----------|----------|-------|
| **Run scripts** | `npm run *`, `yarn *` | Any script from package.json |
| **Run scripts** | `php artisan *` | EXCEPT `migrate`, `db:*` |
| **Run scripts** | `composer run-script *` | Defined scripts only |
| **Install deps** | `npm install`, `npm ci` | From lockfile only (no package name) |
| **Install deps** | `composer install` | From lockfile only |
| **Build** | `npm run build`, `npm run dev` | Build commands |
| **Build** | `composer dump-autoload` | Autoloader |
| **Testing** | `npm test`, `phpunit`, `pest` | Test runners |
| **Testing** | `playwright test`, `cypress` | E2E testing |
| **Linting** | `npm run lint`, `eslint`, `phpcs` | Code quality |

#### Git - Read Only

| Command | Allowed |
|---------|---------|
| `git status` | ✅ |
| `git log` | ✅ |
| `git diff` | ✅ |
| `git branch` | ✅ |
| `git show` | ✅ |

---

### ❓ Requires Approval (Prompts user)

#### Package Management - New Packages

| Command | Why |
|---------|-----|
| `npm install <package>` | Security - new dependency |
| `npm install <package> --save-dev` | Security - new dependency |
| `composer require <package>` | Security - new dependency |
| `npm update` | May change versions |
| `composer update` | May change versions |

#### Database Operations

| Command | Why |
|---------|-----|
| `php artisan migrate` | Modifies database schema |
| `php artisan migrate:fresh` | Destroys data |
| `php artisan db:seed` | Modifies data |
| Direct SQL queries | Data modification |

#### Git - Write Operations

| Command | Why |
|---------|-----|
| `git add` | Staging changes |
| `git commit` | Creating history |
| `git push` | Remote changes |
| `git pull` | May cause conflicts |
| `git merge` | May cause conflicts |
| `git checkout <branch>` | Switching context |
| `git stash` | Modifying state |

#### System Services

| Command | Why |
|---------|-----|
| `systemctl restart *` | Service disruption |
| `systemctl stop *` | Service disruption |
| `service * restart` | Service disruption |

#### Network Operations

| Command | Why |
|---------|-----|
| `curl` (to external APIs) | Data exfiltration risk |
| `wget` | Downloading unknown content |
| `ssh` | Remote access |

---

### ❌ Always Blocked

#### Protected Paths Within Project

| Path | Reason |
|------|--------|
| `.git/` | Backup/version control protection |
| `.git/*` | All git internals |

**Note:** `git init` is also blocked as it would create `.git/`

#### Paths Outside Project

| Path | Reason |
|------|--------|
| `/opt/codehero/` | System installation |
| `/etc/` | System configuration |
| `~/.ssh/` | SSH keys |
| `~/.aws/` | AWS credentials |
| `/var/www/projects/<other>/` | Other projects |

#### System Commands

| Command | Reason |
|---------|--------|
| `sudo *` | Privilege escalation |
| `apt *`, `apt-get *` | System packages |
| `yum *`, `dnf *` | System packages |
| `rm -rf /` | Obviously |
| `chmod 777` | Security risk |
| `chown` | Ownership changes |

---

## How It Works - Technical Architecture

### Current System (2 modes)

```
┌─────────────────────────────────────────────────────────────────┐
│ SUPERVISED MODE                                                 │
│                                                                 │
│ Claude runs WITHOUT --dangerously-skip-permissions              │
│     ↓                                                           │
│ Claude wants to Edit → Requests permission                      │
│     ↓                                                           │
│ Non-interactive → permission_denials captured                   │
│     ↓                                                           │
│ Daemon catches denial → pending_permission in DB                │
│     ↓                                                           │
│ UI shows Allow/Deny banner                                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ AUTONOMOUS MODE                                                 │
│                                                                 │
│ Claude runs WITH --dangerously-skip-permissions                 │
│     ↓                                                           │
│ Does everything without asking                                  │
└─────────────────────────────────────────────────────────────────┘
```

### New System (3 modes) - Using PreToolUse Hook

```
┌─────────────────────────────────────────────────────────────────┐
│ SEMI-AUTONOMOUS MODE                                            │
│                                                                 │
│ Claude runs WITHOUT --dangerously-skip-permissions              │
│     ↓                                                           │
│ Claude wants to do something                                    │
│     ↓                                                           │
│ PreToolUse Hook runs FIRST (before Claude's permission system)  │
│     ↓                                                           │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Hook Logic (semi_autonomous_hook.py):                       │ │
│ │                                                             │ │
│ │ if is_safe(tool, input):      → return ALLOW (auto-approve)│ │
│ │ elif is_blocked(tool, input): → return DENY  (block)       │ │
│ │ else:                         → return ASK   (ask user)    │ │
│ └─────────────────────────────────────────────────────────────┘ │
│     ↓                                                           │
│ ALLOW: Executes without prompt                                  │
│ DENY:  Blocked, Claude gets error message                       │
│ ASK:   Goes to pending_permission flow (same as supervised)     │
└─────────────────────────────────────────────────────────────────┘
```

### Hook Input/Output

**Input (JSON via stdin):**
```json
{
  "session_id": "abc123",
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": {
    "command": "npm install axios",
    "description": "Install axios package"
  },
  "cwd": "/var/www/projects/myproject"
}
```

**Output (JSON via stdout):**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "Safe operation: npm install within project"
  }
}
```

**Permission Decision Values:**
- `"allow"` - Auto-approve, no prompt
- `"deny"` - Block with error message
- `"ask"` - Use default permission flow (prompts user)

---

## Implementation Plan

### Step 1: Create Hook Script

**File:** `/opt/codehero/scripts/semi_autonomous_hook.py`

```python
#!/usr/bin/env python3
"""
Semi-autonomous mode hook for CodeHero.
Filters tool requests based on safety rules.
"""
import sys
import json
import os
import re

def main():
    # Read input from stdin
    input_data = json.load(sys.stdin)

    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})
    cwd = input_data.get('cwd', '')

    # Get project path from environment (set by daemon)
    project_path = os.environ.get('CODEHERO_PROJECT_PATH', cwd)

    decision, reason = evaluate_permission(tool_name, tool_input, project_path)

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason
        }
    }

    print(json.dumps(output))

def evaluate_permission(tool_name, tool_input, project_path):
    """
    Returns: (decision, reason)
    decision: "allow" | "deny" | "ask"
    """

    # === FILE OPERATIONS ===
    if tool_name in ['Read', 'Edit', 'Write']:
        file_path = tool_input.get('file_path', '')
        return evaluate_file_operation(tool_name, file_path, project_path)

    # === BASH COMMANDS ===
    if tool_name == 'Bash':
        command = tool_input.get('command', '')
        return evaluate_bash_command(command, project_path)

    # === OTHER TOOLS ===
    # Default: ask for permission
    return ("ask", f"Unknown tool: {tool_name}")

def evaluate_file_operation(tool_name, file_path, project_path):
    """Evaluate file read/edit/write operations"""

    # Block .git folder
    if '/.git/' in file_path or file_path.endswith('/.git'):
        return ("deny", "Protected: .git folder is read-only (backup)")

    # Block paths outside project
    if not file_path.startswith(project_path):
        # Check for blocked system paths
        blocked_paths = ['/etc/', '/opt/codehero/', '/.ssh/', '/.aws/']
        for blocked in blocked_paths:
            if blocked in file_path:
                return ("deny", f"Blocked: {blocked} is protected")
        return ("deny", f"Outside project path: {project_path}")

    # Allow file operations within project
    return ("allow", f"Safe: {tool_name} within project")

def evaluate_bash_command(command, project_path):
    """Evaluate bash commands"""

    # === ALWAYS BLOCKED ===
    blocked_patterns = [
        r'^sudo\s',
        r'^apt\s', r'^apt-get\s',
        r'^yum\s', r'^dnf\s',
        r'^systemctl\s',
        r'^service\s',
        r'^chmod\s+777',
        r'^chown\s',
        r'^rm\s+-rf\s+/',
        r'^git\s+init',
    ]
    for pattern in blocked_patterns:
        if re.search(pattern, command):
            return ("deny", f"Blocked: {pattern.strip('^').strip('s')} not allowed")

    # === AUTO-APPROVE: Safe commands ===
    safe_patterns = [
        # NPM/Yarn - run scripts, install from lockfile
        r'^npm\s+run\s',
        r'^npm\s+test',
        r'^npm\s+install$',  # No package name = from lockfile
        r'^npm\s+ci',
        r'^yarn\s+run\s',
        r'^yarn\s+test',
        r'^yarn\s+install$',
        r'^yarn$',

        # Composer - run scripts, install from lockfile
        r'^composer\s+install$',
        r'^composer\s+dump-autoload',
        r'^composer\s+run-script\s',

        # PHP Artisan (except migrate/db)
        r'^php\s+artisan\s+(?!migrate|db:)',

        # Testing
        r'^phpunit',
        r'^pest',
        r'^playwright\s+test',
        r'^cypress\s+run',
        r'^npx\s+playwright',
        r'^npx\s+cypress',

        # Linting
        r'^eslint',
        r'^phpcs',
        r'^php-cs-fixer',

        # Git read-only
        r'^git\s+status',
        r'^git\s+log',
        r'^git\s+diff',
        r'^git\s+branch',
        r'^git\s+show',

        # Build tools
        r'^npm\s+run\s+build',
        r'^npm\s+run\s+dev',
        r'^npx\s+',
    ]
    for pattern in safe_patterns:
        if re.search(pattern, command):
            return ("allow", f"Safe command: matches {pattern}")

    # === REQUIRES APPROVAL ===
    # npm install <package>, composer require, git write, migrate, etc.
    return ("ask", "Requires approval: not in safe list")

if __name__ == '__main__':
    main()
```

### Step 2: Create Settings Generator

**In daemon (claude-daemon.py):**

```python
def create_semi_autonomous_settings(self, project_path):
    """Create .claude/settings.json for semi-autonomous mode"""

    settings_dir = os.path.join(project_path, '.claude')
    os.makedirs(settings_dir, exist_ok=True)

    settings = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": ".*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "/opt/codehero/scripts/semi_autonomous_hook.py"
                        }
                    ]
                }
            ]
        }
    }

    settings_file = os.path.join(settings_dir, 'settings.json')
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)

    return settings_file
```

### Step 3: Update Daemon Logic

```python
# In run_claude() method:

if execution_mode == 'supervised':
    self.log("Supervised mode: Claude will ask for permission on all operations")
elif execution_mode == 'semi-autonomous':
    self.log("Semi-autonomous mode: Smart sandbox with rules")
    # Create hook settings
    self.create_semi_autonomous_settings(work_path)
    # Set environment variable for hook
    claude_env['CODEHERO_PROJECT_PATH'] = work_path
else:  # autonomous
    cmd.append('--dangerously-skip-permissions')
```

### Step 4: Database Migration

```sql
-- File: database/migrations/X.XX.X_semi_autonomous_mode.sql

-- Update tickets table
ALTER TABLE tickets
MODIFY COLUMN execution_mode ENUM('autonomous', 'semi-autonomous', 'supervised')
DEFAULT 'autonomous';

-- Update projects table
ALTER TABLE projects
MODIFY COLUMN default_execution_mode ENUM('autonomous', 'semi-autonomous', 'supervised')
DEFAULT 'autonomous';

-- Note: Default remains 'autonomous' for backward compatibility
-- Can be changed to 'semi-autonomous' after testing
```

### Step 5: UI Updates

**ticket_detail.html / project forms:**
- Add "Semi-autonomous" option to execution mode dropdown
- Add tooltip explaining each mode

---

## Implementation Details

### Project Path Structure

```
Project path: /var/www/projects/myproject/
                    │
                    ├── app/           ✅ Full access
                    ├── src/           ✅ Full access
                    ├── public/        ✅ Full access
                    ├── resources/     ✅ Full access
                    ├── tests/         ✅ Full access
                    ├── package.json   ✅ Full access
                    ├── composer.json  ✅ Full access
                    ├── .env           ✅ Full access
                    ├── .env.example   ✅ Full access
                    └── .git/          ❌ BLOCKED (backup)
```

### Working Directory Enforcement

All bash commands MUST run with the project folder as working directory:

```python
# In daemon
subprocess.run(
    command,
    cwd=project.web_path or project.app_path,  # ENFORCED
    ...
)
```

### Claude Code Configuration

For semi-autonomous mode, generate a `.claude/settings.json` in the project:

```json
{
  "permissions": {
    "allow": [
      "Read(**)",
      "Edit(**)",
      "Write(**)",
      "Bash(npm run *)",
      "Bash(npm install)",
      "Bash(npm test)",
      "Bash(composer install)",
      "Bash(php artisan *)",
      "Bash(git status)",
      "Bash(git log *)",
      "Bash(git diff *)"
    ],
    "deny": [
      "Read(.git/**)",
      "Edit(.git/**)",
      "Write(.git/**)",
      "Bash(git init)",
      "Bash(sudo *)",
      "Bash(apt *)",
      "Bash(systemctl *)"
    ]
  }
}
```

### Approval Flow

When a command requires approval:

1. Claude pauses execution
2. Ticket status changes to `awaiting_input`
3. User sees prompt in UI: "Claude wants to run: `npm install axios`. Allow?"
4. User approves/denies
5. Response sent back to Claude
6. Execution continues or aborts

---

## Database Schema Changes

```sql
-- execution_mode enum update
ALTER TABLE tickets
MODIFY COLUMN execution_mode ENUM('autonomous', 'semi-autonomous', 'supervised')
DEFAULT 'semi-autonomous';

ALTER TABLE projects
MODIFY COLUMN default_execution_mode ENUM('autonomous', 'semi-autonomous', 'supervised')
DEFAULT 'semi-autonomous';
```

---

## UI Changes

### Ticket Creation

```
Execution Mode:
○ Autonomous (full access, no prompts)
● Semi-autonomous (smart sandbox) [DEFAULT]
○ Supervised (asks for everything)
```

### Project Settings

```
Default Execution Mode:
[Semi-autonomous ▼]

□ Allow git write operations without prompt
□ Allow database migrations without prompt
□ Allow new package installation without prompt
```

---

## Migration Path

1. Existing `supervised` tickets → remain `supervised`
2. Existing `autonomous` tickets → remain `autonomous`
3. New tickets default to `semi-autonomous`
4. Projects can set their default mode

---

## "Approve Similar" Feature

When a permission prompt appears, users can click **"Approve All Similar"** to auto-approve similar operations in the future.

### How It Works

1. User approves `npm install express` with "Approve All Similar"
2. System stores pattern `{"tool": "Bash", "pattern": "npm *"}` in `approved_permissions`
3. Hook reads `approved_permissions` from database
4. Future `npm install axios` matches pattern → auto-approved

### Pattern Examples

| Original Command | Generated Pattern | Future Auto-Approved |
|-----------------|-------------------|---------------------|
| `npm install express` | `npm *` | Any npm command |
| `pip install requests` | `pip *` | Any pip command |
| `composer require guzzle` | `composer *` | Any composer command |

### Technical Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ Hook receives tool request                                      │
│     ↓                                                           │
│ Read approved_permissions from DB (via CODEHERO_TICKET_ID)      │
│     ↓                                                           │
│ Check if matches any approved pattern                           │
│     ↓                                                           │
│ Match found? → Return ALLOW (auto-approve)                      │
│ No match?    → Continue with normal evaluation                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Status

### Completed ✅

- [x] Create `/opt/codehero/scripts/semi_autonomous_hook.py`
- [x] Add `create_semi_autonomous_settings()` to daemon
- [x] Update `run_claude()` logic for semi-autonomous mode
- [x] Create database migration (`2.79.0_semi_autonomous_mode.sql`)
- [x] Update UI dropdowns (ticket creation, project settings)
- [x] Real-time permission banner via WebSocket
- [x] "Approve All Similar" feature with pattern matching
- [x] Hook reads approved patterns from database
- [x] Test: auto-approve scenarios
- [x] Test: blocked scenarios
- [x] Test: ask scenarios (approval flow)
- [x] Documentation update

### Future Enhancements

- [ ] Per-project allowlist customization UI
- [ ] Pattern management UI (view/delete approved patterns)
- [ ] Risk scoring for commands
- [ ] Command history with approval status

---

## Version

- Spec version: 2.0
- Created: 2025-01-20
- Updated: 2026-01-20
- Status: **IMPLEMENTED** ✅
