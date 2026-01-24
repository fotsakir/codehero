# .NET/C# Development Context

## Security Patterns

### SQL Injection Prevention

```csharp
// Entity Framework - Safe by default
var user = await _context.Users
    .Where(u => u.Email == email && u.Status == status)
    .FirstOrDefaultAsync();

// Parameterized queries with Dapper
var sql = "SELECT * FROM Users WHERE Email = @Email AND Status = @Status";
var user = await connection.QueryFirstOrDefaultAsync<User>(sql, new { Email = email, Status = status });

// Raw SQL with parameters (if absolutely necessary)
var users = await _context.Users
    .FromSqlRaw("SELECT * FROM Users WHERE Role = {0}", role)
    .ToListAsync();

// NEVER concatenate SQL strings
// BAD: $"SELECT * FROM Users WHERE Id = {userId}"
```

### XSS Prevention

```csharp
// Razor - Escapes by default
<span>@userInput</span>

// For raw HTML (use sparingly with trusted content only)
@Html.Raw(trustedHtml)

// Manual encoding
@using System.Text.Encodings.Web
<span>@HtmlEncoder.Default.Encode(userInput)</span>

// In API responses - JSON serialization is safe by default
return Ok(new { message = userInput });
```

### Password Security

```csharp
using Microsoft.AspNetCore.Identity;

// Hash password
var hasher = new PasswordHasher<User>();
string hash = hasher.HashPassword(user, password);

// Verify password
var result = hasher.VerifyHashedPassword(user, storedHash, inputPassword);
if (result == PasswordVerificationResult.Success)
{
    // Password correct
}

// Or use Identity framework (recommended)
var result = await _signInManager.PasswordSignInAsync(email, password, isPersistent: false, lockoutOnFailure: true);
```

### CSRF Protection

```csharp
// Program.cs - Enabled by default for forms
builder.Services.AddControllersWithViews(options =>
{
    options.Filters.Add(new AutoValidateAntiforgeryTokenAttribute());
});

// In Razor forms - automatic
<form asp-action="Submit" method="post">
    <!-- Anti-forgery token added automatically -->
</form>

// For AJAX requests
services.AddAntiforgery(options => options.HeaderName = "X-XSRF-TOKEN");

// JavaScript
fetch('/api/submit', {
    method: 'POST',
    headers: { 'X-XSRF-TOKEN': getCsrfToken() }
});
```

### Session Security

```csharp
// Program.cs
builder.Services.AddSession(options =>
{
    options.Cookie.HttpOnly = true;
    options.Cookie.SecurePolicy = CookieSecurePolicy.Always;
    options.Cookie.SameSite = SameSiteMode.Strict;
    options.IdleTimeout = TimeSpan.FromMinutes(30);
});

// Authentication cookie settings
builder.Services.ConfigureApplicationCookie(options =>
{
    options.Cookie.HttpOnly = true;
    options.Cookie.SecurePolicy = CookieSecurePolicy.Always;
    options.ExpireTimeSpan = TimeSpan.FromHours(24);
    options.SlidingExpiration = true;
});
```

---

## Authentication Pattern (ASP.NET Identity)

```csharp
// Program.cs
builder.Services.AddIdentity<ApplicationUser, IdentityRole>(options =>
{
    options.Password.RequiredLength = 8;
    options.Password.RequireDigit = true;
    options.Password.RequireLowercase = true;
    options.Password.RequireUppercase = true;
    options.Lockout.DefaultLockoutTimeSpan = TimeSpan.FromMinutes(5);
    options.Lockout.MaxFailedAccessAttempts = 5;
})
.AddEntityFrameworkStores<ApplicationDbContext>()
.AddDefaultTokenProviders();

// AccountController
public class AccountController : Controller
{
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly SignInManager<ApplicationUser> _signInManager;

    [HttpPost]
    public async Task<IActionResult> Login(LoginDto model)
    {
        if (!ModelState.IsValid) return View(model);

        var result = await _signInManager.PasswordSignInAsync(
            model.Email, model.Password, model.RememberMe, lockoutOnFailure: true);

        if (result.Succeeded)
            return RedirectToAction("Index", "Home");

        if (result.IsLockedOut)
            return View("Lockout");

        ModelState.AddModelError("", "Invalid login attempt");
        return View(model);
    }

    [HttpPost]
    public async Task<IActionResult> Logout()
    {
        await _signInManager.SignOutAsync();
        return RedirectToAction("Index", "Home");
    }
}
```

### Authorization

```csharp
// Attribute-based
[Authorize]
public class DashboardController : Controller { }

[Authorize(Roles = "Admin")]
public class AdminController : Controller { }

// Policy-based
builder.Services.AddAuthorization(options =>
{
    options.AddPolicy("RequireAdmin", policy => policy.RequireRole("Admin"));
    options.AddPolicy("RequireVerified", policy => policy.RequireClaim("EmailVerified", "true"));
});

[Authorize(Policy = "RequireAdmin")]
public IActionResult AdminOnly() { }
```

---

## Database Patterns (Entity Framework Core)

### DbContext

```csharp
public class ApplicationDbContext : DbContext
{
    public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options) : base(options) { }

    public DbSet<User> Users { get; set; }
    public DbSet<Order> Orders { get; set; }
    public DbSet<OrderItem> OrderItems { get; set; }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<User>(entity =>
        {
            entity.HasIndex(e => e.Email).IsUnique();
            entity.Property(e => e.CreatedAt).HasDefaultValueSql("GETUTCDATE()");
        });

        modelBuilder.Entity<OrderItem>()
            .HasOne(oi => oi.Order)
            .WithMany(o => o.Items)
            .HasForeignKey(oi => oi.OrderId);
    }
}
```

### Entity Definition

```csharp
public class User
{
    public int Id { get; set; }

    [Required]
    [MaxLength(255)]
    public string Email { get; set; }

    [Required]
    public string PasswordHash { get; set; }

    [MaxLength(50)]
    public string Role { get; set; } = "User";

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;
}
```

### Repository Pattern

```csharp
public interface IUserRepository
{
    Task<User?> GetByIdAsync(int id);
    Task<User?> GetByEmailAsync(string email);
    Task<IEnumerable<User>> GetAllAsync();
    Task<User> CreateAsync(User user);
    Task UpdateAsync(User user);
    Task DeleteAsync(int id);
}

public class UserRepository : IUserRepository
{
    private readonly ApplicationDbContext _context;

    public UserRepository(ApplicationDbContext context) => _context = context;

    public async Task<User?> GetByIdAsync(int id) =>
        await _context.Users.FindAsync(id);

    public async Task<User?> GetByEmailAsync(string email) =>
        await _context.Users.FirstOrDefaultAsync(u => u.Email == email);

    public async Task<User> CreateAsync(User user)
    {
        _context.Users.Add(user);
        await _context.SaveChangesAsync();
        return user;
    }
}
```

### Transactions

```csharp
public async Task<Order> CreateOrderAsync(int userId, List<OrderItemDto> items)
{
    await using var transaction = await _context.Database.BeginTransactionAsync();

    try
    {
        var order = new Order
        {
            UserId = userId,
            Total = items.Sum(i => i.Price * i.Quantity)
        };
        _context.Orders.Add(order);
        await _context.SaveChangesAsync();

        foreach (var item in items)
        {
            _context.OrderItems.Add(new OrderItem
            {
                OrderId = order.Id,
                ProductId = item.ProductId,
                Quantity = item.Quantity
            });
        }
        await _context.SaveChangesAsync();

        await transaction.CommitAsync();
        return order;
    }
    catch
    {
        await transaction.RollbackAsync();
        throw;
    }
}
```

### Pagination

```csharp
public async Task<PagedResult<User>> GetUsersAsync(int page = 1, int pageSize = 20)
{
    page = Math.Max(1, page);
    pageSize = Math.Clamp(pageSize, 1, 100);

    var query = _context.Users.AsQueryable();
    var total = await query.CountAsync();

    var items = await query
        .OrderByDescending(u => u.CreatedAt)
        .Skip((page - 1) * pageSize)
        .Take(pageSize)
        .ToListAsync();

    return new PagedResult<User>
    {
        Items = items,
        Page = page,
        PageSize = pageSize,
        TotalCount = total,
        TotalPages = (int)Math.Ceiling(total / (double)pageSize)
    };
}
```

---

## REST API Pattern

```csharp
[ApiController]
[Route("api/[controller]")]
public class UsersController : ControllerBase
{
    private readonly IUserService _userService;

    public UsersController(IUserService userService) => _userService = userService;

    [HttpGet]
    public async Task<ActionResult<ApiResponse<IEnumerable<UserDto>>>> GetUsers()
    {
        var users = await _userService.GetAllAsync();
        return Ok(ApiResponse<IEnumerable<UserDto>>.Success(users));
    }

    [HttpGet("{id}")]
    public async Task<ActionResult<ApiResponse<UserDto>>> GetUser(int id)
    {
        var user = await _userService.GetByIdAsync(id);
        if (user == null)
            return NotFound(ApiResponse<UserDto>.Error("NOT_FOUND", "User not found"));

        return Ok(ApiResponse<UserDto>.Success(user));
    }

    [HttpPost]
    public async Task<ActionResult<ApiResponse<UserDto>>> CreateUser([FromBody] CreateUserDto dto)
    {
        var user = await _userService.CreateAsync(dto);
        return CreatedAtAction(nameof(GetUser), new { id = user.Id }, ApiResponse<UserDto>.Success(user));
    }
}

// Response wrapper
public class ApiResponse<T>
{
    public bool Success { get; set; }
    public T? Data { get; set; }
    public ApiError? Error { get; set; }

    public static ApiResponse<T> Success(T data) => new() { Success = true, Data = data };
    public static ApiResponse<T> Error(string code, string message) =>
        new() { Success = false, Error = new ApiError { Code = code, Message = message } };
}
```

---

## Input Validation

```csharp
public class CreateUserDto
{
    [Required(ErrorMessage = "Email is required")]
    [EmailAddress(ErrorMessage = "Invalid email format")]
    public string Email { get; set; }

    [Required(ErrorMessage = "Password is required")]
    [MinLength(8, ErrorMessage = "Password must be at least 8 characters")]
    public string Password { get; set; }

    [Required(ErrorMessage = "Name is required")]
    [StringLength(255, MinimumLength = 1, ErrorMessage = "Name must be 1-255 characters")]
    public string Name { get; set; }
}

// Custom validation
public class ValidEmailDomainAttribute : ValidationAttribute
{
    protected override ValidationResult? IsValid(object? value, ValidationContext context)
    {
        if (value is string email && !email.EndsWith("@company.com"))
            return new ValidationResult("Email must be a company email");
        return ValidationResult.Success;
    }
}
```

---

## Error Handling

```csharp
// Program.cs - Global exception handler
app.UseExceptionHandler(errorApp =>
{
    errorApp.Run(async context =>
    {
        context.Response.ContentType = "application/json";
        var exception = context.Features.Get<IExceptionHandlerFeature>()?.Error;

        var (statusCode, message) = exception switch
        {
            NotFoundException => (404, "Resource not found"),
            UnauthorizedAccessException => (403, "Access denied"),
            _ => (500, "An unexpected error occurred")
        };

        context.Response.StatusCode = statusCode;
        await context.Response.WriteAsJsonAsync(ApiResponse<object>.Error("ERROR", message));
    });
});

// Or using middleware
public class ExceptionMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<ExceptionMiddleware> _logger;

    public async Task InvokeAsync(HttpContext context)
    {
        try
        {
            await _next(context);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Unhandled exception");
            context.Response.StatusCode = 500;
            await context.Response.WriteAsJsonAsync(ApiResponse<object>.Error("SERVER_ERROR", "An error occurred"));
        }
    }
}
```

---

## File Upload Security

```csharp
[HttpPost("upload")]
public async Task<IActionResult> Upload(IFormFile file)
{
    var allowedTypes = new[] { "image/jpeg", "image/png", "application/pdf" };
    var maxSize = 10 * 1024 * 1024; // 10MB

    if (file == null || file.Length == 0)
        return BadRequest("No file provided");

    if (file.Length > maxSize)
        return BadRequest("File too large");

    if (!allowedTypes.Contains(file.ContentType))
        return BadRequest("File type not allowed");

    // NEVER use original filename
    var extension = Path.GetExtension(file.FileName);
    var newName = $"{Guid.NewGuid()}{extension}";
    var uploadPath = Path.Combine("/var/www/uploads", newName);

    await using var stream = new FileStream(uploadPath, FileMode.Create);
    await file.CopyToAsync(stream);

    return Ok(new { filename = newName });
}
```

---

## Configuration

```json
// appsettings.json (NEVER commit secrets)
{
  "ConnectionStrings": {
    "DefaultConnection": "Server=${DB_HOST};Database=${DB_NAME};User=${DB_USER};Password=${DB_PASS};"
  },
  "Jwt": {
    "Key": "${JWT_SECRET}",
    "Issuer": "MyApp",
    "Audience": "MyApp"
  }
}
```

```csharp
// Program.cs
builder.Configuration.AddEnvironmentVariables();

var connectionString = builder.Configuration.GetConnectionString("DefaultConnection");
builder.Services.AddDbContext<ApplicationDbContext>(options =>
    options.UseSqlServer(connectionString));

// Access configuration
public class MyService
{
    private readonly IConfiguration _config;

    public MyService(IConfiguration config) => _config = config;

    public string GetApiKey() => _config["ApiKey"] ?? throw new InvalidOperationException("ApiKey not configured");
}
```
