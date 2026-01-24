# PHP Development Context

## Security Patterns

### SQL Injection Prevention

```php
// PDO - ALWAYS use prepared statements
$stmt = $pdo->prepare("SELECT * FROM users WHERE email = ? AND status = ?");
$stmt->execute([$email, $status]);
$user = $stmt->fetch();

// MySQLi
$stmt = $mysqli->prepare("SELECT * FROM users WHERE id = ?");
$stmt->bind_param("i", $id);
$stmt->execute();
```

### XSS Prevention

```php
// HTML output - ALWAYS escape
echo htmlspecialchars($userInput, ENT_QUOTES, 'UTF-8');

// In attributes
<input value="<?= htmlspecialchars($value, ENT_QUOTES, 'UTF-8') ?>">

// JSON output
header('Content-Type: application/json');
echo json_encode($data, JSON_HEX_TAG | JSON_HEX_AMP);
```

### Password Security

```php
// Hashing
$hash = password_hash($password, PASSWORD_BCRYPT, ['cost' => 12]);

// Verification
if (password_verify($inputPassword, $storedHash)) {
    // Password correct
}
```

### CSRF Protection

```php
// Generate token (on session start)
if (empty($_SESSION['csrf_token'])) {
    $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
}

// In every form
<form method="POST">
    <input type="hidden" name="csrf_token" value="<?= $_SESSION['csrf_token'] ?>">
</form>

// Validate on every POST
if (!hash_equals($_SESSION['csrf_token'], $_POST['csrf_token'] ?? '')) {
    http_response_code(403);
    die('CSRF validation failed');
}
```

### Session Security

```php
ini_set('session.cookie_httponly', 1);
ini_set('session.cookie_secure', 1);
ini_set('session.cookie_samesite', 'Strict');

// Regenerate after login
session_regenerate_id(true);
```

---

## Authentication Pattern

```php
class Auth {
    private PDO $db;

    public function __construct(PDO $db) {
        $this->db = $db;
    }

    public function login(string $email, string $password): ?array {
        $email = filter_var($email, FILTER_VALIDATE_EMAIL);
        if (!$email) return null;

        $stmt = $this->db->prepare("SELECT id, email, password_hash, role FROM users WHERE email = ?");
        $stmt->execute([$email]);
        $user = $stmt->fetch(PDO::FETCH_ASSOC);

        if (!$user || !password_verify($password, $user['password_hash'])) {
            return null;
        }

        session_regenerate_id(true);
        $_SESSION['user_id'] = $user['id'];
        $_SESSION['user_email'] = $user['email'];
        $_SESSION['user_role'] = $user['role'];

        return $user;
    }

    public function requireAuth(): void {
        if (!isset($_SESSION['user_id'])) {
            header('Location: /login.php');
            exit;
        }
    }
}
```

### Protected Page Pattern

```php
<?php
// EVERY protected page starts like this
require_once __DIR__ . '/includes/auth.php';
require_once __DIR__ . '/includes/db.php';

session_start();
$auth = new Auth($pdo);
$auth->requireAuth();

// Now safe to show protected content
?>
```

---

## Database Patterns

### Connection

```php
$dsn = sprintf('mysql:host=%s;dbname=%s;charset=utf8mb4',
    $_ENV['DB_HOST'], $_ENV['DB_NAME']);

$pdo = new PDO($dsn, $_ENV['DB_USER'], $_ENV['DB_PASS'], [
    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    PDO::ATTR_EMULATE_PREPARES => false,
]);
```

### Transactions

```php
try {
    $pdo->beginTransaction();

    // Multiple related operations
    $stmt = $pdo->prepare("INSERT INTO orders (user_id, total) VALUES (?, ?)");
    $stmt->execute([$userId, $total]);
    $orderId = $pdo->lastInsertId();

    $stmt = $pdo->prepare("INSERT INTO order_items (order_id, product_id) VALUES (?, ?)");
    foreach ($items as $item) {
        $stmt->execute([$orderId, $item['product_id']]);
    }

    $pdo->commit();
} catch (Exception $e) {
    $pdo->rollBack();
    throw $e;
}
```

### Pagination

```php
function paginate(PDO $pdo, string $query, array $params, int $page = 1, int $perPage = 20): array {
    $page = max(1, $page);
    $perPage = min(100, max(1, $perPage));
    $offset = ($page - 1) * $perPage;

    // Get total count
    $countQuery = preg_replace('/SELECT .* FROM/i', 'SELECT COUNT(*) FROM', $query);
    $countQuery = preg_replace('/ORDER BY .*/i', '', $countQuery);
    $stmt = $pdo->prepare($countQuery);
    $stmt->execute($params);
    $total = (int) $stmt->fetchColumn();

    // Get results
    $query .= " LIMIT $perPage OFFSET $offset";
    $stmt = $pdo->prepare($query);
    $stmt->execute($params);

    return [
        'items' => $stmt->fetchAll(),
        'pagination' => [
            'page' => $page,
            'total' => $total,
            'total_pages' => (int) ceil($total / $perPage),
        ]
    ];
}
```

---

## API Response Pattern

```php
function jsonResponse($data, int $status = 200): never {
    http_response_code($status);
    header('Content-Type: application/json');
    echo json_encode([
        'success' => $status >= 200 && $status < 300,
        'data' => $data
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

function jsonError(string $message, string $code = 'ERROR', int $status = 400): never {
    http_response_code($status);
    header('Content-Type: application/json');
    echo json_encode([
        'success' => false,
        'error' => ['code' => $code, 'message' => $message]
    ], JSON_UNESCAPED_UNICODE);
    exit;
}
```

---

## Input Validation

```php
class Validator {
    private array $errors = [];

    public function email(string $value, string $field = 'email'): ?string {
        $value = trim($value);
        if (empty($value)) {
            $this->errors[$field] = 'Email is required';
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
        return $value;
    }

    public function string(string $value, string $field, int $min = 1, int $max = 255): ?string {
        $value = trim($value);
        if (strlen($value) < $min || strlen($value) > $max) {
            $this->errors[$field] = "$field must be $min-$max characters";
            return null;
        }
        return $value;
    }

    public function hasErrors(): bool { return !empty($this->errors); }
    public function getErrors(): array { return $this->errors; }
}
```

---

## Error Handling

```php
set_exception_handler(function (Throwable $e) {
    error_log(sprintf("[%s] %s in %s:%d",
        date('Y-m-d H:i:s'), $e->getMessage(), $e->getFile(), $e->getLine()
    ));

    http_response_code(500);
    if (str_contains($_SERVER['HTTP_ACCEPT'] ?? '', 'application/json')) {
        header('Content-Type: application/json');
        echo json_encode(['success' => false, 'error' => 'Server error']);
    } else {
        include __DIR__ . '/templates/error_500.html';
    }
    exit;
});
```

---

## File Upload Security

```php
function handleSecureUpload($file, $uploadDir = '/var/www/uploads/') {
    $allowed = ['jpg', 'jpeg', 'png', 'gif', 'pdf'];
    $maxSize = 10 * 1024 * 1024; // 10MB

    if ($file['error'] !== UPLOAD_ERR_OK) throw new Exception('Upload failed');
    if ($file['size'] > $maxSize) throw new Exception('File too large');

    $ext = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));
    if (!in_array($ext, $allowed)) throw new Exception('File type not allowed');

    // NEVER use original filename
    $newName = bin2hex(random_bytes(16)) . '.' . $ext;
    move_uploaded_file($file['tmp_name'], $uploadDir . $newName);

    return $newName;
}
```

---

## Environment Variables

```php
// .env file (NEVER commit to git)
// DB_HOST=localhost
// DB_NAME=myapp
// DB_USER=myuser
// DB_PASS=secretpassword

// Load with vlucas/phpdotenv
$dotenv = Dotenv\Dotenv::createImmutable(__DIR__);
$dotenv->load();

$dbHost = $_ENV['DB_HOST'] ?? 'localhost';
```
