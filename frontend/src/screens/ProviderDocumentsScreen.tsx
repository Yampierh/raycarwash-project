/**
 * frontend/src/screens/ProviderDocumentsScreen.tsx
 *
 * KYC documents — insurance, business license, certifications, W-9.
 * Upload uses ImagePicker today (users can photograph paper copies);
 * adding a real PDF picker via expo-document-picker is a follow-up
 * once we confirm the dep is acceptable.
 *
 * Download URLs in the list payload are 1 h signed — tapping a doc
 * opens the URL in the system browser/viewer. Delete is step-up
 * gated server-side; the apiClient interceptor surfaces
 * StepUpRequiredError which we surface as a friendly message.
 */
import { Ionicons } from "@expo/vector-icons";
import * as ImageManipulator from "expo-image-manipulator";
import * as ImagePicker from "expo-image-picker";
import React, { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Linking,
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
  useDeleteDocument,
  useDocuments,
  useUploadDocument,
} from "../hooks/useProviderResources";
import { ApiError, StepUpRequiredError } from "../lib/api-error";
import { uriToBlob } from "../services/s3-uploader";
import type {
  DocumentType,
  ProviderDocument,
} from "../services/provider-documents.service";
import { Colors } from "../theme/colors";

const MAX_BYTES = 20 * 1024 * 1024;
const MAX_DIMENSION_PX = 2400;
const ALLOWED_MIME = new Set(["image/jpeg", "image/png"]);

const DOC_LABELS: Record<DocumentType, string> = {
  insurance: "Insurance",
  business_license: "Business license",
  certification: "Certification",
  w9: "W-9",
  other: "Other",
};

const DOC_OPTIONS: DocumentType[] = [
  "insurance",
  "business_license",
  "certification",
  "w9",
  "other",
];

function inferMimeFromUri(uri: string): string {
  const ext = uri.split(".").pop()?.toLowerCase() ?? "";
  if (ext === "png") return "image/png";
  return "image/jpeg";
}

function formatExpiry(expiresAt: string | null): {
  text: string;
  warning: boolean;
} {
  if (!expiresAt) return { text: "No expiry", warning: false };
  const days = Math.floor(
    (new Date(expiresAt).getTime() - Date.now()) / (1000 * 60 * 60 * 24),
  );
  if (days < 0) return { text: `Expired ${-days}d ago`, warning: true };
  if (days < 30) return { text: `Expires in ${days}d`, warning: true };
  return { text: `Expires ${new Date(expiresAt).toLocaleDateString()}`, warning: false };
}

interface RowProps {
  doc: ProviderDocument;
  onOpen: () => void;
  onDelete: () => void;
  busy: boolean;
}

function DocumentRow({ doc, onOpen, onDelete, busy }: RowProps) {
  const expiry = formatExpiry(doc.expires_at);
  return (
    <View style={styles.card}>
      <TouchableOpacity style={styles.cardHead} onPress={onOpen}>
        <View style={styles.iconBox}>
          <Ionicons name="document-text-outline" size={18} color={Colors.primary} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.docTitle}>
            {doc.title || DOC_LABELS[doc.type as DocumentType] || doc.type}
          </Text>
          <Text style={styles.docSub}>
            {DOC_LABELS[doc.type as DocumentType] || doc.type} ·{" "}
            <Text style={expiry.warning ? styles.warning : undefined}>
              {expiry.text}
            </Text>
          </Text>
        </View>
        <Ionicons name="open-outline" size={18} color="#475569" />
      </TouchableOpacity>

      <View style={styles.actions}>
        <TouchableOpacity
          style={[styles.actionBtn, styles.actionBtnDanger]}
          onPress={onDelete}
          disabled={busy}
        >
          <Ionicons name="trash-outline" size={16} color="#EF4444" />
          <Text style={[styles.actionText, styles.actionTextDanger]}>Remove</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

export default function ProviderDocumentsScreen({ navigation }: any) {
  const query = useDocuments();
  const upload = useUploadDocument();
  const remove = useDeleteDocument();
  const [uploading, setUploading] = useState(false);

  const [pending, setPending] = useState<{
    blob: Blob;
    mime: string;
    size: number;
  } | null>(null);
  const [docType, setDocType] = useState<DocumentType>("insurance");
  const [title, setTitle] = useState("");
  const [expiresAt, setExpiresAt] = useState("");

  const docs = query.data ?? [];

  const pick = async () => {
    if (uploading) return;
    try {
      const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!perm.granted) {
        Alert.alert(
          "Permission needed",
          "Allow photo library access to upload documents.",
        );
        return;
      }
      const picked = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        quality: 0.9,
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
          { compress: 0.9, format: ImageManipulator.SaveFormat.JPEG },
        );
        workingUri = resized.uri;
        mimeType = "image/jpeg";
      }

      const blob = await uriToBlob(workingUri);
      if (blob.size > MAX_BYTES) {
        Alert.alert("File too large", "Documents must be under 20 MB.");
        return;
      }
      if (!ALLOWED_MIME.has(mimeType)) {
        mimeType = "image/jpeg";
      }

      setPending({ blob, mime: mimeType, size: blob.size });
      setTitle("");
      setExpiresAt("");
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Could not prepare the file.";
      Alert.alert("Could not prepare", message);
    }
  };

  const confirmUpload = async () => {
    if (!pending) return;
    if (expiresAt && !/^\d{4}-\d{2}-\d{2}$/.test(expiresAt)) {
      Alert.alert(
        "Invalid date",
        "Use YYYY-MM-DD format, e.g. 2027-12-31.",
      );
      return;
    }
    setUploading(true);
    try {
      await upload.mutateAsync({
        blob: pending.blob,
        type: docType,
        mimeType: pending.mime,
        sizeBytes: pending.size,
        title: title.trim() || undefined,
        expiresAt: expiresAt || undefined,
      });
      setPending(null);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : (err as Error)?.message ?? "Could not upload the document.";
      Alert.alert("Upload failed", message);
    } finally {
      setUploading(false);
    }
  };

  const handleOpen = (doc: ProviderDocument) => {
    if (!doc.download_url) {
      Alert.alert("Unavailable", "Could not load the document right now.");
      return;
    }
    Linking.openURL(doc.download_url).catch(() =>
      Alert.alert("Could not open", "Try downloading from a desktop browser."),
    );
  };

  const handleDelete = (doc: ProviderDocument) => {
    Alert.alert(
      "Remove document?",
      "You'll need to re-upload to restore it.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Remove",
          style: "destructive",
          onPress: () =>
            remove.mutate(doc.id, {
              onError: (err) => {
                if (err instanceof StepUpRequiredError) {
                  Alert.alert(
                    "Verification required",
                    "Confirm it's you to remove a KYC document.",
                  );
                  return;
                }
                Alert.alert("Could not remove", "Please try again.");
              },
            }),
        },
      ],
    );
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
        <Text style={styles.headerTitle}>KYC documents</Text>
        <TouchableOpacity
          onPress={pick}
          style={styles.addBtn}
          hitSlop={12}
          disabled={uploading}
        >
          <Ionicons name="add" size={24} color={Colors.primary} />
        </TouchableOpacity>
      </View>

      {query.isLoading ? (
        <View style={styles.center}>
          <ActivityIndicator color={Colors.primary} />
        </View>
      ) : docs.length === 0 ? (
        <EmptyState
          icon="file-document-outline"
          title="No documents uploaded"
          subtitle="Insurance + a business license are required before you can accept bookings."
          action={{ label: "Upload first document", onPress: pick }}
        />
      ) : (
        <FlatList
          contentContainerStyle={styles.list}
          data={docs}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <DocumentRow
              doc={item}
              onOpen={() => handleOpen(item)}
              onDelete={() => handleDelete(item)}
              busy={remove.isPending}
            />
          )}
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
              <Text style={styles.modalTitle}>Add document</Text>
              <TouchableOpacity onPress={() => setPending(null)} hitSlop={12}>
                <Ionicons name="close" size={22} color={Colors.text} />
              </TouchableOpacity>
            </View>

            <Text style={styles.fieldLabel}>TYPE</Text>
            <View style={styles.typeRow}>
              {DOC_OPTIONS.map((opt) => (
                <TouchableOpacity
                  key={opt}
                  style={[
                    styles.typeChip,
                    docType === opt && styles.typeChipActive,
                  ]}
                  onPress={() => setDocType(opt)}
                >
                  <Text
                    style={[
                      styles.typeChipText,
                      docType === opt && styles.typeChipTextActive,
                    ]}
                  >
                    {DOC_LABELS[opt]}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <Text style={styles.fieldLabel}>TITLE (OPTIONAL)</Text>
            <TextInput
              style={styles.input}
              value={title}
              onChangeText={setTitle}
              placeholder="2026 GL policy"
              placeholderTextColor="#475569"
              maxLength={120}
            />

            <Text style={styles.fieldLabel}>EXPIRES (YYYY-MM-DD, OPTIONAL)</Text>
            <TextInput
              style={styles.input}
              value={expiresAt}
              onChangeText={setExpiresAt}
              placeholder="2027-12-31"
              placeholderTextColor="#475569"
              maxLength={10}
              keyboardType="numbers-and-punctuation"
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

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.background },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  backBtn: { padding: 4 },
  addBtn: { padding: 4 },
  headerTitle: {
    flex: 1,
    color: Colors.text,
    fontSize: 18,
    fontWeight: "600",
    textAlign: "center",
  },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  list: { padding: 16, gap: 12 },
  card: {
    backgroundColor: Colors.card,
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: "#1E293B",
  },
  cardHead: { flexDirection: "row", alignItems: "center", gap: 12 },
  iconBox: {
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: "rgba(59,130,246,0.12)",
    alignItems: "center",
    justifyContent: "center",
  },
  docTitle: { color: Colors.text, fontSize: 15, fontWeight: "600" },
  docSub: { color: Colors.secondaryText, fontSize: 12, marginTop: 4 },
  warning: { color: "#F59E0B", fontWeight: "600" },
  actions: { flexDirection: "row", marginTop: 12 },
  actionBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 8,
    backgroundColor: "#1A2233",
  },
  actionBtnDanger: { backgroundColor: "rgba(239,68,68,0.1)" },
  actionText: { color: Colors.text, fontSize: 13, fontWeight: "500" },
  actionTextDanger: { color: "#EF4444" },

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
  typeRow: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  typeChip: {
    backgroundColor: "#1A2233",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 999,
  },
  typeChipActive: { backgroundColor: Colors.primary },
  typeChipText: { color: Colors.secondaryText, fontSize: 12, fontWeight: "500" },
  typeChipTextActive: { color: Colors.text },
});
