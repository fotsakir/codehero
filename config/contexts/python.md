# Python Development Context

## Security Patterns

### SQL Injection Prevention

```python
# MySQL Connector
cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
user = cursor.fetchone()

# SQLAlchemy
user = session.query(User).filter(User.email == email).first()
```

### Password Security

```python
import bcrypt

# Hashing
hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))

# Verification
if bcrypt.checkpw(input_password.encode(), stored_hash):
    # Password correct
```

### Environment Variables

```python
from dotenv import load_dotenv
import os

load_dotenv()
db_host = os.getenv('DB_HOST', 'localhost')
api_key = os.environ['API_KEY']  # Raises if missing
```

---

## Flask Application Pattern

```python
from flask import Flask, jsonify, request, session
from functools import wraps
import mysql.connector

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Database connection
def get_db():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASS')
    )
```

### Authentication Decorator

```python
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/api/protected')
@login_required
def protected():
    return jsonify({'message': 'Welcome!'})
```

### Login Route

```python
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, email, password_hash FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user or not bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
        return jsonify({'error': 'Invalid credentials'}), 401

    session['user_id'] = user['id']
    return jsonify({'success': True, 'user': {'id': user['id'], 'email': user['email']}})
```

---

## API Response Pattern

```python
def json_response(data, status=200):
    return jsonify({
        'success': status >= 200 and status < 300,
        'data': data
    }), status

def json_error(message, code='ERROR', status=400):
    return jsonify({
        'success': False,
        'error': {'code': code, 'message': message}
    }), status

# Usage
@app.route('/api/users/<int:user_id>')
def get_user(user_id):
    user = find_user(user_id)
    if not user:
        return json_error('User not found', 'NOT_FOUND', 404)
    return json_response(user)
```

---

## Input Validation

```python
from email_validator import validate_email, EmailNotValidError

def validate_user_input(data):
    errors = {}

    # Email validation
    email = data.get('email', '').strip()
    if not email:
        errors['email'] = 'Email is required'
    else:
        try:
            valid = validate_email(email)
            email = valid.normalized
        except EmailNotValidError:
            errors['email'] = 'Invalid email format'

    # Password validation
    password = data.get('password', '')
    if len(password) < 8:
        errors['password'] = 'Password must be at least 8 characters'

    # Name validation
    name = data.get('name', '').strip()
    if not name or len(name) < 2:
        errors['name'] = 'Name must be at least 2 characters'

    return errors, {'email': email, 'password': password, 'name': name}
```

---

## Database Patterns

### Connection Pool

```python
from mysql.connector import pooling

db_pool = pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=5,
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASS')
)

def get_db():
    return db_pool.get_connection()
```

### Transactions

```python
conn = get_db()
cursor = conn.cursor()
try:
    cursor.execute("INSERT INTO orders (user_id, total) VALUES (%s, %s)", (user_id, total))
    order_id = cursor.lastrowid

    for item in items:
        cursor.execute(
            "INSERT INTO order_items (order_id, product_id) VALUES (%s, %s)",
            (order_id, item['product_id'])
        )

    conn.commit()
except Exception as e:
    conn.rollback()
    raise e
finally:
    cursor.close()
    conn.close()
```

### Pagination

```python
def paginate(query, params, page=1, per_page=20):
    page = max(1, page)
    per_page = min(100, max(1, per_page))
    offset = (page - 1) * per_page

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # Get total count
    count_query = f"SELECT COUNT(*) as total FROM ({query}) as subquery"
    cursor.execute(count_query, params)
    total = cursor.fetchone()['total']

    # Get results
    paginated_query = f"{query} LIMIT %s OFFSET %s"
    cursor.execute(paginated_query, params + (per_page, offset))
    items = cursor.fetchall()

    cursor.close()
    conn.close()

    return {
        'items': items,
        'pagination': {
            'page': page,
            'total': total,
            'total_pages': (total + per_page - 1) // per_page
        }
    }
```

---

## Error Handling

```python
from flask import Flask
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {e}", exc_info=True)
    return jsonify({
        'success': False,
        'error': {'code': 'SERVER_ERROR', 'message': 'An error occurred'}
    }), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        'success': False,
        'error': {'code': 'NOT_FOUND', 'message': 'Resource not found'}
    }), 404
```

---

## File Upload Security

```python
import os
import secrets
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'pdf'}
MAX_SIZE = 10 * 1024 * 1024  # 10MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return json_error('No file provided', 'BAD_REQUEST', 400)

    file = request.files['file']
    if file.filename == '':
        return json_error('No file selected', 'BAD_REQUEST', 400)

    if not allowed_file(file.filename):
        return json_error('File type not allowed', 'BAD_REQUEST', 400)

    # Generate secure random filename
    ext = file.filename.rsplit('.', 1)[1].lower()
    new_filename = f"{secrets.token_hex(16)}.{ext}"

    file.save(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))
    return json_response({'filename': new_filename})
```

---

## Testing with pytest

```python
import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_login_success(client):
    response = client.post('/api/login', json={
        'email': 'test@example.com',
        'password': 'password123'
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] == True

def test_login_invalid_credentials(client):
    response = client.post('/api/login', json={
        'email': 'test@example.com',
        'password': 'wrongpassword'
    })
    assert response.status_code == 401
```
