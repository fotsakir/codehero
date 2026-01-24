# Global Project Context v3.0

> **MISSION:** Build production-ready code that works correctly the first time.

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
- **PHP Binary**: `/usr/bin/php`
- **Node Binary**: `/usr/bin/node`

## IMPORTANT RULES

1. **Check before installing**: Most tools are already installed. Verify with `which [tool]` first
2. **Do NOT run `apt-get install`** for packages that are already installed
3. **Project isolation**: Each project has its own directory and optionally its own MySQL database
4. **SSL certificates**: Managed by system - do not modify SSL config
5. **NO build steps**: Do NOT use build tools (Vite, Webpack, etc.)

---

## NO BUILD WORKFLOW (CRITICAL!)

**NEVER create projects that require `npm run build` or dev servers.**

```
FORBIDDEN:                      ALLOWED:
- .vue files (SFC)             - Plain .js files with ES modules
- .jsx/.tsx files              - Pre-built library files (.min.js)
- npm run dev/build            - Direct browser JavaScript
- vite, webpack, parcel
```

### Vue/React WITHOUT Build

Write components in plain .js files:

```javascript
// js/components/Header.js - Plain JS, not .vue!
const Header = {
  template: `<header><h1>{{ title }}</h1></header>`,
  data() { return { title: 'My App' } }
}
```

### Download Libraries (NO CDN in production!)

```bash
mkdir -p libs
curl -o libs/vue.global.min.js https://unpkg.com/vue@3/dist/vue.global.prod.js
```

---

## QUICK SECURITY REFERENCE

### ALWAYS DO:

| Category | Rule |
|----------|------|
| **SQL** | Use prepared statements: `$stmt->execute([$id])` |
| **XSS** | Escape output: `htmlspecialchars($x, ENT_QUOTES, 'UTF-8')` |
| **Passwords** | Hash with bcrypt: `password_hash($p, PASSWORD_BCRYPT)` |
| **Forms** | Include CSRF token on every POST form |
| **Sessions** | Call `session_regenerate_id(true)` after login |
| **Auth** | Check authentication at TOP of every protected file |

### NEVER DO:

| Bad | Why | Good |
|-----|-----|------|
| `"WHERE id=$id"` | SQL Injection | `"WHERE id=?"` + bind |
| `echo $userInput` | XSS Attack | `echo htmlspecialchars($userInput)` |
| `$password` in code | Credential leak | `$_ENV['DB_PASS']` from .env |

---

## VISUAL VERIFICATION WITH PLAYWRIGHT

Use Playwright when:
1. User says something "doesn't look right"
2. You need to verify visual changes
3. User asks you to "see" or "check" the page

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    page.set_viewport_size({"width": 1920, "height": 1080})
    page.goto('https://127.0.0.1:9867/myproject/')
    page.wait_for_load_state("networkidle")
    page.screenshot(path='/tmp/screenshot.png', full_page=True)
    browser.close()
```

**After screenshots, check server logs:**
```bash
sudo tail -20 /var/log/nginx/codehero-projects-error.log
```

---

## VISUAL CHECK GUIDELINES

1. **Alignment** - Elements in same row/column must align
2. **Symmetry** - Equal spacing on both sides
3. **Color contrast** - Text readable on background
4. **Typography** - Readable size, proper hierarchy
5. **Responsiveness** - Test at different viewport sizes
6. **Forms** - Validate inputs, show clear errors
7. **Links** - All internal links work

---

## PROGRAMMING PHILOSOPHY

### Clean Code Only

- Code must be readable by a **junior developer**
- Comments explain **WHY**, not just what
- Variable names are **descriptive**
- Functions are **small** and do **one thing**

### Bottom-Up Development

```
1. Database + Config     <- Test it works
2. User model            <- Test CRUD works
3. Auth system           <- Test login/logout works
4. Features              <- Build on working foundation
```

**NEVER build on untested code.**

### UI Design (Tailwind)

- Spacing: Use 4px grid (`gap-2`=8px, `gap-4`=16px)
- Colors: 60% neutral, 30% secondary, 10% accent
- No pure black/white: Use `gray-900` and `gray-50`
- Buttons: `px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md`
- Cards: `bg-white rounded-lg shadow-sm border border-gray-200 p-6`

---

## PROJECT DOCUMENTATION

Every project should have:

1. **technologies.md** - Tech stack, versions, libraries used
2. **map.md** - Directory structure, page flow, database tables

---

## WORKSPACE PATHS

```
Web projects:  /var/www/projects/{name}/
App projects:  /opt/apps/{name}/

FORBIDDEN:     /opt/codehero/, /etc/nginx/, /etc/systemd/
```
