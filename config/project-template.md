# Project Blueprint Template

Use this template with Claude Assistant to design your solution. Copy the completed blueprint to your project's description or CLAUDE.md.

---

## 1. Project Overview

**Project Name:** [Name]

**One-line Description:** [What does this project do?]

**Problem Statement:**
[What problem are you solving? Who is the target user?]

**Goals:**
- [ ] Goal 1
- [ ] Goal 2
- [ ] Goal 3

---

## 2. Tech Stack

### Project Type
- **Category:** [Web / Mobile / Hybrid / API]
- **Specific Type:** [See mobile types below if applicable]

### Frontend (Web/Hybrid)
- **Framework:** [React / Vue / Angular / Vanilla JS / None]
- **Styling:** [Tailwind / Bootstrap / CSS Modules / Styled Components]
- **State Management:** [Redux / Zustand / Context / None]
- **Build Tool:** [Vite / Webpack / None]

### Mobile Framework (if applicable)

#### Hybrid (WebView-based)
- **Platform:** [Capacitor + Ionic (Vue)]
- **UI Components:** [Ionic Components]
- **Web Framework:** [Vue 3]

#### Cross-platform Native
- **React Native:**
  - Navigation: [React Navigation / Expo Router]
  - State: [Redux / Zustand / Context]
  - UI Library: [React Native Paper / Native Base / Custom]
- **Flutter:**
  - State Management: [Provider / Riverpod / Bloc / GetX]
  - Navigation: [Navigator 2.0 / go_router / auto_route]
  - UI: [Material / Cupertino / Custom]
- **Kotlin Multiplatform (KMP):**
  - Shared Code: [Business Logic / Networking / Database]
  - UI: [Compose Multiplatform / Native per platform]

#### Native Android
- **Language:** [Java / Kotlin]
- **UI:** [XML Layouts / Jetpack Compose]
- **Architecture:** [MVVM / MVP / MVI]
- **Navigation:** [Navigation Component / Manual]
- **DI:** [Hilt / Dagger / Koin / Manual]

### Backend
- **Language:** [Python / Node.js / PHP / Go / Other]
- **Framework:** [Flask / FastAPI / Express / Laravel / None]
- **API Style:** [REST / GraphQL / None]

### Database
- **Type:** [MySQL / PostgreSQL / MongoDB / SQLite / None]
- **ORM:** [SQLAlchemy / Prisma / Eloquent / None]
- **Local Database (Mobile):** [SQLite / Realm / CoreData / Room / Hive]

### Infrastructure
- **Hosting:** [VPS / Cloud / Shared / Local]
- **Web Server:** [Nginx / Apache / OpenLiteSpeed]
- **Other Services:** [Redis / Elasticsearch / S3 / Firebase / etc.]
- **Mobile Services:** [Firebase / AWS Amplify / Supabase / None]

---

## 3. Database Schema

### Tables/Collections

```
[table_name]
├── id (PK)
├── field1 (type) - description
├── field2 (type) - description
├── created_at (datetime)
└── updated_at (datetime)

[another_table]
├── id (PK)
├── table_name_id (FK -> table_name)
└── ...
```

### Relationships
- [table1] 1:N [table2] - description
- [table2] N:M [table3] - description

---

## 4. API Endpoints

### Authentication
```
POST /api/auth/login      - User login
POST /api/auth/register   - User registration
POST /api/auth/logout     - User logout
```

### [Resource Name]
```
GET    /api/resource      - List all
GET    /api/resource/:id  - Get one
POST   /api/resource      - Create new
PUT    /api/resource/:id  - Update
DELETE /api/resource/:id  - Delete
```

---

## 5. File Structure

### Web/Traditional Project
```
project-root/
├── frontend/              # Frontend application
│   ├── src/
│   │   ├── components/    # Reusable components
│   │   ├── pages/         # Page components
│   │   ├── hooks/         # Custom hooks
│   │   ├── utils/         # Helper functions
│   │   └── styles/        # Global styles
│   └── public/            # Static assets
│
├── backend/               # Backend application
│   ├── app/
│   │   ├── routes/        # API routes
│   │   ├── models/        # Database models
│   │   ├── services/      # Business logic
│   │   └── utils/         # Helper functions
│   └── config/            # Configuration files
│
├── database/              # Database files
│   ├── migrations/        # Schema migrations
│   └── seeds/             # Seed data
│
└── docs/                  # Documentation
```

### Mobile - Capacitor + Ionic (Vue)
```
project-root/
├── src/
│   ├── views/             # Page components
│   ├── components/        # Reusable components
│   ├── router/            # Vue Router config
│   ├── stores/            # Pinia stores
│   ├── composables/       # Vue composables
│   ├── services/          # API services
│   └── theme/             # Ionic theme customization
├── public/                # Static assets
├── android/               # Native Android project (generated)
├── ios/                   # Native iOS project (generated)
├── capacitor.config.ts    # Capacitor configuration
└── ionic.config.json      # Ionic configuration
```

### Mobile - React Native
```
project-root/
├── src/
│   ├── screens/           # Screen components
│   ├── components/        # Reusable components
│   ├── navigation/        # Navigation setup
│   ├── services/          # API services
│   ├── store/             # State management
│   ├── hooks/             # Custom hooks
│   ├── utils/             # Helper functions
│   └── assets/            # Images, fonts, etc.
├── android/               # Native Android project
├── ios/                   # Native iOS project
├── __tests__/             # Test files
└── app.json               # App configuration
```

### Mobile - Flutter
```
project-root/
├── lib/
│   ├── main.dart          # App entry point
│   ├── screens/           # Screen widgets
│   ├── widgets/           # Reusable widgets
│   ├── models/            # Data models
│   ├── services/          # API services
│   ├── providers/         # State management
│   ├── utils/             # Helper functions
│   └── theme/             # Theme configuration
├── android/               # Native Android project
├── ios/                   # Native iOS project
├── test/                  # Unit tests
├── assets/                # Images, fonts
└── pubspec.yaml           # Dependencies
```

### Mobile - Native Android (Kotlin + Compose)
```
project-root/
├── app/
│   └── src/
│       └── main/
│           ├── java/com/example/app/
│           │   ├── ui/
│           │   │   ├── screens/       # Screen composables
│           │   │   ├── components/    # Reusable composables
│           │   │   └── theme/         # Material theme
│           │   ├── data/
│           │   │   ├── repository/    # Data repositories
│           │   │   ├── api/           # Network layer
│           │   │   └── local/         # Local database
│           │   ├── domain/
│           │   │   ├── model/         # Domain models
│           │   │   └── usecase/       # Business logic
│           │   ├── di/                # Dependency injection
│           │   └── MainActivity.kt
│           ├── res/                   # Resources
│           └── AndroidManifest.xml
├── gradle/                # Gradle wrapper
└── build.gradle.kts       # Build configuration
```

### Mobile - Kotlin Multiplatform
```
project-root/
├── shared/                # Shared code module
│   └── src/
│       ├── commonMain/    # Shared business logic
│       │   ├── domain/    # Domain models, use cases
│       │   ├── data/      # Repositories, network
│       │   └── utils/     # Common utilities
│       ├── androidMain/   # Android-specific code
│       ├── iosMain/       # iOS-specific code
│       └── commonTest/    # Shared tests
├── androidApp/            # Android UI module
│   └── src/main/
│       └── java/com/example/
│           └── ui/        # Compose UI
├── iosApp/                # iOS UI module
│   └── iosApp/
│       └── Views/         # SwiftUI views
└── gradle/
```

---

## 6. Features Breakdown

### MVP (Must Have)
1. **Feature 1:** [Description]
   - Sub-task A
   - Sub-task B

2. **Feature 2:** [Description]
   - Sub-task A
   - Sub-task B

### Phase 2 (Should Have)
1. **Feature 3:** [Description]
2. **Feature 4:** [Description]

### Future (Nice to Have)
1. **Feature 5:** [Description]
2. **Feature 6:** [Description]

---

## 7. Milestones / Roadmap

### Milestone 1: Foundation
- [ ] Project setup
- [ ] Database schema
- [ ] Basic API structure
- [ ] Authentication

### Milestone 2: Core Features
- [ ] Feature 1
- [ ] Feature 2

### Milestone 3: Polish
- [ ] UI improvements
- [ ] Testing
- [ ] Documentation

---

## 8. Coding Standards

### General
- Language: [English / Greek] for code and comments
- Indentation: [2 spaces / 4 spaces / tabs]
- Max line length: [80 / 120 / none]

### Naming Conventions
- Variables: `camelCase` / `snake_case`
- Functions: `camelCase` / `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Files: `kebab-case` / `snake_case`

### Git
- Branch naming: `feature/`, `fix/`, `refactor/`
- Commit style: [Conventional Commits / Free form]

---

## 9. External Integrations

- [ ] Payment: [Stripe / PayPal / None]
- [ ] Email: [SendGrid / Mailgun / SMTP]
- [ ] Storage: [S3 / Local / Cloudinary]
- [ ] Analytics: [Google Analytics / Plausible / None]
- [ ] Push Notifications (Mobile): [Firebase / OneSignal / APNs / FCM / None]
- [ ] Maps (Mobile): [Google Maps / Mapbox / Apple Maps]
- [ ] Authentication (Mobile): [Firebase Auth / Auth0 / Custom]
- [ ] Other: [...]

---

## 10. Mobile Platform Configuration (if applicable)

### App Identity
- **App Name:** [Display name on device]
- **Package Name (Android):** [com.company.appname]
- **Version:** [1.0.0]
- **Build Number:** [1]

### App Store Information
- **Target Platform:** Android Only
- **Minimum Android SDK:** [API 24 / API 26 / API 28]
- **Target Android SDK:** [API 34]

### Signing & Distribution
- **Android:**
  - [ ] Keystore created
  - [ ] Release signing configured
  - Google Play Console project: [...]

### Capabilities & Permissions

#### Android Permissions
- [ ] INTERNET
- [ ] CAMERA
- [ ] ACCESS_FINE_LOCATION
- [ ] WRITE_EXTERNAL_STORAGE
- [ ] READ_CONTACTS
- [ ] Other: [...]

### Build Configuration
- **Development:**
  - API Base URL: [http://localhost:3000 / dev.api.com]
  - Debug mode: Enabled
- **Staging:**
  - API Base URL: [staging.api.com]
- **Production:**
  - API Base URL: [api.com]
  - Minification: Enabled
  - Obfuscation: [Yes / No]

### Native Dependencies
- [ ] Camera module
- [ ] Geolocation
- [ ] Biometric authentication
- [ ] Local notifications
- [ ] File system access
- [ ] Bluetooth
- [ ] Other: [...]

### Testing Strategy
- **Unit Tests:** [Jest / JUnit / Flutter Test]
- **Integration Tests:** [Detox / Espresso / Android Instrumented Tests]
- **E2E Tests:** [Appium / Maestro / Manual]
- **Device Testing:** [Physical devices / Android Emulator / Cloud testing (BrowserStack, Firebase Test Lab)]

---

## 11. Security Considerations

### General
- [ ] Input validation
- [ ] SQL injection prevention
- [ ] XSS protection
- [ ] CSRF tokens
- [ ] Rate limiting
- [ ] Password hashing
- [ ] HTTPS only
- [ ] Environment variables for secrets

### Mobile-Specific
- [ ] API keys not hardcoded in app
- [ ] Certificate pinning for API calls
- [ ] Secure storage for tokens (Android KeyStore)
- [ ] Root detection
- [ ] Code obfuscation (production builds)
- [ ] Prevent screenshots on sensitive screens
- [ ] Biometric authentication implementation
- [ ] Deep link validation
- [ ] Network Security Config (Android)

---

## 12. Notes / Decisions

[Any important decisions, constraints, or notes about the project]

### Mobile-Specific Notes (if applicable)
- **Target Markets:** [US / EU / Global / Specific countries]
- **Offline Support:** [Required / Nice to have / Not needed]
- **Monetization:** [Free / Paid / Freemium / Ads / IAP]
- **App Size Constraints:** [Target < 50MB / < 100MB / No limit]
- **Battery Considerations:** [Background tasks / Location tracking notes]
- **Accessibility:** [WCAG compliance / VoiceOver / TalkBack support]

---

## 13. Quick Start for Claude

When working on this project:
1. Follow the tech stack defined above
2. Use the file structure as guide (choose the appropriate mobile/web structure)
3. Implement features in milestone order
4. Follow coding standards
5. Always consider security (including mobile-specific concerns)
6. For mobile: Test on both emulators and real devices
7. For mobile: Follow Material Design guidelines for Android

Priority: [MVP features first / Speed / Code quality / All balanced]

### Mobile Development Quick Commands
**Capacitor/Ionic:**
```bash
npm install
ionic serve                    # Web preview
ionic cap add android          # Add Android platform
ionic cap sync                 # Sync web code
ionic cap run android          # Run on Android device
```

**React Native:**
```bash
npm install
npx react-native start         # Start Metro bundler
npx react-native run-android   # Run on Android
```

**Flutter:**
```bash
flutter pub get                # Install dependencies
flutter run                    # Run on connected device
flutter build apk              # Build Android APK
```

**Android Studio (Native Android):**
```bash
./gradlew assembleDebug       # Build debug APK
./gradlew installDebug        # Install on device
```
