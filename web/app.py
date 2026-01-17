#!/usr/bin/env python3
"""
CodeHero Admin Panel v2
- Projects & Tickets management
- Real-time chat with Claude
- Background daemon control
"""

# Eventlet monkey patching - MUST be at the very top before any other imports
import eventlet
eventlet.monkey_patch()

# Read version from file
try:
    with open('/opt/codehero/VERSION', 'r') as f:
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
sys.path.insert(0, '/opt/codehero/scripts')
try:
    from smart_context import SmartContextManager
except ImportError:
    SmartContextManager = None

try:
    from lsp_manager import LSPManager, lsp_manager
    LSP_ENABLED = True
except ImportError:
    LSP_ENABLED = False
    lsp_manager = None

try:
    from git_manager import GitManager, get_git_manager
    GIT_ENABLED = True
except ImportError:
    GIT_ENABLED = False
    GitManager = None
    get_git_manager = None

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

CONFIG_FILE = "/etc/codehero/system.conf"
DAEMON_SCRIPT = "/opt/codehero/scripts/claude-daemon.py"
PID_FILE = "/var/run/codehero/daemon.pid"

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = os.urandom(24)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', allow_upgrades=True)

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

def get_next_dotnet_port():
    """Get the next available port for .NET apps (5001-5999)"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT MAX(dotnet_port) as max_port FROM projects WHERE dotnet_port IS NOT NULL")
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result and result['max_port']:
            return result['max_port'] + 1
        return 5001  # Start from 5001
    except:
        return 5001

def setup_dotnet_project(code, dotnet_port, app_path):
    """Create Nginx config and systemd service for .NET project"""
    code_lower = code.lower()

    try:
        # Read templates
        nginx_template_path = '/opt/codehero/config/nginx-dotnet-template.conf'
        systemd_template_path = '/opt/codehero/config/systemd-dotnet-template.service'

        # Create Nginx config
        with open(nginx_template_path, 'r') as f:
            nginx_config = f.read()

        nginx_config = nginx_config.replace('{PROJECT_CODE}', code_lower)
        nginx_config = nginx_config.replace('{DOTNET_PORT}', str(dotnet_port))

        # Write to temp file and move with sudo
        nginx_tmp = f'/tmp/nginx-dotnet-{code_lower}.conf'
        with open(nginx_tmp, 'w') as f:
            f.write(nginx_config)

        nginx_path = f'/etc/nginx/codehero-dotnet/{code_lower}.conf'
        os.system(f'sudo mv {nginx_tmp} {nginx_path}')

        # Create systemd service
        with open(systemd_template_path, 'r') as f:
            systemd_config = f.read()

        systemd_config = systemd_config.replace('{PROJECT_CODE}', code_lower)
        systemd_config = systemd_config.replace('{DOTNET_PORT}', str(dotnet_port))
        systemd_config = systemd_config.replace('{APP_PATH}', app_path)

        # Write to temp file and move with sudo
        service_tmp = f'/tmp/codehero-dotnet-{code_lower}.service'
        with open(service_tmp, 'w') as f:
            f.write(systemd_config)

        service_path = f'/etc/systemd/system/codehero-dotnet-{code_lower}.service'
        os.system(f'sudo mv {service_tmp} {service_path}')

        # Reload nginx and systemd
        os.system('sudo systemctl daemon-reload')
        os.system('sudo nginx -s reload 2>/dev/null || true')

        return True
    except Exception as e:
        print(f"Failed to setup .NET project configs: {e}")
        return False

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
    next_sequence = 1

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

        # Get next sequence order
        cursor.execute("""
            SELECT COALESCE(MAX(sequence_order), 0) + 1 as next_seq
            FROM tickets WHERE project_id = %s
        """, (project_id,))
        seq_result = cursor.fetchone()
        next_sequence = seq_result['next_seq'] if seq_result else 1

        cursor.close(); conn.close()
    except Exception as e:
        print(f"Project detail error: {e}")

    return render_template('project_detail.html', user=session['user'], role=session.get('role'),
                         project=project, tickets=tickets, next_sequence=next_sequence)

@app.route('/project/<int:project_id>/tickets')
@login_required
def project_tickets_view(project_id):
    """Table view of all tickets for a project with side panel"""
    project = None
    tickets = []

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
        project = cursor.fetchone()

        cursor.execute("""
            SELECT id, ticket_number, title, status, priority, ticket_type, sequence_order, is_forced, created_at, updated_at
            FROM tickets WHERE project_id = %s
            ORDER BY is_forced DESC, sequence_order IS NULL, sequence_order ASC, id ASC
        """, (project_id,))
        tickets = cursor.fetchall()

        cursor.close(); conn.close()
    except Exception as e:
        print(f"Project tickets view error: {e}")

    return render_template('project_tickets.html', user=session['user'], role=session.get('role'),
                         project=project, tickets=tickets)


@app.route('/project/<int:project_id>/progress')
@login_required
def project_progress_view(project_id):
    """Progress dashboard for a project"""
    project = None

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
        project = cursor.fetchone()
        cursor.close(); conn.close()
    except Exception as e:
        print(f"Project progress view error: {e}")

    return render_template('project_progress.html', user=session['user'], role=session.get('role'),
                         project=project)


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

def get_project_path(project_id, path_type=None):
    """Get project base path. If path_type is 'app', returns app_path first, otherwise web_path first."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT web_path, app_path FROM projects WHERE id = %s", (project_id,))
    project = cursor.fetchone()
    cursor.close()
    conn.close()

    if not project:
        return None
    if path_type == 'app':
        return project.get('app_path') or project.get('web_path')
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
    path_type = request.args.get('path_type', 'web')
    base_path = get_project_path(project_id, path_type)
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
    path_type = request.args.get('path_type', 'web')
    base_path = get_project_path(project_id, path_type)
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
    data = request.json
    path_type = data.get('path_type', 'web')
    base_path = get_project_path(project_id, path_type)
    if not base_path:
        return jsonify({'success': False, 'message': 'Project path not configured'})

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
    data = request.json
    path_type = data.get('path_type', 'web')
    base_path = get_project_path(project_id, path_type)
    if not base_path:
        return jsonify({'success': False, 'message': 'Project path not configured'})

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
    data = request.json
    path_type = data.get('path_type', 'web')
    base_path = get_project_path(project_id, path_type)
    if not base_path:
        return jsonify({'success': False, 'message': 'Project path not configured'})

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

BACKUP_DIR = "/var/backups/codehero"
MAX_BACKUPS = 30


def create_project_backup(project_id, trigger='manual', ticket_id=None):
    """Create a backup of project files and database.
    Returns (success, message, backup_filename)
    If ticket_id is provided, emits progress via WebSocket.
    """
    def emit_progress(step, percent, message):
        """Emit backup progress to ticket room"""
        if ticket_id:
            try:
                socketio.emit('backup_progress', {
                    'ticket_id': ticket_id,
                    'step': step,
                    'percent': percent,
                    'message': message
                }, room=f'ticket_{ticket_id}')
            except:
                pass

    try:
        emit_progress('init', 5, 'Starting backup...')

        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
        project = cursor.fetchone()
        cursor.close()
        conn.close()

        if not project:
            emit_progress('error', 0, 'Project not found')
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
                emit_progress('web', 15, 'Copying web files...')
                web_dest = os.path.join(temp_backup, 'web')
                shutil.copytree(project['web_path'], web_dest, dirs_exist_ok=True)

            # Copy app folder
            if project.get('app_path') and os.path.exists(project['app_path']):
                emit_progress('app', 35, 'Copying app files...')
                app_dest = os.path.join(temp_backup, 'app')
                shutil.copytree(project['app_path'], app_dest, dirs_exist_ok=True)

            # Export database if exists
            if project.get('db_name') and project.get('db_user') and project.get('db_password'):
                emit_progress('db', 55, 'Exporting database...')
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
                emit_progress('db_data', 65, 'Exporting database data...')
                data_file = os.path.join(db_dir, 'data.sql')
                data_cmd = f"mysqldump -h {db_host} -u {db_user} -p'{db_pass}' --no-create-info {db_name} 2>/dev/null"
                result = subprocess.run(data_cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    with open(data_file, 'w') as f:
                        f.write(result.stdout)

            # Create backup info
            emit_progress('info', 75, 'Creating backup info...')
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
            emit_progress('zip', 85, 'Compressing backup...')
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_backup):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, temp_backup)
                        zipf.write(file_path, arc_name)

            # Cleanup old backups (keep last MAX_BACKUPS)
            cleanup_old_backups(backup_subdir)

            emit_progress('done', 100, f'Backup complete: {backup_name}')
            return True, f"Backup created: {backup_name}", backup_name

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    except Exception as e:
        emit_progress('error', 0, f'Backup failed: {str(e)}')
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
    data = request.get_json(silent=True) or {}
    ticket_id = data.get('ticket_id')

    # Run backup in background thread with progress
    def async_backup(proj_id, tid):
        try:
            create_project_backup(proj_id, 'manual', ticket_id=tid)
        except Exception as e:
            print(f"Background backup error: {e}")

    threading.Thread(target=async_backup, args=(project_id, ticket_id), daemon=True).start()
    return jsonify({'success': True, 'message': 'Backup started', 'filename': None})


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


# ==========================================
# GIT VERSION CONTROL ROUTES
# ==========================================

@app.route('/project/<int:project_id>/git')
@login_required
def project_git_history(project_id):
    """Git history page for a project"""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT p.*, pgr.id as repo_id, pgr.repo_path, pgr.last_commit_hash,
               pgr.last_commit_at, pgr.total_commits, pgr.status as git_status
        FROM projects p
        LEFT JOIN project_git_repos pgr ON pgr.project_id = p.id
        WHERE p.id = %s
    """, (project_id,))
    project = cursor.fetchone()
    cursor.close()
    conn.close()

    if not project:
        return "Project not found", 404

    return render_template('project_git.html', project=project)


@app.route('/project/<int:project_id>/phpmyadmin')
@login_required
def project_phpmyadmin(project_id):
    """Redirect to phpMyAdmin with project database credentials"""
    import base64
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT db_name, db_user, db_password, db_host FROM projects WHERE id = %s", (project_id,))
    project = cursor.fetchone()
    cursor.close()
    conn.close()

    if not project or not project.get('db_name'):
        return "Project has no database configured", 404

    # Encode credentials for signon
    user = base64.b64encode((project.get('db_user') or 'root').encode()).decode()
    password = base64.b64encode((project.get('db_password') or '').encode()).decode()
    db = base64.b64encode(project['db_name'].encode()).decode()

    # Get host without port for phpMyAdmin URL
    host = request.host.split(':')[0]

    return redirect(f"https://{host}:9454/signon.php?u={user}&p={password}&db={db}")


@app.route('/api/project/<int:project_id>/git/commits', methods=['GET'])
@login_required
def api_git_commits(project_id):
    """Get commits for a project"""
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))

        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Get project path
        cursor.execute("""
            SELECT web_path, app_path, project_type, tech_stack
            FROM projects WHERE id = %s
        """, (project_id,))
        project = cursor.fetchone()

        if not project:
            return jsonify({'success': False, 'message': 'Project not found'})

        git_path = project.get('web_path') or project.get('app_path')
        if not git_path or not GIT_ENABLED:
            return jsonify({'success': False, 'message': 'Git not available for this project'})

        gm = GitManager(
            git_path,
            project.get('project_type', 'web'),
            project.get('tech_stack', '')
        )

        if not gm.is_initialized():
            return jsonify({'success': False, 'message': 'Git repository not initialized'})

        commits = gm.get_commits(limit=limit + offset)
        commits = commits[offset:offset + limit] if offset else commits[:limit]

        # Enrich with database info (ticket links)
        cursor.execute("""
            SELECT pgc.commit_hash, t.ticket_number, t.title as ticket_title
            FROM project_git_commits pgc
            LEFT JOIN tickets t ON pgc.ticket_id = t.id
            WHERE pgc.project_id = %s
        """, (project_id,))
        db_commits = {row['commit_hash']: row for row in cursor.fetchall()}

        for commit in commits:
            if commit['hash'] in db_commits:
                commit['ticket_number'] = db_commits[commit['hash']].get('ticket_number')
                commit['ticket_title'] = db_commits[commit['hash']].get('ticket_title')

        cursor.close()
        conn.close()

        return jsonify({'success': True, 'commits': commits})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/project/<int:project_id>/git/commit/<commit_hash>', methods=['GET'])
@login_required
def api_git_commit_detail(project_id, commit_hash):
    """Get details of a specific commit"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT web_path, app_path, project_type, tech_stack
            FROM projects WHERE id = %s
        """, (project_id,))
        project = cursor.fetchone()
        cursor.close()
        conn.close()

        if not project:
            return jsonify({'success': False, 'message': 'Project not found'})

        git_path = project.get('web_path') or project.get('app_path')
        if not git_path or not GIT_ENABLED:
            return jsonify({'success': False, 'message': 'Git not available'})

        gm = GitManager(
            git_path,
            project.get('project_type', 'web'),
            project.get('tech_stack', '')
        )

        commit = gm.get_commit_detail(commit_hash)
        if not commit:
            return jsonify({'success': False, 'message': 'Commit not found'})

        return jsonify({'success': True, 'commit': commit})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/project/<int:project_id>/git/diff/<commit_hash>', methods=['GET'])
@login_required
def api_git_diff(project_id, commit_hash):
    """Get diff for a commit"""
    try:
        file_path = request.args.get('file')

        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT web_path, app_path, project_type, tech_stack
            FROM projects WHERE id = %s
        """, (project_id,))
        project = cursor.fetchone()
        cursor.close()
        conn.close()

        if not project:
            return jsonify({'success': False, 'message': 'Project not found'})

        git_path = project.get('web_path') or project.get('app_path')
        if not git_path or not GIT_ENABLED:
            return jsonify({'success': False, 'message': 'Git not available'})

        gm = GitManager(
            git_path,
            project.get('project_type', 'web'),
            project.get('tech_stack', '')
        )

        diff = gm.get_diff(commit_hash, file_path)
        if diff is None:
            return jsonify({'success': False, 'message': 'Could not get diff'})

        return jsonify({'success': True, 'diff': diff})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/project/<int:project_id>/git/status', methods=['GET'])
@login_required
def api_git_status(project_id):
    """Get current Git status"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT web_path, app_path, project_type, tech_stack
            FROM projects WHERE id = %s
        """, (project_id,))
        project = cursor.fetchone()
        cursor.close()
        conn.close()

        if not project:
            return jsonify({'success': False, 'message': 'Project not found'})

        git_path = project.get('web_path') or project.get('app_path')
        if not git_path or not GIT_ENABLED:
            return jsonify({'success': False, 'message': 'Git not available'})

        gm = GitManager(
            git_path,
            project.get('project_type', 'web'),
            project.get('tech_stack', '')
        )

        if not gm.is_initialized():
            return jsonify({'success': False, 'initialized': False, 'message': 'Git not initialized'})

        status = gm.get_status()
        return jsonify({'success': True, 'initialized': True, 'status': status})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/project/<int:project_id>/git/init', methods=['POST'])
@login_required
def api_git_init(project_id):
    """Initialize Git repository for a project"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT id, web_path, app_path, project_type, tech_stack
            FROM projects WHERE id = %s
        """, (project_id,))
        project = cursor.fetchone()

        if not project:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Project not found'})

        git_path = project.get('web_path') or project.get('app_path')
        if not git_path or not GIT_ENABLED:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Git not available'})

        gm = GitManager(
            git_path,
            project.get('project_type', 'web'),
            project.get('tech_stack', '')
        )

        success, msg = gm.init_repo()
        if success:
            # Create repo record
            cursor.execute("""
                INSERT INTO project_git_repos (project_id, repo_path, path_type, status)
                VALUES (%s, %s, 'web', 'active')
                ON DUPLICATE KEY UPDATE status = 'active'
            """, (project_id, git_path))
            conn.commit()

        cursor.close()
        conn.close()

        return jsonify({'success': success, 'message': msg})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/project/<int:project_id>/git/rollback', methods=['POST'])
@login_required
def api_git_rollback(project_id):
    """Rollback to a specific commit"""
    try:
        data = request.get_json()
        target_hash = data.get('commit_hash')
        reason = data.get('reason', 'Manual rollback')

        if not target_hash:
            return jsonify({'success': False, 'message': 'Commit hash required'})

        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT id, web_path, app_path, project_type, tech_stack
            FROM projects WHERE id = %s
        """, (project_id,))
        project = cursor.fetchone()

        if not project:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Project not found'})

        git_path = project.get('web_path') or project.get('app_path')
        if not git_path or not GIT_ENABLED:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Git not available'})

        gm = GitManager(
            git_path,
            project.get('project_type', 'web'),
            project.get('tech_stack', '')
        )

        if not gm.is_initialized():
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Git not initialized'})

        success, result = gm.rollback_to_commit(target_hash, reason)

        if success:
            # Record rollback commit
            cursor.execute("""
                SELECT id FROM project_git_repos WHERE project_id = %s
            """, (project_id,))
            repo = cursor.fetchone()

            if repo:
                # Get new commit hash (result contains the new commit hash)
                new_hash = result
                cursor.execute("""
                    INSERT INTO project_git_commits
                    (project_id, repo_id, commit_hash, short_hash, message,
                     is_rollback, rollback_to_hash)
                    VALUES (%s, %s, %s, %s, %s, 1, %s)
                """, (
                    project_id, repo['id'], new_hash, new_hash[:7],
                    f"Rollback to {target_hash[:7]}: {reason}", target_hash
                ))

                cursor.execute("""
                    UPDATE project_git_repos
                    SET last_commit_hash = %s, last_commit_at = NOW(),
                        total_commits = total_commits + 1
                    WHERE id = %s
                """, (new_hash, repo['id']))
                conn.commit()

        cursor.close()
        conn.close()

        return jsonify({
            'success': success,
            'message': 'Rollback successful' if success else result,
            'commit_hash': result if success else None
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/project/<int:project_id>/git/file/<commit_hash>', methods=['GET'])
@login_required
def api_git_file_at_commit(project_id, commit_hash):
    """Get file content at a specific commit"""
    try:
        file_path = request.args.get('path')
        if not file_path:
            return jsonify({'success': False, 'message': 'File path required'})

        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT web_path, app_path, project_type, tech_stack
            FROM projects WHERE id = %s
        """, (project_id,))
        project = cursor.fetchone()
        cursor.close()
        conn.close()

        if not project:
            return jsonify({'success': False, 'message': 'Project not found'})

        git_path = project.get('web_path') or project.get('app_path')
        if not git_path or not GIT_ENABLED:
            return jsonify({'success': False, 'message': 'Git not available'})

        gm = GitManager(
            git_path,
            project.get('project_type', 'web'),
            project.get('tech_stack', '')
        )

        content = gm.get_file_at_commit(commit_hash, file_path)
        if content is None:
            return jsonify({'success': False, 'message': 'Could not get file'})

        return jsonify({'success': True, 'content': content})

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

        # Determine upload directory based on path_type parameter
        path_type = request.form.get('path_type', 'web')
        if path_type == 'app':
            upload_dir = project.get('app_path') or project.get('web_path')
        else:
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

        # Determine which path to use based on path_type parameter
        path_type = request.args.get('path_type', 'web')
        if path_type == 'app':
            base_path = project.get('app_path') or project.get('web_path')
        else:
            base_path = project.get('web_path') or project.get('app_path')

        if not base_path or not os.path.exists(base_path):
            return jsonify({'success': True, 'files': [], 'base_path': base_path, 'path_type': path_type})

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

        data = request.get_json()

        # Determine base path from path_type parameter
        path_type = data.get('path_type', 'web')
        if path_type == 'app':
            base_path = project.get('app_path') or project.get('web_path')
        else:
            base_path = project.get('web_path') or project.get('app_path')
        if not base_path:
            return jsonify({'success': False, 'message': 'No project path configured'})

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
        default_execution_mode = data.get('default_execution_mode', 'autonomous')
        skip_database = data.get('skip_database', False)

        # Validate execution mode
        if default_execution_mode not in ('autonomous', 'supervised'):
            default_execution_mode = 'autonomous'

        # Android settings
        android_device_type = data.get('android_device_type') or 'none'
        android_remote_host = (data.get('android_remote_host') or '').strip() or None
        android_remote_port = data.get('android_remote_port') or 5555
        android_screen_size = data.get('android_screen_size') or 'phone'

        # Validate ai_model
        if ai_model not in ('opus', 'sonnet', 'haiku'):
            ai_model = 'sonnet'

        # Validate android settings
        if android_device_type not in ('none', 'server', 'remote'):
            android_device_type = 'none'
        if android_screen_size not in ('phone', 'phone_small', 'tablet_7', 'tablet_10'):
            android_screen_size = 'phone'

        if not name or not code:
            return jsonify({'success': False, 'message': 'Name and code required'})

        if not code.isalnum() or len(code) > 10:
            return jsonify({'success': False, 'message': 'Code must be alphanumeric, max 10 chars'})

        # Default paths based on type
        if not web_path and project_type in ('web', 'hybrid'):
            web_path = f'/var/www/projects/{code.lower()}'
        if not app_path and project_type in ('app', 'hybrid', 'api', 'capacitor', 'react_native', 'flutter', 'native_android', 'dotnet'):
            app_path = f'/opt/apps/{code.lower()}'

        # .NET specific: get next available port
        dotnet_port = None
        if project_type == 'dotnet':
            dotnet_port = get_next_dotnet_port()

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
                    ai_model, default_execution_mode, android_device_type, android_remote_host, android_remote_port, android_screen_size,
                    dotnet_port, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'localhost', %s, %s, %s, %s, %s, %s, %s, 'active', NOW(), NOW())
            """, (name, code, description, project_type, tech_stack or None,
                  web_path or None, app_path or None, preview_url or None, context or None,
                  db_name, db_user, db_password, ai_model, default_execution_mode,
                  android_device_type, android_remote_host, android_remote_port, android_screen_size,
                  dotnet_port))
            conn.commit()
            project_id = cursor.lastrowid

            # Create directories with proper permissions
            if web_path:
                os.makedirs(web_path, mode=0o2775, exist_ok=True)
                os.chmod(web_path, 0o2775)  # Ensure setgid and group write
            if app_path:
                os.makedirs(app_path, mode=0o2775, exist_ok=True)
                os.chmod(app_path, 0o2775)  # Ensure setgid and group write

            # Setup .NET project Nginx and systemd configs
            if project_type == 'dotnet' and dotnet_port and app_path:
                setup_dotnet_project(code, dotnet_port, app_path)

            # Initialize Git repository for the project
            git_initialized = False
            if GIT_ENABLED:
                git_path = web_path or app_path
                if git_path:
                    try:
                        gm = GitManager(git_path, project_type or 'web', tech_stack or '')
                        success, msg = gm.init_repo()
                        if success:
                            git_initialized = True
                            # Record in database
                            cursor.execute("""
                                INSERT INTO project_git_repos (project_id, repo_path, path_type, status)
                                VALUES (%s, %s, %s, 'active')
                            """, (project_id, git_path, 'web' if web_path else 'app'))
                            conn.commit()
                            print(f"[Git] Initialized repo for project {code} at {git_path}")
                        else:
                            print(f"[Git] Failed to init repo for {code}: {msg}")
                    except Exception as e:
                        print(f"[Git] Error initializing repo for {code}: {e}")

            cursor.close(); conn.close()

            result = {'success': True, 'project_id': project_id, 'message': 'Project created'}
            if db_name:
                result['db_created'] = True
                result['db_name'] = db_name
                result['db_user'] = db_user
            if dotnet_port:
                result['dotnet_port'] = dotnet_port
            if git_initialized:
                result['git_initialized'] = True
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
    if 'default_test_command' in data:
        updates.append("default_test_command = %s")
        test_cmd = data['default_test_command']
        params.append(test_cmd.strip() if test_cmd else None)
    if 'default_execution_mode' in data:
        exec_mode = data['default_execution_mode']
        if exec_mode in ('autonomous', 'supervised'):
            updates.append("default_execution_mode = %s")
            params.append(exec_mode)

    # Android settings
    if 'android_device_type' in data:
        device_type = data['android_device_type']
        if device_type in ('none', 'server', 'remote'):
            updates.append("android_device_type = %s")
            params.append(device_type)
    if 'android_remote_host' in data:
        updates.append("android_remote_host = %s")
        params.append(data['android_remote_host'].strip() if data['android_remote_host'] else None)
    if 'android_remote_port' in data:
        updates.append("android_remote_port = %s")
        params.append(data['android_remote_port'] or 5555)
    if 'android_screen_size' in data:
        screen_size = data['android_screen_size']
        if screen_size in ('phone', 'phone_small', 'tablet_7', 'tablet_10'):
            updates.append("android_screen_size = %s")
            params.append(screen_size)

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
    project_tickets = []
    current_deps = []

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT t.*, p.name as project_name, p.code as project_code,
                   p.web_path, p.app_path,
                   COALESCE(p.web_path, p.app_path) as project_path,
                   p.preview_url, p.ai_model as project_ai_model,
                   p.default_execution_mode as project_default_execution_mode,
                   p.project_type, p.android_device_type, p.android_screen_size,
                   p.db_name, p.db_user, p.db_host
            FROM tickets t JOIN projects p ON t.project_id = p.id
            WHERE t.id = %s
        """, (ticket_id,))
        ticket = cursor.fetchone()

        if ticket:
            # Generate default preview_url if not set
            if not ticket.get('preview_url') and ticket.get('project_code'):
                host = request.host.split(':')[0]  # Get hostname without port
                ticket['preview_url'] = f"https://{host}:9867/{ticket['project_code'].lower()}"

            # Parse pending_permission JSON if present
            if ticket.get('pending_permission'):
                if isinstance(ticket['pending_permission'], str):
                    try:
                        ticket['pending_permission'] = json.loads(ticket['pending_permission'])
                    except:
                        ticket['pending_permission'] = None
            cursor.execute("""
                SELECT * FROM conversation_messages
                WHERE ticket_id = %s ORDER BY created_at ASC
            """, (ticket_id,))
            messages = cursor.fetchall()

            # Get other tickets in the same project (for dependencies/parent selection)
            cursor.execute("""
                SELECT id, ticket_number, title, status, parent_ticket_id
                FROM tickets WHERE project_id = %s AND id != %s
                ORDER BY sequence_order ASC, created_at ASC
            """, (ticket['project_id'], ticket_id))
            project_tickets = cursor.fetchall()

            # Get current dependencies
            cursor.execute("""
                SELECT depends_on_ticket_id FROM ticket_dependencies WHERE ticket_id = %s
            """, (ticket_id,))
            current_deps = [row['depends_on_ticket_id'] for row in cursor.fetchall()]

        cursor.close(); conn.close()
    except Exception as e:
        print(f"Ticket detail error: {e}")

    embed = request.args.get('embed') == '1'
    return render_template('ticket_detail.html', user=session['user'], role=session.get('role'),
                         ticket=ticket, messages=messages, embed=embed,
                         project_tickets=project_tickets, current_deps=set(current_deps))

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

        # New fields for ticket sequencing & types
        ticket_type = data.get('ticket_type', 'task')
        sequence_order = data.get('sequence_order')
        depends_on = data.get('depends_on', [])  # List of ticket IDs or ticket numbers
        parent_ticket_id = data.get('parent_ticket_id')
        test_command = data.get('test_command')
        require_tests_pass = data.get('require_tests_pass', False)
        max_retries = data.get('max_retries', 3)
        max_duration_minutes = data.get('max_duration_minutes', 60)
        start_when_ready = data.get('start_when_ready', True)  # Auto-start after deps complete
        deps_include_awaiting = data.get('deps_include_awaiting', False)  # Relaxed mode for deps
        execution_mode = data.get('execution_mode')  # None = inherit, 'autonomous', or 'supervised'

        # Validate execution_mode (None = inherit from project)
        if execution_mode and execution_mode not in ('autonomous', 'supervised'):
            execution_mode = None

        # Validate ai_model
        if ai_model and ai_model not in ('opus', 'sonnet', 'haiku'):
            ai_model = None

        # Validate ticket_type
        valid_types = ('feature', 'bug', 'debug', 'rnd', 'task', 'improvement', 'docs')
        if ticket_type not in valid_types:
            ticket_type = 'task'

        if not project_id or not title:
            return jsonify({'success': False, 'message': 'Project and title required'})

        try:
            # Get project info
            cursor.execute("SELECT code, default_test_command FROM projects WHERE id = %s", (project_id,))
            project = cursor.fetchone()
            if not project:
                return jsonify({'success': False, 'message': 'Project not found'})

            ticket_number = generate_ticket_number(project['code'], cursor)

            # Use project's default test command if not specified
            if test_command is None and project.get('default_test_command'):
                test_command = project['default_test_command']

            cursor.execute("""
                INSERT INTO tickets (project_id, ticket_number, title, description, priority, ai_model,
                                     ticket_type, sequence_order, parent_ticket_id, test_command,
                                     require_tests_pass, max_retries, max_duration_minutes, start_when_ready,
                                     deps_include_awaiting, execution_mode, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'open', NOW(), NOW())
            """, (project_id, ticket_number, title, description, priority, ai_model,
                  ticket_type, sequence_order, parent_ticket_id, test_command,
                  require_tests_pass, max_retries, max_duration_minutes, start_when_ready, deps_include_awaiting,
                  execution_mode))
            conn.commit()
            ticket_id = cursor.lastrowid

            # Handle dependencies
            if depends_on:
                for dep in depends_on:
                    # dep can be ticket_id (int) or ticket_number (string)
                    if isinstance(dep, int):
                        dep_id = dep
                    else:
                        # Look up by ticket_number
                        cursor.execute("SELECT id FROM tickets WHERE ticket_number = %s", (dep,))
                        dep_ticket = cursor.fetchone()
                        dep_id = dep_ticket['id'] if dep_ticket else None

                    if dep_id:
                        cursor.execute("""
                            INSERT IGNORE INTO ticket_dependencies (ticket_id, depends_on_ticket_id)
                            VALUES (%s, %s)
                        """, (ticket_id, dep_id))
                conn.commit()

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
            WHERE t.project_id = %s
            ORDER BY t.is_forced DESC, t.sequence_order IS NULL, t.sequence_order ASC, t.id ASC
        """, (project_id,))
    else:
        cursor.execute("""
            SELECT t.*, p.name as project_name FROM tickets t
            JOIN projects p ON t.project_id = p.id
            ORDER BY t.is_forced DESC, t.sequence_order IS NULL, t.sequence_order ASC, t.id ASC
        """)
    
    tickets = cursor.fetchall()
    cursor.close(); conn.close()
    
    for t in tickets:
        for k, v in t.items():
            if hasattr(v, 'isoformat'): t[k] = v.isoformat()
    
    return jsonify(tickets)

@app.route('/api/ticket/<int:ticket_id>')
@login_required
def get_ticket_detail(ticket_id):
    """Get ticket details with messages for side panel"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Get ticket
        cursor.execute("SELECT * FROM tickets WHERE id = %s", (ticket_id,))
        ticket = cursor.fetchone()

        if not ticket:
            cursor.close(); conn.close()
            return jsonify({'error': 'Ticket not found'}), 404

        # Get messages
        cursor.execute("""
            SELECT id, role, content, created_at FROM conversation_messages
            WHERE ticket_id = %s ORDER BY created_at ASC
        """, (ticket_id,))
        messages = cursor.fetchall()

        cursor.close(); conn.close()

        # Convert datetimes
        for key in ['created_at', 'updated_at', 'started_at', 'completed_at']:
            if ticket.get(key):
                ticket[key] = to_iso_utc(ticket[key])

        for m in messages:
            if m.get('created_at'):
                m['created_at'] = to_iso_utc(m['created_at'])

        ticket['messages'] = messages
        return jsonify(ticket)

    except Exception as e:
        print(f"Get ticket detail error: {e}")
        return jsonify({'error': str(e)}), 500

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

        # Close ticket first (fast operation)
        cursor.execute("""
            UPDATE tickets SET status = 'done', closed_at = NOW(),
            closed_by = %s, close_reason = %s, updated_at = NOW()
            WHERE id = %s
        """, (session['user'], reason, ticket_id))
        conn.commit()
        cursor.close(); conn.close()

        # Create backup in background thread (slow operation)
        if ticket:
            def async_backup(project_id, tid):
                try:
                    create_project_backup(project_id, 'close', ticket_id=tid)
                except Exception as e:
                    print(f"Background backup error: {e}")
            threading.Thread(target=async_backup, args=(ticket['project_id'], ticket_id), daemon=True).start()

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/ticket/<int:ticket_id>/kill', methods=['POST'])
@login_required
def kill_ticket(ticket_id):
    """Kill Switch - Stop Claude process immediately and pause ticket"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Get ticket info
        cursor.execute("SELECT * FROM tickets WHERE id = %s", (ticket_id,))
        ticket = cursor.fetchone()

        if not ticket:
            cursor.close(); conn.close()
            return jsonify({'success': False, 'message': 'Ticket not found'})

        if ticket['status'] != 'in_progress':
            cursor.close(); conn.close()
            return jsonify({'success': False, 'message': 'Ticket is not in progress'})

        # Update ticket status FIRST (so daemon doesn't mark as failed)
        cursor.execute("""
            UPDATE tickets SET status = 'awaiting_input', updated_at = NOW()
            WHERE id = %s
        """, (ticket_id,))
        conn.commit()

        # INSTANT KILL: Send SIGTERM to Claude process
        killed = kill_claude_process(ticket_id)

        # Save system message
        system_msg = '⏹️ Kill switch activated - Process stopped' if killed else '⏹️ Kill switch activated - Waiting for process to stop'
        cursor.execute("""
            INSERT INTO conversation_messages (ticket_id, role, content, created_at)
            VALUES (%s, 'system', %s, NOW())
        """, (ticket_id, system_msg))
        sys_msg_id = cursor.lastrowid

        # Add log entry
        log_msg = f"⏹️ Kill switch activated - Ticket {ticket['ticket_number']} paused"
        cursor.execute("""
            INSERT INTO daemon_logs (ticket_id, log_type, message, created_at)
            VALUES (%s, 'warning', %s, NOW())
        """, (ticket_id, log_msg))
        conn.commit()

        # Broadcast system message
        cursor.execute("SELECT * FROM conversation_messages WHERE id = %s", (sys_msg_id,))
        sys_msg_obj = cursor.fetchone()
        if sys_msg_obj:
            if sys_msg_obj.get('created_at'): sys_msg_obj['created_at'] = to_iso_utc(sys_msg_obj['created_at'])
            sys_msg_obj['ticket_number'] = ticket['ticket_number']
            socketio.emit('new_message', sys_msg_obj, room=f'ticket_{ticket_id}')
            socketio.emit('new_message', sys_msg_obj, room='console')

        # Broadcast status change
        socketio.emit('ticket_status', {'ticket_id': ticket_id, 'status': 'awaiting_input'}, room=f'ticket_{ticket_id}')

        # Broadcast log to console
        socketio.emit('new_log', {'log_type': 'warning', 'message': log_msg, 'created_at': datetime.now().isoformat() + 'Z'}, room='console')

        cursor.close(); conn.close()
        return jsonify({'success': True, 'message': 'Process stopped', 'killed': killed})
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

        # Approve ticket first (fast operation)
        cursor.execute("""
            UPDATE tickets SET status = 'done', closed_at = NOW(),
            closed_by = %s, close_reason = 'approved', review_deadline = NULL, updated_at = NOW()
            WHERE id = %s
        """, (session['user'], ticket_id))
        conn.commit()
        cursor.close()
        conn.close()

        # Create backup in background thread (slow operation)
        def async_backup(project_id, tid):
            try:
                create_project_backup(project_id, 'close', ticket_id=tid)
            except Exception as e:
                print(f"Background backup error: {e}")
        threading.Thread(target=async_backup, args=(ticket['project_id'], ticket_id), daemon=True).start()

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

        # Update ticket status first (fast)
        # Update ticket status and reset retry count
        cursor.execute("""
            UPDATE tickets SET status = 'open', retry_count = 0, closed_at = NULL,
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

        # Create backup in background thread (slow operation)
        if ticket:
            def async_backup(project_id, tid):
                try:
                    create_project_backup(project_id, 'reopen', ticket_id=tid)
                except Exception as e:
                    print(f"Background backup error: {e}")
            threading.Thread(target=async_backup, args=(ticket['project_id'], ticket_id), daemon=True).start()

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
    """Update ticket settings - all editable fields"""
    try:
        data = request.get_json()
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        updates = []
        params = []

        # Title
        if 'title' in data and data['title']:
            updates.append("title = %s")
            params.append(data['title'].strip())

        # Description
        if 'description' in data:
            updates.append("description = %s")
            params.append(data['description'].strip() if data['description'] else '')

        # Priority
        if 'priority' in data:
            if data['priority'] in ('low', 'medium', 'high', 'critical'):
                updates.append("priority = %s")
                params.append(data['priority'])

        # Status
        if 'status' in data:
            valid_statuses = ('open', 'in_progress', 'awaiting_input', 'done', 'skipped', 'failed')
            if data['status'] in valid_statuses:
                updates.append("status = %s")
                params.append(data['status'])

        # Ticket Type
        if 'ticket_type' in data:
            valid_types = ('feature', 'bug', 'debug', 'rnd', 'task', 'improvement', 'docs')
            if data['ticket_type'] in valid_types:
                updates.append("ticket_type = %s")
                params.append(data['ticket_type'])

        # Execution Mode (NULL = inherit from project)
        if 'execution_mode' in data:
            if data['execution_mode'] in ('autonomous', 'supervised'):
                updates.append("execution_mode = %s")
                params.append(data['execution_mode'])
            elif data['execution_mode'] is None or data['execution_mode'] == '':
                updates.append("execution_mode = NULL")

        # Sequence Order
        if 'sequence_order' in data:
            seq = data['sequence_order']
            if seq is None or seq == '':
                updates.append("sequence_order = NULL")
            else:
                updates.append("sequence_order = %s")
                params.append(int(seq))

        # Parent Ticket
        if 'parent_ticket_id' in data:
            parent = data['parent_ticket_id']
            if parent is None or parent == '' or parent == 0:
                updates.append("parent_ticket_id = NULL")
            else:
                updates.append("parent_ticket_id = %s")
                params.append(int(parent))

        # Start When Ready
        if 'start_when_ready' in data:
            updates.append("start_when_ready = %s")
            params.append(1 if data['start_when_ready'] else 0)

        # Deps Include Awaiting (relaxed mode)
        if 'deps_include_awaiting' in data:
            updates.append("deps_include_awaiting = %s")
            params.append(1 if data['deps_include_awaiting'] else 0)

        # AI Model
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

        # Handle dependencies separately (many-to-many)
        if 'depends_on' in data:
            # Clear existing dependencies
            cursor.execute("DELETE FROM ticket_dependencies WHERE ticket_id = %s", (ticket_id,))
            # Add new dependencies
            depends_on = data['depends_on'] or []
            for dep_id in depends_on:
                if dep_id and int(dep_id) != ticket_id:  # Can't depend on self
                    cursor.execute("""
                        INSERT IGNORE INTO ticket_dependencies (ticket_id, depends_on_ticket_id)
                        VALUES (%s, %s)
                    """, (ticket_id, int(dep_id)))

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# ============ TICKET SEQUENCING & TYPES ============

@app.route('/api/tickets/reorder', methods=['POST'])
@login_required
def reorder_tickets():
    """Bulk update sequence_order for multiple tickets (for drag-drop reordering)"""
    try:
        data = request.get_json()
        tickets = data.get('tickets', [])  # List of {ticket_id, sequence_order}

        if not tickets:
            return jsonify({'success': False, 'message': 'No tickets provided'})

        conn = get_db()
        cursor = conn.cursor()

        for item in tickets:
            ticket_id = item.get('ticket_id')
            seq = item.get('sequence_order')
            if ticket_id is not None and seq is not None:
                cursor.execute("""
                    UPDATE tickets SET sequence_order = %s, updated_at = NOW()
                    WHERE id = %s
                """, (seq, ticket_id))

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'updated': len(tickets)})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/ticket/<int:ticket_id>/type', methods=['POST'])
@login_required
def update_ticket_type(ticket_id):
    """Update ticket type"""
    try:
        data = request.get_json()
        ticket_type = data.get('ticket_type')

        valid_types = ('feature', 'bug', 'debug', 'rnd', 'task', 'improvement', 'docs')
        if ticket_type not in valid_types:
            return jsonify({'success': False, 'message': f'Invalid ticket type. Valid: {valid_types}'})

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tickets SET ticket_type = %s, updated_at = NOW()
            WHERE id = %s
        """, (ticket_type, ticket_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/ticket/<int:ticket_id>/force', methods=['POST'])
@login_required
def force_ticket(ticket_id):
    """Set is_forced = TRUE to move ticket to front of queue"""
    try:
        data = request.get_json() or {}
        force = data.get('force', True)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tickets SET is_forced = %s, updated_at = NOW()
            WHERE id = %s
        """, (force, ticket_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'is_forced': force})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/ticket/<int:ticket_id>/permission', methods=['POST'])
@login_required
def handle_permission(ticket_id):
    """Handle permission approval/rejection for supervised mode"""
    try:
        data = request.get_json() or {}
        action = data.get('action')  # 'approve', 'approve_all', 'reject'

        if action not in ('approve', 'approve_all', 'reject'):
            return jsonify({'success': False, 'message': 'Invalid action'})

        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Get ticket with pending permission
        cursor.execute("""
            SELECT id, pending_permission, approved_permissions, execution_mode
            FROM tickets WHERE id = %s
        """, (ticket_id,))
        ticket = cursor.fetchone()

        if not ticket:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Ticket not found'})

        pending = ticket.get('pending_permission')
        if isinstance(pending, str):
            pending = json.loads(pending) if pending else None

        if not pending:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'No pending permission'})

        if action == 'reject':
            # Clear pending permission and keep ticket in awaiting_input
            cursor.execute("""
                UPDATE tickets SET pending_permission = NULL, updated_at = NOW()
                WHERE id = %s
            """, (ticket_id,))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True, 'action': 'rejected'})

        # Approve - add to approved_permissions
        approved = ticket.get('approved_permissions')
        if isinstance(approved, str):
            approved = json.loads(approved) if approved else []
        if not approved:
            approved = []

        tool = pending.get('tool', '')
        tool_input = pending.get('input', {})

        if action == 'approve':
            # Add specific approval for this exact operation
            new_perm = {'tool': tool, 'pattern': '*', 'once': True}
            approved.append(new_perm)
        elif action == 'approve_all':
            # Add pattern-based approval for similar operations
            if tool == 'Bash':
                cmd = tool_input.get('command', '')
                # Extract command prefix (e.g., "npm install" -> "npm *")
                parts = cmd.split()
                if len(parts) >= 1:
                    pattern = parts[0] + ' *'
                else:
                    pattern = '*'
                new_perm = {'tool': tool, 'pattern': pattern}
            elif tool in ('Edit', 'Write'):
                # Approve edits to same directory
                file_path = tool_input.get('file_path', '')
                import os
                dir_path = os.path.dirname(file_path)
                pattern = dir_path + '/*' if dir_path else '*'
                new_perm = {'tool': tool, 'pattern': pattern}
            else:
                new_perm = {'tool': tool, 'pattern': '*'}
            approved.append(new_perm)

        # Save approved permissions file for the hook to read
        perm_file = f"/var/run/codehero/permissions_{ticket_id}.json"
        import os
        os.makedirs('/var/run/codehero', exist_ok=True)
        with open(perm_file, 'w') as f:
            json.dump(approved, f)

        # Clear pending permission and set status to open for daemon to pick up
        cursor.execute("""
            UPDATE tickets
            SET pending_permission = NULL,
                approved_permissions = %s,
                status = 'open',
                updated_at = NOW()
            WHERE id = %s
        """, (json.dumps(approved), ticket_id))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True, 'action': action, 'approved': approved})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/ticket/<int:ticket_id>/start', methods=['POST'])
@login_required
def start_ticket(ticket_id):
    """Start ticket: set status='open' and is_forced=TRUE to queue it next.
    For sub-tickets, starts the parent instead."""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Check current status and parent
        cursor.execute("""
            SELECT t.id, t.status, t.project_id, t.parent_ticket_id, t.ticket_number,
                   p.ticket_number as parent_ticket_number, p.status as parent_status
            FROM tickets t
            LEFT JOIN tickets p ON t.parent_ticket_id = p.id
            WHERE t.id = %s
        """, (ticket_id,))
        ticket = cursor.fetchone()

        if not ticket:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Ticket not found'})

        # If this is a sub-ticket, start the parent instead
        target_id = ticket_id
        target_number = ticket['ticket_number']
        is_subticket = False

        if ticket['parent_ticket_id']:
            is_subticket = True
            target_id = ticket['parent_ticket_id']
            target_number = ticket['parent_ticket_number']

            # Check if parent is already running
            if ticket['parent_status'] == 'in_progress':
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': f'Parent {target_number} is already running'})
        else:
            # If already in_progress, don't change
            if ticket['status'] == 'in_progress':
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': 'Ticket is already running'})

        # Set to open + forced (will be picked up next by daemon)
        cursor.execute("""
            UPDATE tickets SET status = 'open', retry_count = 0, is_forced = TRUE, updated_at = NOW()
            WHERE id = %s
        """, (target_id,))
        conn.commit()
        cursor.close()
        conn.close()

        if is_subticket:
            return jsonify({'success': True, 'message': f'Parent {target_number} queued to start next (will process sub-tickets)'})
        return jsonify({'success': True, 'message': 'Ticket queued to start next'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/ticket/<int:ticket_id>/dependencies', methods=['GET', 'POST'])
@login_required
def ticket_dependencies(ticket_id):
    """Get or update ticket dependencies"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        if request.method == 'GET':
            # Get current dependencies
            cursor.execute("""
                SELECT td.depends_on_ticket_id, t.ticket_number, t.title, t.status
                FROM ticket_dependencies td
                JOIN tickets t ON t.id = td.depends_on_ticket_id
                WHERE td.ticket_id = %s
            """, (ticket_id,))
            deps = cursor.fetchall()
            cursor.close()
            conn.close()
            return jsonify({'success': True, 'dependencies': deps})

        # POST - Update dependencies
        data = request.get_json()
        depends_on = data.get('depends_on', [])  # List of ticket IDs or ticket numbers

        # Clear existing dependencies
        cursor.execute("DELETE FROM ticket_dependencies WHERE ticket_id = %s", (ticket_id,))

        # Add new dependencies
        for dep in depends_on:
            if isinstance(dep, int):
                dep_id = dep
            else:
                # Look up by ticket_number
                cursor.execute("SELECT id FROM tickets WHERE ticket_number = %s", (dep,))
                dep_ticket = cursor.fetchone()
                dep_id = dep_ticket['id'] if dep_ticket else None

            if dep_id and dep_id != ticket_id:  # Prevent self-dependency
                cursor.execute("""
                    INSERT IGNORE INTO ticket_dependencies (ticket_id, depends_on_ticket_id)
                    VALUES (%s, %s)
                """, (ticket_id, dep_id))

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/ticket/<int:ticket_id>', methods=['DELETE'])
@login_required
def delete_ticket(ticket_id):
    """Delete a ticket and its conversation history"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Get ticket info for response
        cursor.execute("SELECT ticket_number, title FROM tickets WHERE id = %s", (ticket_id,))
        ticket = cursor.fetchone()

        if not ticket:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Ticket not found'}), 404

        # Delete ticket (cascade will handle messages, logs, etc.)
        cursor.execute("DELETE FROM tickets WHERE id = %s", (ticket_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({
            'success': True,
            'message': f"Ticket {ticket['ticket_number']} deleted"
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/ticket/<int:ticket_id>/retry', methods=['POST'])
@login_required
def retry_ticket(ticket_id):
    """Reset a failed/timeout ticket for retry"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE tickets
            SET status = 'open', retry_count = 0, updated_at = NOW()
            WHERE id = %s AND status IN ('failed', 'timeout', 'stuck')
        """, (ticket_id,))

        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Ticket not found or not in failed/timeout state'})

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/project/<int:project_id>/progress')
@login_required
def get_project_progress(project_id):
    """Get detailed project progress statistics"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Basic project info
        cursor.execute("SELECT id, name, code FROM projects WHERE id = %s", (project_id,))
        project = cursor.fetchone()
        if not project:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Project not found'}), 404

        # Ticket counts by status (all tickets, including sub-tickets)
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM tickets
            WHERE project_id = %s
            GROUP BY status
        """, (project_id,))
        status_counts = {row['status']: row['count'] for row in cursor.fetchall()}

        # Ticket counts by type (awaiting_input counts as completed)
        cursor.execute("""
            SELECT ticket_type, COUNT(*) as total,
                   SUM(CASE WHEN status IN ('done', 'skipped', 'awaiting_input') THEN 1 ELSE 0 END) as completed
            FROM tickets
            WHERE project_id = %s
            GROUP BY ticket_type
        """, (project_id,))
        by_type = {row['ticket_type']: {'total': row['total'], 'completed': row['completed']}
                   for row in cursor.fetchall()}

        # Totals
        total_tickets = sum(status_counts.values())
        # awaiting_input counts as completed (task is done, just waiting for review)
        completed = (status_counts.get('done', 0) + status_counts.get('skipped', 0) +
                     status_counts.get('awaiting_input', 0))
        failed = status_counts.get('failed', 0)
        timeout_count = status_counts.get('timeout', 0)
        in_progress = status_counts.get('in_progress', 0)
        pending = (status_counts.get('open', 0) + status_counts.get('new', 0) +
                   status_counts.get('pending', 0))
        awaiting = status_counts.get('awaiting_input', 0)

        progress_percent = round((completed * 100.0) / total_tickets, 1) if total_tickets > 0 else 0

        # Time spent (from usage_stats)
        cursor.execute("""
            SELECT SUM(duration_seconds) as total_seconds, SUM(total_tokens) as total_tokens
            FROM usage_stats
            WHERE project_id = %s
        """, (project_id,))
        usage = cursor.fetchone()
        time_spent_minutes = int((usage['total_seconds'] or 0) / 60)
        total_tokens = usage['total_tokens'] or 0

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

        # Blocked tickets (have unfinished dependencies)
        # Respects deps_include_awaiting flag per ticket
        cursor.execute("""
            SELECT t.ticket_number
            FROM tickets t
            JOIN ticket_dependencies td ON td.ticket_id = t.id
            JOIN tickets dt ON dt.id = td.depends_on_ticket_id
            WHERE t.project_id = %s
              AND t.status NOT IN ('done', 'skipped', 'failed', 'awaiting_input')
              AND NOT (
                  dt.status IN ('done', 'skipped')
                  OR (COALESCE(t.deps_include_awaiting, FALSE) = TRUE AND dt.status = 'awaiting_input')
              )
            GROUP BY t.id, t.ticket_number
        """, (project_id,))
        blocked_tickets = [row['ticket_number'] for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        return jsonify({
            'project_id': project_id,
            'project_name': project['name'],
            'project_code': project['code'],
            'total_tickets': total_tickets,
            'completed': completed,
            'failed': failed,
            'timeout': timeout_count,
            'in_progress': in_progress,
            'pending': pending,
            'awaiting_input': awaiting,
            'progress_percent': progress_percent,
            'time_spent_minutes': time_spent_minutes,
            'total_tokens': total_tokens,
            'by_type': by_type,
            'current_ticket': current_ticket,
            'failed_tickets': failed_tickets,
            'blocked_tickets': blocked_tickets
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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

def kill_claude_process(ticket_id):
    """Send SIGTERM to Claude process for instant stop"""
    pid_file = f"/var/run/codehero/claude_{ticket_id}.pid"
    try:
        if os.path.exists(pid_file):
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            os.kill(pid, signal.SIGTERM)
            return True
    except (ProcessLookupError, ValueError, PermissionError):
        pass
    return False

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
                UPDATE tickets SET status = 'open', retry_count = 0, review_deadline = NULL,
                closed_at = NULL, closed_by = NULL, close_reason = NULL, updated_at = NOW()
                WHERE id = %s
            """, (ticket_id,))

        # Handle commands
        if message.startswith('/'):
            cmd = message.lower().split()[0]
            if cmd == '/stop':
                # Update ticket status FIRST (so daemon doesn't mark as failed)
                cursor.execute("""
                    UPDATE tickets SET status = 'awaiting_input', updated_at = NOW()
                    WHERE id = %s
                """, (ticket_id,))
                conn.commit()
                # INSTANT KILL: Send SIGTERM to Claude process
                killed = kill_claude_process(ticket_id)
                # Save user command to conversation
                cursor.execute("""
                    INSERT INTO conversation_messages (ticket_id, role, content, created_at)
                    VALUES (%s, 'user', %s, NOW())
                """, (ticket_id, message))
                user_msg_id = cursor.lastrowid
                # Save system response message
                system_msg = '⏸️ Stopped by user (/stop) - Waiting for new instructions' if killed else '⏸️ Stop command received - Waiting for new instructions'
                cursor.execute("""
                    INSERT INTO conversation_messages (ticket_id, role, content, created_at)
                    VALUES (%s, 'system', %s, NOW())
                """, (ticket_id, system_msg))
                sys_msg_id = cursor.lastrowid
                # Log command (mark as processed since web app handles it directly)
                cursor.execute("""
                    INSERT INTO user_messages (ticket_id, user_id, content, message_type, processed)
                    VALUES (%s, %s, '/stop', 'command', TRUE)
                """, (ticket_id, session.get('user_id')))
                # Add log entry
                log_msg = f"⏸️ User command: /stop - Ticket {ticket['ticket_number']} paused"
                cursor.execute("""
                    INSERT INTO daemon_logs (ticket_id, log_type, message, created_at)
                    VALUES (%s, 'warning', %s, NOW())
                """, (ticket_id, log_msg))
                conn.commit()
                # Broadcast user message
                cursor.execute("SELECT * FROM conversation_messages WHERE id = %s", (user_msg_id,))
                new_msg = cursor.fetchone()
                if new_msg:
                    if new_msg.get('created_at'): new_msg['created_at'] = to_iso_utc(new_msg['created_at'])
                    new_msg['ticket_number'] = ticket['ticket_number']
                    socketio.emit('new_message', new_msg, room=f'ticket_{ticket_id}')
                    socketio.emit('new_message', new_msg, room='console')
                # Broadcast system message
                cursor.execute("SELECT * FROM conversation_messages WHERE id = %s", (sys_msg_id,))
                sys_msg_obj = cursor.fetchone()
                if sys_msg_obj:
                    if sys_msg_obj.get('created_at'): sys_msg_obj['created_at'] = to_iso_utc(sys_msg_obj['created_at'])
                    sys_msg_obj['ticket_number'] = ticket['ticket_number']
                    socketio.emit('new_message', sys_msg_obj, room=f'ticket_{ticket_id}')
                    socketio.emit('new_message', sys_msg_obj, room='console')
                # Broadcast status change
                socketio.emit('ticket_status', {'ticket_id': ticket_id, 'status': 'awaiting_input'}, room=f'ticket_{ticket_id}')
                # Broadcast log to console
                socketio.emit('new_log', {'log_type': 'warning', 'message': log_msg, 'created_at': datetime.now().isoformat() + 'Z'}, room='console')
                cursor.close(); conn.close()
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

        # If ticket is awaiting_input, change to open so daemon picks it up
        if ticket.get('status') == 'awaiting_input':
            cursor.execute("UPDATE tickets SET status = 'open', retry_count = 0 WHERE id = %s", (ticket_id,))
            socketio.emit('ticket_status', {'ticket_id': ticket_id, 'status': 'open'}, room=f'ticket_{ticket_id}')

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
                        stdout=open('/var/log/codehero/daemon.log', 'a'),
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

# ============ ANDROID EMULATOR ============

# Screen size presets for Redroid
SCREEN_PRESETS = {
    'phone': {'width': 1080, 'height': 1920, 'dpi': 440, 'label': 'Phone (1080x1920)'},
    'phone_small': {'width': 720, 'height': 1280, 'dpi': 320, 'label': 'Phone Small (720x1280)'},
    'tablet_7': {'width': 1200, 'height': 1920, 'dpi': 240, 'label': 'Tablet 7" (1200x1920)'},
    'tablet_10': {'width': 1600, 'height': 2560, 'dpi': 320, 'label': 'Tablet 10" (1600x2560)'}
}

@app.route('/api/emulator/start', methods=['POST'])
@login_required
def emulator_start():
    """Start the Android emulator (Redroid container)"""
    try:
        data = request.get_json() or {}
        screen_size = data.get('screen_size', 'phone')
        preset = SCREEN_PRESETS.get(screen_size, SCREEN_PRESETS['phone'])

        # Check if already running
        result = subprocess.run(['docker', 'ps', '-q', '--filter', 'name=redroid'],
                              capture_output=True, text=True, timeout=10)
        if result.stdout.strip():
            return jsonify({'status': 'running', 'message': 'Emulator already running'})

        # Try to start existing container
        result = subprocess.run(['docker', 'start', 'redroid'],
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            # Wait for boot and connect ADB
            time.sleep(5)
            subprocess.run(['adb', 'connect', 'localhost:5556'], capture_output=True, timeout=10)
            return jsonify({'status': 'running', 'message': 'Emulator started'})

        # Create new container
        cmd = [
            'docker', 'run', '-d', '--name', 'redroid',
            '--privileged',
            '-p', '5556:5555',
            'redroid/redroid:15.0.0_64only-latest',
            'androidboot.redroid_gpu_mode=guest',
            f'androidboot.redroid_width={preset["width"]}',
            f'androidboot.redroid_height={preset["height"]}',
            f'androidboot.redroid_dpi={preset["dpi"]}'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            return jsonify({'status': 'error', 'message': f'Failed to start: {result.stderr}'})

        # Wait for boot and connect ADB
        time.sleep(10)
        subprocess.run(['adb', 'connect', 'localhost:5556'], capture_output=True, timeout=10)

        return jsonify({'status': 'running', 'message': 'Emulator started'})
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'message': 'Timeout starting emulator'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/emulator/stop', methods=['POST'])
@login_required
def emulator_stop():
    """Stop the Android emulator"""
    try:
        result = subprocess.run(['docker', 'stop', 'redroid'],
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return jsonify({'status': 'stopped', 'message': 'Emulator stopped'})
        return jsonify({'status': 'stopped', 'message': 'Emulator was not running'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/emulator/status')
@login_required
def emulator_status():
    """Get Android emulator status"""
    try:
        # Check if container is running
        result = subprocess.run(['docker', 'ps', '-q', '--filter', 'name=redroid'],
                              capture_output=True, text=True, timeout=10)
        if result.stdout.strip():
            # Check ADB connection
            adb_result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=10)
            connected = 'localhost:5556' in adb_result.stdout
            return jsonify({
                'status': 'running',
                'device': 'localhost:5556',
                'adb_connected': connected,
                'stream_url': f'https://{request.host.split(":")[0]}:8443/'
            })
        return jsonify({'status': 'stopped', 'device': None})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

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
                UPDATE tickets SET status = 'open', retry_count = 0, review_deadline = NULL, updated_at = NOW()
                WHERE id = %s
            """, (ticket['id'],))

        # Handle commands
        if message.startswith('/'):
            cmd = message.lower().split()[0]
            if cmd == '/stop':
                # Update ticket status FIRST (so daemon doesn't mark as failed)
                cursor.execute("""
                    UPDATE tickets SET status = 'awaiting_input', updated_at = NOW()
                    WHERE id = %s
                """, (ticket['id'],))
                conn.commit()
                # INSTANT KILL: Send SIGTERM to Claude process
                killed = kill_claude_process(ticket['id'])
                # Save user command to conversation
                cursor.execute("""
                    INSERT INTO conversation_messages (ticket_id, role, content, created_at)
                    VALUES (%s, 'user', %s, NOW())
                """, (ticket['id'], message))
                user_msg_id = cursor.lastrowid
                # Save system response message
                system_msg_text = '⏸️ Stopped by user (/stop) - Waiting for new instructions' if killed else '⏸️ Stop command received - Waiting for new instructions'
                cursor.execute("""
                    INSERT INTO conversation_messages (ticket_id, role, content, created_at)
                    VALUES (%s, 'system', %s, NOW())
                """, (ticket['id'], system_msg_text))
                sys_msg_id = cursor.lastrowid
                cursor.execute("""
                    INSERT INTO user_messages (ticket_id, user_id, content, message_type, processed)
                    VALUES (%s, %s, '/stop', 'command', TRUE)
                """, (ticket['id'], session.get('user_id')))
                # Add log entry
                log_msg = f"⏸️ User command: /stop - Ticket {ticket['ticket_number']} paused"
                cursor.execute("""
                    INSERT INTO daemon_logs (ticket_id, log_type, message, created_at)
                    VALUES (%s, 'warning', %s, NOW())
                """, (ticket['id'], log_msg))
                conn.commit()
                # Broadcast user message
                cursor.execute("SELECT * FROM conversation_messages WHERE id = %s", (user_msg_id,))
                new_msg = cursor.fetchone()
                if new_msg:
                    if new_msg.get('created_at'): new_msg['created_at'] = to_iso_utc(new_msg['created_at'])
                    new_msg['ticket_number'] = ticket['ticket_number']
                    socketio.emit('new_message', new_msg, room=f"ticket_{ticket['id']}")
                    socketio.emit('new_message', new_msg, room='console')
                # Broadcast system message
                cursor.execute("SELECT * FROM conversation_messages WHERE id = %s", (sys_msg_id,))
                sys_msg_obj = cursor.fetchone()
                if sys_msg_obj:
                    if sys_msg_obj.get('created_at'): sys_msg_obj['created_at'] = to_iso_utc(sys_msg_obj['created_at'])
                    sys_msg_obj['ticket_number'] = ticket['ticket_number']
                    socketio.emit('new_message', sys_msg_obj, room=f"ticket_{ticket['id']}")
                    socketio.emit('new_message', sys_msg_obj, room='console')
                # Broadcast status change
                socketio.emit('ticket_status', {'ticket_id': ticket['id'], 'status': 'awaiting_input'}, room=f"ticket_{ticket['id']}")
                # Broadcast log
                socketio.emit('new_log', {'log_type': 'warning', 'message': log_msg, 'created_at': datetime.now().isoformat() + 'Z'}, room='console')
                cursor.close(); conn.close()
                return jsonify({'success': True, 'message': 'Stop signal sent'})

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
        print(f"[DEBUG] ActivationSession _reader started, fd={self.fd}")
        while self.running:
            try:
                r, _, _ = select.select([self.fd], [], [], 0.1)
                if r:
                    data = os.read(self.fd, 4096)
                    if data:
                        decoded = data.decode('utf-8', errors='replace')
                        print(f"[DEBUG] Read {len(decoded)} chars from pty")
                        with self.lock:
                            self.output_buffer += decoded
                        # Check if output contains the final OAuth token
                        self._check_for_token(decoded)
                    else:
                        print("[DEBUG] No data, breaking")
                        break
            except Exception as e:
                print(f"[DEBUG] Reader exception: {e}")
                break
        print("[DEBUG] Reader stopped")
        self.running = False

    def _check_for_token(self, output):
        """Check if credentials.json was created and sync token to .env"""
        # Check if .credentials.json exists (claude login saves tokens there)
        creds_file = os.path.join(self.user_home, ".claude/.credentials.json")
        if os.path.exists(creds_file):
            try:
                with open(creds_file, 'r') as f:
                    creds = json.load(f)
                # Extract OAuth token from credentials
                oauth = creds.get('claudeAiOauth', {})
                access_token = oauth.get('accessToken')
                if access_token and access_token.startswith('sk-ant-'):
                    # Check if we already saved this token
                    env_file = os.path.join(self.user_home, ".claude/.env")
                    already_saved = False
                    if os.path.exists(env_file):
                        with open(env_file, 'r') as f:
                            if access_token in f.read():
                                already_saved = True
                    if not already_saved:
                        print(f"[DEBUG] Found OAuth token in credentials.json: {access_token[:20]}...")
                        self._save_api_key(access_token)
            except Exception as e:
                print(f"[DEBUG] Error reading credentials: {e}")

    def get_output(self):
        with self.lock:
            out, self.output_buffer = self.output_buffer, ""
            return out

    def send_input(self, data):
        if self.fd and self.running:
            try:
                # Don't intercept authorization code - let Claude process it
                # The final token will be caught by _check_for_token
                os.write(self.fd, data.encode() if isinstance(data, str) else data)
                return True
            except: pass
        return False

    def _save_api_key(self, api_key):
        """Save API key or OAuth token to .env file for daemon to use"""
        try:
            env_dir = os.path.join(self.user_home, ".claude")
            os.makedirs(env_dir, exist_ok=True)
            env_file = os.path.join(env_dir, ".env")

            # Detect token type and use correct env var name
            if api_key.startswith('sk-ant-oat'):
                # OAuth token
                env_var = 'CLAUDE_CODE_OAUTH_TOKEN'
            else:
                # API key
                env_var = 'ANTHROPIC_API_KEY'

            with open(env_file, 'w') as f:
                f.write(f"{env_var}={api_key}\n")
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

        # If credentials.json exists, sync token to .env
        if os.path.exists(creds_file):
            try:
                with open(creds_file, 'r') as f:
                    creds = json.load(f)
                oauth = creds.get('claudeAiOauth', {})
                access_token = oauth.get('accessToken')
                if access_token and access_token.startswith('sk-ant-'):
                    # Sync to .env if not already there
                    self._save_api_key(access_token)
            except: pass
            return True

        if os.path.exists(env_file):
            try:
                with open(env_file, 'r') as f:
                    content = f.read()
                    # Check for both OAuth token and API key
                    if 'ANTHROPIC_API_KEY=sk-ant-' in content or 'CLAUDE_CODE_OAUTH_TOKEN=sk-ant-' in content:
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
    # Check multiple possible credential locations
    creds_old = os.path.join(CLAUDE_USER_HOME, ".claude/.credentials.json")
    creds_new = os.path.join(CLAUDE_USER_HOME, ".claude.json")
    env_file = os.path.join(CLAUDE_USER_HOME, ".claude/.env")

    activated = False

    # Check old credentials file
    if os.path.exists(creds_old):
        activated = True

    # Check new .claude.json for oauthAccount
    if not activated and os.path.exists(creds_new):
        try:
            with open(creds_new, 'r') as f:
                config = json.load(f)
                if 'oauthAccount' in config:
                    activated = True
        except:
            pass

    # Check .env file for valid tokens/keys
    if not activated and os.path.exists(env_file):
        try:
            with open(env_file, 'r') as f:
                content = f.read()
                # Check for both OAuth token and API key
                if 'ANTHROPIC_API_KEY=sk-ant-' in content or 'CLAUDE_CODE_OAUTH_TOKEN=sk-ant-' in content:
                    activated = True
        except:
            pass

    if activated:
        ensure_claude_config_flags()
    return jsonify({'activated': activated})

# Activation Terminal Routes
@app.route('/api/claude/activate/start', methods=['POST'])
@login_required
def claude_activate_start():
    try:
        session_id = str(uuid.uuid4())
        sess = ActivationSession()
        if sess.start():
            activation_sessions[session_id] = sess
            return jsonify({'success': True, 'session_id': session_id})
        return jsonify({'success': False, 'error': 'Failed to start activation session'})
    except Exception as e:
        import traceback
        print(f"Activation start error: {e}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)})

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
        config_file = '/etc/codehero/system.conf'
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
        config_file = '/etc/codehero/system.conf'

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
            f.write("# CodeHero Configuration\n")
            for key, value in existing.items():
                f.write(f"{key}={value}\n")

        # Restart daemon to load new settings
        try:
            subprocess.run(['sudo', 'systemctl', 'restart', 'codehero-daemon'],
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
            'text': '✅ <b>CodeHero</b>\n\nTest notification successful!\nYou will receive alerts when tickets need attention.',
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
    project_id = request.args.get('project_id', type=int)

    # Get project info if project_id provided
    project = None
    if project_id:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
        project = cursor.fetchone()
        cursor.close()
        conn.close()

    return render_template('claude_assistant.html', user=session.get('user'), popup=popup, mode=mode, project_id=project_id, project=project)

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
            headers={'User-Agent': 'CodeHero/' + VERSION}
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

# Store active upgrade process
active_upgrade = {'running': False, 'process': None, 'temp_dir': None, 'log': ''}

@app.route('/api/ai-fix-upgrade', methods=['POST'])
@login_required
def ai_fix_upgrade():
    """Ask AI to analyze upgrade error and suggest fix"""
    try:
        data = request.get_json() or {}
        error_log = data.get('log', '')

        if not error_log:
            return jsonify({'error': 'No error log provided'}), 400

        # Truncate log if too long (keep last 3000 chars)
        if len(error_log) > 3000:
            error_log = "...(truncated)...\n" + error_log[-3000:]

        # Build prompt for Claude
        prompt = f'''The CodeHero upgrade script failed. Analyze the error and provide a fix.

## Error Log:
```
{error_log}
```

## Instructions:
1. Identify the root cause of the failure
2. Provide the exact commands to fix it (one command per line)
3. Be concise and practical

Format your response as:
**Problem:** [one line description]

**Fix:**
```bash
command1
command2
```

**Explanation:** [brief explanation]'''

        # Write prompt to file (safer for special characters)
        prompt_file = '/tmp/upgrade_fix_prompt.txt'
        with open(prompt_file, 'w') as f:
            f.write(prompt)

        # Call Claude CLI
        result = subprocess.run(
            ['sudo', '-u', 'claude', 'bash', '-c',
             f'export PATH="$HOME/.local/bin:$PATH" && cat {prompt_file} | claude -p --print --model haiku'],
            capture_output=True,
            text=True,
            timeout=60,
            cwd='/home/claude'
        )

        os.remove(prompt_file)

        response = result.stdout.strip() if result.stdout else result.stderr.strip()

        if not response:
            return jsonify({'error': 'No response from AI', 'stderr': result.stderr}), 500

        # Extract commands from response
        commands = []
        in_bash_block = False
        for line in response.split('\n'):
            if line.strip().startswith('```bash'):
                in_bash_block = True
                continue
            elif line.strip().startswith('```') and in_bash_block:
                in_bash_block = False
                continue
            elif in_bash_block and line.strip():
                commands.append(line.strip())

        return jsonify({
            'success': True,
            'response': response,
            'commands': commands
        })

    except subprocess.TimeoutExpired:
        return jsonify({'error': 'AI request timed out'}), 504
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/run-fix-command', methods=['POST'])
@login_required
def run_fix_command():
    """Execute a fix command suggested by AI"""
    try:
        data = request.get_json() or {}
        command = data.get('command', '')

        if not command:
            return jsonify({'error': 'No command provided'}), 400

        # Security: block dangerous commands
        dangerous = ['rm -rf /', 'mkfs', 'dd if=', ':(){', 'chmod -R 777 /']
        for d in dangerous:
            if d in command:
                return jsonify({'error': 'Command blocked for safety'}), 403

        # Run command
        result = subprocess.run(
            ['sudo', 'bash', '-c', command],
            capture_output=True,
            text=True,
            timeout=120,
            cwd='/opt/codehero'
        )

        return jsonify({
            'success': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr,
            'exit_code': result.returncode
        })

    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Command timed out'}), 504
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/do-update', methods=['POST'])
@login_required
def do_update():
    """Download the update and prepare for installation"""
    global active_upgrade

    if active_upgrade['running']:
        return jsonify({'error': 'Upgrade already in progress'}), 400

    try:
        # First check for update
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={'User-Agent': 'CodeHero/' + VERSION}
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

        req = urllib.request.Request(download_url, headers={'User-Agent': 'CodeHero/' + VERSION})
        with urllib.request.urlopen(req, timeout=300) as response:
            with open(zip_path, 'wb') as f:
                f.write(response.read())

        # Extract
        extract_dir = os.path.join(temp_dir, 'extracted')
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(extract_dir)

        # Find the codehero folder inside
        extracted_folder = None
        for item in os.listdir(extract_dir):
            if item.startswith('codehero'):
                extracted_folder = os.path.join(extract_dir, item)
                break

        if not extracted_folder or not os.path.isdir(extracted_folder):
            shutil.rmtree(temp_dir)
            return jsonify({'error': 'Invalid archive structure'}), 400

        # Verify upgrade.sh exists
        upgrade_script = os.path.join(extracted_folder, 'upgrade.sh')
        if not os.path.exists(upgrade_script):
            shutil.rmtree(temp_dir)
            return jsonify({'error': 'upgrade.sh not found'}), 400

        os.chmod(upgrade_script, 0o755)

        # Store for websocket to use
        active_upgrade['temp_dir'] = temp_dir
        active_upgrade['extracted_folder'] = extracted_folder
        active_upgrade['upgrade_script'] = upgrade_script

        return jsonify({
            'success': True,
            'message': 'Download complete. Ready to install.',
            'ready': True
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

@socketio.on('join_upgrade')
def handle_join_upgrade():
    join_room('upgrade')
    emit('joined', {'room': 'upgrade'})

@socketio.on('start_upgrade')
def handle_start_upgrade():
    """Run upgrade.sh with real-time output streaming"""
    global active_upgrade

    if active_upgrade['running']:
        emit('upgrade_error', {'error': 'Upgrade already in progress'})
        return

    if not active_upgrade.get('upgrade_script'):
        emit('upgrade_error', {'error': 'No upgrade prepared. Call /api/do-update first.'})
        return

    active_upgrade['running'] = True
    emit('upgrade_started', {'message': 'Starting upgrade...'})

    def run_upgrade():
        global active_upgrade
        try:
            upgrade_script = active_upgrade['upgrade_script']
            extracted_folder = active_upgrade['extracted_folder']
            temp_dir = active_upgrade['temp_dir']

            # Run upgrade.sh with sudo and capture output
            process = subprocess.Popen(
                ['sudo', 'bash', upgrade_script, '-y'],
                cwd=extracted_folder,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=True
            )
            active_upgrade['process'] = process

            # Stream output line by line
            for line in iter(process.stdout.readline, ''):
                if line:
                    socketio.emit('upgrade_output', {'line': line.rstrip()}, room='upgrade')

            process.wait()
            exit_code = process.returncode

            # Cleanup temp directory
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

            if exit_code == 0:
                socketio.emit('upgrade_complete', {
                    'success': True,
                    'message': 'Upgrade completed successfully!'
                }, room='upgrade')
            else:
                socketio.emit('upgrade_complete', {
                    'success': False,
                    'message': f'Upgrade failed with exit code {exit_code}'
                }, room='upgrade')

        except Exception as e:
            socketio.emit('upgrade_error', {'error': str(e)}, room='upgrade')
        finally:
            active_upgrade['running'] = False
            active_upgrade['process'] = None
            active_upgrade['temp_dir'] = None
            active_upgrade['extracted_folder'] = None
            active_upgrade['upgrade_script'] = None

    # Run in background thread
    thread = threading.Thread(target=run_upgrade)
    thread.daemon = True
    thread.start()

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

# ==================== LSP WebSocket Handlers ====================

# Store LSP sessions per client
lsp_sessions = {}
lsp_lock = threading.Lock()

@socketio.on('lsp:init')
def handle_lsp_init(data):
    """Initialize LSP for a project"""
    if not LSP_ENABLED or not lsp_manager:
        emit('lsp:error', {'message': 'LSP not available'})
        return

    project_path = data.get('projectPath', '')
    language = data.get('language', '')
    sid = request.sid

    if not project_path or not language:
        emit('lsp:error', {'message': 'Missing projectPath or language'})
        return

    server = lsp_manager.get_server(project_path, language)
    if server:
        with lsp_lock:
            if sid not in lsp_sessions:
                lsp_sessions[sid] = {}
            lsp_sessions[sid][language] = {
                'projectPath': project_path,
                'server': server
            }

        # Register message handler for diagnostics
        def on_notification(lang, msg):
            if msg.get('method') == 'textDocument/publishDiagnostics':
                emit('lsp:diagnostics', msg.get('params', {}), room=sid)

        lsp_manager.register_message_handler(f'{sid}_{language}', on_notification)

        emit('lsp:ready', {
            'language': language,
            'capabilities': server.capabilities
        })
    else:
        emit('lsp:error', {'message': f'Failed to start {language} server'})

@socketio.on('lsp:didOpen')
def handle_lsp_did_open(data):
    """Notify LSP that a file was opened"""
    if not LSP_ENABLED:
        return

    sid = request.sid
    uri = data.get('uri', '')
    language = data.get('language', '')
    text = data.get('text', '')

    with lsp_lock:
        if sid in lsp_sessions and language in lsp_sessions[sid]:
            server = lsp_sessions[sid][language]['server']
            server.did_open(uri, language, text)

@socketio.on('lsp:didChange')
def handle_lsp_did_change(data):
    """Notify LSP of document changes"""
    if not LSP_ENABLED:
        return

    sid = request.sid
    uri = data.get('uri', '')
    language = data.get('language', '')
    version = data.get('version', 1)
    text = data.get('text', '')

    with lsp_lock:
        if sid in lsp_sessions and language in lsp_sessions[sid]:
            server = lsp_sessions[sid][language]['server']
            server.did_change(uri, version, text)

@socketio.on('lsp:didSave')
def handle_lsp_did_save(data):
    """Notify LSP that a file was saved"""
    if not LSP_ENABLED:
        return

    sid = request.sid
    uri = data.get('uri', '')
    language = data.get('language', '')

    with lsp_lock:
        if sid in lsp_sessions and language in lsp_sessions[sid]:
            server = lsp_sessions[sid][language]['server']
            server.did_save(uri)

@socketio.on('lsp:didClose')
def handle_lsp_did_close(data):
    """Notify LSP that a file was closed"""
    if not LSP_ENABLED:
        return

    sid = request.sid
    uri = data.get('uri', '')
    language = data.get('language', '')

    with lsp_lock:
        if sid in lsp_sessions and language in lsp_sessions[sid]:
            server = lsp_sessions[sid][language]['server']
            server.did_close(uri)

@socketio.on('lsp:completion')
def handle_lsp_completion(data):
    """Request code completion"""
    if not LSP_ENABLED:
        return

    sid = request.sid
    uri = data.get('uri', '')
    language = data.get('language', '')
    line = data.get('line', 0)
    character = data.get('character', 0)
    request_id = data.get('requestId', 0)

    with lsp_lock:
        if sid in lsp_sessions and language in lsp_sessions[sid]:
            server = lsp_sessions[sid][language]['server']
            result = server.completion(uri, line, character)
            emit('lsp:completionResponse', {
                'requestId': request_id,
                'result': result.get('result') if result else None
            })

@socketio.on('lsp:hover')
def handle_lsp_hover(data):
    """Request hover info"""
    if not LSP_ENABLED:
        return

    sid = request.sid
    uri = data.get('uri', '')
    language = data.get('language', '')
    line = data.get('line', 0)
    character = data.get('character', 0)
    request_id = data.get('requestId', 0)

    with lsp_lock:
        if sid in lsp_sessions and language in lsp_sessions[sid]:
            server = lsp_sessions[sid][language]['server']
            result = server.hover(uri, line, character)
            emit('lsp:hoverResponse', {
                'requestId': request_id,
                'result': result.get('result') if result else None
            })

@socketio.on('lsp:definition')
def handle_lsp_definition(data):
    """Request go-to-definition"""
    if not LSP_ENABLED:
        return

    sid = request.sid
    uri = data.get('uri', '')
    language = data.get('language', '')
    line = data.get('line', 0)
    character = data.get('character', 0)
    request_id = data.get('requestId', 0)

    with lsp_lock:
        if sid in lsp_sessions and language in lsp_sessions[sid]:
            server = lsp_sessions[sid][language]['server']
            result = server.definition(uri, line, character)
            emit('lsp:definitionResponse', {
                'requestId': request_id,
                'result': result.get('result') if result else None
            })

@socketio.on('lsp:signatureHelp')
def handle_lsp_signature_help(data):
    """Request signature help"""
    if not LSP_ENABLED:
        return

    sid = request.sid
    uri = data.get('uri', '')
    language = data.get('language', '')
    line = data.get('line', 0)
    character = data.get('character', 0)
    request_id = data.get('requestId', 0)

    with lsp_lock:
        if sid in lsp_sessions and language in lsp_sessions[sid]:
            server = lsp_sessions[sid][language]['server']
            result = server.signature_help(uri, line, character)
            emit('lsp:signatureHelpResponse', {
                'requestId': request_id,
                'result': result.get('result') if result else None
            })

@socketio.on('disconnect')
def handle_disconnect():
    """Clean up terminals and LSP sessions when client disconnects"""
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

    # Clean up LSP sessions
    if LSP_ENABLED and lsp_manager:
        with lsp_lock:
            if sid in lsp_sessions:
                for lang in lsp_sessions[sid]:
                    lsp_manager.unregister_message_handler(f'{sid}_{lang}')
                del lsp_sessions[sid]

# ============ PACKAGE MANAGER ============

# Package definitions - commands to check if installed and install
PACKAGES = {
    # Core Infrastructure (from setup.sh)
    'mysql': {
        'name': 'MySQL Server',
        'check': 'mysql --version',
        'version_regex': r'mysql\s+Ver\s+(\S+)',
        'install': [
            'apt-get update',
            'DEBIAN_FRONTEND=noninteractive apt-get install -y mysql-server',
            'systemctl enable mysql || true',
            'systemctl start mysql || true',
            # Create codehero database and user if not exists
            'mysql -e "CREATE DATABASE IF NOT EXISTS claude_knowledge;" || true',
            'mysql -e "CREATE USER IF NOT EXISTS \'claude_user\'@\'localhost\' IDENTIFIED BY \'claudepass123\';" || true',
            'mysql -e "GRANT ALL PRIVILEGES ON claude_knowledge.* TO \'claude_user\'@\'localhost\';" || true',
            'mysql -e "FLUSH PRIVILEGES;" || true'
        ]
    },
    'nginx': {
        'name': 'Nginx',
        'check': 'nginx -v 2>&1',
        'version_regex': r'nginx/(\d+\.\d+\.\d+)',
        'install': [
            'apt-get update',
            'apt-get install -y nginx',
            'systemctl enable nginx || true',
            'systemctl start nginx || true',
            # Create SSL certs if not exist
            'mkdir -p /etc/codehero/ssl',
            'test -f /etc/codehero/ssl/cert.pem || openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/codehero/ssl/key.pem -out /etc/codehero/ssl/cert.pem -subj "/C=GR/ST=Athens/L=Athens/O=CodeHero/CN=codehero"',
            # Create admin site config if not exists
            '''test -f /etc/nginx/sites-available/codehero-admin || cat > /etc/nginx/sites-available/codehero-admin << 'NGINXADMIN'
server {
    listen 9453 ssl http2;
    server_name _;
    ssl_certificate /etc/codehero/ssl/cert.pem;
    ssl_certificate_key /etc/codehero/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    client_max_body_size 500M;
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }
    location /socket.io {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400s;
    }
}
NGINXADMIN''',
            'ln -sf /etc/nginx/sites-available/codehero-admin /etc/nginx/sites-enabled/ || true',
            'rm -f /etc/nginx/sites-enabled/default || true',
            'nginx -t && systemctl reload nginx || true'
        ]
    },
    'php': {
        'name': 'PHP 8.3',
        'check': 'php -v | head -1',
        'version_regex': r'PHP (\d+\.\d+\.\d+)',
        'install': [
            'apt-get update',
            'apt-get install -y php8.3-fpm php8.3-mysql php8.3-curl php8.3-intl php8.3-opcache php8.3-redis php8.3-imagick php8.3-sqlite3 php8.3-imap php8.3-apcu php8.3-igbinary php8.3-tidy php8.3-pgsql php8.3-cli || apt-get install -y php-fpm php-mysql php-curl',
            'systemctl enable php8.3-fpm || systemctl enable php-fpm || true',
            'systemctl start php8.3-fpm || systemctl start php-fpm || true'
        ]
    },
    'phpmyadmin': {
        'name': 'phpMyAdmin',
        'check': 'dpkg -l phpmyadmin 2>/dev/null | grep -q "^ii" && echo installed',
        'version_regex': r'(installed)',
        'install': [
            'apt-get update',
            'DEBIAN_FRONTEND=noninteractive apt-get install -y phpmyadmin',
            # Create signon.php only if not exists
            '''test -f /usr/share/phpmyadmin/signon.php || cat > /usr/share/phpmyadmin/signon.php << 'PMASIGNON'
<?php
session_name('PMA_signon');
session_start();
$user = isset($_GET['u']) ? base64_decode($_GET['u']) : '';
$pass = isset($_GET['p']) ? base64_decode($_GET['p']) : '';
$db = isset($_GET['db']) ? base64_decode($_GET['db']) : '';
if (empty($user)) { die('Missing credentials'); }
$_SESSION['PMA_single_signon_user'] = $user;
$_SESSION['PMA_single_signon_password'] = $pass;
$_SESSION['PMA_single_signon_host'] = 'localhost';
$redirect = 'index.php';
if (!empty($db)) { $redirect .= '?db=' . urlencode($db); }
header('Location: ' . $redirect);
exit;
PMASIGNON''',
            'mkdir -p /etc/phpmyadmin/conf.d',
            '''test -f /etc/phpmyadmin/conf.d/codehero-signon.php || cat > /etc/phpmyadmin/conf.d/codehero-signon.php << 'PMACONFIG'
<?php
$cfg['Servers'][1]['auth_type'] = 'signon';
$cfg['Servers'][1]['SignonSession'] = 'PMA_signon';
$cfg['Servers'][1]['SignonURL'] = '/signon.php';
$cfg['Servers'][1]['LogoutURL'] = '/';
PMACONFIG''',
            # Create nginx config only if not exists
            '''test -f /etc/nginx/sites-available/codehero-phpmyadmin || cat > /etc/nginx/sites-available/codehero-phpmyadmin << 'NGINXPMA'
server {
    listen 9454 ssl http2;
    server_name _;
    ssl_certificate /etc/codehero/ssl/cert.pem;
    ssl_certificate_key /etc/codehero/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    root /usr/share/phpmyadmin;
    index index.php index.html;
    location / { try_files $uri $uri/ /index.php?$args; }
    location ~ \\.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php8.3-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
    }
    location ~ /\\.ht { deny all; }
    location /setup { deny all; }
}
NGINXPMA''',
            'ln -sf /etc/nginx/sites-available/codehero-phpmyadmin /etc/nginx/sites-enabled/ || true',
            'nginx -t && systemctl reload nginx || true'
        ]
    },
    'python-core': {
        'name': 'Python Core Packages',
        'check': 'python3 -c "import flask; print(flask.__version__)"',
        'version_regex': r'(\d+\.\d+\.\d+)',
        'install': [
            'apt-get install -y python3 python3-pip || true',
            'pip3 install --ignore-installed flask flask-socketio flask-cors mysql-connector-python bcrypt eventlet --break-system-packages || pip3 install --ignore-installed flask flask-socketio flask-cors mysql-connector-python bcrypt eventlet || true'
        ]
    },
    'claude-cli': {
        'name': 'Claude Code CLI',
        'check': 'test -f /home/claude/.local/bin/claude && /home/claude/.local/bin/claude --version 2>/dev/null | head -1',
        'version_regex': r'(\d+\.\d+\.\d+)',
        'install': [
            'sudo -u claude bash -c "curl -fsSL https://claude.ai/install.sh | bash" || true',
            # Add to PATH if not already
            'sudo -u claude bash -c "grep -q .local/bin ~/.bashrc || echo \'export PATH=\\\"\\$HOME/.local/bin:\\$PATH\\\"\' >> ~/.bashrc" || true'
        ]
    },
    # Development Tools
    'nodejs': {
        'name': 'Node.js 22',
        'check': 'node --version',
        'version_regex': r'v(\d+\.\d+\.\d+)',
        'install': [
            # Check if nodesource repo already added
            'test -f /etc/apt/sources.list.d/nodesource.list || curl -fsSL https://deb.nodesource.com/setup_22.x | bash -',
            'apt-get install -y nodejs'
        ]
    },
    'graalvm': {
        'name': 'GraalVM Java 24',
        'check': 'test -d /opt/graalvm && /opt/graalvm/bin/java -version 2>&1 | head -1',
        'version_regex': r'(\d+\.\d+\.\d+)',
        'install': [
            # Only download if not exists
            'test -d /opt/graalvm || curl -fsSL https://github.com/graalvm/graalvm-ce-builds/releases/download/jdk-24.0.1/graalvm-community-jdk-24.0.1_linux-x64_bin.tar.gz -o /tmp/graalvm.tar.gz',
            'test -d /opt/graalvm || tar -xzf /tmp/graalvm.tar.gz -C /opt/',
            'test -d /opt/graalvm || ln -sf /opt/graalvm-community-openjdk-24.0.1+11.1 /opt/graalvm',
            'update-alternatives --install /usr/bin/java java /opt/graalvm/bin/java 100 || true',
            'update-alternatives --install /usr/bin/javac javac /opt/graalvm/bin/javac 100 || true',
            'rm -f /tmp/graalvm.tar.gz || true'
        ]
    },
    'playwright': {
        'name': 'Playwright',
        'check': 'python3 -c "import playwright; print(\'installed\')" 2>/dev/null',
        'version_regex': r'(installed)',
        'install': [
            'apt-get update',
            'apt-get install -y xvfb libgbm1 libasound2t64 libatk-bridge2.0-0t64 libdrm2 libnss3 || apt-get install -y xvfb libgbm1 libasound2 || true',
            'pip3 install playwright --break-system-packages || pip3 install playwright || true',
            'su - claude -c "playwright install chromium" || playwright install chromium || true'
        ]
    },
    'multimedia': {
        'name': 'Multimedia Tools',
        'check': 'ffmpeg -version 2>&1 | head -1',
        'version_regex': r'ffmpeg version (\S+)',
        'install': [
            'apt-get update',
            'apt-get install -y ffmpeg imagemagick tesseract-ocr poppler-utils sox || true'
        ]
    },
    # Code Intelligence (Monaco + LSP Servers) - All installed to /opt/codehero/lsp/
    # Each LSP updates /opt/codehero/lsp/config.json with its path for the app to use
    'monaco-editor': {
        'name': 'Monaco Editor',
        'check': 'test -f /opt/codehero/web/static/monaco/min/vs/editor/editor.main.js && echo installed',
        'version_regex': r'(installed)',
        'install': [
            'mkdir -p /opt/codehero/web/static/monaco',
            'test -f /opt/codehero/web/static/monaco/min/vs/editor/editor.main.js || curl -fsSL "https://registry.npmjs.org/monaco-editor/-/monaco-editor-0.45.0.tgz" -o /tmp/monaco.tgz',
            'test -f /tmp/monaco.tgz && tar -xzf /tmp/monaco.tgz -C /tmp && cp -r /tmp/package/* /opt/codehero/web/static/monaco/ && rm -rf /tmp/monaco.tgz /tmp/package || true',
            'mkdir -p /opt/codehero/web/static/monaco-workers',
            'echo "self.MonacoEnvironment={baseUrl:self.location.origin+\\"/static/monaco/min/\\"};importScripts(self.location.origin+\\"/static/monaco/min/vs/base/worker/workerMain.js\\");" > /opt/codehero/web/static/monaco-workers/editor.worker.js',
            'echo "self.MonacoEnvironment={baseUrl:self.location.origin+\\"/static/monaco/min/\\"};importScripts(self.location.origin+\\"/static/monaco/min/vs/language/json/jsonWorker.js\\");" > /opt/codehero/web/static/monaco-workers/json.worker.js',
            'echo "self.MonacoEnvironment={baseUrl:self.location.origin+\\"/static/monaco/min/\\"};importScripts(self.location.origin+\\"/static/monaco/min/vs/language/css/cssWorker.js\\");" > /opt/codehero/web/static/monaco-workers/css.worker.js',
            'echo "self.MonacoEnvironment={baseUrl:self.location.origin+\\"/static/monaco/min/\\"};importScripts(self.location.origin+\\"/static/monaco/min/vs/language/html/htmlWorker.js\\");" > /opt/codehero/web/static/monaco-workers/html.worker.js',
            'echo "self.MonacoEnvironment={baseUrl:self.location.origin+\\"/static/monaco/min/\\"};importScripts(self.location.origin+\\"/static/monaco/min/vs/language/typescript/tsWorker.js\\");" > /opt/codehero/web/static/monaco-workers/ts.worker.js',
            'python3 /opt/codehero/scripts/update_lsp_config.py monaco /opt/codehero/web/static/monaco',
            'echo "Monaco Editor installed to /opt/codehero/web/static/monaco"'
        ]
    },
    'lsp-python': {
        'name': 'Python LSP',
        'check': 'test -f /opt/codehero/lsp/python/bin/pylsp && /opt/codehero/lsp/python/bin/pylsp --version 2>/dev/null | head -1',
        'version_regex': r'v(\d+\.\d+\.\d+)',
        'install': [
            'mkdir -p /opt/codehero/lsp/python',
            'python3 -m venv /opt/codehero/lsp/python',
            '/opt/codehero/lsp/python/bin/pip install --upgrade pip',
            '/opt/codehero/lsp/python/bin/pip install python-lsp-server pylsp-mypy python-lsp-black',
            'ln -sf /opt/codehero/lsp/python/bin/pylsp /usr/local/bin/pylsp 2>/dev/null || true',
            'python3 /opt/codehero/scripts/update_lsp_config.py python /opt/codehero/lsp/python/bin/pylsp',
            'echo "Python LSP installed to /opt/codehero/lsp/python"'
        ]
    },
    'lsp-typescript': {
        'name': 'TypeScript/JS LSP',
        'check': 'test -f /opt/codehero/lsp/node/node_modules/.bin/typescript-language-server && /opt/codehero/lsp/node/node_modules/.bin/typescript-language-server --version 2>/dev/null',
        'version_regex': r'(\d+\.\d+\.\d+)',
        'install': [
            'mkdir -p /opt/codehero/lsp/node',
            'cd /opt/codehero/lsp/node && npm init -y 2>/dev/null || true',
            'cd /opt/codehero/lsp/node && npm install typescript typescript-language-server',
            'ln -sf /opt/codehero/lsp/node/node_modules/.bin/typescript-language-server /usr/local/bin/typescript-language-server 2>/dev/null || true',
            'ln -sf /opt/codehero/lsp/node/node_modules/.bin/tsserver /usr/local/bin/tsserver 2>/dev/null || true',
            'python3 /opt/codehero/scripts/update_lsp_config.py typescript /opt/codehero/lsp/node/node_modules/.bin/typescript-language-server javascript /opt/codehero/lsp/node/node_modules/.bin/typescript-language-server',
            'echo "TypeScript/JS LSP installed to /opt/codehero/lsp/node"'
        ]
    },
    'lsp-html-css': {
        'name': 'HTML/CSS/JSON LSP',
        'check': 'test -f /opt/codehero/lsp/node/node_modules/.bin/vscode-html-language-server && echo installed',
        'version_regex': r'(installed)',
        'install': [
            'mkdir -p /opt/codehero/lsp/node',
            'cd /opt/codehero/lsp/node && npm init -y 2>/dev/null || true',
            'cd /opt/codehero/lsp/node && npm install vscode-langservers-extracted',
            'ln -sf /opt/codehero/lsp/node/node_modules/.bin/vscode-html-language-server /usr/local/bin/vscode-html-language-server 2>/dev/null || true',
            'ln -sf /opt/codehero/lsp/node/node_modules/.bin/vscode-css-language-server /usr/local/bin/vscode-css-language-server 2>/dev/null || true',
            'ln -sf /opt/codehero/lsp/node/node_modules/.bin/vscode-json-language-server /usr/local/bin/vscode-json-language-server 2>/dev/null || true',
            'python3 /opt/codehero/scripts/update_lsp_config.py html /opt/codehero/lsp/node/node_modules/.bin/vscode-html-language-server css /opt/codehero/lsp/node/node_modules/.bin/vscode-css-language-server json /opt/codehero/lsp/node/node_modules/.bin/vscode-json-language-server',
            'echo "HTML/CSS/JSON LSP installed to /opt/codehero/lsp/node"'
        ]
    },
    'lsp-php': {
        'name': 'PHP LSP (Intelephense)',
        'check': 'test -f /opt/codehero/lsp/node/node_modules/.bin/intelephense && echo installed',
        'version_regex': r'(installed)',
        'install': [
            'mkdir -p /opt/codehero/lsp/node',
            'cd /opt/codehero/lsp/node && npm init -y 2>/dev/null || true',
            'cd /opt/codehero/lsp/node && npm install intelephense',
            'ln -sf /opt/codehero/lsp/node/node_modules/.bin/intelephense /usr/local/bin/intelephense 2>/dev/null || true',
            'python3 /opt/codehero/scripts/update_lsp_config.py php /opt/codehero/lsp/node/node_modules/.bin/intelephense',
            'echo "PHP LSP (Intelephense) installed to /opt/codehero/lsp/node"'
        ]
    },
    'lsp-java': {
        'name': 'Java LSP (Eclipse)',
        'check': 'test -d /opt/codehero/lsp/jdtls/plugins && echo installed',
        'version_regex': r'(installed)',
        'install': [
            'apt-get update && apt-get install -y default-jdk || true',
            'mkdir -p /opt/codehero/lsp/jdtls',
            'test -d /opt/codehero/lsp/jdtls/plugins || curl -fsSL "https://download.eclipse.org/jdtls/snapshots/jdt-language-server-latest.tar.gz" -o /tmp/jdtls.tar.gz',
            'test -f /tmp/jdtls.tar.gz && tar -xzf /tmp/jdtls.tar.gz -C /opt/codehero/lsp/jdtls && rm -f /tmp/jdtls.tar.gz || true',
            'echo "#!/bin/bash" > /opt/codehero/lsp/jdtls/jdtls.sh',
            'echo "JAR=\\$(find /opt/codehero/lsp/jdtls/plugins -name org.eclipse.equinox.launcher_*.jar | head -1)" >> /opt/codehero/lsp/jdtls/jdtls.sh',
            'echo "CONFIG=/opt/codehero/lsp/jdtls/config_linux" >> /opt/codehero/lsp/jdtls/jdtls.sh',
            'echo "java -Declipse.application=org.eclipse.jdt.ls.core.id1 -Dosgi.bundles.defaultStartLevel=4 -Declipse.product=org.eclipse.jdt.ls.core.product -jar \\$JAR -configuration \\$CONFIG -data \\${1:-/tmp/jdtls-workspace} \\$@" >> /opt/codehero/lsp/jdtls/jdtls.sh',
            'chmod +x /opt/codehero/lsp/jdtls/jdtls.sh',
            'ln -sf /opt/codehero/lsp/jdtls/jdtls.sh /usr/local/bin/jdtls 2>/dev/null || true',
            'python3 /opt/codehero/scripts/update_lsp_config.py java /opt/codehero/lsp/jdtls/jdtls.sh',
            'echo "Java LSP (Eclipse JDTLS) installed to /opt/codehero/lsp/jdtls"'
        ]
    },
    'lsp-csharp': {
        'name': 'C# LSP (OmniSharp)',
        'check': 'test -f /opt/codehero/lsp/omnisharp/OmniSharp && echo installed',
        'version_regex': r'(installed)',
        'install': [
            'mkdir -p /opt/codehero/lsp/omnisharp',
            'test -f /opt/codehero/lsp/omnisharp/OmniSharp || curl -fsSL "https://github.com/OmniSharp/omnisharp-roslyn/releases/download/v1.39.11/omnisharp-linux-x64-net6.0.tar.gz" -o /tmp/omnisharp.tar.gz',
            'test -f /tmp/omnisharp.tar.gz && tar -xzf /tmp/omnisharp.tar.gz -C /opt/codehero/lsp/omnisharp && chmod +x /opt/codehero/lsp/omnisharp/OmniSharp && rm -f /tmp/omnisharp.tar.gz || true',
            'ln -sf /opt/codehero/lsp/omnisharp/OmniSharp /usr/local/bin/omnisharp 2>/dev/null || true',
            'python3 /opt/codehero/scripts/update_lsp_config.py csharp /opt/codehero/lsp/omnisharp/OmniSharp',
            'echo "C# LSP (OmniSharp) installed to /opt/codehero/lsp/omnisharp"'
        ]
    },
    'lsp-kotlin': {
        'name': 'Kotlin LSP',
        'check': 'test -f /opt/codehero/lsp/kotlin/server/bin/kotlin-language-server && echo installed',
        'version_regex': r'(installed)',
        'install': [
            'apt-get update && apt-get install -y default-jdk unzip || true',
            'mkdir -p /opt/codehero/lsp/kotlin',
            'test -f /opt/codehero/lsp/kotlin/server/bin/kotlin-language-server || curl -fsSL "https://github.com/fwcd/kotlin-language-server/releases/download/1.3.9/server.zip" -o /tmp/kotlin-ls.zip',
            'test -f /tmp/kotlin-ls.zip && unzip -q -o /tmp/kotlin-ls.zip -d /opt/codehero/lsp/kotlin && chmod +x /opt/codehero/lsp/kotlin/server/bin/kotlin-language-server && rm -f /tmp/kotlin-ls.zip || true',
            'ln -sf /opt/codehero/lsp/kotlin/server/bin/kotlin-language-server /usr/local/bin/kotlin-language-server 2>/dev/null || true',
            'python3 /opt/codehero/scripts/update_lsp_config.py kotlin /opt/codehero/lsp/kotlin/server/bin/kotlin-language-server',
            'echo "Kotlin LSP installed to /opt/codehero/lsp/kotlin"'
        ]
    },
    'dotnet': {
        'name': '.NET SDK 8.0',
        'check': 'dotnet --version',
        'version_regex': r'(\d+\.\d+\.\d+)',
        'install': [
            'apt-get update',
            'apt-get install -y wget',
            # Only add MS repo if not exists
            'test -f /etc/apt/sources.list.d/microsoft-prod.list || wget https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/packages-microsoft-prod.deb -O /tmp/packages-microsoft-prod.deb',
            'test -f /etc/apt/sources.list.d/microsoft-prod.list || dpkg -i /tmp/packages-microsoft-prod.deb',
            'apt-get update',
            'apt-get install -y dotnet-sdk-8.0',
            'rm -f /tmp/packages-microsoft-prod.deb || true'
        ]
    },
    'powershell': {
        'name': 'PowerShell',
        'check': 'pwsh --version',
        'version_regex': r'PowerShell (\d+\.\d+\.\d+)',
        'install': [
            'apt-get update',
            'apt-get install -y wget apt-transport-https software-properties-common',
            # Only add MS repo if not exists
            'test -f /etc/apt/sources.list.d/microsoft-prod.list || wget https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/packages-microsoft-prod.deb -O /tmp/packages-microsoft-prod.deb',
            'test -f /etc/apt/sources.list.d/microsoft-prod.list || dpkg -i /tmp/packages-microsoft-prod.deb || true',
            'apt-get update',
            'apt-get install -y powershell',
            'rm -f /tmp/packages-microsoft-prod.deb || true'
        ]
    },
    'wine': {
        'name': 'Wine',
        'check': 'wine --version',
        'version_regex': r'wine-(\d+\.\d+)',
        'install': [
            'dpkg --add-architecture i386 || true',
            'apt-get update',
            'apt-get install -y wine wine64 || apt-get install -y wine || true'
        ]
    },
    'mono': {
        'name': 'Mono Runtime',
        'check': 'mono --version | head -1',
        'version_regex': r'(\d+\.\d+\.\d+)',
        'install': [
            'apt-get install -y gnupg ca-certificates',
            # Only add mono repo if not exists
            'test -f /etc/apt/sources.list.d/mono-official-stable.list || apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 3FA7E0328081BFF6A14DA29AA6A19B38D3D831EF',
            'test -f /etc/apt/sources.list.d/mono-official-stable.list || echo "deb https://download.mono-project.com/repo/ubuntu stable-focal main" | tee /etc/apt/sources.list.d/mono-official-stable.list',
            'apt-get update',
            'apt-get install -y mono-complete nuget || apt-get install -y mono-runtime || true'
        ]
    },
    'docker': {
        'name': 'Docker',
        'check': 'docker --version',
        'version_regex': r'Docker version (\d+\.\d+\.\d+)',
        'install': [
            'apt-get update',
            'apt-get install -y ca-certificates curl gnupg',
            'install -m 0755 -d /etc/apt/keyrings',
            # Only add docker repo if not exists
            'test -f /etc/apt/keyrings/docker.gpg || curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg',
            'chmod a+r /etc/apt/keyrings/docker.gpg || true',
            'test -f /etc/apt/sources.list.d/docker.list || echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null',
            'apt-get update',
            'apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin',
            'systemctl enable docker || true',
            'systemctl start docker || true',
            'usermod -aG docker claude || true'
        ]
    },
    'redroid': {
        'name': 'Redroid Android',
        'check': 'docker images redroid/redroid --format "{{.Tag}}" 2>/dev/null | head -1',
        'version_regex': r'(\d+\.\d+\.\d+)',
        'install': [
            # Check if docker is running
            'systemctl is-active docker || systemctl start docker',
            'docker pull redroid/redroid:15.0.0-latest',
            'apt-get install -y android-tools-adb || true',
            # Create config directory
            'mkdir -p /opt/codehero/android',
            # Update config
            '''python3 -c "import json; f='/opt/codehero/android/config.json'; c=json.load(open(f)) if __import__('os').path.exists(f) else {}; c['redroid']={'image':'redroid/redroid:15.0.0-latest','status':'installed'}; json.dump(c,open(f,'w'),indent=2)"''',
            'echo "Redroid Android configured in /opt/codehero/android/config.json"'
        ]
    },
    'flutter': {
        'name': 'Flutter SDK',
        'check': 'test -d /opt/flutter && /opt/flutter/bin/flutter --version 2>&1 | head -1',
        'version_regex': r'Flutter (\d+\.\d+\.\d+)',
        'install': [
            'apt-get install -y curl git unzip xz-utils zip libglu1-mesa clang cmake ninja-build pkg-config libgtk-3-dev || true',
            # Only clone if not exists
            'test -d /opt/flutter || git clone https://github.com/flutter/flutter.git -b stable /opt/flutter',
            'ln -sf /opt/flutter/bin/flutter /usr/local/bin/flutter || true',
            'ln -sf /opt/flutter/bin/dart /usr/local/bin/dart || true',
            '/opt/flutter/bin/flutter precache || true',
            # Create config directory
            'mkdir -p /opt/codehero/android',
            # Update config
            '''python3 -c "import json; f='/opt/codehero/android/config.json'; c=json.load(open(f)) if __import__('os').path.exists(f) else {}; c['flutter']='/opt/flutter/bin/flutter'; c['dart']='/opt/flutter/bin/dart'; json.dump(c,open(f,'w'),indent=2)"''',
            'echo "Flutter SDK configured in /opt/codehero/android/config.json"'
        ]
    },
    'android-tools': {
        'name': 'Android Tools',
        'check': 'adb version 2>&1 | head -1',
        'version_regex': r'(\d+\.\d+\.\d+)',
        'install': [
            'apt-get update',
            'apt-get install -y android-tools-adb gradle openjdk-17-jdk || apt-get install -y android-tools-adb || true',
            'update-alternatives --set java /usr/lib/jvm/java-17-openjdk-amd64/bin/java 2>/dev/null || true',
            # Create config directory
            'mkdir -p /opt/codehero/android',
            # Update config
            '''python3 -c "import json; f='/opt/codehero/android/config.json'; c=json.load(open(f)) if __import__('os').path.exists(f) else {}; c['adb']='$(which adb)'; c['gradle']='$(which gradle)'; json.dump(c,open(f,'w'),indent=2)"''',
            'echo "Android Tools configured in /opt/codehero/android/config.json"'
        ]
    },
    'scrcpy': {
        'name': 'ws-scrcpy',
        'check': 'test -f /opt/ws-scrcpy/package.json && echo installed',
        'version_regex': r'(installed)',
        'install': [
            'apt-get install -y git ffmpeg libsdl2-2.0-0 wget gcc make || true',
            'apt-get install -y android-tools-adb || true',
            # Only clone if not exists
            'test -d /opt/ws-scrcpy || git clone https://github.com/AltScore/ws-scrcpy.git /opt/ws-scrcpy',
            'cd /opt/ws-scrcpy && npm install || true',
            'cd /opt/ws-scrcpy && npm run dist || true',
            # Create config directory
            'mkdir -p /opt/codehero/android',
            # Update config
            '''python3 -c "import json; f='/opt/codehero/android/config.json'; c=json.load(open(f)) if __import__('os').path.exists(f) else {}; c['scrcpy']='/opt/ws-scrcpy'; json.dump(c,open(f,'w'),indent=2)"''',
            'echo "ws-scrcpy configured in /opt/codehero/android/config.json"'
        ]
    },
    # =====================================================
    # Configuration Scripts - Full environment setup
    # These run the complete setup scripts with all configurations
    # =====================================================
    'setup-android': {
        'name': 'Android Environment Setup',
        'check': 'test -f /etc/systemd/system/ws-scrcpy.service && docker ps -a --format "{{.Names}}" | grep -q "^redroid$" && echo configured',
        'version_regex': r'(configured)',
        'install': [
            'echo "Running full Android environment setup..."',
            'bash /opt/codehero/scripts/setup_android.sh',
            # Update config with full android setup
            'mkdir -p /opt/codehero/android',
            'python3 /opt/codehero/scripts/update_android_config.py',
            'echo "Android environment fully configured!"'
        ]
    },
    'setup-lsp': {
        'name': 'LSP Servers Setup',
        'check': 'test -f /usr/local/bin/jdtls && test -f /usr/local/bin/omnisharp && echo configured',
        'version_regex': r'(configured)',
        'install': [
            'echo "Running full LSP servers setup..."',
            'bash /opt/codehero/scripts/setup_lsp.sh',
            # Update config with all LSP paths
            'mkdir -p /opt/codehero/lsp',
            'python3 /opt/codehero/scripts/update_lsp_full_config.py',
            'echo "LSP servers fully configured!"'
        ]
    },
    'setup-windows': {
        'name': 'Windows Dev Environment Setup',
        'check': 'test -f /etc/profile.d/windows-dev.sh && command -v dotnet && echo configured',
        'version_regex': r'(configured)',
        'install': [
            'echo "Running full Windows development setup..."',
            'bash /opt/codehero/scripts/setup_windows.sh',
            # Update config
            'mkdir -p /opt/codehero/windows',
            'python3 /opt/codehero/scripts/update_windows_config.py',
            'echo "Windows development environment fully configured!"'
        ]
    }
}

@app.route('/packages')
@login_required
def packages():
    """Package Manager page"""
    return render_template('packages.html', user=session['user'], role=session.get('role'), version=VERSION)

@app.route('/api/packages/status')
@login_required
def packages_status():
    """Check installed status of all packages"""
    import re
    results = {}

    for pkg_id, pkg_info in PACKAGES.items():
        try:
            result = subprocess.run(
                pkg_info['check'],
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and result.stdout.strip():
                output = result.stdout.strip()
                version = None
                if pkg_info.get('version_regex'):
                    match = re.search(pkg_info['version_regex'], output)
                    if match:
                        version = match.group(1)
                results[pkg_id] = {'installed': True, 'version': version}
            else:
                results[pkg_id] = {'installed': False, 'version': None}
        except Exception as e:
            results[pkg_id] = {'installed': False, 'version': None, 'error': str(e)}

    return jsonify(results)

@app.route('/api/packages/install/<pkg>', methods=['POST'])
@login_required
def packages_install(pkg):
    """Start package installation (async with SocketIO updates)"""
    if pkg not in PACKAGES:
        return jsonify({'error': f'Unknown package: {pkg}'}), 404

    # Start installation in background thread
    def install_worker():
        pkg_info = PACKAGES[pkg]
        success = True

        try:
            socketio.emit('package_log', {'package': pkg, 'line': f'[INFO] Starting installation of {pkg_info["name"]}...'})

            for i, cmd in enumerate(pkg_info['install'], 1):
                # Wrap command with sudo for system-level operations
                display_cmd = cmd
                if not cmd.startswith('echo '):
                    cmd = f'sudo bash -c {repr(cmd)}'

                socketio.emit('package_log', {'package': pkg, 'line': f'\n[{i}/{len(pkg_info["install"])}] Running: {display_cmd}'})

                process = subprocess.Popen(
                    cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )

                # Stream output line by line
                for line in iter(process.stdout.readline, ''):
                    if line:
                        socketio.emit('package_log', {'package': pkg, 'line': line.rstrip()})

                process.wait()

                if process.returncode != 0:
                    socketio.emit('package_log', {'package': pkg, 'line': f'[ERROR] Command failed with exit code {process.returncode}'})
                    success = False
                    break
                else:
                    socketio.emit('package_log', {'package': pkg, 'line': '[OK] Command completed'})

            socketio.emit('package_complete', {'package': pkg, 'success': success})

        except Exception as e:
            socketio.emit('package_log', {'package': pkg, 'line': f'[ERROR] {str(e)}'})
            socketio.emit('package_complete', {'package': pkg, 'success': False})

    # Start worker thread
    threading.Thread(target=install_worker, daemon=True).start()

    return jsonify({'status': 'started', 'package': pkg})

@app.route('/api/lsp/config')
@login_required
def lsp_config():
    """Get LSP configuration for the app"""
    import json
    config_path = '/opt/codehero/lsp/config.json'
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            return jsonify(config)
        else:
            return jsonify({})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/android/config')
@login_required
def android_config():
    """Get Android development configuration for the app"""
    import json
    config_path = '/opt/codehero/android/config.json'
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            return jsonify(config)
        else:
            return jsonify({})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/windows/config')
@login_required
def windows_config():
    """Get Windows development configuration for the app"""
    import json
    config_path = '/opt/codehero/windows/config.json'
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            return jsonify(config)
        else:
            return jsonify({})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
    # Flask runs on internal port, Nginx handles SSL termination
    port = int(config.get('WEB_PORT', '5000'))
    host = config.get('WEB_HOST', '127.0.0.1')

    print(f"Starting Flask+SocketIO on http://{host}:{port}")
    print(f"Nginx proxies HTTPS:{config.get('ADMIN_PORT', '9453')} -> http://{host}:{port}")

    socketio.run(app, host=host, port=port, allow_unsafe_werkzeug=True)
