/**
 * OAuth Client IDs
 *
 * Google:
 *  1. Go to https://console.cloud.google.com/apis/credentials
 *  2. Create an OAuth 2.0 client for each platform (Web, iOS, Android)
 *  3. Add "raycarwash://" as an authorized redirect URI for iOS/Android
 *  4. For Expo Go, also add "https://auth.expo.io/@<your-expo-username>/raycarwash-app"
 *
 * Apple:
 *  - Configured automatically via expo-apple-authentication (requires Apple Developer account)
 *  - Enable "Sign In with Apple" in your App ID at https://developer.apple.com
 */
export const GOOGLE_CLIENT_IDS = {
  web: "",      // e.g. "123456789-abc.apps.googleusercontent.com"
  ios: "",      // e.g. "123456789-xyz.apps.googleusercontent.com"
  android: "",  // e.g. "123456789-def.apps.googleusercontent.com"
};
