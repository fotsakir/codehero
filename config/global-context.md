# Global Project Context v4.0

> **MISSION:** Build production-ready code that works correctly the first time.

---

## MANDATORY WORKFLOW

### Step 1: Analyze Request
- Understand what the user is asking for
- Assess complexity

### Step 2: Break Into Parts
- Split the request into small, manageable pieces
- Each part must be testable

### Step 3: Implementation Plan
- Write which parts you will implement and in what order
- Document in the project's map.md

### Step 4: Implement Part by Part
- Implement one part at a time
- DO NOT proceed to the next without verification

### Step 5: Verify Each Part
- MANDATORY: Run the checks from the VERIFICATION PROTOCOL
- If it fails, fix it BEFORE proceeding

### Step 6: Full Test
- After all parts are completed
- End-to-end testing of all functionality

### Step 7: Final Report
- What was implemented
- What technologies were used
- Any notes for the user

---

## VERIFICATION PROTOCOL (MANDATORY!)

### 1. Syntax Check
Check syntax by language:
```bash
# PHP
php -l filename.php

# Python
python3 -m py_compile filename.py

# JavaScript
node --check filename.js

# HTML (via validator)
tidy -e -q filename.html 2>&1 || true
```

### 2. Log Check
Check relevant log files:
```bash
# PHP/Nginx errors
sudo tail -30 /var/log/nginx/codehero-projects-error.log

# PHP-FPM errors
sudo tail -30 /var/log/php8.3-fpm.log

# System logs
sudo journalctl -u nginx --since "5 minutes ago" --no-pager
```

### 3. Visual Verification (MANDATORY for UI!)

Choose the appropriate method based on project type:

#### Web Projects (PHP, HTML, Node.js, Python web, .NET Blazor)
**Use Playwright:**
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()

    # Desktop test
    page.set_viewport_size({"width": 1920, "height": 1080})
    page.goto('https://127.0.0.1:9867/project/')
    page.wait_for_load_state("networkidle")

    # Console errors check
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

    # Full page screenshot
    page.screenshot(path='/tmp/desktop.png', full_page=True)

    # Mobile test
    page.set_viewport_size({"width": 375, "height": 812})
    page.screenshot(path='/tmp/mobile.png', full_page=True)

    browser.close()
```

#### Android (Java/Kotlin, React Native, Capacitor, Flutter)
**Use ADB with emulator:**
```bash
# Start emulator (if not running)
emulator -avd Pixel_6_API_33 -no-audio -no-window &

# Wait for device
adb wait-for-device

# Install APK
adb install -r app/build/outputs/apk/debug/app-debug.apk

# Launch app
adb shell am start -n com.package.name/.MainActivity

# Wait for app to load
sleep 3

# Take screenshot
adb exec-out screencap -p > /tmp/android_screenshot.png

# Get logs
adb logcat -d -s "AppTag:*" > /tmp/android_logs.txt
```

#### iOS (Swift, React Native, Capacitor, Flutter)
**Use Xcode Simulator:**
```bash
# List available simulators
xcrun simctl list devices

# Boot simulator
xcrun simctl boot "iPhone 15 Pro"

# Install app
xcrun simctl install booted /path/to/MyApp.app

# Launch app
xcrun simctl launch booted com.bundle.identifier

# Take screenshot
xcrun simctl io booted screenshot /tmp/ios_screenshot.png

# Get logs
xcrun simctl spawn booted log show --predicate 'subsystem == "com.bundle.identifier"' --last 5m
```

#### Desktop Apps (.NET WinForms/WPF, Java Swing/JavaFX, Electron)
**Use platform screenshot tools:**
```bash
# Linux (for Electron or Java desktop)
import -window root /tmp/desktop_app.png

# Or with specific window
xdotool search --name "App Title" | xargs -I {} import -window {} /tmp/app.png

# For headless Java apps testing
java -Djava.awt.headless=false -jar app.jar &
sleep 3
import -window root /tmp/java_app.png
```

#### React Native / Expo
**Use Expo or platform-specific:**
```bash
# With Expo (web preview)
npx expo start --web &
sleep 5
# Then use Playwright for web testing

# For native, use ADB (Android) or simctl (iOS) as above
```

#### Flutter
**Use Flutter integration test:**
```bash
# Run with screenshots
flutter drive --driver=test_driver/integration_test.dart \
  --target=integration_test/app_test.dart \
  --screenshot=/tmp/flutter_screenshots/

# Or use platform tools (ADB/simctl) after building
flutter build apk --debug
adb install build/app/outputs/flutter-apk/app-debug.apk
```

### UI Checklist (All Platforms)
- [ ] No console/logcat errors
- [ ] All interactive elements work (buttons, inputs, navigation)
- [ ] Colors: Consistency, good contrast
- [ ] Alignment: Proper alignment
- [ ] Sizing: Appropriate element/font sizes
- [ ] Text: Readable, no truncation
- [ ] Loading states: Shown correctly
- [ ] **Web**: Desktop + Mobile responsive
- [ ] **Mobile apps**: Portrait + Landscape orientation

### Tags/Badges σε Cards (ΠΡΟΣΟΧΗ!)
- Position tags με `absolute` ΜΟΝΟ αν το parent έχει `relative`
- Αφήνε padding στο content για να μην επικαλύπτεται: `pt-8` αν το tag είναι πάνω
- Χρησιμοποίησε `z-index` σωστά: tag `z-10`, content `z-0`
- ΠΟΤΕ μην βάζεις tag πάνω σε κείμενο - χρησιμοποίησε corners (top-right, top-left)

**Παράδειγμα:**
```html
<div class="relative bg-white rounded-lg p-4 pt-10">
  <span class="absolute top-2 right-2 bg-blue-500 text-white text-xs px-2 py-1 rounded z-10">Tag</span>
  <h3 class="z-0">Τίτλος</h3>
  <p>Περιεχόμενο που δεν επικαλύπτεται</p>
</div>
```

### Εικόνες & Placeholders (MANDATORY!)
- ΠΟΤΕ μην αφήνεις κενό χώρο για εικόνες
- Χρησιμοποίησε placeholder service: `https://placehold.co/400x300/EEE/333?text=Κατηγορία`
- Ή δημιούργησε SVG placeholder με σχετικό icon
- Για κατηγορίες χρησιμοποίησε σχετικά icons (FontAwesome, Heroicons)

**Παραδείγματα placeholders:**
| Κατηγορία | Placeholder |
|-----------|-------------|
| Οχήματα | 🚗 icon ή placehold.co με "Οχήματα" |
| Ακίνητα | 🏠 icon |
| Ηλεκτρονικά | 📱 icon |
| Γενικό | Γκρι background με όνομα κατηγορίας |

**Κώδικας:**
```html
<!-- Με εικόνα ή fallback -->
<img src="photo.jpg"
     onerror="this.src='https://placehold.co/400x300/f3f4f6/9ca3af?text=Χωρίς+Εικόνα'"
     alt="Περιγραφή">

<!-- SVG Placeholder -->
<div class="bg-gray-100 flex items-center justify-center h-48">
  <svg class="w-16 h-16 text-gray-400">...</svg>
</div>
```

---

## MANDATORY UI TESTING RULES

### 1. Color Contrast Check (CRITICAL!)
**NEVER create invisible elements!** Always verify:
- Text is readable against background
- Buttons/links are visible WITHOUT hover
- Icons have sufficient contrast

```python
# Check element visibility BEFORE and AFTER hover
element = page.locator('[data-testid="menu-toggle"]')
# Screenshot in normal state
page.screenshot(path='/tmp/before_hover.png')
# Screenshot on hover
element.hover()
page.screenshot(path='/tmp/after_hover.png')
# BOTH must show the element clearly!
```

**BAD (invisible until hover):**
```css
.menu-btn { color: #333; background: #333; } /* INVISIBLE! */
.menu-btn:hover { color: #fff; }
```

**GOOD (always visible):**
```css
.menu-btn { color: #fff; background: #333; } /* Always visible */
.menu-btn:hover { background: #555; }
```

### 2. Interactive Elements Testing (MANDATORY!)
**Open and verify ALL interactive elements:**

```python
# Test ALL dropdowns/selects
for select in page.locator('select').all():
    select.click()
    page.screenshot(path=f'/tmp/select_{select.get_attribute("name")}.png')
    # Verify options are visible and readable

# Test ALL expandable menus
for menu in page.locator('[data-testid*="menu"], .dropdown, .accordion').all():
    menu.click()
    page.wait_for_timeout(300)
    page.screenshot(path=f'/tmp/menu_open.png')
    # Verify expanded content is visible
```

### 3. Login & Authenticated Views (MANDATORY!)
**If the project has login, you MUST test authenticated state:**

```python
# Login first
page.goto('https://127.0.0.1:9867/project/login.php')
page.fill('[data-testid="username"]', 'test_user')
page.fill('[data-testid="password"]', 'test_pass')
page.click('[data-testid="login-btn"]')
page.wait_for_url('**/dashboard**')

# Now test authenticated pages
page.screenshot(path='/tmp/dashboard.png')
page.goto('https://127.0.0.1:9867/project/profile.php')
page.screenshot(path='/tmp/profile.png')
```

**Create test credentials in your setup:**
```sql
-- Add test user for Playwright testing
INSERT INTO users (username, password, email)
VALUES ('test_user', '$2y$10$...hashed...', 'test@test.com');
```

### 4. Test IDs in Code (MANDATORY!)
**ALWAYS add `data-testid` attributes for testable elements:**

```html
<!-- MANDATORY for all interactive elements -->
<button data-testid="submit-btn">Submit</button>
<input data-testid="email-input" type="email">
<select data-testid="category-select">...</select>
<div data-testid="user-menu" class="dropdown">...</div>
<a data-testid="nav-home" href="/">Home</a>

<!-- For lists/grids -->
<div data-testid="product-list">
    <div data-testid="product-item-1">...</div>
    <div data-testid="product-item-2">...</div>
</div>

<!-- For modals/dialogs -->
<div data-testid="confirm-modal" class="modal">
    <button data-testid="confirm-yes">Yes</button>
    <button data-testid="confirm-no">No</button>
</div>
```

**Naming convention:**
| Element | data-testid format |
|---------|-------------------|
| Buttons | `{action}-btn` (submit-btn, delete-btn) |
| Inputs | `{field}-input` (email-input, search-input) |
| Links | `nav-{page}` (nav-home, nav-about) |
| Lists | `{item}-list`, `{item}-item-{id}` |
| Modals | `{name}-modal` |
| Menus | `{name}-menu` |

### 5. Full Playwright Test Template
```python
from playwright.sync_api import sync_playwright

def test_project():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

        # 1. Test public pages
        page.goto('https://127.0.0.1:9867/project/')
        page.screenshot(path='/tmp/01_home.png', full_page=True)

        # 2. Test all interactive elements
        for btn in page.locator('[data-testid*="-btn"]').all():
            testid = btn.get_attribute('data-testid')
            # Verify button is visible (not same color as background)
            assert btn.is_visible(), f"Button {testid} not visible!"

        # 3. Open and test dropdowns
        for dropdown in page.locator('select, [data-testid*="-select"]').all():
            dropdown.click()
            page.screenshot(path='/tmp/dropdown_open.png')

        # 4. Login if needed
        if page.locator('[data-testid="login-btn"]').count() > 0:
            page.fill('[data-testid="username-input"]', 'test_user')
            page.fill('[data-testid="password-input"]', 'test_pass')
            page.click('[data-testid="login-btn"]')
            page.wait_for_load_state('networkidle')
            page.screenshot(path='/tmp/02_logged_in.png', full_page=True)

        # 5. Mobile test
        page.set_viewport_size({"width": 375, "height": 812})
        page.screenshot(path='/tmp/03_mobile.png', full_page=True)

        # 6. Report errors
        if errors:
            print(f"Console errors: {errors}")

        browser.close()

test_project()
```

---

## CODE QUALITY RULES (MANDATORY!)

### ALWAYS DO:
| Rule | Why |
|------|-----|
| Clean, readable code | Junior dev must understand |
| Comments that explain WHY | Not just what it does |
| Descriptive variable names | `$userEmail` not `$ue` |
| Small functions, one purpose | Easier testing |
| **RELATIVE PATHS** | Avoid broken links |

### NEVER DO:
| Bad | Why |
|-----|-----|
| Minified code | We want readable source |
| Obfuscated code | We want readable source |
| CDN for libraries | Download locally! |
| Absolute paths | Break in different environments |

---

## LIBRARIES RULE

**ALWAYS download locally:**
```bash
mkdir -p libs
curl -o libs/vue.global.min.js https://unpkg.com/vue@3/dist/vue.global.prod.js
curl -o libs/tailwind.min.css https://cdn.tailwindcss.com/...
```

**EXCEPTIONS** (external APIs that can't be local):
- Google Maps API
- Stripe.js
- PayPal SDK
- reCAPTCHA

---

## PROJECT DOCUMENTATION

### Mandatory files:
1. **technologies.md** - Technologies, versions, libraries
2. **map.md** - Project structure, database schema, page flow

### While working, keep track of:
- **Index** of what you did (for navigation)
- **Notes** of commands you used
- **Log** of technologies

---

## SERVER ENVIRONMENT

- **OS**: Ubuntu 24.04 LTS
- **Web Server**: Nginx
- **PHP**: 8.3 | **Node.js**: v22.x | **Python**: 3.12 | **MySQL**: 8.0

## PORTS

| Service | Port | Protocol |
|---------|------|----------|
| Admin Panel | 9453 | HTTPS |
| Web Projects | 9867 | HTTPS |
| MySQL | 3306 | TCP (localhost only) |

## FILE LOCATIONS

- **PHP/Web Projects**: `/var/www/projects/{project}/`
- **App Projects**: `/opt/apps/{project}/`

---

## QUICK SECURITY REFERENCE

### ALWAYS DO:
| Category | Rule |
|----------|------|
| **SQL** | Prepared statements: `$stmt->execute([$id])` |
| **XSS** | Escape output: `htmlspecialchars($x, ENT_QUOTES, 'UTF-8')` |
| **Passwords** | Hash: `password_hash($p, PASSWORD_BCRYPT)` |
| **Forms** | CSRF token on every POST |
| **Sessions** | `session_regenerate_id(true)` after login |

### NEVER DO:
| Bad | Good |
|-----|------|
| `"WHERE id=$id"` | `"WHERE id=?"` + bind |
| `echo $userInput` | `echo htmlspecialchars($userInput)` |
| Passwords in code | Use `.env` files |

---

## DATABASE DESIGN (MANDATORY!)

### Σωστοί Τύποι Πεδίων (ΚΡΙΣΙΜΟ!)

| Δεδομένο | Σωστός Τύπος | ❌ Λάθος | Γιατί |
|----------|--------------|----------|-------|
| ID/Primary Key | `INT UNSIGNED` ή `BIGINT UNSIGNED` | `INT` (signed) | Δεν χρειαζόμαστε αρνητικά IDs |
| Foreign Key | Ίδιος τύπος με το PK | Διαφορετικός | Πρέπει να ταιριάζουν ακριβώς |
| Τιμή/Χρήματα | `DECIMAL(10,2)` | `FLOAT`, `DOUBLE` | Float έχει precision errors |
| Email | `VARCHAR(255)` | `TEXT` | Email max 254 chars by RFC |
| Username | `VARCHAR(50)` | `VARCHAR(255)` | Περιττό μέγεθος |
| Password hash | `VARCHAR(255)` | `TEXT`, `CHAR` | bcrypt = 60 chars, future-proof |
| Short text | `VARCHAR(n)` | `TEXT` | TEXT δεν έχει index limit |
| Long text | `TEXT` ή `MEDIUMTEXT` | `VARCHAR(10000)` | VARCHAR max 65535 bytes |
| Boolean | `TINYINT(1)` ή `BOOLEAN` | `INT`, `ENUM('0','1')` | Σπατάλη χώρου |
| Status/Type | `ENUM(...)` | `VARCHAR`, `INT` | Validation + readability |
| Date μόνο | `DATE` | `DATETIME`, `VARCHAR` | Σωστός τύπος για dates |
| Date + Time | `DATETIME` | `TIMESTAMP` (για events) | TIMESTAMP για auto-update |
| Created/Updated | `TIMESTAMP` | `DATETIME` | Auto-update support |
| IP Address | `VARCHAR(45)` | `VARCHAR(15)` | IPv6 = 45 chars |
| Phone | `VARCHAR(20)` | `INT` | Phones έχουν + και spaces |
| UUID | `CHAR(36)` ή `BINARY(16)` | `VARCHAR` | Fixed length |
| JSON data | `JSON` | `TEXT` | Validation + indexing |
| Percentage | `DECIMAL(5,2)` | `INT`, `FLOAT` | 0.00 - 100.00 |

### Δομή Πίνακα - Best Practices

**Standard Columns (ΠΑΝΤΑ περιλαμβάνουμε):**
```sql
CREATE TABLE table_name (
    -- Primary Key
    id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,

    -- Business columns εδώ...

    -- Standard timestamps (ΠΑΝΤΑ!)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Optional: Soft delete
    deleted_at TIMESTAMP NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Naming Conventions:**
| Τι | Convention | Παράδειγμα |
|----|------------|------------|
| Table names | Πληθυντικός, snake_case | `users`, `order_items` |
| Column names | Ενικός, snake_case | `user_id`, `created_at` |
| Primary key | `id` | `id` |
| Foreign key | `{table_singular}_id` | `user_id`, `product_id` |
| Boolean | `is_` ή `has_` prefix | `is_active`, `has_verified` |
| Timestamps | `_at` suffix | `created_at`, `expires_at` |
| Indexes | `idx_{columns}` | `idx_user_id`, `idx_status_created` |

**Επεκτασιμότητα - Σκέψου το Μέλλον:**
```sql
-- ❌ ΛΑΘΟΣ: Hardcoded columns
CREATE TABLE users (
    phone1 VARCHAR(20),
    phone2 VARCHAR(20),  -- Τι γίνεται αν θέλει 3 τηλέφωνα;
    phone3 VARCHAR(20)
);

-- ✅ ΣΩΣΤΟ: Separate table για πολλαπλές τιμές
CREATE TABLE users (
    id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT
);

CREATE TABLE user_phones (
    id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    user_id INT UNSIGNED NOT NULL,
    phone VARCHAR(20) NOT NULL,
    type ENUM('mobile','home','work') DEFAULT 'mobile',
    is_primary TINYINT(1) DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### Indexes - ΠΑΝΤΑ προσθέτουμε:
| Column Type | Index Type | Παράδειγμα |
|-------------|------------|------------|
| Primary Key | PRIMARY | `id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT` |
| Foreign Key | INDEX | `INDEX idx_user_id (user_id)` |
| WHERE columns | INDEX | `INDEX idx_status (status)` |
| ORDER BY columns | INDEX | `INDEX idx_created (created_at)` |
| Unique fields | UNIQUE | `UNIQUE idx_email (email)` |
| Composite WHERE | COMPOSITE | `INDEX idx_user_status (user_id, status)` |

### Foreign Keys - Σωστά Actions (ΚΡΙΣΙΜΟ!)

**ON DELETE + ON UPDATE Actions:**
| Action | ON DELETE | ON UPDATE |
|--------|-----------|-----------|
| `CASCADE` | Διαγραφή parent → διαγραφή children | Update parent ID → update children |
| `RESTRICT` | Απαγόρευση διαγραφής αν υπάρχουν children | Απαγόρευση update αν υπάρχουν children |
| `SET NULL` | Διαγραφή parent → NULL στο child | Update parent ID → NULL στο child |
| `NO ACTION` | Ίδιο με RESTRICT (SQL standard) | Ίδιο με RESTRICT |

**Πότε χρησιμοποιούμε τι:**
| Σχέση | ON DELETE | ON UPDATE | Παράδειγμα |
|-------|-----------|-----------|------------|
| Parent-Child (ownership) | `CASCADE` | `CASCADE` | user → user_settings |
| Parent-Child (data) | `CASCADE` | `CASCADE` | order → order_items |
| Reference (required) | `RESTRICT` | `CASCADE` | order → product |
| Reference (optional) | `SET NULL` | `CASCADE` | post → category (nullable) |
| Audit/Log | `RESTRICT` | `CASCADE` | payment → order |
| Self-reference | `SET NULL` ή `CASCADE` | `CASCADE` | employee → manager |

**Παράδειγμα Σωστής Δομής:**
```sql
CREATE TABLE orders (
    id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    user_id INT UNSIGNED NOT NULL,
    product_id INT UNSIGNED NOT NULL,
    status ENUM('pending','processing','completed','cancelled') DEFAULT 'pending',
    total_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    notes TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Foreign Keys με ΣΩΣΤΑ actions
    FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE ON UPDATE CASCADE,      -- Διαγραφή user = διαγραφή orders
    FOREIGN KEY (product_id) REFERENCES products(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,     -- Δεν μπορείς να διαγράψεις product με orders

    -- Indexes
    INDEX idx_user_id (user_id),
    INDEX idx_product_id (product_id),
    INDEX idx_status (status),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### Query Optimization - ΠΑΝΤΑ ελέγχουμε:
```sql
-- Πριν γράψεις query, έλεγξε με EXPLAIN:
EXPLAIN SELECT * FROM orders WHERE user_id = 1 AND status = 'pending';

-- Αν δεις "type: ALL" → ΧΡΕΙΑΖΕΤΑΙ INDEX!
-- Στόχος: "type: ref" ή "type: range"
```

### Database Checklist πριν τελειώσεις:
- [ ] Τύποι πεδίων είναι σωστοί (DECIMAL για χρήματα, κλπ)
- [ ] Primary keys είναι UNSIGNED
- [ ] Foreign keys έχουν ίδιο τύπο με το PK που αναφέρονται
- [ ] Κάθε foreign key έχει INDEX
- [ ] Foreign keys έχουν σωστό ON DELETE ΚΑΙ ON UPDATE
- [ ] Υπάρχουν created_at και updated_at columns
- [ ] WHERE columns έχουν INDEX
- [ ] ORDER BY columns έχουν INDEX
- [ ] Πίνακες έχουν utf8mb4 charset
- [ ] EXPLAIN δείχνει σωστή χρήση indexes

---

## NO BUILD WORKFLOW

**NEVER use build tools** (Vite, Webpack, npm run build)

Write Vue/React in plain .js files:
```javascript
const MyComponent = {
  template: `<div>{{ message }}</div>`,
  data() { return { message: 'Hello' } }
}
```

---

## WORKSPACE PATHS (CRITICAL!)

### Πού Δουλεύεις
Όταν εκτελείς ticket, το σύστημα σου δίνει τα paths στο context:
- **Web path**: Για web εφαρμογές (PHP, HTML, frontend)
- **App path**: Για backend/app (Node.js API, Python, CLI, mobile)

**ΚΡΙΣΙΜΟ:** Δούλεψε ΜΟΝΟ μέσα στα paths που σου δόθηκαν!

### Κανόνες Τοποθέτησης Αρχείων

| Τύπος Αρχείου | Που Πάει | Path |
|---------------|----------|------|
| HTML, CSS, JS, PHP | Web folder | `{web_path}/` |
| Images, fonts, assets | Web folder | `{web_path}/assets/` |
| Libraries (local) | Web folder | `{web_path}/libs/` |
| Backend API (Node/Python) | App folder | `{app_path}/` |
| Config files | Root του project | `{web_path}/` ή `{app_path}/` |
| SQL/migrations | Project folder | `{web_path}/database/` ή `{app_path}/database/` |

### Project Structure Examples

**Web Project (PHP/HTML):**
```
{web_path}/
├── index.php          # Entry point
├── css/               # Stylesheets
├── js/                # JavaScript
├── libs/              # Downloaded libraries (Tailwind, Vue, etc.)
├── assets/            # Images, fonts
├── includes/          # PHP includes
├── database/          # SQL files
└── config.php         # Configuration
```

**App Project (Node.js API):**
```
{app_path}/
├── index.js           # Entry point
├── src/               # Source code
├── routes/            # API routes
├── models/            # Data models
├── config/            # Configuration
├── database/          # Migrations, schema
└── package.json       # Dependencies
```

**Hybrid Project (Frontend + Backend):**
```
{web_path}/            # Frontend (Vue/React)
├── index.html
├── css/
├── js/
└── libs/

{app_path}/            # Backend API
├── index.js
├── routes/
└── models/
```

### ΑΠΑΓΟΡΕΥΜΕΝΕΣ Τοποθεσίες (NEVER!)

```
❌ FORBIDDEN - ΠΟΤΕ μην γράφεις εδώ:
/opt/codehero/         # System files
/etc/nginx/            # Server config
/etc/systemd/          # Service files
/var/log/              # Logs
/tmp/                  # Temporary (εκτός για screenshots)
/home/claude/          # Home directory
/root/                 # Root home

✅ ALLOWED - Μόνο εδώ:
{web_path}/...         # Το web path του project
{app_path}/...         # Το app path του project
```

### Checklist Πριν Δημιουργήσεις Αρχείο

- [ ] Είμαι μέσα στο `{web_path}` ή `{app_path}` του project;
- [ ] Ο τύπος αρχείου ταιριάζει με το path (web files → web_path);
- [ ] Χρησιμοποιώ relative paths μέσα στο project;
- [ ] Libraries πάνε στο `libs/` folder, όχι στο root;
