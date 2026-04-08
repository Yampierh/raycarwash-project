/**
 * Central app configuration.
 * Swap apiBaseUrl via environment variable in production.
 */
export const APP_CONFIG = {
  apiBaseUrl: process.env.EXPO_PUBLIC_API_URL || "http://192.168.0.10:8000",
  supportEmail: "support@raycarwash.com",
  privacyUrl: "https://raycarwash.com/privacy",
  termsUrl: "https://raycarwash.com/terms",
  appStoreUrl: "",
  playStoreUrl: "",
  fallbackCoords: {
    lat: 41.1306,
    lng: -85.1289,
    address: "Fort Wayne, IN 46802",
  },
};
