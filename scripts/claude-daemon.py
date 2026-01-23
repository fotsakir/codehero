#!/usr/bin/env python3
"""
Claude Code Daemon v3 - Multi-worker with project isolation
- One worker per project (parallel between projects)
- Sequential execution within each project
- Runs as claude-worker user
- Restricted to project directories
"""

import subprocess
import time
import json
import os
import sys

# Add scripts directory to Python path for module imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import signal
import smtplib
import threading
import urllib.request
import urllib.error
import shutil
import zipfile
import tempfile
import select
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import mysql.connector
from mysql.connector import pooling

# Import Smart Context Manager
try:
    from smart_context import SmartContextManager
    SMART_CONTEXT_ENABLED = True
except ImportError:
    SMART_CONTEXT_ENABLED = False
    print("[WARNING] SmartContextManager not available - using basic context")

# Import Git Manager
try:
    from git_manager import GitManager, get_git_manager
    GIT_ENABLED = True
except ImportError:
    GIT_ENABLED = False
    GitManager = None
    get_git_manager = None
    print("[WARNING] GitManager not available - Git auto-commit disabled")

# Auto-review settings (uses Claude CLI with --model haiku)
AUTO_REVIEW_ENABLED = False
AUTO_REVIEW_DELAY_SECONDS = 10  # 10 seconds default

BACKUP_DIR = "/var/backups/codehero"
MAX_BACKUPS = 30

# Web app URL for broadcasting messages
WEB_APP_URL = "http://127.0.0.1:5000"

CONFIG_FILE = "/etc/codehero/system.conf"
PID_FILE = "/var/run/codehero/daemon.pid"
LOG_FILE = "/var/log/codehero/daemon.log"
GLOBAL_CONTEXT_FILE = "/etc/codehero/global-context.md"
STUCK_TIMEOUT_MINUTES = 30
POLL_INTERVAL = 3
MAX_PARALLEL_PROJECTS = 10

# Rate limit and retry cooldown settings (defaults, can be overridden in system.conf)
RATE_LIMIT_COOLDOWN_MINUTES = 30  # Wait time after hitting API rate limit
RETRY_COOLDOWN_MINUTES = 5        # Wait time between retries for other errors

# Telegram notification settings (loaded from config)
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""
NOTIFY_SETTINGS = {
    'ticket_completed': True,
    'awaiting_input': True,
    'ticket_failed': True,
    'watchdog_alert': True
}

def send_telegram(message, parse_mode="HTML"):
    """Send notification via Telegram bot"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = json.dumps({
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': parse_mode
        }).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as e:
        print(f"[WARNING] Telegram notification failed: {e}")
        return False

# Telegram polling for replies
TELEGRAM_LAST_UPDATE_ID = 0

def log_debug(message):
    """Write debug message to log file"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(f"[{timestamp}] [DEBUG] {message}\n")
    except: pass

def poll_telegram_replies():
    """Poll Telegram for new reply messages"""
    global TELEGRAM_LAST_UPDATE_ID
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return []

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        params = f"?offset={TELEGRAM_LAST_UPDATE_ID + 1}&timeout=5"
        req = urllib.request.Request(url + params)
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read().decode('utf-8'))

        replies = []
        if data.get('ok') and data.get('result'):
            for update in data['result']:
                TELEGRAM_LAST_UPDATE_ID = update['update_id']
                msg = update.get('message', {})
                msg_text = msg.get('text', '')

                # Debug: log received messages
                if msg_text:
                    log_debug(f"Telegram message received: {msg_text[:50]}...")

                # Check if it's a reply to one of our messages
                reply_to = msg.get('reply_to_message')
                if reply_to and msg_text:
                    # Extract ticket number from original message
                    original_text = reply_to.get('text', '')
                    log_debug(f"Reply to message: {original_text[:50]}...")
                    ticket_number = extract_ticket_from_message(original_text)
                    log_debug(f"Extracted ticket: {ticket_number}")
                    replies.append({
                        'ticket_number': ticket_number,  # May be None if not found
                        'message': msg_text,
                        'from': msg.get('from', {}).get('first_name', 'User'),
                        'is_reply': True
                    })
                elif msg_text and not reply_to:
                    log_debug(f"Not a reply - sending help message")
                    # Direct message - inform user to use reply
                    replies.append({
                        'ticket_number': None,
                        'message': msg_text,
                        'from': msg.get('from', {}).get('first_name', 'User'),
                        'is_reply': False
                    })
        return replies
    except Exception as e:
        log_debug(f"Telegram polling failed: {e}")
        return []

def extract_ticket_from_message(text):
    """Extract ticket number from notification message"""
    import re
    # Look for ticket number pattern: XXXX-0000 or XXX30-0000 (e.g., WEATHERAPP-0002, TEST30-0001)
    # Project code can be letters followed by optional numbers
    match = re.search(r'([A-Z]+\d*-\d+)', text)
    if match:
        return match.group(1)
    return None

def notify(event_type, title, message, project_name=None, ticket_number=None):
    """Send notification based on event type and settings"""
    if not NOTIFY_SETTINGS.get(event_type, False):
        return

    icons = {
        'ticket_completed': '✅',
        'awaiting_input': '⏳',
        'ticket_failed': '❌',
        'watchdog_alert': '⚠️'
    }
    icon = icons.get(event_type, '📢')

    text = f"{icon} <b>{title}</b>\n"
    if project_name:
        text += f"📁 Project: {project_name}\n"
    if ticket_number:
        text += f"🎫 Ticket: {ticket_number}\n"
    text += f"\n{message}"

    send_telegram(text)

class ProjectWorker(threading.Thread):
    """Worker thread for a specific project"""

    def __init__(self, daemon, project_id, project_name, work_path, global_context="", context_manager=None):
        super().__init__(daemon=True)
        self.daemon_ref = daemon
        self.project_id = project_id
        self.project_name = project_name
        self.work_path = work_path
        self.global_context = global_context
        self.context_manager = context_manager  # SmartContextManager instance
        self.running = True
        # Thread-local storage for parallel ticket execution
        self._thread_local = threading.local()
        self.last_activity = None
        # Token tracking - NOW THREAD-LOCAL (see properties below)
        # These are initialized per-thread in reset_token_tracking()
        # Permission denials (supervised mode) - also thread-local
        # Last task summary - also thread-local
        # Current running Claude process (for watchdog to kill if stuck)
        self.current_process = None
        self.current_process_lock = threading.Lock()

    # Thread-local properties for parallel execution safety
    @property
    def current_ticket_id(self):
        return getattr(self._thread_local, 'ticket_id', None)

    @current_ticket_id.setter
    def current_ticket_id(self, value):
        self._thread_local.ticket_id = value

    @property
    def current_session_id(self):
        return getattr(self._thread_local, 'session_id', None)

    @current_session_id.setter
    def current_session_id(self, value):
        self._thread_local.session_id = value

    # Thread-local token tracking properties (for parallel ticket safety)
    @property
    def session_start_time(self):
        return getattr(self._thread_local, 'session_start_time', None)

    @session_start_time.setter
    def session_start_time(self, value):
        self._thread_local.session_start_time = value

    @property
    def session_input_tokens(self):
        return getattr(self._thread_local, 'session_input_tokens', 0)

    @session_input_tokens.setter
    def session_input_tokens(self, value):
        self._thread_local.session_input_tokens = value

    @property
    def session_output_tokens(self):
        return getattr(self._thread_local, 'session_output_tokens', 0)

    @session_output_tokens.setter
    def session_output_tokens(self, value):
        self._thread_local.session_output_tokens = value

    @property
    def session_cache_read_tokens(self):
        return getattr(self._thread_local, 'session_cache_read_tokens', 0)

    @session_cache_read_tokens.setter
    def session_cache_read_tokens(self, value):
        self._thread_local.session_cache_read_tokens = value

    @property
    def session_cache_creation_tokens(self):
        return getattr(self._thread_local, 'session_cache_creation_tokens', 0)

    @session_cache_creation_tokens.setter
    def session_cache_creation_tokens(self, value):
        self._thread_local.session_cache_creation_tokens = value

    @property
    def session_api_calls(self):
        return getattr(self._thread_local, 'session_api_calls', 0)

    @session_api_calls.setter
    def session_api_calls(self, value):
        self._thread_local.session_api_calls = value

    @property
    def permission_denials(self):
        if not hasattr(self._thread_local, 'permission_denials'):
            self._thread_local.permission_denials = []
        return self._thread_local.permission_denials

    @permission_denials.setter
    def permission_denials(self, value):
        self._thread_local.permission_denials = value

    @property
    def last_summary(self):
        return getattr(self._thread_local, 'last_summary', None)

    @last_summary.setter
    def last_summary(self, value):
        self._thread_local.last_summary = value

    def log(self, message, level="INFO"):
        self.daemon_ref.log(f"[{self.project_name}] {message}", level)

    def kill_process(self):
        """Kill the current Claude process (called by watchdog)"""
        with self.current_process_lock:
            if self.current_process and self.current_process.poll() is None:
                self.log("Killing Claude process (watchdog)", "WARNING")
                try:
                    self.current_process.terminate()
                    self.current_process.wait(timeout=5)
                except:
                    try:
                        self.current_process.kill()
                    except:
                        pass
                return True
        return False

    def get_db(self):
        return self.daemon_ref.get_db()
    
    def broadcast_message(self, msg_data):
        """Send message to web app for WebSocket broadcast"""
        try:
            data = json.dumps({
                'type': 'message',
                'ticket_id': self.current_ticket_id,
                'message': msg_data
            }).encode('utf-8')
            req = urllib.request.Request(
                f"{WEB_APP_URL}/api/internal/broadcast",
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            urllib.request.urlopen(req, timeout=2)
        except Exception as e:
            self.log(f"Broadcast failed: {e}", "ERROR")

    def save_message(self, role, content, tool_name=None, tool_input=None, tokens=0):
        if not self.current_ticket_id:
            return
        try:
            # Use actual token count from API if provided, otherwise estimate
            if tokens > 0:
                # Actual count from Claude API response
                token_count = tokens
            elif content:
                # Estimate: ~4 chars per token for English/code
                token_count = len(content.encode('utf-8')) // 4
            elif tool_input:
                # For tool_use messages, estimate tokens from tool_input
                tool_input_str = json.dumps(tool_input) if isinstance(tool_input, dict) else str(tool_input)
                token_count = len(tool_input_str.encode('utf-8')) // 4
            else:
                token_count = 0

            conn = self.get_db()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO conversation_messages
                (ticket_id, session_id, role, content, tool_name, tool_input, tokens_used, token_count, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, (
                self.current_ticket_id,
                self.current_session_id,
                role,
                content[:50000] if content else None,
                tool_name,
                json.dumps(tool_input) if tool_input else None,
                tokens,
                token_count
            ))
            msg_id = cursor.lastrowid
            conn.commit()
            cursor.close()
            conn.close()
            self.last_activity = datetime.now()

            # Broadcast to web app for real-time updates
            self.broadcast_message({
                'id': msg_id,
                'ticket_id': self.current_ticket_id,
                'role': role,
                'content': content[:50000] if content else None,
                'tool_name': tool_name,
                'tool_input': json.dumps(tool_input) if tool_input else None,
                'created_at': datetime.now().isoformat() + 'Z'
            })
        except Exception as e:
            self.log(f"Error saving message: {e}", "ERROR")
    
    def save_log(self, log_type, message):
        if not self.current_session_id:
            return
        conn = None
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO execution_logs (session_id, log_type, message, created_at)
                VALUES (%s, %s, %s, NOW())
            """, (self.current_session_id, log_type, message[:10000]))
            conn.commit()
            cursor.close()
        except:
            pass
        finally:
            if conn:
                conn.close()
    
    def update_waiting_tickets(self):
        """Update tickets with completed deps but start_when_ready=FALSE to awaiting_input.
        Skip if user has already sent a message (meaning they want it to start)."""
        conn = None
        try:
            conn = self.get_db()
            cursor = conn.cursor(dictionary=True)
            # Find ticket IDs that need updating - exclude tickets with user messages
            cursor.execute("""
                SELECT t.id FROM tickets t
                WHERE t.project_id = %s
                  AND t.status = 'open'
                  AND t.start_when_ready = FALSE
                  AND EXISTS (
                      SELECT 1 FROM ticket_dependencies td WHERE td.ticket_id = t.id
                  )
                  AND NOT EXISTS (
                      -- Respects deps_include_awaiting per ticket
                      SELECT 1 FROM ticket_dependencies td
                      JOIN tickets dt ON dt.id = td.depends_on_ticket_id
                      WHERE td.ticket_id = t.id
                        AND NOT (
                            dt.status IN ('done', 'skipped')
                            -- Relaxed mode no longer treats awaiting_input as done
                            -- Auto-review will close ticket to 'done' after 15 minutes
                        )
                  )
                  AND NOT EXISTS (
                      SELECT 1 FROM user_messages um
                      WHERE um.ticket_id = t.id AND um.processed = FALSE
                  )
                  AND NOT EXISTS (
                      SELECT 1 FROM conversation_messages cm
                      WHERE cm.ticket_id = t.id AND cm.role = 'user'
                  )
            """, (self.project_id,))
            ticket_ids = [row['id'] for row in cursor.fetchall()]

            if ticket_ids:
                # Now update them
                cursor.execute(f"""
                    UPDATE tickets SET status = 'awaiting_input'
                    WHERE id IN ({','.join(map(str, ticket_ids))})
                """)
                conn.commit()
                self.log(f"Set {len(ticket_ids)} ticket(s) to awaiting_input (deps complete, start_when_ready=FALSE)")
            cursor.close()
        except Exception as e:
            self.log(f"Error updating waiting tickets: {e}", "ERROR")
        finally:
            if conn:
                conn.close()

    def get_next_ticket(self):
        """Get next ticket respecting: forced > sequence_order > priority > created_at
        Also skips tickets with unfinished dependencies."""
        # First, update any tickets that need to wait for user input
        self.update_waiting_tickets()

        try:
            conn = self.get_db()
            cursor = conn.cursor(dictionary=True)

            # Get all eligible tickets (open/new/pending, not blocked by dependencies)
            cursor.execute("""
                SELECT t.*, p.web_path, p.app_path, p.name as project_name, p.code as project_code,
                       p.project_type, p.tech_stack, p.context as project_context, t.context as ticket_context,
                       p.db_name, p.db_user, p.db_password, p.db_host,
                       p.ai_model as project_ai_model, t.ai_model as ticket_ai_model,
                       p.android_device_type, p.android_remote_host, p.android_remote_port, p.android_screen_size,
                       p.dotnet_port, p.default_test_command,
                       p.default_execution_mode, p.reference_path
                FROM tickets t
                JOIN projects p ON t.project_id = p.id
                WHERE t.project_id = %s
                  AND t.status IN ('open', 'new', 'pending')
                  AND (t.retry_after IS NULL OR t.retry_after <= NOW())  -- Skip if in cooldown
                  AND NOT EXISTS (
                      -- Skip if has unfinished dependencies
                      -- Dependencies must ALWAYS be 'done' or 'skipped' before proceeding
                      SELECT 1 FROM ticket_dependencies td
                      JOIN tickets dt ON dt.id = td.depends_on_ticket_id
                      WHERE td.ticket_id = t.id
                        AND dt.status NOT IN ('done', 'skipped')
                  )
                  AND (
                      -- Parent ticket must be done/skipped (parent = implicit dependency)
                      t.parent_ticket_id IS NULL
                      OR EXISTS (
                          SELECT 1 FROM tickets pt
                          WHERE pt.id = t.parent_ticket_id
                            AND pt.status IN ('done', 'skipped')
                      )
                  )
                ORDER BY
                    t.is_forced DESC,  -- Forced tickets first
                    CASE WHEN t.sequence_order IS NOT NULL THEN 0 ELSE 1 END,  -- Sequenced tickets before non-sequenced
                    t.sequence_order ASC,  -- By sequence order
                    CASE t.priority
                        WHEN 'critical' THEN 1 WHEN 'high' THEN 2
                        WHEN 'medium' THEN 3 WHEN 'low' THEN 4
                    END,
                    t.created_at ASC
                LIMIT 1
            """, (self.project_id,))
            ticket = cursor.fetchone()
            cursor.close()
            conn.close()
            return ticket
        except Exception as e:
            self.log(f"Error getting ticket: {e}", "ERROR")
            return None

    def get_pending_sub_tickets(self, parent_ticket_id):
        """Get unfinished sub-tickets for a parent ticket, ordered by sequence.
        Also respects dependencies - sub-tickets with unfinished deps are skipped."""
        try:
            conn = self.get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT t.*, p.web_path, p.app_path, p.name as project_name, p.code as project_code,
                       p.project_type, p.tech_stack, p.context as project_context, t.context as ticket_context,
                       p.db_name, p.db_user, p.db_password, p.db_host,
                       p.ai_model as project_ai_model, t.ai_model as ticket_ai_model,
                       p.default_test_command, p.reference_path
                FROM tickets t
                JOIN projects p ON t.project_id = p.id
                WHERE t.parent_ticket_id = %s
                  AND t.status NOT IN ('done', 'skipped', 'failed', 'awaiting_input')
                  AND (t.retry_after IS NULL OR t.retry_after <= NOW())  -- Skip if in cooldown
                  AND NOT EXISTS (
                      -- Respect dependencies for sub-tickets too
                      -- Dependencies must ALWAYS be 'done' or 'skipped'
                      SELECT 1 FROM ticket_dependencies td
                      JOIN tickets dt ON dt.id = td.depends_on_ticket_id
                      WHERE td.ticket_id = t.id
                        AND dt.status NOT IN ('done', 'skipped')
                  )
                ORDER BY
                    CASE WHEN t.sequence_order IS NOT NULL THEN 0 ELSE 1 END,
                    t.sequence_order ASC,
                    t.created_at ASC
            """, (parent_ticket_id,))
            sub_tickets = cursor.fetchall()
            cursor.close()
            conn.close()
            return sub_tickets
        except Exception as e:
            self.log(f"Error getting sub-tickets: {e}", "ERROR")
            return []

    def all_sub_tickets_done(self, parent_ticket_id):
        """Check if all sub-tickets of a parent are completed.
        Only 'done' and 'skipped' count as completed (awaiting_input waits for auto-review)."""
        conn = None
        try:
            conn = self.get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT COUNT(*) as pending FROM tickets
                WHERE parent_ticket_id = %s
                  AND status NOT IN ('done', 'skipped')
            """, (parent_ticket_id,))
            result = cursor.fetchone()
            cursor.close()
            return result['pending'] == 0
        except:
            return True
        finally:
            if conn:
                conn.close()

    def get_conversation_history(self, ticket_id):
        # Use smart history if context manager is available
        if self.context_manager:
            try:
                return self.context_manager.get_smart_history(ticket_id)
            except Exception as e:
                self.log(f"Smart history failed, falling back to basic: {e}", "WARNING")

        # Fallback to basic history
        conn = None
        try:
            conn = self.get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT role, content, tool_name, tool_input FROM conversation_messages
                WHERE ticket_id = %s ORDER BY created_at ASC
            """, (ticket_id,))
            messages = cursor.fetchall()
            cursor.close()
            return messages
        except:
            return []
        finally:
            if conn:
                conn.close()

    def get_pending_user_messages(self, ticket_id):
        conn = None
        try:
            conn = self.get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM user_messages
                WHERE ticket_id = %s AND processed = FALSE
                ORDER BY created_at ASC
            """, (ticket_id,))
            messages = cursor.fetchall()
            if messages:
                ids = [m['id'] for m in messages]
                cursor.execute(f"UPDATE user_messages SET processed = TRUE WHERE id IN ({','.join(map(str, ids))})")
                conn.commit()
            cursor.close()
            return messages
        except:
            return []
        finally:
            if conn:
                conn.close()
    
    def generate_summary_with_haiku(self, ticket_id):
        """Generate a brief summary of the ticket using Haiku"""
        if not AUTO_REVIEW_ENABLED:
            return None

        try:
            conn = self.get_db()
            cursor = conn.cursor(dictionary=True)

            # Get ticket info
            cursor.execute("SELECT title, description FROM tickets WHERE id = %s", (ticket_id,))
            ticket = cursor.fetchone()

            # Get last 50 messages from conversation
            cursor.execute("""
                SELECT role, content FROM conversation_messages
                WHERE ticket_id = %s AND role IN ('user', 'assistant')
                ORDER BY created_at DESC LIMIT 50
            """, (ticket_id,))
            messages = cursor.fetchall()
            cursor.close()
            conn.close()

            if not messages:
                return None

            # Build conversation for Haiku (truncate each message to fit context)
            conversation = []
            for msg in reversed(messages):
                role = msg['role'].upper()
                content = (msg['content'] or '')[:500]  # Shorter per message since we have more
                conversation.append(f"[{role}]: {content}")

            # Use all messages but limit total size
            conv_text = chr(10).join(conversation)
            if len(conv_text) > 15000:
                conv_text = conv_text[-15000:]  # Keep last 15k chars

            prompt = f"""Analyze this completed task and provide a brief summary.

TASK: {ticket['title'] if ticket else 'Unknown'}
DESCRIPTION: {(ticket['description'] or '')[:500] if ticket else ''}

CONVERSATION (last 50 messages):
{conv_text}

Provide a 1-2 sentence summary of what was accomplished. Be specific about files created/modified and features implemented. Just the summary text, no labels or prefixes."""

            result = subprocess.run(
                ['/home/claude/.local/bin/claude', '--model', 'haiku', '--print'],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=30,
                cwd='/tmp'
            )

            if result.returncode == 0 and result.stdout:
                summary = result.stdout.strip()
                # Clean up - remove any prefixes Haiku might add
                for prefix in ['Summary:', 'SUMMARY:', 'Result:', 'Accomplished:']:
                    if summary.startswith(prefix):
                        summary = summary[len(prefix):].strip()
                self.log(f"Haiku summary generated for ticket {ticket_id}")
                return summary[:500]  # Limit length
            else:
                self.log(f"Haiku summary failed: {result.stderr[:100] if result.stderr else 'no output'}", "WARNING")
                return None

        except subprocess.TimeoutExpired:
            self.log(f"Haiku summary timeout for ticket {ticket_id}", "WARNING")
            return None
        except Exception as e:
            self.log(f"Haiku summary error: {e}", "WARNING")
            return None

    def get_ancestor_summaries(self, cursor, parent_ticket_id):
        """Get combined summaries from all ancestors (recursive)"""
        if not parent_ticket_id:
            return ""

        ancestors = []
        current_parent_id = parent_ticket_id
        max_depth = 10

        while current_parent_id and len(ancestors) < max_depth:
            cursor.execute("""
                SELECT id, parent_ticket_id, ticket_number, title, result_summary
                FROM tickets WHERE id = %s
            """, (current_parent_id,))
            parent = cursor.fetchone()
            if parent:
                ancestors.append(parent)
                current_parent_id = parent.get('parent_ticket_id')
            else:
                break

        if not ancestors:
            return ""

        # Reverse to show from oldest to most recent
        ancestors.reverse()

        summary_parts = []
        for ancestor in ancestors:
            if ancestor.get('result_summary'):
                summary_parts.append(f"[{ancestor['ticket_number']}] {ancestor['result_summary']}")

        if summary_parts:
            return "=== Ancestor Summary ===\n" + "\n".join(summary_parts) + "\n========================\n"
        return ""

    def update_ticket(self, ticket_id, status, result=None):
        try:
            conn = self.get_db()
            cursor = conn.cursor(dictionary=True)

            # Get ticket info for notification (including current status and retry info)
            cursor.execute("""
                SELECT t.ticket_number, t.title, t.status as current_status, p.name as project_name,
                       t.retry_count, t.max_retries, t.is_forced, t.test_command, t.require_tests_pass,
                       t.parent_ticket_id
                FROM tickets t JOIN projects p ON t.project_id = p.id
                WHERE t.id = %s
            """, (ticket_id,))
            ticket_info = cursor.fetchone()

            # Build combined summary with ancestors (for sub-tickets)
            combined_result = result
            if result and ticket_info and ticket_info.get('parent_ticket_id'):
                ancestor_summary = self.get_ancestor_summaries(cursor, ticket_info['parent_ticket_id'])
                if ancestor_summary:
                    combined_result = ancestor_summary + result

            # If trying to set 'failed' but ticket is already 'awaiting_input' (from /stop command),
            # don't overwrite - the user intentionally paused it
            if status == 'failed' and ticket_info and ticket_info.get('current_status') == 'awaiting_input':
                self.log(f"Ticket {ticket_id} already awaiting_input (user paused), not marking as failed", "DEBUG")
                cursor.close()
                conn.close()
                return

            # Handle rate limit - wait 30 minutes, don't count as failure
            if status == 'rate_limited' and ticket_info:
                cursor.execute("""
                    UPDATE tickets SET status = 'open',
                    retry_after = DATE_ADD(NOW(), INTERVAL %s MINUTE),
                    result_summary = %s, updated_at = NOW()
                    WHERE id = %s
                """, (RATE_LIMIT_COOLDOWN_MINUTES,
                      f"Rate limited - will retry after {RATE_LIMIT_COOLDOWN_MINUTES} minutes",
                      ticket_id))
                conn.commit()
                self.log(f"⏳ Rate limit cooldown set for ticket {ticket_info.get('ticket_number', ticket_id)}")
                cursor.close()
                conn.close()
                return  # Will be picked up after cooldown

            # Handle retry logic for failed tickets
            if status == 'failed' and ticket_info:
                retry_count = ticket_info.get('retry_count') or 0
                max_retries = ticket_info.get('max_retries') or 3

                if retry_count < max_retries:
                    # Increment retry count and set cooldown before retry
                    new_retry_count = retry_count + 1
                    cursor.execute("""
                        UPDATE tickets SET status = 'open', retry_count = %s,
                        retry_after = DATE_ADD(NOW(), INTERVAL %s MINUTE),
                        result_summary = %s, updated_at = NOW()
                        WHERE id = %s
                    """, (new_retry_count, RETRY_COOLDOWN_MINUTES,
                          f"Retry {new_retry_count}/{max_retries}: {result[:500] if result else 'Unknown error'}",
                          ticket_id))
                    conn.commit()
                    self.log(f"Retry {new_retry_count}/{max_retries} for ticket {ticket_info.get('ticket_number', ticket_id)} (cooldown {RETRY_COOLDOWN_MINUTES} min)")
                    cursor.close()
                    conn.close()
                    return  # Will be picked up after cooldown

            actual_status = status
            reset_forced = False

            if status == 'done':
                # Set to awaiting_input instead of done - user must respond or close
                # Summary will be generated when ticket is actually closed
                actual_status = 'awaiting_input'
                reset_forced = ticket_info.get('is_forced', False)

                # Schedule auto-review after configured delay
                cursor.execute(f"""
                    UPDATE tickets SET status = 'awaiting_input',
                    review_deadline = DATE_ADD(NOW(), INTERVAL 7 DAY),
                    review_scheduled_at = DATE_ADD(NOW(), INTERVAL {AUTO_REVIEW_DELAY_SECONDS} SECOND),
                    updated_at = NOW(),
                    is_forced = FALSE, retry_count = 0, retry_after = NULL
                    WHERE id = %s
                """, (ticket_id,))
            elif status == 'failed':
                # Already past max retries if we get here
                reset_forced = ticket_info.get('is_forced', False)
                cursor.execute("""
                    UPDATE tickets SET status = %s, result_summary = %s, updated_at = NOW(),
                    is_forced = FALSE, retry_after = NULL
                    WHERE id = %s
                """, (status, result[:1000] if result else None, ticket_id))
            else:
                cursor.execute("""
                    UPDATE tickets SET status = %s, result_summary = %s, updated_at = NOW(), retry_after = NULL
                    WHERE id = %s
                """, (status, result[:1000] if result else None, ticket_id))
            conn.commit()

            # Git auto-commit when ticket completes (awaiting_input)
            if actual_status == 'awaiting_input' and GIT_ENABLED:
                try:
                    # Get project info for Git
                    cursor.execute("""
                        SELECT p.id, p.web_path, p.app_path, p.project_type, p.tech_stack,
                               t.ticket_number, t.title,
                               COALESCE(
                                   (SELECT SUM(es.tokens_used) FROM execution_sessions es WHERE es.ticket_id = t.id),
                                   0
                               ) as tokens_used,
                               COALESCE(
                                   (SELECT TIMESTAMPDIFF(SECOND, MIN(es2.started_at), MAX(es2.ended_at))
                                    FROM execution_sessions es2 WHERE es2.ticket_id = t.id),
                                   0
                               ) as duration_seconds
                        FROM tickets t
                        JOIN projects p ON t.project_id = p.id
                        WHERE t.id = %s
                    """, (ticket_id,))
                    project_info = cursor.fetchone()

                    if project_info:
                        # Determine repo path (prefer web_path, fallback to app_path)
                        git_path = project_info.get('web_path') or project_info.get('app_path')

                        if git_path and os.path.exists(git_path):
                            gm = GitManager(
                                git_path,
                                project_info.get('project_type', 'web'),
                                project_info.get('tech_stack', '')
                            )

                            if gm.is_initialized():
                                success, msg, commit_hash = gm.auto_commit(
                                    ticket_number=project_info.get('ticket_number', ''),
                                    title=project_info.get('title', 'Automated commit'),
                                    session_id=self.current_session_id,
                                    status=actual_status,
                                    duration_seconds=project_info.get('duration_seconds', 0),
                                    tokens_used=project_info.get('tokens_used', 0)
                                )

                                if success and commit_hash:
                                    # Get or create repo record
                                    cursor.execute("""
                                        SELECT id FROM project_git_repos
                                        WHERE project_id = %s AND repo_path = %s
                                    """, (project_info['id'], git_path))
                                    repo_record = cursor.fetchone()

                                    if not repo_record:
                                        # Create repo record if missing
                                        cursor.execute("""
                                            INSERT INTO project_git_repos
                                            (project_id, repo_path, path_type, status)
                                            VALUES (%s, %s, 'web', 'active')
                                        """, (project_info['id'], git_path))
                                        conn.commit()
                                        repo_id = cursor.lastrowid
                                    else:
                                        repo_id = repo_record['id']

                                    # Get commit stats
                                    commit_detail = gm.get_commit_detail(commit_hash)
                                    files_changed = commit_detail.get('files_changed', 0) if commit_detail else 0
                                    insertions = commit_detail.get('insertions', 0) if commit_detail else 0
                                    deletions = commit_detail.get('deletions', 0) if commit_detail else 0

                                    # Store commit in database
                                    cursor.execute("""
                                        INSERT INTO project_git_commits
                                        (project_id, repo_id, ticket_id, session_id, commit_hash, short_hash,
                                         message, files_changed, insertions, deletions)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    """, (
                                        project_info['id'], repo_id, ticket_id, self.current_session_id,
                                        commit_hash, commit_hash[:7],
                                        f"[{project_info.get('ticket_number', '')}] {project_info.get('title', '')}",
                                        files_changed, insertions, deletions
                                    ))

                                    # Update repo stats
                                    cursor.execute("""
                                        UPDATE project_git_repos
                                        SET last_commit_hash = %s, last_commit_at = NOW(),
                                            total_commits = total_commits + 1
                                        WHERE id = %s
                                    """, (commit_hash, repo_id))
                                    conn.commit()

                                    self.log(f"Git auto-commit created: {commit_hash[:7]}", "INFO")
                                elif not success:
                                    self.log(f"Git auto-commit skipped: {msg}", "DEBUG")
                except Exception as e:
                    self.log(f"Git auto-commit error: {e}", "WARNING")

            cursor.close()
            conn.close()

            # Broadcast status change to web UI
            self.broadcast_status(ticket_id, actual_status)

            # Send Telegram notification (protected)
            try:
                if ticket_info:
                    if actual_status == 'awaiting_input':
                        notify('awaiting_input', 'Task Completed - Awaiting Review',
                               ticket_info.get('title', ''),
                               ticket_info.get('project_name'), ticket_info.get('ticket_number'))
                    elif actual_status == 'failed':
                        notify('ticket_failed', 'Task Failed',
                               result or ticket_info.get('title', ''),
                               ticket_info.get('project_name'), ticket_info.get('ticket_number'))
            except:
                pass  # Notification failure should not affect ticket processing
        except Exception as e:
            self.log(f"Error updating ticket: {e}", "ERROR")

    def broadcast_status(self, ticket_id, status, pending_permission=None):
        """Broadcast ticket status change to web app"""
        try:
            payload = {
                'type': 'status',
                'ticket_id': ticket_id,
                'status': status
            }
            if pending_permission:
                payload['pending_permission'] = pending_permission
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                f"{WEB_APP_URL}/api/internal/broadcast",
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            urllib.request.urlopen(req, timeout=2)
        except Exception as e:
            pass  # Silent fail - not critical

    def create_backup(self, ticket_id, trigger='auto'):
        """Create automatic backup. Trigger can be: auto, close, reopen"""
        try:
            conn = self.get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT p.* FROM projects p
                JOIN tickets t ON t.project_id = p.id
                WHERE t.id = %s
            """, (ticket_id,))
            project = cursor.fetchone()
            cursor.close()
            conn.close()

            if not project:
                self.log("Could not find project for backup", "WARNING")
                return

            project_code = project['code']
            backup_subdir = os.path.join(BACKUP_DIR, project_code)
            os.makedirs(backup_subdir, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"{project_code}_{timestamp}_{trigger}.zip"
            backup_path = os.path.join(backup_subdir, backup_name)

            temp_dir = tempfile.mkdtemp()
            temp_backup = os.path.join(temp_dir, 'backup')
            os.makedirs(temp_backup)

            try:
                # Copy web folder
                if project.get('web_path') and os.path.exists(project['web_path']):
                    shutil.copytree(project['web_path'], os.path.join(temp_backup, 'web'), dirs_exist_ok=True)

                # Copy app folder
                if project.get('app_path') and os.path.exists(project['app_path']):
                    shutil.copytree(project['app_path'], os.path.join(temp_backup, 'app'), dirs_exist_ok=True)

                # Export database
                if project.get('db_name') and project.get('db_user') and project.get('db_password'):
                    db_dir = os.path.join(temp_backup, 'database')
                    os.makedirs(db_dir, exist_ok=True)

                    db_host = project.get('db_host', 'localhost')
                    db_name = project['db_name']
                    db_user = project['db_user']
                    db_pass = project['db_password']

                    # Schema
                    schema_cmd = f"mysqldump -h {db_host} -u {db_user} -p'{db_pass}' --no-data {db_name} 2>/dev/null"
                    result = subprocess.run(schema_cmd, shell=True, capture_output=True, text=True)
                    if result.returncode == 0:
                        with open(os.path.join(db_dir, 'schema.sql'), 'w') as f:
                            f.write(result.stdout)

                    # Data
                    data_cmd = f"mysqldump -h {db_host} -u {db_user} -p'{db_pass}' --no-create-info {db_name} 2>/dev/null"
                    result = subprocess.run(data_cmd, shell=True, capture_output=True, text=True)
                    if result.returncode == 0:
                        with open(os.path.join(db_dir, 'data.sql'), 'w') as f:
                            f.write(result.stdout)

                # Create zip
                with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(temp_backup):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arc_name = os.path.relpath(file_path, temp_backup)
                            zipf.write(file_path, arc_name)

                # Cleanup old backups
                backups = sorted(
                    [f for f in os.listdir(backup_subdir) if f.endswith('.zip')],
                    key=lambda x: os.path.getmtime(os.path.join(backup_subdir, x)),
                    reverse=True
                )
                for old_backup in backups[MAX_BACKUPS:]:
                    os.remove(os.path.join(backup_subdir, old_backup))

                self.log(f"Backup created: {backup_name}")
                self.save_log('info', f'Auto-backup created: {backup_name}')

                # Notify user in UI
                self.broadcast_message({
                    'role': 'system',
                    'content': f'📦 Backup created: {backup_name}',
                    'created_at': datetime.now().isoformat(),
                    'ticket_id': ticket_id
                })

            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        except Exception as e:
            self.log(f"Backup error: {e}", "WARNING")

    def reset_token_tracking(self):
        """Reset token counters for a new session"""
        self.session_start_time = datetime.now()
        self.session_input_tokens = 0
        self.session_output_tokens = 0
        self.session_cache_read_tokens = 0
        self.session_cache_creation_tokens = 0
        self.session_api_calls = 0
        self.permission_denials = []

    def save_usage_stats(self):
        """Save usage statistics to database"""
        if not self.current_ticket_id or not self.session_start_time:
            return

        try:
            # Calculate duration
            duration = int((datetime.now() - self.session_start_time).total_seconds())
            total_tokens = self.session_input_tokens + self.session_output_tokens

            conn = self.get_db()
            cursor = conn.cursor()

            # Insert usage record
            cursor.execute("""
                INSERT INTO usage_stats
                (ticket_id, project_id, session_id, input_tokens, output_tokens, total_tokens,
                 cache_read_tokens, cache_creation_tokens, duration_seconds, api_calls)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                self.current_ticket_id,
                self.project_id,
                self.current_session_id,
                self.session_input_tokens,
                self.session_output_tokens,
                total_tokens,
                self.session_cache_read_tokens,
                self.session_cache_creation_tokens,
                duration,
                self.session_api_calls
            ))

            # Note: Ticket totals are updated in real-time by update_session_tokens()
            # Only update project totals here (cumulative)

            # Update project totals
            cursor.execute("""
                UPDATE projects
                SET total_tokens = total_tokens + %s,
                    total_duration_seconds = total_duration_seconds + %s
                WHERE id = %s
            """, (total_tokens, duration, self.project_id))

            conn.commit()
            cursor.close()
            conn.close()

            self.log(f"Usage: {total_tokens:,} tokens, {duration}s, {self.session_api_calls} API calls")

        except Exception as e:
            self.log(f"Error saving usage stats: {e}", "ERROR")

    def create_session(self, ticket_id):
        try:
            self.reset_token_tracking()
            conn = self.get_db()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO execution_sessions (ticket_id, status, started_at)
                VALUES (%s, 'running', NOW())
            """, (ticket_id,))
            session_id = cursor.lastrowid
            conn.commit()
            cursor.close()
            conn.close()
            return session_id
        except Exception as e:
            self.log(f"Error creating session: {e}", "ERROR")
            return None
    
    def update_session_tokens(self):
        """Update session and ticket tokens in real-time (called after each API response)"""
        if not self.current_session_id or not self.current_ticket_id:
            return
        try:
            total_tokens = self.session_input_tokens + self.session_output_tokens
            duration = int((datetime.now() - self.session_start_time).total_seconds()) if self.session_start_time else 0

            conn = self.get_db()
            cursor = conn.cursor()

            # Update session
            cursor.execute("""
                UPDATE execution_sessions
                SET tokens_used = %s, api_calls = %s
                WHERE id = %s
            """, (total_tokens, self.session_api_calls, self.current_session_id))

            # Update ticket totals in real-time
            cursor.execute("""
                UPDATE tickets
                SET total_tokens = (
                    SELECT COALESCE(SUM(tokens_used), 0)
                    FROM execution_sessions
                    WHERE ticket_id = %s
                ),
                total_duration_seconds = (
                    SELECT COALESCE(SUM(TIMESTAMPDIFF(SECOND, started_at, IFNULL(ended_at, NOW()))), 0)
                    FROM execution_sessions
                    WHERE ticket_id = %s
                )
                WHERE id = %s
            """, (self.current_ticket_id, self.current_ticket_id, self.current_ticket_id))

            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            pass  # Don't log errors for real-time updates to avoid spam

    def end_session(self, session_id, status, tokens=0):
        # Save usage stats before ending session
        self.save_usage_stats()

        try:
            # Use the total tokens we tracked
            total_tokens = self.session_input_tokens + self.session_output_tokens
            conn = self.get_db()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE execution_sessions SET status = %s, ended_at = NOW(), tokens_used = %s
                WHERE id = %s
            """, (status, total_tokens, session_id))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            self.log(f"Error ending session: {e}", "ERROR")
    
    def build_prompt(self, ticket, history):
        # Determine working paths
        paths_info = []
        if ticket.get('web_path'):
            paths_info.append(f"Web path: {ticket['web_path']}")
        if ticket.get('app_path'):
            paths_info.append(f"App path: {ticket['app_path']}")
        paths_str = "\n".join(paths_info) if paths_info else "No paths configured"

        # Build tech info
        tech_info = ""
        if ticket.get('tech_stack'):
            tech_info = f"\nTech Stack: {ticket.get('tech_stack')}"
        if ticket.get('project_type'):
            tech_info += f"\nProject Type: {ticket.get('project_type')}"

        # Global context (server environment, installed tools, etc)
        global_context_str = ""
        if self.global_context:
            global_context_str = f"""
=== SERVER ENVIRONMENT ===
{self.global_context}
==========================
"""

        # Smart context from context manager (user prefs, project map, knowledge, extraction)
        smart_context_str = ""
        if self.context_manager:
            try:
                # Refresh tree structure before building context (fast, ~20-60ms)
                self.context_manager.refresh_project_tree(
                    ticket.get('project_id'),
                    web_path=ticket.get('web_path'),
                    app_path=ticket.get('app_path'),
                    reference_path=ticket.get('reference_path')
                )

                smart_ctx = self.context_manager.build_full_context(ticket)
                if smart_ctx.get('system_context'):
                    smart_context_str = smart_ctx['system_context']
            except Exception as e:
                self.log(f"Error building smart context: {e}", "WARNING")

        # Project database credentials (auto-created)
        db_info = ""
        if ticket.get('db_name') and ticket.get('db_user'):
            db_info = f"""
=== PROJECT DATABASE ===
Host: {ticket.get('db_host', 'localhost')}
Database: {ticket['db_name']}
Username: {ticket['db_user']}
Password: {ticket['db_password']}
========================
"""

        # Project context (databases, APIs, credentials, etc)
        project_context = ""
        if ticket.get('project_context'):
            project_context = f"""
=== PROJECT CONTEXT ===
{ticket['project_context']}
=======================
"""

        # Ticket-specific context
        ticket_context = ""
        if ticket.get('ticket_context'):
            ticket_context = f"""
=== TICKET CONTEXT ===
{ticket['ticket_context']}
======================
"""

        # Parent ticket context (for sub-tickets) - recursive to get all ancestors
        parent_context = ""
        if ticket.get('parent_ticket_id'):
            try:
                conn = self.get_db()
                cursor = conn.cursor(dictionary=True)

                # Get all ancestors recursively (grandparent → parent → current)
                ancestors = []
                current_parent_id = ticket['parent_ticket_id']
                max_depth = 10  # Prevent infinite loops

                while current_parent_id and len(ancestors) < max_depth:
                    cursor.execute("""
                        SELECT id, parent_ticket_id, ticket_number, title, description, result_summary
                        FROM tickets WHERE id = %s
                    """, (current_parent_id,))
                    parent = cursor.fetchone()
                    if parent:
                        ancestors.append(parent)
                        current_parent_id = parent.get('parent_ticket_id')
                    else:
                        break

                cursor.close()
                conn.close()

                if ancestors:
                    # Reverse to show from oldest ancestor to immediate parent
                    ancestors.reverse()
                    parent_info = ""
                    for i, ancestor in enumerate(ancestors):
                        level = "Root" if i == 0 else f"Level {i}"
                        parent_info += f"[{level}] {ancestor['ticket_number']} - {ancestor['title']}\n"
                        parent_info += f"  Description: {ancestor['description']}\n"
                        if ancestor.get('result_summary'):
                            parent_info += f"  Result: {ancestor['result_summary']}\n"
                        parent_info += "\n"

                    parent_context = f"""
=== PARENT TICKET CONTEXT ({len(ancestors)} level{'s' if len(ancestors) > 1 else ''}) ===
{parent_info}
This is a sub-task. Use the parent context to understand the overall goal.
{'=' * 50}
"""
            except Exception as e:
                self.log(f"Error getting parent context: {e}", "DEBUG")

        # Git version control context
        git_context = ""
        if GIT_ENABLED:
            try:
                git_path = ticket.get('web_path') or ticket.get('app_path')
                if git_path and os.path.exists(git_path):
                    gm = GitManager(
                        git_path,
                        ticket.get('project_type', 'web'),
                        ticket.get('tech_stack', '')
                    )
                    if gm.is_initialized():
                        git_info = gm.get_context_for_claude(max_commits=5)
                        if git_info:
                            git_context = f"""
=== GIT VERSION CONTROL ===
{git_info}
===========================
"""
            except Exception as e:
                self.log(f"Error getting Git context: {e}", "DEBUG")

        # Reference project context (imported templates)
        reference_context = ""
        if ticket.get('reference_path') and os.path.exists(ticket.get('reference_path', '')):
            reference_context = f"""
=== REFERENCE PROJECT ===
A reference project has been imported for this project.
Location: {ticket['reference_path']}
Use this as a template/reference when building features.
You can READ from this path to understand patterns and structure.
Do NOT modify files in the reference path - only use it for reference.
=========================
"""

        # Allowed paths
        allowed_paths = []
        if ticket.get('web_path'): allowed_paths.append(ticket['web_path'])
        if ticket.get('app_path'): allowed_paths.append(ticket['app_path'])
        allowed_str = " and ".join(allowed_paths) if allowed_paths else "/var/www/projects"

        # Allow reading reference path but not writing
        read_paths = list(allowed_paths)
        if ticket.get('reference_path') and os.path.exists(ticket.get('reference_path', '')):
            read_paths.append(f"{ticket['reference_path']} (read-only reference)")

        system = f"""You are working on project: {ticket['project_name']}
{paths_str}{tech_info}
{global_context_str}{smart_context_str}{db_info}{project_context}{ticket_context}{parent_context}{git_context}{reference_context}
Ticket: {ticket['ticket_number']} - {ticket['title']}

IMPORTANT: You can ONLY create/modify files within: {allowed_str}
Do NOT attempt to modify system files or files outside these directories.

Description:
{ticket['description']}

Complete this task. When finished, say "TASK COMPLETED" with a summary."""

        prompt_parts = [system, "\n--- Conversation History ---\n"]

        for msg in history:
            if msg['role'] == 'user':
                prompt_parts.append(f"\nUser: {msg['content']}")
            elif msg['role'] == 'assistant':
                prompt_parts.append(f"\nAssistant: {msg['content']}")
            elif msg['role'] == 'tool_use':
                prompt_parts.append(f"\n[Used tool: {msg['tool_name']}]")
            elif msg['role'] == 'tool_result':
                result = msg['content'] or ''
                prompt_parts.append(f"\n[Result: {result[:200]}...]" if len(result) > 200 else f"\n[Result: {result}]")

        prompt_parts.append("\n\nContinue working on this task:")
        return '\n'.join(prompt_parts)
    
    def parse_claude_output(self, line):
        try:
            data = json.loads(line)
            msg_type = data.get('type', '')

            if msg_type == 'assistant':
                # Extract usage data from the message (incremental in streaming)
                usage = data.get('message', {}).get('usage', {})
                self.session_api_calls += 1

                # Accumulate incremental token counts for real-time tracking
                if usage:
                    self.session_input_tokens += usage.get('input_tokens', 0)
                    self.session_output_tokens += usage.get('output_tokens', 0)
                    self.session_cache_read_tokens += usage.get('cache_read_input_tokens', 0)
                    self.session_cache_creation_tokens += usage.get('cache_creation_input_tokens', 0)
                    # Update session in real-time
                    self.update_session_tokens()

                content = ''
                for block in data.get('message', {}).get('content', []):
                    if block.get('type') == 'text':
                        content += block.get('text', '')
                    elif block.get('type') == 'tool_use':
                        self.save_message('tool_use', None,
                                        tool_name=block.get('name'),
                                        tool_input=block.get('input'))
                        self.save_log('output', f"🔧 Tool: {block.get('name')}")

                if content:
                    # Estimate tokens from content (streaming usage is incremental, not total)
                    self.save_message('assistant', content)  # Uses len/4 estimation
                    preview = content[:200] + '...' if len(content) > 200 else content
                    self.save_log('output', preview)

                    if 'TASK COMPLETED' in content.upper():
                        # Extract summary after "TASK COMPLETED"
                        upper_content = content.upper()
                        idx = upper_content.find('TASK COMPLETED')
                        if idx != -1:
                            # Get the text after "TASK COMPLETED" as summary
                            summary_text = content[idx + len('TASK COMPLETED'):].strip()
                            # Clean up common prefixes
                            for prefix in [':', '-', '.', '\n']:
                                if summary_text.startswith(prefix):
                                    summary_text = summary_text[1:].strip()
                            self.last_summary = summary_text[:1000] if summary_text else "Completed successfully"
                        else:
                            self.last_summary = "Completed successfully"
                        return 'completed'

            elif msg_type == 'result':
                # Result message has the correct TOTAL usage for the session
                result_usage = data.get('usage', {})
                if result_usage:
                    self.session_input_tokens = result_usage.get('input_tokens', 0)
                    self.session_output_tokens = result_usage.get('output_tokens', 0)
                    self.session_cache_read_tokens = result_usage.get('cache_read_input_tokens', 0)
                    self.session_cache_creation_tokens = result_usage.get('cache_creation_input_tokens', 0)
                    # Final update with correct totals
                    self.update_session_tokens()
                result = data.get('result', '')
                if isinstance(result, dict):
                    result = json.dumps(result)
                self.save_message('tool_result', str(result)[:5000])

                # Check for permission denials (supervised mode)
                permission_denials = data.get('permission_denials', [])
                if permission_denials:
                    self.permission_denials = permission_denials
                    self.log(f"Permission denials captured: {len(permission_denials)} denial(s)", "INFO")

            elif msg_type == 'error':
                error = data.get('error', {}).get('message', 'Unknown error')
                error_type = data.get('error', {}).get('type', '')
                self.save_message('system', f"Error: {error}")
                self.save_log('error', error)

                # Detect rate limit and overload errors
                error_lower = error.lower()
                is_rate_limit = (
                    error_type == 'rate_limit_error' or
                    'rate_limit' in error_lower or
                    'rate limit' in error_lower or
                    '429' in error or
                    'overloaded' in error_lower or
                    'capacity' in error_lower or
                    ('exceeded' in error_lower and 'limit' in error_lower)
                )
                if is_rate_limit:
                    self.log(f"⏳ Rate limit detected: {error}", "WARNING")
                    return 'rate_limited'

        except json.JSONDecodeError:
            if line.strip():
                self.save_log('output', line.strip())

        return None

    def check_pending_permission(self, ticket_id):
        """Check if there's a pending permission request"""
        pending_file = f"/var/run/codehero/pending_{ticket_id}.json"
        if os.path.exists(pending_file):
            try:
                with open(pending_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return None

    def clear_pending_permission(self, ticket_id):
        """Clear the pending permission file"""
        pending_file = f"/var/run/codehero/pending_{ticket_id}.json"
        try:
            if os.path.exists(pending_file):
                os.remove(pending_file)
        except:
            pass

    def save_pending_permission_to_db(self, ticket_id, pending):
        """Save pending permission to database for user review"""
        try:
            db = self.get_db()
            cursor = db.cursor()
            cursor.execute(
                "UPDATE tickets SET pending_permission = %s, status = 'awaiting_input' WHERE id = %s",
                (json.dumps(pending), ticket_id)
            )
            db.commit()
            cursor.close()
            # Broadcast status change with pending permission for real-time UI update
            self.broadcast_status(ticket_id, 'awaiting_input', pending)
            return True
        except Exception as e:
            self.log(f"Error saving pending permission: {e}", "ERROR")
            return False

    def create_semi_autonomous_settings(self, project_path):
        """Create .claude/settings.json for semi-autonomous mode with hooks"""
        try:
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

            self.log(f"Created semi-autonomous settings at {settings_file}")
            return settings_file
        except Exception as e:
            self.log(f"Error creating semi-autonomous settings: {e}", "ERROR")
            return None

    def run_claude(self, ticket, prompt):
        """Run Claude Code within project directory"""

        # Determine working directory based on project type
        project_type = ticket.get('project_type', 'web')
        mobile_types = ['capacitor', 'react_native', 'flutter', 'native_android', 'app', 'api', 'dotnet']

        if project_type in mobile_types:
            # For mobile/app projects, prefer app_path
            work_path = ticket.get('app_path') or ticket.get('web_path') or '/opt/apps'
        else:
            # For web projects, prefer web_path
            work_path = ticket.get('web_path') or ticket.get('app_path') or '/var/www/projects'
        work_path = os.path.abspath(work_path)

        # Create directories if needed
        if ticket.get('web_path'):
            os.makedirs(ticket['web_path'], exist_ok=True)
        if ticket.get('app_path'):
            os.makedirs(ticket['app_path'], exist_ok=True)

        # Determine AI model: ticket override > project default > sonnet
        ai_model = ticket.get('ticket_ai_model') or ticket.get('project_ai_model') or 'sonnet'
        self.log(f"Using AI model: {ai_model}")

        # Check execution mode: autonomous (default), semi-autonomous, or supervised
        execution_mode = ticket.get('execution_mode') or ticket.get('default_execution_mode') or 'autonomous'
        self.log(f"Execution mode: {execution_mode}")

        # Build command based on execution mode
        cmd = [
            '/home/claude/.local/bin/claude',
            '--model', ai_model,
            '--verbose',
            '--output-format', 'stream-json',
        ]

        # Load API key from .env if exists (needed early for environment setup)
        claude_env = os.environ.copy()
        env_file = os.path.join(os.path.expanduser("~"), ".claude/.env")
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        claude_env[key] = value

        # Execution mode handling:
        # - autonomous: skip all permission prompts
        # - semi-autonomous: use hooks to auto-approve safe operations, ask for risky ones
        # - supervised: ask for permission on all write operations
        if execution_mode == 'autonomous':
            cmd.append('--dangerously-skip-permissions')
            self.log("Autonomous mode: skipping all permission prompts")
        elif execution_mode == 'semi-autonomous':
            # Create hook settings for smart permission handling
            self.create_semi_autonomous_settings(work_path)
            # Set environment variables for the hook to use
            claude_env['CODEHERO_PROJECT_PATH'] = work_path
            claude_env['CODEHERO_TICKET_ID'] = str(ticket.get('id', ''))
            self.log("Semi-autonomous mode: using hooks for smart permission handling")
        else:  # supervised
            self.log("Supervised mode: Claude will ask for permission on write operations")

        cmd.extend(['-p', prompt])

        self.log(f"Starting Claude in {work_path}")
        try:
            # Run in project directory
            process = subprocess.Popen(
                cmd,
                cwd=work_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=claude_env
            )

            # Store process reference for watchdog to kill if needed
            with self.current_process_lock:
                self.current_process = process

            # Write PID file for instant kill switch
            pid_file = f"/var/run/codehero/claude_{ticket['id']}.pid"
            try:
                with open(pid_file, 'w') as f:
                    f.write(str(process.pid))
            except:
                pass

            result = None
            while True:
                # Check for user commands (non-blocking)
                new_msgs = self.get_pending_user_messages(ticket['id'])
                for msg in new_msgs:
                    content = msg['content'].strip()
                    if content == '/stop':
                        process.terminate()
                        self.save_log('warning', '⏸️ User command: /stop - Waiting for new instructions')
                        self.save_message('system', '⏸️ Stopped by user (/stop) - Waiting for new instructions')
                        return 'interrupted'

                if not self.running or not self.daemon_ref.running:
                    process.terminate()
                    return 'stopped'

                # Use select with timeout to avoid blocking
                ready, _, _ = select.select([process.stdout], [], [], 1.0)

                if ready:
                    # Read available data without blocking
                    # readline() can block if there's partial data without newline
                    line = process.stdout.readline()
                    if not line:
                        if process.poll() is not None:
                            break
                        # No complete line yet, continue loop to check stuck timeout
                        continue
                    result = self.parse_claude_output(line) or result
                elif process.poll() is not None:
                    # Process finished
                    break

                if self.last_activity:
                    stuck_time = (datetime.now() - self.last_activity).total_seconds()
                    if stuck_time > STUCK_TIMEOUT_MINUTES * 60:
                        self.log("STUCK detected", "ERROR")
                        self.daemon_ref.send_email(f"Stuck on {ticket['ticket_number']}",
                                       f"Ticket: {ticket['title']}\nNo activity for {STUCK_TIMEOUT_MINUTES} minutes.")
                        process.terminate()
                        with self.current_process_lock:
                            self.current_process = None
                        return 'stuck'
            
            # Check for permission denials in supervised or semi-autonomous mode
            if execution_mode in ('supervised', 'semi-autonomous') and self.permission_denials:
                # Take the first denied permission
                denied = self.permission_denials[0]
                pending = {
                    'tool': denied.get('tool_name', 'unknown'),
                    'input': denied.get('tool_input', {}),
                    'tool_use_id': denied.get('tool_use_id', ''),
                    'timestamp': datetime.now().isoformat()
                }
                self.log(f"Permission required: {pending['tool']}", "INFO")
                self.save_pending_permission_to_db(ticket['id'], pending)
                self.save_log('warning', f"🛡️ Permission required: {pending['tool']}")
                self.save_message('system', f"🛡️ Permission required for {pending['tool']}. Waiting for approval.")
                with self.current_process_lock:
                    self.current_process = None
                return 'permission_needed'

            # Drain any remaining output from the buffer after process ends
            # This prevents losing messages that were written just before exit
            try:
                remaining_output = process.stdout.read()
                if remaining_output:
                    for line in remaining_output.strip().split('\n'):
                        if line.strip():
                            drain_result = self.parse_claude_output(line)
                            if drain_result:
                                result = drain_result
                    self.log(f"Drained {len(remaining_output)} bytes of remaining output", "DEBUG")
            except Exception as e:
                self.log(f"Error draining output: {e}", "WARNING")

            final_result = result if result else ('success' if process.returncode == 0 else 'failed')
            self.log(f"Claude finished - returncode: {process.returncode}, result: {result}, final: {final_result}", "DEBUG")

            # Cleanup PID file
            try:
                if os.path.exists(pid_file):
                    os.remove(pid_file)
            except:
                pass

            # Clear process reference
            with self.current_process_lock:
                self.current_process = None

            return final_result

        except Exception as e:
            import traceback
            self.log(f"Error running Claude: {e}")
            self.log(f"Traceback: {traceback.format_exc()}")
            # Cleanup PID file on error
            try:
                pid_file = f"/var/run/codehero/claude_{ticket['id']}.pid"
                if os.path.exists(pid_file):
                    os.remove(pid_file)
            except:
                pass
            # Clear process reference
            with self.current_process_lock:
                self.current_process = None
            return 'failed'
    
    def ensure_ancestor_summaries(self, ticket):
        """Generate summaries for ancestors that don't have one (called when child starts)"""
        if not ticket.get('parent_ticket_id'):
            return

        try:
            conn = self.get_db()
            cursor = conn.cursor(dictionary=True)

            # Get all ancestors
            ancestors = []
            current_parent_id = ticket['parent_ticket_id']
            max_depth = 10

            while current_parent_id and len(ancestors) < max_depth:
                cursor.execute("""
                    SELECT id, parent_ticket_id, ticket_number, result_summary
                    FROM tickets WHERE id = %s
                """, (current_parent_id,))
                parent = cursor.fetchone()
                if parent:
                    ancestors.append(parent)
                    current_parent_id = parent.get('parent_ticket_id')
                else:
                    break

            # Generate summaries for ancestors that don't have one
            for ancestor in ancestors:
                if not ancestor.get('result_summary'):
                    self.log(f"Generating summary for ancestor {ancestor['ticket_number']}...")
                    summary = self.generate_summary_with_haiku(ancestor['id'])
                    if summary:
                        cursor.execute("""
                            UPDATE tickets SET result_summary = %s WHERE id = %s
                        """, (summary[:2000], ancestor['id']))
                        conn.commit()
                        self.log(f"Summary generated for {ancestor['ticket_number']}")

            cursor.close()
            conn.close()
        except Exception as e:
            self.log(f"Error ensuring ancestor summaries: {e}", "WARNING")

    def process_ticket(self, ticket):
        self.current_ticket_id = ticket['id']
        self.current_session_id = self.create_session(ticket['id'])
        self.last_activity = datetime.now()

        self.log(f"Processing: {ticket['ticket_number']} - {ticket['title']}")

        # Generate summaries for ancestors if this is a sub-ticket
        self.ensure_ancestor_summaries(ticket)

        # Auto backup disabled - backup happens on ticket close instead
        # self.create_backup(ticket['id'])

        self.update_ticket(ticket['id'], 'in_progress')
        self.save_log('info', f"Starting: {ticket['ticket_number']}")

        history = self.get_conversation_history(ticket['id'])

        if not history:
            self.save_message('user', f"Task: {ticket['title']}\n\n{ticket['description']}")
            history = self.get_conversation_history(ticket['id'])

        # Loop to handle interruptions and pending messages
        while True:
            prompt = self.build_prompt(ticket, history)
            result = self.run_claude(ticket, prompt)

            if result == 'permission_needed':
                # Supervised mode - waiting for user to approve permission
                self.end_session(self.current_session_id, 'awaiting_permission')
                self.log(f"🛡️ Permission needed: {ticket['ticket_number']} - waiting for approval")
                break

            elif result == 'interrupted':
                # User sent /stop - check for new instructions
                time.sleep(1)  # Brief pause to allow message to be sent
                pending = self.get_pending_user_messages(ticket['id'])
                if pending:
                    # Add pending messages to conversation and continue
                    for msg in pending:
                        content = msg['content'].strip()
                        if not content.startswith('/'):  # Skip commands
                            self.save_message('user', content)
                            self.save_log('info', f'User message: {content[:100]}...' if len(content) > 100 else f'User message: {content}')
                    history = self.get_conversation_history(ticket['id'])
                    self.log(f"Continuing with user feedback...")
                    continue
                else:
                    # No messages yet, wait for user to add instructions
                    self.update_ticket(ticket['id'], 'awaiting_input')
                    self.end_session(self.current_session_id, 'stopped')
                    self.log(f"⏸️ Stopped: {ticket['ticket_number']} - waiting for user input")
                    break

            elif result == 'completed':
                # Check for any pending messages before marking done
                pending = self.get_pending_user_messages(ticket['id'])
                if pending:
                    # User sent feedback - add to conversation and continue
                    for msg in pending:
                        content = msg['content'].strip()
                        if not content.startswith('/'):
                            self.save_message('user', content)
                            self.save_log('info', f'User message: {content[:100]}...' if len(content) > 100 else f'User message: {content}')
                    history = self.get_conversation_history(ticket['id'])
                    self.log(f"Processing user feedback before completing...")
                    continue

                summary = self.last_summary or 'Completed successfully'
                self.update_ticket(ticket['id'], 'done', summary)
                self.end_session(self.current_session_id, 'completed')
                self.log(f"✅ Completed: {ticket['ticket_number']}")
                self.last_summary = None  # Reset for next ticket
                break

            elif result == 'skipped':
                self.update_ticket(ticket['id'], 'skipped')
                self.end_session(self.current_session_id, 'skipped')
                self.log(f"⏭️ Skipped: {ticket['ticket_number']}")
                break

            elif result == 'stuck':
                self.update_ticket(ticket['id'], 'stuck')
                self.end_session(self.current_session_id, 'stuck')
                break

            elif result == 'stopped':
                self.update_ticket(ticket['id'], 'pending')
                self.end_session(self.current_session_id, 'stopped')
                break

            elif result == 'success':
                # Claude finished without explicit TASK COMPLETED - waiting for user
                pending = self.get_pending_user_messages(ticket['id'])
                if pending:
                    for msg in pending:
                        content = msg['content'].strip()
                        if not content.startswith('/'):
                            self.save_message('user', content)
                            self.save_log('info', f'User message: {content[:100]}...' if len(content) > 100 else f'User message: {content}')
                    history = self.get_conversation_history(ticket['id'])
                    self.log(f"Continuing with user feedback...")
                    continue
                else:
                    # Use 'done' to ensure review_scheduled_at is set for auto-review
                    self.update_ticket(ticket['id'], 'done', 'Task completed - awaiting review')
                    self.end_session(self.current_session_id, 'completed')
                    self.log(f"✅ Success: {ticket['ticket_number']} - awaiting review")
                    break

            elif result == 'rate_limited':
                # Rate limit - wait 30 minutes before retrying (don't count as failure)
                self.update_ticket(ticket['id'], 'rate_limited', 'API rate limit reached')
                self.end_session(self.current_session_id, 'rate_limited')
                self.log(f"⏳ Rate limited: {ticket['ticket_number']} - will retry in {RATE_LIMIT_COOLDOWN_MINUTES} minutes", "WARNING")
                break

            else:
                self.update_ticket(ticket['id'], 'failed', str(result))
                self.end_session(self.current_session_id, 'failed')
                self.log(f"❌ Failed: {ticket['ticket_number']}", "ERROR")
                break

        self.current_ticket_id = None
        self.current_session_id = None
    
    def get_parallel_tickets(self, max_parallel=5):
        """Get tickets with the same sequence_order for parallel execution (max 5)"""
        try:
            conn = self.get_db()
            cursor = conn.cursor(dictionary=True)

            # First, get the lowest available sequence_order
            cursor.execute("""
                SELECT MIN(t.sequence_order) as min_seq
                FROM tickets t
                WHERE t.project_id = %s
                  AND t.status IN ('open', 'new', 'pending')
                  AND (t.retry_after IS NULL OR t.retry_after <= NOW())
                  AND NOT EXISTS (
                      SELECT 1 FROM ticket_dependencies td
                      JOIN tickets dt ON dt.id = td.depends_on_ticket_id
                      WHERE td.ticket_id = t.id
                        AND dt.status NOT IN ('done', 'skipped')
                  )
                  AND (
                      t.parent_ticket_id IS NULL
                      OR EXISTS (
                          SELECT 1 FROM tickets pt
                          WHERE pt.id = t.parent_ticket_id
                            AND pt.status IN ('done', 'skipped')
                      )
                  )
            """, (self.project_id,))
            result = cursor.fetchone()
            min_seq = result['min_seq'] if result else None

            if min_seq is None:
                cursor.close()
                conn.close()
                return []

            # Get all tickets with that sequence_order (up to max_parallel)
            cursor.execute("""
                SELECT t.*, p.web_path, p.app_path, p.name as project_name, p.code as project_code,
                       p.project_type, p.tech_stack, p.context as project_context, t.context as ticket_context,
                       p.db_name, p.db_user, p.db_password, p.db_host,
                       p.ai_model as project_ai_model, t.ai_model as ticket_ai_model,
                       p.android_device_type, p.android_remote_host, p.android_remote_port, p.android_screen_size,
                       p.dotnet_port, p.default_test_command,
                       p.default_execution_mode, p.reference_path
                FROM tickets t
                JOIN projects p ON t.project_id = p.id
                WHERE t.project_id = %s
                  AND t.status IN ('open', 'new', 'pending')
                  AND t.sequence_order = %s
                  AND (t.retry_after IS NULL OR t.retry_after <= NOW())
                  AND NOT EXISTS (
                      SELECT 1 FROM ticket_dependencies td
                      JOIN tickets dt ON dt.id = td.depends_on_ticket_id
                      WHERE td.ticket_id = t.id
                        AND dt.status NOT IN ('done', 'skipped')
                  )
                  AND (
                      t.parent_ticket_id IS NULL
                      OR EXISTS (
                          SELECT 1 FROM tickets pt
                          WHERE pt.id = t.parent_ticket_id
                            AND pt.status IN ('done', 'skipped')
                      )
                  )
                ORDER BY t.is_forced DESC, t.created_at ASC
                LIMIT %s
            """, (self.project_id, min_seq, max_parallel))
            tickets = cursor.fetchall()
            cursor.close()
            conn.close()
            return tickets
        except Exception as e:
            self.log(f"Error getting parallel tickets: {e}", "ERROR")
            return []

    def run(self):
        self.log(f"Worker started")

        while self.running and self.daemon_ref.running:
            try:
                # Get tickets with same sequence_order for parallel execution
                tickets = self.get_parallel_tickets(max_parallel=5)

                if tickets:
                    if len(tickets) == 1:
                        # Single ticket - run directly
                        self.process_ticket(tickets[0])
                    else:
                        # Multiple tickets - run in parallel
                        self.log(f"Running {len(tickets)} tickets in parallel (seq={tickets[0].get('sequence_order')})")
                        from concurrent.futures import ThreadPoolExecutor, as_completed

                        with ThreadPoolExecutor(max_workers=5) as executor:
                            futures = {executor.submit(self.process_ticket, t): t for t in tickets}
                            for future in as_completed(futures):
                                ticket = futures[future]
                                try:
                                    future.result()
                                except Exception as e:
                                    self.log(f"Parallel ticket error {ticket['ticket_number']}: {e}", "ERROR")
                else:
                    time.sleep(POLL_INTERVAL)
                    tickets = self.get_parallel_tickets(max_parallel=5)
                    if not tickets:
                        self.log("No more tickets, worker stopping")
                        break
            except Exception as e:
                self.log(f"Error: {e}", "ERROR")
                time.sleep(POLL_INTERVAL)

        self.log(f"Worker stopped")
    
    def stop(self):
        self.running = False


# ============================================================================
# WATCHDOG - Monitors tickets for stuck patterns using Haiku
# ============================================================================

WATCHDOG_INTERVAL = 1800  # Check every 30 minutes
WATCHDOG_MIN_MESSAGES = 10  # Minimum messages before checking
WATCHDOG_CHECK_LAST_N = 30  # Analyze last N messages

class Watchdog(threading.Thread):
    """Background thread that monitors running tickets for stuck patterns"""

    def __init__(self, daemon):
        super().__init__(daemon=True)
        self.daemon_ref = daemon
        self.running = True

    def log(self, message, level="INFO"):
        self.daemon_ref.log(f"[Watchdog] {message}", level)

    def get_db(self):
        return self.daemon_ref.get_db()

    def run(self):
        self.log("Watchdog started - monitoring for stuck tickets")

        while self.running:
            try:
                time.sleep(WATCHDOG_INTERVAL)
                if not self.running:
                    break
                self.check_running_tickets()
            except Exception as e:
                self.log(f"Error: {e}", "ERROR")

    def check_running_tickets(self):
        """Check all in_progress tickets for stuck patterns"""
        try:
            conn = self.get_db()
            cursor = conn.cursor(dictionary=True)

            # Get tickets that have been in_progress for a while
            cursor.execute("""
                SELECT t.id, t.project_id, t.ticket_number, t.title, p.name as project_name,
                       (SELECT COUNT(*) FROM conversation_messages WHERE ticket_id = t.id) as msg_count,
                       (SELECT SUM(tokens_used) FROM execution_sessions WHERE ticket_id = t.id AND status = 'running') as running_tokens
                FROM tickets t
                JOIN projects p ON t.project_id = p.id
                WHERE t.status = 'in_progress'
            """)
            tickets = cursor.fetchall()
            cursor.close()
            conn.close()

            for ticket in tickets:
                if ticket['msg_count'] >= WATCHDOG_MIN_MESSAGES:
                    self.analyze_ticket(ticket)

        except Exception as e:
            self.log(f"Error checking tickets: {e}", "ERROR")

    def analyze_ticket(self, ticket):
        """Use Haiku to analyze if a ticket is stuck"""
        try:
            conn = self.get_db()
            cursor = conn.cursor(dictionary=True)

            # Get last N messages
            cursor.execute("""
                SELECT role, content, created_at
                FROM conversation_messages
                WHERE ticket_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (ticket['id'], WATCHDOG_CHECK_LAST_N))
            messages = cursor.fetchall()
            cursor.close()
            conn.close()

            if not messages:
                return

            # Reverse to chronological order
            messages = list(reversed(messages))

            # Build conversation summary for analysis
            conversation = []
            for msg in messages:
                role = msg['role'].upper()
                content = msg['content'] or "[tool use]"
                # Truncate long messages
                if len(content) > 500:
                    content = content[:500] + "..."
                conversation.append(f"[{role}]: {content}")

            conversation_text = "\n".join(conversation)

            # Call Haiku for analysis
            prompt = f"""Analyze this AI assistant conversation and determine if it's stuck in an unproductive loop.

TICKET: {ticket['ticket_number']} - {ticket['title']}
PROJECT: {ticket['project_name']}
MESSAGES ANALYZED: {len(messages)}
TOKENS USED: {ticket.get('running_tokens', 0) or 0}

RECENT CONVERSATION:
{conversation_text}

SIGNS OF BEING STUCK:
1. Same error appearing repeatedly without resolution
2. AI trying the same fix multiple times
3. Tests failing repeatedly with same errors
4. Circular behavior (edit → test → fail → same edit)
5. AI expressing uncertainty or asking for help repeatedly
6. No meaningful progress in last several messages

RESPOND WITH EXACTLY ONE LINE:
- "CONTINUE" if the AI is making progress
- "STUCK: <brief reason>" if the AI appears stuck

Your response:"""

            result = subprocess.run(
                ['/home/claude/.local/bin/claude', '--model', 'haiku', '--print'],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=30,
                cwd='/tmp'
            )

            if result.returncode == 0 and result.stdout:
                response = result.stdout.strip().split('\n')[0]  # First line only

                if response.startswith('STUCK:'):
                    reason = response[6:].strip()
                    self.mark_ticket_stuck(ticket, reason)
                else:
                    self.log(f"Ticket {ticket['ticket_number']}: OK - making progress")

        except subprocess.TimeoutExpired:
            self.log(f"Haiku timeout analyzing {ticket['ticket_number']}", "WARNING")
        except Exception as e:
            self.log(f"Error analyzing {ticket['ticket_number']}: {e}", "ERROR")

    def mark_ticket_stuck(self, ticket, reason):
        """Mark a ticket as stuck and notify"""
        self.log(f"STUCK DETECTED: {ticket['ticket_number']} - {reason}", "WARNING")

        # Kill the running Claude process for this ticket
        project_id = ticket.get('project_id')
        if project_id and project_id in self.daemon_ref.workers:
            worker = self.daemon_ref.workers[project_id]
            if worker.current_ticket_id == ticket['id']:
                if worker.kill_process():
                    self.log(f"Killed Claude process for ticket {ticket['ticket_number']}", "WARNING")

        try:
            conn = self.get_db()
            cursor = conn.cursor()

            # Update ticket status
            cursor.execute("""
                UPDATE tickets SET status = 'stuck', updated_at = NOW()
                WHERE id = %s
            """, (ticket['id'],))

            # Add system message explaining why
            stuck_message = f"[WATCHDOG] Ticket marked as stuck: {reason}\n\nThe AI appears to be in an unproductive loop. Human intervention may be required."
            cursor.execute("""
                INSERT INTO conversation_messages (ticket_id, role, content, created_at)
                VALUES (%s, 'system', %s, NOW())
            """, (ticket['id'], stuck_message))

            # Stop any running sessions for this ticket
            cursor.execute("""
                UPDATE execution_sessions SET status = 'stuck', ended_at = NOW()
                WHERE ticket_id = %s AND status = 'running'
            """, (ticket['id'],))

            conn.commit()
            cursor.close()
            conn.close()

            # Send email notification
            self.daemon_ref.send_email(
                f"Ticket Stuck: {ticket['ticket_number']}",
                f"Ticket: {ticket['ticket_number']} - {ticket['title']}\n"
                f"Project: {ticket['project_name']}\n"
                f"Reason: {reason}\n\n"
                f"The AI has been detected in an unproductive loop and the ticket has been paused.\n"
                f"Please review and provide guidance to continue."
            )

            # Send Telegram notification
            notify('watchdog_alert', 'Ticket Stuck - Watchdog Alert',
                   f"{reason}\n\nThe AI appears stuck and needs intervention.",
                   ticket.get('project_name'), ticket.get('ticket_number'))

            # Broadcast to web UI
            try:
                data = json.dumps({
                    'type': 'ticket_stuck',
                    'ticket_id': ticket['id'],
                    'reason': reason
                }).encode('utf-8')
                req = urllib.request.Request(
                    f"{WEB_APP_URL}/api/internal/broadcast",
                    data=data,
                    headers={'Content-Type': 'application/json'}
                )
                urllib.request.urlopen(req, timeout=2)
            except:
                pass

        except Exception as e:
            self.log(f"Error marking ticket stuck: {e}", "ERROR")

    def stop(self):
        self.running = False


class TelegramPoller(threading.Thread):
    """Background thread that polls Telegram for reply messages"""

    def __init__(self, daemon):
        super().__init__(daemon=True)
        self.daemon_ref = daemon
        self.running = True

    def log(self, message, level="INFO"):
        self.daemon_ref.log(f"[TelegramPoller] {message}", level)

    def run(self):
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            self.log("Telegram not configured - poller disabled")
            return

        self.log("Telegram poller started - listening for replies")

        while self.running:
            try:
                time.sleep(10)  # Poll every 10 seconds
                if not self.running:
                    break
                self.daemon_ref.process_telegram_replies()
            except Exception as e:
                self.log(f"Error: {e}", "ERROR")

    def stop(self):
        self.running = False


class ClaudeDaemon:
    """Main daemon - manages project workers"""

    def __init__(self):
        self.running = True
        self.config = self.load_config()
        self.db_pool = self.create_db_pool()
        self.workers = {}
        self.workers_lock = threading.Lock()
        self.max_parallel = int(self.config.get('MAX_PARALLEL_PROJECTS', MAX_PARALLEL_PROJECTS))

        # Load Telegram notification settings
        global TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, NOTIFY_SETTINGS
        TELEGRAM_BOT_TOKEN = self.config.get('TELEGRAM_BOT_TOKEN', '')
        TELEGRAM_CHAT_ID = self.config.get('TELEGRAM_CHAT_ID', '')
        NOTIFY_SETTINGS['ticket_completed'] = self.config.get('NOTIFY_TICKET_COMPLETED', 'yes').lower() == 'yes'
        NOTIFY_SETTINGS['awaiting_input'] = self.config.get('NOTIFY_AWAITING_INPUT', 'yes').lower() == 'yes'
        NOTIFY_SETTINGS['ticket_failed'] = self.config.get('NOTIFY_TICKET_FAILED', 'yes').lower() == 'yes'
        NOTIFY_SETTINGS['watchdog_alert'] = self.config.get('NOTIFY_WATCHDOG_ALERT', 'yes').lower() == 'yes'
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            print(f"[INFO] Telegram notifications enabled")

        # Load retry cooldown settings
        global RATE_LIMIT_COOLDOWN_MINUTES, RETRY_COOLDOWN_MINUTES
        RATE_LIMIT_COOLDOWN_MINUTES = int(self.config.get('RATE_LIMIT_COOLDOWN_MINUTES', '30'))
        RETRY_COOLDOWN_MINUTES = int(self.config.get('RETRY_COOLDOWN_MINUTES', '5'))
        print(f"[INFO] Retry cooldowns: rate_limit={RATE_LIMIT_COOLDOWN_MINUTES}min, errors={RETRY_COOLDOWN_MINUTES}min")

        # Load Auto-review settings (uses Claude CLI with --model haiku)
        global AUTO_REVIEW_ENABLED, AUTO_REVIEW_DELAY_SECONDS
        AUTO_REVIEW_DELAY_SECONDS = int(self.config.get('AUTO_REVIEW_DELAY_SECONDS', '10'))

        # Check if Claude CLI exists
        claude_cli = '/home/claude/.local/bin/claude'
        if os.path.exists(claude_cli):
            AUTO_REVIEW_ENABLED = True
            print(f"[INFO] Auto-review enabled (Haiku via CLI, {AUTO_REVIEW_DELAY_SECONDS}s delay)")
        else:
            AUTO_REVIEW_ENABLED = False
            print("[INFO] Auto-review disabled (Claude CLI not found)")

        self.global_context = self.load_global_context()

        # Initialize Smart Context Manager
        self.context_manager = None
        if SMART_CONTEXT_ENABLED:
            try:
                self.context_manager = SmartContextManager(self.db_pool, self.log)
                self.log("Smart Context Manager initialized")
            except Exception as e:
                self.log(f"Failed to initialize Smart Context Manager: {e}", "WARNING")

        # Initialize Watchdog (will be started in run())
        self.watchdog = None
        # Initialize Telegram Poller (will be started in run())
        self.telegram_poller = None

    def load_global_context(self):
        """Load global context that applies to all projects"""
        try:
            if os.path.exists(GLOBAL_CONTEXT_FILE):
                with open(GLOBAL_CONTEXT_FILE, 'r') as f:
                    return f.read().strip()
        except Exception as e:
            self.log(f"Warning: Could not load global context: {e}", "WARNING")
        return ""

    # ==================== AUTO-REVIEW SYSTEM ====================

    def get_last_message_role(self, ticket_id: int) -> str:
        """Get the role of the most recent message for a ticket."""
        conn = None
        try:
            conn = self.get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT role FROM conversation_messages
                WHERE ticket_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT 1
            """, (ticket_id,))
            result = cursor.fetchone()
            cursor.close()
            return result['role'] if result else None
        except Exception as e:
            self.log(f"Error getting last message role: {e}", "ERROR")
            return None
        finally:
            if conn:
                conn.close()

    def get_last_user_message(self, ticket_id: int) -> dict:
        """Get the most recent user message for a ticket."""
        conn = None
        try:
            conn = self.get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, content, created_at FROM conversation_messages
                WHERE ticket_id = %s AND role = 'user'
                ORDER BY created_at DESC, id DESC
                LIMIT 1
            """, (ticket_id,))
            result = cursor.fetchone()
            cursor.close()
            return result
        except Exception as e:
            self.log(f"Error getting last user message: {e}", "ERROR")
            return None
        finally:
            if conn:
                conn.close()

    def get_messages_after_last_user(self, ticket_id: int) -> list:
        """Get all assistant messages after the last user message."""
        conn = None
        try:
            conn = self.get_db()
            cursor = conn.cursor(dictionary=True)
            # Get last user message timestamp
            cursor.execute("""
                SELECT created_at FROM conversation_messages
                WHERE ticket_id = %s AND role = 'user'
                ORDER BY created_at DESC, id DESC
                LIMIT 1
            """, (ticket_id,))
            last_user = cursor.fetchone()

            if not last_user:
                # No user messages, get all assistant messages
                cursor.execute("""
                    SELECT role, content, created_at FROM conversation_messages
                    WHERE ticket_id = %s AND role = 'assistant'
                    ORDER BY created_at ASC
                """, (ticket_id,))
            else:
                # Get messages after last user message
                cursor.execute("""
                    SELECT role, content, created_at FROM conversation_messages
                    WHERE ticket_id = %s AND role = 'assistant'
                      AND created_at >= %s
                    ORDER BY created_at ASC
                """, (ticket_id, last_user['created_at']))

            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            self.log(f"Error getting messages after last user: {e}", "ERROR")
            return []
        finally:
            if conn:
                conn.close()

    def classify_with_haiku(self, ticket_id: int):
        """
        Use Haiku (via Claude CLI) to classify if ticket is completed or needs input.
        Returns: 'completed', 'question', 'error', or None if call failed (for retry)
        """
        if not AUTO_REVIEW_ENABLED:
            return 'completed'  # Default to completed if auto-review disabled

        try:
            # Get last user message (the task)
            last_user = self.get_last_user_message(ticket_id)
            user_task = last_user['content'][:1000] if last_user else "Unknown task"

            # Get all assistant messages after last user message
            ai_messages = self.get_messages_after_last_user(ticket_id)
            if not ai_messages:
                return 'error'

            # Format AI messages - focus on the last message (most important for classification)
            # Last message gets 3000 chars, previous 5 get 500 chars each for context
            formatted_messages = []
            recent = ai_messages[-6:]  # Last 6 messages
            for i, msg in enumerate(recent):
                if i == len(recent) - 1:
                    # Last message - full content (up to 3000 chars)
                    formatted_messages.append(msg['content'][:3000])
                else:
                    # Previous messages - shorter (500 chars)
                    formatted_messages.append(msg['content'][:500])
            ai_response = "\n---\n".join(formatted_messages)

            # Build prompt for Haiku
            prompt = f"""Analyze this AI assistant conversation and classify the outcome.

User's Request:
{user_task}

AI's Response (last messages):
{ai_response[-5000:]}

Based on the AI's final response, classify as ONE of:
- COMPLETED - The AI finished the task and is reporting completion/results
- QUESTION - The AI is asking the user a question and waiting for a response
- ERROR - The AI encountered a problem it cannot solve alone

Important: If the AI says "Done", "Completed", "Finished", "Ready", etc. → COMPLETED
If the AI asks "Should I..?", "Do you want..?", "What do you think?" → QUESTION
If the AI reports an error or asks for help → ERROR

Reply with ONLY one word: COMPLETED, QUESTION, or ERROR"""

            # Call Haiku via Claude CLI (same as watchdog)
            result = subprocess.run(
                ['/home/claude/.local/bin/claude', '--model', 'haiku', '--print'],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=30,
                cwd='/tmp'
            )

            if result.returncode == 0 and result.stdout:
                response = result.stdout.strip().split('\n')[0].upper()  # First line only
                self.log(f"Haiku classification for ticket {ticket_id}: {response}")

                if response in ['COMPLETED', 'QUESTION', 'ERROR']:
                    return response.lower()
                else:
                    self.log(f"Unexpected Haiku response: {response}, defaulting to question", "WARNING")
                    return 'question'
            else:
                self.log(f"Haiku CLI failed: {result.stderr}", "ERROR")
                return None  # Return None for retry

        except subprocess.TimeoutExpired:
            self.log(f"Haiku timeout classifying ticket {ticket_id}", "WARNING")
            return None  # Return None for retry
        except Exception as e:
            self.log(f"Haiku classification failed: {e}", "ERROR")
            return None  # Return None for retry

    def process_scheduled_reviews(self):
        """Process tickets that are due for auto-review."""
        if not AUTO_REVIEW_ENABLED:
            return

        MAX_REVIEW_ATTEMPTS = 10
        RETRY_DELAY_MINUTES = 5

        conn = None
        try:
            conn = self.get_db()
            cursor = conn.cursor(dictionary=True)

            # Find tickets ready for review
            cursor.execute("""
                SELECT t.id, t.ticket_number, t.deps_include_awaiting, t.review_attempts,
                       p.name as project_name
                FROM tickets t
                JOIN projects p ON t.project_id = p.id
                WHERE t.status = 'awaiting_input'
                  AND t.review_scheduled_at IS NOT NULL
                  AND t.review_scheduled_at <= NOW()
                  AND t.awaiting_reason IS NULL
            """)
            tickets = cursor.fetchall()

            for ticket in tickets:
                ticket_id = ticket['id']
                ticket_number = ticket['ticket_number']
                attempts = ticket.get('review_attempts', 0) or 0

                # Check last message role - skip if user replied (user or system)
                last_role = self.get_last_message_role(ticket_id)

                if last_role in ('user', 'system'):
                    # User replied - skip review, clear schedule and reset attempts
                    cursor.execute("""
                        UPDATE tickets SET review_scheduled_at = NULL, review_attempts = 0
                        WHERE id = %s
                    """, (ticket_id,))
                    conn.commit()
                    self.log(f"Skipping review for {ticket_number} (user replied)")
                    continue

                # Only auto-close for relaxed mode tickets
                if not ticket['deps_include_awaiting']:
                    # Strict mode - mark as completed but don't auto-close
                    cursor.execute("""
                        UPDATE tickets SET
                            review_scheduled_at = NULL,
                            review_attempts = 0,
                            awaiting_reason = 'completed'
                        WHERE id = %s
                    """, (ticket_id,))
                    conn.commit()
                    self.log(f"Strict mode ticket {ticket_number} marked as completed (awaiting user review)")
                    continue

                # Relaxed mode - do Haiku classification
                result = self.classify_with_haiku(ticket_id)

                if result is None:
                    # Haiku call failed - retry if under max attempts
                    attempts += 1
                    if attempts < MAX_REVIEW_ATTEMPTS:
                        cursor.execute("""
                            UPDATE tickets SET
                                review_scheduled_at = DATE_ADD(NOW(), INTERVAL %s MINUTE),
                                review_attempts = %s
                            WHERE id = %s
                        """, (RETRY_DELAY_MINUTES, attempts, ticket_id))
                        conn.commit()
                        self.log(f"Haiku failed for {ticket_number}, retry {attempts}/{MAX_REVIEW_ATTEMPTS} in {RETRY_DELAY_MINUTES}min")
                    else:
                        # Max retries reached - mark as error
                        cursor.execute("""
                            UPDATE tickets SET
                                awaiting_reason = 'error',
                                review_scheduled_at = NULL,
                                review_attempts = %s
                            WHERE id = %s
                        """, (attempts, ticket_id))
                        conn.commit()
                        self.log(f"Haiku failed for {ticket_number} after {attempts} attempts, marked as error", "WARNING")
                        notify('awaiting_input', 'Review Failed',
                               f"{ticket_number} review failed after {attempts} attempts",
                               ticket['project_name'], ticket_number)
                    continue

                if result == 'completed':
                    # Auto-close ticket (summary will be generated when child starts, if needed)
                    cursor.execute("""
                        UPDATE tickets SET
                            status = 'done',
                            awaiting_reason = NULL,
                            review_scheduled_at = NULL,
                            review_attempts = 0,
                            close_reason = 'auto_reviewed',
                            updated_at = NOW()
                        WHERE id = %s
                    """, (ticket_id,))
                    conn.commit()
                    self.log(f"Auto-closed {ticket_number} (Haiku: COMPLETED)")

                    # Create backup on ticket close
                    self.create_backup(ticket_id, 'close')

                    # Send notification
                    notify('ticket_completed', 'Ticket Auto-Closed',
                           f"{ticket_number} auto-reviewed and closed",
                           ticket['project_name'], ticket_number)
                else:
                    # Stay in awaiting_input with reason
                    cursor.execute("""
                        UPDATE tickets SET
                            awaiting_reason = %s,
                            review_scheduled_at = NULL,
                            review_attempts = 0
                        WHERE id = %s
                    """, (result, ticket_id))
                    conn.commit()
                    self.log(f"Ticket {ticket_number} needs input (Haiku: {result.upper()})")

                    # Send notification
                    notify('awaiting_input', f'Ticket Needs Input ({result})',
                           f"{ticket_number} is waiting for your response",
                           ticket['project_name'], ticket_number)

            cursor.close()
        except Exception as e:
            self.log(f"Error processing scheduled reviews: {e}", "ERROR")
        finally:
            if conn:
                conn.close()

    # ==================== END AUTO-REVIEW SYSTEM ====================

    def load_config(self):
        config = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        # Remove inline comments (but be careful with # in passwords)
                        if ' #' in value:
                            value = value.split(' #')[0]
                        config[key.strip()] = value.strip().strip('"').strip("'")
        return config
    
    def create_db_pool(self):
        return pooling.MySQLConnectionPool(
            host=self.config.get('DB_HOST', 'localhost'),
            user=self.config.get('DB_USER', 'claude_user'),
            password=self.config.get('DB_PASSWORD', ''),
            database=self.config.get('DB_NAME', 'claude_knowledge'),
            pool_name='daemon_pool',
            pool_size=30,
            pool_reset_session=True
        )
    
    def get_db(self):
        return self.db_pool.get_connection()
    
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] [{level}] {message}"
        try:
            os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
            with open(LOG_FILE, 'a') as f:
                f.write(log_line + "\n")
        except: pass

    def create_backup(self, ticket_id, trigger='auto'):
        """Create automatic backup from ClaudeDaemon (for auto-close scenarios)"""
        try:
            conn = self.get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT p.* FROM projects p
                JOIN tickets t ON t.project_id = p.id
                WHERE t.id = %s
            """, (ticket_id,))
            project = cursor.fetchone()
            cursor.close()
            conn.close()

            if not project:
                self.log("Could not find project for backup", "WARNING")
                return

            project_code = project['code']
            backup_subdir = os.path.join(BACKUP_DIR, project_code)
            os.makedirs(backup_subdir, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"{project_code}_{timestamp}_{trigger}.zip"
            backup_path = os.path.join(backup_subdir, backup_name)

            temp_dir = tempfile.mkdtemp()
            temp_backup = os.path.join(temp_dir, 'backup')
            os.makedirs(temp_backup)

            try:
                # Copy web folder
                if project.get('web_path') and os.path.exists(project['web_path']):
                    shutil.copytree(project['web_path'], os.path.join(temp_backup, 'web'), dirs_exist_ok=True)

                # Copy app folder
                if project.get('app_path') and os.path.exists(project['app_path']):
                    shutil.copytree(project['app_path'], os.path.join(temp_backup, 'app'), dirs_exist_ok=True)

                # Export database
                if project.get('db_name') and project.get('db_user') and project.get('db_password'):
                    db_dir = os.path.join(temp_backup, 'database')
                    os.makedirs(db_dir, exist_ok=True)

                    db_host = project.get('db_host', 'localhost')
                    db_name = project['db_name']
                    db_user = project['db_user']
                    db_pass = project['db_password']

                    # Schema + Data
                    dump_cmd = f"mysqldump -h {db_host} -u {db_user} -p'{db_pass}' {db_name} 2>/dev/null"
                    result = subprocess.run(dump_cmd, shell=True, capture_output=True, text=True)
                    if result.returncode == 0:
                        with open(os.path.join(db_dir, 'dump.sql'), 'w') as f:
                            f.write(result.stdout)

                # Create zip
                with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(temp_backup):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arc_name = os.path.relpath(file_path, temp_backup)
                            zipf.write(file_path, arc_name)

                # Cleanup old backups (keep MAX_BACKUPS)
                backups = sorted(
                    [f for f in os.listdir(backup_subdir) if f.endswith('.zip')],
                    key=lambda x: os.path.getmtime(os.path.join(backup_subdir, x)),
                    reverse=True
                )
                for old_backup in backups[MAX_BACKUPS:]:
                    os.remove(os.path.join(backup_subdir, old_backup))

                self.log(f"Backup created: {backup_name}")

            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        except Exception as e:
            self.log(f"Backup error: {e}", "WARNING")

    def process_telegram_replies(self):
        """Process replies received via Telegram and add them to tickets"""
        try:
            replies = poll_telegram_replies()
            for reply in replies:
                ticket_number = reply['ticket_number']
                message = reply['message']
                from_user = reply['from']
                is_reply = reply.get('is_reply', True)

                # Check if it's a direct message (not a reply)
                if not is_reply:
                    send_telegram("ℹ️ To interact with a ticket, please **reply** to a notification message.\n\n💡 Tip: Add ? at start or end to ask a question without reopening the ticket.")
                    continue

                # Check if ticket number was extracted
                if not ticket_number:
                    send_telegram("❌ Could not find ticket number in that message.\nPlease reply to a notification that contains a ticket number.")
                    continue

                # Find ticket by number
                conn = self.get_db()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT t.id, t.status, t.title, t.project_id, p.name as project_name
                    FROM tickets t
                    JOIN projects p ON t.project_id = p.id
                    WHERE t.ticket_number = %s
                """, (ticket_number,))
                ticket = cursor.fetchone()

                if ticket:
                    # Check if it's a question (starts or ends with ?)
                    msg_stripped = message.strip()
                    is_question = msg_stripped.startswith('?') or msg_stripped.endswith('?')
                    if is_question:
                        # It's a question - get summary and respond without reopening
                        # Remove ? from start or end
                        question = msg_stripped.lstrip('?').rstrip('?').strip()
                        cursor.close()
                        conn.close()
                        self.handle_telegram_question(ticket, ticket_number, question)
                        continue

                    # Normal flow - add message to conversation
                    cursor.execute("""
                        INSERT INTO conversation_messages (ticket_id, role, content, created_at)
                        VALUES (%s, 'user', %s, NOW())
                    """, (ticket['id'], f"[Via Telegram from {from_user}]\n{message}"))

                    # If ticket is awaiting_input, reopen it
                    # Clear awaiting_reason and review_scheduled_at to cancel any pending auto-review
                    if ticket['status'] == 'awaiting_input':
                        cursor.execute("""
                            UPDATE tickets SET status = 'open',
                            awaiting_reason = NULL, review_scheduled_at = NULL,
                            updated_at = NOW()
                            WHERE id = %s
                        """, (ticket['id'],))
                        self.log(f"Telegram reply reopened ticket {ticket_number}")

                        # Send confirmation
                        send_telegram(f"✅ Message received for {ticket_number}\nTicket reopened - Claude will continue.")

                    conn.commit()
                else:
                    self.log(f"Telegram reply for unknown ticket: {ticket_number}", "WARNING")
                    send_telegram(f"❌ Ticket {ticket_number} not found.\nIt may have been deleted or archived.")

                cursor.close()
                conn.close()
        except Exception as e:
            self.log(f"Error processing Telegram replies: {e}", "ERROR")

    def handle_telegram_question(self, ticket, ticket_number, question):
        """Handle a question from Telegram - respond with summary without reopening ticket"""
        try:
            # Get last messages from conversation
            conn = self.get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT role, content, created_at
                FROM conversation_messages
                WHERE ticket_id = %s
                ORDER BY created_at DESC
                LIMIT 10
            """, (ticket['id'],))
            messages = cursor.fetchall()
            messages.reverse()  # Chronological order

            # Get token usage
            cursor.execute("""
                SELECT COALESCE(SUM(tokens_used), 0) as total_tokens
                FROM execution_sessions
                WHERE ticket_id = %s
            """, (ticket['id'],))
            tokens_row = cursor.fetchone()
            total_tokens = tokens_row['total_tokens'] if tokens_row else 0

            cursor.close()
            conn.close()

            # Build context for Haiku
            context = f"Ticket: {ticket_number}\n"
            context += f"Title: {ticket['title']}\n"
            context += f"Status: {ticket['status']}\n"
            context += f"Tokens used: {total_tokens:,}\n\n"
            context += "Recent conversation:\n"
            for msg in messages[-5:]:  # Last 5 messages
                role = "User" if msg['role'] == 'user' else "Claude"
                msg_content = msg['content'] or "[no content]"
                content = msg_content[:300] + "..." if len(msg_content) > 300 else msg_content
                context += f"\n{role}: {content}\n"

            # Call Haiku for summary
            summary = self.ask_haiku_for_summary(context, question)

            # Send response via Telegram
            response = f"📋 <b>{ticket_number}</b>\n\n{summary}"
            send_telegram(response)
            self.log(f"Telegram question answered for {ticket_number}")

        except Exception as e:
            self.log(f"Error handling Telegram question: {e}", "ERROR")
            send_telegram(f"❌ Error getting info for {ticket_number}")

    def ask_haiku_for_summary(self, context, question):
        """Use Claude Haiku to generate a short summary"""
        try:
            import subprocess

            prompt = f"""Based on this ticket information, answer the user's question in 2-3 short sentences in the same language as the question. Be concise.

{context}

User's question: {question if question else "What is the current status?"}

Answer briefly:"""

            # Load API key from .env if exists (same as main ticket processing)
            claude_env = os.environ.copy()
            env_file = os.path.join(os.path.expanduser("~"), ".claude/.env")
            if os.path.exists(env_file):
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if '=' in line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            claude_env[key] = value

            # Use claude CLI with haiku model (full path needed for daemon)
            claude_bin = os.path.expanduser('~/.local/bin/claude')
            self.log(f"Calling Haiku: {claude_bin}", "DEBUG")
            result = subprocess.run(
                [claude_bin, '--model', 'haiku', '-p', prompt, '--dangerously-skip-permissions'],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.path.expanduser('~'),
                env=claude_env
            )

            self.log(f"Haiku returncode: {result.returncode}", "DEBUG")
            self.log(f"Haiku stdout: {result.stdout[:100] if result.stdout else 'empty'}...", "DEBUG")
            self.log(f"Haiku stderr: {result.stderr[:100] if result.stderr else 'empty'}...", "DEBUG")

            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            else:
                # Fallback to basic info
                self.log(f"Haiku failed, using fallback", "WARNING")
                return f"Status: {context.split('Status:')[1].split(chr(10))[0].strip() if 'Status:' in context else 'unknown'}"

        except Exception as e:
            self.log(f"Haiku summary failed: {e}", "WARNING")
            return "Could not generate summary. Check the web panel for details."

    def send_email(self, subject, body):
        if self.config.get('SMTP_ENABLED', 'false').lower() != 'true':
            return
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config.get('SMTP_USER', '')
            msg['To'] = self.config.get('ALERT_EMAIL', '')
            msg['Subject'] = f"[CodeHero] {subject}"
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.config.get('SMTP_HOST', 'smtp.gmail.com'),
                                 int(self.config.get('SMTP_PORT', '587')))
            if self.config.get('SMTP_USE_TLS', 'true').lower() == 'true':
                server.starttls()
            server.login(self.config.get('SMTP_USER', ''), self.config.get('SMTP_PASSWORD', ''))
            server.send_message(msg)
            server.quit()
            self.log(f"Email sent: {subject}")
        except Exception as e:
            self.log(f"Email error: {e}", "ERROR")
    
    def get_projects_with_open_tickets(self):
        try:
            conn = self.get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT DISTINCT p.id, p.name, p.code, COALESCE(p.web_path, p.app_path) as work_path,
                       (SELECT COUNT(*) FROM tickets WHERE project_id = p.id AND status IN ('open', 'new', 'pending')) as open_count
                FROM projects p
                JOIN tickets t ON t.project_id = p.id
                WHERE t.status IN ('open', 'new', 'pending')
                AND p.status = 'active'
                ORDER BY 
                    (SELECT MIN(CASE priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END) 
                     FROM tickets WHERE project_id = p.id AND status IN ('open', 'new', 'pending')) ASC
            """)
            projects = cursor.fetchall()
            cursor.close()
            conn.close()
            return projects
        except Exception as e:
            self.log(f"Error getting projects: {e}", "ERROR")
            return []
    
    def cleanup_dead_workers(self):
        with self.workers_lock:
            dead = [pid for pid, w in self.workers.items() if not w.is_alive()]
            for pid in dead:
                del self.workers[pid]

        # Also reset orphaned in_progress tickets (no active worker)
        self.reset_orphaned_tickets()

    def reset_orphaned_tickets(self):
        """Reset in_progress tickets that have no active worker"""
        try:
            conn = self.get_db()
            cursor = conn.cursor(dictionary=True)

            # Get all in_progress tickets
            cursor.execute("""
                SELECT t.id, t.ticket_number, t.project_id
                FROM tickets t
                WHERE t.status = 'in_progress'
            """)
            in_progress = cursor.fetchall()

            # Check which ones have no active worker
            with self.workers_lock:
                active_project_ids = set(self.workers.keys())

            orphaned = [t for t in in_progress if t['project_id'] not in active_project_ids]

            if orphaned:
                orphan_ids = [t['id'] for t in orphaned]
                cursor.execute(f"""
                    UPDATE tickets
                    SET status = 'open', updated_at = NOW()
                    WHERE id IN ({','.join(['%s']*len(orphan_ids))})
                """, orphan_ids)
                conn.commit()
                for t in orphaned:
                    self.log(f"Reset orphaned ticket {t['ticket_number']} to open")

            cursor.close()
            conn.close()
        except Exception as e:
            self.log(f"Error resetting orphaned tickets: {e}", "ERROR")

    def auto_close_expired_reviews(self):
        """Auto-close awaiting_input tickets that have passed their 7-day deadline"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tickets
                SET status = 'done',
                    closed_at = NOW(),
                    closed_by = 'Claude',
                    close_reason = 'auto_closed_7days',
                    review_deadline = NULL,
                    updated_at = NOW()
                WHERE status = 'awaiting_input'
                AND review_deadline IS NOT NULL
                AND review_deadline < NOW()
            """)
            affected = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()
            if affected > 0:
                self.log(f"Auto-closed {affected} expired awaiting_input ticket(s)")
        except Exception as e:
            self.log(f"Error auto-closing tickets: {e}", "ERROR")

    def recover_orphaned_tickets(self):
        """Reset tickets that were left in_progress from a previous daemon run (e.g., after reboot)"""
        self.log("Checking for orphaned tickets from previous run...")

        # Retry up to 5 times in case MySQL isn't ready yet
        for attempt in range(5):
            try:
                conn = self.get_db()
                cursor = conn.cursor()

                # Reset in_progress tickets back to open
                cursor.execute("""
                    UPDATE tickets
                    SET status='open', updated_at=NOW()
                    WHERE status='in_progress'
                """)
                reset_tickets = cursor.rowcount

                # Also reset failed tickets back to open (from interrupted runs)
                cursor.execute("""
                    UPDATE tickets
                    SET status='open', updated_at=NOW()
                    WHERE status='failed'
                    AND updated_at > DATE_SUB(NOW(), INTERVAL 1 HOUR)
                """)
                reset_failed = cursor.rowcount

                # Mark orphaned running sessions as stuck
                cursor.execute("""
                    UPDATE execution_sessions
                    SET status='stuck', ended_at=NOW()
                    WHERE status='running'
                """)
                stuck_sessions = cursor.rowcount

                conn.commit()
                cursor.close()
                conn.close()

                if reset_tickets > 0 or reset_failed > 0 or stuck_sessions > 0:
                    self.log(f"Startup recovery: reset {reset_tickets} in_progress, {reset_failed} recently failed ticket(s), marked {stuck_sessions} session(s) as stuck")
                else:
                    self.log("Startup recovery: no orphaned tickets found")
                return

            except Exception as e:
                self.log(f"Startup recovery attempt {attempt + 1}/5 failed: {e}", "WARNING")
                if attempt < 4:
                    time.sleep(2)  # Wait before retry
                else:
                    self.log(f"Startup recovery failed after 5 attempts", "ERROR")

    def run(self):
        self.log(f"Claude Daemon v3 started (user: {os.getenv('USER', 'unknown')})")
        self.log(f"Max parallel projects: {self.max_parallel}")
        
        os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE daemon_status SET status='running', started_at=NOW() WHERE id=1")
            conn.commit()
            cursor.close()
            conn.close()
        except: pass

        # Recover any orphaned tickets from previous run
        self.recover_orphaned_tickets()

        # Start Watchdog thread
        self.watchdog = Watchdog(self)
        self.watchdog.start()
        self.log("Watchdog thread started")

        # Start Telegram Poller thread
        self.telegram_poller = TelegramPoller(self)
        self.telegram_poller.start()

        while self.running:
            try:
                self.cleanup_dead_workers()
                self.auto_close_expired_reviews()
                self.process_scheduled_reviews()  # Auto-review system
                projects = self.get_projects_with_open_tickets()
                
                with self.workers_lock:
                    active_count = len([w for w in self.workers.values() if w.is_alive()])
                
                for project in projects:
                    if active_count >= self.max_parallel:
                        break
                    
                    with self.workers_lock:
                        if project['id'] not in self.workers or not self.workers[project['id']].is_alive():
                            worker = ProjectWorker(
                                self,
                                project['id'],
                                project['name'],
                                project['work_path'],
                                self.global_context,
                                self.context_manager  # Pass Smart Context Manager
                            )
                            worker.start()
                            self.workers[project['id']] = worker
                            active_count += 1
                            self.log(f"Started worker for {project['name']} ({project['open_count']} tickets)")
                
                time.sleep(POLL_INTERVAL)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.log(f"Error: {e}", "ERROR")
                time.sleep(POLL_INTERVAL)
        
        # Stop Watchdog
        if self.watchdog:
            self.log("Stopping Watchdog...")
            self.watchdog.stop()

        # Stop Telegram Poller
        if self.telegram_poller:
            self.log("Stopping Telegram Poller...")
            self.telegram_poller.stop()

        self.log("Stopping all workers...")
        with self.workers_lock:
            for worker in self.workers.values():
                worker.stop()

        for worker in self.workers.values():
            worker.join(timeout=5)
        
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE daemon_status SET status='stopped' WHERE id=1")
            conn.commit()
            cursor.close()
            conn.close()
        except: pass
        
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        self.log("Claude Daemon stopped")


if __name__ == '__main__':
    # Retry startup if MySQL not ready (common after VM restart)
    max_retries = 10
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            daemon = ClaudeDaemon()
            signal.signal(signal.SIGTERM, lambda s, f: setattr(daemon, 'running', False))
            signal.signal(signal.SIGINT, lambda s, f: setattr(daemon, 'running', False))
            daemon.run()
            break
        except mysql.connector.Error as e:
            print(f"[STARTUP] MySQL not ready (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"[STARTUP] Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"[STARTUP] Failed to connect to MySQL after {max_retries} attempts. Exiting.")
                sys.exit(1)
        except Exception as e:
            print(f"[STARTUP] Fatal error: {e}")
            sys.exit(1)
