# Java Development Context

## Security Patterns

### SQL Injection Prevention

```java
// ALWAYS use PreparedStatement
String sql = "SELECT * FROM users WHERE email = ? AND status = ?";
try (PreparedStatement stmt = connection.prepareStatement(sql)) {
    stmt.setString(1, email);
    stmt.setString(2, status);
    ResultSet rs = stmt.executeQuery();
    // Process results
}

// Spring JPA - Safe by default
@Repository
public interface UserRepository extends JpaRepository<User, Long> {
    Optional<User> findByEmail(String email);

    @Query("SELECT u FROM User u WHERE u.status = :status")
    List<User> findByStatus(@Param("status") String status);
}

// NEVER concatenate SQL strings
// BAD: "SELECT * FROM users WHERE id = " + userId
```

### XSS Prevention

```java
// Spring MVC - Thymeleaf escapes by default
<span th:text="${userInput}">Safe output</span>

// For raw HTML (use sparingly)
<span th:utext="${trustedHtml}">Raw HTML</span>

// Manual escaping
import org.apache.commons.text.StringEscapeUtils;
String safe = StringEscapeUtils.escapeHtml4(userInput);

// JSON output
@RestController
public class ApiController {
    @GetMapping("/api/data")
    public ResponseEntity<Map<String, Object>> getData() {
        // Jackson escapes by default
        return ResponseEntity.ok(data);
    }
}
```

### Password Security

```java
// BCrypt hashing
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

BCryptPasswordEncoder encoder = new BCryptPasswordEncoder(12);
String hash = encoder.encode(password);

// Verification
if (encoder.matches(inputPassword, storedHash)) {
    // Password correct
}
```

### CSRF Protection

```java
// Spring Security - enabled by default
@Configuration
@EnableWebSecurity
public class SecurityConfig {
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf
                .csrfTokenRepository(CookieCsrfTokenRepository.withHttpOnlyFalse())
            );
        return http.build();
    }
}

// Thymeleaf form - automatic CSRF token
<form th:action="@{/submit}" method="post">
    <!-- CSRF token added automatically -->
</form>
```

### Session Security

```java
// application.properties
server.servlet.session.cookie.http-only=true
server.servlet.session.cookie.secure=true
server.servlet.session.cookie.same-site=strict
server.servlet.session.timeout=30m

// Regenerate session after login
@PostMapping("/login")
public String login(HttpServletRequest request) {
    request.getSession().invalidate();
    request.getSession(true);
    // Set user attributes
}
```

---

## Authentication Pattern (Spring Security)

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/", "/public/**", "/login").permitAll()
                .requestMatchers("/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated()
            )
            .formLogin(form -> form
                .loginPage("/login")
                .defaultSuccessUrl("/dashboard")
                .permitAll()
            )
            .logout(logout -> logout
                .logoutSuccessUrl("/")
                .permitAll()
            );
        return http.build();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder(12);
    }
}

@Service
public class UserDetailsServiceImpl implements UserDetailsService {
    @Autowired
    private UserRepository userRepository;

    @Override
    public UserDetails loadUserByUsername(String email) throws UsernameNotFoundException {
        User user = userRepository.findByEmail(email)
            .orElseThrow(() -> new UsernameNotFoundException("User not found"));

        return org.springframework.security.core.userdetails.User.builder()
            .username(user.getEmail())
            .password(user.getPasswordHash())
            .roles(user.getRole())
            .build();
    }
}
```

---

## Database Patterns (Spring Data JPA)

### Entity Definition

```java
@Entity
@Table(name = "users")
public class User {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String email;

    @Column(name = "password_hash", nullable = false)
    private String passwordHash;

    @Column(nullable = false)
    private String role = "USER";

    @CreationTimestamp
    private LocalDateTime createdAt;

    @UpdateTimestamp
    private LocalDateTime updatedAt;

    // Getters and setters
}
```

### Repository

```java
@Repository
public interface UserRepository extends JpaRepository<User, Long> {
    Optional<User> findByEmail(String email);
    List<User> findByRole(String role);

    @Query("SELECT u FROM User u WHERE u.createdAt > :date")
    List<User> findRecentUsers(@Param("date") LocalDateTime date);

    @Modifying
    @Query("UPDATE User u SET u.role = :role WHERE u.id = :id")
    int updateRole(@Param("id") Long id, @Param("role") String role);
}
```

### Transactions

```java
@Service
@Transactional
public class OrderService {
    @Autowired
    private OrderRepository orderRepository;
    @Autowired
    private OrderItemRepository orderItemRepository;

    public Order createOrder(Long userId, List<OrderItemDto> items) {
        Order order = new Order();
        order.setUserId(userId);
        order.setTotal(calculateTotal(items));
        order = orderRepository.save(order);

        for (OrderItemDto item : items) {
            OrderItem orderItem = new OrderItem();
            orderItem.setOrderId(order.getId());
            orderItem.setProductId(item.getProductId());
            orderItemRepository.save(orderItem);
        }

        return order;
    }
}
```

### Pagination

```java
@GetMapping("/users")
public Page<User> getUsers(
    @RequestParam(defaultValue = "0") int page,
    @RequestParam(defaultValue = "20") int size,
    @RequestParam(defaultValue = "createdAt") String sortBy
) {
    Pageable pageable = PageRequest.of(page, Math.min(size, 100), Sort.by(sortBy).descending());
    return userRepository.findAll(pageable);
}
```

---

## REST API Pattern

```java
@RestController
@RequestMapping("/api/users")
public class UserController {
    @Autowired
    private UserService userService;

    @GetMapping
    public ResponseEntity<ApiResponse<List<UserDto>>> getUsers() {
        List<UserDto> users = userService.getAllUsers();
        return ResponseEntity.ok(ApiResponse.success(users));
    }

    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<UserDto>> getUser(@PathVariable Long id) {
        return userService.findById(id)
            .map(user -> ResponseEntity.ok(ApiResponse.success(user)))
            .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    public ResponseEntity<ApiResponse<UserDto>> createUser(@Valid @RequestBody CreateUserDto dto) {
        UserDto user = userService.create(dto);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.success(user));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiResponse<Void>> handleValidation(MethodArgumentNotValidException ex) {
        String message = ex.getBindingResult().getFieldErrors().stream()
            .map(e -> e.getField() + ": " + e.getDefaultMessage())
            .collect(Collectors.joining(", "));
        return ResponseEntity.badRequest().body(ApiResponse.error("VALIDATION_ERROR", message));
    }
}

// Response wrapper
public class ApiResponse<T> {
    private boolean success;
    private T data;
    private ApiError error;

    public static <T> ApiResponse<T> success(T data) {
        ApiResponse<T> response = new ApiResponse<>();
        response.success = true;
        response.data = data;
        return response;
    }

    public static <T> ApiResponse<T> error(String code, String message) {
        ApiResponse<T> response = new ApiResponse<>();
        response.success = false;
        response.error = new ApiError(code, message);
        return response;
    }
}
```

---

## Input Validation

```java
public class CreateUserDto {
    @NotBlank(message = "Email is required")
    @Email(message = "Invalid email format")
    private String email;

    @NotBlank(message = "Password is required")
    @Size(min = 8, message = "Password must be at least 8 characters")
    private String password;

    @NotBlank(message = "Name is required")
    @Size(min = 1, max = 255, message = "Name must be 1-255 characters")
    private String name;

    // Getters and setters
}

// In controller
@PostMapping
public ResponseEntity<?> create(@Valid @RequestBody CreateUserDto dto) {
    // Validation happens automatically
}
```

---

## Error Handling

```java
@ControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger logger = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiResponse<Void>> handleException(Exception ex) {
        logger.error("Unhandled exception", ex);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
            .body(ApiResponse.error("SERVER_ERROR", "An unexpected error occurred"));
    }

    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<ApiResponse<Void>> handleNotFound(ResourceNotFoundException ex) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
            .body(ApiResponse.error("NOT_FOUND", ex.getMessage()));
    }

    @ExceptionHandler(AccessDeniedException.class)
    public ResponseEntity<ApiResponse<Void>> handleAccessDenied(AccessDeniedException ex) {
        return ResponseEntity.status(HttpStatus.FORBIDDEN)
            .body(ApiResponse.error("FORBIDDEN", "Access denied"));
    }
}
```

---

## File Upload Security

```java
@PostMapping("/upload")
public ResponseEntity<?> uploadFile(@RequestParam("file") MultipartFile file) {
    List<String> allowedTypes = Arrays.asList("image/jpeg", "image/png", "application/pdf");
    long maxSize = 10 * 1024 * 1024; // 10MB

    if (file.isEmpty()) {
        return ResponseEntity.badRequest().body("No file provided");
    }
    if (file.getSize() > maxSize) {
        return ResponseEntity.badRequest().body("File too large");
    }
    if (!allowedTypes.contains(file.getContentType())) {
        return ResponseEntity.badRequest().body("File type not allowed");
    }

    // NEVER use original filename
    String extension = StringUtils.getFilenameExtension(file.getOriginalFilename());
    String newName = UUID.randomUUID().toString() + "." + extension;

    Path uploadPath = Paths.get("/var/www/uploads", newName);
    Files.copy(file.getInputStream(), uploadPath);

    return ResponseEntity.ok(Map.of("filename", newName));
}
```

---

## Environment Configuration

```properties
# application.properties (NEVER commit secrets)
spring.datasource.url=jdbc:mysql://${DB_HOST:localhost}:3306/${DB_NAME}
spring.datasource.username=${DB_USER}
spring.datasource.password=${DB_PASS}

spring.jpa.hibernate.ddl-auto=validate
spring.jpa.show-sql=false

server.port=${PORT:8080}
```

```java
// Access environment variables
@Value("${DB_HOST:localhost}")
private String dbHost;

@Value("${API_KEY}")
private String apiKey;
```
