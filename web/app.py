#!/usr/bin/env python3
"""
Fotios Claude Admin Panel v2
- Projects & Tickets management
- Real-time chat with Claude
- Background daemon control
"""

# Read version from file
try:
    with open('/opt/fotios-claude/VERSION', 'r') as f:
        VERSION = f.read().strip()
except:
    VERSION = "unknown"

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import re
import unicodedata
import mysql.connector
from mysql.connector import pooling
import bcrypt
import os
import pty
import pwd
import select
import struct
import fcntl
import termios
import signal
import subprocess
import threading
import time
import json
import secrets
import string
import zipfile
import tempfile
import shutil
import uuid
import urllib.request
import urllib.error
from datetime import datetime
from functools import wraps
import sys
sys.path.insert(0, '/opt/fotios-claude/scripts')
try:
    from smart_context import SmartContextManager
except ImportError:
    SmartContextManager = None

def to_iso_utc(dt):
    """Convert datetime to ISO format with UTC indicator for JavaScript"""
    if dt is None:
        return None
    return dt.isoformat() + 'Z' if not str(dt).endswith('Z') else dt.isoformat()

def safe_filename(filename):
    """Sanitize filename while preserving unicode characters (Greek, etc.)"""
    # Normalize unicode
    filename = unicodedata.normalize('NFC', filename)
    # Remove path separators and null bytes
    filename = filename.replace('/', '_').replace('\\', '_').replace('\x00', '')
    # Remove .. to prevent directory traversal
    while '..' in filename:
        filename = filename.replace('..', '.')
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    # If empty, generate a random name
    if not filename:
        filename = 'file_' + secrets.token_hex(4)
    return filename

CONFIG_FILE = "/etc/fotios-claude/system.conf"
DAEMON_SCRIPT = "/opt/fotios-claude/scripts/claude-daemon.py"
PID_FILE = "/var/run/fotios-claude/daemon.pid"

app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', allow_upgrades=False)

@app.context_processor
def inject_version():
    return {'version': VERSION}

def load_config():
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip().strip('"').strip("'")
    return config

config = load_config()

try:
    db_pool = pooling.MySQLConnectionPool(
        host=config.get('DB_HOST', 'localhost'),
        user=config.get('DB_USER', 'claude_user'),
        password=config.get('DB_PASSWORD', ''),
        database=config.get('DB_NAME', 'claude_knowledge'),
        pool_name='web_pool',
        pool_size=10
    )
except Exception as e:
    print(f"DB pool error: {e}")
    db_pool = None

def get_db():
    return db_pool.get_connection() if db_pool else None

def create_project_database(code):
    """Create a dedicated database and user for a project.
    Returns (db_name, db_user, db_password) or (None, None, None) on failure."""
    try:
        db_name = f"{code.lower()}_db"
        db_user = f"{code.lower()}_user"
        db_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))

        conn = get_db()
        if not conn:
            return None, None, None

        cursor = conn.cursor()

        # Create database
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")

        # Create user (ignore if exists)
        try:
            cursor.execute(f"CREATE USER '{db_user}'@'localhost' IDENTIFIED BY '{db_password}'")
        except mysql.connector.Error as e:
            if e.errno != 1396:  # User already exists
                raise

        # Grant privileges
        cursor.execute(f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{db_user}'@'localhost'")
        cursor.execute("FLUSH PRIVILEGES")

        conn.commit()
        cursor.close()
        conn.close()

        return db_name, db_user, db_password
    except Exception as e:
        print(f"Database creation failed (insufficient privileges?): {e}")
        return None, None, None

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Not logged in'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def generate_ticket_number(project_code, cursor):
    cursor.execute("""
        SELECT COUNT(*) + 1 as next_num FROM tickets t
        JOIN projects p ON t.project_id = p.id
        WHERE p.code = %s
    """, (project_code,))
    num = cursor.fetchone()['next_num']
    return f"{project_code}-{num:04d}"

# ============ AUTH ROUTES ============

@app.route('/')
def index():
    return redirect(url_for('dashboard') if 'user' in session else url_for('login'))

@app.route('/health')
def health():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        v = cursor.fetchone()[0]
        cursor.close(); conn.close()
        return jsonify({'status': 'ok', 'mysql': v})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        try:
            conn = get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM developers WHERE username = %s AND is_active = TRUE", (username,))
            user = cursor.fetchone()
            cursor.close(); conn.close()
            
            if user and bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
                session['user'] = username
                session['user_id'] = user['id']
                session['role'] = user['role']
                return redirect(url_for('dashboard'))
            return render_template('login.html', error="Invalid credentials")
        except Exception as e:
            return render_template('login.html', error=f"Error: {e}")
    return render_template('login.html', error=None)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ============ DASHBOARD ============

@app.route('/dashboard')
@login_required
def dashboard():
    stats = {'projects': 0, 'open_tickets': 0, 'in_progress': 0, 'awaiting_input': 0,
             'completed_today': 0, 'daemon_status': 'stopped', 'active_workers': [], 'max_workers': 3}
    projects = []
    recent_tickets = []

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) as cnt FROM projects WHERE status = 'active'")
        stats['projects'] = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) as cnt FROM tickets WHERE status IN ('new', 'open', 'pending')")
        stats['open_tickets'] = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) as cnt FROM tickets WHERE status = 'in_progress'")
        stats['in_progress'] = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) as cnt FROM tickets WHERE status = 'awaiting_input'")
        stats['awaiting_input'] = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) as cnt FROM tickets WHERE status = 'done' AND DATE(updated_at) = CURDATE()")
        stats['completed_today'] = cursor.fetchone()['cnt']

        # Daemon status
        if os.path.exists(PID_FILE):
            try:
                with open(PID_FILE) as f:
                    os.kill(int(f.read().strip()), 0)
                stats['daemon_status'] = 'running'
            except: pass

        # Active workers - tickets in progress with project info
        cursor.execute("""
            SELECT t.ticket_number, t.title, p.name as project_name
            FROM tickets t
            JOIN projects p ON t.project_id = p.id
            WHERE t.status = 'in_progress'
            ORDER BY t.updated_at DESC
        """)
        stats['active_workers'] = cursor.fetchall()
        stats['max_workers'] = int(config.get('MAX_PARALLEL_PROJECTS', '3'))

        cursor.execute("SELECT * FROM projects WHERE status = 'active' ORDER BY updated_at DESC LIMIT 10")
        projects = cursor.fetchall()

        cursor.execute("""
            SELECT t.*, p.name as project_name, p.code as project_code
            FROM tickets t JOIN projects p ON t.project_id = p.id
            ORDER BY t.updated_at DESC LIMIT 10
        """)
        recent_tickets = cursor.fetchall()
        
        cursor.close(); conn.close()
    except Exception as e:
        print(f"Dashboard error: {e}")
    
    return render_template('dashboard.html', 
                         user=session['user'], role=session.get('role'),
                         stats=stats, projects=projects, recent_tickets=recent_tickets)

# ============ PROJECTS ============

@app.route('/tickets')
@login_required
def tickets_list():
    """List tickets with optional filtering and search"""
    status_filter = request.args.get('status', '')
    today_only = request.args.get('today', '')
    search_query = request.args.get('q', '').strip()
    tickets = []

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT t.*, p.name as project_name, p.code as project_code
            FROM tickets t
            JOIN projects p ON t.project_id = p.id
            WHERE 1=1
        """
        params = []

        if status_filter:
            if status_filter == 'open':
                query += " AND t.status IN ('new', 'open', 'pending')"
            else:
                query += " AND t.status = %s"
                params.append(status_filter)

        if today_only == '1':
            query += " AND DATE(t.updated_at) = CURDATE()"

        if search_query:
            query += " AND (t.ticket_number LIKE %s OR t.title LIKE %s OR t.description LIKE %s OR p.name LIKE %s OR p.code LIKE %s)"
            search_pattern = f"%{search_query}%"
            params.extend([search_pattern] * 5)

        query += " ORDER BY t.updated_at DESC LIMIT 100"

        cursor.execute(query, params)
        tickets = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Tickets list error: {e}")

    title_map = {
        'open': 'Open Tickets',
        'in_progress': 'In Progress',
        'awaiting_input': 'Awaiting Input',
        'done': 'Completed' + (' Today' if today_only == '1' else ''),
        '': 'All Tickets'
    }
    title = title_map.get(status_filter, f'{status_filter.title()} Tickets')
    if search_query:
        title += f' - Search: "{search_query}"'

    return render_template('tickets_list.html', user=session['user'], role=session.get('role'),
                          tickets=tickets, status_filter=status_filter, title=title, search_query=search_query)

@app.route('/projects')
@login_required
def projects_list():
    projects = []
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT p.*,
                   (SELECT COUNT(*) FROM tickets WHERE project_id = p.id) as ticket_count,
                   (SELECT COUNT(*) FROM tickets WHERE project_id = p.id AND status IN ('new', 'open', 'pending', 'in_progress')) as open_count
            FROM projects p ORDER BY p.updated_at DESC
        """)
        projects = cursor.fetchall()
        cursor.close(); conn.close()
    except Exception as e:
        print(f"Projects error: {e}")
    
    return render_template('projects.html', user=session['user'], role=session.get('role'), projects=projects)

@app.route('/project/<int:project_id>')
@login_required
def project_detail(project_id):
    project = None
    tickets = []
    
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
        project = cursor.fetchone()
        
        cursor.execute("""
            SELECT * FROM tickets WHERE project_id = %s ORDER BY 
            CASE status WHEN 'in_progress' THEN 1 WHEN 'open' THEN 2 WHEN 'new' THEN 3 ELSE 4 END,
            updated_at DESC
        """, (project_id,))
        tickets = cursor.fetchall()
        
        cursor.close(); conn.close()
    except Exception as e:
        print(f"Project detail error: {e}")
    
    return render_template('project_detail.html', user=session['user'], role=session.get('role'),
                         project=project, tickets=tickets)

@app.route('/api/project/<int:project_id>/archive', methods=['POST'])
@login_required
def archive_project(project_id):
    """Archive a project (close)"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE projects SET status = 'archived', updated_at = NOW() WHERE id = %s", (project_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/project/<int:project_id>/reopen', methods=['POST'])
@login_required
def reopen_project(project_id):
    """Reopen an archived project"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE projects SET status = 'active', updated_at = NOW() WHERE id = %s", (project_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/project/<int:project_id>/export', methods=['GET'])
@login_required
def export_project(project_id):
    """Export project files and database as a zip file"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
        project = cursor.fetchone()
        cursor.close()
        conn.close()

        if not project:
            return jsonify({'success': False, 'message': 'Project not found'}), 404

        # Create temp directory for export
        temp_dir = tempfile.mkdtemp()
        export_name = f"{project['code']}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        export_path = os.path.join(temp_dir, export_name)
        os.makedirs(export_path)

        try:
            # Copy web folder
            if project.get('web_path') and os.path.exists(project['web_path']):
                web_dest = os.path.join(export_path, 'web')
                shutil.copytree(project['web_path'], web_dest, dirs_exist_ok=True)

            # Copy app folder
            if project.get('app_path') and os.path.exists(project['app_path']):
                app_dest = os.path.join(export_path, 'app')
                shutil.copytree(project['app_path'], app_dest, dirs_exist_ok=True)

            # Export database if exists
            if project.get('db_name') and project.get('db_user') and project.get('db_password'):
                db_dir = os.path.join(export_path, 'database')
                os.makedirs(db_dir, exist_ok=True)

                db_host = project.get('db_host', 'localhost')
                db_name = project['db_name']
                db_user = project['db_user']
                db_pass = project['db_password']

                # Export schema (structure only)
                schema_file = os.path.join(db_dir, 'schema.sql')
                schema_cmd = f"mysqldump -h {db_host} -u {db_user} -p'{db_pass}' --no-data {db_name}"
                result = subprocess.run(schema_cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    with open(schema_file, 'w') as f:
                        f.write(result.stdout)

                # Export data only
                data_file = os.path.join(db_dir, 'data.sql')
                data_cmd = f"mysqldump -h {db_host} -u {db_user} -p'{db_pass}' --no-create-info {db_name}"
                result = subprocess.run(data_cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    with open(data_file, 'w') as f:
                        f.write(result.stdout)

            # Create project info file
            info_file = os.path.join(export_path, 'project_info.json')
            project_info = {
                'name': project['name'],
                'code': project['code'],
                'description': project.get('description'),
                'project_type': project.get('project_type'),
                'tech_stack': project.get('tech_stack'),
                'web_path': project.get('web_path'),
                'app_path': project.get('app_path'),
                'db_name': project.get('db_name'),
                'db_user': project.get('db_user'),
                'db_host': project.get('db_host', 'localhost'),
                'preview_url': project.get('preview_url'),
                'exported_at': datetime.now().isoformat()
            }
            with open(info_file, 'w') as f:
                json.dump(project_info, f, indent=2, ensure_ascii=False)

            # Create zip file
            zip_path = os.path.join(temp_dir, f"{export_name}.zip")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(export_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, export_path)
                        zipf.write(file_path, arc_name)

            # Send file and cleanup after
            return send_file(
                zip_path,
                mimetype='application/zip',
                as_attachment=True,
                download_name=f"{export_name}.zip"
            )

        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise e

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ============ DATABASE EDITOR ============

def get_project_db_connection(project_id):
    """Get a database connection for a project's database"""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT db_name, db_user, db_password, db_host FROM projects WHERE id = %s", (project_id,))
    project = cursor.fetchone()
    cursor.close()
    conn.close()

    if not project or not project.get('db_name'):
        return None, "Project has no database configured"

    try:
        db_conn = mysql.connector.connect(
            host=project.get('db_host', 'localhost'),
            user=project['db_user'],
            password=project['db_password'],
            database=project['db_name']
        )
        return db_conn, None
    except Exception as e:
        return None, str(e)


@app.route('/api/project/<int:project_id>/db/tables', methods=['GET'])
@login_required
def get_db_tables(project_id):
    """Get list of tables in project database"""
    db_conn, error = get_project_db_connection(project_id)
    if error:
        return jsonify({'success': False, 'message': error})

    try:
        cursor = db_conn.cursor(dictionary=True)
        cursor.execute("SHOW TABLES")
        tables = [list(row.values())[0] for row in cursor.fetchall()]

        # Get row counts for each table
        table_info = []
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) as count FROM `{table}`")
            count = cursor.fetchone()['count']
            table_info.append({'name': table, 'rows': count})

        cursor.close()
        db_conn.close()
        return jsonify({'success': True, 'tables': table_info})
    except Exception as e:
        db_conn.close()
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/project/<int:project_id>/db/table/<table_name>/structure', methods=['GET'])
@login_required
def get_table_structure(project_id, table_name):
    """Get table structure (columns, types, keys)"""
    db_conn, error = get_project_db_connection(project_id)
    if error:
        return jsonify({'success': False, 'message': error})

    try:
        cursor = db_conn.cursor(dictionary=True)
        cursor.execute(f"DESCRIBE `{table_name}`")
        columns = cursor.fetchall()

        # Get indexes
        cursor.execute(f"SHOW INDEX FROM `{table_name}`")
        indexes = cursor.fetchall()

        cursor.close()
        db_conn.close()
        return jsonify({'success': True, 'columns': columns, 'indexes': indexes})
    except Exception as e:
        db_conn.close()
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/project/<int:project_id>/db/table/<table_name>/data', methods=['GET'])
@login_required
def get_table_data(project_id, table_name):
    """Get table data with pagination"""
    db_conn, error = get_project_db_connection(project_id)
    if error:
        return jsonify({'success': False, 'message': error})

    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    offset = (page - 1) * per_page

    try:
        cursor = db_conn.cursor(dictionary=True)

        # Get total count
        cursor.execute(f"SELECT COUNT(*) as total FROM `{table_name}`")
        total = cursor.fetchone()['total']

        # Get data
        cursor.execute(f"SELECT * FROM `{table_name}` LIMIT %s OFFSET %s", (per_page, offset))
        rows = cursor.fetchall()

        # Convert datetime objects to strings
        for row in rows:
            for key, value in row.items():
                if isinstance(value, datetime):
                    row[key] = value.isoformat()
                elif isinstance(value, bytes):
                    row[key] = value.decode('utf-8', errors='replace')

        cursor.close()
        db_conn.close()
        return jsonify({
            'success': True,
            'rows': rows,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        })
    except Exception as e:
        db_conn.close()
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/project/<int:project_id>/db/query', methods=['POST'])
@login_required
def run_db_query(project_id):
    """Run a custom SQL query"""
    db_conn, error = get_project_db_connection(project_id)
    if error:
        return jsonify({'success': False, 'message': error})

    data = request.json
    query = data.get('query', '').strip()

    if not query:
        return jsonify({'success': False, 'message': 'No query provided'})

    # Check for dangerous operations
    query_upper = query.upper()
    if any(cmd in query_upper for cmd in ['DROP DATABASE', 'DROP SCHEMA']):
        return jsonify({'success': False, 'message': 'DROP DATABASE is not allowed'})

    try:
        cursor = db_conn.cursor(dictionary=True)
        cursor.execute(query)

        # Check if it's a SELECT query
        if query_upper.startswith('SELECT') or query_upper.startswith('SHOW') or query_upper.startswith('DESCRIBE'):
            rows = cursor.fetchall()
            # Convert datetime objects
            for row in rows:
                for key, value in row.items():
                    if isinstance(value, datetime):
                        row[key] = value.isoformat()
                    elif isinstance(value, bytes):
                        row[key] = value.decode('utf-8', errors='replace')

            cursor.close()
            db_conn.close()
            return jsonify({'success': True, 'rows': rows, 'affected': len(rows)})
        else:
            # For INSERT, UPDATE, DELETE
            db_conn.commit()
            affected = cursor.rowcount
            cursor.close()
            db_conn.close()
            return jsonify({'success': True, 'affected': affected, 'message': f'{affected} row(s) affected'})

    except Exception as e:
        db_conn.close()
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/project/<int:project_id>/db/table/<table_name>/row', methods=['DELETE'])
@login_required
def delete_table_row(project_id, table_name):
    """Delete a row from table"""
    db_conn, error = get_project_db_connection(project_id)
    if error:
        return jsonify({'success': False, 'message': error})

    data = request.json
    where_clause = data.get('where', {})

    if not where_clause:
        return jsonify({'success': False, 'message': 'No WHERE clause provided'})

    try:
        cursor = db_conn.cursor()
        conditions = ' AND '.join([f"`{k}` = %s" for k in where_clause.keys()])
        values = list(where_clause.values())

        cursor.execute(f"DELETE FROM `{table_name}` WHERE {conditions} LIMIT 1", values)
        db_conn.commit()
        affected = cursor.rowcount

        cursor.close()
        db_conn.close()
        return jsonify({'success': True, 'affected': affected})
    except Exception as e:
        db_conn.close()
        return jsonify({'success': False, 'message': str(e)})


# ============ FILE EDITOR ============

def get_project_path(project_id):
    """Get project base path"""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT web_path, app_path FROM projects WHERE id = %s", (project_id,))
    project = cursor.fetchone()
    cursor.close()
    conn.close()

    if not project:
        return None
    return project.get('web_path') or project.get('app_path')


@app.route('/project/<int:project_id>/files')
@login_required
def project_files_popup(project_id):
    """File explorer popup window"""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
    project = cursor.fetchone()
    cursor.close()
    conn.close()

    if not project:
        return "Project not found", 404

    return render_template('file_explorer.html', project=project)


@app.route('/project/<int:project_id>/editor')
@login_required
def project_editor(project_id):
    """File editor page"""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
    project = cursor.fetchone()
    cursor.close()
    conn.close()

    if not project:
        return "Project not found", 404

    return render_template('editor.html', project=project)


@app.route('/api/project/<int:project_id>/editor/tree', methods=['GET'])
@login_required
def get_file_tree(project_id):
    """Get recursive file tree"""
    base_path = get_project_path(project_id)
    if not base_path:
        return jsonify({'success': False, 'message': 'Project path not configured'})

    if not os.path.exists(base_path):
        return jsonify({'success': False, 'message': 'Project path does not exist'})

    def build_tree(path, rel_path=''):
        items = []
        try:
            entries = sorted(os.listdir(path), key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))
            for entry in entries:
                # Skip hidden and common ignored files
                if entry.startswith('.') or entry in ['node_modules', '__pycache__', 'vendor', '.git']:
                    continue

                full_path = os.path.join(path, entry)
                entry_rel = os.path.join(rel_path, entry) if rel_path else entry

                if os.path.isdir(full_path):
                    items.append({
                        'name': entry,
                        'path': entry_rel,
                        'type': 'dir',
                        'children': build_tree(full_path, entry_rel)
                    })
                else:
                    items.append({
                        'name': entry,
                        'path': entry_rel,
                        'type': 'file',
                        'size': os.path.getsize(full_path)
                    })
        except PermissionError:
            pass
        return items

    tree = build_tree(base_path)
    return jsonify({'success': True, 'tree': tree, 'base_path': base_path})


@app.route('/api/project/<int:project_id>/editor/file', methods=['GET'])
@login_required
def get_file_content(project_id):
    """Get file content"""
    base_path = get_project_path(project_id)
    if not base_path:
        return jsonify({'success': False, 'message': 'Project path not configured'})

    file_path = request.args.get('path', '')
    if not file_path:
        return jsonify({'success': False, 'message': 'No file path provided'})

    # Security: prevent path traversal
    full_path = os.path.normpath(os.path.join(base_path, file_path))
    if not full_path.startswith(os.path.normpath(base_path)):
        return jsonify({'success': False, 'message': 'Invalid path'})

    if not os.path.exists(full_path):
        return jsonify({'success': False, 'message': 'File not found'})

    if not os.path.isfile(full_path):
        return jsonify({'success': False, 'message': 'Not a file'})

    # Check file size (limit to 2MB)
    if os.path.getsize(full_path) > 2 * 1024 * 1024:
        return jsonify({'success': False, 'message': 'File too large (max 2MB)'})

    try:
        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        return jsonify({'success': True, 'content': content, 'path': file_path})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/project/<int:project_id>/editor/file', methods=['POST'])
@login_required
def save_file_content(project_id):
    """Save file content"""
    base_path = get_project_path(project_id)
    if not base_path:
        return jsonify({'success': False, 'message': 'Project path not configured'})

    data = request.json
    file_path = data.get('path', '')
    content = data.get('content', '')

    if not file_path:
        return jsonify({'success': False, 'message': 'No file path provided'})

    # Security: prevent path traversal
    full_path = os.path.normpath(os.path.join(base_path, file_path))
    if not full_path.startswith(os.path.normpath(base_path)):
        return jsonify({'success': False, 'message': 'Invalid path'})

    try:
        # Create parent directories if needed
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({'success': True, 'message': 'File saved'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/project/<int:project_id>/editor/create', methods=['POST'])
@login_required
def create_file_or_folder(project_id):
    """Create new file or folder"""
    base_path = get_project_path(project_id)
    if not base_path:
        return jsonify({'success': False, 'message': 'Project path not configured'})

    data = request.json
    path = data.get('path', '')
    item_type = data.get('type', 'file')  # 'file' or 'dir'

    if not path:
        return jsonify({'success': False, 'message': 'No path provided'})

    # Security: prevent path traversal
    full_path = os.path.normpath(os.path.join(base_path, path))
    if not full_path.startswith(os.path.normpath(base_path)):
        return jsonify({'success': False, 'message': 'Invalid path'})

    if os.path.exists(full_path):
        return jsonify({'success': False, 'message': 'Already exists'})

    try:
        if item_type == 'dir':
            os.makedirs(full_path)
        else:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as f:
                f.write('')
        return jsonify({'success': True, 'message': f'{item_type.capitalize()} created'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/project/<int:project_id>/editor/rename', methods=['POST'])
@login_required
def rename_file_or_folder(project_id):
    """Rename file or folder"""
    base_path = get_project_path(project_id)
    if not base_path:
        return jsonify({'success': False, 'message': 'Project path not configured'})

    data = request.json
    old_path = data.get('old_path', '')
    new_path = data.get('new_path', '')

    if not old_path or not new_path:
        return jsonify({'success': False, 'message': 'Paths required'})

    # Security: prevent path traversal
    old_full = os.path.normpath(os.path.join(base_path, old_path))
    new_full = os.path.normpath(os.path.join(base_path, new_path))

    if not old_full.startswith(os.path.normpath(base_path)) or not new_full.startswith(os.path.normpath(base_path)):
        return jsonify({'success': False, 'message': 'Invalid path'})

    if not os.path.exists(old_full):
        return jsonify({'success': False, 'message': 'Source not found'})

    if os.path.exists(new_full):
        return jsonify({'success': False, 'message': 'Destination already exists'})

    try:
        os.rename(old_full, new_full)
        return jsonify({'success': True, 'message': 'Renamed successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# ============ BACKUP & RESTORE ============

BACKUP_DIR = "/var/backups/fotios-claude"
MAX_BACKUPS = 30


def create_project_backup(project_id, trigger='manual'):
    """Create a backup of project files and database.
    Returns (success, message, backup_filename)
    """
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
        project = cursor.fetchone()
        cursor.close()
        conn.close()

        if not project:
            return False, "Project not found", None

        project_code = project['code']
        backup_subdir = os.path.join(BACKUP_DIR, project_code)
        os.makedirs(backup_subdir, exist_ok=True)

        # Create backup filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{project_code}_{timestamp}_{trigger}.zip"
        backup_path = os.path.join(backup_subdir, backup_name)

        # Create temp directory for backup contents
        temp_dir = tempfile.mkdtemp()
        temp_backup = os.path.join(temp_dir, 'backup')
        os.makedirs(temp_backup)

        try:
            # Copy web folder
            if project.get('web_path') and os.path.exists(project['web_path']):
                web_dest = os.path.join(temp_backup, 'web')
                shutil.copytree(project['web_path'], web_dest, dirs_exist_ok=True)

            # Copy app folder
            if project.get('app_path') and os.path.exists(project['app_path']):
                app_dest = os.path.join(temp_backup, 'app')
                shutil.copytree(project['app_path'], app_dest, dirs_exist_ok=True)

            # Export database if exists
            if project.get('db_name') and project.get('db_user') and project.get('db_password'):
                db_dir = os.path.join(temp_backup, 'database')
                os.makedirs(db_dir, exist_ok=True)

                db_host = project.get('db_host', 'localhost')
                db_name = project['db_name']
                db_user = project['db_user']
                db_pass = project['db_password']

                # Export schema
                schema_file = os.path.join(db_dir, 'schema.sql')
                schema_cmd = f"mysqldump -h {db_host} -u {db_user} -p'{db_pass}' --no-data {db_name} 2>/dev/null"
                result = subprocess.run(schema_cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    with open(schema_file, 'w') as f:
                        f.write(result.stdout)

                # Export data
                data_file = os.path.join(db_dir, 'data.sql')
                data_cmd = f"mysqldump -h {db_host} -u {db_user} -p'{db_pass}' --no-create-info {db_name} 2>/dev/null"
                result = subprocess.run(data_cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    with open(data_file, 'w') as f:
                        f.write(result.stdout)

            # Create backup info
            info_file = os.path.join(temp_backup, 'backup_info.json')
            backup_info = {
                'project_id': project_id,
                'project_code': project_code,
                'project_name': project['name'],
                'trigger': trigger,
                'created_at': datetime.now().isoformat(),
                'web_path': project.get('web_path'),
                'app_path': project.get('app_path'),
                'db_name': project.get('db_name')
            }
            with open(info_file, 'w') as f:
                json.dump(backup_info, f, indent=2)

            # Create zip
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_backup):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, temp_backup)
                        zipf.write(file_path, arc_name)

            # Cleanup old backups (keep last MAX_BACKUPS)
            cleanup_old_backups(backup_subdir)

            return True, f"Backup created: {backup_name}", backup_name

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    except Exception as e:
        return False, str(e), None


def cleanup_old_backups(backup_dir):
    """Remove old backups, keep only MAX_BACKUPS most recent"""
    try:
        backups = sorted(
            [f for f in os.listdir(backup_dir) if f.endswith('.zip')],
            key=lambda x: os.path.getmtime(os.path.join(backup_dir, x)),
            reverse=True
        )
        for old_backup in backups[MAX_BACKUPS:]:
            os.remove(os.path.join(backup_dir, old_backup))
    except Exception:
        pass


def restore_project_backup(project_id, backup_filename):
    """Restore project from a backup file"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
        project = cursor.fetchone()
        cursor.close()
        conn.close()

        if not project:
            return False, "Project not found"

        project_code = project['code']
        backup_path = os.path.join(BACKUP_DIR, project_code, backup_filename)

        if not os.path.exists(backup_path):
            return False, "Backup file not found"

        # Extract to temp directory
        temp_dir = tempfile.mkdtemp()

        try:
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(temp_dir)

            # Restore web folder
            web_backup = os.path.join(temp_dir, 'web')
            if os.path.exists(web_backup) and project.get('web_path'):
                # Clear existing and copy
                if os.path.exists(project['web_path']):
                    shutil.rmtree(project['web_path'])
                shutil.copytree(web_backup, project['web_path'])

            # Restore app folder
            app_backup = os.path.join(temp_dir, 'app')
            if os.path.exists(app_backup) and project.get('app_path'):
                if os.path.exists(project['app_path']):
                    shutil.rmtree(project['app_path'])
                shutil.copytree(app_backup, project['app_path'])

            # Restore database
            db_dir = os.path.join(temp_dir, 'database')
            if os.path.exists(db_dir) and project.get('db_name'):
                db_host = project.get('db_host', 'localhost')
                db_name = project['db_name']
                db_user = project['db_user']
                db_pass = project['db_password']

                # Restore schema first
                schema_file = os.path.join(db_dir, 'schema.sql')
                if os.path.exists(schema_file):
                    cmd = f"mysql -h {db_host} -u {db_user} -p'{db_pass}' {db_name} < {schema_file} 2>/dev/null"
                    subprocess.run(cmd, shell=True)

                # Restore data
                data_file = os.path.join(db_dir, 'data.sql')
                if os.path.exists(data_file):
                    cmd = f"mysql -h {db_host} -u {db_user} -p'{db_pass}' {db_name} < {data_file} 2>/dev/null"
                    subprocess.run(cmd, shell=True)

            return True, "Restore completed successfully"

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    except Exception as e:
        return False, str(e)


@app.route('/api/project/<int:project_id>/backup', methods=['POST'])
@login_required
def api_create_backup(project_id):
    """Create a manual backup"""
    success, message, filename = create_project_backup(project_id, 'manual')
    return jsonify({'success': success, 'message': message, 'filename': filename})


@app.route('/api/project/<int:project_id>/backups', methods=['GET'])
@login_required
def api_list_backups(project_id):
    """List available backups for a project"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT code FROM projects WHERE id = %s", (project_id,))
        project = cursor.fetchone()
        cursor.close()
        conn.close()

        if not project:
            return jsonify({'success': False, 'message': 'Project not found'})

        backup_dir = os.path.join(BACKUP_DIR, project['code'])
        if not os.path.exists(backup_dir):
            return jsonify({'success': True, 'backups': []})

        backups = []
        for f in sorted(os.listdir(backup_dir), reverse=True):
            if f.endswith('.zip'):
                path = os.path.join(backup_dir, f)
                stat = os.stat(path)
                # Parse filename: {code}_{timestamp}_{trigger}.zip
                parts = f.replace('.zip', '').split('_')
                trigger = parts[-1] if len(parts) > 3 else 'unknown'

                backups.append({
                    'filename': f,
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'trigger': trigger
                })

        return jsonify({'success': True, 'backups': backups})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/project/<int:project_id>/restore', methods=['POST'])
@login_required
def api_restore_backup(project_id):
    """Restore from a backup"""
    data = request.json
    filename = data.get('filename')

    if not filename:
        return jsonify({'success': False, 'message': 'No backup filename provided'})

    # Create a backup before restore (safety)
    create_project_backup(project_id, 'pre-restore')

    success, message = restore_project_backup(project_id, filename)
    return jsonify({'success': success, 'message': message})


@app.route('/api/project/<int:project_id>/backup/<filename>', methods=['GET'])
@login_required
def api_download_backup(project_id, filename):
    """Download a backup file"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT code FROM projects WHERE id = %s", (project_id,))
        project = cursor.fetchone()
        cursor.close()
        conn.close()

        if not project:
            return jsonify({'success': False, 'message': 'Project not found'}), 404

        backup_path = os.path.join(BACKUP_DIR, project['code'], filename)

        if not os.path.exists(backup_path):
            return jsonify({'success': False, 'message': 'Backup not found'}), 404

        return send_file(backup_path, as_attachment=True, download_name=filename)

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/project/<int:project_id>/backup/<filename>', methods=['DELETE'])
@login_required
def api_delete_backup(project_id, filename):
    """Delete a backup file"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT code FROM projects WHERE id = %s", (project_id,))
        project = cursor.fetchone()
        cursor.close()
        conn.close()

        if not project:
            return jsonify({'success': False, 'message': 'Project not found'})

        backup_path = os.path.join(BACKUP_DIR, project['code'], filename)

        if os.path.exists(backup_path):
            os.remove(backup_path)
            return jsonify({'success': True, 'message': 'Backup deleted'})
        else:
            return jsonify({'success': False, 'message': 'Backup not found'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/project/<int:project_id>/upload', methods=['POST'])
@login_required
def upload_file(project_id):
    """Upload file(s) to project directory"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT web_path, app_path, code FROM projects WHERE id = %s", (project_id,))
        project = cursor.fetchone()
        cursor.close()
        conn.close()

        if not project:
            return jsonify({'success': False, 'message': 'Project not found'}), 404

        # Determine upload directory
        upload_dir = project.get('web_path') or project.get('app_path')
        if not upload_dir:
            return jsonify({'success': False, 'message': 'No project path configured'})

        # Get optional subdirectory
        subdir = request.form.get('subdir', '').strip().strip('/')
        if subdir:
            upload_dir = os.path.join(upload_dir, subdir)

        # Create directory if needed
        os.makedirs(upload_dir, exist_ok=True)

        if 'files' not in request.files:
            return jsonify({'success': False, 'message': 'No files provided'})

        files = request.files.getlist('files')
        uploaded = []

        for file in files:
            if file.filename:
                filename = safe_filename(file.filename)
                filepath = os.path.join(upload_dir, filename)
                file.save(filepath)
                uploaded.append(filename)

        # If ticket_id provided, save message to conversation
        ticket_id = request.form.get('ticket_id')
        if ticket_id and uploaded:
            try:
                conn2 = get_db()
                cursor2 = conn2.cursor()
                file_list = ', '.join(uploaded)
                msg = f"[Uploaded files to ticket_files/: {file_list}]"
                msg_tokens = len(msg.encode('utf-8')) // 4
                cursor2.execute(
                    "INSERT INTO conversation_messages (ticket_id, role, content, token_count) VALUES (%s, 'user', %s, %s)",
                    (ticket_id, msg, msg_tokens)
                )
                cursor2.execute("UPDATE tickets SET total_tokens = total_tokens + %s WHERE id = %s", (msg_tokens, ticket_id))
                conn2.commit()
                cursor2.close()
                conn2.close()
                # Emit to websocket
                socketio.emit('new_message', {
                    'ticket_id': int(ticket_id),
                    'role': 'user',
                    'content': msg
                }, room=f'ticket_{ticket_id}')
            except Exception as e:
                print(f"Error saving upload message: {e}")

        return jsonify({
            'success': True,
            'uploaded': uploaded,
            'directory': upload_dir,
            'count': len(uploaded)
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/project/<int:project_id>/files', methods=['GET'])
@login_required
def list_files(project_id):
    """List files in project directory"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT web_path, app_path FROM projects WHERE id = %s", (project_id,))
        project = cursor.fetchone()
        cursor.close()
        conn.close()

        if not project:
            return jsonify({'success': False, 'message': 'Project not found'}), 404

        base_path = project.get('web_path') or project.get('app_path')
        if not base_path or not os.path.exists(base_path):
            return jsonify({'success': True, 'files': [], 'base_path': base_path})

        subdir = request.args.get('subdir', '').strip().strip('/')
        current_path = os.path.join(base_path, subdir) if subdir else base_path

        if not os.path.exists(current_path):
            return jsonify({'success': True, 'files': [], 'base_path': base_path, 'current_path': current_path})

        files = []
        for item in sorted(os.listdir(current_path)):
            item_path = os.path.join(current_path, item)
            rel_path = os.path.join(subdir, item) if subdir else item
            stat = os.stat(item_path)
            files.append({
                'name': item,
                'path': rel_path,
                'is_dir': os.path.isdir(item_path),
                'size': stat.st_size if not os.path.isdir(item_path) else None,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })

        # Sort: directories first, then files
        files.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))

        return jsonify({
            'success': True,
            'files': files,
            'base_path': base_path,
            'current_path': current_path,
            'subdir': subdir
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/project/<int:project_id>/files/delete', methods=['POST'])
@login_required
def delete_file(project_id):
    """Delete a file from project directory"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT web_path, app_path FROM projects WHERE id = %s", (project_id,))
        project = cursor.fetchone()
        cursor.close()
        conn.close()

        if not project:
            return jsonify({'success': False, 'message': 'Project not found'}), 404

        base_path = project.get('web_path') or project.get('app_path')
        if not base_path:
            return jsonify({'success': False, 'message': 'No project path configured'})

        data = request.get_json()
        file_path = data.get('path', '').strip().strip('/')

        if not file_path:
            return jsonify({'success': False, 'message': 'No file path provided'})

        # Security: prevent path traversal
        full_path = os.path.abspath(os.path.join(base_path, file_path))
        if not full_path.startswith(os.path.abspath(base_path)):
            return jsonify({'success': False, 'message': 'Invalid path'})

        if not os.path.exists(full_path):
            return jsonify({'success': False, 'message': 'File not found'})

        if os.path.isdir(full_path):
            import shutil
            shutil.rmtree(full_path)
        else:
            os.remove(full_path)

        return jsonify({'success': True, 'deleted': file_path})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/projects', methods=['GET', 'POST'])
@login_required
def api_projects():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        data = request.get_json()
        name = data.get('name', '').strip()
        code = data.get('code', '').strip().upper()
        description = data.get('description', '').strip()
        project_type = data.get('project_type', 'web')
        tech_stack = data.get('tech_stack', '').strip()
        web_path = data.get('web_path', '').strip()
        app_path = data.get('app_path', '').strip()
        preview_url = data.get('preview_url', '').strip()
        context = data.get('context', '').strip()
        ai_model = data.get('ai_model', 'sonnet')
        skip_database = data.get('skip_database', False)

        # Validate ai_model
        if ai_model not in ('opus', 'sonnet', 'haiku'):
            ai_model = 'sonnet'

        if not name or not code:
            return jsonify({'success': False, 'message': 'Name and code required'})

        if not code.isalnum() or len(code) > 10:
            return jsonify({'success': False, 'message': 'Code must be alphanumeric, max 10 chars'})

        # Default paths based on type
        if not web_path and project_type in ('web', 'hybrid'):
            web_path = f'/var/www/projects/{code.lower()}'
        if not app_path and project_type in ('app', 'hybrid', 'api'):
            app_path = f'/opt/apps/{code.lower()}'

        # Auto-create project database unless skipped
        db_name, db_user, db_password = None, None, None
        db_warning = None
        if not skip_database:
            db_name, db_user, db_password = create_project_database(code)
            if not db_name:
                db_warning = 'Database creation failed (insufficient privileges). Project created without database.'

        try:
            cursor.execute("""
                INSERT INTO projects (name, code, description, project_type, tech_stack,
                    web_path, app_path, preview_url, context, db_name, db_user, db_password, db_host,
                    ai_model, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'localhost', %s, 'active', NOW(), NOW())
            """, (name, code, description, project_type, tech_stack or None,
                  web_path or None, app_path or None, preview_url or None, context or None,
                  db_name, db_user, db_password, ai_model))
            conn.commit()
            project_id = cursor.lastrowid

            # Create directories
            if web_path:
                os.makedirs(web_path, exist_ok=True)
            if app_path:
                os.makedirs(app_path, exist_ok=True)

            cursor.close(); conn.close()

            result = {'success': True, 'project_id': project_id, 'message': 'Project created'}
            if db_name:
                result['db_created'] = True
                result['db_name'] = db_name
                result['db_user'] = db_user
            if db_warning:
                result['warning'] = db_warning
            return jsonify(result)
        except Exception as e:
            cursor.close(); conn.close()
            return jsonify({'success': False, 'message': str(e)})
    
    # GET
    cursor.execute("""
        SELECT p.*, (SELECT COUNT(*) FROM tickets WHERE project_id = p.id) as ticket_count
        FROM projects p ORDER BY p.updated_at DESC
    """)
    projects = cursor.fetchall()
    cursor.close(); conn.close()
    
    for p in projects:
        for k, v in p.items():
            if hasattr(v, 'isoformat'): p[k] = v.isoformat()
    
    return jsonify(projects)

@app.route('/api/project/<int:project_id>', methods=['GET', 'PUT'])
@login_required
def api_project_detail(project_id):
    """Get or update a single project"""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'GET':
        cursor.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
        project = cursor.fetchone()
        cursor.close(); conn.close()

        if not project:
            return jsonify({'success': False, 'message': 'Project not found'}), 404

        for k, v in project.items():
            if hasattr(v, 'isoformat'): project[k] = v.isoformat()
        return jsonify(project)

    # PUT - Update project
    data = request.get_json()

    # Fields that can be updated
    updates = []
    params = []

    if 'name' in data:
        updates.append("name = %s")
        params.append(data['name'].strip())
    if 'description' in data:
        updates.append("description = %s")
        params.append(data['description'].strip())
    if 'project_type' in data:
        updates.append("project_type = %s")
        params.append(data['project_type'])
    if 'tech_stack' in data:
        updates.append("tech_stack = %s")
        params.append(data['tech_stack'].strip() or None)
    if 'web_path' in data:
        updates.append("web_path = %s")
        params.append(data['web_path'].strip() or None)
    if 'app_path' in data:
        updates.append("app_path = %s")
        params.append(data['app_path'].strip() or None)
    if 'context' in data:
        updates.append("context = %s")
        params.append(data['context'].strip() or None)
    if 'db_host' in data:
        updates.append("db_host = %s")
        params.append(data['db_host'].strip() or 'localhost')
    if 'db_name' in data:
        updates.append("db_name = %s")
        params.append(data['db_name'].strip() or None)
    if 'db_user' in data:
        updates.append("db_user = %s")
        params.append(data['db_user'].strip() or None)
    if 'db_password' in data:
        updates.append("db_password = %s")
        params.append(data['db_password'] or None)
    if 'preview_url' in data:
        updates.append("preview_url = %s")
        params.append(data['preview_url'].strip() or None)
    if 'ai_model' in data:
        ai_model = data['ai_model']
        if ai_model in ('opus', 'sonnet', 'haiku'):
            updates.append("ai_model = %s")
            params.append(ai_model)

    if not updates:
        cursor.close(); conn.close()
        return jsonify({'success': False, 'message': 'No fields to update'})

    updates.append("updated_at = NOW()")
    params.append(project_id)

    try:
        cursor.execute(f"UPDATE projects SET {', '.join(updates)} WHERE id = %s", params)
        conn.commit()
        cursor.close(); conn.close()
        return jsonify({'success': True, 'message': 'Project updated'})
    except Exception as e:
        cursor.close(); conn.close()
        return jsonify({'success': False, 'message': str(e)})


# ============ TICKETS ============

@app.route('/ticket/<int:ticket_id>')
@login_required
def ticket_detail(ticket_id):
    ticket = None
    project = None
    messages = []
    
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT t.*, p.name as project_name, p.code as project_code,
                   COALESCE(p.web_path, p.app_path) as project_path,
                   p.preview_url, p.ai_model as project_ai_model
            FROM tickets t JOIN projects p ON t.project_id = p.id
            WHERE t.id = %s
        """, (ticket_id,))
        ticket = cursor.fetchone()

        if ticket:
            # Generate default preview_url if not set
            if not ticket.get('preview_url') and ticket.get('project_code'):
                host = request.host.split(':')[0]  # Get hostname without port
                ticket['preview_url'] = f"https://{host}:9867/{ticket['project_code'].lower()}"
            cursor.execute("""
                SELECT * FROM conversation_messages 
                WHERE ticket_id = %s ORDER BY created_at ASC
            """, (ticket_id,))
            messages = cursor.fetchall()
        
        cursor.close(); conn.close()
    except Exception as e:
        print(f"Ticket detail error: {e}")
    
    return render_template('ticket_detail.html', user=session['user'], role=session.get('role'),
                         ticket=ticket, messages=messages)

@app.route('/api/tickets', methods=['GET', 'POST'])
@login_required
def api_tickets():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        data = request.get_json()
        project_id = data.get('project_id')
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        priority = data.get('priority', 'medium')
        ai_model = data.get('ai_model')  # None = inherit from project

        # Validate ai_model
        if ai_model and ai_model not in ('opus', 'sonnet', 'haiku'):
            ai_model = None

        if not project_id or not title:
            return jsonify({'success': False, 'message': 'Project and title required'})

        try:
            # Get project code
            cursor.execute("SELECT code FROM projects WHERE id = %s", (project_id,))
            project = cursor.fetchone()
            if not project:
                return jsonify({'success': False, 'message': 'Project not found'})

            ticket_number = generate_ticket_number(project['code'], cursor)

            cursor.execute("""
                INSERT INTO tickets (project_id, ticket_number, title, description, priority, ai_model, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, 'open', NOW(), NOW())
            """, (project_id, ticket_number, title, description, priority, ai_model))
            conn.commit()
            ticket_id = cursor.lastrowid
            
            cursor.close(); conn.close()
            return jsonify({'success': True, 'ticket_id': ticket_id, 'ticket_number': ticket_number})
        except Exception as e:
            cursor.close(); conn.close()
            return jsonify({'success': False, 'message': str(e)})
    
    # GET
    project_id = request.args.get('project_id')
    if project_id:
        cursor.execute("""
            SELECT t.*, p.name as project_name FROM tickets t 
            JOIN projects p ON t.project_id = p.id 
            WHERE t.project_id = %s ORDER BY t.updated_at DESC
        """, (project_id,))
    else:
        cursor.execute("""
            SELECT t.*, p.name as project_name FROM tickets t 
            JOIN projects p ON t.project_id = p.id ORDER BY t.updated_at DESC
        """)
    
    tickets = cursor.fetchall()
    cursor.close(); conn.close()
    
    for t in tickets:
        for k, v in t.items():
            if hasattr(v, 'isoformat'): t[k] = v.isoformat()
    
    return jsonify(tickets)

@app.route('/api/ticket/<int:ticket_id>/close', methods=['POST'])
@login_required
def close_ticket(ticket_id):
    data = request.get_json()
    reason = data.get('reason', 'manual')

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Get project_id for backup
        cursor.execute("SELECT project_id FROM tickets WHERE id = %s", (ticket_id,))
        ticket = cursor.fetchone()

        if ticket:
            # Create backup before closing
            create_project_backup(ticket['project_id'], 'close')

        cursor.execute("""
            UPDATE tickets SET status = 'done', closed_at = NOW(),
            closed_by = %s, close_reason = %s, updated_at = NOW()
            WHERE id = %s
        """, (session['user'], reason, ticket_id))
        conn.commit()
        cursor.close(); conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/ticket/<int:ticket_id>/skip', methods=['POST'])
@login_required
def skip_ticket(ticket_id):
    """Skip a ticket - mark as skipped and stop processing"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tickets SET status = 'skipped', closed_at = NOW(),
            closed_by = %s, close_reason = 'skipped', updated_at = NOW()
            WHERE id = %s AND status = 'in_progress'
        """, (session['user'], ticket_id))
        affected = cursor.rowcount
        conn.commit()
        cursor.close(); conn.close()

        if affected > 0:
            return jsonify({'success': True, 'message': 'Ticket skipped'})
        else:
            return jsonify({'success': False, 'message': 'Ticket not in progress'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/ticket/<int:ticket_id>/approve', methods=['POST'])
@login_required
def approve_ticket(ticket_id):
    """Approve a awaiting_input ticket as done"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Get project_id for backup
        cursor.execute("SELECT project_id FROM tickets WHERE id = %s AND status = 'awaiting_input'", (ticket_id,))
        ticket = cursor.fetchone()

        if not ticket:
            cursor.close(); conn.close()
            return jsonify({'success': False, 'message': 'Ticket not found or not pending review'})

        # Create backup before approving
        create_project_backup(ticket['project_id'], 'close')

        cursor.execute("""
            UPDATE tickets SET status = 'done', closed_at = NOW(),
            closed_by = %s, close_reason = 'approved', review_deadline = NULL, updated_at = NOW()
            WHERE id = %s
        """, (session['user'], ticket_id))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/ticket/<int:ticket_id>/reopen', methods=['POST'])
@login_required
def reopen_ticket(ticket_id):
    try:
        data = request.get_json() or {}
        instructions = data.get('instructions', '').strip()

        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Get project_id for backup
        cursor.execute("SELECT project_id FROM tickets WHERE id = %s", (ticket_id,))
        ticket = cursor.fetchone()

        if ticket:
            # Create backup before reopening
            create_project_backup(ticket['project_id'], 'reopen')

        # Update ticket status
        cursor.execute("""
            UPDATE tickets SET status = 'open', closed_at = NULL,
            closed_by = NULL, close_reason = NULL, review_deadline = NULL, updated_at = NOW()
            WHERE id = %s
        """, (ticket_id,))

        # If instructions provided, add as a user message for Claude to see
        if instructions:
            reopen_msg = f"[REOPEN] Additional instructions:\n{instructions}"
            msg_tokens = len(reopen_msg.encode('utf-8')) // 4
            cursor.execute("""
                INSERT INTO conversation_messages (ticket_id, role, content, token_count, created_at)
                VALUES (%s, 'user', %s, %s, NOW())
            """, (ticket_id, reopen_msg, msg_tokens))
            cursor.execute("UPDATE tickets SET total_tokens = total_tokens + %s WHERE id = %s", (msg_tokens, ticket_id))

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/message/<int:message_id>', methods=['DELETE'])
@login_required
def delete_message(message_id):
    """Delete a conversation message"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Get message info first
        cursor.execute("SELECT id, ticket_id, token_count FROM conversation_messages WHERE id = %s", (message_id,))
        message = cursor.fetchone()

        if not message:
            cursor.close(); conn.close()
            return jsonify({'success': False, 'message': 'Message not found'})

        ticket_id = message['ticket_id']
        token_count = message['token_count'] or 0

        # Delete the message
        cursor.execute("DELETE FROM conversation_messages WHERE id = %s", (message_id,))

        # Update ticket token count
        if token_count > 0:
            cursor.execute("UPDATE tickets SET total_tokens = GREATEST(0, total_tokens - %s) WHERE id = %s",
                          (token_count, ticket_id))

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'message': 'Message deleted'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/ticket/<int:ticket_id>/summarize', methods=['POST'])
@login_required
def create_ticket_summary(ticket_id):
    """Create manual summary/extraction using Haiku to save tokens"""
    try:
        if not SmartContextManager:
            return jsonify({'success': False, 'message': 'SmartContextManager not available'})

        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Get all unsummarized messages
        cursor.execute("""
            SELECT id, role, content, tool_name, tool_input, token_count
            FROM conversation_messages
            WHERE ticket_id = %s AND is_summarized = FALSE
            ORDER BY created_at ASC
        """, (ticket_id,))
        messages = cursor.fetchall()

        if not messages:
            cursor.close(); conn.close()
            return jsonify({'success': False, 'message': 'No messages to summarize'})

        # Count tokens before
        tokens_before = sum(len(m.get('content', '') or '') // 4 for m in messages)

        cursor.close(); conn.close()

        # Create SmartContextManager instance
        context_manager = SmartContextManager(db_pool, logger=lambda msg, level: print(f"[{level}] {msg}"))

        # Create extraction
        result = context_manager.create_extraction(ticket_id, messages)

        if result:
            tokens_after = result.get('tokens_after', 0)
            saved = tokens_before - tokens_after
            return jsonify({
                'success': True,
                'message': f'Summary created! Compressed {len(messages)} messages.',
                'tokens_before': tokens_before,
                'tokens_after': tokens_after,
                'messages_summarized': len(messages)
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to create summary'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/ticket/<int:ticket_id>/settings', methods=['POST'])
@login_required
def update_ticket_settings(ticket_id):
    """Update ticket settings like AI model"""
    try:
        data = request.get_json()
        conn = get_db()
        cursor = conn.cursor()

        updates = []
        params = []

        if 'ai_model' in data:
            ai_model = data['ai_model']
            if ai_model in ('opus', 'sonnet', 'haiku'):
                updates.append("ai_model = %s")
                params.append(ai_model)
            elif ai_model == '' or ai_model is None:
                updates.append("ai_model = NULL")

        if not updates:
            cursor.close(); conn.close()
            return jsonify({'success': False, 'message': 'No valid settings to update'})

        updates.append("updated_at = NOW()")
        params.append(ticket_id)

        cursor.execute(f"UPDATE tickets SET {', '.join(updates)} WHERE id = %s", params)
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ============ CHAT ============

@app.route('/api/ticket/<int:ticket_id>/messages')
@login_required
def get_ticket_messages(ticket_id):
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM conversation_messages 
            WHERE ticket_id = %s ORDER BY created_at ASC
        """, (ticket_id,))
        messages = cursor.fetchall()
        cursor.close(); conn.close()
        
        for m in messages:
            if m.get('created_at'): m['created_at'] = to_iso_utc(m['created_at'])
            if m.get('tool_input') and isinstance(m['tool_input'], str):
                try: m['tool_input'] = json.loads(m['tool_input'])
                except: pass
        
        return jsonify(messages)
    except Exception as e:
        return jsonify([])

@app.route('/api/ticket/<int:ticket_id>/logs')
@login_required
def get_ticket_logs(ticket_id):
    """Get execution logs for a ticket's sessions (for console tab)"""
    include_code = request.args.get('include_code', '0') == '1'

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        results = []

        # Get execution logs
        cursor.execute("""
            SELECT el.id, el.log_type, el.message, el.created_at, 'log' as source
            FROM execution_logs el
            JOIN execution_sessions es ON el.session_id = es.id
            WHERE es.ticket_id = %s
        """, (ticket_id,))
        logs = cursor.fetchall()
        for log in logs:
            if log.get('created_at'): log['created_at'] = to_iso_utc(log['created_at'])
        results.extend(logs)

        # If include_code, also get tool_use messages with their content
        if include_code:
            cursor.execute("""
                SELECT id, role, tool_name, tool_input, content, created_at, 'tool' as source
                FROM conversation_messages
                WHERE ticket_id = %s AND role IN ('tool_use', 'tool_result')
            """, (ticket_id,))
            tools = cursor.fetchall()
            for t in tools:
                if t.get('created_at'): t['created_at'] = to_iso_utc(t['created_at'])
                # Parse tool_input if it's a string
                if t.get('tool_input') and isinstance(t['tool_input'], str):
                    try: t['tool_input'] = json.loads(t['tool_input'])
                    except: pass
            results.extend(tools)

        cursor.close(); conn.close()

        # Sort all results by created_at
        results.sort(key=lambda x: x.get('created_at') or '')

        return jsonify(results)
    except Exception as e:
        return jsonify([])

@app.route('/api/ticket/<int:ticket_id>/send', methods=['POST'])
@login_required
def send_ticket_message(ticket_id):
    data = request.get_json()
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({'success': False, 'message': 'Empty message'})
    
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Check ticket exists and is valid
        cursor.execute("SELECT * FROM tickets WHERE id = %s", (ticket_id,))
        ticket = cursor.fetchone()
        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket not found'})

        # If ticket is in awaiting_input or skipped, auto-reopen it so Claude can respond
        if ticket['status'] in ('awaiting_input', 'skipped'):
            cursor.execute("""
                UPDATE tickets SET status = 'open', review_deadline = NULL,
                closed_at = NULL, closed_by = NULL, close_reason = NULL, updated_at = NOW()
                WHERE id = %s
            """, (ticket_id,))

        # Handle commands
        if message.startswith('/'):
            cmd = message.lower().split()[0]
            if cmd == '/done':
                # Save command to conversation for display
                cursor.execute("""
                    INSERT INTO conversation_messages (ticket_id, role, content, created_at)
                    VALUES (%s, 'user', %s, NOW())
                """, (ticket_id, message))
                msg_id = cursor.lastrowid
                cursor.execute("""
                    UPDATE tickets SET status = 'done', closed_at = NOW(),
                    closed_by = %s, close_reason = 'manual', updated_at = NOW()
                    WHERE id = %s
                """, (session['user'], ticket_id))
                # Signal daemon to stop Claude immediately
                cursor.execute("""
                    INSERT INTO user_messages (ticket_id, user_id, content, message_type)
                    VALUES (%s, %s, '/done', 'command')
                """, (ticket_id, session.get('user_id')))
                # Add log entry
                log_msg = f"✅ User command: /done - Ticket {ticket['ticket_number']} closed"
                cursor.execute("""
                    INSERT INTO daemon_logs (ticket_id, log_type, message, created_at)
                    VALUES (%s, 'info', %s, NOW())
                """, (ticket_id, log_msg))
                conn.commit()
                # Broadcast log to console
                socketio.emit('new_log', {'log_type': 'info', 'message': log_msg, 'created_at': datetime.now().isoformat() + 'Z'}, room='console')
                # Broadcast message immediately
                cursor.execute("SELECT * FROM conversation_messages WHERE id = %s", (msg_id,))
                new_msg = cursor.fetchone()
                cursor.close(); conn.close()
                if new_msg:
                    if new_msg.get('created_at'): new_msg['created_at'] = to_iso_utc(new_msg['created_at'])
                    new_msg['ticket_number'] = ticket['ticket_number']
                    socketio.emit('new_message', new_msg, room=f'ticket_{ticket_id}')
                    socketio.emit('new_message', new_msg, room='console')
                socketio.emit('ticket_closed', {'ticket_id': ticket_id}, room=f'ticket_{ticket_id}')
                return jsonify({'success': True, 'message': 'Ticket closed'})
            elif cmd == '/skip':
                # Save command to conversation for display
                cursor.execute("""
                    INSERT INTO conversation_messages (ticket_id, role, content, created_at)
                    VALUES (%s, 'user', %s, NOW())
                """, (ticket_id, message))
                msg_id = cursor.lastrowid
                cursor.execute("""
                    UPDATE tickets SET status = 'skipped', closed_at = NOW(),
                    closed_by = %s, close_reason = 'skipped', updated_at = NOW()
                    WHERE id = %s
                """, (session['user'], ticket_id))
                # Also signal daemon
                cursor.execute("""
                    INSERT INTO user_messages (ticket_id, user_id, content, message_type)
                    VALUES (%s, %s, '/skip', 'command')
                """, (ticket_id, session.get('user_id')))
                # Add log entry
                log_msg = f"⏭️ User command: /skip - Ticket {ticket['ticket_number']} skipped"
                cursor.execute("""
                    INSERT INTO daemon_logs (ticket_id, log_type, message, created_at)
                    VALUES (%s, 'warning', %s, NOW())
                """, (ticket_id, log_msg))
                conn.commit()
                # Broadcast log to console
                socketio.emit('new_log', {'log_type': 'warning', 'message': log_msg, 'created_at': datetime.now().isoformat() + 'Z'}, room='console')
                # Broadcast message immediately
                cursor.execute("SELECT * FROM conversation_messages WHERE id = %s", (msg_id,))
                new_msg = cursor.fetchone()
                cursor.close(); conn.close()
                if new_msg:
                    if new_msg.get('created_at'): new_msg['created_at'] = to_iso_utc(new_msg['created_at'])
                    new_msg['ticket_number'] = ticket['ticket_number']
                    socketio.emit('new_message', new_msg, room=f'ticket_{ticket_id}')
                    socketio.emit('new_message', new_msg, room='console')
                return jsonify({'success': True, 'message': 'Ticket skipped'})
            elif cmd == '/stop':
                # Save command to conversation for display
                cursor.execute("""
                    INSERT INTO conversation_messages (ticket_id, role, content, created_at)
                    VALUES (%s, 'user', %s, NOW())
                """, (ticket_id, message))
                msg_id = cursor.lastrowid
                # Signal daemon to stop Claude and wait for input
                cursor.execute("""
                    INSERT INTO user_messages (ticket_id, user_id, content, message_type)
                    VALUES (%s, %s, '/stop', 'command')
                """, (ticket_id, session.get('user_id')))
                # Add log entry
                log_msg = f"⏸️ User command: /stop - Ticket {ticket['ticket_number']} paused"
                cursor.execute("""
                    INSERT INTO daemon_logs (ticket_id, log_type, message, created_at)
                    VALUES (%s, 'warning', %s, NOW())
                """, (ticket_id, log_msg))
                conn.commit()
                # Broadcast log to console
                socketio.emit('new_log', {'log_type': 'warning', 'message': log_msg, 'created_at': datetime.now().isoformat() + 'Z'}, room='console')
                # Broadcast message immediately
                cursor.execute("SELECT * FROM conversation_messages WHERE id = %s", (msg_id,))
                new_msg = cursor.fetchone()
                cursor.close(); conn.close()
                if new_msg:
                    if new_msg.get('created_at'): new_msg['created_at'] = to_iso_utc(new_msg['created_at'])
                    new_msg['ticket_number'] = ticket['ticket_number']
                    socketio.emit('new_message', new_msg, room=f'ticket_{ticket_id}')
                    socketio.emit('new_message', new_msg, room='console')
                return jsonify({'success': True, 'message': 'Stop signal sent'})

        # Save user message
        msg_tokens = len(message.encode('utf-8')) // 4
        cursor.execute("""
            INSERT INTO conversation_messages (ticket_id, role, content, token_count, created_at)
            VALUES (%s, 'user', %s, %s, NOW())
        """, (ticket_id, message, msg_tokens))

        # Also save to user_messages for daemon to pick up
        cursor.execute("""
            INSERT INTO user_messages (ticket_id, user_id, content, message_type, processed)
            VALUES (%s, %s, %s, 'message', FALSE)
        """, (ticket_id, session.get('user_id'), message))

        # Update ticket tokens and timestamp
        cursor.execute("UPDATE tickets SET total_tokens = total_tokens + %s, updated_at = NOW() WHERE id = %s", (msg_tokens, ticket_id))
        
        conn.commit()
        
        # Get the inserted message
        cursor.execute("SELECT * FROM conversation_messages WHERE ticket_id = %s ORDER BY id DESC LIMIT 1", (ticket_id,))
        new_msg = cursor.fetchone()
        cursor.close(); conn.close()
        
        if new_msg.get('created_at'): new_msg['created_at'] = to_iso_utc(new_msg['created_at'])
        
        # Broadcast to room
        socketio.emit('new_message', new_msg, room=f'ticket_{ticket_id}')
        
        return jsonify({'success': True, 'message_id': new_msg['id']})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ============ DAEMON CONTROL ============

@app.route('/api/daemon/start', methods=['POST'])
@login_required
def start_daemon():
    try:
        # Check if daemon already running by process name
        result = subprocess.run(['pgrep', '-f', 'claude-daemon.py'], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return jsonify({"success": False, "message": "Daemon already running"})

        subprocess.Popen(['python3', DAEMON_SCRIPT],
                        stdout=open('/var/log/fotios-claude/daemon.log', 'a'),
                        stderr=subprocess.STDOUT, start_new_session=True)
        return jsonify({"success": True, "message": "Daemon started"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/daemon/stop', methods=['POST'])
@login_required
def stop_daemon():
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE) as f:
                os.kill(int(f.read().strip()), 15)
            return jsonify({"success": True, "message": "Daemon stopped"})
        return jsonify({"success": False, "message": "Not running"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/daemon/status')
@login_required
def daemon_status():
    status = {"running": False, "current_ticket": None}
    
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                os.kill(int(f.read().strip()), 0)
            status["running"] = True
        except: pass
    
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        # Get all in_progress tickets (multi-worker support)
        cursor.execute("""
            SELECT t.ticket_number, t.title, p.name as project_name
            FROM tickets t
            JOIN projects p ON t.project_id = p.id
            WHERE t.status = 'in_progress'
            ORDER BY t.updated_at DESC
        """)
        active = cursor.fetchall()
        status["active_workers"] = len(active)
        status["active_tickets"] = active
        if active:
            status["current_ticket"] = active[0]['ticket_number']
            status["current_title"] = active[0]['title']
        cursor.close(); conn.close()
    except: pass

    return jsonify(status)

# ============ CONSOLE ============

@app.route('/console')
@login_required
def console():
    return render_template('console.html', user=session['user'], role=session.get('role'))

@app.route('/terminal')
@login_required
def terminal():
    popup = request.args.get('popup', '0') == '1'
    return render_template('terminal.html', user=session['user'], role=session.get('role'), popup=popup)

@app.route('/api/logs/recent')
@login_required
def recent_logs():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT el.*, t.ticket_number FROM execution_logs el
            LEFT JOIN execution_sessions es ON el.session_id = es.id
            LEFT JOIN tickets t ON es.ticket_id = t.id
            WHERE el.created_at > DATE_SUB(NOW(), INTERVAL 1 HOUR)
            ORDER BY el.created_at DESC LIMIT 100
        """)
        logs = cursor.fetchall()
        cursor.close(); conn.close()

        for log in logs:
            if log.get('created_at'): log['created_at'] = to_iso_utc(log['created_at'])
        return jsonify(logs)
    except:
        return jsonify([])

@app.route('/api/conversation/current')
@login_required
def current_conversation():
    """Get messages from all active tickets (for multi-worker view)"""
    ticket_id = request.args.get('ticket_id')
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        if ticket_id:
            # Specific ticket requested
            cursor.execute("""
                SELECT * FROM conversation_messages
                WHERE ticket_id = %s ORDER BY created_at ASC LIMIT 100
            """, (ticket_id,))
        else:
            # Get messages from ALL in_progress tickets
            cursor.execute("""
                SELECT cm.*, t.ticket_number, p.name as project_name
                FROM conversation_messages cm
                JOIN tickets t ON cm.ticket_id = t.id
                JOIN projects p ON t.project_id = p.id
                WHERE t.status = 'in_progress'
                ORDER BY cm.created_at ASC LIMIT 200
            """)

        messages = cursor.fetchall()
        cursor.close(); conn.close()

        for m in messages:
            if m.get('created_at'): m['created_at'] = to_iso_utc(m['created_at'])
            if m.get('tool_input') and isinstance(m['tool_input'], str):
                try: m['tool_input'] = json.loads(m['tool_input'])
                except: pass
        return jsonify(messages)
    except Exception as e:
        return jsonify([])

@app.route('/api/active_tickets')
@login_required
def active_tickets():
    """Get list of all currently in_progress tickets"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT t.id, t.ticket_number, t.title, p.name as project_name
            FROM tickets t
            JOIN projects p ON t.project_id = p.id
            WHERE t.status = 'in_progress'
            ORDER BY t.updated_at DESC
        """)
        tickets = cursor.fetchall()
        cursor.close(); conn.close()
        return jsonify(tickets)
    except:
        return jsonify([])

@app.route('/api/send_message', methods=['POST'])
@login_required
def send_console_message():
    """Send a message to a specific active ticket"""
    data = request.get_json()
    message = data.get('message', '').strip()
    ticket_id = data.get('ticket_id')

    if not message:
        return jsonify({'success': False, 'message': 'Empty message'})

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Use specific ticket_id if provided, otherwise get most recent active
        if ticket_id:
            cursor.execute("""
                SELECT id, ticket_number, status FROM tickets WHERE id = %s AND status IN ('in_progress', 'awaiting_input')
            """, (ticket_id,))
        else:
            cursor.execute("""
                SELECT id, ticket_number, status FROM tickets WHERE status IN ('in_progress', 'awaiting_input')
                ORDER BY updated_at DESC LIMIT 1
            """)
        ticket = cursor.fetchone()
        if not ticket:
            cursor.close(); conn.close()
            return jsonify({'success': False, 'message': 'No active ticket'})

        # If ticket is in awaiting_input, auto-reopen it
        if ticket['status'] == 'awaiting_input':
            cursor.execute("""
                UPDATE tickets SET status = 'open', review_deadline = NULL, updated_at = NOW()
                WHERE id = %s
            """, (ticket['id'],))

        # Handle commands
        if message.startswith('/'):
            cmd = message.lower().split()[0]
            if cmd == '/skip':
                cursor.execute("""
                    INSERT INTO user_messages (ticket_id, user_id, content, message_type)
                    VALUES (%s, %s, '/skip', 'command')
                """, (ticket['id'], session.get('user_id')))
                conn.commit()
                cursor.close(); conn.close()
                return jsonify({'success': True, 'message': 'Skip command sent'})

        # Save user message
        msg_tokens = len(message.encode('utf-8')) // 4
        cursor.execute("""
            INSERT INTO conversation_messages (ticket_id, role, content, token_count, created_at)
            VALUES (%s, 'user', %s, %s, NOW())
        """, (ticket['id'], message, msg_tokens))

        cursor.execute("""
            INSERT INTO user_messages (ticket_id, user_id, content, message_type, processed)
            VALUES (%s, %s, %s, 'message', FALSE)
        """, (ticket['id'], session.get('user_id'), message))

        # Update ticket tokens
        cursor.execute("UPDATE tickets SET total_tokens = total_tokens + %s WHERE id = %s", (msg_tokens, ticket['id']))

        conn.commit()
        cursor.close(); conn.close()

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ============ HISTORY ============

@app.route('/history')
@login_required
def history():
    sessions = []
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT es.*, t.ticket_number, t.title,
                   TIMESTAMPDIFF(MINUTE, es.started_at, COALESCE(es.ended_at, NOW())) as duration_minutes
            FROM execution_sessions es 
            LEFT JOIN tickets t ON es.ticket_id = t.id
            ORDER BY es.started_at DESC LIMIT 50
        """)
        sessions = cursor.fetchall()
        cursor.close(); conn.close()
    except Exception as e:
        print(f"History error: {e}")
    
    return render_template('history.html', user=session['user'], role=session.get('role'), sessions=sessions)

@app.route('/session/<int:session_id>')
@login_required
def session_detail(session_id):
    """View details of a specific execution session"""
    session_data = None
    logs = []
    messages = []
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Get session with ticket info
        cursor.execute("""
            SELECT es.*, t.ticket_number, t.title, t.description, t.id as ticket_id,
                   p.name as project_name,
                   TIMESTAMPDIFF(MINUTE, es.started_at, COALESCE(es.ended_at, NOW())) as duration_minutes
            FROM execution_sessions es
            LEFT JOIN tickets t ON es.ticket_id = t.id
            LEFT JOIN projects p ON t.project_id = p.id
            WHERE es.id = %s
        """, (session_id,))
        session_data = cursor.fetchone()

        if session_data:
            # Get execution logs for this session
            cursor.execute("""
                SELECT * FROM execution_logs
                WHERE session_id = %s
                ORDER BY created_at ASC
            """, (session_id,))
            logs = cursor.fetchall()

            # Get conversation messages for this ticket
            cursor.execute("""
                SELECT * FROM conversation_messages
                WHERE ticket_id = %s
                ORDER BY created_at ASC
            """, (session_data['ticket_id'],))
            messages = cursor.fetchall()

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Session detail error: {e}")

    if not session_data:
        return "Session not found", 404

    return render_template('session_detail.html',
                          user=session['user'],
                          role=session.get('role'),
                          session=session_data,
                          logs=logs,
                          messages=messages)

# ============ STATISTICS API ============

# Anthropic pricing (per million tokens) - June 2024
PRICING = {
    'sonnet': {'input': 3.0, 'output': 15.0, 'cache_read': 0.30, 'cache_write': 3.75},
    'opus': {'input': 15.0, 'output': 75.0, 'cache_read': 1.50, 'cache_write': 18.75},
    'haiku': {'input': 0.25, 'output': 1.25, 'cache_read': 0.03, 'cache_write': 0.30}
}
DEFAULT_MODEL = 'sonnet'

def calculate_cost(input_tokens, output_tokens, cache_read=0, cache_write=0, model=DEFAULT_MODEL):
    """Calculate cost in USD based on token usage"""
    prices = PRICING.get(model, PRICING[DEFAULT_MODEL])
    cost = (
        (input_tokens / 1_000_000) * prices['input'] +
        (output_tokens / 1_000_000) * prices['output'] +
        (cache_read / 1_000_000) * prices['cache_read'] +
        (cache_write / 1_000_000) * prices['cache_write']
    )
    return round(cost, 4)

def format_duration(seconds):
    """Format seconds to human readable"""
    seconds = int(seconds or 0)
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins}m {secs}s"
    else:
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        return f"{hours}h {mins}m"

@app.route('/api/stats/dashboard')
@login_required
def get_dashboard_stats():
    """Get comprehensive statistics for dashboard"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Today's stats (completed sessions)
        cursor.execute("""
            SELECT
                COALESCE(SUM(input_tokens), 0) as input_tokens,
                COALESCE(SUM(output_tokens), 0) as output_tokens,
                COALESCE(SUM(total_tokens), 0) as total_tokens,
                COALESCE(SUM(cache_read_tokens), 0) as cache_read_tokens,
                COALESCE(SUM(cache_creation_tokens), 0) as cache_creation_tokens,
                COALESCE(SUM(duration_seconds), 0) as duration_seconds,
                COALESCE(SUM(api_calls), 0) as api_calls,
                COUNT(DISTINCT ticket_id) as tickets_worked
            FROM usage_stats
            WHERE DATE(created_at) = CURDATE()
        """)
        today = cursor.fetchone()

        # Add running sessions to today's stats
        cursor.execute("""
            SELECT
                COALESCE(SUM(tokens_used), 0) as running_tokens,
                COALESCE(SUM(api_calls), 0) as running_api_calls,
                COALESCE(SUM(TIMESTAMPDIFF(SECOND, started_at, NOW())), 0) as running_duration,
                COUNT(DISTINCT ticket_id) as running_tickets
            FROM execution_sessions
            WHERE status = 'running' AND DATE(started_at) = CURDATE()
        """)
        running = cursor.fetchone()
        if running:
            today['total_tokens'] = int(today['total_tokens'] or 0) + int(running['running_tokens'] or 0)
            today['api_calls'] = int(today['api_calls'] or 0) + int(running['running_api_calls'] or 0)
            today['duration_seconds'] = int(today['duration_seconds'] or 0) + int(running['running_duration'] or 0)

        # Last 7 days stats
        cursor.execute("""
            SELECT
                COALESCE(SUM(input_tokens), 0) as input_tokens,
                COALESCE(SUM(output_tokens), 0) as output_tokens,
                COALESCE(SUM(total_tokens), 0) as total_tokens,
                COALESCE(SUM(cache_read_tokens), 0) as cache_read_tokens,
                COALESCE(SUM(cache_creation_tokens), 0) as cache_creation_tokens,
                COALESCE(SUM(duration_seconds), 0) as duration_seconds,
                COALESCE(SUM(api_calls), 0) as api_calls,
                COUNT(DISTINCT ticket_id) as tickets_worked
            FROM usage_stats
            WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
        """)
        week = cursor.fetchone()
        # Add running sessions to week
        if running:
            week['total_tokens'] = int(week['total_tokens'] or 0) + int(running['running_tokens'] or 0)
            week['api_calls'] = int(week['api_calls'] or 0) + int(running['running_api_calls'] or 0)
            week['duration_seconds'] = int(week['duration_seconds'] or 0) + int(running['running_duration'] or 0)

        # This month stats
        cursor.execute("""
            SELECT
                COALESCE(SUM(input_tokens), 0) as input_tokens,
                COALESCE(SUM(output_tokens), 0) as output_tokens,
                COALESCE(SUM(total_tokens), 0) as total_tokens,
                COALESCE(SUM(cache_read_tokens), 0) as cache_read_tokens,
                COALESCE(SUM(cache_creation_tokens), 0) as cache_creation_tokens,
                COALESCE(SUM(duration_seconds), 0) as duration_seconds,
                COALESCE(SUM(api_calls), 0) as api_calls,
                COUNT(DISTINCT ticket_id) as tickets_worked
            FROM usage_stats
            WHERE YEAR(created_at) = YEAR(CURDATE()) AND MONTH(created_at) = MONTH(CURDATE())
        """)
        month = cursor.fetchone()
        # Add running sessions to month
        if running:
            month['total_tokens'] = int(month['total_tokens'] or 0) + int(running['running_tokens'] or 0)
            month['api_calls'] = int(month['api_calls'] or 0) + int(running['running_api_calls'] or 0)
            month['duration_seconds'] = int(month['duration_seconds'] or 0) + int(running['running_duration'] or 0)

        # All time stats
        cursor.execute("""
            SELECT
                COALESCE(SUM(input_tokens), 0) as input_tokens,
                COALESCE(SUM(output_tokens), 0) as output_tokens,
                COALESCE(SUM(total_tokens), 0) as total_tokens,
                COALESCE(SUM(cache_read_tokens), 0) as cache_read_tokens,
                COALESCE(SUM(cache_creation_tokens), 0) as cache_creation_tokens,
                COALESCE(SUM(duration_seconds), 0) as duration_seconds,
                COALESCE(SUM(api_calls), 0) as api_calls,
                COUNT(DISTINCT ticket_id) as tickets_worked
            FROM usage_stats
        """)
        all_time = cursor.fetchone()
        # Add ALL running sessions to all_time (not just today's)
        cursor.execute("""
            SELECT
                COALESCE(SUM(tokens_used), 0) as running_tokens,
                COALESCE(SUM(api_calls), 0) as running_api_calls,
                COALESCE(SUM(TIMESTAMPDIFF(SECOND, started_at, NOW())), 0) as running_duration
            FROM execution_sessions
            WHERE status = 'running'
        """)
        all_running = cursor.fetchone()
        if all_running:
            all_time['total_tokens'] = int(all_time['total_tokens'] or 0) + int(all_running['running_tokens'] or 0)
            all_time['api_calls'] = int(all_time['api_calls'] or 0) + int(all_running['running_api_calls'] or 0)
            all_time['duration_seconds'] = int(all_time['duration_seconds'] or 0) + int(all_running['running_duration'] or 0)

        # Daily breakdown for chart (last 30 days)
        cursor.execute("""
            SELECT
                DATE(created_at) as date,
                COALESCE(SUM(input_tokens), 0) as input_tokens,
                COALESCE(SUM(output_tokens), 0) as output_tokens,
                COALESCE(SUM(total_tokens), 0) as tokens,
                COALESCE(SUM(cache_read_tokens), 0) as cache_read_tokens,
                COALESCE(SUM(cache_creation_tokens), 0) as cache_creation_tokens,
                COALESCE(SUM(duration_seconds), 0) as duration,
                COALESCE(SUM(api_calls), 0) as api_calls,
                COUNT(DISTINCT ticket_id) as tickets
            FROM usage_stats
            WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            GROUP BY DATE(created_at)
            ORDER BY date ASC
        """)
        daily_data = cursor.fetchall()

        # Top projects by tokens (last 30 days)
        cursor.execute("""
            SELECT
                p.name,
                p.code,
                COALESCE(SUM(u.input_tokens), 0) as input_tokens,
                COALESCE(SUM(u.output_tokens), 0) as output_tokens,
                COALESCE(SUM(u.total_tokens), 0) as tokens,
                COALESCE(SUM(u.cache_read_tokens), 0) as cache_read_tokens,
                COALESCE(SUM(u.cache_creation_tokens), 0) as cache_creation_tokens,
                COALESCE(SUM(u.duration_seconds), 0) as duration,
                COUNT(DISTINCT u.ticket_id) as tickets
            FROM usage_stats u
            JOIN projects p ON u.project_id = p.id
            WHERE u.created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            GROUP BY p.id
            ORDER BY tokens DESC
            LIMIT 10
        """)
        top_projects = cursor.fetchall()

        # Recent activity (last 20 usage records)
        cursor.execute("""
            SELECT
                u.created_at,
                t.ticket_number,
                t.title as ticket_title,
                p.name as project_name,
                u.total_tokens,
                u.duration_seconds,
                u.api_calls
            FROM usage_stats u
            JOIN tickets t ON u.ticket_id = t.id
            JOIN projects p ON u.project_id = p.id
            ORDER BY u.created_at DESC
            LIMIT 20
        """)
        recent_activity = cursor.fetchall()

        cursor.close()
        conn.close()

        # Calculate costs for each period
        def add_cost(data):
            if data:
                # Convert Decimal to int for calculations
                for key in ['input_tokens', 'output_tokens', 'total_tokens', 'cache_read_tokens',
                           'cache_creation_tokens', 'duration_seconds', 'api_calls', 'tickets_worked']:
                    if key in data and data[key] is not None:
                        data[key] = int(data[key])
                    elif key in data:
                        data[key] = 0
                data['cost'] = calculate_cost(
                    data['input_tokens'],
                    data['output_tokens'],
                    data.get('cache_read_tokens', 0),
                    data.get('cache_creation_tokens', 0)
                )
                data['duration_formatted'] = format_duration(data['duration_seconds'])
            return data

        # Format daily data for charts
        daily_formatted = []
        for row in daily_data:
            tokens = int(row['tokens'] or 0)
            input_tok = int(row['input_tokens'] or 0)
            output_tok = int(row['output_tokens'] or 0)
            cache_read = int(row['cache_read_tokens'] or 0)
            cache_write = int(row['cache_creation_tokens'] or 0)
            daily_formatted.append({
                'date': row['date'].isoformat() if row['date'] else None,
                'tokens': tokens,
                'duration': int(row['duration'] or 0),
                'api_calls': int(row['api_calls'] or 0),
                'tickets': int(row['tickets'] or 0),
                'cost': calculate_cost(input_tok, output_tok, cache_read, cache_write)
            })

        # Format top projects
        top_projects_formatted = []
        for row in top_projects:
            tokens = int(row['tokens'] or 0)
            input_tok = int(row['input_tokens'] or 0)
            output_tok = int(row['output_tokens'] or 0)
            cache_read = int(row['cache_read_tokens'] or 0)
            cache_write = int(row['cache_creation_tokens'] or 0)
            top_projects_formatted.append({
                'name': row['name'],
                'code': row['code'],
                'tokens': tokens,
                'duration': int(row['duration'] or 0),
                'duration_formatted': format_duration(int(row['duration'] or 0)),
                'tickets': int(row['tickets'] or 0),
                'cost': calculate_cost(input_tok, output_tok, cache_read, cache_write)
            })

        # Format recent activity
        recent_formatted = []
        for row in recent_activity:
            recent_formatted.append({
                'created_at': to_iso_utc(row['created_at']),
                'ticket_number': row['ticket_number'],
                'ticket_title': row['ticket_title'],
                'project_name': row['project_name'],
                'tokens': int(row['total_tokens'] or 0),
                'duration': int(row['duration_seconds'] or 0),
                'duration_formatted': format_duration(row['duration_seconds']),
                'api_calls': int(row['api_calls'] or 0)
            })

        return jsonify({
            'today': add_cost(today),
            'week': add_cost(week),
            'month': add_cost(month),
            'all_time': add_cost(all_time),
            'daily_chart': daily_formatted,
            'top_projects': top_projects_formatted,
            'recent_activity': recent_formatted
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats/project/<int:project_id>')
@login_required
def get_project_stats(project_id):
    """Get statistics for a specific project"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Project totals
        cursor.execute("""
            SELECT
                COALESCE(SUM(input_tokens), 0) as input_tokens,
                COALESCE(SUM(output_tokens), 0) as output_tokens,
                COALESCE(SUM(total_tokens), 0) as total_tokens,
                COALESCE(SUM(cache_read_tokens), 0) as cache_read_tokens,
                COALESCE(SUM(cache_creation_tokens), 0) as cache_creation_tokens,
                COALESCE(SUM(duration_seconds), 0) as duration_seconds,
                COALESCE(SUM(api_calls), 0) as api_calls,
                COUNT(DISTINCT ticket_id) as tickets_worked
            FROM usage_stats
            WHERE project_id = %s
        """, (project_id,))
        totals = cursor.fetchone()

        # Last 7 days for this project
        cursor.execute("""
            SELECT
                COALESCE(SUM(total_tokens), 0) as total_tokens,
                COALESCE(SUM(duration_seconds), 0) as duration_seconds
            FROM usage_stats
            WHERE project_id = %s AND created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
        """, (project_id,))
        week = cursor.fetchone()

        # Top tickets by tokens
        cursor.execute("""
            SELECT
                t.ticket_number,
                t.title,
                COALESCE(SUM(u.total_tokens), 0) as tokens,
                COALESCE(SUM(u.duration_seconds), 0) as duration
            FROM usage_stats u
            JOIN tickets t ON u.ticket_id = t.id
            WHERE u.project_id = %s
            GROUP BY t.id
            ORDER BY tokens DESC
            LIMIT 10
        """, (project_id,))
        top_tickets = cursor.fetchall()

        cursor.close()
        conn.close()

        # Convert Decimal to int
        for key in ['input_tokens', 'output_tokens', 'total_tokens', 'cache_read_tokens',
                   'cache_creation_tokens', 'duration_seconds', 'api_calls', 'tickets_worked']:
            if key in totals and totals[key] is not None:
                totals[key] = int(totals[key])
            elif key in totals:
                totals[key] = 0

        if week:
            week['total_tokens'] = int(week.get('total_tokens') or 0)
            week['duration_seconds'] = int(week.get('duration_seconds') or 0)

        totals['cost'] = calculate_cost(
            totals['input_tokens'],
            totals['output_tokens'],
            totals.get('cache_read_tokens', 0),
            totals.get('cache_creation_tokens', 0)
        )
        totals['duration_formatted'] = format_duration(totals['duration_seconds'])

        top_tickets_formatted = []
        for row in top_tickets:
            top_tickets_formatted.append({
                'ticket_number': row['ticket_number'],
                'title': row['title'],
                'tokens': int(row['tokens'] or 0),
                'duration': int(row['duration'] or 0),
                'duration_formatted': format_duration(row['duration'])
            })

        return jsonify({
            'totals': totals,
            'week': week,
            'top_tickets': top_tickets_formatted
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats/ticket/<int:ticket_id>')
@login_required
def get_ticket_stats(ticket_id):
    """Get statistics for a specific ticket"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Ticket totals from usage_stats (completed sessions)
        cursor.execute("""
            SELECT
                COALESCE(SUM(input_tokens), 0) as input_tokens,
                COALESCE(SUM(output_tokens), 0) as output_tokens,
                COALESCE(SUM(total_tokens), 0) as total_tokens,
                COALESCE(SUM(cache_read_tokens), 0) as cache_read_tokens,
                COALESCE(SUM(cache_creation_tokens), 0) as cache_creation_tokens,
                COALESCE(SUM(duration_seconds), 0) as duration_seconds,
                COALESCE(SUM(api_calls), 0) as api_calls,
                COUNT(*) as sessions
            FROM usage_stats
            WHERE ticket_id = %s
        """, (ticket_id,))
        totals = cursor.fetchone()

        # Add running session tokens (real-time)
        cursor.execute("""
            SELECT COALESCE(SUM(tokens_used), 0) as running_tokens,
                   COALESCE(SUM(TIMESTAMPDIFF(SECOND, started_at, NOW())), 0) as running_duration,
                   COALESCE(SUM(api_calls), 0) as running_api_calls,
                   COUNT(*) as running_sessions
            FROM execution_sessions
            WHERE ticket_id = %s AND status = 'running'
        """, (ticket_id,))
        running = cursor.fetchone()

        if running and running['running_sessions']:
            totals['total_tokens'] = int(totals['total_tokens'] or 0) + int(running['running_tokens'] or 0)
            totals['duration_seconds'] = int(totals['duration_seconds'] or 0) + int(running['running_duration'] or 0)
            totals['api_calls'] = int(totals['api_calls'] or 0) + int(running['running_api_calls'] or 0)
            totals['sessions'] = int(totals['sessions'] or 0) + int(running['running_sessions'] or 0)

        # Add user message tokens (from conversation_messages)
        cursor.execute("""
            SELECT COALESCE(SUM(token_count), 0) as user_tokens
            FROM conversation_messages
            WHERE ticket_id = %s AND role = 'user'
        """, (ticket_id,))
        user_msg = cursor.fetchone()
        if user_msg and user_msg['user_tokens']:
            totals['total_tokens'] = int(totals['total_tokens'] or 0) + int(user_msg['user_tokens'] or 0)

        # Session breakdown
        cursor.execute("""
            SELECT
                u.created_at,
                u.input_tokens,
                u.output_tokens,
                u.total_tokens,
                u.duration_seconds,
                u.api_calls
            FROM usage_stats u
            WHERE u.ticket_id = %s
            ORDER BY u.created_at DESC
        """, (ticket_id,))
        sessions = cursor.fetchall()

        cursor.close()
        conn.close()

        # Convert Decimal to int
        for key in ['input_tokens', 'output_tokens', 'total_tokens', 'cache_read_tokens',
                   'cache_creation_tokens', 'duration_seconds', 'api_calls', 'sessions']:
            if key in totals and totals[key] is not None:
                totals[key] = int(totals[key])
            elif key in totals:
                totals[key] = 0

        totals['cost'] = calculate_cost(
            totals['input_tokens'],
            totals['output_tokens'],
            totals.get('cache_read_tokens', 0),
            totals.get('cache_creation_tokens', 0)
        )
        totals['duration_formatted'] = format_duration(totals['duration_seconds'])

        sessions_formatted = []
        for row in sessions:
            input_tok = int(row['input_tokens'] or 0)
            output_tok = int(row['output_tokens'] or 0)
            sessions_formatted.append({
                'created_at': to_iso_utc(row['created_at']),
                'input_tokens': input_tok,
                'output_tokens': output_tok,
                'total_tokens': int(row['total_tokens'] or 0),
                'duration': int(row['duration_seconds'] or 0),
                'duration_formatted': format_duration(row['duration_seconds']),
                'api_calls': int(row['api_calls'] or 0),
                'cost': calculate_cost(input_tok, output_tok)
            })

        return jsonify({
            'totals': totals,
            'sessions': sessions_formatted
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ INTERNAL API FOR DAEMON ============

@app.route('/api/internal/broadcast', methods=['POST'])
def internal_broadcast():
    """Called by daemon to broadcast new messages via WebSocket"""
    # Only allow from localhost
    if request.remote_addr not in ('127.0.0.1', '::1', 'localhost'):
        return jsonify({'error': 'forbidden'}), 403

    data = request.get_json()
    msg_type = data.get('type')
    ticket_id = data.get('ticket_id')

    if msg_type == 'message' and ticket_id:
        msg = data.get('message', {})
        if msg.get('tool_input') and isinstance(msg['tool_input'], str):
            try: msg['tool_input'] = json.loads(msg['tool_input'])
            except: pass
        socketio.emit('new_message', msg, room=f'ticket_{ticket_id}')

    elif msg_type == 'status' and ticket_id:
        status = data.get('status')
        socketio.emit('ticket_status', {
            'ticket_id': int(ticket_id),
            'status': status
        }, room=f'ticket_{ticket_id}')

    return jsonify({'success': True})

# ============ CLAUDE ACTIVATION ============

# Store terminal sessions for activation
activation_sessions = {}
# Store Claude chat sessions
claude_sessions = {}

CLAUDE_USER_HOME = "/home/claude"

class ActivationSession:
    """Terminal session for Claude setup-token"""
    def __init__(self):
        self.user_home = CLAUDE_USER_HOME
        self.fd = None
        self.pid = None
        self.output_buffer = ""
        self.running = False
        self.lock = threading.Lock()

    def start(self):
        claude_path = os.path.join(self.user_home, ".local/bin/claude")
        username = os.path.basename(self.user_home)
        try:
            pw = pwd.getpwnam(username)
            uid, gid = pw.pw_uid, pw.pw_gid
        except KeyError:
            uid, gid = None, None

        pid, fd = pty.fork()
        if pid == 0:
            if gid: os.setgid(gid)
            if uid: os.setuid(uid)
            env = {
                'HOME': self.user_home, 'USER': username, 'LOGNAME': username,
                'TERM': 'xterm-256color', 'PATH': '/usr/local/bin:/usr/bin:/bin',
                'SHELL': '/bin/bash', 'LANG': os.environ.get('LANG', 'en_US.UTF-8'),
            }
            os.chdir(self.user_home)
            os.execvpe(claude_path, [claude_path, 'setup-token'], env)
        else:
            self.pid, self.fd, self.running = pid, fd, True
            fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            threading.Thread(target=self._reader, daemon=True).start()
            return True
        return False

    def _reader(self):
        while self.running:
            try:
                r, _, _ = select.select([self.fd], [], [], 0.1)
                if r:
                    data = os.read(self.fd, 4096)
                    if data:
                        with self.lock:
                            self.output_buffer += data.decode('utf-8', errors='replace')
                    else:
                        break
            except:
                break
        self.running = False

    def get_output(self):
        with self.lock:
            out, self.output_buffer = self.output_buffer, ""
            return out

    def send_input(self, data):
        if self.fd and self.running:
            try:
                # Check if user is entering an API key
                if isinstance(data, str) and data.strip().startswith('sk-ant-'):
                    self._save_api_key(data.strip().split('\n')[0].split('\r')[0])
                os.write(self.fd, data.encode() if isinstance(data, str) else data)
                return True
            except: pass
        return False

    def _save_api_key(self, api_key):
        """Save API key to .env file for daemon to use"""
        try:
            env_dir = os.path.join(self.user_home, ".claude")
            os.makedirs(env_dir, exist_ok=True)
            env_file = os.path.join(env_dir, ".env")
            with open(env_file, 'w') as f:
                f.write(f"ANTHROPIC_API_KEY={api_key}\n")
            # Set proper ownership
            username = os.path.basename(self.user_home)
            try:
                pw = pwd.getpwnam(username)
                os.chown(env_file, pw.pw_uid, pw.pw_gid)
                os.chmod(env_file, 0o600)
            except: pass
        except Exception as e:
            pass  # Silent fail

    def resize(self, rows, cols):
        if self.fd:
            try:
                fcntl.ioctl(self.fd, termios.TIOCSWINSZ, struct.pack('HHHH', rows, cols, 0, 0))
            except: pass

    def stop(self):
        self.running = False
        if self.pid:
            try:
                os.kill(self.pid, signal.SIGTERM)
                os.waitpid(self.pid, os.WNOHANG)
            except: pass
        if self.fd:
            try: os.close(self.fd)
            except: pass

    def is_activated(self):
        # Check for OAuth credentials OR API key in .env
        creds_file = os.path.join(self.user_home, ".claude/.credentials.json")
        env_file = os.path.join(self.user_home, ".claude/.env")
        if os.path.exists(creds_file):
            return True
        if os.path.exists(env_file):
            try:
                with open(env_file, 'r') as f:
                    content = f.read()
                    if 'ANTHROPIC_API_KEY=sk-ant-' in content:
                        return True
            except: pass
        # Also check .claude.json for oauthAccount
        claude_json = os.path.join(self.user_home, ".claude.json")
        if os.path.exists(claude_json):
            try:
                with open(claude_json, 'r') as f:
                    config = json.load(f)
                    if 'oauthAccount' in config:
                        return True
            except: pass
        return False


class ClaudeChatSession:
    """Interactive Claude chat session"""
    def __init__(self):
        self.user_home = CLAUDE_USER_HOME
        self.fd = None
        self.pid = None
        self.output_buffer = ""
        self.running = False
        self.lock = threading.Lock()

    def start(self, model='sonnet'):
        # Ensure config flags are set before starting Claude
        ensure_claude_config_flags()

        claude_path = os.path.join(self.user_home, ".local/bin/claude")
        username = os.path.basename(self.user_home)
        try:
            pw = pwd.getpwnam(username)
            uid, gid = pw.pw_uid, pw.pw_gid
        except KeyError:
            uid, gid = None, None

        # Use simple model aliases (opus, sonnet, haiku)
        if model not in ('opus', 'sonnet', 'haiku'):
            model = 'sonnet'

        pid, fd = pty.fork()
        if pid == 0:
            if gid: os.setgid(gid)
            if uid: os.setuid(uid)
            # Inherit current environment and update with user-specific values
            env = os.environ.copy()
            env.update({
                'HOME': self.user_home, 'USER': username, 'LOGNAME': username,
                'TERM': 'xterm-256color', 'SHELL': '/bin/bash',
            })
            # Load API key from .env if exists
            env_file = os.path.join(self.user_home, ".claude/.env")
            if os.path.exists(env_file):
                try:
                    with open(env_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if '=' in line and not line.startswith('#'):
                                key, value = line.split('=', 1)
                                env[key] = value
                except: pass
            os.chdir(self.user_home)
            os.execvpe(claude_path, [claude_path, '--dangerously-skip-permissions', '--model', model], env)
        else:
            self.pid, self.fd, self.running = pid, fd, True
            fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            threading.Thread(target=self._reader, daemon=True).start()
            return True
        return False

    def _reader(self):
        while self.running:
            try:
                r, _, _ = select.select([self.fd], [], [], 0.1)
                if r:
                    data = os.read(self.fd, 4096)
                    if data:
                        with self.lock:
                            self.output_buffer += data.decode('utf-8', errors='replace')
                    else:
                        break
            except:
                break
        self.running = False

    def get_output(self):
        with self.lock:
            out, self.output_buffer = self.output_buffer, ""
            return out

    def send_input(self, data):
        if self.fd and self.running:
            try:
                os.write(self.fd, data.encode() if isinstance(data, str) else data)
                return True
            except: pass
        return False

    def resize(self, rows, cols):
        if self.fd:
            try:
                fcntl.ioctl(self.fd, termios.TIOCSWINSZ, struct.pack('HHHH', rows, cols, 0, 0))
            except: pass

    def stop(self):
        self.running = False
        if self.pid:
            try:
                os.kill(self.pid, signal.SIGTERM)
                os.waitpid(self.pid, os.WNOHANG)
            except: pass
        if self.fd:
            try: os.close(self.fd)
            except: pass


def ensure_claude_config_flags():
    """Ensure .claude.json has required flags to skip interactive prompts"""
    config_path = os.path.join(CLAUDE_USER_HOME, ".claude.json")
    if not os.path.exists(config_path):
        return
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        modified = False
        if not config.get('hasCompletedOnboarding'):
            config['hasCompletedOnboarding'] = True
            modified = True
        if not config.get('bypassPermissionsModeAccepted'):
            config['bypassPermissionsModeAccepted'] = True
            modified = True
        if not config.get('preferredTheme'):
            config['preferredTheme'] = 'dark'
            config['theme'] = 'dark'
            modified = True
        if modified:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
    except:
        pass

# Claude License Status
@app.route('/api/claude/status')
@login_required
def claude_status():
    creds = os.path.join(CLAUDE_USER_HOME, ".claude/.credentials.json")
    env_file = os.path.join(CLAUDE_USER_HOME, ".claude/.env")
    activated = os.path.exists(creds) or os.path.exists(env_file)
    if activated:
        ensure_claude_config_flags()
    return jsonify({'activated': activated})

# Activation Terminal Routes
@app.route('/api/claude/activate/start', methods=['POST'])
@login_required
def claude_activate_start():
    session_id = str(uuid.uuid4())
    sess = ActivationSession()
    if sess.start():
        activation_sessions[session_id] = sess
        return jsonify({'success': True, 'session_id': session_id})
    return jsonify({'success': False, 'error': 'Failed to start'})

@app.route('/api/claude/activate/output/<session_id>')
@login_required
def claude_activate_output(session_id):
    if session_id not in activation_sessions:
        return jsonify({'error': 'Not found'}), 404
    sess = activation_sessions[session_id]
    return jsonify({'output': sess.get_output(), 'running': sess.running, 'activated': sess.is_activated()})

@app.route('/api/claude/activate/input/<session_id>', methods=['POST'])
@login_required
def claude_activate_input(session_id):
    if session_id not in activation_sessions:
        return jsonify({'error': 'Not found'}), 404
    data = request.json.get('input', '')
    return jsonify({'success': activation_sessions[session_id].send_input(data)})

@app.route('/api/claude/activate/resize/<session_id>', methods=['POST'])
@login_required
def claude_activate_resize(session_id):
    if session_id not in activation_sessions:
        return jsonify({'error': 'Not found'}), 404
    data = request.json
    activation_sessions[session_id].resize(data.get('rows', 24), data.get('cols', 80))
    return jsonify({'success': True})

@app.route('/api/claude/activate/stop/<session_id>', methods=['POST'])
@login_required
def claude_activate_stop(session_id):
    if session_id in activation_sessions:
        activation_sessions[session_id].stop()
        del activation_sessions[session_id]
    return jsonify({'success': True})

@app.route('/api/claude/deactivate', methods=['POST'])
@login_required
def claude_deactivate():
    creds = os.path.join(CLAUDE_USER_HOME, ".claude/.credentials.json")
    env_file = os.path.join(CLAUDE_USER_HOME, ".claude/.env")
    claude_json = os.path.join(CLAUDE_USER_HOME, ".claude.json")
    removed = []
    try:
        if os.path.exists(creds):
            os.remove(creds)
            removed.append('credentials')
        if os.path.exists(env_file):
            os.remove(env_file)
            removed.append('env')
        # Also remove OAuth from .claude.json
        if os.path.exists(claude_json):
            with open(claude_json, 'r') as f:
                config = json.load(f)
            if 'oauthAccount' in config:
                del config['oauthAccount']
                with open(claude_json, 'w') as f:
                    json.dump(config, f, indent=2)
                removed.append('oauth')
        return jsonify({'success': True, 'message': f'Removed: {", ".join(removed)}' if removed else 'No credentials'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/claude/apikey', methods=['POST'])
@login_required
def claude_save_apikey():
    api_key = request.json.get('api_key', '').strip()
    if not api_key:
        return jsonify({'success': False, 'error': 'No API key'})
    if not api_key.startswith('sk-ant-'):
        return jsonify({'success': False, 'error': 'Invalid format'})
    try:
        env_file = os.path.join(CLAUDE_USER_HOME, ".claude/.env")
        os.makedirs(os.path.dirname(env_file), exist_ok=True)
        existing = {}
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    if '=' in line:
                        k, v = line.strip().split('=', 1)
                        existing[k] = v
        existing['ANTHROPIC_API_KEY'] = api_key
        with open(env_file, 'w') as f:
            for k, v in existing.items():
                f.write(f'{k}={v}\n')
        os.chmod(env_file, 0o600)
        # Change ownership to claude user
        try:
            pw = pwd.getpwnam('claude')
            os.chown(env_file, pw.pw_uid, pw.pw_gid)
        except: pass
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Settings API
@app.route('/api/settings', methods=['GET'])
@login_required
def get_settings():
    """Get current settings from system.conf"""
    try:
        config_file = '/etc/fotios-claude/system.conf'
        settings = {}
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        settings[key.strip()] = value.strip()
        return jsonify({
            'success': True,
            'settings': {
                'telegram_bot_token': settings.get('TELEGRAM_BOT_TOKEN', ''),
                'telegram_chat_id': settings.get('TELEGRAM_CHAT_ID', ''),
                'notify_completed': settings.get('NOTIFY_TICKET_COMPLETED', 'yes').lower() == 'yes',
                'notify_awaiting': settings.get('NOTIFY_AWAITING_INPUT', 'yes').lower() == 'yes',
                'notify_failed': settings.get('NOTIFY_TICKET_FAILED', 'yes').lower() == 'yes',
                'notify_watchdog': settings.get('NOTIFY_WATCHDOG_ALERT', 'yes').lower() == 'yes'
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/settings', methods=['POST'])
@login_required
def save_settings():
    """Save settings to system.conf"""
    try:
        data = request.get_json() or {}
        config_file = '/etc/fotios-claude/system.conf'

        # Read existing config
        existing = {}
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        existing[key.strip()] = value.strip()

        # Update Telegram settings
        existing['TELEGRAM_BOT_TOKEN'] = data.get('telegram_bot_token', '')
        existing['TELEGRAM_CHAT_ID'] = data.get('telegram_chat_id', '')
        existing['NOTIFY_TICKET_COMPLETED'] = 'yes' if data.get('notify_completed', True) else 'no'
        existing['NOTIFY_AWAITING_INPUT'] = 'yes' if data.get('notify_awaiting', True) else 'no'
        existing['NOTIFY_TICKET_FAILED'] = 'yes' if data.get('notify_failed', True) else 'no'
        existing['NOTIFY_WATCHDOG_ALERT'] = 'yes' if data.get('notify_watchdog', True) else 'no'

        # Write back
        with open(config_file, 'w') as f:
            f.write("# Fotios Claude System Configuration\n")
            for key, value in existing.items():
                f.write(f"{key}={value}\n")

        # Restart daemon to load new settings
        try:
            subprocess.run(['sudo', 'systemctl', 'restart', 'fotios-claude-daemon'],
                          timeout=10, capture_output=True)
        except:
            pass  # Non-critical, daemon will load on next restart

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/settings/test-telegram', methods=['POST'])
@login_required
def test_telegram():
    """Send a test notification via Telegram"""
    try:
        data = request.get_json() or {}
        token = data.get('token', '').strip()
        chat_id = data.get('chat_id', '').strip()

        if not token or not chat_id:
            return jsonify({'success': False, 'error': 'Missing token or chat_id'})

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps({
            'chat_id': chat_id,
            'text': '✅ <b>Fotios Claude System</b>\n\nTest notification successful!\nYou will receive alerts when tickets need attention.',
            'parse_mode': 'HTML'
        }).encode('utf-8')

        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read().decode('utf-8'))

        if result.get('ok'):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': result.get('description', 'Unknown error')})
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        try:
            error_json = json.loads(error_body)
            return jsonify({'success': False, 'error': error_json.get('description', 'HTTP error')})
        except:
            return jsonify({'success': False, 'error': f'HTTP {e.code}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Claude Chat Routes
@app.route('/api/claude/chat/start', methods=['POST'])
@login_required
def claude_chat_start():
    data = request.get_json() or {}
    model = data.get('model', 'sonnet')
    if model not in ('opus', 'sonnet', 'haiku'):
        model = 'sonnet'

    session_id = str(uuid.uuid4())
    sess = ClaudeChatSession()
    if sess.start(model=model):
        claude_sessions[session_id] = sess
        return jsonify({'success': True, 'session_id': session_id})
    return jsonify({'success': False, 'error': 'Failed to start'})

@app.route('/api/claude/chat/output/<session_id>')
@login_required
def claude_chat_output(session_id):
    if session_id not in claude_sessions:
        return jsonify({'error': 'Not found'}), 404
    sess = claude_sessions[session_id]
    return jsonify({'output': sess.get_output(), 'running': sess.running})

@app.route('/api/claude/chat/input/<session_id>', methods=['POST'])
@login_required
def claude_chat_input(session_id):
    if session_id not in claude_sessions:
        return jsonify({'error': 'Not found'}), 404
    data = request.json.get('input', '')
    return jsonify({'success': claude_sessions[session_id].send_input(data)})

@app.route('/api/claude/chat/resize/<session_id>', methods=['POST'])
@login_required
def claude_chat_resize(session_id):
    if session_id not in claude_sessions:
        return jsonify({'error': 'Not found'}), 404
    data = request.json
    claude_sessions[session_id].resize(data.get('rows', 24), data.get('cols', 80))
    return jsonify({'success': True})

@app.route('/api/claude/chat/stop/<session_id>', methods=['POST'])
@login_required
def claude_chat_stop(session_id):
    if session_id in claude_sessions:
        claude_sessions[session_id].stop()
        del claude_sessions[session_id]
    return jsonify({'success': True})

# Claude Assistant Page
@app.route('/claude-assistant')
@login_required
def claude_assistant():
    popup = request.args.get('popup', '0') == '1'
    mode = request.args.get('mode', '')  # blueprint, etc.
    return render_template('claude_assistant.html', user=session.get('user'), popup=popup, mode=mode)

# ============ UPDATE SYSTEM ============

GITHUB_REPO = "fotsakir/codehero"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

@app.route('/api/check-update')
@login_required
def check_update():
    """Check if a new version is available on GitHub"""
    try:
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={'User-Agent': 'FotiosClaude/' + VERSION}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

        latest_version = data.get('tag_name', '').lstrip('v')
        release_name = data.get('name', '')
        release_body = data.get('body', '')
        release_url = data.get('html_url', '')
        published_at = data.get('published_at', '')

        # Find the zip asset
        download_url = None
        for asset in data.get('assets', []):
            if asset['name'].endswith('.zip'):
                download_url = asset['browser_download_url']
                break

        # Compare versions
        def parse_version(v):
            return [int(x) for x in v.split('.') if x.isdigit()]

        current = parse_version(VERSION)
        latest = parse_version(latest_version)

        has_update = latest > current

        return jsonify({
            'has_update': has_update,
            'current_version': VERSION,
            'latest_version': latest_version,
            'release_name': release_name,
            'release_notes': release_body[:500] + ('...' if len(release_body) > 500 else ''),
            'release_url': release_url,
            'download_url': download_url,
            'published_at': published_at
        })
    except Exception as e:
        return jsonify({'error': str(e), 'has_update': False}), 500

@app.route('/api/do-update', methods=['POST'])
@login_required
def do_update():
    """Download and install the latest update"""
    try:
        # First check for update
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={'User-Agent': 'FotiosClaude/' + VERSION}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

        # Find the zip asset
        download_url = None
        zip_name = None
        for asset in data.get('assets', []):
            if asset['name'].endswith('.zip'):
                download_url = asset['browser_download_url']
                zip_name = asset['name']
                break

        if not download_url:
            return jsonify({'error': 'No download found'}), 400

        # Download to temp directory
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, zip_name)

        req = urllib.request.Request(download_url, headers={'User-Agent': 'FotiosClaude/' + VERSION})
        with urllib.request.urlopen(req, timeout=300) as response:
            with open(zip_path, 'wb') as f:
                f.write(response.read())

        # Extract
        extract_dir = os.path.join(temp_dir, 'extracted')
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(extract_dir)

        # Find the fotios-claude-system folder inside
        extracted_folder = None
        for item in os.listdir(extract_dir):
            if item.startswith('fotios-claude-system'):
                extracted_folder = os.path.join(extract_dir, item)
                break

        if not extracted_folder or not os.path.isdir(extracted_folder):
            shutil.rmtree(temp_dir)
            return jsonify({'error': 'Invalid archive structure'}), 400

        # Run upgrade.sh
        upgrade_script = os.path.join(extracted_folder, 'upgrade.sh')
        if not os.path.exists(upgrade_script):
            shutil.rmtree(temp_dir)
            return jsonify({'error': 'upgrade.sh not found'}), 400

        # Make executable and run with sudo in background
        # The upgrade restarts services, so we run it detached
        os.chmod(upgrade_script, 0o755)

        # Create a wrapper script that runs upgrade and cleans up
        wrapper_script = os.path.join(temp_dir, 'run_upgrade.sh')
        with open(wrapper_script, 'w') as f:
            f.write(f'''#!/bin/bash
cd "{extracted_folder}"
bash "{upgrade_script}" -y > /var/log/fotios-claude/upgrade.log 2>&1
rm -rf "{temp_dir}"
''')
        os.chmod(wrapper_script, 0o755)

        # Run in background with nohup
        subprocess.Popen(
            ['sudo', 'nohup', 'bash', wrapper_script],
            cwd=extracted_folder,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

        return jsonify({
            'success': True,
            'message': 'Update started. The page will reload in 30 seconds.',
            'background': True
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ WEBSOCKET ============

@socketio.on('connect')
def handle_connect():
    emit('connected', {'status': 'ok'})

@socketio.on('join_ticket')
def handle_join_ticket(data):
    ticket_id = data.get('ticket_id')
    if ticket_id:
        join_room(f'ticket_{ticket_id}')
        emit('joined', {'room': f'ticket_{ticket_id}'})

@socketio.on('leave_ticket')
def handle_leave_ticket(data):
    ticket_id = data.get('ticket_id')
    if ticket_id:
        leave_room(f'ticket_{ticket_id}')

@socketio.on('join_console')
def handle_join_console():
    join_room('console')
    emit('joined', {'room': 'console'})

# ============ TERMINAL WEBSOCKET ============

# Store active terminal sessions: {terminal_id: {'fd': master_fd, 'pid': pid, 'sid': socket_sid}}
active_terminals = {}
terminal_lock = threading.Lock()

def terminal_reader(terminal_id, master_fd, sid):
    """Background thread to read terminal output and send to client"""
    try:
        while True:
            if terminal_id not in active_terminals:
                break
            try:
                ready, _, _ = select.select([master_fd], [], [], 0.1)
                if ready:
                    data = os.read(master_fd, 4096)
                    if data:
                        socketio.emit('terminal_output', {'id': terminal_id, 'data': data.decode('utf-8', errors='replace')}, room=sid)
                    else:
                        break
            except (OSError, IOError):
                break
    except Exception as e:
        pass
    finally:
        # Cleanup when reader exits
        with terminal_lock:
            if terminal_id in active_terminals:
                term_info = active_terminals.pop(terminal_id)
                try:
                    os.close(term_info['fd'])
                except: pass
                try:
                    os.kill(term_info['pid'], signal.SIGTERM)
                except: pass
        socketio.emit('terminal_exit', {'id': terminal_id}, room=sid)

@socketio.on('terminal_create')
def handle_terminal_create(data):
    """Create a new terminal session"""
    cols = data.get('cols', 80)
    rows = data.get('rows', 24)
    sid = request.sid

    try:
        # Create pseudo-terminal
        pid, fd = pty.fork()

        if pid == 0:
            # Child process - exec shell
            os.chdir('/home/claude')
            env = os.environ.copy()
            env['TERM'] = 'xterm-256color'
            env['HOME'] = '/home/claude'
            env['USER'] = 'claude'
            env['SHELL'] = '/bin/bash'
            os.execvpe('/bin/bash', ['/bin/bash', '-l'], env)
        else:
            # Parent process
            # Set terminal size
            winsize = struct.pack('HHHH', rows, cols, 0, 0)
            fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)

            # Make fd non-blocking
            flags = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            # Generate unique terminal ID
            terminal_id = str(uuid.uuid4())[:8]

            # Store terminal info
            with terminal_lock:
                active_terminals[terminal_id] = {
                    'fd': fd,
                    'pid': pid,
                    'sid': sid
                }

            # Start reader thread
            threading.Thread(target=terminal_reader, args=(terminal_id, fd, sid), daemon=True).start()

            emit('terminal_created', {'id': terminal_id})

    except Exception as e:
        emit('terminal_error', {'error': str(e)})

@socketio.on('terminal_input')
def handle_terminal_input(data):
    """Handle input from client"""
    terminal_id = data.get('id')
    input_data = data.get('data', '')

    with terminal_lock:
        if terminal_id in active_terminals:
            fd = active_terminals[terminal_id]['fd']
            try:
                os.write(fd, input_data.encode('utf-8'))
            except (OSError, IOError):
                pass

@socketio.on('terminal_resize')
def handle_terminal_resize(data):
    """Handle terminal resize"""
    terminal_id = data.get('id')
    cols = data.get('cols', 80)
    rows = data.get('rows', 24)

    with terminal_lock:
        if terminal_id in active_terminals:
            fd = active_terminals[terminal_id]['fd']
            try:
                winsize = struct.pack('HHHH', rows, cols, 0, 0)
                fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
            except (OSError, IOError):
                pass

@socketio.on('terminal_kill')
def handle_terminal_kill(data):
    """Kill a terminal session"""
    terminal_id = data.get('id')

    with terminal_lock:
        if terminal_id in active_terminals:
            term_info = active_terminals.pop(terminal_id)
            try:
                os.close(term_info['fd'])
            except: pass
            try:
                os.kill(term_info['pid'], signal.SIGTERM)
            except: pass

@socketio.on('disconnect')
def handle_disconnect():
    """Clean up terminals when client disconnects"""
    sid = request.sid
    terminals_to_kill = []

    with terminal_lock:
        for tid, info in list(active_terminals.items()):
            if info['sid'] == sid:
                terminals_to_kill.append((tid, info))

    for tid, info in terminals_to_kill:
        with terminal_lock:
            if tid in active_terminals:
                del active_terminals[tid]
        try:
            os.close(info['fd'])
        except: pass
        try:
            os.kill(info['pid'], signal.SIGTERM)
        except: pass

# Background thread to push new messages
def message_pusher():
    last_ids = {}
    while True:
        try:
            conn = get_db()
            if conn:
                cursor = conn.cursor(dictionary=True)

                # Get active tickets with their ticket_number
                cursor.execute("SELECT id, ticket_number FROM tickets WHERE status = 'in_progress'")
                active_tickets = cursor.fetchall()

                for ticket in active_tickets:
                    tid = ticket['id']
                    ticket_number = ticket['ticket_number']
                    last_id = last_ids.get(tid, 0)

                    cursor.execute("""
                        SELECT * FROM conversation_messages
                        WHERE ticket_id = %s AND id > %s
                        ORDER BY id ASC LIMIT 20
                    """, (tid, last_id))

                    messages = cursor.fetchall()
                    for msg in messages:
                        last_ids[tid] = msg['id']
                        if msg.get('created_at'): msg['created_at'] = to_iso_utc(msg['created_at'])
                        if msg.get('tool_input') and isinstance(msg['tool_input'], str):
                            try: msg['tool_input'] = json.loads(msg['tool_input'])
                            except: pass
                        socketio.emit('new_message', msg, room=f'ticket_{tid}')
                        # Also broadcast to console with ticket_number
                        msg['ticket_number'] = ticket_number
                        socketio.emit('new_message', msg, room='console')

                cursor.close(); conn.close()
        except: pass
        time.sleep(1)

threading.Thread(target=message_pusher, daemon=True).start()


# ============ MAIN ============

if __name__ == '__main__':
    # Flask runs on internal port, OpenLiteSpeed handles SSL termination
    port = int(config.get('WEB_PORT', '5000'))
    host = config.get('WEB_HOST', '127.0.0.1')

    print(f"Starting Flask+SocketIO on http://{host}:{port}")
    print(f"OpenLiteSpeed proxies HTTPS:{config.get('ADMIN_PORT', '9453')} -> http://{host}:{port}")

    socketio.run(app, host=host, port=port, allow_unsafe_werkzeug=True)
