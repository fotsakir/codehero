#!/usr/bin/env python3
"""
CodeHero Permission Hook for Supervised Mode

This hook intercepts tool calls and checks if they're approved.
Used with Claude Code's PreToolUse hook mechanism.

Exit codes:
  0 = approve (tool can proceed)
  2 = block (tool is blocked, reason in stdout)

Environment variables:
  CODEHERO_TICKET_ID - The ticket ID being processed
  CODEHERO_APPROVED_PERMISSIONS - JSON array of approved permission patterns
"""

import sys
import json
import os
import re
import fnmatch

# Safe tools that are always allowed (read-only operations)
SAFE_TOOLS = [
    'Read',
    'Glob',
    'Grep',
    'WebSearch',
    'WebFetch',
    'Task',  # Sub-agents inherit permissions
    'TodoWrite',
    'AskUserQuestion',
]

# Tools that need explicit approval
RESTRICTED_TOOLS = [
    'Bash',
    'Edit',
    'Write',
    'NotebookEdit',
]

def load_approved_permissions():
    """Load approved permissions from environment or file"""
    # Try environment variable first
    env_perms = os.environ.get('CODEHERO_APPROVED_PERMISSIONS', '')
    if env_perms:
        try:
            return json.loads(env_perms)
        except:
            pass

    # Try file
    ticket_id = os.environ.get('CODEHERO_TICKET_ID', '')
    if ticket_id:
        perm_file = f"/var/run/codehero/permissions_{ticket_id}.json"
        if os.path.exists(perm_file):
            try:
                with open(perm_file, 'r') as f:
                    return json.load(f)
            except:
                pass

    return []

def save_pending_permission(ticket_id, tool_name, tool_input):
    """Save the pending permission request for user review"""
    pending = {
        'tool': tool_name,
        'input': tool_input,
        'timestamp': __import__('datetime').datetime.now().isoformat()
    }

    perm_file = f"/var/run/codehero/pending_{ticket_id}.json"
    try:
        os.makedirs('/var/run/codehero', exist_ok=True)
        with open(perm_file, 'w') as f:
            json.dump(pending, f)
    except Exception as e:
        sys.stderr.write(f"Error saving pending permission: {e}\n")

def is_permission_approved(tool_name, tool_input, approved_perms):
    """Check if this tool call matches any approved permission pattern"""
    for perm in approved_perms:
        perm_tool = perm.get('tool', '')
        perm_pattern = perm.get('pattern', '*')

        # Check tool match
        if perm_tool != '*' and perm_tool != tool_name:
            continue

        # Check pattern match based on tool type
        if tool_name == 'Bash':
            command = tool_input.get('command', '')
            if fnmatch.fnmatch(command, perm_pattern):
                return True
            # Also check if pattern is a prefix (e.g., "npm *" matches "npm install")
            if perm_pattern.endswith(' *'):
                prefix = perm_pattern[:-2]
                if command.startswith(prefix):
                    return True

        elif tool_name in ['Edit', 'Write']:
            file_path = tool_input.get('file_path', '')
            if fnmatch.fnmatch(file_path, perm_pattern):
                return True

        elif perm_pattern == '*':
            # Wildcard pattern approves any input for this tool
            return True

    return False

def get_tool_description(tool_name, tool_input):
    """Get a human-readable description of the tool call"""
    if tool_name == 'Bash':
        cmd = tool_input.get('command', 'unknown command')
        desc = tool_input.get('description', '')
        if desc:
            return f"Run command: {cmd}\n({desc})"
        return f"Run command: {cmd}"

    elif tool_name == 'Edit':
        path = tool_input.get('file_path', 'unknown file')
        old = tool_input.get('old_string', '')[:50]
        new = tool_input.get('new_string', '')[:50]
        return f"Edit file: {path}\nReplace: '{old}...' → '{new}...'"

    elif tool_name == 'Write':
        path = tool_input.get('file_path', 'unknown file')
        content_len = len(tool_input.get('content', ''))
        return f"Write file: {path} ({content_len} chars)"

    elif tool_name == 'NotebookEdit':
        path = tool_input.get('notebook_path', 'unknown notebook')
        return f"Edit notebook: {path}"

    return f"{tool_name}: {json.dumps(tool_input)[:100]}"

def main():
    # Read tool call from stdin
    try:
        input_data = json.load(sys.stdin)
    except:
        # Can't parse input, allow by default
        sys.exit(0)

    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})

    # Safe tools are always allowed
    if tool_name in SAFE_TOOLS:
        sys.exit(0)

    # Check if tool is restricted
    if tool_name not in RESTRICTED_TOOLS:
        # Unknown tool - allow by default
        sys.exit(0)

    # Load approved permissions
    approved_perms = load_approved_permissions()

    # Check if this specific call is approved
    if is_permission_approved(tool_name, tool_input, approved_perms):
        sys.exit(0)

    # Not approved - block and save pending permission
    ticket_id = os.environ.get('CODEHERO_TICKET_ID', '')
    if ticket_id:
        save_pending_permission(ticket_id, tool_name, tool_input)

    # Return block message
    description = get_tool_description(tool_name, tool_input)
    print(f"Permission required: {description}")
    sys.exit(2)

if __name__ == '__main__':
    main()
