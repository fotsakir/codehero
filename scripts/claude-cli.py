#!/usr/bin/env python3
"""
CodeHero CLI - Command line tool for managing projects and tickets
"""

import argparse
import sys
import os
import mysql.connector

CONFIG_FILE = "/etc/codehero/system.conf"

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

def get_db():
    config = load_config()
    return mysql.connector.connect(
        host=config.get('DB_HOST', 'localhost'),
        user=config.get('DB_USER', 'claude_user'),
        password=config.get('DB_PASSWORD', ''),
        database=config.get('DB_NAME', 'claude_knowledge')
    )

def generate_ticket_number(project_code, conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM tickets t
        JOIN projects p ON t.project_id = p.id
        WHERE p.code = %s
    """, (project_code,))
    count = cursor.fetchone()[0]
    cursor.close()
    return f"{project_code}-{count + 1:04d}"

# ============ PROJECT COMMANDS ============

def project_add(args):
    if not args.name or not args.code:
        print("Error: --name and --code are required")
        sys.exit(1)
    
    code = args.code.upper()
    project_type = args.type or 'web'
    
    # Default paths based on type
    web_path = args.web_path
    app_path = args.app_path
    
    if not web_path and project_type in ('web', 'hybrid', 'capacitor_ionic_vue'):
        web_path = f'/var/www/projects/{code.lower()}'

    # All mobile project types need app_path for their source/native code
    mobile_types = ('capacitor_ionic_vue', 'react_native', 'flutter', 'kotlin_multiplatform',
                   'android_java_xml', 'android_kotlin_xml', 'android_kotlin_compose')
    if not app_path and project_type in ('app', 'hybrid', 'api') + mobile_types:
        app_path = f'/opt/apps/{code.lower()}'
    
    # Read context from file if specified
    context = args.context or ''
    if args.context_file:
        try:
            with open(args.context_file, 'r') as f:
                context = f.read()
        except Exception as e:
            print(f"Warning: Could not read context file: {e}")
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO projects (name, code, description, project_type, tech_stack, 
                web_path, app_path, context, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'active', NOW(), NOW())
        """, (
            args.name, code, args.description or '', project_type,
            args.tech_stack or None, web_path or None, app_path or None, context or None
        ))
        conn.commit()
        project_id = cursor.lastrowid
        cursor.close()
        conn.close()
        
        # Create directories
        if web_path:
            os.makedirs(web_path, exist_ok=True)
            os.system(f'chown -R claude-worker:www-data {web_path} 2>/dev/null || true')
        if app_path:
            os.makedirs(app_path, exist_ok=True)
            os.system(f'chown -R claude-worker:claude-worker {app_path} 2>/dev/null || true')
        
        print(f"✅ Project created: {args.name} ({code})")
        print(f"   ID: {project_id}")
        print(f"   Type: {project_type}")
        if web_path: print(f"   Web: {web_path}")
        if app_path: print(f"   App: {app_path}")
        if context: print(f"   Context: {len(context)} chars")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

def project_list(args):
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
        cursor.close()
        conn.close()
        
        if not projects:
            print("No projects found.")
            return
        
        print(f"\n{'Code':<8} {'Name':<20} {'Type':<8} {'Tickets':<10} {'Paths':<35}")
        print("-" * 85)
        for p in projects:
            paths = []
            if p.get('web_path'): paths.append('web')
            if p.get('app_path'): paths.append('app')
            paths_str = '+'.join(paths) if paths else '-'
            print(f"{p['code']:<8} {p['name'][:18]:<20} {p.get('project_type','web'):<8} {p['open_count']}/{p['ticket_count']:<7} {paths_str:<35}")
        print()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

# ============ TICKET COMMANDS ============

def ticket_add(args):
    if not args.project or not args.title:
        print("Error: --project and --title are required")
        sys.exit(1)
    
    # Read context from file if specified
    context = args.context or ''
    if args.context_file:
        try:
            with open(args.context_file, 'r') as f:
                context = f.read()
        except Exception as e:
            print(f"Warning: Could not read context file: {e}")
    
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT id, code FROM projects WHERE code = %s OR name = %s", 
                      (args.project.upper(), args.project))
        project = cursor.fetchone()
        
        if not project:
            print(f"❌ Project not found: {args.project}")
            sys.exit(1)
        
        ticket_number = generate_ticket_number(project['code'], conn)
        priority = args.priority or 'medium'
        
        cursor.execute("""
            INSERT INTO tickets (project_id, ticket_number, title, description, context, priority, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'open', NOW(), NOW())
        """, (project['id'], ticket_number, args.title, args.description or '', context or None, priority))
        conn.commit()
        ticket_id = cursor.lastrowid
        cursor.close()
        conn.close()
        
        print(f"✅ Ticket created: {ticket_number}")
        print(f"   Title: {args.title}")
        print(f"   Priority: {priority}")
        if context: print(f"   Context: {len(context)} chars")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

def ticket_list(args):
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        if args.project:
            cursor.execute("""
                SELECT t.*, p.name as project_name, p.code FROM tickets t
                JOIN projects p ON t.project_id = p.id
                WHERE p.code = %s OR p.name = %s
                ORDER BY t.updated_at DESC
            """, (args.project.upper(), args.project))
        else:
            cursor.execute("""
                SELECT t.*, p.name as project_name, p.code FROM tickets t
                JOIN projects p ON t.project_id = p.id
                ORDER BY t.updated_at DESC LIMIT 20
            """)
        
        tickets = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not tickets:
            print("No tickets found.")
            return
        
        print(f"\n{'Number':<12} {'Title':<35} {'Priority':<10} {'Status':<12}")
        print("-" * 75)
        for t in tickets:
            print(f"{t['ticket_number']:<12} {t['title'][:33]:<35} {t['priority']:<10} {t['status']:<12}")
        print()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

# ============ STATUS COMMAND ============

def show_status(args):
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT COUNT(*) as cnt FROM projects WHERE status = 'active'")
        projects = cursor.fetchone()['cnt']
        
        cursor.execute("SELECT status, COUNT(*) as cnt FROM tickets GROUP BY status")
        ticket_stats = {r['status']: r['cnt'] for r in cursor.fetchall()}
        
        cursor.close()
        conn.close()
        
        print("\n=== CodeHero Status ===\n")
        print(f"Projects:        {projects}")
        print(f"Open tickets:    {ticket_stats.get('open', 0) + ticket_stats.get('new', 0)}")
        print(f"In progress:     {ticket_stats.get('in_progress', 0)}")
        print(f"Completed:       {ticket_stats.get('done', 0)}")
        
        pid_file = "/var/run/codehero/daemon.pid"
        daemon_running = False
        if os.path.exists(pid_file):
            try:
                with open(pid_file) as f:
                    pid = int(f.read().strip())
                os.kill(pid, 0)
                daemon_running = True
            except: pass
        
        print(f"\nDaemon:          {'🟢 Running' if daemon_running else '🔴 Stopped'}")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

# ============ MAIN ============

def main():
    parser = argparse.ArgumentParser(description='CodeHero CLI')
    subparsers = parser.add_subparsers(dest='command')
    
    # Project commands
    project_parser = subparsers.add_parser('project', help='Project management')
    project_sub = project_parser.add_subparsers(dest='action')
    
    p_add = project_sub.add_parser('add', help='Add new project')
    p_add.add_argument('--name', '-n', required=True, help='Project name')
    p_add.add_argument('--code', '-c', required=True, help='Project code')
    p_add.add_argument('--description', '-d', help='Description')
    p_add.add_argument('--type', '-t', choices=['web', 'app', 'hybrid', 'api', 'other'], default='web')
    p_add.add_argument('--tech-stack', help='Tech stack')
    p_add.add_argument('--web-path', help='Web files path')
    p_add.add_argument('--app-path', help='App files path')
    p_add.add_argument('--context', help='Context info (inline)')
    p_add.add_argument('--context-file', help='Context info from file')
    
    project_sub.add_parser('list', help='List projects')
    
    # Ticket commands
    ticket_parser = subparsers.add_parser('ticket', help='Ticket management')
    ticket_sub = ticket_parser.add_subparsers(dest='action')
    
    t_add = ticket_sub.add_parser('add', help='Add new ticket')
    t_add.add_argument('--project', '-p', required=True, help='Project code')
    t_add.add_argument('--title', '-t', required=True, help='Ticket title')
    t_add.add_argument('--description', '-d', help='Description')
    t_add.add_argument('--priority', choices=['low', 'medium', 'high', 'critical'], default='medium')
    t_add.add_argument('--context', help='Context info (inline)')
    t_add.add_argument('--context-file', help='Context info from file')
    
    t_list = ticket_sub.add_parser('list', help='List tickets')
    t_list.add_argument('--project', '-p', help='Filter by project')
    
    subparsers.add_parser('status', help='Show system status')
    
    args = parser.parse_args()
    
    if args.command == 'project':
        if args.action == 'add': project_add(args)
        elif args.action == 'list': project_list(args)
        else: project_parser.print_help()
    elif args.command == 'ticket':
        if args.action == 'add': ticket_add(args)
        elif args.action == 'list': ticket_list(args)
        else: ticket_parser.print_help()
    elif args.command == 'status':
        show_status(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
