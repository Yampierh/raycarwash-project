/**
 * frontend/src/screens/VehiclePhotosScreen.tsx
 *
 * Gallery for a single vehicle's photos (max 4). Tap the "+" tile to
 * pick from the library; the file is resized to 1600px max-edge,
 * uploaded via the two-step presigned flow, and the gallery refetches
 * on success. Long-press a photo to delete.
 *
 * Route: VehiclePhotos { vehicleId, vehicleLabel? }
 *
 * Reuses the same ImagePicker → ImageManipulator → uriToBlob chain that
 * AvatarPicker uses — only the upload target changes.
 */
import { Ionicons } from "@expo/vector-icons";
import * as ImageManipulator from "expo-image-manipulator";
import * as ImagePicker from "expo-image-picker";
import React, { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Image,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import EmptyState from "../components/EmptyState";
import {
  useDeleteVehiclePhoto,
  useUploadVehiclePhoto,
  useVehiclePhotos,
} from "../hooks/useProfileResources";
import { ApiError } from "../lib/api-error";
import { uriToBlob } from "../services/s3-uploader";
import type { VehiclePhoto } from "../services/vehicle-photos.service";
import { Colors } from "../theme/colors";

const MAX_DIMENSION_PX = 1600;
const MAX_BYTES = 8 * 1024 * 1024; // matches backend per-photo cap
const MAX_PHOTOS = 4;
const ALLOWED_MIME = new Set(["image/jpeg", "image/png", "image/webp"]);

function inferMimeFromUri(uri: string): string {
  const ext = uri.split(".").pop()?.toLowerCase() ?? "";
  if (ext === "png") return "image/png";
  if (ext === "webp") return "image/webp";
  return "image/jpeg";
}

export default function VehiclePhotosScreen({ navigation, route }: any) {
  const vehicleId: string = route.params?.vehicleId;
  const vehicleLabel: string | undefined = route.params?.vehicleLabel;

  const query = useVehiclePhotos(vehicleId);
  const upload = useUploadVehiclePhoto(vehicleId);
  const remove = useDeleteVehiclePhoto(vehicleId);
  const [uploading, setUploading] = useState(false);

  const photos = query.data ?? [];
  const remaining = MAX_PHOTOS - photos.length;

  const pickAndUpload = async () => {
    if (uploading) return;
    if (remaining <= 0) {
      Alert.alert(
        "Photo limit reached",
        `You can store up to ${MAX_PHOTOS} photos per vehicle. Remove one to add another.`,
      );
      return;
    }

    try {
      const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!perm.granted) {
        Alert.alert(
          "Permission needed",
          "Allow photo library access to add vehicle photos.",
        );
        return;
      }

      const picked = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        quality: 0.85,
      });
      if (picked.canceled || picked.assets.length === 0) return;

      const asset = picked.assets[0];
      let workingUri = asset.uri;
      let mimeType = asset.mimeType ?? inferMimeFromUri(workingUri);

      if (
        (asset.width ?? 0) > MAX_DIMENSION_PX ||
        (asset.height ?? 0) > MAX_DIMENSION_PX
      ) {
        const resized = await ImageManipulator.manipulateAsync(
          workingUri,
          [{ resize: { width: MAX_DIMENSION_PX } }],
          { compress: 0.85, format: ImageManipulator.SaveFormat.JPEG },
        );
        workingUri = resized.uri;
        mimeType = "image/jpeg";
      }

      const blob = await uriToBlob(workingUri);
      if (blob.size > MAX_BYTES) {
        Alert.alert("Image too large", "Please choose a photo under 8 MB.");
        return;
      }
      if (!ALLOWED_MIME.has(mimeType)) {
        mimeType = "image/jpeg";
      }

      setUploading(true);
      await upload.mutateAsync({
        blob,
        mimeType,
        sizeBytes: blob.size,
      });
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : (err as Error)?.message ?? "Could not upload the photo.";
      Alert.alert("Upload failed", message);
    } finally {
      setUploading(false);
    }
  };

  const confirmDelete = (photo: VehiclePhoto) => {
    Alert.alert("Remove photo?", "This cannot be undone.", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Remove",
        style: "destructive",
        onPress: () =>
          remove.mutate(photo.id, {
            onError: () =>
              Alert.alert("Could not remove", "Please try again."),
          }),
      },
    ]);
  };

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          style={styles.backBtn}
          hitSlop={12}
        >
          <Ionicons name="chevron-back" size={24} color={Colors.text} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>
          {vehicleLabel ? `${vehicleLabel} photos` : "Photos"}
        </Text>
        <View style={{ width: 32 }} />
      </View>

      {query.isLoading ? (
        <View style={styles.center}>
          <ActivityIndicator color={Colors.primary} />
        </View>
      ) : (
        <FlatList
          contentContainerStyle={styles.list}
          data={photos}
          numColumns={2}
          keyExtractor={(item) => item.id}
          columnWrapperStyle={{ gap: 12 }}
          ListHeaderComponent={
            <View style={styles.headerHint}>
              <Text style={styles.hint}>
                Up to {MAX_PHOTOS} photos per vehicle. {remaining} remaining.
              </Text>
            </View>
          }
          renderItem={({ item }) => (
            <TouchableOpacity
              style={styles.tile}
              onLongPress={() => confirmDelete(item)}
              activeOpacity={0.9}
            >
              {item.photo_url ? (
                <Image source={{ uri: item.photo_url }} style={styles.tileImage} />
              ) : (
                <View style={[styles.tileImage, styles.tilePlaceholder]}>
                  <Ionicons name="image-outline" size={28} color="#475569" />
                </View>
              )}
              {item.caption ? (
                <Text style={styles.caption} numberOfLines={1}>
                  {item.caption}
                </Text>
              ) : null}
            </TouchableOpacity>
          )}
          ListFooterComponent={
            remaining > 0 ? (
              <TouchableOpacity
                style={[styles.tile, styles.addTile, photos.length === 0 && styles.addTileFull]}
                onPress={pickAndUpload}
                disabled={uploading}
              >
                {uploading ? (
                  <ActivityIndicator color={Colors.primary} />
                ) : (
                  <>
                    <Ionicons name="add" size={32} color={Colors.primary} />
                    <Text style={styles.addText}>Add photo</Text>
                  </>
                )}
              </TouchableOpacity>
            ) : null
          }
          ListEmptyComponent={
            !uploading ? (
              <EmptyState
                icon="image-multiple-outline"
                title="No photos yet"
                subtitle="Add up to 4 photos so detailers can see what they're working with."
                action={{ label: "Add photo", onPress: pickAndUpload }}
                style={{ marginTop: 24 }}
              />
            ) : null
          }
        />
      )}
    </SafeAreaView>
  );
}

const TILE_SIZE = 160;

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.background },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  backBtn: { padding: 4 },
  headerTitle: {
    flex: 1,
    color: Colors.text,
    fontSize: 18,
    fontWeight: "600",
    textAlign: "center",
  },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  list: { padding: 16, gap: 12 },
  headerHint: { marginBottom: 12 },
  hint: { color: Colors.secondaryText, fontSize: 12 },
  tile: {
    width: TILE_SIZE,
    marginBottom: 12,
  },
  tileImage: {
    width: TILE_SIZE,
    height: TILE_SIZE,
    borderRadius: 12,
    backgroundColor: Colors.card,
  },
  tilePlaceholder: {
    alignItems: "center",
    justifyContent: "center",
  },
  caption: { color: Colors.secondaryText, fontSize: 12, marginTop: 6 },
  addTile: {
    height: TILE_SIZE,
    backgroundColor: Colors.card,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#1E293B",
    borderStyle: "dashed",
    alignItems: "center",
    justifyContent: "center",
    marginTop: 0,
  },
  addTileFull: { width: "100%" },
  addText: { color: Colors.primary, marginTop: 6, fontSize: 13, fontWeight: "500" },
});
