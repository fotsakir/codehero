# Go Development Context

## Security Patterns

### SQL Injection Prevention

```go
// ALWAYS use parameterized queries
var user User
err := db.QueryRow("SELECT id, email, role FROM users WHERE email = ? AND status = ?",
    email, status).Scan(&user.ID, &user.Email, &user.Role)

// With database/sql
stmt, err := db.Prepare("SELECT * FROM users WHERE id = ?")
if err != nil {
    return err
}
defer stmt.Close()
row := stmt.QueryRow(id)

// With GORM - Safe by default
var user User
db.Where("email = ? AND status = ?", email, status).First(&user)

// GORM with struct (safe)
db.Where(&User{Email: email, Status: status}).First(&user)

// NEVER concatenate SQL strings
// BAD: fmt.Sprintf("SELECT * FROM users WHERE id = %d", userID)
```

### XSS Prevention

```go
// html/template - Escapes by default
import "html/template"

tmpl := template.Must(template.ParseFiles("template.html"))
tmpl.Execute(w, data) // Safe - auto-escapes

// For raw HTML (use sparingly with trusted content only)
import "html/template"
data := map[string]interface{}{
    "TrustedHTML": template.HTML(trustedHtml),
}

// Manual escaping
import "html"
safe := html.EscapeString(userInput)

// JSON response - Safe by default
json.NewEncoder(w).Encode(data)
```

### Password Security

```go
import "golang.org/x/crypto/bcrypt"

// Hash password
hash, err := bcrypt.GenerateFromPassword([]byte(password), 12)
if err != nil {
    return err
}

// Verify password
err = bcrypt.CompareHashAndPassword(storedHash, []byte(inputPassword))
if err == nil {
    // Password correct
}
```

### CSRF Protection

```go
import "github.com/gorilla/csrf"

// Setup middleware
csrfMiddleware := csrf.Protect(
    []byte("32-byte-long-auth-key-here!!!!!"),
    csrf.Secure(true),
    csrf.HttpOnly(true),
    csrf.SameSite(csrf.SameSiteStrictMode),
)
http.ListenAndServe(":8080", csrfMiddleware(router))

// In templates
<form method="POST">
    <input type="hidden" name="gorilla.csrf.Token" value="{{.CSRFToken}}">
</form>

// Handler
func handler(w http.ResponseWriter, r *http.Request) {
    data := map[string]interface{}{
        "CSRFToken": csrf.Token(r),
    }
    tmpl.Execute(w, data)
}
```

### Session Security

```go
import "github.com/gorilla/sessions"

var store = sessions.NewCookieStore([]byte("secret-key-min-32-bytes-long!!!!"))

func init() {
    store.Options = &sessions.Options{
        Path:     "/",
        MaxAge:   3600 * 24, // 24 hours
        HttpOnly: true,
        Secure:   true,
        SameSite: http.SameSiteStrictMode,
    }
}

// Get/Set session
func handler(w http.ResponseWriter, r *http.Request) {
    session, _ := store.Get(r, "session-name")
    session.Values["user_id"] = userID
    session.Save(r, w)
}
```

---

## Authentication Pattern

```go
type AuthService struct {
    db *sql.DB
}

func (a *AuthService) Login(email, password string) (*User, error) {
    var user User
    err := a.db.QueryRow(
        "SELECT id, email, password_hash, role FROM users WHERE email = ?",
        email,
    ).Scan(&user.ID, &user.Email, &user.PasswordHash, &user.Role)

    if err == sql.ErrNoRows {
        return nil, ErrInvalidCredentials
    }
    if err != nil {
        return nil, err
    }

    if err := bcrypt.CompareHashAndPassword([]byte(user.PasswordHash), []byte(password)); err != nil {
        return nil, ErrInvalidCredentials
    }

    return &user, nil
}

// Middleware for protected routes
func RequireAuth(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        session, _ := store.Get(r, "session")
        userID, ok := session.Values["user_id"].(int)
        if !ok || userID == 0 {
            http.Redirect(w, r, "/login", http.StatusSeeOther)
            return
        }

        // Add user to context
        ctx := context.WithValue(r.Context(), "user_id", userID)
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}

// Usage
router.Handle("/dashboard", RequireAuth(http.HandlerFunc(dashboardHandler)))
```

---

## Database Patterns

### Connection Pool

```go
import (
    "database/sql"
    _ "github.com/go-sql-driver/mysql"
)

func NewDB() (*sql.DB, error) {
    dsn := fmt.Sprintf("%s:%s@tcp(%s:3306)/%s?parseTime=true",
        os.Getenv("DB_USER"),
        os.Getenv("DB_PASS"),
        os.Getenv("DB_HOST"),
        os.Getenv("DB_NAME"),
    )

    db, err := sql.Open("mysql", dsn)
    if err != nil {
        return nil, err
    }

    db.SetMaxOpenConns(25)
    db.SetMaxIdleConns(5)
    db.SetConnMaxLifetime(5 * time.Minute)

    if err := db.Ping(); err != nil {
        return nil, err
    }

    return db, nil
}
```

### GORM Setup

```go
import (
    "gorm.io/driver/mysql"
    "gorm.io/gorm"
)

func NewGormDB() (*gorm.DB, error) {
    dsn := fmt.Sprintf("%s:%s@tcp(%s:3306)/%s?charset=utf8mb4&parseTime=True&loc=Local",
        os.Getenv("DB_USER"),
        os.Getenv("DB_PASS"),
        os.Getenv("DB_HOST"),
        os.Getenv("DB_NAME"),
    )

    db, err := gorm.Open(mysql.Open(dsn), &gorm.Config{})
    if err != nil {
        return nil, err
    }

    return db, nil
}
```

### Model Definition

```go
type User struct {
    ID           uint      `gorm:"primaryKey"`
    Email        string    `gorm:"uniqueIndex;not null"`
    PasswordHash string    `gorm:"not null"`
    Role         string    `gorm:"default:user"`
    CreatedAt    time.Time
    UpdatedAt    time.Time
}

type Order struct {
    ID        uint `gorm:"primaryKey"`
    UserID    uint
    User      User `gorm:"foreignKey:UserID"`
    Total     float64
    Items     []OrderItem
    CreatedAt time.Time
}

type OrderItem struct {
    ID        uint `gorm:"primaryKey"`
    OrderID   uint
    ProductID uint
    Quantity  int
}
```

### Transactions

```go
// With database/sql
func CreateOrder(db *sql.DB, userID int, items []OrderItem) (*Order, error) {
    tx, err := db.Begin()
    if err != nil {
        return nil, err
    }
    defer tx.Rollback()

    result, err := tx.Exec("INSERT INTO orders (user_id, total) VALUES (?, ?)", userID, total)
    if err != nil {
        return nil, err
    }
    orderID, _ := result.LastInsertId()

    stmt, err := tx.Prepare("INSERT INTO order_items (order_id, product_id, quantity) VALUES (?, ?, ?)")
    if err != nil {
        return nil, err
    }
    defer stmt.Close()

    for _, item := range items {
        _, err = stmt.Exec(orderID, item.ProductID, item.Quantity)
        if err != nil {
            return nil, err
        }
    }

    if err := tx.Commit(); err != nil {
        return nil, err
    }

    return &Order{ID: uint(orderID)}, nil
}

// With GORM
func CreateOrderGorm(db *gorm.DB, userID uint, items []OrderItem) (*Order, error) {
    order := &Order{UserID: userID}

    err := db.Transaction(func(tx *gorm.DB) error {
        if err := tx.Create(order).Error; err != nil {
            return err
        }

        for i := range items {
            items[i].OrderID = order.ID
        }

        if err := tx.Create(&items).Error; err != nil {
            return err
        }

        return nil
    })

    return order, err
}
```

### Pagination

```go
type PagedResult[T any] struct {
    Items      []T `json:"items"`
    Page       int `json:"page"`
    TotalCount int `json:"total_count"`
    TotalPages int `json:"total_pages"`
}

func GetUsers(db *gorm.DB, page, pageSize int) (*PagedResult[User], error) {
    if page < 1 {
        page = 1
    }
    if pageSize < 1 || pageSize > 100 {
        pageSize = 20
    }

    var total int64
    db.Model(&User{}).Count(&total)

    var users []User
    offset := (page - 1) * pageSize
    db.Order("created_at DESC").Offset(offset).Limit(pageSize).Find(&users)

    return &PagedResult[User]{
        Items:      users,
        Page:       page,
        TotalCount: int(total),
        TotalPages: int(math.Ceil(float64(total) / float64(pageSize))),
    }, nil
}
```

---

## REST API Pattern

```go
import (
    "encoding/json"
    "github.com/gorilla/mux"
)

type ApiResponse struct {
    Success bool        `json:"success"`
    Data    interface{} `json:"data,omitempty"`
    Error   *ApiError   `json:"error,omitempty"`
}

type ApiError struct {
    Code    string `json:"code"`
    Message string `json:"message"`
}

func jsonResponse(w http.ResponseWriter, status int, data interface{}) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(status)
    json.NewEncoder(w).Encode(ApiResponse{Success: true, Data: data})
}

func jsonError(w http.ResponseWriter, status int, code, message string) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(status)
    json.NewEncoder(w).Encode(ApiResponse{
        Success: false,
        Error:   &ApiError{Code: code, Message: message},
    })
}

// Handlers
func GetUsers(w http.ResponseWriter, r *http.Request) {
    users, err := userService.GetAll()
    if err != nil {
        jsonError(w, 500, "SERVER_ERROR", "Failed to fetch users")
        return
    }
    jsonResponse(w, 200, users)
}

func GetUser(w http.ResponseWriter, r *http.Request) {
    vars := mux.Vars(r)
    id, _ := strconv.Atoi(vars["id"])

    user, err := userService.GetByID(id)
    if err == ErrNotFound {
        jsonError(w, 404, "NOT_FOUND", "User not found")
        return
    }
    if err != nil {
        jsonError(w, 500, "SERVER_ERROR", "Failed to fetch user")
        return
    }
    jsonResponse(w, 200, user)
}

func CreateUser(w http.ResponseWriter, r *http.Request) {
    var dto CreateUserDTO
    if err := json.NewDecoder(r.Body).Decode(&dto); err != nil {
        jsonError(w, 400, "INVALID_JSON", "Invalid request body")
        return
    }

    if err := validate.Struct(dto); err != nil {
        jsonError(w, 400, "VALIDATION_ERROR", err.Error())
        return
    }

    user, err := userService.Create(dto)
    if err != nil {
        jsonError(w, 500, "SERVER_ERROR", "Failed to create user")
        return
    }
    jsonResponse(w, 201, user)
}

// Router setup
func SetupRoutes() *mux.Router {
    r := mux.NewRouter()

    api := r.PathPrefix("/api").Subrouter()
    api.HandleFunc("/users", GetUsers).Methods("GET")
    api.HandleFunc("/users/{id}", GetUser).Methods("GET")
    api.HandleFunc("/users", CreateUser).Methods("POST")

    return r
}
```

---

## Input Validation

```go
import "github.com/go-playground/validator/v10"

var validate = validator.New()

type CreateUserDTO struct {
    Email    string `json:"email" validate:"required,email"`
    Password string `json:"password" validate:"required,min=8"`
    Name     string `json:"name" validate:"required,min=1,max=255"`
}

func (dto *CreateUserDTO) Validate() error {
    return validate.Struct(dto)
}

// Custom validation
validate.RegisterValidation("strongpassword", func(fl validator.FieldLevel) bool {
    password := fl.Field().String()
    hasUpper := regexp.MustCompile(`[A-Z]`).MatchString(password)
    hasLower := regexp.MustCompile(`[a-z]`).MatchString(password)
    hasDigit := regexp.MustCompile(`[0-9]`).MatchString(password)
    return hasUpper && hasLower && hasDigit
})
```

---

## Error Handling

```go
import (
    "log"
    "runtime/debug"
)

// Recovery middleware
func RecoveryMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        defer func() {
            if err := recover(); err != nil {
                log.Printf("Panic: %v\n%s", err, debug.Stack())
                jsonError(w, 500, "SERVER_ERROR", "Internal server error")
            }
        }()
        next.ServeHTTP(w, r)
    })
}

// Custom errors
var (
    ErrNotFound           = errors.New("not found")
    ErrInvalidCredentials = errors.New("invalid credentials")
    ErrUnauthorized       = errors.New("unauthorized")
)

// Error handling in handlers
func handleError(w http.ResponseWriter, err error) {
    switch {
    case errors.Is(err, ErrNotFound):
        jsonError(w, 404, "NOT_FOUND", err.Error())
    case errors.Is(err, ErrUnauthorized):
        jsonError(w, 401, "UNAUTHORIZED", err.Error())
    default:
        log.Printf("Error: %v", err)
        jsonError(w, 500, "SERVER_ERROR", "An unexpected error occurred")
    }
}
```

---

## File Upload Security

```go
func UploadHandler(w http.ResponseWriter, r *http.Request) {
    const maxSize = 10 << 20 // 10MB
    r.Body = http.MaxBytesReader(w, r.Body, maxSize)

    if err := r.ParseMultipartForm(maxSize); err != nil {
        jsonError(w, 400, "FILE_TOO_LARGE", "File too large")
        return
    }

    file, header, err := r.FormFile("file")
    if err != nil {
        jsonError(w, 400, "NO_FILE", "No file provided")
        return
    }
    defer file.Close()

    // Validate content type
    allowedTypes := map[string]bool{
        "image/jpeg":      true,
        "image/png":       true,
        "application/pdf": true,
    }

    contentType := header.Header.Get("Content-Type")
    if !allowedTypes[contentType] {
        jsonError(w, 400, "INVALID_TYPE", "File type not allowed")
        return
    }

    // NEVER use original filename
    ext := filepath.Ext(header.Filename)
    newName := fmt.Sprintf("%s%s", uuid.New().String(), ext)
    uploadPath := filepath.Join("/var/www/uploads", newName)

    dst, err := os.Create(uploadPath)
    if err != nil {
        jsonError(w, 500, "UPLOAD_FAILED", "Failed to save file")
        return
    }
    defer dst.Close()

    io.Copy(dst, file)
    jsonResponse(w, 200, map[string]string{"filename": newName})
}
```

---

## Environment Configuration

```go
import "github.com/joho/godotenv"

func LoadConfig() {
    // Load .env file (for development)
    godotenv.Load()
}

func GetEnv(key, defaultValue string) string {
    if value := os.Getenv(key); value != "" {
        return value
    }
    return defaultValue
}

func MustGetEnv(key string) string {
    value := os.Getenv(key)
    if value == "" {
        log.Fatalf("Required environment variable %s is not set", key)
    }
    return value
}

// Usage
dbHost := GetEnv("DB_HOST", "localhost")
apiKey := MustGetEnv("API_KEY")
```
