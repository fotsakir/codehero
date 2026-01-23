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

### 1.4 GIT - DO NOT INITIALIZE WITHOUT PERMISSION

**⚠️ DO NOT create git repositories in project folders!**

```bash
# ❌ NEVER do this automatically:
git init
git add .
git commit -m "Initial commit"
```

**Why:**
- User may have their own version control setup
- Creates extra files that may not be wanted
- Takes time away from the actual task
- `.git` folder can be security risk if exposed

**If user wants git:**
- They will explicitly ask: "Initialize git" or "Add version control"
- Only then create the repository

**If project already has .git folder:**
- Do NOT make commits unless user asks
- Do NOT push to remote
- Respect existing git configuration

---

### 1.5 AUTHENTICATION - VERIFY EVERY FILE

**⚠️ CRITICAL: When building login/admin systems, EVERY protected file must check authentication!**

#### The Problem

```
/admin/
  login.php        ← Public (login form)
  dashboard.php    ← Has auth check ✅
  users.php        ← FORGOT auth check! ❌ Anyone can access!
  settings.php     ← FORGOT auth check! ❌ Anyone can access!
  api/data.php     ← FORGOT auth check! ❌ Data exposed!
```

#### The Solution

**Step 1: Create auth check include**
```php
// /admin/includes/auth_check.php
<?php
session_start();
if (!isset($_SESSION['admin_logged_in']) || $_SESSION['admin_logged_in'] !== true) {
    header('Location: login.php');
    exit;
}
?>
```

**Step 2: Include at TOP of EVERY protected file**
```php
<?php
// /admin/dashboard.php - FIRST LINE!
require_once __DIR__ . '/includes/auth_check.php';

// Rest of the file...
?>
```

#### Verification Checklist

**After creating login system, verify EVERY file in protected folder:**

```bash
# List all PHP files in admin folder
find /admin -name "*.php" -type f

# For EACH file, check if it has auth:
grep -l "auth_check\|session.*admin\|isLoggedIn" /admin/*.php
```

**Manual checklist:**
```
□ login.php - NO auth (it's the login page)
□ logout.php - NO auth (destroys session)
□ dashboard.php - HAS auth check at top?
□ users.php - HAS auth check at top?
□ settings.php - HAS auth check at top?
□ ALL other .php files - HAS auth check?
□ API endpoints - HAS auth check?
□ AJAX handlers - HAS auth check?
```

#### Common Mistakes

| Mistake | Risk | Fix |
|---------|------|-----|
| Auth check after HTML | Page partially loads | Put auth check at VERY TOP, before any output |
| Only checking on dashboard | Other pages exposed | Check on EVERY file |
| Checking $_SESSION without session_start() | Always fails | Include session_start() in auth check |
| API returns data without auth | Data leak | API endpoints need auth too |
| Forgot AJAX handlers | Actions without auth | All handlers need auth |

#### Testing Authentication

**After implementing login, test EACH protected URL directly:**

```python
import requests

# List of ALL protected pages
protected_urls = [
    "https://site/admin/dashboard.php",
    "https://site/admin/users.php",
    "https://site/admin/settings.php",
    "https://site/admin/api/data.php",
]

# Test WITHOUT login (should redirect or 403)
for url in protected_urls:
    r = requests.get(url, allow_redirects=False, verify=False)
    if r.status_code == 200:
        print(f"❌ VULNERABLE: {url} - accessible without login!")
    elif r.status_code in [301, 302, 303, 307, 308]:
        print(f"✅ Protected: {url} - redirects to login")
    elif r.status_code == 403:
        print(f"✅ Protected: {url} - returns 403")
```

**CRITICAL: Run this test BEFORE marking login task complete!**

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

**PHILOSOPHY: DIRECT EDITING ON PRODUCTION**
The code must be editable directly on the production server. When there's a bug:
1. Find the file on the server
2. Open it, find the line
3. Fix it on the spot
4. Done!

**This means:**
- ✅ **Source code format** - NOT minified, NOT bundled, NOT compressed
- ✅ **One file = one purpose** - NOT 5000 lines in one file
- ✅ **Readable names** - Know what it does by reading it
- ✅ **No build required for hotfixes** - Edit and it works
- ❌ **NO webpack/vite bundles in production** (unless user requests it)
- ❌ **NO TypeScript** (requires compilation)
- ❌ **NO minification** (can't read/debug it)
- ❌ **NO source maps needed** (code IS the source)

**Performance is NOT a priority.** We prefer:
- Readable code over fast code
- Multiple files over one bundled file
- Clear structure over optimized structure
- Easy debugging over micro-optimizations

**LANGUAGE DEFAULTS:**
- **JavaScript by default** - Use `.js` files, NOT TypeScript (`.ts`)
- Only use TypeScript if the project already has `tsconfig.json` or user explicitly requests it
- If user requests Vue/React: Use `.js`/`.jsx`, NOT `.ts`/`.tsx`
- PHP: Plain PHP files, directly editable

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

### 5.2 PLAYWRIGHT - COMPLETE VERIFICATION SCRIPT

**Use this ONE script for ALL checks: screenshots + console + links**

```python
from playwright.sync_api import sync_playwright
from urllib.parse import urljoin

def verify_page(url, project_path="/tmp"):
    """
    Complete page verification:
    - Desktop + Mobile screenshots
    - Console errors capture
    - Failed requests capture
    - All links extraction
    """
    results = {
        "console_errors": [],
        "console_warnings": [],
        "failed_requests": [],
        "all_links": [],
        "screenshots": {}
    }
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        
        # Capture console messages
        page.on("console", lambda msg: 
            results["console_errors"].append(msg.text) if msg.type == "error" else 
            results["console_warnings"].append(msg.text) if msg.type == "warning" else None
        )
        
        # Capture failed requests (404, CORS, etc.)
        page.on("requestfailed", lambda req: 
            results["failed_requests"].append(f"{req.url} - {req.failure}")
        )
        
        # Navigate to page
        page.goto(url)
        page.wait_for_load_state("networkidle")
        
        # Desktop screenshot
        page.set_viewport_size({"width": 1920, "height": 1080})
        desktop_path = f"{project_path}/screenshot_desktop.png"
        page.screenshot(path=desktop_path, full_page=True)
        results["screenshots"]["desktop"] = desktop_path
        
        # Mobile screenshot
        page.set_viewport_size({"width": 375, "height": 667})
        mobile_path = f"{project_path}/screenshot_mobile.png"
        page.screenshot(path=mobile_path, full_page=True)
        results["screenshots"]["mobile"] = mobile_path
        
        # Extract all links
        for a in page.query_selector_all("a[href]"):
            href = a.get_attribute("href")
            if href and not href.startswith("#") and not href.startswith("javascript:"):
                results["all_links"].append(urljoin(url, href))
        
        # Extract all images
        for img in page.query_selector_all("img[src]"):
            results["all_links"].append(urljoin(url, img.get_attribute("src")))
        
        browser.close()
    
    return results

# Usage
url = "https://127.0.0.1:9867/{folder_name}/"
results = verify_page(url)

# Print results
print("=== SCREENSHOTS ===")
print(f"Desktop: {results['screenshots']['desktop']}")
print(f"Mobile: {results['screenshots']['mobile']}")

print("\n=== CONSOLE ERRORS ===")
if results["console_errors"]:
    for e in results["console_errors"]:
        print(f"❌ {e}")
else:
    print("✅ No errors")

print("\n=== FAILED REQUESTS ===")
if results["failed_requests"]:
    for f in results["failed_requests"]:
        print(f"❌ {f}")
else:
    print("✅ All requests OK")

print(f"\n=== LINKS FOUND: {len(results['all_links'])} ===")
```

**After running, use Read tool to view screenshots:**
```
Read /tmp/screenshot_desktop.png
Read /tmp/screenshot_mobile.png
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
□ Color harmony (see 5.6.1)?
```

### 5.6.1 COLOR HARMONY & DESIGN CONSISTENCY

**⚠️ CRITICAL: Avoid jarring color combinations!**

#### The Problem: Extreme Contrast

```css
/* ❌ BAD - Jarring contrast */
.sidebar { background: #1f2937; }  /* Almost black */
.main    { background: #ffffff; }  /* Pure white */
/* Result: Visual "shock" between sections */

/* ✅ GOOD - Smooth transitions */
.sidebar { background: #1e3a5f; }  /* Deep blue */
.main    { background: #f0f4f8; }  /* Soft blue-gray */
/* Result: Harmonious, professional look */
```

#### Color Palette Rules

1. **Use 3-5 colors maximum** (primary, secondary, accent, neutral, background)
2. **Keep colors in the same temperature** (all warm OR all cool)
3. **Use tints/shades of the same hue** for variations
4. **Avoid pure black (#000) and pure white (#fff)** - use soft alternatives

#### Recommended Color Approach

| Element | Approach | Example |
|---------|----------|---------|
| **Background** | Soft, not pure white | `#f8fafc`, `#f1f5f9` |
| **Dark sections** | Deep but not black | `#1e3a5f`, `#1e293b` |
| **Text on light** | Dark gray, not black | `#1f2937`, `#334155` |
| **Text on dark** | Off-white, not pure white | `#e2e8f0`, `#f1f5f9` |
| **Primary color** | Saturated but not neon | `#2563eb`, `#0066cc` |
| **Accent** | Complementary to primary | If blue primary → orange/yellow accent |

#### Section Transitions

When sections have different backgrounds, ensure smooth visual flow:

```css
/* ❌ BAD - Abrupt change */
.hero    { background: #0f172a; }  /* Very dark */
.content { background: #ffffff; }  /* Pure white */

/* ✅ GOOD - Gradual transition */
.hero    { background: #1e3a5f; }  /* Deep blue */
.bridge  { background: #e2e8f0; }  /* Light blue-gray (optional transition) */
.content { background: #f8fafc; }  /* Very light blue-gray */
```

#### Harmony Checklist

```
□ Maximum 5 colors in palette?
□ Colors share same temperature (warm/cool)?
□ No pure black (#000) or pure white (#fff)?
□ Dark backgrounds use deep colors (not gray)?
□ Light backgrounds use soft tints (not stark white)?
□ Sections flow smoothly (no jarring transitions)?
□ Text has sufficient contrast but isn't harsh?
□ Accent color complements (not clashes with) primary?
```

#### Quick Fixes for Common Issues

| Issue | Fix |
|-------|-----|
| Sidebar too dark vs content | Use deep blue/green instead of gray |
| Sections feel disconnected | Add subtle gradient or transition section |
| Colors feel random | Pick colors from same palette (Tailwind, Material, etc.) |
| Text too stark | Use `#1f2937` instead of `#000`, `#f1f5f9` instead of `#fff` |
| Accent color clashes | Use color wheel - pick complementary or analogous |

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

**⚠️ REMEMBER: NO BUILD STEP!** All code must be directly editable on production server.

### Default by Project Type:

| Project Type | Default Stack |
|--------------|---------------|
| **Dashboard / Admin / ERP** | PHP + Alpine.js + Tailwind CSS |
| **Landing Page / Marketing** | HTML + Alpine.js + Tailwind CSS |
| **Simple Website** | HTML + Tailwind CSS |
| **API / Backend** | Based on project's tech_stack setting |

### Why NOT Vue/React/Angular with Build Tools:
```
❌ Vue + Vite       → Requires `npm run build`, can't hotfix on server
❌ React + Webpack  → Bundled output, source maps needed to debug
❌ Angular CLI      → Complex build, not directly editable
❌ TypeScript       → Requires compilation
```

### Libraries: Download Locally (No CDN in production!)

**Step 1: Download libraries once (at project setup):**
```bash
mkdir -p assets/lib
curl -o assets/lib/alpine.min.js https://unpkg.com/alpinejs@3/dist/cdn.min.js
curl -o assets/lib/tailwind.js https://cdn.tailwindcss.com/3.4.1
curl -o assets/lib/chart.min.js https://cdn.jsdelivr.net/npm/chart.js/dist/chart.umd.min.js
```

**Step 2: Use local files in HTML:**
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <script src="assets/lib/tailwind.js"></script>
    <script defer src="assets/lib/alpine.min.js"></script>
</head>
<body class="bg-gray-900 text-white">
    <div x-data="{ open: false }">
        <button @click="open = !open">Toggle Menu</button>
        <nav x-show="open">...</nav>
    </div>
</body>
</html>
```

**Why local downloads (NOT CDN):**
- ✅ Works offline
- ✅ No external dependencies
- ✅ Faster (no DNS lookup, no external request)
- ✅ More secure (no third-party CDN)
- ✅ Reliable (CDN might go down)
- ✅ Still no build step - just curl once

### For Complex Tables/Grids:
Use server-side rendering with Alpine.js for interactivity:
```html
<!-- PHP generates the table, Alpine handles UI -->
<table x-data="{ selected: [] }">
    <?php foreach($rows as $row): ?>
    <tr @click="selected.push(<?= $row['id'] ?>)">
        <td><?= $row['name'] ?></td>
    </tr>
    <?php endforeach; ?>
</table>
```

### If User EXPLICITLY Requests Vue/React:
Only then use build tools, but warn them:
```
User: "Use Vue with Vite"  → OK, but inform: "This requires build step,
                              hotfixes will need rebuild"
User: "Use React"          → OK, use create-react-app or Vite
```

### Common Libraries to Download:
```bash
# Core
curl -o assets/lib/alpine.min.js https://unpkg.com/alpinejs@3/dist/cdn.min.js
curl -o assets/lib/tailwind.js https://cdn.tailwindcss.com/3.4.1

# Charts
curl -o assets/lib/chart.min.js https://cdn.jsdelivr.net/npm/chart.js/dist/chart.umd.min.js
curl -o assets/lib/apexcharts.min.js https://cdn.jsdelivr.net/npm/apexcharts/dist/apexcharts.min.js

# Icons
curl -o assets/lib/lucide.min.js https://unpkg.com/lucide@latest/dist/umd/lucide.min.js

# Date/Time
curl -o assets/lib/dayjs.min.js https://cdn.jsdelivr.net/npm/dayjs@1/dayjs.min.js
```

**Exceptions (MUST stay as CDN/external):**
- Google Maps API (requires dynamic API key)
- Payment SDKs (Stripe.js, PayPal - security requirement)
- Analytics (Google Analytics, etc.)
- reCAPTCHA

### ⚠️ Download ALL External Assets Locally

**CRITICAL: Download EVERYTHING that can be downloaded. No external dependencies!**

**What MUST be downloaded locally:**
| Asset Type | Download To | Example |
|------------|-------------|----------|
| JS Libraries | `assets/lib/` | alpine.js, chart.js |
| CSS Frameworks | `assets/lib/` | bootstrap.css, tailwind.js |
| Fonts | `assets/fonts/` | roboto.woff2, icons.woff2 |
| Images/Photos | `assets/images/` | logo.png, hero.jpg |
| Icons | `assets/icons/` | favicon.ico, sprite.svg |
| Placeholder images | `assets/images/` | Use ui-avatars.com or download |

**For placeholder/avatar images:**
```bash
# ❌ NEVER use external placeholder services in production
# via.placeholder.com, placekitten.com, etc. are SLOW and unreliable

# ✅ Option 1: ui-avatars.com (acceptable - fast, generates on-the-fly)
<img src="https://ui-avatars.com/api/?name=John+Doe&size=300&background=667eea&color=fff">

# ✅ Option 2: Download placeholder once at setup
curl -o assets/images/default-avatar.png "https://ui-avatars.com/api/?name=User&size=300"

# ✅ Option 3: Create local colored placeholder with ImageMagick
convert -size 300x300 xc:#667eea assets/images/default-avatar.png
```

**Bootstrap example (download ALL parts):**
```bash
mkdir -p assets/lib assets/fonts

# CSS
curl -o assets/lib/bootstrap.min.css https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css

# JS
curl -o assets/lib/bootstrap.bundle.min.js https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js

# Icons (if using Bootstrap Icons)
curl -o assets/lib/bootstrap-icons.css https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css
mkdir -p assets/fonts
curl -o assets/fonts/bootstrap-icons.woff2 https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/fonts/bootstrap-icons.woff2
```

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
---

## 🧪 PART 9: MANDATORY TESTING

### 9.1 TEST FILE FOR EVERY CODE FILE

**CRITICAL: Every code file MUST have a corresponding test file!**

| Code File | Test File | Run With |
|-----------|-----------|----------|
| `user.php` | `user_test.php` | `php user_test.php` |
| `api.php` | `api_test.php` | `php api_test.php` |
| `service.py` | `service_test.py` | `python service_test.py` |
| `utils.js` | `utils_test.js` | `node utils_test.js` |

### 9.2 PHP TEST TEMPLATE

```php
<?php
/**
 * @file: user_test.php
 * @description: Tests for user.php
 * @usage: php user_test.php
 */
require_once __DIR__ . '/user.php';

$tests_passed = 0;
$tests_failed = 0;

function test($name, $condition) {
    global $tests_passed, $tests_failed;
    if ($condition) {
        echo "✅ PASS: $name\n";
        $tests_passed++;
    } else {
        echo "❌ FAIL: $name\n";
        $tests_failed++;
    }
}

// Tests
test('function exists', function_exists('myFunction'));
test('returns expected', myFunction('input') === 'expected');

// Summary
echo "\n=============================\n";
echo "Passed: $tests_passed | Failed: $tests_failed\n";
exit($tests_failed > 0 ? 1 : 0);
```

### 9.2b CHECK SERVER LOGS (MANDATORY!)

**⚠️ After ANY code change, check the relevant server logs for errors!**

**Log locations by tool:**
| Tool | Log File | Check Command |
|------|----------|---------------|
| PHP | `/var/log/nginx/*-error.log` | `sudo tail -20 /var/log/nginx/codehero-projects-error.log` |
| PHP-FPM | `/var/log/php8.3-fpm.log` | `sudo tail -20 /var/log/php8.3-fpm.log` |
| MySQL | `/var/log/mysql/error.log` | `sudo tail -20 /var/log/mysql/error.log` |
| Node.js | stdout or pm2 logs | `pm2 logs` or check process output |
| Python | stdout or app logs | Check process output or app log file |
| Nginx | `/var/log/nginx/error.log` | `sudo tail -20 /var/log/nginx/error.log` |

**After running/testing code, ALWAYS check logs:**
```bash
# PHP project - check for PHP errors
sudo tail -30 /var/log/nginx/codehero-projects-error.log | grep -i "error\|warning\|fatal"

# MySQL - check for query errors
sudo tail -20 /var/log/mysql/error.log

# Check all recent errors across logs
sudo journalctl -p err -n 20 --no-pager
```

**Common log errors to fix:**
| Error in Log | Meaning | Fix |
|--------------|---------|-----|
| `PHP Fatal error` | Code crash | Fix PHP syntax/logic |
| `PHP Warning` | Non-fatal issue | Fix but code runs |
| `MySQL Connection refused` | DB not running | `systemctl start mysql` |
| `Permission denied` | File permissions | `chmod`/`chown` fix |
| `File not found` | Missing file | Check path, create file |
| `Memory exhausted` | Out of RAM | Optimize code or increase limit |

**Workflow:**
```
1. Make code change
2. Test the feature (browser or CLI)
3. Check server logs for errors ← MANDATORY!
4. Fix any errors found
5. Repeat until logs are clean
```


### 9.3 BROWSER CONSOLE CHECK (MANDATORY!)

**⚠️ Use the unified script from Section 5.2!**

The script in **Section 5.2** does everything:
- ✅ Desktop + Mobile screenshots
- ✅ Console errors capture
- ✅ Failed requests (404, CORS, etc.)
- ✅ All links extraction

**Quick reference - what to check in results:**
| Result | Must Be | Action if Not |
|--------|---------|---------------|
| `console_errors` | Empty `[]` | Fix JavaScript errors |
| `failed_requests` | Empty `[]` | Fix missing files/paths |
| Screenshots | Visually correct | Fix CSS/layout issues |

**Common console errors:**
| Error | Cause | Fix |
|-------|-------|-----|
| `Uncaught ReferenceError` | Missing variable/function | Check typos, script order |
| `404 (Not Found)` | Missing file | Download locally or fix path |
| `CORS error` | Cross-origin blocked | Download resource locally |
| `TypeError: null` | Element not found | Add null checks |

### 9.4 LINK VERIFICATION (ALL LINKS!)

**Generate list of ALL links and test each one:**

```python
from playwright.sync_api import sync_playwright
import requests

# Get all links
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_context(ignore_https_errors=True).new_page()
    page.goto("https://127.0.0.1:9867/myproject/")
    
    links = [a.get_attribute('href') for a in page.query_selector_all('a[href]')]
    images = [img.get_attribute('src') for img in page.query_selector_all('img[src]')]
    browser.close()

# Test each link
for url in set(links + images):
    if url and not url.startswith('#'):
        try:
            r = requests.head(url, timeout=10, verify=False)
            status = "✅" if r.status_code < 400 else "❌"
            print(f"{status} {r.status_code} {url}")
        except Exception as e:
            print(f"❌ ERROR {url}: {e}")
```

### 9.5 TEXT CONTRAST RULES

**⚠️ Text must be readable! No dark-on-dark or light-on-light!**

| Background | Text Color | Result |
|------------|------------|--------|
| Dark (#1a1a2e, black) | White/Light (#f0f0f0) | ✅ Good |
| Light (#f5f5f5, white) | Black/Dark (#333) | ✅ Good |
| Dark | Dark | ❌ BAD - Unreadable! |
| Light | Light | ❌ BAD - Unreadable! |

**Minimum contrast ratio: 4.5:1 for normal text**

```css
/* ❌ BAD */
.dark-bg { background: #1a1a2e; color: #333; }

/* ✅ GOOD */
.dark-bg { background: #1a1a2e; color: #f0f0f0; }
```

### 9.6 COMPLETE VERIFICATION WORKFLOW

**Before marking ANY task complete:**

```
1. □ Run syntax check (php -l, python -m py_compile, etc.)
2. □ Run test file (*_test.php, *_test.py)
3. □ Check SERVER LOGS for errors (PHP, MySQL, Nginx)
4. □ Take screenshots (desktop + mobile)
5. □ Read screenshots with Read tool
6. □ Run BROWSER console error check (Playwright)
7. □ Run link verification (all links + images)
8. □ Check text contrast (no dark-on-dark)
9. □ Fix any issues found
10. □ Repeat from step 3 until ALL checks pass (zero errors!)
```



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
- [ ] Test file exists for each code file (*_test.php, *_test.py)
- [ ] All tests pass
- [ ] TECHNOLOGIES.md updated

**Assets:**
- [ ] All JS/CSS libraries downloaded locally (not CDN)
- [ ] All images/photos downloaded locally (not placeholder.com)
- [ ] Fonts downloaded locally (if used)

**UI:**
- [ ] data-testid on elements
- [ ] Screenshots taken (desktop + mobile, full page)
- [ ] Screenshots reviewed (actually looked at them!)
- [ ] No giant padding/margins/icons
- [ ] Text contrast OK (no dark-on-dark, light-on-light)
- [ ] Browser console errors checked (Playwright) - ZERO errors!
- [ ] Server logs checked (PHP, MySQL, etc.) - ZERO errors!
- [ ] All links verified (curl + Playwright)
- [ ] All images loading (no broken icons)
- [ ] Visual quality checklist passed (5.6)

---

> **Remember:** Simple code → Easy maintenance → AI can fix it → Evolution!
