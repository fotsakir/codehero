# Node.js Development Context

## Security Patterns

### SQL Injection Prevention

```javascript
// MySQL2 - ALWAYS use prepared statements
const [rows] = await pool.execute('SELECT * FROM users WHERE email = ?', [email]);

// Sequelize
const user = await User.findOne({ where: { email } });
```

### Password Security

```javascript
const bcrypt = require('bcrypt');

// Hashing
const hash = await bcrypt.hash(password, 12);

// Verification
const match = await bcrypt.compare(inputPassword, storedHash);
if (match) {
    // Password correct
}
```

### Environment Variables

```javascript
require('dotenv').config();

const dbHost = process.env.DB_HOST || 'localhost';
const apiKey = process.env.API_KEY;
if (!apiKey) throw new Error('API_KEY required');
```

---

## Express Application Pattern

```javascript
const express = require('express');
const session = require('express-session');
const mysql = require('mysql2/promise');

const app = express();

// Middleware
app.use(express.json());
app.use(session({
    secret: process.env.SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    cookie: {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'strict',
        maxAge: 24 * 60 * 60 * 1000 // 24 hours
    }
}));

// Database pool
const pool = mysql.createPool({
    host: process.env.DB_HOST,
    user: process.env.DB_USER,
    password: process.env.DB_PASS,
    database: process.env.DB_NAME,
    waitForConnections: true,
    connectionLimit: 10
});
```

### Authentication Middleware

```javascript
const requireAuth = (req, res, next) => {
    if (!req.session.userId) {
        return res.status(401).json({
            success: false,
            error: { code: 'UNAUTHORIZED', message: 'Login required' }
        });
    }
    next();
};

// Usage
app.get('/api/protected', requireAuth, (req, res) => {
    res.json({ success: true, data: { userId: req.session.userId } });
});
```

### Login Route

```javascript
app.post('/api/login', async (req, res) => {
    try {
        const { email, password } = req.body;

        if (!email || !password) {
            return res.status(400).json({
                success: false,
                error: { code: 'VALIDATION', message: 'Email and password required' }
            });
        }

        const [rows] = await pool.execute(
            'SELECT id, email, password_hash FROM users WHERE email = ?',
            [email]
        );

        const user = rows[0];
        if (!user || !await bcrypt.compare(password, user.password_hash)) {
            return res.status(401).json({
                success: false,
                error: { code: 'INVALID_CREDENTIALS', message: 'Invalid email or password' }
            });
        }

        req.session.userId = user.id;
        res.json({ success: true, data: { id: user.id, email: user.email } });
    } catch (error) {
        console.error('Login error:', error);
        res.status(500).json({
            success: false,
            error: { code: 'SERVER_ERROR', message: 'An error occurred' }
        });
    }
});
```

---

## API Response Pattern

```javascript
const jsonResponse = (res, data, status = 200) => {
    res.status(status).json({
        success: status >= 200 && status < 300,
        data
    });
};

const jsonError = (res, message, code = 'ERROR', status = 400) => {
    res.status(status).json({
        success: false,
        error: { code, message }
    });
};

// Usage
app.get('/api/users/:id', async (req, res) => {
    const user = await findUser(req.params.id);
    if (!user) return jsonError(res, 'User not found', 'NOT_FOUND', 404);
    jsonResponse(res, user);
});
```

---

## Input Validation

```javascript
const validator = require('validator');

function validateUserInput(data) {
    const errors = {};
    const clean = {};

    // Email
    const email = (data.email || '').trim();
    if (!email) {
        errors.email = 'Email is required';
    } else if (!validator.isEmail(email)) {
        errors.email = 'Invalid email format';
    } else {
        clean.email = validator.normalizeEmail(email);
    }

    // Password
    const password = data.password || '';
    if (password.length < 8) {
        errors.password = 'Password must be at least 8 characters';
    } else {
        clean.password = password;
    }

    // Name
    const name = (data.name || '').trim();
    if (!name || name.length < 2) {
        errors.name = 'Name must be at least 2 characters';
    } else {
        clean.name = validator.escape(name);
    }

    return { errors, data: clean, hasErrors: Object.keys(errors).length > 0 };
}
```

---

## Database Patterns

### Transactions

```javascript
const connection = await pool.getConnection();
try {
    await connection.beginTransaction();

    const [orderResult] = await connection.execute(
        'INSERT INTO orders (user_id, total) VALUES (?, ?)',
        [userId, total]
    );
    const orderId = orderResult.insertId;

    for (const item of items) {
        await connection.execute(
            'INSERT INTO order_items (order_id, product_id) VALUES (?, ?)',
            [orderId, item.productId]
        );
    }

    await connection.commit();
} catch (error) {
    await connection.rollback();
    throw error;
} finally {
    connection.release();
}
```

### Pagination

```javascript
async function paginate(query, params, page = 1, perPage = 20) {
    page = Math.max(1, page);
    perPage = Math.min(100, Math.max(1, perPage));
    const offset = (page - 1) * perPage;

    // Get total count
    const countQuery = query.replace(/SELECT .* FROM/i, 'SELECT COUNT(*) as total FROM')
                           .replace(/ORDER BY .*/i, '');
    const [[{ total }]] = await pool.execute(countQuery, params);

    // Get results
    const [items] = await pool.execute(
        `${query} LIMIT ? OFFSET ?`,
        [...params, perPage, offset]
    );

    return {
        items,
        pagination: {
            page,
            total,
            totalPages: Math.ceil(total / perPage)
        }
    };
}
```

---

## Error Handling

```javascript
// Global error handler
app.use((err, req, res, next) => {
    console.error('Unhandled error:', err);
    res.status(500).json({
        success: false,
        error: { code: 'SERVER_ERROR', message: 'An error occurred' }
    });
});

// Async wrapper to catch promise rejections
const asyncHandler = (fn) => (req, res, next) => {
    Promise.resolve(fn(req, res, next)).catch(next);
};

// Usage
app.get('/api/users', asyncHandler(async (req, res) => {
    const users = await getUsers();
    res.json({ success: true, data: users });
}));
```

---

## File Upload Security

```javascript
const multer = require('multer');
const path = require('path');
const crypto = require('crypto');

const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'application/pdf'];
const MAX_SIZE = 10 * 1024 * 1024; // 10MB

const storage = multer.diskStorage({
    destination: './uploads/',
    filename: (req, file, cb) => {
        const ext = path.extname(file.originalname).toLowerCase();
        const randomName = crypto.randomBytes(16).toString('hex');
        cb(null, `${randomName}${ext}`);
    }
});

const upload = multer({
    storage,
    limits: { fileSize: MAX_SIZE },
    fileFilter: (req, file, cb) => {
        if (ALLOWED_TYPES.includes(file.mimetype)) {
            cb(null, true);
        } else {
            cb(new Error('File type not allowed'), false);
        }
    }
});

app.post('/api/upload', upload.single('file'), (req, res) => {
    if (!req.file) {
        return jsonError(res, 'No file uploaded', 'BAD_REQUEST', 400);
    }
    jsonResponse(res, { filename: req.file.filename });
});
```

---

## Testing with Jest

```javascript
const request = require('supertest');
const app = require('./app');

describe('Auth API', () => {
    test('POST /api/login - success', async () => {
        const res = await request(app)
            .post('/api/login')
            .send({ email: 'test@example.com', password: 'password123' });

        expect(res.status).toBe(200);
        expect(res.body.success).toBe(true);
    });

    test('POST /api/login - invalid credentials', async () => {
        const res = await request(app)
            .post('/api/login')
            .send({ email: 'test@example.com', password: 'wrongpassword' });

        expect(res.status).toBe(401);
        expect(res.body.success).toBe(false);
    });
});
```
