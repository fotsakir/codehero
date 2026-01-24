# Swift/iOS Development Context

## Security Patterns

### Keychain Storage

```swift
import Security

class KeychainService {
    enum KeychainError: Error {
        case duplicateItem
        case itemNotFound
        case unexpectedStatus(OSStatus)
    }

    static func save(key: String, value: String) throws {
        guard let data = value.data(using: .utf8) else { return }

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        ]

        // Delete existing item first
        SecItemDelete(query as CFDictionary)

        let status = SecItemAdd(query as CFDictionary, nil)
        guard status == errSecSuccess else {
            throw KeychainError.unexpectedStatus(status)
        }
    }

    static func get(key: String) throws -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        guard status == errSecSuccess else {
            if status == errSecItemNotFound { return nil }
            throw KeychainError.unexpectedStatus(status)
        }

        guard let data = result as? Data,
              let value = String(data: data, encoding: .utf8) else {
            return nil
        }

        return value
    }

    static func delete(key: String) throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key
        ]

        let status = SecItemDelete(query as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw KeychainError.unexpectedStatus(status)
        }
    }
}
```

### Network Security

```swift
// App Transport Security (Info.plist) - Keep strict by default
// Only add exceptions when absolutely necessary

// Certificate Pinning with URLSession
class PinnedURLSessionDelegate: NSObject, URLSessionDelegate {
    private let pinnedCertificates: [Data]

    init(pinnedCertificates: [Data]) {
        self.pinnedCertificates = pinnedCertificates
    }

    func urlSession(_ session: URLSession,
                    didReceive challenge: URLAuthenticationChallenge,
                    completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {

        guard let serverTrust = challenge.protectionSpace.serverTrust,
              let serverCertificate = SecTrustGetCertificateAtIndex(serverTrust, 0) else {
            completionHandler(.cancelAuthenticationChallenge, nil)
            return
        }

        let serverCertificateData = SecCertificateCopyData(serverCertificate) as Data

        if pinnedCertificates.contains(serverCertificateData) {
            completionHandler(.useCredential, URLCredential(trust: serverTrust))
        } else {
            completionHandler(.cancelAuthenticationChallenge, nil)
        }
    }
}
```

### Input Validation

```swift
enum ValidationError: LocalizedError {
    case required(String)
    case invalidEmail
    case passwordTooShort(Int)
    case invalidFormat(String)

    var errorDescription: String? {
        switch self {
        case .required(let field): return "\(field) is required"
        case .invalidEmail: return "Invalid email format"
        case .passwordTooShort(let min): return "Password must be at least \(min) characters"
        case .invalidFormat(let field): return "Invalid \(field) format"
        }
    }
}

struct Validators {
    static func email(_ value: String?) -> ValidationError? {
        guard let value = value, !value.isEmpty else {
            return .required("Email")
        }
        let emailRegex = "[A-Z0-9a-z._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,64}"
        let predicate = NSPredicate(format: "SELF MATCHES %@", emailRegex)
        return predicate.evaluate(with: value) ? nil : .invalidEmail
    }

    static func password(_ value: String?, minLength: Int = 8) -> ValidationError? {
        guard let value = value, !value.isEmpty else {
            return .required("Password")
        }
        return value.count >= minLength ? nil : .passwordTooShort(minLength)
    }

    static func required(_ value: String?, fieldName: String) -> ValidationError? {
        guard let value = value, !value.trimmingCharacters(in: .whitespaces).isEmpty else {
            return .required(fieldName)
        }
        return nil
    }
}
```

---

## Architecture (MVVM + Combine)

### Project Structure

```
App/
├── Core/
│   ├── Network/
│   │   ├── APIClient.swift
│   │   └── Endpoints.swift
│   ├── Storage/
│   │   └── KeychainService.swift
│   └── Extensions/
├── Features/
│   └── Auth/
│       ├── Data/
│       │   ├── AuthRepository.swift
│       │   └── AuthModels.swift
│       ├── Domain/
│       │   ├── User.swift
│       │   └── AuthUseCases.swift
│       └── Presentation/
│           ├── LoginView.swift
│           └── LoginViewModel.swift
└── App.swift
```

### Model

```swift
struct User: Codable, Identifiable {
    let id: String
    let email: String
    let name: String
    let role: String

    init(id: String, email: String, name: String, role: String = "user") {
        self.id = id
        self.email = email
        self.name = name
        self.role = role
    }
}

struct LoginRequest: Codable {
    let email: String
    let password: String
}

struct APIResponse<T: Codable>: Codable {
    let success: Bool
    let data: T?
    let error: APIError?
}

struct APIError: Codable {
    let code: String
    let message: String
}
```

### Repository

```swift
protocol AuthRepositoryProtocol {
    func login(email: String, password: String) async throws -> User
    func logout() async throws
    func getCurrentUser() async throws -> User?
}

class AuthRepository: AuthRepositoryProtocol {
    private let apiClient: APIClient
    private let keychainService: KeychainService

    init(apiClient: APIClient, keychainService: KeychainService = KeychainService()) {
        self.apiClient = apiClient
        self.keychainService = keychainService
    }

    func login(email: String, password: String) async throws -> User {
        let request = LoginRequest(email: email, password: password)
        let response: APIResponse<LoginResponse> = try await apiClient.post("/auth/login", body: request)

        guard let data = response.data else {
            throw APIClientError.invalidResponse
        }

        try KeychainService.save(key: "auth_token", value: data.token)
        return data.user
    }

    func logout() async throws {
        try KeychainService.delete(key: "auth_token")
    }

    func getCurrentUser() async throws -> User? {
        guard let token = try KeychainService.get(key: "auth_token") else {
            return nil
        }

        let response: APIResponse<User> = try await apiClient.get("/auth/me")
        return response.data
    }
}
```

---

## ViewModel

```swift
import Combine

@MainActor
class LoginViewModel: ObservableObject {
    @Published var email = ""
    @Published var password = ""
    @Published var isLoading = false
    @Published var error: String?
    @Published var isAuthenticated = false

    private let authRepository: AuthRepositoryProtocol
    private var cancellables = Set<AnyCancellable>()

    init(authRepository: AuthRepositoryProtocol) {
        self.authRepository = authRepository
    }

    func login() async {
        // Validate
        if let emailError = Validators.email(email) {
            error = emailError.localizedDescription
            return
        }
        if let passwordError = Validators.password(password) {
            error = passwordError.localizedDescription
            return
        }

        isLoading = true
        error = nil

        do {
            let _ = try await authRepository.login(email: email, password: password)
            isAuthenticated = true
        } catch let apiError as APIClientError {
            error = apiError.localizedDescription
        } catch {
            error = "An unexpected error occurred"
        }

        isLoading = false
    }

    func logout() async {
        do {
            try await authRepository.logout()
            isAuthenticated = false
        } catch {
            self.error = error.localizedDescription
        }
    }
}
```

---

## SwiftUI Views

### Login Screen

```swift
import SwiftUI

struct LoginView: View {
    @StateObject private var viewModel: LoginViewModel
    @FocusState private var focusedField: Field?

    enum Field {
        case email, password
    }

    init(authRepository: AuthRepositoryProtocol) {
        _viewModel = StateObject(wrappedValue: LoginViewModel(authRepository: authRepository))
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                Spacer()

                Text("Welcome")
                    .font(.largeTitle)
                    .fontWeight(.bold)

                VStack(spacing: 16) {
                    TextField("Email", text: $viewModel.email)
                        .textFieldStyle(.roundedBorder)
                        .textContentType(.emailAddress)
                        .keyboardType(.emailAddress)
                        .autocapitalization(.none)
                        .focused($focusedField, equals: .email)
                        .submitLabel(.next)
                        .onSubmit { focusedField = .password }

                    SecureField("Password", text: $viewModel.password)
                        .textFieldStyle(.roundedBorder)
                        .textContentType(.password)
                        .focused($focusedField, equals: .password)
                        .submitLabel(.go)
                        .onSubmit { Task { await viewModel.login() } }
                }
                .padding(.horizontal)

                if let error = viewModel.error {
                    Text(error)
                        .foregroundColor(.red)
                        .font(.caption)
                }

                Button {
                    Task { await viewModel.login() }
                } label: {
                    if viewModel.isLoading {
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle(tint: .white))
                    } else {
                        Text("Login")
                    }
                }
                .frame(maxWidth: .infinity)
                .padding()
                .background(Color.blue)
                .foregroundColor(.white)
                .cornerRadius(10)
                .padding(.horizontal)
                .disabled(viewModel.isLoading)

                Spacer()
            }
            .navigationDestination(isPresented: $viewModel.isAuthenticated) {
                HomeView()
            }
        }
    }
}
```

### Reusable Components

```swift
struct LoadingButton: View {
    let title: String
    let isLoading: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            if isLoading {
                ProgressView()
                    .progressViewStyle(CircularProgressViewStyle(tint: .white))
            } else {
                Text(title)
            }
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(Color.blue)
        .foregroundColor(.white)
        .cornerRadius(10)
        .disabled(isLoading)
    }
}

struct ValidatedTextField: View {
    let title: String
    @Binding var text: String
    let validator: (String?) -> ValidationError?

    @State private var error: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            TextField(title, text: $text)
                .textFieldStyle(.roundedBorder)
                .onChange(of: text) { newValue in
                    error = validator(newValue)?.localizedDescription
                }

            if let error = error {
                Text(error)
                    .font(.caption)
                    .foregroundColor(.red)
            }
        }
    }
}
```

---

## Network Layer

```swift
enum APIClientError: LocalizedError {
    case invalidURL
    case invalidResponse
    case httpError(Int, String)
    case decodingError
    case networkError(Error)

    var errorDescription: String? {
        switch self {
        case .invalidURL: return "Invalid URL"
        case .invalidResponse: return "Invalid response"
        case .httpError(_, let message): return message
        case .decodingError: return "Failed to decode response"
        case .networkError(let error): return error.localizedDescription
        }
    }
}

actor APIClient {
    private let baseURL: String
    private let session: URLSession

    init(baseURL: String, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.session = session
    }

    func get<T: Decodable>(_ path: String) async throws -> T {
        return try await request(path, method: "GET")
    }

    func post<T: Decodable, B: Encodable>(_ path: String, body: B) async throws -> T {
        return try await request(path, method: "POST", body: body)
    }

    private func request<T: Decodable, B: Encodable>(_ path: String, method: String, body: B? = nil as String?) async throws -> T {
        guard let url = URL(string: baseURL + path) else {
            throw APIClientError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        // Add auth token if available
        if let token = try? KeychainService.get(key: "auth_token") {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        if let body = body {
            request.httpBody = try JSONEncoder().encode(body)
        }

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIClientError.invalidResponse
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            let errorMessage = String(data: data, encoding: .utf8) ?? "Unknown error"
            throw APIClientError.httpError(httpResponse.statusCode, errorMessage)
        }

        do {
            return try JSONDecoder().decode(T.self, from: data)
        } catch {
            throw APIClientError.decodingError
        }
    }
}
```

---

## Core Data

```swift
import CoreData

// User+CoreDataClass.swift
@objc(UserEntity)
public class UserEntity: NSManagedObject {
    @NSManaged public var id: String
    @NSManaged public var email: String
    @NSManaged public var name: String
    @NSManaged public var role: String
    @NSManaged public var createdAt: Date
}

extension UserEntity {
    func toDomain() -> User {
        User(id: id, email: email, name: name, role: role)
    }

    func update(from user: User) {
        self.id = user.id
        self.email = user.email
        self.name = user.name
        self.role = user.role
    }
}

// CoreDataManager
class CoreDataManager {
    static let shared = CoreDataManager()

    lazy var persistentContainer: NSPersistentContainer = {
        let container = NSPersistentContainer(name: "Model")
        container.loadPersistentStores { _, error in
            if let error = error {
                fatalError("Unable to load persistent stores: \(error)")
            }
        }
        return container
    }()

    var context: NSManagedObjectContext {
        persistentContainer.viewContext
    }

    func save() throws {
        if context.hasChanges {
            try context.save()
        }
    }

    func fetch<T: NSManagedObject>(_ request: NSFetchRequest<T>) throws -> [T] {
        return try context.fetch(request)
    }
}
```

---

## Navigation

```swift
enum AppRoute: Hashable {
    case login
    case home
    case userDetail(String)
    case settings
}

@MainActor
class AppRouter: ObservableObject {
    @Published var path = NavigationPath()
    @Published var isAuthenticated = false

    func navigate(to route: AppRoute) {
        path.append(route)
    }

    func pop() {
        path.removeLast()
    }

    func popToRoot() {
        path.removeLast(path.count)
    }
}

struct ContentView: View {
    @StateObject private var router = AppRouter()

    var body: some View {
        NavigationStack(path: $router.path) {
            if router.isAuthenticated {
                HomeView()
            } else {
                LoginView(authRepository: AuthRepository(apiClient: APIClient(baseURL: Config.apiURL)))
            }
        }
        .environmentObject(router)
        .navigationDestination(for: AppRoute.self) { route in
            switch route {
            case .login:
                LoginView(authRepository: AuthRepository(apiClient: APIClient(baseURL: Config.apiURL)))
            case .home:
                HomeView()
            case .userDetail(let userId):
                UserDetailView(userId: userId)
            case .settings:
                SettingsView()
            }
        }
    }
}
```

---

## Error Handling

```swift
enum AppError: LocalizedError {
    case network(Error)
    case validation(ValidationError)
    case authentication
    case unknown

    var errorDescription: String? {
        switch self {
        case .network(let error): return error.localizedDescription
        case .validation(let error): return error.localizedDescription
        case .authentication: return "Authentication failed"
        case .unknown: return "An unexpected error occurred"
        }
    }
}

// Result builder for handling errors
extension View {
    func handleError(_ error: Binding<AppError?>) -> some View {
        self.alert(
            "Error",
            isPresented: Binding(
                get: { error.wrappedValue != nil },
                set: { if !$0 { error.wrappedValue = nil } }
            ),
            presenting: error.wrappedValue
        ) { _ in
            Button("OK") { error.wrappedValue = nil }
        } message: { error in
            Text(error.localizedDescription)
        }
    }
}
```

---

## Testing

```swift
import XCTest
@testable import App

class LoginViewModelTests: XCTestCase {
    var sut: LoginViewModel!
    var mockRepository: MockAuthRepository!

    @MainActor
    override func setUp() {
        super.setUp()
        mockRepository = MockAuthRepository()
        sut = LoginViewModel(authRepository: mockRepository)
    }

    @MainActor
    func testLoginSuccess() async {
        // Given
        let expectedUser = User(id: "1", email: "test@test.com", name: "Test User")
        mockRepository.loginResult = .success(expectedUser)
        sut.email = "test@test.com"
        sut.password = "password123"

        // When
        await sut.login()

        // Then
        XCTAssertTrue(sut.isAuthenticated)
        XCTAssertNil(sut.error)
    }

    @MainActor
    func testLoginValidationError() async {
        // Given
        sut.email = ""
        sut.password = "password123"

        // When
        await sut.login()

        // Then
        XCTAssertFalse(sut.isAuthenticated)
        XCTAssertNotNil(sut.error)
        XCTAssertEqual(sut.error, "Email is required")
    }
}

class MockAuthRepository: AuthRepositoryProtocol {
    var loginResult: Result<User, Error> = .failure(AppError.unknown)

    func login(email: String, password: String) async throws -> User {
        switch loginResult {
        case .success(let user): return user
        case .failure(let error): throw error
        }
    }

    func logout() async throws {}
    func getCurrentUser() async throws -> User? { nil }
}
```
