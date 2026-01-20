#!/usr/bin/env python3
"""
CodeHero MCP Server
Provides tools for Claude to manage projects and tickets via the CodeHero API.
"""

import json
import sys
import os
import mysql.connector
from datetime import datetime
from typing import Any, Dict, List, Optional

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'claude_user',
    'password': 'claudepass123',
    'database': 'claude_knowledge'
}

def get_db_connection():
    """Get a database connection."""
    return mysql.connector.connect(**DB_CONFIG)

def serialize_row(row: dict) -> dict:
    """Convert datetime objects to ISO format strings for JSON serialization."""
    from datetime import datetime, date
    if row is None:
        return None
    result = {}
    for key, value in row.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, date):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result

def log_error(msg: str):
    """Log error to stderr."""
    sys.stderr.write(f"[CodeHero MCP] ERROR: {msg}\n")
    sys.stderr.flush()

def log_info(msg: str):
    """Log info to stderr."""
    sys.stderr.write(f"[CodeHero MCP] {msg}\n")
    sys.stderr.flush()

# Tool definitions
TOOLS = [
    {
        "name": "codehero_list_projects",
        "description": "List all projects in CodeHero. Returns project names, IDs, types, and status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter by status (active, completed, all). Default: active",
                    "enum": ["active", "completed", "all"]
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of projects to return. Default: 20"
                }
            },
            "required": []
        }
    },
    {
        "name": "codehero_get_project",
        "description": "Get detailed information about a specific project including its tickets.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "integer",
                    "description": "The project ID"
                },
                "project_name": {
                    "type": "string",
                    "description": "The project name (alternative to ID)"
                }
            },
            "required": []
        }
    },
    {
        "name": "codehero_create_project",
        "description": "Create a new project in CodeHero. Projects organize work and contain tickets.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Project name (required)"
                },
                "description": {
                    "type": "string",
                    "description": "Project description"
                },
                "project_type": {
                    "type": "string",
                    "description": "Type of project: web, app, api, cli, library, other",
                    "enum": ["web", "app", "api", "cli", "library", "other"]
                },
                "tech_stack": {
                    "type": "string",
                    "description": "Technology stack: php, python, node, java, dotnet, other"
                },
                "web_path": {
                    "type": "string",
                    "description": "Path for web files (e.g., /var/www/html/myproject)"
                },
                "app_path": {
                    "type": "string",
                    "description": "Path for app/backend files"
                },
                "ai_model": {
                    "type": "string",
                    "description": "Default AI model for tickets: opus (Master Developer), sonnet (Senior Developer), haiku (Junior Developer). Default: sonnet",
                    "enum": ["opus", "sonnet", "haiku"]
                }
            },
            "required": ["name"]
        }
    },
    {
        "name": "codehero_list_tickets",
        "description": "List tickets for a project. Shows ticket numbers, titles, status, and priority.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "integer",
                    "description": "The project ID (required)"
                },
                "status": {
                    "type": "string",
                    "description": "Filter by status: open, in_progress, awaiting_input, completed, closed, all",
                    "enum": ["open", "in_progress", "awaiting_input", "completed", "closed", "all"]
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of tickets to return. Default: 20"
                }
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "codehero_get_ticket",
        "description": "Get detailed information about a specific ticket including description and conversation history.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "integer",
                    "description": "The ticket ID"
                },
                "ticket_number": {
                    "type": "string",
                    "description": "The ticket number (e.g., 'PROJ-0001')"
                }
            },
            "required": []
        }
    },
    {
        "name": "codehero_create_ticket",
        "description": "Create a new ticket in a project. Tickets represent tasks for Claude to work on.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "integer",
                    "description": "The project ID (required)"
                },
                "title": {
                    "type": "string",
                    "description": "Ticket title (required)"
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of the task"
                },
                "priority": {
                    "type": "string",
                    "description": "Priority: low, medium, high, critical",
                    "enum": ["low", "medium", "high", "critical"]
                },
                "ticket_type": {
                    "type": "string",
                    "description": "Type of ticket: feature, bug, debug, rnd, task, improvement, docs. Default: task",
                    "enum": ["feature", "bug", "debug", "rnd", "task", "improvement", "docs"]
                },
                "sequence_order": {
                    "type": "integer",
                    "description": "Sequence position for ordering (lower = executed first)"
                },
                "depends_on": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of ticket numbers this ticket depends on (e.g., ['PROJ-0001', 'PROJ-0002'])"
                },
                "parent_ticket_id": {
                    "type": "integer",
                    "description": "Parent ticket ID for sub-tickets"
                },
                "auto_start": {
                    "type": "boolean",
                    "description": "Automatically start processing. Default: true"
                },
                "execution_mode": {
                    "type": "string",
                    "description": "Execution mode: autonomous (full access), semi-autonomous (smart sandbox), supervised (asks for permissions), or omit to inherit from project default",
                    "enum": ["autonomous", "semi-autonomous", "supervised"]
                },
                "deps_include_awaiting": {
                    "type": "boolean",
                    "description": "Set to TRUE for 'relaxed' mode (tickets run continuously), FALSE for 'strict' mode (waits between tickets). Default: false (strict)"
                },
                "ai_model": {
                    "type": "string",
                    "description": "AI model for this ticket: opus (Master Developer), sonnet (Senior Developer), haiku (Junior Developer). Default: inherit from project",
                    "enum": ["opus", "sonnet", "haiku"]
                }
            },
            "required": ["project_id", "title"]
        }
    },
    {
        "name": "codehero_update_ticket",
        "description": "Update an existing ticket (status, priority, add reply).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "integer",
                    "description": "The ticket ID (required)"
                },
                "status": {
                    "type": "string",
                    "description": "New status",
                    "enum": ["open", "in_progress", "awaiting_input", "completed", "closed"]
                },
                "priority": {
                    "type": "string",
                    "description": "New priority",
                    "enum": ["low", "medium", "high", "critical"]
                },
                "reply": {
                    "type": "string",
                    "description": "Add a user reply to the ticket conversation"
                },
                "ai_model": {
                    "type": "string",
                    "description": "Change AI model: opus (Master), sonnet (Senior), haiku (Junior)",
                    "enum": ["opus", "sonnet", "haiku"]
                }
            },
            "required": ["ticket_id"]
        }
    },
    {
        "name": "codehero_dashboard_stats",
        "description": "Get dashboard statistics: project counts, ticket counts, recent activity.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "codehero_kill_switch",
        "description": "Kill switch - immediately stop a running ticket. Sends SIGTERM to the Claude process and pauses the ticket for new instructions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "integer",
                    "description": "The ticket ID to stop (required)"
                },
                "ticket_number": {
                    "type": "string",
                    "description": "The ticket number to stop (alternative to ticket_id)"
                }
            },
            "required": []
        }
    },
    {
        "name": "codehero_delete_ticket",
        "description": "Delete a ticket and its conversation history.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "integer",
                    "description": "The ticket ID to delete"
                },
                "ticket_number": {
                    "type": "string",
                    "description": "The ticket number to delete (alternative to ticket_id)"
                }
            },
            "required": []
        }
    },
    {
        "name": "codehero_bulk_create_tickets",
        "description": "Create multiple tickets at once with sequence ordering. Useful for AI project planning.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "integer",
                    "description": "The project ID (required)"
                },
                "tickets": {
                    "type": "array",
                    "description": "Array of ticket objects to create",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "ticket_type": {"type": "string", "enum": ["feature", "bug", "debug", "rnd", "task", "improvement", "docs"]},
                            "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                            "sequence_order": {"type": "integer"},
                            "depends_on": {"type": "array", "items": {"type": "integer"}},
                            "parent_sequence": {"type": "integer", "description": "Sequence order of parent ticket (for sub-tickets)"},
                            "ai_model": {"type": "string", "enum": ["opus", "sonnet", "haiku"], "description": "AI model for this ticket"}
                        },
                        "required": ["title"]
                    }
                },
                "execution_mode": {
                    "type": "string",
                    "description": "Execution mode for ALL tickets: autonomous (full access), semi-autonomous (smart sandbox), supervised (asks for permissions). Default: inherit from project",
                    "enum": ["autonomous", "semi-autonomous", "supervised"]
                },
                "deps_include_awaiting": {
                    "type": "boolean",
                    "description": "Set to TRUE for 'relaxed' mode (tickets run continuously), FALSE for 'strict' mode (waits between tickets). Default: false"
                }
            },
            "required": ["project_id", "tickets"]
        }
    },
    {
        "name": "codehero_get_project_progress",
        "description": "Get detailed project progress statistics including tickets by status, type, and completion percentage.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "integer",
                    "description": "The project ID (required)"
                }
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "codehero_retry_ticket",
        "description": "Retry a failed or timed-out ticket by resetting it to open status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "integer",
                    "description": "The ticket ID to retry"
                },
                "ticket_number": {
                    "type": "string",
                    "description": "The ticket number to retry (alternative to ticket_id)"
                }
            },
            "required": []
        }
    },
    {
        "name": "codehero_set_ticket_sequence",
        "description": "Set the sequence order for a single ticket.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "integer",
                    "description": "The ticket ID (required)"
                },
                "sequence_order": {
                    "type": "integer",
                    "description": "New sequence position (lower = executed first)"
                },
                "is_forced": {
                    "type": "boolean",
                    "description": "Set to true to force this ticket to the front of the queue"
                }
            },
            "required": ["ticket_id"]
        }
    },
    {
        "name": "codehero_start_ticket",
        "description": "Start a ticket immediately by setting it to open and forcing it to the front of the queue.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "integer",
                    "description": "The ticket ID to start"
                },
                "ticket_number": {
                    "type": "string",
                    "description": "The ticket number to start (alternative to ticket_id)"
                }
            },
            "required": []
        }
    },
    {
        "name": "codehero_reload",
        "description": "Reload the MCP server to apply code changes. Use this after updating mcp_server.py.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "codehero_import_project",
        "description": "Import an existing project into CodeHero. Supports ZIP files, git repos, or local paths. Two modes: 'extend' (add to existing project) or 'reference' (use as template for new project).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "integer",
                    "description": "The project ID to import into (required)"
                },
                "source_type": {
                    "type": "string",
                    "description": "Type of source: zip (URL or path to ZIP), git (git clone URL), path (local folder path)",
                    "enum": ["zip", "git", "path"]
                },
                "source": {
                    "type": "string",
                    "description": "The source location: URL for zip/git, or path for local folder"
                },
                "mode": {
                    "type": "string",
                    "description": "Import mode: extend (copy to project path, modify existing), reference (store separately as template)",
                    "enum": ["extend", "reference"],
                    "default": "extend"
                },
                "git_username": {
                    "type": "string",
                    "description": "Git username (for private repos)"
                },
                "git_token": {
                    "type": "string",
                    "description": "Git personal access token or app password (for private repos). GitHub/GitLab: use PAT. Bitbucket: use app password."
                }
            },
            "required": ["project_id", "source_type", "source"]
        }
    },
    {
        "name": "codehero_analyze_project",
        "description": "Analyze/re-analyze a project to build its map (structure, tech stack, entry points). The map is used to provide context to AI when working on tickets.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "integer",
                    "description": "The project ID to analyze (required)"
                },
                "force": {
                    "type": "boolean",
                    "description": "Force re-analysis even if a recent map exists. Default: false",
                    "default": False
                }
            },
            "required": ["project_id"]
        }
    }
]

def handle_reload(args: Dict[str, Any]) -> Dict[str, Any]:
    """Reload the MCP server by restarting the process."""
    import os
    import signal

    # Send response first, then exit
    # Claude Code will restart the MCP server automatically
    def delayed_exit():
        os._exit(0)

    import threading
    threading.Timer(0.1, delayed_exit).start()

    return {"content": [{"type": "text", "text": "MCP server reloading... Next call will use updated code."}]}

def handle_list_projects(args: Dict[str, Any]) -> Dict[str, Any]:
    """List all projects."""
    status = args.get('status', 'active')
    limit = args.get('limit', 20)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        if status == 'all':
            query = """
                SELECT id, name, description, project_type, tech_stack, status,
                       created_at, code,
                       (SELECT COUNT(*) FROM tickets WHERE project_id = projects.id) as ticket_count,
                       (SELECT COUNT(*) FROM tickets WHERE project_id = projects.id AND status IN ('open', 'in_progress')) as open_tickets
                FROM projects
                ORDER BY created_at DESC
                LIMIT %s
            """
            cursor.execute(query, (limit,))
        else:
            query = """
                SELECT id, name, description, project_type, tech_stack, status,
                       created_at, code,
                       (SELECT COUNT(*) FROM tickets WHERE project_id = projects.id) as ticket_count,
                       (SELECT COUNT(*) FROM tickets WHERE project_id = projects.id AND status IN ('open', 'in_progress')) as open_tickets
                FROM projects
                WHERE status = %s
                ORDER BY created_at DESC
                LIMIT %s
            """
            cursor.execute(query, (status, limit))

        projects = cursor.fetchall()

        # Convert datetime to string
        for p in projects:
            if p.get('created_at'):
                p['created_at'] = p['created_at'].isoformat()

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"projects": projects, "count": len(projects)}, indent=2)
                }
            ]
        }
    finally:
        cursor.close()
        conn.close()

def handle_get_project(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get project details."""
    project_id = args.get('project_id')
    project_name = args.get('project_name')

    if not project_id and not project_name:
        return {"content": [{"type": "text", "text": "Error: Either project_id or project_name is required"}]}

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        if project_id:
            cursor.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
        else:
            cursor.execute("SELECT * FROM projects WHERE name = %s", (project_name,))

        project = cursor.fetchone()

        if not project:
            return {"content": [{"type": "text", "text": f"Error: Project not found"}]}

        # Get recent tickets
        cursor.execute("""
            SELECT id, ticket_number, title, status, priority, created_at
            FROM tickets
            WHERE project_id = %s
            ORDER BY created_at DESC
            LIMIT 10
        """, (project['id'],))
        tickets = cursor.fetchall()

        # Serialize all rows (converts datetime to ISO format)
        project = serialize_row(project)
        tickets = [serialize_row(t) for t in tickets]

        result = {
            "project": project,
            "recent_tickets": tickets
        }

        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
    finally:
        cursor.close()
        conn.close()

def handle_create_project(args: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new project with directories and database."""
    import subprocess
    import secrets
    import string

    name = args.get('name')
    if not name:
        return {"content": [{"type": "text", "text": "Error: name is required"}]}

    description = args.get('description', '')
    project_type = args.get('project_type', 'web')
    tech_stack = args.get('tech_stack', 'php')
    web_path = args.get('web_path', '')
    app_path = args.get('app_path', '')
    ai_model = args.get('ai_model', 'sonnet')

    # Validate ai_model
    if ai_model not in ('opus', 'sonnet', 'haiku'):
        ai_model = 'sonnet'

    # Generate code from name (up to 8 characters)
    original_code = ''.join(c.upper() for c in name if c.isalnum())[:8]
    if not original_code:
        original_code = 'PROJ'
    code = original_code
    code_was_changed = False

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Check if project name exists
        cursor.execute("SELECT id FROM projects WHERE name = %s", (name,))
        if cursor.fetchone():
            return {"content": [{"type": "text", "text": f"Error: Project '{name}' already exists"}]}

        # Check code uniqueness and modify if needed
        cursor.execute("SELECT id, name FROM projects WHERE code = %s", (code,))
        existing = cursor.fetchone()
        if existing:
            # Add number to make unique
            for i in range(1, 100):
                new_code = f"{original_code[:5]}{i}"
                cursor.execute("SELECT code FROM projects WHERE code = %s", (new_code,))
                if not cursor.fetchone():
                    code = new_code
                    code_was_changed = True
                    break

        # Generate paths based on project type
        project_slug = code.lower()
        if not web_path and project_type in ('web', 'api'):
            web_path = f"/var/www/projects/{project_slug}"
        if not app_path and project_type in ('app', 'cli', 'library'):
            app_path = f"/opt/apps/{project_slug}"

        # Create directories
        created_dirs = []
        for path in [web_path, app_path]:
            if path:
                try:
                    subprocess.run(['sudo', 'mkdir', '-p', path], check=True, capture_output=True)
                    subprocess.run(['sudo', 'chown', '-R', 'claude:claude', path], check=True, capture_output=True)
                    created_dirs.append(path)
                except Exception as e:
                    pass  # Directory creation failed, continue anyway

        # Initialize Git repository
        git_initialized = False
        git_path = web_path or app_path
        if git_path and os.path.exists(git_path):
            try:
                from git_manager import GitManager
                gm = GitManager(git_path, project_type, tech_stack)
                success, msg = gm.init_repo()
                git_initialized = success
            except Exception as e:
                pass  # Git init failed, continue anyway

        # Generate database credentials
        db_name = f"proj_{project_slug}"
        db_user = f"proj_{project_slug}"
        db_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
        db_host = 'localhost'

        # Create database and user using claude_user (has CREATE USER privilege)
        db_created = False
        try:
            admin_conn = mysql.connector.connect(
                host='localhost',
                user='claude_user',
                password='claudepass123'
            )
            admin_cursor = admin_conn.cursor()

            # Create database
            admin_cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")

            # Drop user if exists, then create fresh
            try:
                admin_cursor.execute(f"DROP USER IF EXISTS '{db_user}'@'localhost'")
            except:
                pass
            admin_cursor.execute(f"CREATE USER '{db_user}'@'localhost' IDENTIFIED BY '{db_password}'")
            admin_cursor.execute(f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{db_user}'@'localhost'")
            admin_cursor.execute("FLUSH PRIVILEGES")
            admin_conn.commit()
            admin_cursor.close()
            admin_conn.close()
            db_created = True
        except Exception as e:
            # Database creation failed, set to None
            db_name = None
            db_user = None
            db_password = None

        # Insert project
        cursor.execute("""
            INSERT INTO projects (name, description, project_type, tech_stack, web_path, app_path, code, status,
                                  db_name, db_user, db_password, db_host, ai_model)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'active', %s, %s, %s, %s, %s)
        """, (name, description, project_type, tech_stack, web_path, app_path, code,
              db_name, db_user, db_password, db_host, ai_model))

        conn.commit()
        project_id = cursor.lastrowid

        # Build message
        msg = f"Project '{name}' created successfully with code '{code}'"
        if code_was_changed:
            msg += f" (NOTE: Code was changed from '{original_code}' because it was already in use)"

        result = {
            "success": True,
            "project_id": project_id,
            "name": name,
            "code": code,
            "original_code": original_code if code_was_changed else None,
            "code_was_changed": code_was_changed,
            "web_path": web_path,
            "app_path": app_path,
            "db_name": db_name,
            "db_user": db_user,
            "db_created": db_created,
            "git_initialized": git_initialized,
            "ai_model": ai_model,
            "message": msg
        }

        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error creating project: {str(e)}"}]}
    finally:
        cursor.close()
        conn.close()

def handle_list_tickets(args: Dict[str, Any]) -> Dict[str, Any]:
    """List tickets for a project."""
    project_id = args.get('project_id')
    if not project_id:
        return {"content": [{"type": "text", "text": "Error: project_id is required"}]}

    status = args.get('status', 'all')
    limit = args.get('limit', 20)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        if status == 'all':
            cursor.execute("""
                SELECT id, ticket_number, title, status, priority, created_at, updated_at
                FROM tickets
                WHERE project_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (project_id, limit))
        else:
            cursor.execute("""
                SELECT id, ticket_number, title, status, priority, created_at, updated_at
                FROM tickets
                WHERE project_id = %s AND status = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (project_id, status, limit))

        tickets = cursor.fetchall()

        for t in tickets:
            if t.get('created_at'):
                t['created_at'] = t['created_at'].isoformat()
            if t.get('updated_at'):
                t['updated_at'] = t['updated_at'].isoformat()

        return {"content": [{"type": "text", "text": json.dumps({"tickets": tickets, "count": len(tickets)}, indent=2)}]}
    finally:
        cursor.close()
        conn.close()

def handle_get_ticket(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get ticket details."""
    ticket_id = args.get('ticket_id')
    ticket_number = args.get('ticket_number')

    if not ticket_id and not ticket_number:
        return {"content": [{"type": "text", "text": "Error: Either ticket_id or ticket_number is required"}]}

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        if ticket_id:
            cursor.execute("""
                SELECT t.*, p.name as project_name, p.code
                FROM tickets t
                JOIN projects p ON t.project_id = p.id
                WHERE t.id = %s
            """, (ticket_id,))
        else:
            cursor.execute("""
                SELECT t.*, p.name as project_name, p.code
                FROM tickets t
                JOIN projects p ON t.project_id = p.id
                WHERE t.ticket_number = %s
            """, (ticket_number,))

        ticket = cursor.fetchone()

        if not ticket:
            return {"content": [{"type": "text", "text": "Error: Ticket not found"}]}

        # Get conversation
        cursor.execute("""
            SELECT role, content, created_at
            FROM conversation_messages
            WHERE ticket_id = %s
            ORDER BY created_at ASC
        """, (ticket['id'],))
        messages = cursor.fetchall()

        # Convert all datetime fields
        ticket = serialize_row(ticket)
        messages = [serialize_row(m) for m in messages]

        result = {
            "ticket": ticket,
            "conversation": messages
        }

        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
    finally:
        cursor.close()
        conn.close()

def handle_create_ticket(args: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new ticket with optional type, sequence, and dependencies."""
    project_id = args.get('project_id')
    title = args.get('title')

    if not project_id:
        return {"content": [{"type": "text", "text": "Error: project_id is required"}]}
    if not title:
        return {"content": [{"type": "text", "text": "Error: title is required"}]}

    description = args.get('description', '')
    priority = args.get('priority', 'medium')
    auto_start = args.get('auto_start', True)
    ticket_type = args.get('ticket_type', 'task')
    sequence_order = args.get('sequence_order')
    depends_on = args.get('depends_on', [])
    parent_ticket_id = args.get('parent_ticket_id')
    execution_mode = args.get('execution_mode')  # None = inherit from project
    deps_include_awaiting = args.get('deps_include_awaiting', False)  # Relaxed mode for deps
    ai_model = args.get('ai_model')  # None = inherit from project

    # Validate execution_mode (None = inherit from project)
    if execution_mode and execution_mode not in ('autonomous', 'semi-autonomous', 'supervised'):
        execution_mode = None

    # Validate ai_model (None = inherit from project)
    if ai_model and ai_model not in ('opus', 'sonnet', 'haiku'):
        ai_model = None

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get project code and next ticket number
        cursor.execute("SELECT id, code FROM projects WHERE id = %s", (project_id,))
        project = cursor.fetchone()

        if not project:
            return {"content": [{"type": "text", "text": f"Error: Project ID {project_id} not found"}]}

        code = project['code']

        # Get next ticket number
        cursor.execute("""
            SELECT ticket_number FROM tickets
            WHERE project_id = %s
            ORDER BY id DESC LIMIT 1
        """, (project_id,))
        last_ticket = cursor.fetchone()

        if last_ticket:
            # Extract number from ticket_number like "PROJ-0001"
            try:
                last_num = int(last_ticket['ticket_number'].split('-')[1])
                next_num = last_num + 1
            except:
                next_num = 1
        else:
            next_num = 1

        ticket_number = f"{code}-{next_num:04d}"
        status = 'open' if auto_start else 'open'

        cursor.execute("""
            INSERT INTO tickets (project_id, ticket_number, title, description, status, priority,
                                 ticket_type, sequence_order, parent_ticket_id, execution_mode, deps_include_awaiting, ai_model)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (project_id, ticket_number, title, description, status, priority,
              ticket_type, sequence_order, parent_ticket_id, execution_mode, deps_include_awaiting, ai_model))

        conn.commit()
        ticket_id = cursor.lastrowid

        # Handle dependencies
        if depends_on:
            for dep in depends_on:
                # dep is a ticket_number string
                cursor.execute("SELECT id FROM tickets WHERE ticket_number = %s", (dep,))
                dep_ticket = cursor.fetchone()
                if dep_ticket:
                    cursor.execute("""
                        INSERT IGNORE INTO ticket_dependencies (ticket_id, depends_on_ticket_id)
                        VALUES (%s, %s)
                    """, (ticket_id, dep_ticket['id']))
            conn.commit()

        # Add initial message if description provided
        if description:
            cursor.execute("""
                INSERT INTO conversation_messages (ticket_id, role, content)
                VALUES (%s, 'user', %s)
            """, (ticket_id, description))
            conn.commit()

        result = {
            "success": True,
            "ticket_id": ticket_id,
            "ticket_number": ticket_number,
            "title": title,
            "ticket_type": ticket_type,
            "sequence_order": sequence_order,
            "status": status,
            "ai_model": ai_model or "inherit",
            "message": f"Ticket {ticket_number} created successfully"
        }

        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error creating ticket: {str(e)}"}]}
    finally:
        cursor.close()
        conn.close()

def handle_update_ticket(args: Dict[str, Any]) -> Dict[str, Any]:
    """Update a ticket."""
    ticket_id = args.get('ticket_id')
    if not ticket_id:
        return {"content": [{"type": "text", "text": "Error: ticket_id is required"}]}

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Check ticket exists
        cursor.execute("SELECT id, ticket_number FROM tickets WHERE id = %s", (ticket_id,))
        ticket = cursor.fetchone()

        if not ticket:
            return {"content": [{"type": "text", "text": f"Error: Ticket ID {ticket_id} not found"}]}

        updates = []
        params = []

        if 'status' in args:
            updates.append("status = %s")
            params.append(args['status'])

        if 'priority' in args:
            updates.append("priority = %s")
            params.append(args['priority'])

        if 'ai_model' in args:
            ai_model = args['ai_model']
            if ai_model in ('opus', 'sonnet', 'haiku'):
                updates.append("ai_model = %s")
                params.append(ai_model)

        if updates:
            updates.append("updated_at = NOW()")
            params.append(ticket_id)
            cursor.execute(f"UPDATE tickets SET {', '.join(updates)} WHERE id = %s", params)

        # Add reply if provided
        if 'reply' in args and args['reply']:
            cursor.execute("""
                INSERT INTO conversation_messages (ticket_id, role, content)
                VALUES (%s, 'user', %s)
            """, (ticket_id, args['reply']))
            # Set ticket to open so daemon picks it up
            cursor.execute("UPDATE tickets SET status = 'open', updated_at = NOW() WHERE id = %s", (ticket_id,))

        conn.commit()

        result = {
            "success": True,
            "ticket_id": ticket_id,
            "ticket_number": ticket['ticket_number'],
            "message": f"Ticket {ticket['ticket_number']} updated successfully"
        }

        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error updating ticket: {str(e)}"}]}
    finally:
        cursor.close()
        conn.close()

def handle_kill_switch(args: Dict[str, Any]) -> Dict[str, Any]:
    """Kill switch - immediately stop a running ticket."""
    import signal

    ticket_id = args.get('ticket_id')
    ticket_number = args.get('ticket_number')

    if not ticket_id and not ticket_number:
        return {"content": [{"type": "text", "text": "Error: Either ticket_id or ticket_number is required"}]}

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get ticket
        if ticket_id:
            cursor.execute("SELECT id, ticket_number, status FROM tickets WHERE id = %s", (ticket_id,))
        else:
            cursor.execute("SELECT id, ticket_number, status FROM tickets WHERE ticket_number = %s", (ticket_number,))

        ticket = cursor.fetchone()

        if not ticket:
            return {"content": [{"type": "text", "text": "Error: Ticket not found"}]}

        if ticket['status'] != 'in_progress':
            return {"content": [{"type": "text", "text": f"Error: Ticket {ticket['ticket_number']} is not in progress (status: {ticket['status']})"}]}

        ticket_id = ticket['id']

        # Update ticket status FIRST (so daemon doesn't mark as failed)
        # Set awaiting_reason='stopped' to prevent auto-review from closing it
        # Clear review_scheduled_at to cancel any pending auto-review
        cursor.execute("""
            UPDATE tickets SET
                status = 'awaiting_input',
                awaiting_reason = 'stopped',
                review_scheduled_at = NULL,
                updated_at = NOW()
            WHERE id = %s
        """, (ticket_id,))
        conn.commit()

        # Try to kill the Claude process
        killed = False
        pid_file = f"/var/run/codehero/claude_{ticket_id}.pid"
        try:
            if os.path.exists(pid_file):
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())
                os.kill(pid, signal.SIGTERM)
                killed = True
        except (ProcessLookupError, ValueError, PermissionError, FileNotFoundError):
            pass

        # Save system message
        system_msg = '⏹️ Kill switch activated (via AI Assistant) - Process stopped' if killed else '⏹️ Kill switch activated (via AI Assistant) - Waiting for process to stop'
        cursor.execute("""
            INSERT INTO conversation_messages (ticket_id, role, content, created_at)
            VALUES (%s, 'system', %s, NOW())
        """, (ticket_id, system_msg))

        # Add log entry
        cursor.execute("""
            INSERT INTO daemon_logs (ticket_id, log_type, message, created_at)
            VALUES (%s, 'warning', %s, NOW())
        """, (ticket_id, f"⏹️ Kill switch activated via MCP - Ticket {ticket['ticket_number']} paused"))

        conn.commit()

        result = {
            "success": True,
            "ticket_id": ticket_id,
            "ticket_number": ticket['ticket_number'],
            "killed": killed,
            "message": f"Kill switch activated for {ticket['ticket_number']}. Process {'stopped' if killed else 'stopping'}."
        }

        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}
    finally:
        cursor.close()
        conn.close()

def handle_dashboard_stats(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get dashboard statistics."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Project counts
        cursor.execute("SELECT COUNT(*) as total FROM projects")
        total_projects = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as active FROM projects WHERE status = 'active'")
        active_projects = cursor.fetchone()['active']

        # Ticket counts
        cursor.execute("SELECT COUNT(*) as total FROM tickets")
        total_tickets = cursor.fetchone()['total']

        cursor.execute("SELECT status, COUNT(*) as count FROM tickets GROUP BY status")
        ticket_stats = {row['status']: row['count'] for row in cursor.fetchall()}

        # Recent activity
        cursor.execute("""
            SELECT t.ticket_number, t.title, t.status, t.updated_at, p.name as project_name
            FROM tickets t
            JOIN projects p ON t.project_id = p.id
            ORDER BY t.updated_at DESC
            LIMIT 5
        """)
        recent = cursor.fetchall()

        for r in recent:
            if r.get('updated_at'):
                r['updated_at'] = r['updated_at'].isoformat()

        result = {
            "projects": {
                "total": total_projects,
                "active": active_projects
            },
            "tickets": {
                "total": total_tickets,
                "by_status": ticket_stats
            },
            "recent_activity": recent
        }

        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
    finally:
        cursor.close()
        conn.close()


def handle_delete_ticket(args: Dict[str, Any]) -> Dict[str, Any]:
    """Delete a ticket and its history."""
    ticket_id = args.get('ticket_id')
    ticket_number = args.get('ticket_number')

    if not ticket_id and not ticket_number:
        return {"content": [{"type": "text", "text": "Error: Either ticket_id or ticket_number is required"}]}

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get ticket
        if ticket_id:
            cursor.execute("SELECT id, ticket_number, title FROM tickets WHERE id = %s", (ticket_id,))
        else:
            cursor.execute("SELECT id, ticket_number, title FROM tickets WHERE ticket_number = %s", (ticket_number,))

        ticket = cursor.fetchone()
        if not ticket:
            return {"content": [{"type": "text", "text": "Error: Ticket not found"}]}

        ticket_id = ticket['id']
        ticket_number = ticket['ticket_number']

        # Delete ticket (cascade will handle messages, etc.)
        cursor.execute("DELETE FROM tickets WHERE id = %s", (ticket_id,))
        conn.commit()

        result = {
            "success": True,
            "ticket_number": ticket_number,
            "message": f"Ticket {ticket_number} deleted successfully"
        }
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}
    finally:
        cursor.close()
        conn.close()


def handle_bulk_create_tickets(args: Dict[str, Any]) -> Dict[str, Any]:
    """Create multiple tickets at once with sequence ordering."""
    project_id = args.get('project_id')
    tickets_data = args.get('tickets', [])
    execution_mode = args.get('execution_mode')  # None = inherit from project
    deps_include_awaiting = args.get('deps_include_awaiting', False)  # Relaxed mode

    # Validate execution_mode
    if execution_mode and execution_mode not in ('autonomous', 'semi-autonomous', 'supervised'):
        execution_mode = None

    if not project_id:
        return {"content": [{"type": "text", "text": "Error: project_id is required"}]}
    if not tickets_data:
        return {"content": [{"type": "text", "text": "Error: tickets array is required"}]}

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get project code
        cursor.execute("SELECT id, code FROM projects WHERE id = %s", (project_id,))
        project = cursor.fetchone()
        if not project:
            return {"content": [{"type": "text", "text": f"Error: Project ID {project_id} not found"}]}

        code = project['code']

        # Get current max ticket number
        cursor.execute("""
            SELECT ticket_number FROM tickets
            WHERE project_id = %s
            ORDER BY id DESC LIMIT 1
        """, (project_id,))
        last_ticket = cursor.fetchone()

        if last_ticket:
            try:
                next_num = int(last_ticket['ticket_number'].split('-')[1]) + 1
            except:
                next_num = 1
        else:
            next_num = 1

        created_tickets = []
        ticket_id_map = {}  # Map sequence position to ticket_id for dependencies

        for i, ticket_data in enumerate(tickets_data):
            title = ticket_data.get('title', '').strip()
            if not title:
                continue

            description = ticket_data.get('description', '')
            priority = ticket_data.get('priority', 'medium')
            ticket_type = ticket_data.get('ticket_type', 'task')
            sequence_order = ticket_data.get('sequence_order', i + 1)
            ticket_ai_model = ticket_data.get('ai_model')  # Per-ticket model

            # Validate ai_model
            if ticket_ai_model and ticket_ai_model not in ('opus', 'sonnet', 'haiku'):
                ticket_ai_model = None

            ticket_number = f"{code}-{next_num:04d}"
            next_num += 1

            cursor.execute("""
                INSERT INTO tickets (project_id, ticket_number, title, description, status, priority,
                                     ticket_type, sequence_order, execution_mode, deps_include_awaiting, ai_model)
                VALUES (%s, %s, %s, %s, 'open', %s, %s, %s, %s, %s, %s)
            """, (project_id, ticket_number, title, description, priority, ticket_type, sequence_order,
                  execution_mode, deps_include_awaiting, ticket_ai_model))

            ticket_id = cursor.lastrowid
            ticket_id_map[sequence_order] = ticket_id

            created_tickets.append({
                "ticket_id": ticket_id,
                "ticket_number": ticket_number,
                "title": title,
                "sequence_order": sequence_order,
                "ai_model": ticket_ai_model or "inherit"
            })

            # Add initial message if description
            if description:
                cursor.execute("""
                    INSERT INTO conversation_messages (ticket_id, role, content)
                    VALUES (%s, 'user', %s)
                """, (ticket_id, description))

        # Handle dependencies and parent tickets (second pass)
        for i, ticket_data in enumerate(tickets_data):
            if i >= len(created_tickets):
                continue
            ticket_id = created_tickets[i]['ticket_id']

            # Handle dependencies
            depends_on = ticket_data.get('depends_on', [])
            if depends_on:
                for dep_seq in depends_on:
                    # dep_seq is a sequence order number
                    if dep_seq in ticket_id_map:
                        cursor.execute("""
                            INSERT IGNORE INTO ticket_dependencies (ticket_id, depends_on_ticket_id)
                            VALUES (%s, %s)
                        """, (ticket_id, ticket_id_map[dep_seq]))

            # Handle parent ticket
            parent_sequence = ticket_data.get('parent_sequence')
            if parent_sequence and parent_sequence in ticket_id_map:
                parent_id = ticket_id_map[parent_sequence]
                cursor.execute("""
                    UPDATE tickets SET parent_ticket_id = %s WHERE id = %s
                """, (parent_id, ticket_id))

        conn.commit()

        result = {
            "success": True,
            "created_count": len(created_tickets),
            "tickets": created_tickets,
            "execution_mode": execution_mode or "project_default",
            "deps_include_awaiting": deps_include_awaiting,
            "message": f"Created {len(created_tickets)} tickets successfully (mode: {execution_mode or 'project_default'}, relaxed: {deps_include_awaiting})"
        }
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}
    finally:
        cursor.close()
        conn.close()


def handle_get_project_progress(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get detailed project progress statistics."""
    project_id = args.get('project_id')
    if not project_id:
        return {"content": [{"type": "text", "text": "Error: project_id is required"}]}

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get project info
        cursor.execute("SELECT id, name, code FROM projects WHERE id = %s", (project_id,))
        project = cursor.fetchone()
        if not project:
            return {"content": [{"type": "text", "text": f"Error: Project {project_id} not found"}]}

        # Ticket counts by status
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM tickets
            WHERE project_id = %s AND parent_ticket_id IS NULL
            GROUP BY status
        """, (project_id,))
        status_counts = {row['status']: row['count'] for row in cursor.fetchall()}

        # Ticket counts by type
        cursor.execute("""
            SELECT ticket_type, COUNT(*) as total,
                   SUM(CASE WHEN status IN ('done', 'skipped') THEN 1 ELSE 0 END) as completed
            FROM tickets
            WHERE project_id = %s AND parent_ticket_id IS NULL
            GROUP BY ticket_type
        """, (project_id,))
        by_type = {row['ticket_type']: {'total': row['total'], 'completed': int(row['completed'])}
                   for row in cursor.fetchall()}

        # Totals
        total_tickets = sum(status_counts.values())
        completed = status_counts.get('done', 0) + status_counts.get('skipped', 0)
        failed = status_counts.get('failed', 0)
        timeout_count = status_counts.get('timeout', 0)
        in_progress = status_counts.get('in_progress', 0)
        pending = (status_counts.get('open', 0) + status_counts.get('new', 0) +
                   status_counts.get('pending', 0))
        awaiting = status_counts.get('awaiting_input', 0)

        progress_percent = round((completed * 100.0) / total_tickets, 1) if total_tickets > 0 else 0

        # Current ticket
        cursor.execute("""
            SELECT ticket_number FROM tickets
            WHERE project_id = %s AND status = 'in_progress'
            LIMIT 1
        """, (project_id,))
        current = cursor.fetchone()
        current_ticket = current['ticket_number'] if current else None

        # Failed tickets
        cursor.execute("""
            SELECT ticket_number FROM tickets
            WHERE project_id = %s AND status IN ('failed', 'timeout')
        """, (project_id,))
        failed_tickets = [row['ticket_number'] for row in cursor.fetchall()]

        # Blocked tickets
        cursor.execute("""
            SELECT t.ticket_number
            FROM tickets t
            JOIN ticket_dependencies td ON td.ticket_id = t.id
            JOIN tickets dt ON dt.id = td.depends_on_ticket_id
            WHERE t.project_id = %s
              AND t.status NOT IN ('done', 'skipped', 'failed')
              AND dt.status NOT IN ('done', 'skipped')
            GROUP BY t.id, t.ticket_number
        """, (project_id,))
        blocked_tickets = [row['ticket_number'] for row in cursor.fetchall()]

        # Model distribution
        cursor.execute("""
            SELECT COALESCE(ai_model, 'inherit') as model, COUNT(*) as count
            FROM tickets
            WHERE project_id = %s AND parent_ticket_id IS NULL
            GROUP BY COALESCE(ai_model, 'inherit')
        """, (project_id,))
        model_distribution = {row['model']: row['count'] for row in cursor.fetchall()}

        # All tickets with details (for management)
        cursor.execute("""
            SELECT id, ticket_number, title, status, priority,
                   COALESCE(ai_model, 'inherit') as ai_model, sequence_order
            FROM tickets
            WHERE project_id = %s AND parent_ticket_id IS NULL
            ORDER BY sequence_order, id
        """, (project_id,))
        tickets_list = []
        for row in cursor.fetchall():
            tickets_list.append({
                "id": row['id'],
                "ticket_number": row['ticket_number'],
                "title": row['title'],
                "status": row['status'],
                "priority": row['priority'],
                "ai_model": row['ai_model'],
                "sequence_order": row['sequence_order']
            })

        result = {
            "project_id": project_id,
            "project_name": project['name'],
            "project_code": project['code'],
            "total_tickets": total_tickets,
            "completed": completed,
            "failed": failed,
            "timeout": timeout_count,
            "in_progress": in_progress,
            "pending": pending,
            "awaiting_input": awaiting,
            "progress_percent": progress_percent,
            "by_type": by_type,
            "current_ticket": current_ticket,
            "failed_tickets": failed_tickets,
            "blocked_tickets": blocked_tickets,
            "model_distribution": model_distribution,
            "tickets": tickets_list
        }

        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}
    finally:
        cursor.close()
        conn.close()


def handle_retry_ticket(args: Dict[str, Any]) -> Dict[str, Any]:
    """Retry a failed/timeout ticket."""
    ticket_id = args.get('ticket_id')
    ticket_number = args.get('ticket_number')

    if not ticket_id and not ticket_number:
        return {"content": [{"type": "text", "text": "Error: Either ticket_id or ticket_number is required"}]}

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        if ticket_id:
            cursor.execute("SELECT id, ticket_number, status FROM tickets WHERE id = %s", (ticket_id,))
        else:
            cursor.execute("SELECT id, ticket_number, status FROM tickets WHERE ticket_number = %s", (ticket_number,))

        ticket = cursor.fetchone()
        if not ticket:
            return {"content": [{"type": "text", "text": "Error: Ticket not found"}]}

        if ticket['status'] not in ('failed', 'timeout', 'stuck'):
            return {"content": [{"type": "text", "text": f"Error: Ticket {ticket['ticket_number']} is not in failed/timeout/stuck state (status: {ticket['status']})"}]}

        cursor.execute("""
            UPDATE tickets SET status = 'open', retry_count = 0, updated_at = NOW()
            WHERE id = %s
        """, (ticket['id'],))
        conn.commit()

        result = {
            "success": True,
            "ticket_number": ticket['ticket_number'],
            "message": f"Ticket {ticket['ticket_number']} reset for retry"
        }
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}
    finally:
        cursor.close()
        conn.close()


def handle_set_ticket_sequence(args: Dict[str, Any]) -> Dict[str, Any]:
    """Set sequence order or force flag for a ticket."""
    ticket_id = args.get('ticket_id')
    if not ticket_id:
        return {"content": [{"type": "text", "text": "Error: ticket_id is required"}]}

    sequence_order = args.get('sequence_order')
    is_forced = args.get('is_forced')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT id, ticket_number FROM tickets WHERE id = %s", (ticket_id,))
        ticket = cursor.fetchone()
        if not ticket:
            return {"content": [{"type": "text", "text": f"Error: Ticket {ticket_id} not found"}]}

        updates = []
        params = []

        if sequence_order is not None:
            updates.append("sequence_order = %s")
            params.append(sequence_order)

        if is_forced is not None:
            updates.append("is_forced = %s")
            params.append(is_forced)

        if not updates:
            return {"content": [{"type": "text", "text": "Error: No updates provided"}]}

        updates.append("updated_at = NOW()")
        params.append(ticket_id)

        cursor.execute(f"UPDATE tickets SET {', '.join(updates)} WHERE id = %s", params)
        conn.commit()

        result = {
            "success": True,
            "ticket_number": ticket['ticket_number'],
            "sequence_order": sequence_order,
            "is_forced": is_forced,
            "message": f"Ticket {ticket['ticket_number']} updated"
        }
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}
    finally:
        cursor.close()
        conn.close()


def handle_start_ticket(args: Dict[str, Any]) -> Dict[str, Any]:
    """Start a ticket immediately by setting it to open and forcing it to the front."""
    ticket_id = args.get('ticket_id')
    ticket_number = args.get('ticket_number')

    if not ticket_id and not ticket_number:
        return {"content": [{"type": "text", "text": "Error: Either ticket_id or ticket_number is required"}]}

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get ticket
        if ticket_id:
            cursor.execute("""
                SELECT t.id, t.status, t.ticket_number, t.parent_ticket_id,
                       p.ticket_number as parent_ticket_number, p.status as parent_status
                FROM tickets t
                LEFT JOIN tickets p ON t.parent_ticket_id = p.id
                WHERE t.id = %s
            """, (ticket_id,))
        else:
            cursor.execute("""
                SELECT t.id, t.status, t.ticket_number, t.parent_ticket_id,
                       p.ticket_number as parent_ticket_number, p.status as parent_status
                FROM tickets t
                LEFT JOIN tickets p ON t.parent_ticket_id = p.id
                WHERE t.ticket_number = %s
            """, (ticket_number,))

        ticket = cursor.fetchone()
        if not ticket:
            return {"content": [{"type": "text", "text": "Error: Ticket not found"}]}

        # If already in_progress, skip
        if ticket['status'] == 'in_progress':
            return {"content": [{"type": "text", "text": f"Ticket {ticket['ticket_number']} is already running"}]}

        # For sub-tickets, start the parent instead
        target_id = ticket['id']
        target_number = ticket['ticket_number']
        is_subticket = False

        if ticket['parent_ticket_id']:
            is_subticket = True
            target_id = ticket['parent_ticket_id']
            target_number = ticket['parent_ticket_number']
            if ticket['parent_status'] == 'in_progress':
                return {"content": [{"type": "text", "text": f"Parent {target_number} is already running"}]}

        # Set to open + forced
        cursor.execute("""
            UPDATE tickets SET status = 'open', is_forced = TRUE, updated_at = NOW()
            WHERE id = %s
        """, (target_id,))
        conn.commit()

        if is_subticket:
            msg = f"Parent {target_number} queued to start next (will process sub-tickets)"
        else:
            msg = f"Ticket {target_number} queued to start next"

        result = {
            "success": True,
            "ticket_number": target_number,
            "is_subticket": is_subticket,
            "message": msg
        }
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}
    finally:
        cursor.close()
        conn.close()


def handle_import_project(args: Dict[str, Any]) -> Dict[str, Any]:
    """Import an existing project via ZIP, git, or path."""
    import subprocess
    import tempfile
    import shutil
    import urllib.request

    project_id = args.get('project_id')
    source_type = args.get('source_type')
    source = args.get('source')
    mode = args.get('mode', 'extend')

    if not project_id:
        return {"content": [{"type": "text", "text": "Error: project_id is required"}]}
    if not source_type or source_type not in ('zip', 'git', 'path'):
        return {"content": [{"type": "text", "text": "Error: source_type must be 'zip', 'git', or 'path'"}]}
    if not source:
        return {"content": [{"type": "text", "text": "Error: source is required"}]}
    if mode not in ('extend', 'reference'):
        mode = 'extend'

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get project details
        cursor.execute("SELECT id, code, web_path, app_path FROM projects WHERE id = %s", (project_id,))
        project = cursor.fetchone()
        if not project:
            return {"content": [{"type": "text", "text": f"Error: Project ID {project_id} not found"}]}

        project_code = project['code']
        project_path = project['web_path'] or project['app_path']

        # Determine destination path
        if mode == 'extend':
            if not project_path:
                return {"content": [{"type": "text", "text": "Error: Project has no web_path or app_path set"}]}
            dest_path = project_path
        else:  # reference
            dest_path = f"/opt/codehero/references/{project_code}"
            # Create references directory if not exists
            os.makedirs("/opt/codehero/references", exist_ok=True)

        # Create temp directory for processing
        temp_dir = tempfile.mkdtemp(prefix='codehero_import_')

        try:
            # Get source files based on source_type
            if source_type == 'path':
                # Local path - verify it exists
                if not os.path.exists(source):
                    return {"content": [{"type": "text", "text": f"Error: Source path does not exist: {source}"}]}
                source_path = source

            elif source_type == 'git':
                # Git clone (with optional credentials for private repos)
                clone_dir = os.path.join(temp_dir, 'repo')
                git_url = source
                git_username = args.get('git_username')
                git_token = args.get('git_token')

                # If credentials provided, inject into URL
                if git_token:
                    # Parse the git URL and inject credentials
                    # Supports: github.com, gitlab.com, bitbucket.org
                    import re
                    match = re.match(r'https?://([^/]+)/(.+)', source)
                    if match:
                        host = match.group(1)
                        path = match.group(2)

                        if 'gitlab' in host:
                            # GitLab uses oauth2:token format
                            git_url = f"https://oauth2:{git_token}@{host}/{path}"
                        elif git_username:
                            # GitHub/Bitbucket use username:token format
                            git_url = f"https://{git_username}:{git_token}@{host}/{path}"
                        else:
                            # GitHub can use just token
                            git_url = f"https://{git_token}@{host}/{path}"

                result = subprocess.run(
                    ['git', 'clone', '--depth', '1', git_url, clone_dir],
                    capture_output=True, text=True, timeout=300
                )
                if result.returncode != 0:
                    # Hide credentials from error message
                    error_msg = result.stderr
                    if git_token:
                        error_msg = error_msg.replace(git_token, '***')
                    if git_username:
                        error_msg = error_msg.replace(git_username, '***')
                    return {"content": [{"type": "text", "text": f"Error cloning git repo: {error_msg}"}]}
                source_path = clone_dir

            elif source_type == 'zip':
                # Download or copy ZIP, then extract
                zip_path = os.path.join(temp_dir, 'source.zip')

                if source.startswith('http://') or source.startswith('https://'):
                    # Download ZIP
                    try:
                        urllib.request.urlretrieve(source, zip_path)
                    except Exception as e:
                        return {"content": [{"type": "text", "text": f"Error downloading ZIP: {str(e)}"}]}
                else:
                    # Local ZIP file
                    if not os.path.exists(source):
                        return {"content": [{"type": "text", "text": f"Error: ZIP file not found: {source}"}]}
                    shutil.copy2(source, zip_path)

                # Extract ZIP
                extract_dir = os.path.join(temp_dir, 'extracted')
                os.makedirs(extract_dir)
                result = subprocess.run(
                    ['unzip', '-q', zip_path, '-d', extract_dir],
                    capture_output=True, text=True
                )
                if result.returncode != 0:
                    return {"content": [{"type": "text", "text": f"Error extracting ZIP: {result.stderr}"}]}

                # Find the root directory (might be inside a single folder)
                contents = os.listdir(extract_dir)
                if len(contents) == 1 and os.path.isdir(os.path.join(extract_dir, contents[0])):
                    source_path = os.path.join(extract_dir, contents[0])
                else:
                    source_path = extract_dir

            # Copy files to destination
            os.makedirs(dest_path, exist_ok=True)

            if source_type == 'path':
                # For local path in extend mode, copy files
                result = subprocess.run(
                    ['rsync', '-av', '--exclude', '.git', f'{source_path}/', f'{dest_path}/'],
                    capture_output=True, text=True
                )
            else:
                # For git/zip, copy from temp
                result = subprocess.run(
                    ['rsync', '-av', '--exclude', '.git', f'{source_path}/', f'{dest_path}/'],
                    capture_output=True, text=True
                )

            if result.returncode != 0:
                return {"content": [{"type": "text", "text": f"Error copying files: {result.stderr}"}]}

            # Set ownership
            subprocess.run(['sudo', 'chown', '-R', 'claude:claude', dest_path], capture_output=True)

            # Update project with reference path if reference mode
            if mode == 'reference':
                cursor.execute("""
                    UPDATE projects SET reference_path = %s WHERE id = %s
                """, (dest_path, project_id))
                conn.commit()

            # Count imported files
            file_count = sum(len(files) for _, _, files in os.walk(dest_path))

            result_data = {
                "success": True,
                "project_id": project_id,
                "mode": mode,
                "source_type": source_type,
                "destination": dest_path,
                "files_imported": file_count,
                "message": f"Project imported successfully to {dest_path}. Use codehero_analyze_project to build the project map."
            }

            return {"content": [{"type": "text", "text": json.dumps(result_data, indent=2)}]}

        finally:
            # Cleanup temp directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error importing project: {str(e)}"}]}
    finally:
        cursor.close()
        conn.close()


def handle_analyze_project(args: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze or re-analyze a project to build its map."""
    project_id = args.get('project_id')
    force = args.get('force', False)

    if not project_id:
        return {"content": [{"type": "text", "text": "Error: project_id is required"}]}

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get project details
        cursor.execute("""
            SELECT id, code, name, web_path, app_path, reference_path
            FROM projects WHERE id = %s
        """, (project_id,))
        project = cursor.fetchone()

        if not project:
            return {"content": [{"type": "text", "text": f"Error: Project ID {project_id} not found"}]}

        # Determine project path to analyze
        project_path = project['web_path'] or project['app_path']
        reference_path = project.get('reference_path')

        if not project_path and not reference_path:
            return {"content": [{"type": "text", "text": "Error: Project has no paths set (web_path, app_path, or reference_path)"}]}

        paths_to_analyze = []
        if project_path and os.path.exists(project_path):
            paths_to_analyze.append(('main', project_path))
        if reference_path and os.path.exists(reference_path):
            paths_to_analyze.append(('reference', reference_path))

        if not paths_to_analyze:
            return {"content": [{"type": "text", "text": "Error: No valid paths found to analyze"}]}

        # Check if analysis needed
        if not force:
            cursor.execute("""
                SELECT generated_at, expires_at FROM project_maps
                WHERE project_id = %s AND (expires_at IS NULL OR expires_at > NOW())
            """, (project_id,))
            existing_map = cursor.fetchone()
            if existing_map:
                return {"content": [{"type": "text", "text": json.dumps({
                    "success": True,
                    "project_id": project_id,
                    "message": "Project map already exists and is valid. Use force=true to re-analyze.",
                    "generated_at": existing_map['generated_at'].isoformat() if existing_map['generated_at'] else None
                }, indent=2)}]}

        # Import smart_context and run analysis
        import sys
        sys.path.insert(0, '/opt/codehero/scripts')
        try:
            from smart_context import SmartContextManager
            import mysql.connector.pooling

            # Create a simple pool for the context manager
            pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name="analysis_pool",
                pool_size=1,
                **DB_CONFIG
            )

            scm = SmartContextManager(pool)

            # Collect all paths to analyze (web_path, app_path, reference_path)
            def has_content(path):
                """Check if path has actual content (not just .git)"""
                if not path or not os.path.exists(path):
                    return False
                contents = [f for f in os.listdir(path) if not f.startswith('.')]
                return len(contents) > 0

            paths_to_analyze = []
            path_labels = []

            # Add web_path if has content
            if has_content(project.get('web_path')):
                paths_to_analyze.append(project['web_path'])
                path_labels.append('web')

            # Add app_path if has content (and different from web_path)
            if has_content(project.get('app_path')) and project.get('app_path') != project.get('web_path'):
                paths_to_analyze.append(project['app_path'])
                path_labels.append('app')

            # Add reference_path if has content (always include alongside other paths)
            if has_content(reference_path):
                paths_to_analyze.append(reference_path)
                path_labels.append('reference')

            if not paths_to_analyze:
                return {"content": [{"type": "text", "text": "Error: No paths with content found to analyze"}]}

            # If multiple paths, analyze each and combine results
            if len(paths_to_analyze) == 1:
                # Single path - use standard analysis
                result = scm.generate_project_map(project_id, paths_to_analyze[0])
            else:
                # Multiple paths - combine analysis
                combined_tree = []
                combined_files = 0
                combined_size = 0
                all_tech_stack = set()
                all_entry_points = []
                languages = {}

                for i, path in enumerate(paths_to_analyze):
                    label = path_labels[i]
                    # Get stats for this path
                    file_count, size_kb = scm._get_project_stats(path)
                    combined_files += file_count
                    combined_size += size_kb

                    # Get tree output
                    tree = scm._get_tree_output(path)
                    if tree:
                        combined_tree.append(f"=== {label.upper()} ({path}) ===\n{tree}")

                    # Detect language
                    lang = scm._detect_language(path)
                    if lang and lang != 'unknown':
                        languages[lang] = languages.get(lang, 0) + file_count

                    # Detect entry points
                    entries = scm._detect_entry_points(path)
                    for ep in entries:
                        all_entry_points.append(f"[{label}] {ep}")

                    # Detect tech stack
                    tech = scm._detect_tech_stack(path, None, None)
                    all_tech_stack.update(tech)

                # Determine primary language (most files)
                primary_language = max(languages, key=languages.get) if languages else 'unknown'

                # Save combined result
                from datetime import datetime, timedelta
                cursor.execute("""
                    INSERT INTO project_maps
                    (project_id, structure_summary, entry_points, key_files, tech_stack,
                     file_count, total_size_kb, primary_language, generated_at, expires_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
                    ON DUPLICATE KEY UPDATE
                    structure_summary = VALUES(structure_summary),
                    entry_points = VALUES(entry_points),
                    tech_stack = VALUES(tech_stack),
                    file_count = VALUES(file_count),
                    total_size_kb = VALUES(total_size_kb),
                    primary_language = VALUES(primary_language),
                    generated_at = NOW(),
                    expires_at = VALUES(expires_at)
                """, (
                    project_id,
                    '\n\n'.join(combined_tree)[:5000],
                    json.dumps(all_entry_points),
                    json.dumps([]),
                    json.dumps(list(all_tech_stack)),
                    combined_files,
                    combined_size,
                    primary_language,
                    datetime.now() + timedelta(days=7)
                ))
                conn.commit()
                result = True

            if result:
                # Get the generated map
                cursor.execute("""
                    SELECT file_count, total_size_kb, primary_language, tech_stack, entry_points
                    FROM project_maps WHERE project_id = %s
                """, (project_id,))
                pmap = cursor.fetchone()

                # Parse JSON fields for display
                tech_stack = []
                entry_points = []
                if pmap:
                    if pmap.get('tech_stack'):
                        try:
                            tech_stack = json.loads(pmap['tech_stack']) if isinstance(pmap['tech_stack'], str) else pmap['tech_stack']
                        except:
                            pass
                    if pmap.get('entry_points'):
                        try:
                            entry_points = json.loads(pmap['entry_points']) if isinstance(pmap['entry_points'], str) else pmap['entry_points']
                        except:
                            pass

                return {"content": [{"type": "text", "text": json.dumps({
                    "success": True,
                    "project_id": project_id,
                    "project_name": project['name'],
                    "analyzed_paths": paths_to_analyze,
                    "file_count": pmap['file_count'] if pmap else 0,
                    "total_size_kb": pmap['total_size_kb'] if pmap else 0,
                    "primary_language": pmap['primary_language'] if pmap else None,
                    "tech_stack": tech_stack,
                    "entry_points": entry_points,
                    "message": "Project analyzed successfully. Map is now available for AI tickets."
                }, indent=2)}]}
            else:
                return {"content": [{"type": "text", "text": "Error: Analysis returned no result"}]}

        except ImportError as e:
            return {"content": [{"type": "text", "text": f"Error: Could not import smart_context module: {str(e)}"}]}

    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error analyzing project: {str(e)}"}]}
    finally:
        cursor.close()
        conn.close()


# Tool handlers mapping
TOOL_HANDLERS = {
    "codehero_list_projects": handle_list_projects,
    "codehero_get_project": handle_get_project,
    "codehero_create_project": handle_create_project,
    "codehero_list_tickets": handle_list_tickets,
    "codehero_get_ticket": handle_get_ticket,
    "codehero_create_ticket": handle_create_ticket,
    "codehero_update_ticket": handle_update_ticket,
    "codehero_dashboard_stats": handle_dashboard_stats,
    "codehero_kill_switch": handle_kill_switch,
    "codehero_delete_ticket": handle_delete_ticket,
    "codehero_bulk_create_tickets": handle_bulk_create_tickets,
    "codehero_get_project_progress": handle_get_project_progress,
    "codehero_retry_ticket": handle_retry_ticket,
    "codehero_set_ticket_sequence": handle_set_ticket_sequence,
    "codehero_start_ticket": handle_start_ticket,
    "codehero_reload": handle_reload,
    "codehero_import_project": handle_import_project,
    "codehero_analyze_project": handle_analyze_project,
}

def handle_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle incoming JSON-RPC request."""
    method = request.get('method', '')
    request_id = request.get('id')
    params = request.get('params', {})

    if method == 'initialize':
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "codehero-mcp",
                    "version": "1.0.0"
                }
            }
        }

    elif method == 'notifications/initialized':
        return None  # No response needed

    elif method == 'tools/list':
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": TOOLS
            }
        }

    elif method == 'tools/call':
        tool_name = params.get('name')
        tool_args = params.get('arguments', {})

        if tool_name in TOOL_HANDLERS:
            try:
                result = TOOL_HANDLERS[tool_name](tool_args)
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }
            except Exception as e:
                log_error(f"Tool {tool_name} error: {str(e)}")
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                        "isError": True
                    }
                }
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Unknown tool: {tool_name}"
                }
            }

    elif method == 'ping':
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {}
        }

    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }

def main():
    """Main entry point - stdio JSON-RPC server."""
    log_info("Starting CodeHero MCP Server...")

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            line = line.strip()
            if not line:
                continue

            request = json.loads(line)
            response = handle_request(request)

            if response is not None:
                sys.stdout.write(json.dumps(response) + '\n')
                sys.stdout.flush()

        except json.JSONDecodeError as e:
            log_error(f"JSON decode error: {e}")
        except Exception as e:
            log_error(f"Error: {e}")

if __name__ == '__main__':
    main()
