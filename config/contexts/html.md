# Static HTML/CSS/JS Development Context

## Project Structure

```
project/
├── index.html           # Homepage
├── about.html           # About page
├── contact.html         # Contact page
├── css/
│   └── style.css        # Custom styles (after Tailwind)
├── js/
│   ├── main.js          # Main JavaScript
│   └── components/      # JS components
├── libs/                # Downloaded libraries (NO CDN)
│   ├── tailwind.min.css
│   └── alpine.min.js
└── assets/
    └── images/
```

---

## HTML Template

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Site</title>
    <link rel="stylesheet" href="libs/tailwind.min.css">
    <link rel="stylesheet" href="css/style.css">
</head>
<body class="bg-gray-50 text-gray-900">
    <header class="bg-white shadow-sm">
        <nav class="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
            <a href="index.html" class="text-xl font-bold text-blue-600">MySite</a>
            <div class="flex gap-6">
                <a href="index.html" class="text-gray-600 hover:text-gray-900">Home</a>
                <a href="about.html" class="text-gray-600 hover:text-gray-900">About</a>
                <a href="contact.html" class="text-gray-600 hover:text-gray-900">Contact</a>
            </div>
        </nav>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-8">
        <!-- Content here -->
    </main>

    <footer class="bg-gray-800 text-white mt-auto">
        <div class="max-w-7xl mx-auto px-4 py-6 text-center">
            <p>&copy; 2024 MySite. All rights reserved.</p>
        </div>
    </footer>

    <script src="libs/alpine.min.js"></script>
    <script src="js/main.js"></script>
</body>
</html>
```

---

## Tailwind CSS Patterns

### Layout

```html
<!-- Container with max width -->
<div class="max-w-7xl mx-auto px-4">

<!-- Grid - ALWAYS specify columns -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

<!-- Flex - ALWAYS specify direction -->
<div class="flex flex-row items-center justify-between">
<div class="flex flex-col gap-4">
```

### Buttons

```html
<!-- Primary -->
<button class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md font-medium transition-colors">
    Submit
</button>

<!-- Secondary -->
<button class="px-4 py-2 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-md font-medium transition-colors">
    Cancel
</button>

<!-- Danger -->
<button class="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md font-medium transition-colors">
    Delete
</button>
```

### Cards

```html
<div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <h3 class="text-lg font-semibold text-gray-900 mb-2">Card Title</h3>
    <p class="text-gray-600">Card content goes here.</p>
</div>
```

### Forms

```html
<form class="space-y-4">
    <div>
        <label for="email" class="block text-sm font-medium text-gray-700 mb-1">Email</label>
        <input type="email" id="email" name="email"
               class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
    </div>
    <div>
        <label for="message" class="block text-sm font-medium text-gray-700 mb-1">Message</label>
        <textarea id="message" name="message" rows="4"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"></textarea>
    </div>
    <button type="submit" class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md font-medium">
        Send
    </button>
</form>
```

---

## JavaScript Patterns

### DOM Ready

```javascript
document.addEventListener('DOMContentLoaded', () => {
    // Code here
});
```

### Event Delegation

```javascript
// Instead of adding listeners to each button
document.querySelector('.button-container').addEventListener('click', (e) => {
    if (e.target.matches('.delete-btn')) {
        handleDelete(e.target.dataset.id);
    }
    if (e.target.matches('.edit-btn')) {
        handleEdit(e.target.dataset.id);
    }
});
```

### Fetch API

```javascript
// GET request
async function fetchData(url) {
    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error('Fetch error:', error);
        throw error;
    }
}

// POST request
async function postData(url, data) {
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error('Post error:', error);
        throw error;
    }
}
```

### Form Handling

```javascript
document.querySelector('#contact-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const form = e.target;
    const data = Object.fromEntries(new FormData(form));

    // Validate
    if (!data.email || !data.message) {
        showError('Please fill in all fields');
        return;
    }

    try {
        const result = await postData('/api/contact', data);
        showSuccess('Message sent!');
        form.reset();
    } catch (error) {
        showError('Failed to send message');
    }
});
```

### Show/Hide Elements

```javascript
function showElement(selector) {
    document.querySelector(selector).classList.remove('hidden');
}

function hideElement(selector) {
    document.querySelector(selector).classList.add('hidden');
}

function toggleElement(selector) {
    document.querySelector(selector).classList.toggle('hidden');
}
```

---

## Alpine.js (Lightweight Interactivity)

```html
<!-- Dropdown -->
<div x-data="{ open: false }">
    <button @click="open = !open" class="btn">Menu</button>
    <div x-show="open" @click.away="open = false" class="dropdown-menu">
        <a href="#">Option 1</a>
        <a href="#">Option 2</a>
    </div>
</div>

<!-- Modal -->
<div x-data="{ showModal: false }">
    <button @click="showModal = true">Open Modal</button>
    <div x-show="showModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
        <div class="bg-white rounded-lg p-6 max-w-md" @click.away="showModal = false">
            <h2>Modal Title</h2>
            <p>Modal content</p>
            <button @click="showModal = false">Close</button>
        </div>
    </div>
</div>

<!-- Tabs -->
<div x-data="{ tab: 'tab1' }">
    <div class="flex gap-2 border-b">
        <button @click="tab = 'tab1'" :class="tab === 'tab1' ? 'border-b-2 border-blue-600' : ''">Tab 1</button>
        <button @click="tab = 'tab2'" :class="tab === 'tab2' ? 'border-b-2 border-blue-600' : ''">Tab 2</button>
    </div>
    <div x-show="tab === 'tab1'">Content 1</div>
    <div x-show="tab === 'tab2'">Content 2</div>
</div>
```

---

## Download Libraries (NO CDN)

```bash
# Create libs folder
mkdir -p libs

# Tailwind CSS (standalone build)
curl -o libs/tailwind.min.css https://cdn.tailwindcss.com/3.4.1

# Alpine.js
curl -o libs/alpine.min.js https://unpkg.com/alpinejs@3/dist/cdn.min.js

# Font Awesome (icons)
curl -o libs/fontawesome.min.css https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css
```

---

## Responsive Design

```html
<!-- Mobile-first approach -->
<div class="
    px-4          /* Mobile: 16px padding */
    md:px-8       /* Tablet: 32px padding */
    lg:px-16      /* Desktop: 64px padding */
">

<!-- Grid columns -->
<div class="
    grid
    grid-cols-1   /* Mobile: 1 column */
    md:grid-cols-2 /* Tablet: 2 columns */
    lg:grid-cols-3 /* Desktop: 3 columns */
    gap-6
">
```

### Breakpoints

| Prefix | Min Width | Typical Device |
|--------|-----------|----------------|
| (none) | 0px | Mobile |
| sm: | 640px | Large phone |
| md: | 768px | Tablet |
| lg: | 1024px | Laptop |
| xl: | 1280px | Desktop |

---

## Accessibility

```html
<!-- Images need alt text -->
<img src="photo.jpg" alt="Description of the image">

<!-- Form inputs need labels -->
<label for="email">Email</label>
<input type="email" id="email" name="email">

<!-- Buttons need descriptive text -->
<button aria-label="Close menu">
    <svg><!-- icon --></svg>
</button>

<!-- Focus visible for keyboard navigation -->
<button class="focus:ring-2 focus:ring-blue-500 focus:outline-none">
```

---

## Testing with Playwright

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # Desktop view
    page.set_viewport_size({"width": 1920, "height": 1080})
    page.goto('file:///path/to/index.html')
    page.screenshot(path='/tmp/desktop.png', full_page=True)

    # Mobile view
    page.set_viewport_size({"width": 375, "height": 667})
    page.screenshot(path='/tmp/mobile.png', full_page=True)

    browser.close()
```
