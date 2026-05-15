/**
 * frontend/src/components/AvatarPicker.tsx
 *
 * Press the avatar → ImagePicker → optional resize → upload-url → upload
 * → confirm → onChange(newUrl). The component owns the upload lifecycle
 * (loading spinner, error alert) so screens just consume the callback.
 *
 * `currentUrl` shows the existing avatar if any; otherwise the component
 * falls back to the user's initials. `fullName` is only used to derive
 * those initials.
 *
 * The picker requests permission lazily on first press. If denied, we
 * surface a clear Alert instead of crashing.
 */
import { Ionicons } from "@expo/vector-icons";
import * as ImageManipulator from "expo-image-manipulator";
import * as ImagePicker from "expo-image-picker";
import React, { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Image,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { useQueryClient } from "@tanstack/react-query";
import { Colors } from "../theme/colors";
import { ApiError } from "../lib/api-error";
import { uploadAvatar } from "../services/avatar.service";

const MAX_DIMENSION_PX = 1024;
const MAX_BYTES = 5 * 1024 * 1024;
const ALLOWED_MIME = new Set(["image/jpeg", "image/png", "image/webp"]);

export interface AvatarPickerProps {
  /** Signed URL of the current avatar, if any. */
  currentUrl: string | null | undefined;
  /** Display name used to derive initials when there's no avatar. */
  fullName: string | null | undefined;
  /** Called after a successful upload + confirm, with the new signed URL. */
  onChange?: (newAvatarUrl: string) => void;
  /** Diameter of the avatar in points. Defaults to 90 (mobile profile screens). */
  size?: number;
}

function deriveInitials(fullName: string | null | undefined): string {
  if (!fullName) return "U";
  return fullName
    .split(" ")
    .filter(Boolean)
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function inferMimeFromUri(uri: string): string {
  const lower = uri.toLowerCase();
  if (lower.endsWith(".png")) return "image/png";
  if (lower.endsWith(".webp")) return "image/webp";
  return "image/jpeg";
}

export default function AvatarPicker({
  currentUrl,
  fullName,
  onChange,
  size = 90,
}: AvatarPickerProps) {
  const queryClient = useQueryClient();
  const [uploading, setUploading] = useState(false);
  const [optimisticUrl, setOptimisticUrl] = useState<string | null>(null);

  const displayUrl = optimisticUrl ?? currentUrl ?? null;
  const dimensionStyle = {
    width: size,
    height: size,
    borderRadius: size / 2,
  };
  const editBadgeSize = Math.max(28, Math.round(size / 3));

  async function handlePress() {
    if (uploading) return;

    try {
      const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!perm.granted) {
        Alert.alert(
          "Permission needed",
          "Allow photo library access to change your avatar.",
        );
        return;
      }

      const picked = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        aspect: [1, 1],
        quality: 0.85,
      });
      if (picked.canceled || picked.assets.length === 0) return;

      const asset = picked.assets[0];
      let workingUri = asset.uri;
      let mimeType = asset.mimeType ?? inferMimeFromUri(workingUri);

      // Resize when the source is bigger than the upload target (saves bandwidth
      // and keeps everyone under the 5 MB cap).
      if ((asset.width ?? 0) > MAX_DIMENSION_PX || (asset.height ?? 0) > MAX_DIMENSION_PX) {
        const resized = await ImageManipulator.manipulateAsync(
          workingUri,
          [{ resize: { width: MAX_DIMENSION_PX } }],
          { compress: 0.85, format: ImageManipulator.SaveFormat.JPEG },
        );
        workingUri = resized.uri;
        mimeType = "image/jpeg";
      }

      // Read the size for the upload-url request body.
      const blob = await (await fetch(workingUri)).blob();
      const sizeBytes = blob.size;
      if (sizeBytes > MAX_BYTES) {
        Alert.alert("Image too large", "Please choose a photo under 5 MB.");
        return;
      }
      if (!ALLOWED_MIME.has(mimeType)) {
        mimeType = "image/jpeg"; // re-encode fallback already applied if needed
      }

      // Optimistic preview while the upload runs.
      setOptimisticUrl(workingUri);
      setUploading(true);

      const newUrl = await uploadAvatar(workingUri, mimeType, sizeBytes);
      onChange?.(newUrl);
      // Tell every cached Hub variant to drop — next read pulls the new
      // avatar_url from the backend.
      queryClient.invalidateQueries({ queryKey: ["users", "me"] });
    } catch (err) {
      setOptimisticUrl(null);
      const message =
        err instanceof ApiError
          ? err.message
          : (err as Error)?.message ?? "Could not update your avatar.";
      Alert.alert("Upload failed", message);
    } finally {
      setUploading(false);
    }
  }

  return (
    <TouchableOpacity
      style={[styles.wrapper, dimensionStyle]}
      onPress={handlePress}
      activeOpacity={0.85}
      disabled={uploading}
    >
      {displayUrl ? (
        <Image
          source={{ uri: displayUrl }}
          style={[styles.image, dimensionStyle]}
          resizeMode="cover"
        />
      ) : (
        <View style={[styles.fallback, dimensionStyle]}>
          <Text style={[styles.fallbackText, { fontSize: Math.round(size / 2.7) }]}>
            {deriveInitials(fullName)}
          </Text>
        </View>
      )}

      <View
        style={[
          styles.editBadge,
          {
            width: editBadgeSize,
            height: editBadgeSize,
            borderRadius: editBadgeSize / 2,
            right: -2,
            bottom: -2,
          },
        ]}
      >
        {uploading ? (
          <ActivityIndicator size="small" color="white" />
        ) : (
          <Ionicons name="pencil" size={Math.round(editBadgeSize * 0.45)} color="white" />
        )}
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    position: "relative",
    alignSelf: "center",
  },
  image: {
    borderWidth: 3,
    borderColor: Colors.primary,
  },
  fallback: {
    backgroundColor: "#1E3A5F",
    borderWidth: 3,
    borderColor: Colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  fallbackText: {
    color: Colors.primary,
    fontWeight: "700",
  },
  editBadge: {
    position: "absolute",
    backgroundColor: Colors.primary,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 3,
    borderColor: "#161E2E",
  },
});
