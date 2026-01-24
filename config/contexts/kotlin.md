# Kotlin/Android Development Context

## Security Patterns

### Secure Storage

```kotlin
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

class SecureStorage(context: Context) {
    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()

    private val sharedPreferences = EncryptedSharedPreferences.create(
        context,
        "secure_prefs",
        masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )

    fun saveToken(token: String) {
        sharedPreferences.edit().putString("auth_token", token).apply()
    }

    fun getToken(): String? {
        return sharedPreferences.getString("auth_token", null)
    }

    fun clearToken() {
        sharedPreferences.edit().remove("auth_token").apply()
    }
}
```

### Network Security

```kotlin
// res/xml/network_security_config.xml
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config cleartextTrafficPermitted="false">
        <trust-anchors>
            <certificates src="system" />
        </trust-anchors>
    </base-config>

    <!-- Certificate pinning -->
    <domain-config>
        <domain includeSubdomains="true">api.example.com</domain>
        <pin-set expiration="2025-01-01">
            <pin digest="SHA-256">BASE64_ENCODED_HASH</pin>
        </pin-set>
    </domain-config>
</network-security-config>

// AndroidManifest.xml
<application
    android:networkSecurityConfig="@xml/network_security_config"
    ...>
```

### Input Validation

```kotlin
object Validators {
    fun email(value: String?): String? {
        if (value.isNullOrBlank()) return "Email is required"
        if (!Patterns.EMAIL_ADDRESS.matcher(value).matches()) return "Invalid email format"
        return null
    }

    fun password(value: String?): String? {
        if (value.isNullOrBlank()) return "Password is required"
        if (value.length < 8) return "Password must be at least 8 characters"
        return null
    }

    fun required(value: String?, fieldName: String): String? {
        if (value.isNullOrBlank()) return "$fieldName is required"
        return null
    }
}
```

### SQL Injection Prevention (Room)

```kotlin
// Room DAO - Always use parameterized queries
@Dao
interface UserDao {
    // Safe - Room uses prepared statements
    @Query("SELECT * FROM users WHERE email = :email")
    suspend fun findByEmail(email: String): User?

    @Query("SELECT * FROM users WHERE id = :id")
    suspend fun findById(id: Long): User?

    // NEVER build queries with string concatenation
    // BAD: @Query("SELECT * FROM users WHERE id = " + id)
}
```

---

## Architecture (MVVM + Clean Architecture)

### Project Structure

```
app/src/main/java/com/example/app/
├── core/
│   ├── di/                    # Dependency injection
│   ├── network/               # API client, interceptors
│   └── utils/                 # Extensions, helpers
├── features/
│   └── auth/
│       ├── data/
│       │   ├── remote/        # API data sources
│       │   ├── local/         # Room DAOs
│       │   └── repository/    # Repository implementations
│       ├── domain/
│       │   ├── model/         # Domain entities
│       │   ├── repository/    # Repository interfaces
│       │   └── usecase/       # Use cases
│       └── presentation/
│           ├── ui/            # Composables/Fragments
│           └── viewmodel/     # ViewModels
└── App.kt
```

### Entity

```kotlin
data class User(
    val id: String,
    val email: String,
    val name: String,
    val role: String = "user"
)
```

### Repository

```kotlin
// Domain layer - interface
interface AuthRepository {
    suspend fun login(email: String, password: String): Result<User>
    suspend fun logout(): Result<Unit>
    suspend fun getCurrentUser(): Result<User?>
}

// Data layer - implementation
class AuthRepositoryImpl(
    private val remoteDataSource: AuthRemoteDataSource,
    private val localDataSource: AuthLocalDataSource
) : AuthRepository {

    override suspend fun login(email: String, password: String): Result<User> {
        return try {
            val user = remoteDataSource.login(email, password)
            localDataSource.saveUser(user)
            Result.success(user)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun getCurrentUser(): Result<User?> {
        return try {
            Result.success(localDataSource.getUser())
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
```

### Use Case

```kotlin
class LoginUseCase(private val authRepository: AuthRepository) {
    suspend operator fun invoke(email: String, password: String): Result<User> {
        // Validate input
        Validators.email(email)?.let { return Result.failure(ValidationException(it)) }
        Validators.password(password)?.let { return Result.failure(ValidationException(it)) }

        return authRepository.login(email, password)
    }
}
```

---

## ViewModel

```kotlin
class AuthViewModel(
    private val loginUseCase: LoginUseCase,
    private val logoutUseCase: LogoutUseCase,
    private val getCurrentUserUseCase: GetCurrentUserUseCase
) : ViewModel() {

    private val _uiState = MutableStateFlow<AuthUiState>(AuthUiState.Initial)
    val uiState: StateFlow<AuthUiState> = _uiState.asStateFlow()

    init {
        checkAuthStatus()
    }

    private fun checkAuthStatus() {
        viewModelScope.launch {
            getCurrentUserUseCase().fold(
                onSuccess = { user ->
                    _uiState.value = if (user != null) {
                        AuthUiState.Authenticated(user)
                    } else {
                        AuthUiState.Unauthenticated
                    }
                },
                onFailure = { _uiState.value = AuthUiState.Unauthenticated }
            )
        }
    }

    fun login(email: String, password: String) {
        viewModelScope.launch {
            _uiState.value = AuthUiState.Loading
            loginUseCase(email, password).fold(
                onSuccess = { user -> _uiState.value = AuthUiState.Authenticated(user) },
                onFailure = { error -> _uiState.value = AuthUiState.Error(error.message ?: "Login failed") }
            )
        }
    }

    fun logout() {
        viewModelScope.launch {
            logoutUseCase()
            _uiState.value = AuthUiState.Unauthenticated
        }
    }
}

sealed class AuthUiState {
    object Initial : AuthUiState()
    object Loading : AuthUiState()
    data class Authenticated(val user: User) : AuthUiState()
    object Unauthenticated : AuthUiState()
    data class Error(val message: String) : AuthUiState()
}
```

---

## Jetpack Compose UI

### Screen

```kotlin
@Composable
fun LoginScreen(
    viewModel: AuthViewModel = hiltViewModel(),
    onLoginSuccess: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsState()

    LaunchedEffect(uiState) {
        if (uiState is AuthUiState.Authenticated) {
            onLoginSuccess()
        }
    }

    LoginContent(
        uiState = uiState,
        onLogin = { email, password -> viewModel.login(email, password) }
    )
}

@Composable
private fun LoginContent(
    uiState: AuthUiState,
    onLogin: (String, String) -> Unit
) {
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.Center
    ) {
        if (uiState is AuthUiState.Error) {
            Text(
                text = uiState.message,
                color = MaterialTheme.colorScheme.error,
                modifier = Modifier.padding(bottom = 16.dp)
            )
        }

        OutlinedTextField(
            value = email,
            onValueChange = { email = it },
            label = { Text("Email") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
            modifier = Modifier.fillMaxWidth()
        )

        Spacer(modifier = Modifier.height(16.dp))

        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            label = { Text("Password") },
            visualTransformation = PasswordVisualTransformation(),
            modifier = Modifier.fillMaxWidth()
        )

        Spacer(modifier = Modifier.height(24.dp))

        Button(
            onClick = { onLogin(email, password) },
            enabled = uiState !is AuthUiState.Loading,
            modifier = Modifier.fillMaxWidth()
        ) {
            if (uiState is AuthUiState.Loading) {
                CircularProgressIndicator(
                    modifier = Modifier.size(24.dp),
                    color = MaterialTheme.colorScheme.onPrimary
                )
            } else {
                Text("Login")
            }
        }
    }
}
```

### Reusable Components

```kotlin
@Composable
fun LoadingButton(
    onClick: () -> Unit,
    isLoading: Boolean,
    modifier: Modifier = Modifier,
    content: @Composable () -> Unit
) {
    Button(
        onClick = onClick,
        enabled = !isLoading,
        modifier = modifier
    ) {
        if (isLoading) {
            CircularProgressIndicator(
                modifier = Modifier.size(24.dp),
                color = MaterialTheme.colorScheme.onPrimary
            )
        } else {
            content()
        }
    }
}

@Composable
fun ValidatedTextField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    validator: (String) -> String?,
    modifier: Modifier = Modifier
) {
    var error by remember { mutableStateOf<String?>(null) }

    OutlinedTextField(
        value = value,
        onValueChange = {
            onValueChange(it)
            error = validator(it)
        },
        label = { Text(label) },
        isError = error != null,
        supportingText = error?.let { { Text(it) } },
        modifier = modifier
    )
}
```

---

## Network Layer (Retrofit + OkHttp)

```kotlin
// API Service
interface ApiService {
    @POST("auth/login")
    suspend fun login(@Body request: LoginRequest): Response<ApiResponse<User>>

    @GET("users/{id}")
    suspend fun getUser(@Path("id") id: String): Response<ApiResponse<User>>

    @GET("users")
    suspend fun getUsers(@Query("page") page: Int): Response<ApiResponse<List<User>>>
}

// Response wrapper
data class ApiResponse<T>(
    val success: Boolean,
    val data: T?,
    val error: ApiError?
)

data class ApiError(
    val code: String,
    val message: String
)

// OkHttp client with interceptors
@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {
    @Provides
    @Singleton
    fun provideOkHttpClient(secureStorage: SecureStorage): OkHttpClient {
        return OkHttpClient.Builder()
            .addInterceptor { chain ->
                val token = secureStorage.getToken()
                val request = chain.request().newBuilder()
                    .apply {
                        token?.let { addHeader("Authorization", "Bearer $it") }
                    }
                    .build()
                chain.proceed(request)
            }
            .addInterceptor(HttpLoggingInterceptor().apply {
                level = if (BuildConfig.DEBUG) {
                    HttpLoggingInterceptor.Level.BODY
                } else {
                    HttpLoggingInterceptor.Level.NONE
                }
            })
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .build()
    }

    @Provides
    @Singleton
    fun provideRetrofit(okHttpClient: OkHttpClient): Retrofit {
        return Retrofit.Builder()
            .baseUrl(BuildConfig.API_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }

    @Provides
    @Singleton
    fun provideApiService(retrofit: Retrofit): ApiService {
        return retrofit.create(ApiService::class.java)
    }
}
```

---

## Room Database

```kotlin
@Entity(tableName = "users")
data class UserEntity(
    @PrimaryKey val id: String,
    val email: String,
    val name: String,
    val role: String,
    @ColumnInfo(name = "created_at") val createdAt: Long = System.currentTimeMillis()
)

@Dao
interface UserDao {
    @Query("SELECT * FROM users WHERE id = :id")
    suspend fun findById(id: String): UserEntity?

    @Query("SELECT * FROM users WHERE email = :email")
    suspend fun findByEmail(email: String): UserEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(user: UserEntity)

    @Delete
    suspend fun delete(user: UserEntity)

    @Query("DELETE FROM users")
    suspend fun deleteAll()
}

@Database(entities = [UserEntity::class], version = 1)
abstract class AppDatabase : RoomDatabase() {
    abstract fun userDao(): UserDao
}

// Mapper
fun UserEntity.toDomain() = User(id, email, name, role)
fun User.toEntity() = UserEntity(id, email, name, role)
```

---

## Navigation

```kotlin
@Composable
fun AppNavigation(
    navController: NavHostController = rememberNavController()
) {
    NavHost(
        navController = navController,
        startDestination = "splash"
    ) {
        composable("splash") {
            SplashScreen(
                onAuthenticated = { navController.navigate("home") { popUpTo("splash") { inclusive = true } } },
                onUnauthenticated = { navController.navigate("login") { popUpTo("splash") { inclusive = true } } }
            )
        }

        composable("login") {
            LoginScreen(
                onLoginSuccess = { navController.navigate("home") { popUpTo("login") { inclusive = true } } },
                onRegisterClick = { navController.navigate("register") }
            )
        }

        composable("home") {
            HomeScreen(
                onUserClick = { userId -> navController.navigate("user/$userId") },
                onLogout = { navController.navigate("login") { popUpTo(0) } }
            )
        }

        composable(
            route = "user/{userId}",
            arguments = listOf(navArgument("userId") { type = NavType.StringType })
        ) { backStackEntry ->
            val userId = backStackEntry.arguments?.getString("userId") ?: return@composable
            UserDetailScreen(userId = userId)
        }
    }
}
```

---

## Dependency Injection (Hilt)

```kotlin
@HiltAndroidApp
class App : Application()

@Module
@InstallIn(SingletonComponent::class)
object AppModule {
    @Provides
    @Singleton
    fun provideSecureStorage(@ApplicationContext context: Context): SecureStorage {
        return SecureStorage(context)
    }

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): AppDatabase {
        return Room.databaseBuilder(context, AppDatabase::class.java, "app_db")
            .build()
    }
}

@Module
@InstallIn(SingletonComponent::class)
abstract class RepositoryModule {
    @Binds
    @Singleton
    abstract fun bindAuthRepository(impl: AuthRepositoryImpl): AuthRepository
}

// Usage in ViewModel
@HiltViewModel
class AuthViewModel @Inject constructor(
    private val loginUseCase: LoginUseCase
) : ViewModel()
```

---

## Testing

```kotlin
@RunWith(MockitoJUnitRunner::class)
class AuthViewModelTest {
    @Mock
    private lateinit var loginUseCase: LoginUseCase

    private lateinit var viewModel: AuthViewModel

    @Before
    fun setup() {
        viewModel = AuthViewModel(loginUseCase)
    }

    @Test
    fun `login success updates state to authenticated`() = runTest {
        // Given
        val user = User("1", "test@test.com", "Test User")
        whenever(loginUseCase("test@test.com", "password"))
            .thenReturn(Result.success(user))

        // When
        viewModel.login("test@test.com", "password")

        // Then
        val state = viewModel.uiState.value
        assertTrue(state is AuthUiState.Authenticated)
        assertEquals(user, (state as AuthUiState.Authenticated).user)
    }

    @Test
    fun `login failure updates state to error`() = runTest {
        // Given
        whenever(loginUseCase("test@test.com", "wrong"))
            .thenReturn(Result.failure(Exception("Invalid credentials")))

        // When
        viewModel.login("test@test.com", "wrong")

        // Then
        val state = viewModel.uiState.value
        assertTrue(state is AuthUiState.Error)
        assertEquals("Invalid credentials", (state as AuthUiState.Error).message)
    }
}
```
