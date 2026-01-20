# Git Manager Implementation Plan

## Executive Summary

Extend CodeHero to support **remote repository management** for user projects (GitHub, GitLab, Bitbucket).

**This is SEPARATE from the internal backup git system.**

---

## Current State

**Already exists in `git_manager.py`:**
- `init_repo()`, `auto_commit()`, `get_commits()`, `get_status()`, `get_diff()`, `rollback_to_commit()`

**Already exists in `app.py`:**
- `/api/project/<id>/git/status`, `/commits`, `/commit/<hash>`, `/diff/<hash>`, `/init`, `/rollback`

**Missing:**
- Remote connections (push/pull/fetch)
- Branch management
- Staging area (stage/unstage files)
- Manual commits
- Credential storage

---

## Implementation Plan

### Phase 1: Database

**New table: `project_git_remotes`**
```sql
CREATE TABLE `project_git_remotes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `project_id` int NOT NULL,
  `repo_id` int DEFAULT NULL,
  `path_type` enum('web', 'app') NOT NULL DEFAULT 'web',
  `name` varchar(50) DEFAULT 'origin',
  `url` varchar(500) NOT NULL,
  `platform` enum('github', 'gitlab', 'bitbucket', 'other') DEFAULT 'other',
  `auth_method` enum('none', 'token', 'ssh') DEFAULT 'none',
  `username` varchar(100) DEFAULT NULL,
  `token_encrypted` varbinary(512) DEFAULT NULL,
  `default_branch` varchar(100) DEFAULT 'main',
  `last_push_at` timestamp NULL DEFAULT NULL,
  `last_pull_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_project_path_remote` (`project_id`, `path_type`, `name`),
  CONSTRAINT `fk_remote_project` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE CASCADE
);
```

---

### Phase 2: Backend - git_manager.py

**New methods:**

```python
# Remote Operations
def add_remote(name, url) -> (bool, str)
def remove_remote(name) -> (bool, str)
def get_remotes() -> List[Dict]
def fetch(remote='origin', branch=None) -> (bool, str)
def pull(remote='origin', branch=None) -> (bool, str)
def push(remote='origin', branch=None, force=False) -> (bool, str)

# Branch Operations
def get_branches(include_remote=True) -> Dict
def create_branch(name, checkout=True) -> (bool, str)
def switch_branch(name) -> (bool, str)
def delete_branch(name, force=False) -> (bool, str)
def merge_branch(branch, no_ff=False) -> (bool, str)

# Staging Operations
def stage_files(files: List[str]) -> (bool, str)
def unstage_files(files: List[str]) -> (bool, str)
def stage_all() -> (bool, str)
def discard_changes(files=None) -> (bool, str)
def get_staged_files() -> List[Dict]

# Manual Commit
def commit(message, author=None) -> (bool, str, commit_hash)
```

---

### Phase 3: Backend - app.py (New Endpoints)

```python
# Path selection (web/app)
@app.route('/api/project/<id>/git/<path_type>/...')

# Remote Management
GET/POST  /api/project/<id>/git/<path_type>/remotes
PUT/DELETE /api/project/<id>/git/<path_type>/remote/<remote_id>

# Remote Operations
POST /api/project/<id>/git/<path_type>/fetch
POST /api/project/<id>/git/<path_type>/pull
POST /api/project/<id>/git/<path_type>/push

# Branch Operations
GET  /api/project/<id>/git/<path_type>/branches
POST /api/project/<id>/git/<path_type>/branch          (create)
DELETE /api/project/<id>/git/<path_type>/branch/<name>
POST /api/project/<id>/git/<path_type>/checkout
POST /api/project/<id>/git/<path_type>/merge

# Staging Operations
POST /api/project/<id>/git/<path_type>/stage
POST /api/project/<id>/git/<path_type>/unstage
POST /api/project/<id>/git/<path_type>/discard

# Manual Commit
POST /api/project/<id>/git/<path_type>/commit
```

---

### Phase 4: Frontend - project_git.html

**UI με tabs per path:**

```
┌─────────────────────────────────────────────────────────────┐
│ Git Manager                                                 │
├─────────────────────────────────────────────────────────────┤
│ [🌐 Web Path] [📱 App Path]              ← Path selector    │
├─────────────────────────────────────────────────────────────┤
│ Branch: [main ▼] | Remote: origin | ↑2 ↓0 | [Pull] [Push]  │
├─────────────────────────────────────────────────────────────┤
│ [Changes] [History] [Branches] [Remotes]  ← Sub-tabs        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Changes Tab:                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Staged (2):                          [Unstage All]  │   │
│  │ ☑ src/App.js                                        │   │
│  │ ☑ src/Cart.js                                       │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ Unstaged (3):                        [Stage All]    │   │
│  │ ☐ src/utils.js                          [Stage]     │   │
│  │ ☐ package.json                          [Stage]     │   │
│  │ ☐ README.md                             [Discard]   │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ Commit Message: [                                 ] │   │
│  │ [Commit]                                            │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### Phase 5: Security

**Credential Encryption:**
```python
# New: /home/claude/codehero/scripts/git_credentials.py
from cryptography.fernet import Fernet

class GitCredentialManager:
    KEY_FILE = '/opt/codehero/config/.git_key'

    def encrypt_token(self, token: str) -> bytes
    def decrypt_token(self, encrypted: bytes) -> str
```

**Security rules:**
- Never log tokens
- Sanitize git error messages
- Rate limit push/pull
- Confirm force push

---

### Phase 6: MCP Tools (Optional)

```python
codehero_git_status   - Get status with branches/remotes
codehero_git_commit   - Manual commit
codehero_git_push     - Push to remote
codehero_git_pull     - Pull from remote
codehero_git_branch   - Branch operations
```

---

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `database/schema.sql` | Modify | Add `project_git_remotes` table |
| `database/migrations/2.80.0_git_remotes.sql` | Create | Migration |
| `scripts/git_manager.py` | Modify | Add remote/branch/staging methods |
| `scripts/git_credentials.py` | Create | Token encryption |
| `web/app.py` | Modify | ~15 new endpoints |
| `web/templates/project_git.html` | Modify | Complete overhaul |
| `scripts/mcp_server.py` | Modify | Add MCP tools (optional) |

---

## Implementation Order

1. Database migration
2. git_credentials.py (encryption)
3. git_manager.py (new methods)
4. app.py (API endpoints)
5. project_git.html (UI)
6. Testing
7. MCP tools (optional)

---

## Estimated Effort

| Phase | Effort |
|-------|--------|
| Database | 15 min |
| git_credentials.py | 30 min |
| git_manager.py | 2 hours |
| app.py endpoints | 1.5 hours |
| project_git.html UI | 2 hours |
| Testing | 1 hour |
| **Total** | **~7 hours** |

---

**Created:** 2026-01-20
