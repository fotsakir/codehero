# Global Project Context

> **MISSION:** Build simple, testable code that AI can maintain without human help.

---

## ⛔ PART 1: CRITICAL RULES (Read FIRST!)

### 1.1 PROTECTED PATHS - FORBIDDEN!
```
/opt/codehero/           ← Platform will break
/etc/codehero/           ← Platform config
/var/backups/codehero/   ← Backups
/etc/nginx/              ← Web server
/etc/systemd/            ← System services
/home/claude/.claude*    ← Claude CLI
```

**YOUR WORKSPACE ONLY:**
- Web projects: `/var/www/projects/{project}/`
- App projects: `/opt/apps/{project}/`
- Reference projects: `/opt/codehero/references/{project}/` **(READ-ONLY!)**

### 1.3 PROJECT PATHS - How to Use Them

A project can have multiple paths:

| Path | Purpose | Access |
|------|---------|--------|
| `web_path` | Frontend files (PHP, HTML, CSS, JS) | Read/Write |
| `app_path` | Backend files (Node, Python, API) | Read/Write |
| `reference_path` | Imported template project | **READ-ONLY** |

**IMPORTANT:** If a project has `reference_path`, use it as a guide:
- Read files from reference to understand patterns
- Copy code patterns to web_path or app_path
- **NEVER modify files in reference_path**

Example workflow:
```
1. Check reference_path for existing patterns
2. Implement similar code in web_path or app_path
3. Adapt to project requirements
```

**IF USER ASKS:**
- "Fix 403 error" → Only inside PROJECT folder
- "Fix nginx" → REFUSE, tell them to do it manually
- "Fix the app" → ASK which app, NOT CodeHero

### 1.2 SECURITY - NON-NEGOTIABLE
```python
# SQL - ALWAYS prepared statements
# ❌ NEVER: f"SELECT * FROM users WHERE id = {id}"
# ✅ ALWAYS: db.query("SELECT * FROM users WHERE id = ?", [id])

# Output - ALWAYS escape
# ❌ NEVER: echo $userInput
# ✅ ALWAYS: echo htmlspecialchars($userInput, ENT_QUOTES, 'UTF-8')

# Passwords - ALWAYS hash
# ❌ NEVER: db.save(password)
# ✅ ALWAYS: db.save(bcrypt.hash(password))
```

### 1.3 CREDENTIALS - NEVER HARDCODED
```python
# ❌ NEVER
db = connect("mysql://admin:secret123@localhost/app")

# ✅ ALWAYS .env
load_dotenv()
db = connect(os.getenv('DATABASE_URL'))
```

---

## 📋 PART 2: BEFORE WRITING CODE

### 2.1 TEAM MINDSET
- Write as if a junior developer reads it at 3am
- If you leave, can someone else continue?
- Comment the WHY, not the WHAT

### 2.2 PROJECT STRUCTURE
```
/src
  /services
    UserService.py       ← Code
    UserService.md       ← API docs (REQUIRED)
    UserService_test.py  ← Tests (REQUIRED)
```

### 2.3 FILE HEADER (in EVERY file)
```python
"""
@file: UserService.py
@description: User registration, login, profile
@tags: #auth #users #login
@dependencies: db.py, validators.py
"""
```

### 2.4 NAMING CONVENTIONS
| Type | Convention | Example |
|------|------------|---------|
| Python files | snake_case | `user_service.py` |
| PHP files | PascalCase | `UserService.php` |
| Classes | PascalCase | `UserService` |
| Functions | camelCase | `createUser()` |
| Constants | UPPER_SNAKE | `MAX_RETRIES` |
| DB tables | snake_case plural | `order_items` |

### 2.5 CODE QUALITY & READABILITY

**⚠️ CRITICAL: Write HUMAN-READABLE code. NO obfuscation!**

**Code MUST be:**
- ✅ Well-formatted and properly indented
- ✅ With meaningful comments explaining complex logic
- ✅ Using descriptive, human-readable names
- ✅ Easy to understand and maintain
- ✅ Properly structured with clear separation of concerns

**NAMING - ALWAYS HUMAN-READABLE:**

| Type | Convention | ✅ Good Example | ❌ BAD Example |
|------|------------|-----------------|----------------|
| Variables | descriptive | `userEmail`, `totalPrice` | `x`, `tmp`, `data1` |
| Functions | verb + noun | `calculateTotal()` | `calc()`, `doIt()` |
| Classes | noun, clear purpose | `UserService` | `US`, `Handler1` |
| Files | describe content | `user_authentication.py` | `ua.py`, `file1.py` |
| Folders | logical grouping | `components/`, `services/` | `c/`, `s/`, `misc/` |

**NEVER:**
- ❌ Single-letter variable names (except loop counters `i`, `j`, `k`)
- ❌ Abbreviated names that aren't universally known
- ❌ Minified or obfuscated code in source files
- ❌ Magic numbers without explanation
- ❌ Functions longer than 50 lines without comments
- ❌ Deeply nested code (max 3-4 levels)

**ALWAYS:**
```python
# ✅ GOOD - Clear, readable
def calculate_order_total(order_items, discount_percentage):
    """Calculate total price with discount applied."""
    subtotal = sum(item.price * item.quantity for item in order_items)
    discount = subtotal * (discount_percentage / 100)
    return subtotal - discount

# ❌ BAD - Cryptic, unreadable
def calc(x, d):
    s = sum(i.p * i.q for i in x)
    return s - s * d / 100
```

```javascript
// ✅ GOOD - Descriptive names
const MAX_LOGIN_ATTEMPTS = 5;
const userAuthenticationStatus = checkUserCredentials(email, password);

// ❌ BAD - Magic numbers, cryptic names
const x = 5;
const s = check(e, p);
```

---

## 💻 PART 3: WRITING CODE

### 3.1 ERROR HANDLING - Never silent failures!
```python
# ❌ BAD - Nobody knows what happened
try:
    do_something()
except:
    pass

# ✅ GOOD
try:
    do_something()
except SpecificError as e:
    logger.error(f"Failed to do X: {e}")
    raise
```

### 3.2 NULL CHECKS - Always check first!
```python
# ❌ Crash if user=None
return f"Hello {user.name}"

# ✅ Safe
if not user:
    return "Hello Guest"
return f"Hello {user.name}"

# ✅ Safe dict access
name = data.get('name', 'Unknown')
```

### 3.3 TIMEOUTS - Never wait forever!
```python
# ❌ Hangs forever
response = requests.get(url)

# ✅ Timeout required
response = requests.get(url, timeout=10)
```

| Operation | Timeout |
|-----------|---------|
| HTTP API | 10-30s |
| DB query | 5-30s |
| File upload | 60-120s |

### 3.4 TRANSACTIONS - All or nothing
```python
# ❌ Crash after charge = money taken, no order
charge_card(user, amount)
create_order(user, amount)  # <-- crash here

# ✅ Transaction
try:
    db.begin()
    order = create_order(user, amount)
    charge_card(user, amount)
    db.commit()
except:
    db.rollback()
    raise
```

### 3.5 IDEMPOTENCY - Safe to run twice
```python
# ❌ 2 runs = 2 users!
db.execute("INSERT INTO users (email) VALUES (?)", [email])

# ✅ Check first
existing = db.query("SELECT id FROM users WHERE email = ?", [email])
if existing:
    return existing['id']
db.execute("INSERT INTO users (email) VALUES (?)", [email])
```

```sql
-- ✅ MySQL idempotent
INSERT INTO users (email, name) VALUES (?, ?)
ON DUPLICATE KEY UPDATE name = VALUES(name);
```

### 3.6 RACE CONDITIONS - Atomic operations
```python
# ❌ 2 users buy last item = stock -1!
item = db.query("SELECT stock FROM items WHERE id = ?", [id])
if item['stock'] > 0:
    db.execute("UPDATE items SET stock = stock - 1 WHERE id = ?", [id])

# ✅ Atomic
result = db.execute("""
    UPDATE items SET stock = stock - 1
    WHERE id = ? AND stock > 0
""", [id])
if result.affected_rows == 0:
    raise OutOfStockError()
```

### 3.7 DATABASE CONSTRAINTS
```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_email (email)
);

CREATE TABLE orders (
    user_id INT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT
);
```

### 3.8 INPUT VALIDATION
```python
def validate_email(email):
    if not email:
        raise ValidationError("Email required")
    if len(email) > 254:
        raise ValidationError("Email too long")
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        raise ValidationError("Invalid email")
    return email.strip().lower()
```

**File uploads:**
```python
ALLOWED = {'jpg', 'png', 'pdf'}
MAX_SIZE = 10 * 1024 * 1024  # 10MB

def validate_file(file):
    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in ALLOWED:
        raise ValidationError(f"Type not allowed: {ext}")
    if file.size > MAX_SIZE:
        raise ValidationError("File too large")
```

### 3.9 ATOMIC FILE WRITES
```python
# ❌ Crash = corrupted file
with open(path, 'w') as f:
    f.write(data)

# ✅ Write temp, then rename
import tempfile
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
with os.fdopen(fd, 'w') as f:
    f.write(data)
os.rename(tmp, path)
```

### 3.10 RESOURCE CLEANUP
```python
# ❌ Connection leak
conn = db.connect()
result = conn.query("SELECT * FROM users")
return result  # Connection never closed!

# ✅ Context manager
with db.connect() as conn:
    return conn.query("SELECT * FROM users")
# Auto-closed!
```

### 3.11 RETRY LOGIC
```python
import time

def retry(func, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            return func()
        except (ConnectionError, TimeoutError) as e:
            if attempt == max_attempts - 1:
                raise
            time.sleep(2 ** attempt)  # 1s, 2s, 4s
```

### 3.12 LOGGING
```python
import logging
logger = logging.getLogger('myapp')

# ✅ Log with context
logger.info(f"Order created: user={user_id}, order={order_id}, total={total}")
logger.error(f"Payment failed: user={user_id}, error={e}")

# ❌ Never log passwords, credit cards
```

| Level | Usage |
|-------|-------|
| DEBUG | Development only |
| INFO | Normal operations |
| WARNING | Recoverable issues |
| ERROR | Failures |
| CRITICAL | System broken |

### 3.13 DATE/TIME - Always UTC!
```python
from datetime import datetime, timezone

# ❌ Local time = bugs
now = datetime.now()

# ✅ UTC internally
now = datetime.now(timezone.utc)

# Convert for display only
from zoneinfo import ZoneInfo
local = utc_time.astimezone(ZoneInfo('Europe/Athens'))
```

**DB:** Store as `TIMESTAMP` (auto UTC)
**API:** ISO 8601 format `"2024-01-15T14:30:00Z"`

### 3.14 UTF-8 - Everywhere!
```python
# Files
with open('file.txt', 'r', encoding='utf-8') as f:

# PHP
mb_strlen($text, 'UTF-8');
```

```sql
-- Database
CREATE DATABASE myapp CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3.15 PAGINATION - Never unlimited!
```python
# ❌ 1M records = crash
users = db.query("SELECT * FROM users")

# ✅ Always LIMIT
def get_users(page=1, per_page=50):
    per_page = min(per_page, 100)  # Max 100!
    offset = (page - 1) * per_page
    return db.query("SELECT * FROM users LIMIT ? OFFSET ?", [per_page, offset])
```

### 3.16 CONFIG DEFAULTS
```python
# ❌ Crash if missing
api_key = os.environ['API_KEY']

# ✅ Default or fail fast
DEBUG = os.getenv('DEBUG', 'false') == 'true'
DB_HOST = os.getenv('DB_HOST', 'localhost')

def required_env(key):
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(f"Missing: {key}")
    return val

API_KEY = required_env('API_KEY')
```

---

## ✅ PART 4: BEFORE FINISHING

### 4.1 VERIFICATION CHECKLIST
```
□ Runs without errors?
□ Main functionality works?
□ Edge cases (null, empty, large data)?
□ Test script passes?
```

**How to verify:**
```bash
python -m py_compile script.py  # Syntax check
python script_test.py           # Run tests
```

### 4.2 DEBUG WORKFLOW
```
1. READ the error message (90% of solutions are there)
2. Check basics: syntax, imports, file paths, permissions
3. Add logging at key points
4. Isolate: comment out until it works
5. Check inputs: what value is ACTUALLY coming?
6. STILL STUCK → Ask user
```

### 4.3 ASK ONLY WHEN NECESSARY
**Default behavior: PROCEED autonomously. Only ask if truly stuck.**

Ask ONLY if:
- Requirements are ambiguous AND you cannot make a reasonable assumption
- Multiple valid approaches AND the choice significantly affects the outcome
- Action might cause data loss or break existing functionality

Do NOT ask for:
- Minor implementation details (just pick one)
- Styling preferences (follow existing patterns)
- Obvious decisions (use common sense)
- Confirmation of your plan (just do it)

---

## 🎨 PART 5: UI RULES

### 5.1 PLAYWRIGHT TEST IDs
```html
<button data-testid="login-btn">Login</button>
<input data-testid="email-input">
<div data-testid="error-message">
```

### 5.2 PLAYWRIGHT URL & SCREENSHOTS
```python
from playwright.sync_api import sync_playwright

url = "https://127.0.0.1:9867/{folder_name}/"

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(ignore_https_errors=True)  # REQUIRED!
    page = context.new_page()
    page.goto(url)

    # Desktop screenshot (full page!)
    page.set_viewport_size({"width": 1920, "height": 1080})
    page.screenshot(path='/tmp/desktop_full.png', full_page=True)

    # Mobile screenshot (full page!)
    page.set_viewport_size({"width": 375, "height": 667})
    page.screenshot(path='/tmp/mobile_full.png', full_page=True)
```

### 5.3 ⚠️ UI QUALITY ENFORCEMENT

**CRITICAL: Before marking ANY UI task as complete:**
1. Take screenshots (desktop + mobile, full page)
2. Read them with Read tool - ACTUALLY LOOK AT THEM!
3. Check for issues below
4. Fix issues → Screenshot again → Repeat until perfect

**Working functionality ≠ Good UI. A form that works but looks terrible = INCOMPLETE!**

### 5.4 COMMON UI KILLERS (Auto-fix without asking)

| Problem | Bad Example | Fix To |
|---------|-------------|--------|
| Giant padding/margins | `padding: 48px, 64px, 128px` | `padding: 16px` or `24px` max |
| Oversized icons | `width: 96px, 128px` | `width: 32px-48px` |
| Excessive spacing | `gap: 48px`, `margin-bottom: 64px` | `gap: 16px`, `margin-bottom: 16px` |
| Huge text (not H1) | `font-size: 3rem` | `font-size: 1.1rem-1.5rem` |

### 5.5 GOOD SIZING REFERENCE

| Element | Good Size |
|---------|-----------|
| Header height | 60-80px |
| Card padding | 16-24px |
| Card gap | 16-24px |
| Small icons | 24-32px |
| Medium icons | 40-48px |
| Profile photos | 80-120px |
| Section padding | 32-48px |
| H1 | 2-3rem (32-48px) |
| H2 | 1.5-2rem (24-32px) |
| Body text | 1rem (16px) |

### 5.6 VISUAL QUALITY CHECKLIST

Before marking UI task complete, verify:
```
□ No giant empty white spaces?
□ Icons/images proportional to containers?
□ Spacing consistent (8px, 12px, 16px, 24px multiples)?
□ Text readable (min 14px body, 16px ideal)?
□ Layout balanced (not all on one side)?
□ Cards similar sizes?
□ Responsive (no horizontal scroll on mobile)?
□ Looks professional (like Bootstrap/Tailwind sites)?
```

### 5.7 UI WORKFLOW

**Simple rule:**
```
UI CHANGE (HTML/CSS/JS)?  → Screenshot BOTH (desktop + mobile)
BACKEND ONLY (Python/PHP)? → No screenshot needed
```

**No gray areas.** If you touched HTML, CSS, or JS → test both viewports.

**Steps:**
```
1. Write HTML/CSS/JS
2. Take screenshots (full page, BOTH viewports!)
3. Read screenshots with Read tool
4. Check quality checklist (5.6)
5. Fix issues → Repeat from step 2
6. ONLY when perfect → Mark task complete
```

### 5.8 LINK & URL HANDLING

**⚠️ CRITICAL: This is a common source of bugs! Read carefully.**

#### The Problem

Projects are NOT at server root. They're in subfolders:
```
Server root:     https://IP:9867/
Project folder:  https://IP:9867/mysite/
Project files:   /var/www/projects/mysite/
```

**If you use `/` at the start, you go to SERVER ROOT, not project folder!**

| You write | Browser goes to | Result |
|-----------|-----------------|--------|
| `/index.php` | `https://IP:9867/index.php` | ❌ 404! |
| `/mysite/index.php` | `https://IP:9867/mysite/index.php` | ✅ Works |
| `index.php` | (current folder)/index.php | ✅ Works |

#### Rule: ALWAYS Use Relative Paths

**From project root (`/mysite/index.php`):**
```html
<!-- ❌ WRONG - Goes to server root -->
<a href="/about.php">About</a>
<a href="/pages/contact.php">Contact</a>
<img src="/images/logo.png">
<link href="/css/style.css">
<script src="/js/app.js"></script>
<form action="/submit.php">

<!-- ✅ CORRECT - Relative paths -->
<a href="about.php">About</a>
<a href="pages/contact.php">Contact</a>
<img src="images/logo.png">
<link href="css/style.css">
<script src="js/app.js"></script>
<form action="submit.php">
```

**From subfolder (`/mysite/pages/about.php`):**
```html
<!-- To go back to root files, use ../ -->
<a href="../index.php">Home</a>
<a href="../products.php">Products</a>
<img src="../images/logo.png">
<link href="../css/style.css">

<!-- To go to sibling file in same folder -->
<a href="contact.php">Contact</a>

<!-- To go deeper -->
<a href="admin/dashboard.php">Dashboard</a>
```

**JavaScript (fetch/AJAX):**
```javascript
// ❌ WRONG
fetch('/api/users')
$.get('/data/products.json')

// ✅ CORRECT - Relative
fetch('api/users')
$.get('data/products.json')

// ✅ CORRECT - From subfolder
fetch('../api/users')
```

**CSS (background images, fonts):**
```css
/* ❌ WRONG */
background: url(/images/bg.png);
src: url(/fonts/roboto.woff2);

/* ✅ CORRECT - From css/ folder, images are in ../images/ */
background: url(../images/bg.png);
src: url(../fonts/roboto.woff2);
```

#### Alternative: Base Tag (for complex sites)

If you have deep folder structures, use `<base>` tag:
```html
<head>
    <!-- All relative URLs will start from /mysite/ -->
    <base href="/mysite/">
</head>
<body>
    <!-- Now these work from ANY page, even /mysite/pages/sub/deep.php -->
    <a href="index.php">Home</a>
    <img src="images/logo.png">
</body>
```

#### Alternative: PHP Base Variable

```php
<?php
// At top of every page or in header.php
$base = rtrim(dirname($_SERVER['SCRIPT_NAME']), '/');
// If in subfolder: $base = '/mysite'
// Use in links:
?>
<a href="<?= $base ?>/index.php">Home</a>
<a href="<?= $base ?>/pages/about.php">About</a>
```

#### Quick Reference Table

| You're at | You want | Write |
|-----------|----------|-------|
| `/mysite/index.php` | `about.php` | `href="about.php"` |
| `/mysite/index.php` | `pages/contact.php` | `href="pages/contact.php"` |
| `/mysite/pages/about.php` | `index.php` | `href="../index.php"` |
| `/mysite/pages/about.php` | `contact.php` | `href="contact.php"` |
| `/mysite/pages/about.php` | `images/logo.png` | `src="../images/logo.png"` |
| `/mysite/admin/users/list.php` | `index.php` | `href="../../index.php"` |

#### MANDATORY: Test All Links

**After creating/modifying ANY page, verify links work:**

```python
# Playwright link test
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    page.goto("https://127.0.0.1:9867/mysite/")

    # Click each navigation link and verify no 404
    for link_text in ["Home", "About", "Contact", "Products"]:
        link = page.get_by_role("link", name=link_text)
        if link.count() > 0:
            link.click()
            page.wait_for_load_state('networkidle')
            # Check not 404
            assert '404' not in page.title().lower()
            assert 'not found' not in page.content().lower()
            page.go_back()

    browser.close()
```

#### Checklist Before Completing ANY Page Task

```
□ All <a href> links - clicked each one, no 404?
□ All <img src> - images visible, no broken icons?
□ All <link href> CSS - page styled correctly?
□ All <script src> JS - no console errors?
□ All <form action> - forms submit to correct URL?
□ All fetch()/AJAX - API calls working?
□ Tested from EVERY page, not just homepage?
□ Tested navigation: Home→About→Contact→Home works?
```

**Remember: A page that "works" but has broken links = INCOMPLETE TASK!**

---

## 🛠️ PART 6: DEFAULT TECH STACK

**⚠️ USER PREFERENCE ALWAYS WINS!** If user specifies a technology, use that instead of defaults.

### Default by Project Type:

| Project Type | Default Stack |
|--------------|---------------|
| **Complex Dashboard / Admin / ERP** | Vue 3 + PrimeVue + Vite |
| **Landing Page / Marketing Site** | HTML + Tailwind CSS + Alpine.js |
| **E-commerce (with SEO)** | Nuxt 3 + PrimeVue |
| **Simple Website** | HTML + Tailwind CSS |
| **API / Backend** | Based on project's tech_stack setting |

### Complex Dashboards (Vue 3 + PrimeVue 4):
```bash
npm create vite@latest myapp -- --template vue
cd myapp
npm install primevue primeicons primeflex @primeuix/themes
```

```javascript
// main.js
import { createApp } from 'vue';
import App from './App.vue';
import PrimeVue from 'primevue/config';
import Aura from '@primeuix/themes/aura';  // Themes: aura, lara, nora
import 'primeicons/primeicons.css';
import 'primeflex/primeflex.css';

const app = createApp(App);
app.use(PrimeVue, {
  theme: {
    preset: Aura,
    options: {
      darkModeSelector: '.p-dark'  // Add class="p-dark" to <html> for dark mode
    }
  }
});
app.mount('#app');
```

**⚠️ IMPORTANT:** Use `@primeuix/themes` (NOT `@primevue/themes` which is deprecated!)

**Dark mode:** Add `class="p-dark"` to `<html>` or `<body>` tag.

**PrimeVue includes:** DataTable (with child rows, filtering, sorting, export), Charts, TreeTable, Drag&Drop, MultiSelect, and 90+ components.

### Landing Pages (Tailwind + Alpine.js):
```html
<head>
    <script src="https://cdn.tailwindcss.com"></script>
    <script defer src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js"></script>
</head>
```

**Use for:** Marketing sites, landing pages, simple interactivity.

### If User Specifies Something Else:
```
User: "Use React instead of Vue"        → Use React
User: "Use Bootstrap not Tailwind"      → Use Bootstrap
User: "Use Angular with AG Grid"        → Use Angular + AG Grid
User: "Plain PHP, no frameworks"        → Use plain PHP
```

**Always follow user's technology preferences over these defaults.**

### Libraries: Download Locally (No CDN!)
**Always download libraries locally. Do NOT use CDN links.**

```bash
# ✅ GOOD - Install locally
npm install primevue chart.js alpinejs

# ❌ BAD - CDN links
<script src="https://cdn.jsdelivr.net/npm/..."></script>
```

**Why local:**
- Works offline
- Faster (no external requests)
- More secure (no third-party CDN)
- Reliable (CDN might go down)

**Exceptions (cannot download):**
- Google Maps API
- Google Fonts (or download fonts manually)
- Other APIs that require remote loading

---

## 📄 PART 7: DOCUMENTATION

### 7.1 TECHNOLOGIES.md (in every project)
```markdown
# Technologies

## Stack
- PHP 8.3 / Laravel 10
- MySQL 8.0
- Tailwind CSS

## APIs
- Stripe (payments)
- SendGrid (email)

## Environment Variables
- DB_HOST, DB_NAME, DB_USER, DB_PASS
- STRIPE_KEY
```

### 7.2 PROJECT_MAP.md
```markdown
# Project Map

## Structure
/src
  /controllers  → Handle HTTP requests
  /services     → Business logic
  /models       → Database entities

## Key Files
- index.php → Entry point
- AuthService.php → Login/logout

## API Endpoints
POST /api/login → AuthController::login
```

---

## 🖥️ PART 8: SERVER INFO

| Tool | Version |
|------|---------|
| Ubuntu | 24.04 |
| PHP | 8.3 |
| Node.js | 22.x |
| MySQL | 8.0 |
| Python | 3.12 |

**Ports:** Admin=9453, Projects=9867, MySQL=3306

**Paths:**
- PHP: `/var/www/projects/{code}/`
- Apps: `/opt/apps/{code}/`

**Before installing:** `which tool` - probably already installed!

---

## ✔️ FINAL CHECKLIST

**Security:**
- [ ] SQL prepared statements
- [ ] Inputs validated, outputs escaped
- [ ] Passwords hashed (bcrypt)
- [ ] No hardcoded credentials

**Reliability:**
- [ ] Timeouts on all external calls
- [ ] Transactions for related DB ops
- [ ] Null checks before using values
- [ ] Idempotent operations (safe to run twice)
- [ ] Race conditions prevented (atomic ops)
- [ ] Resources cleaned up (connections, files)
- [ ] Config has defaults or fails fast
- [ ] Dates in UTC
- [ ] UTF-8 everywhere
- [ ] Queries paginated

**Code Quality:**
- [ ] Junior can understand?
- [ ] File headers with @tags
- [ ] API docs (.md) exists
- [ ] Test script exists & passes
- [ ] TECHNOLOGIES.md updated

**UI:**
- [ ] data-testid on elements
- [ ] Screenshots taken (desktop + mobile, full page)
- [ ] Screenshots reviewed (actually looked at them!)
- [ ] No giant padding/margins/icons
- [ ] Visual quality checklist passed (5.6)

---

> **Remember:** Simple code → Easy maintenance → AI can fix it → Evolution!
