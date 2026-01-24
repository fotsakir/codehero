# Capacitor/Ionic Development Context

## Security Patterns

### Secure Storage

```typescript
import { Preferences } from '@capacitor/preferences';
// For sensitive data, use a secure storage plugin
import { SecureStoragePlugin } from 'capacitor-secure-storage-plugin';

// Regular storage (NOT for sensitive data)
class StorageService {
  async set(key: string, value: string): Promise<void> {
    await Preferences.set({ key, value });
  }

  async get(key: string): Promise<string | null> {
    const { value } = await Preferences.get({ key });
    return value;
  }

  async remove(key: string): Promise<void> {
    await Preferences.remove({ key });
  }
}

// Secure storage (for tokens, credentials)
class SecureStorageService {
  async saveToken(token: string): Promise<void> {
    await SecureStoragePlugin.set({ key: 'auth_token', value: token });
  }

  async getToken(): Promise<string | null> {
    try {
      const { value } = await SecureStoragePlugin.get({ key: 'auth_token' });
      return value;
    } catch {
      return null;
    }
  }

  async clearToken(): Promise<void> {
    try {
      await SecureStoragePlugin.remove({ key: 'auth_token' });
    } catch {
      // Key might not exist
    }
  }
}
```

### API Security

```typescript
// NEVER expose secrets in frontend code
// BAD: const API_KEY = "sk-12345"; // Bundled in app!

// Use environment variables (build-time only)
const API_URL = import.meta.env.VITE_API_URL || 'https://api.example.com';

// For sensitive operations, always use your backend
class ApiService {
  private baseUrl = API_URL;
  private secureStorage = new SecureStorageService();

  async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = await this.secureStorage.getToken();

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
        ...options.headers,
      },
    });

    if (!response.ok) {
      if (response.status === 401) {
        await this.secureStorage.clearToken();
        // Redirect to login
      }
      throw new ApiError(response.status, await response.text());
    }

    return response.json();
  }
}
```

### Input Validation

```typescript
interface ValidationResult {
  valid: boolean;
  error?: string;
}

const Validators = {
  email(value: string): ValidationResult {
    if (!value?.trim()) {
      return { valid: false, error: 'Email is required' };
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(value)) {
      return { valid: false, error: 'Invalid email format' };
    }
    return { valid: true };
  },

  password(value: string, minLength = 8): ValidationResult {
    if (!value) {
      return { valid: false, error: 'Password is required' };
    }
    if (value.length < minLength) {
      return { valid: false, error: `Password must be at least ${minLength} characters` };
    }
    return { valid: true };
  },

  required(value: string, fieldName: string): ValidationResult {
    if (!value?.trim()) {
      return { valid: false, error: `${fieldName} is required` };
    }
    return { valid: true };
  },
};

// Sanitize user input
function sanitizeHtml(input: string): string {
  const div = document.createElement('div');
  div.textContent = input;
  return div.innerHTML;
}
```

### Deep Link Security

```typescript
import { App, URLOpenListenerEvent } from '@capacitor/app';

// Validate deep links before processing
App.addListener('appUrlOpen', (event: URLOpenListenerEvent) => {
  const url = new URL(event.url);

  // Only accept links from trusted schemes
  const trustedSchemes = ['myapp', 'https'];
  if (!trustedSchemes.includes(url.protocol.replace(':', ''))) {
    console.warn('Untrusted deep link scheme');
    return;
  }

  // Validate and sanitize path
  const path = url.pathname;
  const allowedPaths = ['/login', '/reset-password', '/verify'];

  if (!allowedPaths.some(p => path.startsWith(p))) {
    console.warn('Invalid deep link path');
    return;
  }

  // Process the deep link
  handleDeepLink(path, url.searchParams);
});
```

---

## Project Structure

```
src/
├── app/
│   ├── core/
│   │   ├── services/
│   │   │   ├── api.service.ts
│   │   │   ├── auth.service.ts
│   │   │   └── storage.service.ts
│   │   ├── guards/
│   │   │   └── auth.guard.ts
│   │   └── interceptors/
│   ├── shared/
│   │   ├── components/
│   │   ├── directives/
│   │   └── pipes/
│   ├── features/
│   │   ├── auth/
│   │   │   ├── login/
│   │   │   └── register/
│   │   ├── home/
│   │   └── profile/
│   └── app.component.ts
├── assets/
├── environments/
│   ├── environment.ts
│   └── environment.prod.ts
└── main.ts
```

---

## Capacitor Configuration

```typescript
// capacitor.config.ts
import { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.example.myapp',
  appName: 'My App',
  webDir: 'www',
  server: {
    androidScheme: 'https', // Use HTTPS for Android WebView
    iosScheme: 'capacitor', // iOS uses capacitor:// by default
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 2000,
      backgroundColor: '#ffffff',
      showSpinner: false,
    },
    PushNotifications: {
      presentationOptions: ['badge', 'sound', 'alert'],
    },
    Keyboard: {
      resize: 'body',
      resizeOnFullScreen: true,
    },
  },
  // iOS specific
  ios: {
    contentInset: 'automatic',
    allowsLinkPreview: false,
  },
  // Android specific
  android: {
    allowMixedContent: false, // Security: don't allow HTTP content
    captureInput: true,
    webContentsDebuggingEnabled: false, // Disable in production!
  },
};

export default config;
```

---

## Native Plugins

### Camera

```typescript
import { Camera, CameraResultType, CameraSource } from '@capacitor/camera';

async function takePhoto(): Promise<string | null> {
  try {
    const image = await Camera.getPhoto({
      quality: 80,
      allowEditing: false,
      resultType: CameraResultType.Base64,
      source: CameraSource.Camera,
      width: 1024,
      height: 1024,
    });

    return image.base64String || null;
  } catch (error) {
    if ((error as Error).message === 'User cancelled photos app') {
      return null;
    }
    throw error;
  }
}

async function pickFromGallery(): Promise<string | null> {
  try {
    const image = await Camera.getPhoto({
      quality: 80,
      resultType: CameraResultType.Base64,
      source: CameraSource.Photos,
    });

    return image.base64String || null;
  } catch (error) {
    return null;
  }
}
```

### Geolocation

```typescript
import { Geolocation, Position } from '@capacitor/geolocation';

async function getCurrentPosition(): Promise<Position | null> {
  try {
    // Check permissions first
    const permissions = await Geolocation.checkPermissions();

    if (permissions.location !== 'granted') {
      const request = await Geolocation.requestPermissions();
      if (request.location !== 'granted') {
        throw new Error('Location permission denied');
      }
    }

    const position = await Geolocation.getCurrentPosition({
      enableHighAccuracy: true,
      timeout: 10000,
    });

    return position;
  } catch (error) {
    console.error('Error getting location:', error);
    return null;
  }
}

// Watch position changes
function watchPosition(callback: (position: Position) => void): string {
  const watchId = Geolocation.watchPosition(
    { enableHighAccuracy: true },
    (position, error) => {
      if (position) {
        callback(position);
      }
    }
  );

  return watchId;
}

function stopWatching(watchId: string): void {
  Geolocation.clearWatch({ id: watchId });
}
```

### Push Notifications

```typescript
import { PushNotifications, Token, PushNotificationSchema } from '@capacitor/push-notifications';
import { Capacitor } from '@capacitor/core';

class PushNotificationService {
  async initialize(): Promise<void> {
    if (!Capacitor.isNativePlatform()) {
      console.log('Push notifications not available on web');
      return;
    }

    // Request permission
    let permission = await PushNotifications.checkPermissions();

    if (permission.receive === 'prompt') {
      permission = await PushNotifications.requestPermissions();
    }

    if (permission.receive !== 'granted') {
      console.log('Push notification permission denied');
      return;
    }

    // Register with APNs/FCM
    await PushNotifications.register();

    // Listen for registration
    PushNotifications.addListener('registration', (token: Token) => {
      console.log('Push registration success:', token.value);
      this.sendTokenToServer(token.value);
    });

    // Listen for registration errors
    PushNotifications.addListener('registrationError', (error) => {
      console.error('Push registration error:', error);
    });

    // Listen for push notifications
    PushNotifications.addListener('pushNotificationReceived', (notification: PushNotificationSchema) => {
      console.log('Push notification received:', notification);
      this.handleNotification(notification);
    });

    // Listen for notification actions
    PushNotifications.addListener('pushNotificationActionPerformed', (action) => {
      console.log('Push notification action:', action);
      this.handleNotificationAction(action);
    });
  }

  private async sendTokenToServer(token: string): Promise<void> {
    // Send token to your backend
    await api.post('/devices/register', { token, platform: Capacitor.getPlatform() });
  }

  private handleNotification(notification: PushNotificationSchema): void {
    // Handle foreground notification
  }

  private handleNotificationAction(action: any): void {
    // Handle notification tap
  }
}
```

### Biometric Authentication

```typescript
import { NativeBiometric, BiometryType } from 'capacitor-native-biometric';

class BiometricService {
  async isAvailable(): Promise<boolean> {
    try {
      const result = await NativeBiometric.isAvailable();
      return result.isAvailable;
    } catch {
      return false;
    }
  }

  async getBiometryType(): Promise<BiometryType> {
    const result = await NativeBiometric.isAvailable();
    return result.biometryType;
  }

  async authenticate(reason: string): Promise<boolean> {
    try {
      await NativeBiometric.verifyIdentity({
        reason,
        title: 'Authentication Required',
        subtitle: 'Verify your identity',
        description: reason,
      });
      return true;
    } catch {
      return false;
    }
  }

  // Store credentials securely with biometric protection
  async saveCredentials(username: string, password: string): Promise<void> {
    await NativeBiometric.setCredentials({
      username,
      password,
      server: 'com.example.myapp',
    });
  }

  async getCredentials(): Promise<{ username: string; password: string } | null> {
    try {
      const credentials = await NativeBiometric.getCredentials({
        server: 'com.example.myapp',
      });
      return credentials;
    } catch {
      return null;
    }
  }
}
```

---

## Platform Detection

```typescript
import { Capacitor } from '@capacitor/core';
import { Device } from '@capacitor/device';

class PlatformService {
  isNative(): boolean {
    return Capacitor.isNativePlatform();
  }

  isIOS(): boolean {
    return Capacitor.getPlatform() === 'ios';
  }

  isAndroid(): boolean {
    return Capacitor.getPlatform() === 'android';
  }

  isWeb(): boolean {
    return Capacitor.getPlatform() === 'web';
  }

  async getDeviceInfo() {
    const info = await Device.getInfo();
    return {
      platform: info.platform,
      model: info.model,
      osVersion: info.osVersion,
      manufacturer: info.manufacturer,
      isVirtual: info.isVirtual,
    };
  }

  async getDeviceId(): Promise<string> {
    const { identifier } = await Device.getId();
    return identifier;
  }
}

// Platform-specific code
function doSomething() {
  if (Capacitor.getPlatform() === 'ios') {
    // iOS-specific code
  } else if (Capacitor.getPlatform() === 'android') {
    // Android-specific code
  } else {
    // Web fallback
  }
}
```

---

## Ionic Components (Angular)

### Page Component

```typescript
import { Component, OnInit, OnDestroy } from '@angular/core';
import { IonicModule, LoadingController, ToastController, AlertController } from '@ionic/angular';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [IonicModule, CommonModule, FormsModule],
  template: `
    <ion-header>
      <ion-toolbar>
        <ion-title>Home</ion-title>
        <ion-buttons slot="end">
          <ion-button (click)="openSettings()">
            <ion-icon name="settings-outline"></ion-icon>
          </ion-button>
        </ion-buttons>
      </ion-toolbar>
    </ion-header>

    <ion-content>
      <ion-refresher slot="fixed" (ionRefresh)="handleRefresh($event)">
        <ion-refresher-content></ion-refresher-content>
      </ion-refresher>

      <ion-list>
        <ion-item *ngFor="let item of items" (click)="openItem(item)">
          <ion-avatar slot="start">
            <img [src]="item.avatar" [alt]="item.name">
          </ion-avatar>
          <ion-label>
            <h2>{{ item.name }}</h2>
            <p>{{ item.description }}</p>
          </ion-label>
          <ion-badge slot="end" [color]="item.status === 'active' ? 'success' : 'medium'">
            {{ item.status }}
          </ion-badge>
        </ion-item>
      </ion-list>

      <ion-infinite-scroll (ionInfinite)="loadMore($event)">
        <ion-infinite-scroll-content></ion-infinite-scroll-content>
      </ion-infinite-scroll>
    </ion-content>

    <ion-fab vertical="bottom" horizontal="end" slot="fixed">
      <ion-fab-button (click)="addItem()">
        <ion-icon name="add"></ion-icon>
      </ion-fab-button>
    </ion-fab>
  `,
})
export class HomePage implements OnInit, OnDestroy {
  items: Item[] = [];
  private destroy$ = new Subject<void>();

  constructor(
    private loadingCtrl: LoadingController,
    private toastCtrl: ToastController,
    private alertCtrl: AlertController,
    private dataService: DataService
  ) {}

  ngOnInit() {
    this.loadItems();
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }

  async loadItems() {
    const loading = await this.loadingCtrl.create({ message: 'Loading...' });
    await loading.present();

    try {
      this.items = await this.dataService.getItems();
    } catch (error) {
      await this.showToast('Failed to load items', 'danger');
    } finally {
      await loading.dismiss();
    }
  }

  async handleRefresh(event: any) {
    try {
      this.items = await this.dataService.getItems();
    } finally {
      event.target.complete();
    }
  }

  async loadMore(event: any) {
    const newItems = await this.dataService.getMoreItems(this.items.length);
    this.items.push(...newItems);

    if (newItems.length === 0) {
      event.target.disabled = true;
    }
    event.target.complete();
  }

  async addItem() {
    const alert = await this.alertCtrl.create({
      header: 'Add Item',
      inputs: [
        { name: 'name', type: 'text', placeholder: 'Name' },
        { name: 'description', type: 'textarea', placeholder: 'Description' },
      ],
      buttons: [
        { text: 'Cancel', role: 'cancel' },
        {
          text: 'Add',
          handler: async (data) => {
            await this.dataService.addItem(data);
            await this.loadItems();
          },
        },
      ],
    });
    await alert.present();
  }

  private async showToast(message: string, color: string = 'primary') {
    const toast = await this.toastCtrl.create({
      message,
      duration: 3000,
      color,
      position: 'bottom',
    });
    await toast.present();
  }
}
```

### Auth Guard

```typescript
import { Injectable, inject } from '@angular/core';
import { CanActivate, Router, UrlTree } from '@angular/router';
import { AuthService } from '../services/auth.service';

@Injectable({ providedIn: 'root' })
export class AuthGuard implements CanActivate {
  private authService = inject(AuthService);
  private router = inject(Router);

  async canActivate(): Promise<boolean | UrlTree> {
    const isAuthenticated = await this.authService.isAuthenticated();

    if (isAuthenticated) {
      return true;
    }

    return this.router.createUrlTree(['/login']);
  }
}

// Usage in routes
const routes: Routes = [
  { path: 'login', component: LoginPage },
  {
    path: 'home',
    component: HomePage,
    canActivate: [AuthGuard],
  },
  {
    path: 'profile',
    loadComponent: () => import('./profile/profile.page').then(m => m.ProfilePage),
    canActivate: [AuthGuard],
  },
];
```

---

## Ionic Components (React)

```tsx
import {
  IonContent,
  IonHeader,
  IonPage,
  IonTitle,
  IonToolbar,
  IonList,
  IonItem,
  IonLabel,
  IonButton,
  IonInput,
  IonLoading,
  IonToast,
  useIonLoading,
  useIonToast,
} from '@ionic/react';
import { useState } from 'react';

const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [present, dismiss] = useIonLoading();
  const [presentToast] = useIonToast();

  const handleLogin = async () => {
    // Validate
    if (!email || !password) {
      presentToast({
        message: 'Please fill in all fields',
        duration: 2000,
        color: 'danger',
      });
      return;
    }

    await present({ message: 'Logging in...' });

    try {
      await authService.login(email, password);
      // Navigate to home
    } catch (error) {
      presentToast({
        message: 'Login failed',
        duration: 3000,
        color: 'danger',
      });
    } finally {
      await dismiss();
    }
  };

  return (
    <IonPage>
      <IonHeader>
        <IonToolbar>
          <IonTitle>Login</IonTitle>
        </IonToolbar>
      </IonHeader>

      <IonContent className="ion-padding">
        <IonList>
          <IonItem>
            <IonInput
              type="email"
              label="Email"
              labelPlacement="floating"
              value={email}
              onIonChange={(e) => setEmail(e.detail.value || '')}
            />
          </IonItem>

          <IonItem>
            <IonInput
              type="password"
              label="Password"
              labelPlacement="floating"
              value={password}
              onIonChange={(e) => setPassword(e.detail.value || '')}
            />
          </IonItem>
        </IonList>

        <IonButton expand="block" onClick={handleLogin} className="ion-margin-top">
          Login
        </IonButton>
      </IonContent>
    </IonPage>
  );
};

export default LoginPage;
```

---

## App Lifecycle

```typescript
import { App } from '@capacitor/app';
import { SplashScreen } from '@capacitor/splash-screen';

class AppLifecycleService {
  initialize() {
    // App state changes
    App.addListener('appStateChange', ({ isActive }) => {
      if (isActive) {
        console.log('App became active');
        this.onResume();
      } else {
        console.log('App went to background');
        this.onPause();
      }
    });

    // Back button (Android)
    App.addListener('backButton', ({ canGoBack }) => {
      if (canGoBack) {
        window.history.back();
      } else {
        // Show exit confirmation or minimize app
        App.minimizeApp();
      }
    });

    // Hide splash screen when ready
    SplashScreen.hide();
  }

  private onResume() {
    // Refresh data, check auth status, etc.
  }

  private onPause() {
    // Save state, pause media, etc.
  }
}
```

---

## Network Handling

```typescript
import { Network, ConnectionStatus } from '@capacitor/network';

class NetworkService {
  private listeners: ((status: ConnectionStatus) => void)[] = [];

  async initialize() {
    // Check current status
    const status = await Network.getStatus();
    console.log('Network status:', status);

    // Listen for changes
    Network.addListener('networkStatusChange', (status) => {
      console.log('Network status changed:', status);
      this.notifyListeners(status);
    });
  }

  async isOnline(): Promise<boolean> {
    const status = await Network.getStatus();
    return status.connected;
  }

  onStatusChange(callback: (status: ConnectionStatus) => void) {
    this.listeners.push(callback);
  }

  private notifyListeners(status: ConnectionStatus) {
    this.listeners.forEach((listener) => listener(status));
  }
}

// Usage with offline handling
async function fetchWithOfflineSupport<T>(endpoint: string): Promise<T> {
  const isOnline = await networkService.isOnline();

  if (!isOnline) {
    // Return cached data
    const cached = await storageService.get(`cache_${endpoint}`);
    if (cached) {
      return JSON.parse(cached);
    }
    throw new Error('No internet connection and no cached data');
  }

  const data = await api.get<T>(endpoint);

  // Cache for offline use
  await storageService.set(`cache_${endpoint}`, JSON.stringify(data));

  return data;
}
```

---

## Building & Deployment

### Environment Configuration

```typescript
// environments/environment.ts (development)
export const environment = {
  production: false,
  apiUrl: 'http://localhost:3000/api',
  debug: true,
};

// environments/environment.prod.ts (production)
export const environment = {
  production: true,
  apiUrl: 'https://api.example.com',
  debug: false,
};
```

### Build Commands

```bash
# Build web app
npm run build

# Sync with native projects
npx cap sync

# Build iOS (requires Mac)
npx cap open ios
# Then build in Xcode

# Build Android
npx cap open android
# Then build in Android Studio

# Live reload during development
ionic cap run ios -l --external
ionic cap run android -l --external
```

### App Store Preparation

```typescript
// Check before submission
const preSubmissionChecklist = {
  // iOS
  ios: [
    'App icons in all required sizes',
    'Launch screen configured',
    'Info.plist permissions descriptions',
    'Provisioning profile and certificates',
    'App Transport Security configured',
  ],
  // Android
  android: [
    'App icons and adaptive icons',
    'Splash screen configured',
    'AndroidManifest.xml permissions',
    'Signed release APK/AAB',
    'ProGuard rules (if using)',
  ],
};
```

---

## Testing

```typescript
// Unit test example (Jest)
describe('AuthService', () => {
  let service: AuthService;
  let mockStorage: jest.Mocked<SecureStorageService>;

  beforeEach(() => {
    mockStorage = {
      saveToken: jest.fn(),
      getToken: jest.fn(),
      clearToken: jest.fn(),
    } as any;

    service = new AuthService(mockStorage);
  });

  it('should store token on successful login', async () => {
    const mockResponse = { token: 'test-token', user: { id: '1', email: 'test@test.com' } };
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    await service.login('test@test.com', 'password');

    expect(mockStorage.saveToken).toHaveBeenCalledWith('test-token');
  });

  it('should clear token on logout', async () => {
    await service.logout();

    expect(mockStorage.clearToken).toHaveBeenCalled();
  });
});

// E2E test with Cypress
describe('Login Flow', () => {
  it('should login successfully', () => {
    cy.visit('/login');
    cy.get('ion-input[type="email"] input').type('test@example.com');
    cy.get('ion-input[type="password"] input').type('password123');
    cy.get('ion-button').contains('Login').click();
    cy.url().should('include', '/home');
  });
});
```
