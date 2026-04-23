/**
 * OAuth Client IDs
 *
 * Google setup:
 *  1. Go to https://console.cloud.google.com/apis/credentials
 *  2. Create an OAuth 2.0 client for each platform (Web, iOS, Android)
 *  3. Under "Authorized redirect URIs" for iOS/Android, add:
 *       raycarwash://
 *  4. For Expo Go dev, also add:
 *       exp://localhost:8081
 *  5. For the Expo auth proxy (managed workflow), also add:
 *       https://auth.expo.io/@YOUR_EXPO_USERNAME/raycarwash-app
 *     Then add the same URI to GOOGLE_ALLOWED_REDIRECT_URIS in backend config.py.
 *
 * Apple:
 *  - Configured automatically via expo-apple-authentication.
 *  - Enable "Sign In with Apple" in your App ID at https://developer.apple.com.
 */

export const GOOGLE_CLIENT_IDS = {
  web:     "",  // e.g. "123456789-abc.apps.googleusercontent.com"
  ios:     "",  // e.g. "123456789-xyz.apps.googleusercontent.com"
  android: "",  // e.g. "123456789-def.apps.googleusercontent.com"
};

/**
 * App scheme used in custom URI deep links.
 * Matches the "scheme" field in app.json.
 */
export const APP_SCHEME = "raycarwash";

/**
 * Expo slug — used to construct the Expo auth proxy URL.
 * Matches "slug" in app.json.
 */
export const EXPO_SLUG = "raycarwash-app";
