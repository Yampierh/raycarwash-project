import { apiClient } from "./api";

export type DevicePlatform = "ios" | "android" | "web";

export const notificationService = {
  registerToken: (token: string, platform: DevicePlatform) =>
    apiClient.post("/api/v1/notifications/device-token", { token, platform }),

  unregisterToken: (token: string, platform: DevicePlatform) =>
    apiClient.delete("/api/v1/notifications/device-token", {
      data: { token, platform },
    }),
};
