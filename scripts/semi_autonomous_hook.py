#!/usr/bin/env python3
"""
Semi-autonomous mode hook for CodeHero.
Filters tool requests based on safety rules.

This hook is called by Claude Code before each tool execution.
It returns one of three decisions:
- "allow": Auto-approve, execute without prompting
- "deny": Block the operation with an error message
- "ask": Use default permission flow (will prompt user via UI)

Environment variables:
- CODEHERO_PROJECT_PATH: The project's working directory
- CODEHERO_TICKET_ID: The ticket ID for checking approved permissions
"""
import sys
import json
import os
import re
import fnmatch

# Try to import mysql connector - if not available, skip DB lookups
try:
    import mysql.connector
    HAS_MYSQL = True
except ImportError:
    HAS_MYSQL = False

def get_approved_permissions(ticket_id):
    """
    Fetch approved_permissions from database for this ticket.
    Returns list of permission patterns or empty list if unavailable.
    """
    if not HAS_MYSQL or not ticket_id:
        return []

    try:
        # Read database config from install.conf
        config_path = '/opt/codehero/install.conf'
        db_config = {'user': 'codehero', 'password': '', 'database': 'codehero', 'host': 'localhost'}

        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        value = value.strip('"\'')
                        if key == 'DB_PASSWORD':
                            db_config['password'] = value
                        elif key == 'DB_USER':
                            db_config['user'] = value
                        elif key == 'DB_NAME':
                            db_config['database'] = value

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT approved_permissions FROM tickets WHERE id = %s", (ticket_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row and row[0]:
            perms = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            return perms if isinstance(perms, list) else []
        return []
    except Exception:
        return []


def check_approved_pattern(tool_name, tool_input, approved_permissions):
    """
    Check if this operation matches any approved pattern.
    Returns (True, reason) if approved, (False, None) otherwise.
    """
    if not approved_permissions:
        return False, None

    for perm in approved_permissions:
        if not isinstance(perm, dict):
            continue

        perm_tool = perm.get('tool', '')
        pattern = perm.get('pattern', '*')
        once = perm.get('once', False)

        # Check if tool matches
        if perm_tool != tool_name:
            continue

        # For Bash commands, check command pattern
        if tool_name == 'Bash':
            command = tool_input.get('command', '')
            # Pattern like "npm *" should match "npm install express"
            if pattern == '*':
                return True, f"Pre-approved: all {tool_name} operations"
            if fnmatch.fnmatch(command, pattern):
                return True, f"Pre-approved: matches pattern '{pattern}'"
            # Also check if command starts with the pattern base (e.g., "npm *" matches "npm install")
            pattern_base = pattern.rstrip(' *')
            if pattern_base and command.startswith(pattern_base):
                return True, f"Pre-approved: command starts with '{pattern_base}'"

        # For file operations, check path pattern
        elif tool_name in ('Edit', 'Write', 'Read'):
            file_path = tool_input.get('file_path', '')
            if pattern == '*':
                return True, f"Pre-approved: all {tool_name} operations"
            if fnmatch.fnmatch(file_path, pattern):
                return True, f"Pre-approved: file matches pattern '{pattern}'"

        # Generic pattern match
        elif pattern == '*':
            return True, f"Pre-approved: all {tool_name} operations"

    return False, None


def main():
    # Read input from stdin
    try:
        input_data = json.load(sys.stdin)
    except Exception as e:
        # If we can't parse input, deny for safety
        output_error("Could not parse hook input")
        return

    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})
    cwd = input_data.get('cwd', '')

    # Get project path from environment (set by daemon)
    project_path = os.environ.get('CODEHERO_PROJECT_PATH', cwd)
    ticket_id = os.environ.get('CODEHERO_TICKET_ID', '')

    # Normalize paths
    project_path = os.path.normpath(project_path) if project_path else ''

    # First, check if this operation is pre-approved
    approved_permissions = get_approved_permissions(ticket_id)
    is_approved, approved_reason = check_approved_pattern(tool_name, tool_input, approved_permissions)
    if is_approved:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": approved_reason
            }
        }
        print(json.dumps(output))
        return

    # Not pre-approved, evaluate using standard rules
    decision, reason = evaluate_permission(tool_name, tool_input, project_path)

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason
        }
    }

    print(json.dumps(output))


def output_error(message):
    """Output a deny decision with error message"""
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"Hook error: {message}"
        }
    }
    print(json.dumps(output))


def evaluate_permission(tool_name, tool_input, project_path):
    """
    Evaluate a tool request and return permission decision.

    Returns: (decision, reason)
    - decision: "allow" | "deny" | "ask"
    - reason: Human-readable explanation
    """

    # === FILE OPERATIONS ===
    if tool_name in ['Read', 'Edit', 'Write']:
        file_path = tool_input.get('file_path', '')
        return evaluate_file_operation(tool_name, file_path, project_path)

    # === BASH COMMANDS ===
    if tool_name == 'Bash':
        command = tool_input.get('command', '')
        return evaluate_bash_command(command, project_path)

    # === GLOB/GREP (Search operations) ===
    if tool_name in ['Glob', 'Grep']:
        path = tool_input.get('path', project_path)
        return evaluate_search_operation(tool_name, path, project_path)

    # === NOTEBOOK EDIT ===
    if tool_name == 'NotebookEdit':
        notebook_path = tool_input.get('notebook_path', '')
        return evaluate_file_operation('Edit', notebook_path, project_path)

    # === TASK/SUBAGENT ===
    if tool_name in ['Task', 'TaskOutput']:
        # Allow task spawning - the subagent will have its own hooks
        return ("allow", "Task operations allowed")

    # === WEB OPERATIONS ===
    if tool_name in ['WebFetch', 'WebSearch']:
        return ("ask", "Web operations require approval")

    # === TODO/ASK (Internal tools) ===
    if tool_name in ['TodoWrite', 'AskUserQuestion', 'EnterPlanMode', 'ExitPlanMode']:
        return ("allow", "Internal tool allowed")

    # === MCP TOOLS ===
    if tool_name.startswith('mcp__'):
        # Allow CodeHero MCP tools
        if tool_name.startswith('mcp__codehero__'):
            return ("allow", "CodeHero MCP tool allowed")
        # Other MCP tools require approval
        return ("ask", "MCP tool requires approval")

    # === UNKNOWN TOOLS ===
    return ("ask", f"Unknown tool '{tool_name}' requires approval")


def evaluate_file_operation(tool_name, file_path, project_path):
    """Evaluate file read/edit/write operations"""

    if not file_path:
        return ("deny", "No file path provided")

    # Normalize the file path
    file_path = os.path.normpath(file_path)

    # Resolve to absolute path if relative
    if not os.path.isabs(file_path):
        file_path = os.path.normpath(os.path.join(project_path, file_path))

    # === BLOCKED: .git folder (backup protection) ===
    if '/.git/' in file_path or file_path.endswith('/.git') or '/.git' in file_path:
        return ("deny", "Protected: .git folder is read-only (backup protection)")

    # === BLOCKED: Paths outside project ===
    if project_path and not file_path.startswith(project_path):
        # Check for specifically blocked system paths
        blocked_paths = [
            '/opt/codehero',
            '/etc/',
            '/.ssh',
            '/.aws',
            '/.claude',
            '/root',
        ]
        for blocked in blocked_paths:
            if blocked in file_path or file_path.startswith(blocked.lstrip('/')):
                return ("deny", f"Blocked: {blocked} is a protected system path")

        # For Read operations outside project, allow (might need to read docs, examples)
        if tool_name == 'Read':
            return ("allow", f"Read allowed outside project")

        # For Edit/Write outside project, require approval
        return ("ask", f"File outside project path requires approval")

    # === ALLOWED: File operations within project (except .git) ===
    return ("allow", f"{tool_name} within project allowed")


def evaluate_search_operation(tool_name, path, project_path):
    """Evaluate Glob/Grep search operations"""

    if not path:
        path = project_path

    path = os.path.normpath(path)

    # Block searching in .git
    if '/.git' in path:
        return ("deny", "Cannot search in .git folder")

    # Block searching in system paths
    blocked_paths = ['/opt/codehero', '/etc/', '/.ssh', '/.aws']
    for blocked in blocked_paths:
        if blocked in path:
            return ("deny", f"Cannot search in {blocked}")

    # Allow searching
    return ("allow", f"{tool_name} allowed")


def evaluate_bash_command(command, project_path):
    """Evaluate bash commands"""

    if not command:
        return ("deny", "No command provided")

    # Normalize command (strip whitespace, handle multiline)
    command = command.strip()

    # === ALWAYS BLOCKED ===
    blocked_patterns = [
        (r'^\s*sudo\s', "sudo commands not allowed"),
        (r'^\s*su\s', "su commands not allowed"),
        (r'\|\s*sudo', "piping to sudo not allowed"),
        (r'^\s*apt\s', "apt not allowed (use approval for package management)"),
        (r'^\s*apt-get\s', "apt-get not allowed"),
        (r'^\s*yum\s', "yum not allowed"),
        (r'^\s*dnf\s', "dnf not allowed"),
        (r'^\s*pacman\s', "pacman not allowed"),
        (r'^\s*systemctl\s', "systemctl not allowed (requires approval)"),
        (r'^\s*service\s', "service not allowed (requires approval)"),
        (r'^\s*chmod\s+777', "chmod 777 not allowed (security risk)"),
        (r'^\s*chmod\s+-R\s+777', "chmod -R 777 not allowed"),
        (r'^\s*chown\s', "chown not allowed"),
        (r'^\s*rm\s+-rf\s+/', "rm -rf / not allowed"),
        (r'^\s*rm\s+-rf\s+~', "rm -rf ~ not allowed"),
        (r'^\s*rm\s+-rf\s+\*', "rm -rf * at root not allowed"),
        (r'^\s*mkfs', "mkfs not allowed"),
        (r'^\s*dd\s+if=', "dd not allowed"),
        (r'^\s*>\s*/dev/', "writing to /dev not allowed"),
        (r'^\s*git\s+init', "git init not allowed (.git is protected)"),
        (r'^\s*git\s+clone', "git clone requires approval"),
        (r'/opt/codehero', "accessing /opt/codehero not allowed"),
        (r'/etc/', "accessing /etc not allowed"),
        (r'~/.ssh', "accessing ~/.ssh not allowed"),
        (r'~/.aws', "accessing ~/.aws not allowed"),
    ]

    for pattern, reason in blocked_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            return ("deny", reason)

    # === AUTO-APPROVE: Safe commands ===
    safe_patterns = [
        # NPM/Yarn - run scripts, install from lockfile
        (r'^\s*npm\s+run\s', "npm run scripts"),
        (r'^\s*npm\s+test', "npm test"),
        (r'^\s*npm\s+install\s*$', "npm install from lockfile"),
        (r'^\s*npm\s+ci', "npm ci"),
        (r'^\s*npm\s+start', "npm start"),
        (r'^\s*npm\s+run-script\s', "npm run-script"),
        (r'^\s*npx\s+', "npx commands"),
        (r'^\s*yarn\s+run\s', "yarn run"),
        (r'^\s*yarn\s+test', "yarn test"),
        (r'^\s*yarn\s+install\s*$', "yarn install from lockfile"),
        (r'^\s*yarn\s+start', "yarn start"),
        (r'^\s*yarn\s*$', "yarn install"),
        (r'^\s*pnpm\s+run\s', "pnpm run"),
        (r'^\s*pnpm\s+test', "pnpm test"),
        (r'^\s*pnpm\s+install\s*$', "pnpm install"),

        # Composer
        (r'^\s*composer\s+install\s*$', "composer install from lockfile"),
        (r'^\s*composer\s+dump-autoload', "composer dump-autoload"),
        (r'^\s*composer\s+run-script\s', "composer run-script"),
        (r'^\s*composer\s+run\s', "composer run"),
        (r'^\s*composer\s+check-platform-reqs', "composer check"),
        (r'^\s*composer\s+validate', "composer validate"),

        # PHP Artisan (except migrate/db)
        (r'^\s*php\s+artisan\s+(?!migrate|db:)', "php artisan (non-db)"),

        # Testing frameworks
        (r'^\s*phpunit', "phpunit"),
        (r'^\s*pest', "pest"),
        (r'^\s*vendor/bin/phpunit', "vendor phpunit"),
        (r'^\s*vendor/bin/pest', "vendor pest"),
        (r'^\s*./vendor/bin/phpunit', "vendor phpunit"),
        (r'^\s*./vendor/bin/pest', "vendor pest"),
        (r'^\s*playwright\s+test', "playwright test"),
        (r'^\s*npx\s+playwright', "npx playwright"),
        (r'^\s*cypress\s+run', "cypress run"),
        (r'^\s*npx\s+cypress', "npx cypress"),
        (r'^\s*jest', "jest"),
        (r'^\s*vitest', "vitest"),
        (r'^\s*mocha', "mocha"),
        (r'^\s*pytest', "pytest"),
        (r'^\s*python\s+-m\s+pytest', "python pytest"),

        # Linting/Formatting
        (r'^\s*eslint', "eslint"),
        (r'^\s*prettier', "prettier"),
        (r'^\s*phpcs', "phpcs"),
        (r'^\s*php-cs-fixer', "php-cs-fixer"),
        (r'^\s*phpcbf', "phpcbf"),
        (r'^\s*phpstan', "phpstan"),
        (r'^\s*psalm', "psalm"),
        (r'^\s*stylelint', "stylelint"),
        (r'^\s*tsc', "typescript compiler"),
        (r'^\s*npx\s+tsc', "npx tsc"),

        # Git read-only
        (r'^\s*git\s+status', "git status"),
        (r'^\s*git\s+log', "git log"),
        (r'^\s*git\s+diff', "git diff"),
        (r'^\s*git\s+branch\s*$', "git branch list"),
        (r'^\s*git\s+branch\s+-[avrl]', "git branch list"),
        (r'^\s*git\s+show', "git show"),
        (r'^\s*git\s+remote\s+-v', "git remote list"),
        (r'^\s*git\s+tag\s*$', "git tag list"),
        (r'^\s*git\s+tag\s+-l', "git tag list"),

        # Build tools
        (r'^\s*make\s', "make"),
        (r'^\s*gradle\s', "gradle"),
        (r'^\s*mvn\s', "maven"),
        (r'^\s*cargo\s+build', "cargo build"),
        (r'^\s*cargo\s+test', "cargo test"),
        (r'^\s*cargo\s+run', "cargo run"),
        (r'^\s*go\s+build', "go build"),
        (r'^\s*go\s+test', "go test"),
        (r'^\s*go\s+run', "go run"),

        # Common safe commands
        (r'^\s*ls\s', "ls"),
        (r'^\s*ls\s*$', "ls"),
        (r'^\s*pwd\s*$', "pwd"),
        (r'^\s*echo\s', "echo"),
        (r'^\s*cat\s', "cat"),
        (r'^\s*head\s', "head"),
        (r'^\s*tail\s', "tail"),
        (r'^\s*wc\s', "wc"),
        (r'^\s*find\s', "find"),
        (r'^\s*grep\s', "grep"),
        (r'^\s*which\s', "which"),
        (r'^\s*whereis\s', "whereis"),
        (r'^\s*file\s', "file"),
        (r'^\s*stat\s', "stat"),
        (r'^\s*du\s', "du"),
        (r'^\s*df\s', "df"),
        (r'^\s*date\s*$', "date"),
        (r'^\s*whoami\s*$', "whoami"),
        (r'^\s*id\s*$', "id"),
        (r'^\s*env\s*$', "env"),
        (r'^\s*printenv', "printenv"),
        (r'^\s*uname', "uname"),
        (r'^\s*hostname\s*$', "hostname"),
        (r'^\s*mkdir\s', "mkdir"),
        (r'^\s*touch\s', "touch"),
        (r'^\s*cp\s', "cp"),
        (r'^\s*mv\s', "mv"),
        (r'^\s*rm\s+(?!-rf)', "rm (non-recursive)"),

        # PHP commands
        (r'^\s*php\s+-[vr]', "php version/run"),
        (r'^\s*php\s+.*\.php', "php script"),

        # Node/Python scripts
        (r'^\s*node\s', "node"),
        (r'^\s*python3?\s', "python"),

        # Curl/wget to localhost only (for testing)
        (r'^\s*curl\s+.*localhost', "curl localhost"),
        (r'^\s*curl\s+.*127\.0\.0\.1', "curl localhost"),
        (r'^\s*wget\s+.*localhost', "wget localhost"),
    ]

    for pattern, description in safe_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            return ("allow", f"Safe: {description}")

    # === REQUIRES APPROVAL ===
    approval_hints = [
        (r'npm\s+install\s+\S', "installing new npm package"),
        (r'npm\s+update', "npm update"),
        (r'yarn\s+add\s', "adding yarn package"),
        (r'composer\s+require\s', "composer require"),
        (r'composer\s+update', "composer update"),
        (r'pip\s+install', "pip install"),
        (r'php\s+artisan\s+migrate', "database migration"),
        (r'php\s+artisan\s+db:', "database operation"),
        (r'git\s+add', "git staging"),
        (r'git\s+commit', "git commit"),
        (r'git\s+push', "git push"),
        (r'git\s+pull', "git pull"),
        (r'git\s+merge', "git merge"),
        (r'git\s+checkout', "git checkout"),
        (r'git\s+stash', "git stash"),
        (r'git\s+reset', "git reset"),
        (r'git\s+rebase', "git rebase"),
        (r'curl\s+', "curl request"),
        (r'wget\s+', "wget request"),
        (r'ssh\s+', "ssh connection"),
        (r'scp\s+', "scp transfer"),
        (r'rsync\s+', "rsync"),
        (r'docker\s+', "docker command"),
        (r'docker-compose\s+', "docker-compose"),
        (r'kubectl\s+', "kubernetes"),
    ]

    for pattern, description in approval_hints:
        if re.search(pattern, command, re.IGNORECASE):
            return ("ask", f"Requires approval: {description}")

    # Default: require approval for unknown commands
    return ("ask", "Unknown command requires approval")


if __name__ == '__main__':
    main()
