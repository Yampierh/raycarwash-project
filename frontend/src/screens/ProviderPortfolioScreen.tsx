/**
 * frontend/src/screens/ProviderPortfolioScreen.tsx
 *
 * Detailer's public gallery (max 30 photos). Same upload pattern as
 * VehiclePhotosScreen: pick → resize to 1600px → presigned upload →
 * confirm. Long-press a tile to delete.
 *
 * Caption + tag entry happens in a tiny inline modal at confirm time
 * so the user can group photos as "before"/"after"/"hero" without an
 * additional edit screen.
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
  Modal,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import Button from "../components/Button";
import EmptyState from "../components/EmptyState";
import {
  useDeletePortfolioPhoto,
  usePortfolio,
  useUploadPortfolioPhoto,
} from "../hooks/useProviderResources";
import { ApiError } from "../lib/api-error";
import { uriToBlob } from "../services/s3-uploader";
import type { PortfolioPhoto } from "../services/provider-portfolio.service";
import { Colors } from "../theme/colors";

const MAX_DIMENSION_PX = 1600;
const MAX_BYTES = 8 * 1024 * 1024;
const MAX_PHOTOS = 30;
const ALLOWED_MIME = new Set(["image/jpeg", "image/png", "image/webp"]);

function inferMimeFromUri(uri: string): string {
  const ext = uri.split(".").pop()?.toLowerCase() ?? "";
  if (ext === "png") return "image/png";
  if (ext === "webp") return "image/webp";
  return "image/jpeg";
}

const TAG_PRESETS = ["hero", "before", "after"];

export default function ProviderPortfolioScreen({ navigation }: any) {
  const query = usePortfolio();
  const upload = useUploadPortfolioPhoto();
  const remove = useDeletePortfolioPhoto();
  const [uploading, setUploading] = useState(false);

  // Two-stage UI: pick the image first, then prompt for caption + tag.
  const [pending, setPending] = useState<{
    blob: Blob;
    mime: string;
    size: number;
  } | null>(null);
  const [caption, setCaption] = useState("");
  const [tag, setTag] = useState("");

  const photos = query.data ?? [];
  const remaining = MAX_PHOTOS - photos.length;

  const pick = async () => {
    if (uploading) return;
    if (remaining <= 0) {
      Alert.alert(
        "Portfolio full",
        `You can store up to ${MAX_PHOTOS} photos. Remove one to add another.`,
      );
      return;
    }

    try {
      const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!perm.granted) {
        Alert.alert(
          "Permission needed",
          "Allow photo library access to add portfolio photos.",
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

      // Stash and prompt for caption + tag.
      setPending({ blob, mime: mimeType, size: blob.size });
      setCaption("");
      setTag("");
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Could not prepare the photo.";
      Alert.alert("Could not prepare", message);
    }
  };

  const confirmUpload = async () => {
    if (!pending) return;
    setUploading(true);
    try {
      await upload.mutateAsync({
        blob: pending.blob,
        mimeType: pending.mime,
        sizeBytes: pending.size,
        caption: caption.trim() || undefined,
        tag: tag.trim() || undefined,
      });
      setPending(null);
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

  const confirmDelete = (photo: PortfolioPhoto) => {
    Alert.alert("Remove photo?", "This cannot be undone.", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Remove",
        style: "destructive",
        onPress: () =>
          remove.mutate(photo.id, {
            onError: () => Alert.alert("Could not remove", "Please try again."),
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
        <Text style={styles.headerTitle}>Portfolio</Text>
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
                Up to {MAX_PHOTOS} photos. {remaining} remaining.
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
              {item.tag ? (
                <View style={styles.tagPill}>
                  <Text style={styles.tagText}>{item.tag}</Text>
                </View>
              ) : null}
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
                onPress={pick}
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
            !uploading && remaining > 0 ? (
              <EmptyState
                icon="image-multiple-outline"
                title="No portfolio photos yet"
                subtitle="Showcase your best work — these appear on your public profile."
                action={{ label: "Add photo", onPress: pick }}
                style={{ marginTop: 24 }}
              />
            ) : null
          }
        />
      )}

      <Modal
        visible={pending !== null}
        animationType="slide"
        transparent
        onRequestClose={() => setPending(null)}
      >
        <View style={styles.modalBackdrop}>
          <View style={styles.modalBody}>
            <View style={styles.modalHead}>
              <Text style={styles.modalTitle}>Add to portfolio</Text>
              <TouchableOpacity onPress={() => setPending(null)} hitSlop={12}>
                <Ionicons name="close" size={22} color={Colors.text} />
              </TouchableOpacity>
            </View>

            <Text style={styles.fieldLabel}>CAPTION</Text>
            <TextInput
              style={styles.input}
              value={caption}
              onChangeText={setCaption}
              placeholder="Ceramic finish on 2022 Tesla Y"
              placeholderTextColor="#475569"
              maxLength={200}
            />

            <Text style={styles.fieldLabel}>TAG</Text>
            <View style={styles.tagRow}>
              {TAG_PRESETS.map((preset) => (
                <TouchableOpacity
                  key={preset}
                  style={[
                    styles.tagChip,
                    tag === preset && styles.tagChipActive,
                  ]}
                  onPress={() => setTag(tag === preset ? "" : preset)}
                >
                  <Text
                    style={[
                      styles.tagChipText,
                      tag === preset && styles.tagChipTextActive,
                    ]}
                  >
                    {preset}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
            <TextInput
              style={styles.input}
              value={tag}
              onChangeText={setTag}
              placeholder="Or a custom tag…"
              placeholderTextColor="#475569"
              maxLength={40}
            />

            <Button
              title="Upload"
              onPress={confirmUpload}
              loading={uploading}
              disabled={uploading}
              style={{ marginTop: 16 }}
            />
          </View>
        </View>
      </Modal>
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
  tile: { width: TILE_SIZE, marginBottom: 12, position: "relative" },
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
  tagPill: {
    position: "absolute",
    top: 8,
    left: 8,
    backgroundColor: "rgba(0,0,0,0.65)",
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 999,
  },
  tagText: { color: "#F1F5F9", fontSize: 10, fontWeight: "600", textTransform: "uppercase" },
  addTile: {
    height: TILE_SIZE,
    backgroundColor: Colors.card,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#1E293B",
    borderStyle: "dashed",
    alignItems: "center",
    justifyContent: "center",
  },
  addTileFull: { width: "100%" },
  addText: { color: Colors.primary, marginTop: 6, fontSize: 13, fontWeight: "500" },

  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.55)",
    justifyContent: "flex-end",
  },
  modalBody: {
    backgroundColor: Colors.card,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 20,
  },
  modalHead: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 12,
  },
  modalTitle: { color: Colors.text, fontSize: 18, fontWeight: "700" },
  fieldLabel: {
    color: Colors.secondaryText,
    fontSize: 11,
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: 0.5,
    marginTop: 12,
    marginBottom: 6,
  },
  input: {
    backgroundColor: "#111827",
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 12,
    color: Colors.text,
    borderWidth: 1,
    borderColor: "#1E293B",
    fontSize: 15,
  },
  tagRow: { flexDirection: "row", gap: 8, marginBottom: 8 },
  tagChip: {
    backgroundColor: "#1A2233",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 999,
  },
  tagChipActive: { backgroundColor: Colors.primary },
  tagChipText: { color: Colors.secondaryText, fontSize: 12, fontWeight: "500" },
  tagChipTextActive: { color: Colors.text },
});
