#!/usr/bin/env python3
"""
Claude Assistant protection hook for CodeHero.
Filters tool requests based on safety rules for general assistant usage.

Unlike semi-autonomous mode (which is scoped to a project), this hook:
- Allows navigation and reading across the entire system
- Asks permission for dangerous commands
- Asks permission for system file modifications
- Blocks truly dangerous operations

This hook is called by Claude Code before each tool execution.
It returns one of three decisions:
- "allow": Auto-approve, execute without prompting
- "deny": Block the operation with an error message
- "ask": Use default permission flow (will prompt user via UI)
"""
import sys
import json
import os
import re


def main():
    # Read input from stdin
    try:
        input_data = json.load(sys.stdin)
    except Exception as e:
        output_error("Could not parse hook input")
        return

    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})

    # Evaluate the permission
    decision, reason = evaluate_permission(tool_name, tool_input)

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


def evaluate_permission(tool_name, tool_input):
    """
    Evaluate a tool request and return permission decision.

    Returns: (decision, reason)
    - decision: "allow" | "deny" | "ask"
    - reason: Human-readable explanation
    """

    # === FILE OPERATIONS ===
    if tool_name == 'Read':
        file_path = tool_input.get('file_path', '')
        return evaluate_read_operation(file_path)

    if tool_name in ['Edit', 'Write']:
        file_path = tool_input.get('file_path', '')
        return evaluate_write_operation(tool_name, file_path)

    # === BASH COMMANDS ===
    if tool_name == 'Bash':
        command = tool_input.get('command', '')
        return evaluate_bash_command(command)

    # === GLOB/GREP (Search operations) ===
    if tool_name in ['Glob', 'Grep']:
        path = tool_input.get('path', '')
        return evaluate_search_operation(tool_name, path)

    # === NOTEBOOK EDIT ===
    if tool_name == 'NotebookEdit':
        notebook_path = tool_input.get('notebook_path', '')
        return evaluate_write_operation('Edit', notebook_path)

    # === TASK/SUBAGENT ===
    if tool_name in ['Task', 'TaskOutput']:
        return ("allow", "Task operations allowed")

    # === WEB OPERATIONS ===
    if tool_name in ['WebFetch', 'WebSearch']:
        return ("allow", "Web operations allowed for assistant")

    # === TODO/ASK (Internal tools) ===
    if tool_name in ['TodoWrite', 'AskUserQuestion', 'EnterPlanMode', 'ExitPlanMode', 'Skill']:
        return ("allow", "Internal tool allowed")

    # === MCP TOOLS ===
    if tool_name.startswith('mcp__'):
        # Allow CodeHero MCP tools
        if tool_name.startswith('mcp__codehero__'):
            return ("allow", "CodeHero MCP tool allowed")
        # Other MCP tools allowed for assistant
        return ("allow", "MCP tool allowed")

    # === UNKNOWN TOOLS ===
    return ("ask", f"Unknown tool '{tool_name}' requires approval")


def evaluate_read_operation(file_path):
    """Evaluate file read operations - mostly permissive"""

    if not file_path:
        return ("deny", "No file path provided")

    file_path = os.path.normpath(file_path)

    # === BLOCKED: Highly sensitive paths ===
    blocked_read_paths = [
        # Root home directory
        '/root/',
        # SSH keys
        '/etc/shadow',
        '/etc/gshadow',
        '/.ssh/id_',
        '/.ssh/authorized_keys',
        '/home/claude/.ssh/',
        # Cloud credentials
        '/.aws/credentials',
        '/.aws/config',
        '/home/claude/.aws/',
        '/.gnupg/',
        '/home/claude/.gnupg/',
        # Database credentials
        '/var/lib/mysql/',
        '/opt/codehero/install.conf',
    ]

    for blocked in blocked_read_paths:
        if blocked in file_path:
            return ("deny", f"Cannot read sensitive file: {blocked}")

    # === ALLOWED: Everything else ===
    return ("allow", "Read allowed")


def evaluate_write_operation(tool_name, file_path):
    """Evaluate file edit/write operations - more restrictive"""

    if not file_path:
        return ("deny", "No file path provided")

    file_path = os.path.normpath(file_path)

    # === BLOCKED: Critical system paths ===
    blocked_paths = [
        # Root home directory
        '/root/',
        # System files
        '/etc/passwd',
        '/etc/shadow',
        '/etc/gshadow',
        '/etc/sudoers',
        '/etc/ssh/sshd_config',
        '/.ssh/',
        '/home/claude/.ssh/',
        '/.aws/',
        '/home/claude/.aws/',
        '/.gnupg/',
        '/home/claude/.gnupg/',
        '/boot/',
        '/usr/bin/',
        '/usr/sbin/',
        '/sbin/',
        '/bin/',
        # Database
        '/var/lib/mysql/',
        '/opt/codehero/install.conf',
        # Backups
        '/var/backups/',
    ]

    for blocked in blocked_paths:
        if blocked in file_path or file_path.startswith(blocked.lstrip('/')):
            return ("deny", f"Blocked: {blocked} is a critical system path")

    # === BLOCKED: .git folders (version control protection) ===
    if '/.git/' in file_path or file_path.endswith('/.git'):
        return ("deny", "Protected: .git folder is read-only (version control protection)")

    # === BLOCKED: Backup zip files ===
    if file_path.startswith('/home/claude/codehero-') and file_path.endswith('.zip'):
        return ("deny", "Protected: backup zip files cannot be modified")

    # === ALLOWED: Safe paths (can edit freely) ===
    safe_paths = [
        '/home/claude/',
        '/var/www/projects/',
        '/opt/apps/',
        '/tmp/',
    ]

    for safe in safe_paths:
        if file_path.startswith(safe):
            return ("allow", f"{tool_name} in safe path allowed")

    # === ASK: System paths that might be needed ===
    system_paths = [
        '/etc/',
        '/var/',
        '/opt/',
        '/usr/',
        '/root/',
    ]

    for sys_path in system_paths:
        if file_path.startswith(sys_path):
            return ("ask", f"Modifying {sys_path} requires approval")

    # === ASK: Unknown paths ===
    return ("ask", f"File modification requires approval: {file_path}")


def evaluate_search_operation(tool_name, path):
    """Evaluate Glob/Grep search operations - permissive"""

    if not path:
        return ("allow", f"{tool_name} allowed")

    path = os.path.normpath(path)

    # Block searching in highly sensitive paths
    blocked_paths = [
        '/root',
        '/.ssh',
        '/home/claude/.ssh',
        '/.aws',
        '/home/claude/.aws',
        '/.gnupg',
        '/var/lib/mysql',
    ]
    for blocked in blocked_paths:
        if blocked in path:
            return ("deny", f"Cannot search in {blocked}")

    return ("allow", f"{tool_name} allowed")


def evaluate_bash_command(command):
    """Evaluate bash commands"""

    if not command:
        return ("deny", "No command provided")

    command = command.strip()

    # === ALWAYS BLOCKED: Destructive/dangerous ===
    blocked_patterns = [
        # System destruction
        (r'rm\s+-rf\s+/', "rm -rf / is blocked"),
        (r'rm\s+-rf\s+~', "rm -rf ~ is blocked"),
        (r'rm\s+-rf\s+/root', "rm -rf /root is blocked"),
        (r'rm\s+-rf\s+/home', "rm -rf /home is blocked"),
        (r'rm\s+-rf\s+/etc', "rm -rf /etc is blocked"),
        (r'rm\s+-rf\s+/var\s*$', "rm -rf /var is blocked"),
        (r'rm\s+-rf\s+/usr', "rm -rf /usr is blocked"),
        (r'rm\s+-rf\s+/opt\s*$', "rm -rf /opt is blocked"),
        (r'rm\s+-rf\s+\*', "rm -rf * is blocked"),
        # Project/backup destruction
        (r'rm\s+-rf\s+/var/www/projects\s*$', "rm -rf /var/www/projects is blocked (all projects)"),
        (r'rm\s+-rf\s+/opt/apps\s*$', "rm -rf /opt/apps is blocked (all apps)"),
        (r'rm\s+-rf\s+/var/backups', "rm -rf /var/backups is blocked"),
        (r'rm\s+.*codehero.*\.zip', "deleting backup zip files is blocked"),
        # Git destruction
        (r'rm\s+-rf\s+.*\.git', "rm -rf .git is blocked (version control)"),
        (r'rm\s+-rf\s+.*/.git', "rm -rf .git is blocked (version control)"),
        # Database destruction
        (r'rm\s+-rf\s+/var/lib/mysql', "rm -rf mysql data is blocked"),
        (r'drop\s+database', "DROP DATABASE is blocked"),
        (r'truncate\s+', "TRUNCATE is blocked"),
        # SSH destruction
        (r'rm\s+.*\.ssh', "deleting .ssh is blocked"),
        (r'rm\s+-rf\s+.*\.ssh', "deleting .ssh is blocked"),
        # Disk operations
        (r'mkfs\.', "mkfs is blocked"),
        (r'dd\s+if=/dev/zero', "dd zero write is blocked"),
        (r'dd\s+if=/dev/random', "dd random write is blocked"),
        (r'>\s*/dev/sd', "writing to disk device is blocked"),
        (r'>\s*/dev/hd', "writing to disk device is blocked"),
        # Security
        (r':\(\)\s*\{\s*:\|:', "fork bomb is blocked"),
        (r'chmod\s+-R\s+777\s+/', "chmod -R 777 / is blocked"),
        (r'chown\s+-R\s+.*\s+/', "chown -R / is blocked"),
        (r'curl.*\|\s*sh', "curl pipe to sh is blocked"),
        (r'curl.*\|\s*bash', "curl pipe to bash is blocked"),
        (r'wget.*\|\s*sh', "wget pipe to sh is blocked"),
        (r'wget.*\|\s*bash', "wget pipe to bash is blocked"),
    ]

    for pattern, reason in blocked_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            return ("deny", reason)

    # === ALWAYS ALLOWED: Safe read-only commands ===
    safe_patterns = [
        (r'^\s*ls(\s|$)', "ls"),
        (r'^\s*pwd\s*$', "pwd"),
        (r'^\s*echo\s', "echo"),
        (r'^\s*cat\s', "cat"),
        (r'^\s*head\s', "head"),
        (r'^\s*tail\s', "tail"),
        (r'^\s*less\s', "less"),
        (r'^\s*more\s', "more"),
        (r'^\s*wc\s', "wc"),
        (r'^\s*find\s', "find"),
        (r'^\s*grep\s', "grep"),
        (r'^\s*rg\s', "ripgrep"),
        (r'^\s*which\s', "which"),
        (r'^\s*whereis\s', "whereis"),
        (r'^\s*type\s', "type"),
        (r'^\s*file\s', "file"),
        (r'^\s*stat\s', "stat"),
        (r'^\s*du\s', "du"),
        (r'^\s*df\s', "df"),
        (r'^\s*free\s', "free"),
        (r'^\s*uptime', "uptime"),
        (r'^\s*date\s*$', "date"),
        (r'^\s*whoami\s*$', "whoami"),
        (r'^\s*id(\s|$)', "id"),
        (r'^\s*env\s*$', "env"),
        (r'^\s*printenv', "printenv"),
        (r'^\s*uname', "uname"),
        (r'^\s*hostname\s*$', "hostname"),
        (r'^\s*ps\s', "ps"),
        (r'^\s*top\s+-bn1', "top batch"),
        (r'^\s*htop', "htop"),

        # Git read-only
        (r'^\s*git\s+status', "git status"),
        (r'^\s*git\s+log', "git log"),
        (r'^\s*git\s+diff', "git diff"),
        (r'^\s*git\s+show', "git show"),
        (r'^\s*git\s+branch(\s+-[avrl]|\s*$)', "git branch"),
        (r'^\s*git\s+remote\s+-v', "git remote"),
        (r'^\s*git\s+tag(\s+-l|\s*$)', "git tag"),
        (r'^\s*git\s+rev-parse', "git rev-parse"),
        (r'^\s*git\s+ls-files', "git ls-files"),
        (r'^\s*git\s+ls-tree', "git ls-tree"),

        # Testing/Building
        (r'^\s*npm\s+run\s', "npm run"),
        (r'^\s*npm\s+test', "npm test"),
        (r'^\s*npm\s+start', "npm start"),
        (r'^\s*npm\s+ci', "npm ci"),
        (r'^\s*yarn\s+run\s', "yarn run"),
        (r'^\s*yarn\s+test', "yarn test"),
        (r'^\s*yarn\s+start', "yarn start"),
        (r'^\s*pnpm\s+run\s', "pnpm run"),
        (r'^\s*pnpm\s+test', "pnpm test"),
        (r'^\s*composer\s+run', "composer run"),
        (r'^\s*phpunit', "phpunit"),
        (r'^\s*pytest', "pytest"),
        (r'^\s*jest', "jest"),
        (r'^\s*vitest', "vitest"),
        (r'^\s*mocha', "mocha"),
        (r'^\s*make(\s|$)', "make"),
        (r'^\s*cargo\s+(build|test|run|check)', "cargo"),
        (r'^\s*go\s+(build|test|run)', "go"),

        # Linting
        (r'^\s*eslint', "eslint"),
        (r'^\s*prettier', "prettier"),
        (r'^\s*phpcs', "phpcs"),
        (r'^\s*phpstan', "phpstan"),
        (r'^\s*tsc(\s|$)', "tsc"),

        # Scripts/interpreters
        (r'^\s*node\s', "node"),
        (r'^\s*python3?\s', "python"),
        (r'^\s*php\s', "php"),

        # System info
        (r'^\s*systemctl\s+status', "systemctl status"),
        (r'^\s*systemctl\s+is-active', "systemctl is-active"),
        (r'^\s*systemctl\s+list-units', "systemctl list-units"),
        (r'^\s*journalctl', "journalctl"),
        (r'^\s*service\s+\S+\s+status', "service status"),
    ]

    for pattern, description in safe_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            return ("allow", f"Safe: {description}")

    # === REQUIRES APPROVAL: Potentially risky commands ===
    approval_patterns = [
        (r'^\s*sudo\s', "sudo command"),
        (r'^\s*su\s', "su command"),
        (r'^\s*apt\s', "apt command"),
        (r'^\s*apt-get\s', "apt-get command"),
        (r'^\s*dpkg\s', "dpkg command"),
        (r'^\s*pip\s+install', "pip install"),
        (r'^\s*pip3\s+install', "pip3 install"),
        (r'^\s*npm\s+install\s+\S', "npm install package"),
        (r'^\s*yarn\s+add\s', "yarn add"),
        (r'^\s*composer\s+require', "composer require"),
        (r'^\s*systemctl\s+(start|stop|restart|enable|disable)', "systemctl control"),
        (r'^\s*service\s+\S+\s+(start|stop|restart)', "service control"),
        (r'^\s*rm\s', "rm command"),
        (r'^\s*rmdir\s', "rmdir command"),
        (r'^\s*mv\s', "mv command"),
        (r'^\s*cp\s', "cp command"),
        (r'^\s*chmod\s', "chmod command"),
        (r'^\s*chown\s', "chown command"),
        (r'^\s*mkdir\s', "mkdir command"),
        (r'^\s*touch\s', "touch command"),
        (r'^\s*git\s+add', "git add"),
        (r'^\s*git\s+commit', "git commit"),
        (r'^\s*git\s+push', "git push"),
        (r'^\s*git\s+pull', "git pull"),
        (r'^\s*git\s+merge', "git merge"),
        (r'^\s*git\s+checkout', "git checkout"),
        (r'^\s*git\s+reset', "git reset"),
        (r'^\s*git\s+rebase', "git rebase"),
        (r'^\s*git\s+stash', "git stash"),
        (r'^\s*git\s+clone', "git clone"),
        (r'^\s*curl\s', "curl"),
        (r'^\s*wget\s', "wget"),
        (r'^\s*ssh\s', "ssh"),
        (r'^\s*scp\s', "scp"),
        (r'^\s*rsync\s', "rsync"),
        (r'^\s*docker\s', "docker"),
        (r'^\s*docker-compose\s', "docker-compose"),
        (r'^\s*kubectl\s', "kubectl"),
        (r'^\s*mysql\s', "mysql"),
        (r'^\s*psql\s', "psql"),
        (r'^\s*mongosh', "mongosh"),
        (r'^\s*redis-cli', "redis-cli"),
        (r'^\s*php\s+artisan\s+migrate', "artisan migrate"),
        (r'^\s*php\s+artisan\s+db:', "artisan db"),
        (r'/etc/', "accessing /etc"),
        (r'/opt/codehero/', "accessing /opt/codehero"),
    ]

    for pattern, description in approval_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            return ("ask", f"Requires approval: {description}")

    # === DEFAULT: Allow simple commands, ask for complex ones ===
    # If command is short and doesn't match dangerous patterns, allow it
    if len(command) < 50 and not any(c in command for c in ['|', '>', '<', ';', '&&', '`', '$(']):
        return ("allow", "Simple command allowed")

    return ("ask", "Complex command requires approval")


if __name__ == '__main__':
    main()
