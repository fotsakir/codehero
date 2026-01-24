# Global Project Context v2.2

> **MISSION:** Build production-ready code that works correctly the first time.

---

## 🖥️ SERVER ENVIRONMENT

- **Operating System**: Ubuntu 24.04 LTS
- **Web Server**: Nginx
- **PHP Version**: PHP 8.3 (default)
- **Node.js**: v22.x
- **Python**: 3.12
- **MySQL**: 8.0

## 🔌 PORTS

| Service | Port | Protocol |
|---------|------|----------|
| Admin Panel | 9453 | HTTPS |
| Web Projects | 9867 | HTTPS |
| MySQL | 3306 | TCP (localhost only) |
| SSH | 22 | TCP |

## 📁 FILE LOCATIONS

- **PHP/Web Projects**: `/var/www/projects/{project}/`
- **App Projects**: `/opt/apps/{project}/`
- **PHP Binary**: `/usr/bin/php`
- **Node Binary**: `/usr/bin/node`

## 🛠️ INSTALLED TOOLS

### System
- Git, curl, wget, OpenSSL

### Databases
- MySQL 8.0 (server and client)

### PHP
- PHP 8.3 with extensions: mysql, curl, intl, opcache, gd, mbstring, xml, zip

### JavaScript
- Node.js 22.x with npm

### Python
- Python 3.12 with pip
- Flask, Flask-SocketIO, Flask-CORS
- mysql-connector-python, bcrypt, eventlet
- **Playwright** (with Chromium browser)
- Pillow, opencv-python-headless, pytesseract

### Multimedia
- ffmpeg, imagemagick, tesseract-ocr, poppler-utils

## ⚠️ IMPORTANT RULES

1. **Check before installing**: Most tools are already installed. Verify with `which [tool]` or `[tool] --version` before attempting installation
2. **Do NOT run `apt-get install`** for packages that are already installed
3. **PHP version**: Default is 8.3
4. **Project isolation**: Each project has its own directory and optionally its own MySQL database
5. **SSL certificates**: Managed by system - do not modify SSL config

### 📦 Libraries: Download Locally (NO CDN!)

**ALWAYS download libraries locally. NEVER use CDN links.**

```bash
# ✅ GOOD - Install locally
npm install primevue chart.js alpinejs
composer require phpmailer/phpmailer

# ❌ BAD - CDN links (FORBIDDEN!)
<script src="https://cdn.jsdelivr.net/npm/..."></script>
<link href="https://unpkg.com/..." rel="stylesheet">
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

## ✅ QUICK CHECKS

```bash
# Check versions
node --version && php --version | head -1 && python3 --version && mysql --version

# Check Playwright
python3 -c "from playwright.sync_api import sync_playwright; print('Playwright OK')"

# Check services
systemctl is-active nginx mysql php8.3-fpm
```

---

## ⚡ QUICK REFERENCE (Read This First!)

### ✅ ALWAYS DO:

**Security:**
- SQL: `$stmt->execute([$id])` — NEVER string concatenation
- Output: `htmlspecialchars($x, ENT_QUOTES, 'UTF-8')` — escape ALL user input
- Passwords: `password_hash($p, PASSWORD_BCRYPT)` — NEVER plain text or MD5
- Forms: Include `<input type="hidden" name="csrf_token">` on every POST form
- Sessions: `session_regenerate_id(true)` after login
- Protected pages: `require 'auth_check.php';` at the TOP of every protected file

**Database:**
- Charset: `utf8mb4` with `utf8mb4_0900_ai_ci` collation (MySQL 8.0+ default)
- Indexes: Add `INDEX` on columns used in WHERE/JOIN
- Transactions: Use `beginTransaction/commit/rollBack` for related operations

**UI:**
- Links: Relative paths `href="about.php"` — NOT `/about.php`
- Grid: Always include `grid-cols-*` (e.g., `grid grid-cols-1 md:grid-cols-3`)
- Flex: Always include direction `flex-row` or `flex-col`
- Dark backgrounds: Use light text `bg-gray-800 text-white`

**Design (Tailwind):**
- Spacing: Use 4px grid (`gap-2`=8px, `gap-4`=16px, `gap-6`=24px)
- Colors: 60% neutral (`gray-50`), 30% secondary (`gray-100-200`), 10% accent (`blue-600`)
- No pure black/white: Use `gray-900` and `gray-50` instead
- Buttons: `px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md`
- Cards: `bg-white rounded-lg shadow-sm border border-gray-200 p-6`
- Inputs: `w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500`
- Dark mode: Always add `dark:` variants (`dark:bg-gray-800 dark:text-white`)

### ❌ NEVER DO:

| Bad | Why | Good |
|-----|-----|------|
| `"WHERE id=$id"` | SQL Injection | `"WHERE id=?"` + bind |
| `echo $userInput` | XSS Attack | `echo htmlspecialchars($userInput)` |
| `$password` in code | Credential leak | `$_ENV['DB_PASS']` from .env |
| `href="/page.php"` | Breaks in subfolders | `href="page.php"` |
| `grid gap-4` | No columns defined | `grid grid-cols-3 gap-4` |
| `flex gap-4` | No direction | `flex flex-row gap-4` |

### 🧪 TEST COMMANDS:

```bash
# PHP Tests
php tests/MyTest.php

# Python Tests
pytest -v tests/

# UI Verification (screenshots + console errors)
python /opt/codehero/scripts/verify_ui.py https://127.0.0.1:9867/myproject/

# Check server logs
sudo tail -20 /var/log/nginx/codehero-projects-error.log
```

### 👁️ VISUAL VERIFICATION WITH PLAYWRIGHT

You have **Playwright with Chromium** available for visual testing. **USE IT** when:
1. User says something "doesn't look right" or "isn't displaying correctly"
2. User mentions layout, styling, or visual issues
3. You need to verify your changes visually
4. User explicitly asks you to "see" or "check" the page

**How to use Playwright for screenshots + error checking:**
```python
from playwright.sync_api import sync_playwright

console_errors = []
failed_requests = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()

    # Capture console errors
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

    # Capture failed requests (404, CORS, network errors)
    page.on("requestfailed", lambda req: failed_requests.append(f"{req.url} - {req.failure}"))

    page.set_viewport_size({"width": 1920, "height": 1080})
    page.goto('https://127.0.0.1:9867/myproject/')
    page.wait_for_load_state("networkidle")
    page.screenshot(path='/tmp/screenshot.png', full_page=True)
    browser.close()

# Report all errors
if console_errors:
    print("JS Console Errors:", console_errors)
if failed_requests:
    print("Failed Requests:", failed_requests)
if not console_errors and not failed_requests:
    print("No errors found!")
```

**After taking screenshot, ALWAYS check server logs for errors:**
```bash
# PHP errors
sudo tail -20 /var/log/nginx/codehero-projects-error.log

# Nginx errors
sudo tail -20 /var/log/nginx/error.log

# MySQL errors
sudo tail -20 /var/log/mysql/error.log

# Python/App errors (check project-specific logs)
sudo tail -20 /var/log/syslog | grep -i error

# Java errors (if applicable)
sudo tail -20 /var/log/syslog | grep -i java
```

**Fix ALL errors before marking task complete!**

**When User Says "It Doesn't Look Right":**
1. **Take a screenshot first** with Playwright
2. Analyze the visual issue
3. Fix and take another screenshot to verify
4. Don't ask the user to describe what's wrong - see it yourself

### 📐 ALIGNMENT & SYMMETRY

**ALWAYS verify visual alignment after changes:**

1. **Horizontal alignment** - Elements in same row must align
   - Use `items-center` for vertical centering in flex rows
   - Use `justify-between` or `justify-center` for horizontal distribution

2. **Vertical alignment** - Elements in same column must align
   - Use consistent widths (`w-full`, `w-1/2`, etc.)
   - Use `text-left`, `text-center`, `text-right` consistently

3. **Symmetry** - Equal spacing on both sides
   - Use `mx-auto` for centering blocks
   - Use equal padding (`px-4` not `pl-2 pr-6`)
   - Cards in grid should have same height (`h-full`)

4. **Visual balance**
   - Check with Playwright screenshot
   - Compare left vs right side
   - Compare top vs bottom

5. **Color check** - Verify in screenshot:
   - Text readable on background (contrast!)
   - Dark backgrounds → light text (`bg-gray-800 text-white`)
   - Light backgrounds → dark text (`bg-white text-gray-900`)
   - No pure black (#000) or pure white (#fff)
   - 60-30-10 color rule (60% neutral, 30% secondary, 10% accent)
   - Buttons visible and distinct from background

6. **Typography check** - Fonts must be:
   - Readable size (min 14px body, 12px captions)
   - Clear font family (no broken/missing fonts)
   - Proper contrast with background
   - Consistent hierarchy (H1 > H2 > H3 > body)
   - Line height for readability (`leading-relaxed` for body text)

7. **Interactive elements** - Test dropdowns, selects, modals:
   - Click select boxes and verify they open correctly
   - Check dropdown menus appear in correct position
   - Verify modals/dialogs display centered
   - Test hover states on buttons/links

8. **Consistency** - Overall uniformity:
   - Same font family throughout
   - Same color palette throughout
   - Same button styles throughout
   - Same spacing patterns throughout
   - Same border radius on similar elements

9. **Performance** - Check load/execution time:
   ```python
   import time
   start = time.time()
   page.goto('https://...')
   page.wait_for_load_state("networkidle")
   load_time = time.time() - start
   print(f"Page load: {load_time:.2f}s")  # Should be < 3s
   ```

10. **Full page inspection** - See ENTIRE page:
    ```python
    # Full page screenshot captures everything (vertical scroll)
    page.screenshot(path='/tmp/full.png', full_page=True)

    # For horizontal overflow, check page width
    width = page.evaluate("document.documentElement.scrollWidth")
    if width > 1920:
        print(f"WARNING: Horizontal overflow! Width: {width}px")

    # Scroll and inspect specific sections
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")  # Bottom
    page.screenshot(path='/tmp/bottom.png')

    page.evaluate("window.scrollTo(0, 0)")  # Back to top

    # Check footer visibility
    footer = page.query_selector("footer")
    if footer:
        footer.scroll_into_view_if_needed()
        page.screenshot(path='/tmp/footer.png')
    ```

    - **Always use `full_page=True`** to capture entire vertical content
    - **Check for horizontal overflow** (shouldn't exist on responsive sites)
    - **Scroll to footer** and verify it looks correct
    - **Take multiple screenshots** if page has different sections

11. **Accessibility**
    - All images have `alt` text
    - Form inputs have `<label>` elements
    - Buttons have descriptive text or `aria-label`
    - Color contrast ratio (text vs background)
    - Keyboard navigation works (Tab through elements)

12. **Forms validation**
    - Required fields show error when empty
    - Email fields validate format
    - Error messages are clear and visible
    - Success messages appear after submit
    - Form doesn't submit with invalid data

13. **Links check**
    - All internal links work (no 404)
    - External links open in new tab (`target="_blank"`)
    - No broken anchor links (#section)

14. **Images**
    - All images load (no broken images)
    - Images have appropriate size (not too large)
    - Lazy loading for below-fold images
    - Alt text describes the image

15. **Responsive - Tablet view** (768px)
    ```python
    page.set_viewport_size({"width": 768, "height": 1024})
    page.screenshot(path='/tmp/tablet.png', full_page=True)
    ```

16. **Empty states**
    - What shows when no data exists
    - Helpful message, not blank page
    - Call-to-action to add data

17. **Error states**
    - What shows when API fails
    - User-friendly error message
    - Retry option if applicable

18. **Favicon**
    ```python
    favicon = page.query_selector("link[rel*='icon']")
    if not favicon:
        print("WARNING: No favicon!")
    ```

19. **Loading states**
    - Spinners or skeletons during load
    - No blank/frozen screen while loading

### 🔄 FULL SITE TEST (End-to-End)

**WHEN to run full site test:**
- When ticket title/description contains: "final", "τελικό", "complete", "ολοκλήρωση", "deploy", "launch", "release"
- When ticket says: "test everything", "full test", "έλεγξε όλα"
- When you finished building a complete feature (e.g., auth system, checkout flow)
- When ticket is the LAST ticket in project sequence
- **Always ask yourself: "Is this a good stopping point to verify everything works?"**

**Run full site test:**

```python
from playwright.sync_api import sync_playwright

def full_site_test(base_url, login_credentials=None):
    """
    Complete site test:
    1. Start from homepage
    2. Login if needed
    3. Visit every link
    4. Test every interactive element
    """
    tested_urls = set()
    errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        # Capture all errors
        page.on("console", lambda msg: errors.append(f"Console: {msg.text}") if msg.type == "error" else None)
        page.on("requestfailed", lambda req: errors.append(f"Request failed: {req.url}"))

        # 1. Go to homepage
        page.goto(base_url)
        page.wait_for_load_state("networkidle")
        page.screenshot(path='/tmp/test_home.png', full_page=True)

        # 2. Login if credentials provided
        if login_credentials:
            login_form = page.query_selector("form[action*='login'], #login-form, .login-form")
            if login_form:
                page.fill("input[type='email'], input[name='email'], input[name='username']", login_credentials['user'])
                page.fill("input[type='password']", login_credentials['password'])
                page.click("button[type='submit'], input[type='submit']")
                page.wait_for_load_state("networkidle")
                print("Logged in successfully")

        # 3. Collect all links
        links = page.query_selector_all("a[href]")
        urls_to_test = []
        for link in links:
            href = link.get_attribute("href")
            if href and not href.startswith("#") and not href.startswith("javascript:"):
                if href.startswith("/"):
                    href = base_url.rstrip("/") + href
                if base_url in href and href not in tested_urls:
                    urls_to_test.append(href)

        # 4. Visit each page
        for url in urls_to_test:
            if url in tested_urls:
                continue
            tested_urls.add(url)
            try:
                page.goto(url)
                page.wait_for_load_state("networkidle")
                print(f"✓ {url}")

                # Test interactive elements on each page
                # Click all buttons (except submit/delete)
                buttons = page.query_selector_all("button:not([type='submit']):not(.delete):not(.danger)")
                for btn in buttons[:3]:  # Test first 3 buttons
                    try:
                        btn.click()
                        page.wait_for_timeout(500)
                    except:
                        pass

                # Test dropdowns/selects
                selects = page.query_selector_all("select")
                for select in selects:
                    try:
                        options = select.query_selector_all("option")
                        if len(options) > 1:
                            select.select_option(index=1)
                    except:
                        pass

            except Exception as e:
                errors.append(f"Failed to load {url}: {e}")
                print(f"✗ {url}: {e}")

        browser.close()

    # Report
    print(f"\n{'='*50}")
    print(f"Tested {len(tested_urls)} pages")
    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
    else:
        print("All tests passed!")
    print('='*50)

    return len(errors) == 0

# Usage:
# full_site_test("https://127.0.0.1:9867/myproject/")
# full_site_test("https://127.0.0.1:9867/myproject/", {"user": "admin@test.com", "password": "test123"})
```

**What this tests:**
- Every page loads without errors
- All links work
- Login functionality
- Buttons respond to clicks
- Dropdowns/selects work
- Console errors on any page
- Failed requests on any page

**Run this at the END of every project!**

**After any UI change, take screenshot and verify ALL above!**

**More Playwright examples:**
```python
# Click element
page.click("button.submit")

# Fill form
page.fill("input[name='email']", "test@example.com")

# Wait for element
page.wait_for_selector(".result")

# Get text content
text = page.text_content(".result")

# Check if element exists
if page.query_selector(".error"):
    print("Error found!")

# Mobile viewport
page.set_viewport_size({"width": 375, "height": 667})
```

### 📁 WORKSPACE:

```
Web projects:  /var/www/projects/{name}/
App projects:  /opt/apps/{name}/

FORBIDDEN:     /opt/codehero/, /etc/nginx/, /etc/systemd/
```

---

## PART 1: SECURITY (NON-NEGOTIABLE)

### 1.1 FORBIDDEN PATHS

```
NEVER TOUCH:
/opt/codehero/          - Platform code
/etc/codehero/          - Platform config
/etc/nginx/             - Web server
/etc/systemd/           - System services

YOUR WORKSPACE:
/var/www/projects/{project}/   - Web projects
/opt/apps/{project}/           - App projects
```

### 1.2 SQL INJECTION PREVENTION

**NEVER concatenate user input into SQL. ALWAYS use prepared statements.**

```php
// PHP - PDO
$stmt = $pdo->prepare("SELECT * FROM users WHERE email = ? AND status = ?");
$stmt->execute([$email, $status]);
$user = $stmt->fetch();

// PHP - MySQLi
$stmt = $mysqli->prepare("SELECT * FROM users WHERE id = ?");
$stmt->bind_param("i", $id);
$stmt->execute();
```

```python
# Python
cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
user = cursor.fetchone()
```

```java
// Java - JDBC
PreparedStatement stmt = conn.prepareStatement("SELECT * FROM users WHERE email = ?");
stmt.setString(1, email);
ResultSet rs = stmt.executeQuery();

// Java - JPA
@Query("SELECT u FROM User u WHERE u.email = :email")
Optional<User> findByEmail(@Param("email") String email);
```

```javascript
// Node.js - MySQL2
const [rows] = await pool.execute('SELECT * FROM users WHERE email = ?', [email]);
```

### 1.3 XSS PREVENTION

**ALWAYS escape output. NEVER trust user input.**

```php
// PHP - HTML output
echo htmlspecialchars($userInput, ENT_QUOTES, 'UTF-8');

// PHP - In attributes
<input value="<?= htmlspecialchars($value, ENT_QUOTES, 'UTF-8') ?>">

// PHP - JSON output
header('Content-Type: application/json');
echo json_encode($data, JSON_HEX_TAG | JSON_HEX_AMP);
```

```javascript
// JavaScript - DOM
element.textContent = userInput;  // Safe
element.innerHTML = userInput;    // DANGEROUS!

// With sanitization
import DOMPurify from 'dompurify';
element.innerHTML = DOMPurify.sanitize(userInput);
```

### 1.4 PASSWORD SECURITY

```php
// PHP - Hashing
$hash = password_hash($password, PASSWORD_BCRYPT, ['cost' => 12]);

// PHP - Verification
if (password_verify($inputPassword, $storedHash)) {
    // Password correct
}
```

```python
# Python
import bcrypt
hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))
if bcrypt.checkpw(input_password.encode(), stored_hash):
    # Password correct
```

```java
// Java
BCryptPasswordEncoder encoder = new BCryptPasswordEncoder(12);
String hash = encoder.encode(password);
if (encoder.matches(inputPassword, storedHash)) {
    // Password correct
}
```

### 1.5 CSRF PROTECTION

```php
// PHP - Generate token (on session start)
if (empty($_SESSION['csrf_token'])) {
    $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
}

// PHP - In every form
<form method="POST">
    <input type="hidden" name="csrf_token" value="<?= $_SESSION['csrf_token'] ?>">
    <!-- form fields -->
</form>

// PHP - Validate on every POST
function validateCsrf() {
    if (!isset($_POST['csrf_token']) ||
        !hash_equals($_SESSION['csrf_token'], $_POST['csrf_token'])) {
        http_response_code(403);
        die('CSRF validation failed');
    }
}
```

```java
// Spring - Auto-configured, just enable
@Configuration
public class SecurityConfig {
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http.csrf(csrf -> csrf.csrfTokenRepository(
            CookieCsrfTokenRepository.withHttpOnlyFalse()
        ));
        return http.build();
    }
}
```

### 1.6 SESSION SECURITY

```php
// PHP - php.ini or runtime
ini_set('session.cookie_httponly', 1);    // No JS access
ini_set('session.cookie_secure', 1);       // HTTPS only
ini_set('session.cookie_samesite', 'Strict');
ini_set('session.use_strict_mode', 1);

// Regenerate session ID after login
session_regenerate_id(true);
```

```java
// Spring - application.properties
server.servlet.session.cookie.http-only=true
server.servlet.session.cookie.secure=true
server.servlet.session.cookie.same-site=strict
server.servlet.session.timeout=30m
```

### 1.7 RATE LIMITING

```php
// PHP - Simple implementation with APCu
function checkRateLimit($key, $maxAttempts, $windowSeconds) {
    $attempts = apcu_fetch($key) ?: 0;
    if ($attempts >= $maxAttempts) {
        http_response_code(429);
        die(json_encode(['error' => 'Too many attempts. Try again later.']));
    }
    apcu_store($key, $attempts + 1, $windowSeconds);
}

// Usage
checkRateLimit('login_' . $_SERVER['REMOTE_ADDR'], 5, 900);  // 5 attempts per 15 min
checkRateLimit('api_' . $userId, 100, 60);                     // 100 requests per minute
```

### 1.8 FILE UPLOAD SECURITY

```php
function handleSecureUpload($file, $uploadDir = '/var/www/uploads/') {
    // Whitelist allowed extensions
    $allowed = ['jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx'];
    $maxSize = 10 * 1024 * 1024; // 10MB

    // Validate
    if ($file['error'] !== UPLOAD_ERR_OK) {
        throw new Exception('Upload failed');
    }
    if ($file['size'] > $maxSize) {
        throw new Exception('File too large');
    }

    $ext = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));
    if (!in_array($ext, $allowed)) {
        throw new Exception('File type not allowed');
    }

    // Generate safe filename (NEVER use original filename in path)
    $newName = bin2hex(random_bytes(16)) . '.' . $ext;
    $destination = $uploadDir . $newName;

    // Move file
    if (!move_uploaded_file($file['tmp_name'], $destination)) {
        throw new Exception('Failed to save file');
    }

    return $newName;
}
```

### 1.9 CREDENTIALS

**NEVER hardcode credentials. ALWAYS use environment variables.**

```
# .env file (NEVER commit to git)
DB_HOST=localhost
DB_NAME=myapp
DB_USER=myuser
DB_PASS=secretpassword
API_KEY=sk_live_xxxxx
```

```php
// PHP - Load with vlucas/phpdotenv
$dotenv = Dotenv\Dotenv::createImmutable(__DIR__);
$dotenv->load();

$dbHost = $_ENV['DB_HOST'] ?? 'localhost';
$apiKey = $_ENV['API_KEY'] ?? throw new Exception('API_KEY required');
```

```python
# Python
from dotenv import load_dotenv
import os

load_dotenv()
db_host = os.getenv('DB_HOST', 'localhost')
api_key = os.environ['API_KEY']  # Raises if missing
```

---

## PART 2: AUTHENTICATION (COMPLETE FLOW)

### 2.1 LOGIN SYSTEM

```php
// auth.php - Complete authentication system

class Auth {
    private PDO $db;

    public function __construct(PDO $db) {
        $this->db = $db;
    }

    public function login(string $email, string $password): ?array {
        // Validate input
        $email = filter_var($email, FILTER_VALIDATE_EMAIL);
        if (!$email) {
            return null;
        }

        // Get user
        $stmt = $this->db->prepare("SELECT id, email, password_hash, role FROM users WHERE email = ?");
        $stmt->execute([$email]);
        $user = $stmt->fetch(PDO::FETCH_ASSOC);

        if (!$user || !password_verify($password, $user['password_hash'])) {
            // Log failed attempt (for security monitoring)
            error_log("Failed login attempt for: $email");
            return null;
        }

        // Regenerate session ID (prevent session fixation)
        session_regenerate_id(true);

        // Store user in session
        $_SESSION['user_id'] = $user['id'];
        $_SESSION['user_email'] = $user['email'];
        $_SESSION['user_role'] = $user['role'];
        $_SESSION['login_time'] = time();

        return $user;
    }

    public function logout(): void {
        $_SESSION = [];
        session_destroy();
    }

    public function isLoggedIn(): bool {
        return isset($_SESSION['user_id']);
    }

    public function requireAuth(): void {
        if (!$this->isLoggedIn()) {
            header('Location: /login.php');
            exit;
        }
    }

    public function requireRole(string $role): void {
        $this->requireAuth();
        if ($_SESSION['user_role'] !== $role) {
            http_response_code(403);
            die('Access denied');
        }
    }
}
```

### 2.2 PROTECTED PAGE PATTERN

```php
<?php
// dashboard.php - EVERY protected page starts like this

require_once __DIR__ . '/includes/auth.php';
require_once __DIR__ . '/includes/db.php';

session_start();

$auth = new Auth($pdo);
$auth->requireAuth();  // Redirects if not logged in

// Now safe to show protected content
$userId = $_SESSION['user_id'];
?>
<!DOCTYPE html>
<html>
<!-- Protected content here -->
</html>
```

### 2.3 API AUTHENTICATION

```php
// api/middleware.php
function requireApiAuth(): array {
    $token = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
    $token = str_replace('Bearer ', '', $token);

    if (empty($token)) {
        http_response_code(401);
        die(json_encode(['error' => 'Token required']));
    }

    // Validate token (JWT or database lookup)
    $user = validateToken($token);
    if (!$user) {
        http_response_code(401);
        die(json_encode(['error' => 'Invalid token']));
    }

    return $user;
}

// api/users.php
header('Content-Type: application/json');
$user = requireApiAuth();

// Now handle the API request
```

---

## PART 3: INPUT VALIDATION

### 3.1 VALIDATION PATTERNS

```php
class Validator {
    private array $errors = [];

    public function email(string $value, string $field = 'email'): ?string {
        $value = trim($value);
        if (empty($value)) {
            $this->errors[$field] = 'Email is required';
            return null;
        }
        if (strlen($value) > 254) {
            $this->errors[$field] = 'Email is too long';
            return null;
        }
        $email = filter_var($value, FILTER_VALIDATE_EMAIL);
        if (!$email) {
            $this->errors[$field] = 'Invalid email format';
            return null;
        }
        return strtolower($email);
    }

    public function password(string $value, string $field = 'password'): ?string {
        if (strlen($value) < 8) {
            $this->errors[$field] = 'Password must be at least 8 characters';
            return null;
        }
        if (strlen($value) > 72) {  // bcrypt limit
            $this->errors[$field] = 'Password is too long';
            return null;
        }
        return $value;
    }

    public function string(string $value, string $field, int $min = 1, int $max = 255): ?string {
        $value = trim($value);
        if (strlen($value) < $min) {
            $this->errors[$field] = "$field must be at least $min characters";
            return null;
        }
        if (strlen($value) > $max) {
            $this->errors[$field] = "$field must be at most $max characters";
            return null;
        }
        return $value;
    }

    public function integer($value, string $field, int $min = null, int $max = null): ?int {
        if (!is_numeric($value)) {
            $this->errors[$field] = "$field must be a number";
            return null;
        }
        $int = (int) $value;
        if ($min !== null && $int < $min) {
            $this->errors[$field] = "$field must be at least $min";
            return null;
        }
        if ($max !== null && $int > $max) {
            $this->errors[$field] = "$field must be at most $max";
            return null;
        }
        return $int;
    }

    public function hasErrors(): bool {
        return !empty($this->errors);
    }

    public function getErrors(): array {
        return $this->errors;
    }
}

// Usage
$v = new Validator();
$email = $v->email($_POST['email'] ?? '');
$password = $v->password($_POST['password'] ?? '');
$name = $v->string($_POST['name'] ?? '', 'name', 2, 100);

if ($v->hasErrors()) {
    http_response_code(400);
    echo json_encode(['errors' => $v->getErrors()]);
    exit;
}
```

### 3.2 JAVA VALIDATION

```java
public class UserDTO {
    @NotNull(message = "Email is required")
    @Email(message = "Invalid email format")
    @Size(max = 254, message = "Email is too long")
    private String email;

    @NotNull(message = "Password is required")
    @Size(min = 8, max = 72, message = "Password must be 8-72 characters")
    private String password;

    @Size(min = 2, max = 100, message = "Name must be 2-100 characters")
    private String name;
}

// Controller
@PostMapping("/users")
public ResponseEntity<?> createUser(@Valid @RequestBody UserDTO dto, BindingResult result) {
    if (result.hasErrors()) {
        Map<String, String> errors = result.getFieldErrors().stream()
            .collect(Collectors.toMap(
                FieldError::getField,
                FieldError::getDefaultMessage
            ));
        return ResponseEntity.badRequest().body(Map.of("errors", errors));
    }
    // Process valid data
}
```

---

## PART 4: DATABASE PATTERNS

### 4.1 CONNECTION & CONFIGURATION

```php
// db.php
$dsn = sprintf(
    'mysql:host=%s;dbname=%s;charset=utf8mb4',
    $_ENV['DB_HOST'],
    $_ENV['DB_NAME']
);

$pdo = new PDO($dsn, $_ENV['DB_USER'], $_ENV['DB_PASS'], [
    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    PDO::ATTR_EMULATE_PREPARES => false,
]);
```

```sql
-- MySQL 8.0+ uses utf8mb4 and utf8mb4_0900_ai_ci by default
CREATE DATABASE myapp CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

-- Table with proper constraints and indexes
CREATE TABLE users (
    id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(254) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    role ENUM('user', 'admin') DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE INDEX idx_email (email),
    INDEX idx_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

### 4.2 TRANSACTIONS

```php
// When multiple related operations must succeed or fail together
try {
    $pdo->beginTransaction();

    // Create order
    $stmt = $pdo->prepare("INSERT INTO orders (user_id, total) VALUES (?, ?)");
    $stmt->execute([$userId, $total]);
    $orderId = $pdo->lastInsertId();

    // Create order items
    $stmt = $pdo->prepare("INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (?, ?, ?, ?)");
    foreach ($items as $item) {
        $stmt->execute([$orderId, $item['product_id'], $item['quantity'], $item['price']]);
    }

    // Decrease stock
    $stmt = $pdo->prepare("UPDATE products SET stock = stock - ? WHERE id = ? AND stock >= ?");
    foreach ($items as $item) {
        $stmt->execute([$item['quantity'], $item['product_id'], $item['quantity']]);
        if ($stmt->rowCount() === 0) {
            throw new Exception("Insufficient stock for product {$item['product_id']}");
        }
    }

    $pdo->commit();
} catch (Exception $e) {
    $pdo->rollBack();
    throw $e;  // Re-throw or handle
}
```

### 4.3 PAGINATION

```php
function paginate(PDO $pdo, string $query, array $params, int $page = 1, int $perPage = 20): array {
    // Ensure valid values
    $page = max(1, $page);
    $perPage = min(100, max(1, $perPage));  // Max 100 per page
    $offset = ($page - 1) * $perPage;

    // Get total count
    $countQuery = preg_replace('/SELECT .* FROM/i', 'SELECT COUNT(*) FROM', $query);
    $countQuery = preg_replace('/ORDER BY .*/i', '', $countQuery);
    $stmt = $pdo->prepare($countQuery);
    $stmt->execute($params);
    $total = (int) $stmt->fetchColumn();

    // Get paginated results
    $query .= " LIMIT $perPage OFFSET $offset";
    $stmt = $pdo->prepare($query);
    $stmt->execute($params);
    $items = $stmt->fetchAll();

    return [
        'items' => $items,
        'pagination' => [
            'page' => $page,
            'per_page' => $perPage,
            'total' => $total,
            'total_pages' => (int) ceil($total / $perPage),
        ]
    ];
}

// Usage
$result = paginate($pdo,
    "SELECT * FROM products WHERE category_id = ? ORDER BY created_at DESC",
    [$categoryId],
    $page,
    20
);
```

---

## PART 5: API DESIGN

### 5.1 CONSISTENT RESPONSE FORMAT

```php
// api/response.php
function jsonResponse($data, int $status = 200): never {
    http_response_code($status);
    header('Content-Type: application/json');
    echo json_encode([
        'success' => $status >= 200 && $status < 300,
        'data' => $data
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

function jsonError(string $message, string $code = 'ERROR', int $status = 400, ?string $field = null): never {
    http_response_code($status);
    header('Content-Type: application/json');
    $error = ['code' => $code, 'message' => $message];
    if ($field) $error['field'] = $field;
    echo json_encode(['success' => false, 'error' => $error], JSON_UNESCAPED_UNICODE);
    exit;
}

// Usage
jsonResponse(['user' => $user]);                           // 200 OK
jsonResponse(['user' => $user], 201);                      // 201 Created
jsonError('Email is required', 'VALIDATION_ERROR', 400, 'email');
jsonError('Not found', 'NOT_FOUND', 404);
jsonError('Server error', 'SERVER_ERROR', 500);
```

### 5.2 API ENDPOINT EXAMPLE

```php
// api/products.php
header('Content-Type: application/json');
require_once __DIR__ . '/../includes/db.php';
require_once __DIR__ . '/middleware.php';
require_once __DIR__ . '/response.php';

$method = $_SERVER['REQUEST_METHOD'];
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
$segments = explode('/', trim($path, '/'));
$productId = $segments[2] ?? null;

try {
    switch ($method) {
        case 'GET':
            if ($productId) {
                // GET /api/products/{id}
                $stmt = $pdo->prepare("SELECT * FROM products WHERE id = ?");
                $stmt->execute([$productId]);
                $product = $stmt->fetch();
                if (!$product) jsonError('Product not found', 'NOT_FOUND', 404);
                jsonResponse($product);
            } else {
                // GET /api/products?page=1&category=5
                $page = (int) ($_GET['page'] ?? 1);
                $category = $_GET['category'] ?? null;

                $query = "SELECT * FROM products";
                $params = [];
                if ($category) {
                    $query .= " WHERE category_id = ?";
                    $params[] = $category;
                }
                $query .= " ORDER BY created_at DESC";

                $result = paginate($pdo, $query, $params, $page);
                jsonResponse($result);
            }
            break;

        case 'POST':
            requireApiAuth();
            $data = json_decode(file_get_contents('php://input'), true);
            // Validate and create...
            jsonResponse($newProduct, 201);
            break;

        case 'PUT':
            requireApiAuth();
            if (!$productId) jsonError('Product ID required', 'BAD_REQUEST', 400);
            // Validate and update...
            jsonResponse($updatedProduct);
            break;

        case 'DELETE':
            requireApiAuth();
            if (!$productId) jsonError('Product ID required', 'BAD_REQUEST', 400);
            // Delete...
            jsonResponse(['deleted' => true]);
            break;

        default:
            jsonError('Method not allowed', 'METHOD_NOT_ALLOWED', 405);
    }
} catch (Exception $e) {
    error_log($e->getMessage());
    jsonError('Internal server error', 'SERVER_ERROR', 500);
}
```

---

## PART 6: ERROR HANDLING

### 6.1 GLOBAL ERROR HANDLER

```php
// includes/error_handler.php

set_error_handler(function ($severity, $message, $file, $line) {
    throw new ErrorException($message, 0, $severity, $file, $line);
});

set_exception_handler(function (Throwable $e) {
    error_log(sprintf(
        "[%s] %s in %s:%d\nStack trace:\n%s",
        date('Y-m-d H:i:s'),
        $e->getMessage(),
        $e->getFile(),
        $e->getLine(),
        $e->getTraceAsString()
    ));

    if (php_sapi_name() === 'cli') {
        echo "Error: " . $e->getMessage() . "\n";
        exit(1);
    }

    http_response_code(500);
    if (str_contains($_SERVER['HTTP_ACCEPT'] ?? '', 'application/json')) {
        header('Content-Type: application/json');
        echo json_encode(['success' => false, 'error' => ['code' => 'SERVER_ERROR', 'message' => 'An error occurred']]);
    } else {
        include __DIR__ . '/../templates/error_500.html';
    }
    exit;
});
```

### 6.2 TRY-CATCH PATTERNS

```php
// Specific exceptions for different error types
class ValidationException extends Exception {}
class NotFoundException extends Exception {}
class AuthException extends Exception {}

// Usage
try {
    $user = $userService->findById($id);
    if (!$user) {
        throw new NotFoundException("User not found");
    }
} catch (NotFoundException $e) {
    jsonError($e->getMessage(), 'NOT_FOUND', 404);
} catch (ValidationException $e) {
    jsonError($e->getMessage(), 'VALIDATION_ERROR', 400);
} catch (Exception $e) {
    error_log($e->getMessage());
    jsonError('An error occurred', 'SERVER_ERROR', 500);
}
```

---

## 🧠 PROGRAMMING PHILOSOPHY

### No Minify, No Obfuscate - CLEAN CODE ONLY

**NEVER minify or obfuscate code. Always keep it readable.**

```javascript
// ❌ FORBIDDEN - Minified/obfuscated
const a=b=>b.map(c=>c*2).filter(d=>d>5);

// ✅ REQUIRED - Clean and readable
const doubleAndFilter = (numbers) => {
    // Double each number
    const doubled = numbers.map(num => num * 2);
    // Keep only numbers greater than 5
    const filtered = doubled.filter(num => num > 5);
    return filtered;
};
```

**Rules:**
- Code must be readable by a **junior developer**
- Comments explain the **WHY**, not just the what
- Variable names are **descriptive** (not `a`, `b`, `x`)
- Functions are **small** and do **one thing**
- No clever tricks - **simple is better**

### Bottom-Up Development

**Always build from the BOTTOM UP:**

```
                    ┌─────────────────┐
                    │   FULL APP      │  ← Build LAST
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
        ┌─────┴─────┐  ┌─────┴─────┐  ┌─────┴─────┐
        │  Feature  │  │  Feature  │  │  Feature  │  ← Build after base works
        │     A     │  │     B     │  │     C     │
        └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
              │              │              │
        ┌─────┴─────────────┴──────────────┴─────┐
        │           BASE COMPONENTS              │  ← Build FIRST
        │   (DB connection, Auth, Utilities)     │
        └────────────────────────────────────────┘
```

**Process:**

1. **Break the problem into pieces**
   - Identify all components needed
   - Find dependencies between them
   - Order from least dependent to most

2. **Start from the BASE**
   - Database connection
   - Configuration
   - Utility functions
   - Authentication

3. **Build UP, one layer at a time**
   - Each layer uses only the layers BELOW it
   - Test each layer BEFORE building the next
   - Never build on something untested

4. **Always build on WORKING code**
   - Run tests after each component
   - Fix bugs immediately, don't continue
   - If it doesn't work, don't build on it

**Example - Building an E-commerce Site:**

```
Step 1: Database + Config     ← Test it works
Step 2: User model            ← Test CRUD works
Step 3: Auth system           ← Test login/logout works
Step 4: Product model         ← Test CRUD works
Step 5: Cart functionality    ← Test add/remove works
Step 6: Checkout flow         ← Test payment works
Step 7: Full integration      ← Test everything together
```

**NEVER:**
- Build checkout before cart works
- Build cart before products work
- Build features before auth works
- Build anything before database works

### Comments Everywhere

```php
<?php
/**
 * Calculate the total price including tax and discounts.
 *
 * Why: Tax calculation is complex because different regions have
 * different rates, and discounts can be percentage or fixed amount.
 */
function calculateTotal(array $items, float $taxRate, ?Discount $discount): float
{
    // Step 1: Sum up all item prices
    // We use array_reduce for cleaner code than a foreach loop
    $subtotal = array_reduce($items, function($sum, $item) {
        return $sum + ($item['price'] * $item['quantity']);
    }, 0);

    // Step 2: Apply discount if exists
    // Discount can be percentage (e.g., 10%) or fixed (e.g., $5 off)
    if ($discount !== null) {
        if ($discount->type === 'percentage') {
            // Percentage discount: subtract percentage of subtotal
            $subtotal -= $subtotal * ($discount->value / 100);
        } else {
            // Fixed discount: subtract fixed amount
            $subtotal -= $discount->value;
        }
    }

    // Step 3: Add tax
    // Tax is calculated on the discounted subtotal
    $tax = $subtotal * $taxRate;

    // Step 4: Return final total (ensure not negative)
    return max(0, $subtotal + $tax);
}
```

**Comment Rules:**
- **File header**: What this file does, how to use it
- **Function header**: Purpose, parameters, return value
- **Complex logic**: Explain WHY, not just what
- **Business rules**: Document the business reason
- **TODO/FIXME**: Mark incomplete or problematic code

### 📝 Project Documentation Files (MANDATORY)

**Every project MUST have these files:**

#### 1. `technologies.md` - Technology Stack Notes

```markdown
# Technologies Used

## Backend
- **PHP 8.3** - Main language
  - PDO for database
  - Sessions for auth

## Database
- **MySQL 8.0**
  - utf8mb4 charset
  - InnoDB engine

## Frontend
- **Tailwind CSS 3.4** - Styling
  - Custom config in tailwind.config.js
  - Dark mode enabled

## Libraries
- **PHPMailer 6.8** - Email sending
  - SMTP config in .env
  - Usage: see `src/EmailService.php`

- **Chart.js 4.4** - Charts
  - Installed in: assets/lib/chart.js/
  - Quick reference: see `docs/chartjs-notes.md`

## APIs
- **Stripe** - Payments
  - API version: 2023-10-16
  - Keys in .env
```

#### 2. `map.md` - Application Structure Map

```markdown
# Application Map

## Directory Structure
```
project/
├── index.php           # Entry point, routes to pages
├── config/
│   ├── database.php    # DB connection (PDO)
│   └── constants.php   # App constants
├── src/
│   ├── Auth.php        # Login/logout/register
│   ├── UserService.php # User CRUD
│   └── ProductService.php
├── pages/
│   ├── home.php        # Homepage
│   ├── login.php       # Login form
│   └── dashboard.php   # Protected - requires auth
├── api/
│   ├── users.php       # REST /api/users
│   └── products.php    # REST /api/products
├── assets/
│   ├── css/
│   ├── js/
│   └── lib/            # Downloaded libraries
└── tests/
```

## Page Flow
```
index.php → login.php → dashboard.php
                ↓
          [Auth.php checks session]
                ↓
          [UserService.php loads data]
```

## Database Tables
- `users` - id, email, password_hash, name, role
- `products` - id, name, price, category_id
- `orders` - id, user_id, total, status, created_at

## API Endpoints
- `GET /api/users` - List users (admin only)
- `POST /api/users` - Create user
- `GET /api/products` - List products
- `POST /api/orders` - Create order
```

#### 3. `docs/` - Library Quick References

**For large libraries, create quick reference notes:**

```
docs/
├── chartjs-notes.md      # Chart.js quick reference
├── primevue-notes.md     # PrimeVue components we use
├── stripe-notes.md       # Stripe API quick reference
└── phpmailer-notes.md    # PHPMailer usage
```

**Example: `docs/chartjs-notes.md`**

```markdown
# Chart.js Quick Reference

## Installation
Located in: `assets/lib/chart.js/chart.min.js`

## Basic Usage
```javascript
const ctx = document.getElementById('myChart');
new Chart(ctx, {
    type: 'bar',  // bar, line, pie, doughnut
    data: {
        labels: ['Jan', 'Feb', 'Mar'],
        datasets: [{
            label: 'Sales',
            data: [10, 20, 30],
            backgroundColor: 'rgba(59, 130, 246, 0.5)'
        }]
    }
});
```

## Common Options
- `responsive: true` - Auto resize
- `maintainAspectRatio: false` - Custom height
- `plugins.legend.position: 'bottom'` - Legend position

## Our Custom Colors
```javascript
const colors = {
    primary: 'rgba(59, 130, 246, 0.5)',   // blue
    success: 'rgba(34, 197, 94, 0.5)',    // green
    danger: 'rgba(239, 68, 68, 0.5)'      // red
};
```

## Examples in Project
- `pages/dashboard.php` - Sales chart
- `pages/reports.php` - Monthly comparison
```

### Why Keep These Notes?

| Problem | Solution |
|---------|----------|
| "What version of X are we using?" | Check `technologies.md` |
| "Where is the auth logic?" | Check `map.md` |
| "How do I use Chart.js?" | Check `docs/chartjs-notes.md` |
| "What API endpoints exist?" | Check `map.md` |

**RULE: Update these files whenever you:**
- Add a new technology
- Add a new file/folder
- Install a new library
- Create a new API endpoint

**Benefits:**
- No searching through huge library docs
- Quick onboarding for new developers
- Instant answers to "how do I...?"
- Reduces repeated questions to AI

### 🏷️ CODE TAGS for Fast Navigation & Testing

**Add tags EVERYWHERE for:**
1. Fast code navigation (search by tag)
2. 100% Playwright testing (select by data-testid)

#### HTML Elements - data-testid

```html
<!-- EVERY interactive element MUST have data-testid -->

<!-- Forms -->
<form data-testid="login-form">
    <input data-testid="login-email" type="email" name="email">
    <input data-testid="login-password" type="password" name="password">
    <button data-testid="login-submit" type="submit">Login</button>
</form>

<!-- Navigation -->
<nav data-testid="main-nav">
    <a data-testid="nav-home" href="/">Home</a>
    <a data-testid="nav-products" href="/products">Products</a>
    <a data-testid="nav-cart" href="/cart">Cart</a>
</nav>

<!-- Buttons -->
<button data-testid="btn-add-to-cart">Add to Cart</button>
<button data-testid="btn-checkout">Checkout</button>
<button data-testid="btn-delete-item">Delete</button>

<!-- Data displays -->
<div data-testid="product-list">...</div>
<div data-testid="cart-total">$99.00</div>
<div data-testid="user-profile">...</div>

<!-- Modals/Dialogs -->
<div data-testid="modal-confirm-delete">...</div>
<div data-testid="modal-success">...</div>

<!-- Messages -->
<div data-testid="alert-success">Saved!</div>
<div data-testid="alert-error">Error occurred</div>
```

#### Naming Convention for data-testid

```
Format: [component]-[element]-[action/type]

Examples:
- login-form
- login-email
- login-submit
- nav-home
- nav-products
- btn-add-to-cart
- btn-delete-item
- modal-confirm
- alert-success
- product-list
- product-card-{id}
- cart-item-{id}
- cart-total
```

#### PHP/Python Code Tags

```php
<?php
// #TAG:AUTH - Authentication functions
// #TAG:AUTH:LOGIN
function login($email, $password) {
    // ...
}

// #TAG:AUTH:LOGOUT
function logout() {
    // ...
}

// #TAG:AUTH:REGISTER
function register($data) {
    // ...
}

// #TAG:PRODUCTS - Product management
// #TAG:PRODUCTS:LIST
function getProducts() {
    // ...
}

// #TAG:PRODUCTS:CREATE
function createProduct($data) {
    // ...
}

// #TAG:CART - Shopping cart
// #TAG:CART:ADD
function addToCart($productId, $quantity) {
    // ...
}
```

```python
# #TAG:API - API endpoints
# #TAG:API:USERS
@app.route('/api/users')
def get_users():
    pass

# #TAG:API:PRODUCTS
@app.route('/api/products')
def get_products():
    pass

# #TAG:DB - Database operations
# #TAG:DB:QUERY
def execute_query(sql, params):
    pass
```

#### Search Tags Quickly

```bash
# Find all auth-related code
grep -r "#TAG:AUTH" src/

# Find all API endpoints
grep -r "#TAG:API" src/

# Find specific function
grep -r "#TAG:CART:ADD" src/
```

#### 100% Playwright Testing with Tags

```python
from playwright.sync_api import sync_playwright

def test_full_application(base_url):
    """
    100% automated testing using data-testid tags.
    Tests EVERY tagged element in the application.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        errors = []
        tested = []

        # ========== LOGIN FLOW ==========
        page.goto(f"{base_url}/login")

        # Test login form exists
        assert page.locator('[data-testid="login-form"]').is_visible(), "Login form not found"
        tested.append("login-form")

        # Test login inputs
        page.locator('[data-testid="login-email"]').fill("test@example.com")
        tested.append("login-email")

        page.locator('[data-testid="login-password"]').fill("password123")
        tested.append("login-password")

        # Test login submit
        page.locator('[data-testid="login-submit"]').click()
        tested.append("login-submit")

        page.wait_for_load_state("networkidle")

        # ========== NAVIGATION ==========
        # Test all nav links
        nav_links = ['nav-home', 'nav-products', 'nav-cart']
        for link in nav_links:
            element = page.locator(f'[data-testid="{link}"]')
            if element.is_visible():
                element.click()
                page.wait_for_load_state("networkidle")
                tested.append(link)
            else:
                errors.append(f"Nav link not found: {link}")

        # ========== PRODUCTS ==========
        page.goto(f"{base_url}/products")

        # Test product list exists
        assert page.locator('[data-testid="product-list"]').is_visible()
        tested.append("product-list")

        # Test add to cart button
        add_btn = page.locator('[data-testid="btn-add-to-cart"]').first
        if add_btn.is_visible():
            add_btn.click()
            tested.append("btn-add-to-cart")

        # ========== CART ==========
        page.goto(f"{base_url}/cart")

        # Test cart total displays
        cart_total = page.locator('[data-testid="cart-total"]')
        if cart_total.is_visible():
            tested.append("cart-total")

        # ========== COLLECT ALL TESTIDS ==========
        # Find ALL data-testid elements on current page
        all_testids = page.evaluate('''() => {
            return Array.from(document.querySelectorAll('[data-testid]'))
                .map(el => el.getAttribute('data-testid'));
        }''')

        print(f"Found {len(all_testids)} testable elements")

        # ========== REPORT ==========
        browser.close()

        print(f"\n{'='*50}")
        print(f"TESTED: {len(tested)} elements")
        for t in tested:
            print(f"  ✓ {t}")

        if errors:
            print(f"\nERRORS: {len(errors)}")
            for e in errors:
                print(f"  ✗ {e}")

        print(f"\nALL DATA-TESTIDS FOUND:")
        for tid in all_testids:
            status = "✓" if tid in tested else "○"
            print(f"  {status} {tid}")

        coverage = len(tested) / len(all_testids) * 100 if all_testids else 0
        print(f"\nCOVERAGE: {coverage:.1f}%")
        print('='*50)

        return errors == []

# Usage
test_full_application("https://127.0.0.1:9867/myproject")
```

#### Tag Checklist

| Element Type | Tag Format | Example |
|--------------|------------|---------|
| Form | `{name}-form` | `login-form`, `register-form` |
| Input | `{form}-{field}` | `login-email`, `register-name` |
| Button | `btn-{action}` | `btn-submit`, `btn-delete` |
| Link/Nav | `nav-{page}` | `nav-home`, `nav-settings` |
| List | `{item}-list` | `product-list`, `user-list` |
| Card | `{item}-card` | `product-card`, `order-card` |
| Modal | `modal-{name}` | `modal-confirm`, `modal-edit` |
| Alert | `alert-{type}` | `alert-success`, `alert-error` |
| Section | `section-{name}` | `section-hero`, `section-features` |

**RULE: No element without a tag = No testing possible!**

---

## 📦 SCRIPT ARCHITECTURE: "CLOSED BOX" PRINCIPLE

**Every script/class/module MUST be a self-contained "closed box":**

1. **Single Responsibility** - Does ONE thing well
2. **Has Documentation** - Explains what it does without reading code
3. **Has Test File** - Can be tested independently
4. **Clear Interface** - Input/output documented

### PHP Script Template

```php
<?php
/**
 * @file: UserService.php
 * @description: Handles user CRUD operations
 * @author: AI Assistant
 * @created: 2024-01-01
 *
 * @usage:
 *   $service = new UserService($pdo);
 *   $user = $service->create(['email' => 'test@example.com', 'name' => 'John']);
 *   $user = $service->getById(1);
 *   $service->update(1, ['name' => 'Jane']);
 *   $service->delete(1);
 *
 * @test: php tests/UserServiceTest.php
 */

class UserService {
    private PDO $db;

    public function __construct(PDO $db) {
        $this->db = $db;
    }

    /**
     * Create a new user
     * @param array $data ['email' => string, 'name' => string, 'password' => string]
     * @return array Created user with id
     * @throws Exception If email already exists
     */
    public function create(array $data): array {
        // Implementation...
    }
}
```

**Test file: `tests/UserServiceTest.php`**
```php
<?php
require_once __DIR__ . '/../src/UserService.php';

// Test create
$service = new UserService($pdo);
$user = $service->create(['email' => 'test@example.com', 'name' => 'Test']);
assert($user['id'] > 0, 'User should have ID');
assert($user['email'] === 'test@example.com', 'Email should match');

// Test getById
$found = $service->getById($user['id']);
assert($found['name'] === 'Test', 'Name should match');

echo "All tests passed!\n";
```

### Python Script Template

```python
#!/usr/bin/env python3
"""
@file: user_service.py
@description: Handles user CRUD operations
@author: AI Assistant
@created: 2024-01-01

@usage:
    from user_service import UserService

    service = UserService(db_connection)
    user = service.create(email='test@example.com', name='John')
    user = service.get_by_id(1)
    service.update(1, name='Jane')
    service.delete(1)

@test: pytest tests/test_user_service.py -v
"""

class UserService:
    """
    User CRUD operations.

    Attributes:
        db: Database connection

    Methods:
        create(email, name, password) -> dict: Create new user
        get_by_id(user_id) -> dict: Get user by ID
        update(user_id, **kwargs) -> dict: Update user
        delete(user_id) -> bool: Delete user
    """

    def __init__(self, db):
        self.db = db

    def create(self, email: str, name: str, password: str = None) -> dict:
        """
        Create a new user.

        Args:
            email: User's email (must be unique)
            name: User's display name
            password: Optional password (will be hashed)

        Returns:
            dict: Created user with 'id', 'email', 'name'

        Raises:
            ValueError: If email already exists
        """
        # Implementation...
        pass
```

**Test file: `tests/test_user_service.py`**
```python
import pytest
from user_service import UserService

class TestUserService:
    def test_create_user(self, db):
        service = UserService(db)
        user = service.create(email='test@example.com', name='Test')
        assert user['id'] > 0
        assert user['email'] == 'test@example.com'

    def test_get_by_id(self, db):
        service = UserService(db)
        user = service.create(email='test2@example.com', name='Test2')
        found = service.get_by_id(user['id'])
        assert found['name'] == 'Test2'

# Run: pytest tests/test_user_service.py -v
```

### Java Class Template

```java
/**
 * @file: UserService.java
 * @description: Handles user CRUD operations
 * @author: AI Assistant
 * @created: 2024-01-01
 *
 * @usage:
 *   UserService service = new UserService(userRepository);
 *   User user = service.create(new CreateUserDTO("test@example.com", "John"));
 *   User user = service.getById(1L);
 *   service.update(1L, new UpdateUserDTO("Jane"));
 *   service.delete(1L);
 *
 * @test: mvn test -Dtest=UserServiceTest
 */
@Service
public class UserService {

    private final UserRepository repository;

    /**
     * Create a new user.
     *
     * @param dto User data (email, name, password)
     * @return Created user entity
     * @throws ValidationException if email already exists
     */
    public User create(CreateUserDTO dto) {
        // Implementation...
    }
}
```

### MANDATORY for EVERY Script:

| Requirement | Description |
|-------------|-------------|
| **Header comment** | @file, @description, @usage, @test |
| **Method docs** | @param, @return, @throws for each method |
| **Test file** | `tests/` folder with matching test |
| **Single purpose** | One class = one responsibility |
| **No side effects** | Methods should be predictable |

### File Structure:

```
project/
├── src/
│   ├── UserService.php      # Has header docs
│   ├── ProductService.php   # Has header docs
│   └── OrderService.php     # Has header docs
├── tests/
│   ├── UserServiceTest.php      # Tests UserService
│   ├── ProductServiceTest.php   # Tests ProductService
│   └── OrderServiceTest.php     # Tests OrderService
└── README.md                    # Project overview
```

### Why "Closed Box"?

- **Read docs, not code** - Understand what it does from header
- **Run test, verify works** - Don't need to trace through code
- **Replace easily** - Clear interface means easy to swap implementations
- **Debug faster** - Test file isolates the problem

**RULE: Never create a script without its test file!**

---

## PART 7: TESTING

### 7.1 PHP TEST TEMPLATE

```php
<?php
// tests/UserTest.php
require_once __DIR__ . '/../src/User.php';

class TestRunner {
    private int $passed = 0;
    private int $failed = 0;
    private array $failures = [];

    public function test(string $name, callable $fn): void {
        try {
            $fn();
            $this->passed++;
            echo "✓ $name\n";
        } catch (Throwable $e) {
            $this->failed++;
            $this->failures[] = "$name: " . $e->getMessage();
            echo "✗ $name\n";
        }
    }

    public function assertEquals($expected, $actual, string $message = ''): void {
        if ($expected !== $actual) {
            throw new Exception($message ?: "Expected " . var_export($expected, true) . ", got " . var_export($actual, true));
        }
    }

    public function assertTrue($value, string $message = ''): void {
        if ($value !== true) {
            throw new Exception($message ?: "Expected true, got " . var_export($value, true));
        }
    }

    public function assertFalse($value, string $message = ''): void {
        if ($value !== false) {
            throw new Exception($message ?: "Expected false, got " . var_export($value, true));
        }
    }

    public function summary(): void {
        echo "\n" . str_repeat('=', 50) . "\n";
        echo "Passed: {$this->passed} | Failed: {$this->failed}\n";
        if ($this->failures) {
            echo "\nFailures:\n";
            foreach ($this->failures as $f) echo "  - $f\n";
        }
        exit($this->failed > 0 ? 1 : 0);
    }
}

// Tests
$t = new TestRunner();

$t->test('validateEmail accepts valid email', function() use ($t) {
    $v = new Validator();
    $result = $v->email('test@example.com');
    $t->assertEquals('test@example.com', $result);
    $t->assertFalse($v->hasErrors());
});

$t->test('validateEmail rejects invalid email', function() use ($t) {
    $v = new Validator();
    $result = $v->email('invalid');
    $t->assertEquals(null, $result);
    $t->assertTrue($v->hasErrors());
});

$t->test('validateEmail rejects empty', function() use ($t) {
    $v = new Validator();
    $result = $v->email('');
    $t->assertEquals(null, $result);
    $t->assertTrue($v->hasErrors());
});

$t->summary();
```

### 7.2 PYTHON TEST

```python
import pytest
from validator import Validator

class TestValidator:
    def test_valid_email(self):
        v = Validator()
        result = v.email('test@example.com')
        assert result == 'test@example.com'
        assert not v.has_errors()

    def test_invalid_email(self):
        v = Validator()
        result = v.email('invalid')
        assert result is None
        assert v.has_errors()

    def test_password_min_length(self):
        v = Validator()
        result = v.password('short')
        assert result is None
        assert 'password' in v.get_errors()

# Run: pytest -v tests/
```

### 7.3 UI TESTING

```bash
# Use the verification script
python /opt/codehero/scripts/verify_ui.py https://127.0.0.1:9867/myproject/

# Outputs:
# - screenshot_desktop.png (1920x1080)
# - screenshot_mobile.png (375x667)
# - Console errors
# - Failed requests
# - All links

# View screenshots
Read /tmp/screenshot_desktop.png
Read /tmp/screenshot_mobile.png
```

---

## PART 8: UI RULES

### 8.1 TAILWIND ESSENTIALS

```html
<!-- Grid MUST have columns -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">

<!-- Flex MUST have direction -->
<div class="flex flex-col md:flex-row gap-4">

<!-- Dark backgrounds need light text -->
<div class="bg-gray-800 text-white">

<!-- Always include responsive breakpoints -->
<div class="w-full md:w-1/2 lg:w-1/3">
```

### 8.2 SIZING REFERENCE

| Element | Size |
|---------|------|
| Header | 60-80px |
| Card padding | 16-24px |
| Gaps | 16-24px |
| Small icons | 24-32px |
| Large icons | 40-48px |
| H1 | 2-3rem |
| Body text | 1rem |

**Avoid:** padding > 32px, icons > 64px, gaps > 32px

### 8.3 ACCESSIBILITY

```html
<!-- Images need alt text -->
<img src="photo.jpg" alt="Description of image">

<!-- Forms need labels -->
<label for="email">Email</label>
<input id="email" type="email">

<!-- Buttons need context -->
<button aria-label="Close dialog">×</button>

<!-- Skip link for keyboard users -->
<a href="#main" class="sr-only focus:not-sr-only">Skip to content</a>
```

### 8.4 LINKS

**Always use relative paths** (projects are in subfolders):

```html
<!-- WRONG - Goes to server root -->
<a href="/about.php">

<!-- CORRECT - Relative to current page -->
<a href="about.php">
<a href="../index.php">
```

---

## PART 9: JAVA/SPRING BOOT

### 9.1 PROJECT STRUCTURE

```
src/main/java/com/example/
├── controller/          # REST endpoints
├── service/             # Business logic
├── repository/          # Data access
├── model/               # JPA entities
├── dto/                 # Request/Response objects
├── config/              # Configuration
├── exception/           # Custom exceptions
└── MyApplication.java
```

### 9.2 COMPLETE CRUD EXAMPLE

```java
// Entity
@Entity
@Table(name = "users")
public class User {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true, length = 254)
    private String email;

    @Column(name = "password_hash", nullable = false)
    private String passwordHash;

    @Column(nullable = false, length = 100)
    private String name;

    @Column(name = "created_at")
    private Instant createdAt = Instant.now();
}

// Repository
public interface UserRepository extends JpaRepository<User, Long> {
    Optional<User> findByEmail(String email);
    boolean existsByEmail(String email);
}

// Service
@Service
@Transactional
public class UserService {
    private final UserRepository repo;
    private final PasswordEncoder encoder;

    public User create(CreateUserDTO dto) {
        if (repo.existsByEmail(dto.getEmail())) {
            throw new ValidationException("Email already exists");
        }
        User user = new User();
        user.setEmail(dto.getEmail().toLowerCase().trim());
        user.setPasswordHash(encoder.encode(dto.getPassword()));
        user.setName(dto.getName().trim());
        return repo.save(user);
    }

    public User getById(Long id) {
        return repo.findById(id)
            .orElseThrow(() -> new NotFoundException("User not found"));
    }
}

// Controller
@RestController
@RequestMapping("/api/users")
public class UserController {
    private final UserService service;

    @PostMapping
    public ResponseEntity<User> create(@Valid @RequestBody CreateUserDTO dto) {
        User user = service.create(dto);
        return ResponseEntity.status(HttpStatus.CREATED).body(user);
    }

    @GetMapping("/{id}")
    public User getById(@PathVariable Long id) {
        return service.getById(id);
    }
}

// Exception Handler
@ControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(ValidationException.class)
    public ResponseEntity<Map<String, Object>> handleValidation(ValidationException e) {
        return ResponseEntity.badRequest().body(Map.of(
            "success", false,
            "error", Map.of("code", "VALIDATION_ERROR", "message", e.getMessage())
        ));
    }

    @ExceptionHandler(NotFoundException.class)
    public ResponseEntity<Map<String, Object>> handleNotFound(NotFoundException e) {
        return ResponseEntity.status(404).body(Map.of(
            "success", false,
            "error", Map.of("code", "NOT_FOUND", "message", e.getMessage())
        ));
    }
}
```

---

## PART 10: MOBILE DEVELOPMENT

### 10.1 ANDROID (KOTLIN)

```kotlin
// Security - Encrypted storage
val masterKey = MasterKey.Builder(context)
    .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
    .build()

val securePrefs = EncryptedSharedPreferences.create(
    context, "secure_prefs", masterKey,
    EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
    EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
)

// Save/retrieve tokens
securePrefs.edit().putString("auth_token", token).apply()
val token = securePrefs.getString("auth_token", null)

// ViewModel pattern
class UserViewModel(private val repo: UserRepository) : ViewModel() {
    private val _user = MutableLiveData<Result<User>>()
    val user: LiveData<Result<User>> = _user

    fun load(id: String) = viewModelScope.launch {
        _user.value = repo.getUser(id)
    }
}

// Fragment observation
viewModel.user.observe(viewLifecycleOwner) { result ->
    when (result) {
        is Result.Success -> showUser(result.data)
        is Result.Error -> showError(result.message)
    }
}
```

### 10.2 REACT NATIVE

```typescript
// Secure storage
import * as SecureStore from 'expo-secure-store';

export const storage = {
    async setToken(token: string) {
        await SecureStore.setItemAsync('auth_token', token);
    },
    async getToken(): Promise<string | null> {
        return SecureStore.getItemAsync('auth_token');
    },
    async clearToken() {
        await SecureStore.deleteItemAsync('auth_token');
    }
};

// API client with auth
const api = {
    async request(endpoint: string, options: RequestInit = {}) {
        const token = await storage.getToken();
        const response = await fetch(`${API_URL}${endpoint}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...(token && { Authorization: `Bearer ${token}` }),
                ...options.headers,
            },
        });
        if (!response.ok) throw new Error(`API Error: ${response.status}`);
        return response.json();
    },
    getUser: (id: string) => api.request(`/users/${id}`),
    updateUser: (id: string, data: object) =>
        api.request(`/users/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
};
```

### 10.3 CAPACITOR

```typescript
// capacitor.config.ts
const config: CapacitorConfig = {
    appId: 'com.example.app',
    appName: 'My App',
    webDir: 'dist',
    server: { androidScheme: 'https' }
};

// Commands
// npm run build && npx cap sync
// npx cap run android -l  (live reload)
// npx cap open android    (open in Android Studio)

// Plugins
import { Camera, CameraResultType } from '@capacitor/camera';
import { Preferences } from '@capacitor/preferences';

const photo = await Camera.getPhoto({ resultType: CameraResultType.Uri });
await Preferences.set({ key: 'user', value: JSON.stringify(user) });
const { value } = await Preferences.get({ key: 'user' });
```

---

## PART 11: SERVER & PROJECT SETUP

### 11.1 SERVER INFO

| Tool | Version |
|------|---------|
| Ubuntu | 24.04 |
| PHP | 8.3 |
| Node.js | 22.x |
| MySQL | 8.0 |
| Python | 3.12 |

**Ports:** Admin=9453, Projects=9867, MySQL=3306

### 11.2 PROJECT STRUCTURES

```
PHP Web Project:
/var/www/projects/mysite/
├── index.php
├── assets/{css,js,images,lib}/
├── includes/{db.php,auth.php,functions.php}
├── api/
├── templates/
└── tests/

Python API:
/opt/apps/myapi/
├── app.py
├── requirements.txt
├── .env
├── src/{routes,services,models}/
└── tests/

Vue/React App:
/opt/apps/myapp/
├── src/{components,views,stores,services}/
├── package.json
└── vite.config.js
```

---

## PART 12: DESIGN STANDARDS

### 12.1 SPACING SYSTEM (4px Grid)

Use multiples of 4px for ALL spacing:

| Token | Value | Use |
|-------|-------|-----|
| xs | 4px | Tight gaps, icon padding |
| sm | 8px | Related elements |
| md | 16px | Section padding, card gaps |
| lg | 24px | Section separators |
| xl | 32px | Major sections |
| 2xl | 48px | Page sections |

**Tailwind classes:** `gap-1` (4px), `gap-2` (8px), `gap-4` (16px), `gap-6` (24px), `gap-8` (32px)

**Rule:** Internal spacing ≤ External spacing
- Card content padding (16px) < Gap between cards (24px)
- Button text padding (8px) < Button margins (16px)

### 12.2 COLOR SYSTEM (60-30-10 Rule)

| Role | % | Tailwind | Use |
|------|---|----------|-----|
| **Primary** | 60% | `gray-50`, `white` | Backgrounds |
| **Secondary** | 30% | `gray-100-200`, `slate-800` | Cards, headers |
| **Accent** | 10% | `blue-600`, `indigo-600` | CTAs, links |

**Semantic Colors:**

| Purpose | Light Mode | Dark Mode |
|---------|------------|-----------|
| Background | `bg-gray-50` | `bg-gray-900` |
| Surface/Card | `bg-white` | `bg-gray-800` |
| Text Primary | `text-gray-900` | `text-white` |
| Text Secondary | `text-gray-600` | `text-gray-400` |
| Border | `border-gray-200` | `border-gray-700` |
| Accent/CTA | `bg-blue-600 text-white` | `bg-blue-500 text-white` |
| Success | `text-green-600` | `text-green-400` |
| Error | `text-red-600` | `text-red-400` |
| Warning | `text-amber-600` | `text-amber-400` |

**Avoid:**
- Pure black (`#000`) → Use `gray-900` or `slate-900`
- Pure white (`#fff`) for large areas → Use `gray-50`
- More than 3 accent colors

### 12.3 TYPOGRAPHY

| Element | Class | Size | Line Height |
|---------|-------|------|-------------|
| H1 | `text-4xl font-bold` | 36px | tight |
| H2 | `text-3xl font-semibold` | 30px | tight |
| H3 | `text-2xl font-semibold` | 24px | snug |
| H4 | `text-xl font-medium` | 20px | snug |
| Body | `text-base` | 16px | relaxed |
| Small | `text-sm` | 14px | normal |
| Caption | `text-xs` | 12px | normal |

**Rules:**
- Body text: `leading-relaxed` (1.625) for readability
- Headings: `leading-tight` (1.25) for compactness
- Maximum line width: `max-w-prose` (65 characters)

### 12.4 BORDER RADIUS

| Token | Class | Value | Use |
|-------|-------|-------|-----|
| None | `rounded-none` | 0 | Tables, full-width |
| Small | `rounded` | 4px | Inputs, badges |
| Medium | `rounded-md` | 6px | Buttons |
| Large | `rounded-lg` | 8px | Cards |
| XL | `rounded-xl` | 12px | Modals, large cards |
| Full | `rounded-full` | 9999px | Avatars, pills |

**Nested Rule:** Outer radius = Inner radius + Padding
- Card with 16px padding and inner 8px radius → outer 24px radius

### 12.5 SHADOWS (Elevation)

| Level | Class | Use |
|-------|-------|-----|
| 0 | `shadow-none` | Flat elements |
| 1 | `shadow-sm` | Subtle lift (cards) |
| 2 | `shadow` | Standard elevation |
| 3 | `shadow-md` | Dropdowns, popovers |
| 4 | `shadow-lg` | Modals, dialogs |
| 5 | `shadow-xl` | Important overlays |

**Dark Mode:** Use lighter surface colors instead of shadows
- `dark:bg-gray-700` instead of `dark:shadow-lg`

### 12.6 COMPONENT PATTERNS

#### Buttons

```html
<!-- Primary -->
<button class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-md transition-colors">
  Primary Action
</button>

<!-- Secondary -->
<button class="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium rounded-md transition-colors">
  Secondary
</button>

<!-- Ghost -->
<button class="px-4 py-2 hover:bg-gray-100 text-gray-600 font-medium rounded-md transition-colors">
  Ghost
</button>

<!-- Disabled -->
<button class="px-4 py-2 bg-gray-200 text-gray-400 font-medium rounded-md cursor-not-allowed" disabled>
  Disabled
</button>
```

**Sizes:**
- Small: `px-3 py-1.5 text-sm`
- Medium: `px-4 py-2 text-base` (default)
- Large: `px-6 py-3 text-lg`

#### Cards

```html
<div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
  <h3 class="text-lg font-semibold text-gray-900 mb-2">Card Title</h3>
  <p class="text-gray-600 mb-4">Card content goes here.</p>
  <button class="text-blue-600 hover:text-blue-700 font-medium">Action →</button>
</div>
```

#### Form Inputs

```html
<div class="space-y-1">
  <label for="email" class="block text-sm font-medium text-gray-700">Email</label>
  <input
    type="email"
    id="email"
    class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm
           focus:ring-2 focus:ring-blue-500 focus:border-blue-500
           placeholder-gray-400"
    placeholder="you@example.com"
  >
  <p class="text-sm text-gray-500">We'll never share your email.</p>
</div>

<!-- Error state -->
<input class="... border-red-500 focus:ring-red-500 focus:border-red-500">
<p class="text-sm text-red-600">Please enter a valid email.</p>
```

**Input Sizes:**
- Height: 40-48px (py-2 to py-3)
- Consistent across all inputs, selects, buttons in same row

### 12.7 RESPONSIVE PATTERNS

```html
<!-- Mobile-first grid -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

<!-- Flexible container -->
<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

<!-- Responsive text -->
<h1 class="text-2xl md:text-3xl lg:text-4xl font-bold">
```

### 12.8 DARK MODE

Always support dark mode with `dark:` variants:

```html
<div class="bg-white dark:bg-gray-800 text-gray-900 dark:text-white">
  <p class="text-gray-600 dark:text-gray-400">Secondary text</p>
  <div class="border border-gray-200 dark:border-gray-700">...</div>
</div>
```

---

## FINAL CHECKLIST

### Before Every Commit

**Security:**
- [ ] All SQL uses prepared statements
- [ ] All output is escaped (htmlspecialchars/DOMPurify)
- [ ] Passwords hashed with bcrypt
- [ ] Credentials in .env (not in code)
- [ ] CSRF tokens on all forms
- [ ] Session cookies are secure (httpOnly, secure, sameSite)
- [ ] Auth check on every protected page/API
- [ ] Rate limiting on login/sensitive endpoints
- [ ] File uploads validated and sanitized

**Data:**
- [ ] Input validated before processing
- [ ] Transactions for related DB operations
- [ ] Null checks before accessing properties
- [ ] Pagination on list endpoints (max 100)
- [ ] Dates stored in UTC

**Code:**
- [ ] Error handling with proper logging
- [ ] Consistent API response format
- [ ] Tests written and passing
- [ ] No TODO/FIXME left in code

**UI:**
- [ ] Screenshots reviewed (desktop + mobile)
- [ ] Zero console errors
- [ ] Zero server log errors
- [ ] All links work
- [ ] Grids have explicit columns
- [ ] Responsive breakpoints present
- [ ] Alt text on images

**Design:**
- [ ] 4px/8px grid for all spacing
- [ ] 60-30-10 color distribution (primary/secondary/accent)
- [ ] No pure black (#000) or pure white (#fff) on large areas
- [ ] Consistent border radius (see 12.4)
- [ ] Dark mode variants on all color classes
- [ ] Typography hierarchy maintained (H1→H4, body, small)
- [ ] Buttons follow standard patterns (primary/secondary/ghost)

---

> **Philosophy:** Write code as if the person maintaining it is a violent psychopath who knows where you live.
