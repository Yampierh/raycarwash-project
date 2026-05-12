/**
 * usePushNotifications
 *
 * Requests permission, obtains the Expo push token, registers it with the
 * backend, and sets up foreground notification + response handlers.
 *
 * Call once at app root after the user is authenticated.
 * On logout, call the returned `unregister()` helper.
 */
import { useEffect, useRef, useCallback } from "react";
import * as Notifications from "expo-notifications";
import * as Device from "expo-device";
import { Platform } from "react-native";
import { notificationService, DevicePlatform } from "../services/notification.service";
import { savePushToken, removePushToken } from "../utils/storage";

// Show notifications as banners even when the app is in the foreground
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge:  true,
    shouldShowBanner: true,
    shouldShowList:   true,
  }),
});

export interface UsePushNotificationsResult {
  /** Call on logout to remove the device token from the backend */
  unregister: () => Promise<void>;
}

export function usePushNotifications(
  onNotificationTapped?: (notification: Notifications.Notification) => void
): UsePushNotificationsResult {
  const tokenRef        = useRef<string | null>(null);
  const platformRef     = useRef<DevicePlatform>("ios");
  const responseListenerRef = useRef<Notifications.EventSubscription | null>(null);
  const receivedListenerRef = useRef<Notifications.EventSubscription | null>(null);

  useEffect(() => {
    let mounted = true;

    async function setup() {
      // Physical device required for real push tokens
      if (!Device.isDevice) return;

      const { status: existing } = await Notifications.getPermissionsAsync();
      let finalStatus = existing;

      if (existing !== "granted") {
        const { status } = await Notifications.requestPermissionsAsync();
        finalStatus = status;
      }

      if (finalStatus !== "granted") return;

      // Android requires a notification channel
      if (Platform.OS === "android") {
        await Notifications.setNotificationChannelAsync("default", {
          name: "Default",
          importance: Notifications.AndroidImportance.MAX,
          vibrationPattern: [0, 250, 250, 250],
          lightColor: "#1D4ED8",
        });
      }

      try {
        const tokenData = await Notifications.getExpoPushTokenAsync();
        if (!mounted) return;

        const token    = tokenData.data;
        const platform = (Platform.OS as DevicePlatform) ?? "ios";
        tokenRef.current    = token;
        platformRef.current = platform;

        await notificationService.registerToken(token, platform);
        await savePushToken(token);
      } catch {
        // Token registration failure must not crash the app
      }

      // Foreground notification listener (app is open)
      receivedListenerRef.current = Notifications.addNotificationReceivedListener(
        (_notification) => {
          // Badge / in-app banner handled by setNotificationHandler above
        }
      );

      // Tap listener — navigate to relevant screen
      responseListenerRef.current = Notifications.addNotificationResponseReceivedListener(
        (response) => {
          if (onNotificationTapped) {
            onNotificationTapped(response.notification);
          }
        }
      );
    }

    setup();

    return () => {
      mounted = false;
      receivedListenerRef.current?.remove();
      responseListenerRef.current?.remove();
    };
  }, [onNotificationTapped]);

  const unregister = useCallback(async () => {
    const token    = tokenRef.current;
    const platform = platformRef.current;
    if (!token) return;
    try {
      await notificationService.unregisterToken(token, platform);
      await removePushToken();
    } catch {
      // Best-effort on logout
    }
    tokenRef.current = null;
  }, []);

  return { unregister };
}
