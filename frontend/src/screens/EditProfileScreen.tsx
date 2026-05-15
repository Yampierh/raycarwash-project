import { Ionicons } from "@expo/vector-icons";
import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import AvatarPicker from "../components/AvatarPicker";
import Button from "../components/Button";
import { ApiError } from "../lib/api-error";
import { useMe, useUpdateProfile } from "../hooks/useMe";
import { updateUserProfile } from "../services/user.service";
import { Colors } from "../theme/colors";

/** Split "First Middle Last" into ("First", "Middle Last"). Mirrors backend. */
function splitFullName(full: string | null | undefined): { first: string; last: string } {
  if (!full) return { first: "", last: "" };
  const parts = full.trim().split(/\s+/);
  if (parts.length <= 1) return { first: parts[0] ?? "", last: "" };
  return { first: parts[0], last: parts.slice(1).join(" ") };
}

export default function EditProfileScreen({ navigation, route }: any) {
  const { focusAddress } = route?.params || {};
  const addressRef = useRef<TextInput>(null);

  // Profile Hub feeds the initial form state. ProfileScreen no longer
  // passes `user` via route params — we read from the Hub directly so
  // the screen works regardless of how it was opened.
  const meQuery = useMe(["profile"]);
  const updateProfile = useUpdateProfile();

  const hubProfile = meQuery.data?.data.profile;
  const hubUser = meQuery.data?.data.user;

  const initialForm = useMemo(() => ({
    full_name: hubProfile?.full_name || "",
    phone_number: hubUser?.phone || "",
    service_address: "",  // ClientProfile.service_address — landing in Phase 4
  }), [hubProfile, hubUser]);

  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState(initialForm);

  // Hub fetch is async; once data lands, hydrate the form one-time.
  useEffect(() => {
    setForm(initialForm);
  }, [initialForm]);

  useEffect(() => {
    if (focusAddress) setTimeout(() => addressRef.current?.focus(), 400);
  }, [focusAddress]);

  const handleUpdate = async () => {
    if (!form.full_name.trim()) {
      Alert.alert("Error", "Full name is required.");
      return;
    }
    setLoading(true);
    try {
      // Hub PATCH handles name (first/last). Backend recomposes full_name.
      const { first, last } = splitFullName(form.full_name);
      const originalFirst = splitFullName(hubProfile?.full_name).first;
      const originalLast = splitFullName(hubProfile?.full_name).last;
      if (first !== originalFirst || last !== originalLast) {
        await updateProfile.mutateAsync({
          first_name: first,
          last_name: last || undefined,
        });
      }

      // Phone change still goes through the legacy /auth/update endpoint —
      // Phase 3 adds /users/me/phone/change-request with OTP verification.
      const trimmedPhone = form.phone_number.trim();
      if (trimmedPhone && trimmedPhone !== (hubUser?.phone || "")) {
        await updateUserProfile({
          full_name: form.full_name.trim(),  // legacy endpoint requires it
          phone_number: trimmedPhone,
        });
      }

      Alert.alert("Success", "Profile updated successfully.", [
        { text: "OK", onPress: () => navigation.goBack() },
      ]);
    } catch (error: any) {
      let errorMessage = "Could not update profile. Try again.";
      if (error instanceof ApiError) {
        errorMessage = error.message;
      } else {
        const serverDetail = error.response?.data?.detail;
        if (Array.isArray(serverDetail)) {
          errorMessage = serverDetail[0]?.msg || errorMessage;
        } else if (serverDetail) {
          errorMessage = serverDetail;
        }
      }
      Alert.alert("Error", errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const Field = ({ label, value, onChangeText, placeholder, keyboardType, autoCapitalize, editable = true, icon, inputRef, hint }: any) => (
    <View style={styles.inputGroup}>
      <Text style={styles.label}>{label}</Text>
      <View style={[styles.inputWrapper, !editable && styles.inputDisabled]}>
        {icon && (
          <Ionicons name={icon} size={18} color={editable ? "#475569" : "#2D3748"} style={styles.inputIcon} />
        )}
        <TextInput
          ref={inputRef}
          style={[styles.input, !editable && styles.inputTextDisabled]}
          value={value}
          onChangeText={onChangeText}
          placeholder={placeholder}
          placeholderTextColor="#334155"
          keyboardType={keyboardType || "default"}
          autoCapitalize={autoCapitalize || "sentences"}
          editable={editable}
          returnKeyType="next"
        />
        {!editable && (
          <Ionicons name="lock-closed" size={14} color="#2D3748" style={{ marginRight: 14 }} />
        )}
      </View>
      {hint && <Text style={styles.hint}>{hint}</Text>}
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
            <Ionicons name="chevron-back" size={22} color="white" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Personal Info</Text>
          <View style={{ width: 40 }} />
        </View>

        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.avatarSection}>
            <AvatarPicker
              currentUrl={hubProfile?.avatar_url ?? null}
              fullName={form.full_name}
              size={90}
            />
            <Text style={styles.avatarHint}>Tap to change your profile photo</Text>
          </View>

          <Text style={styles.sectionLabel}>PERSONAL INFORMATION</Text>

          <Field
            label="FULL NAME"
            value={form.full_name}
            onChangeText={(t: string) => setForm({ ...form, full_name: t })}
            placeholder="Your full name"
            icon="person-outline"
          />
          <Field
            label="EMAIL ADDRESS"
            value={hubUser?.email || ""}
            editable={false}
            icon="mail-outline"
            hint="Contact support to change your email address"
          />
          <Field
            label="PHONE NUMBER"
            value={form.phone_number}
            onChangeText={(t: string) => setForm({ ...form, phone_number: t })}
            placeholder="+1 (555) 000-0000"
            keyboardType="phone-pad"
            autoCapitalize="none"
            icon="call-outline"
            hint="Include country code (e.g. +1 for US)"
          />

          <Text style={[styles.sectionLabel, { marginTop: 28 }]}>SERVICE PREFERENCES</Text>

          <Field
            label="DEFAULT SERVICE ADDRESS"
            value={form.service_address}
            onChangeText={(t: string) => setForm({ ...form, service_address: t })}
            placeholder="123 Main St, Fort Wayne, IN 46802"
            icon="location-outline"
            inputRef={addressRef}
            hint="Used to pre-fill your service location when booking"
          />

          <View style={styles.infoBox}>
            <Ionicons name="information-circle-outline" size={18} color={Colors.primary} />
            <Text style={styles.infoText}>
              Your address is only shared with your assigned detailer after a booking is confirmed.
            </Text>
          </View>

          <Button
            title="SAVE CHANGES"
            onPress={handleUpdate}
            variant="primary"
            size="lg"
            fullWidth
            loading={loading}
          />

          <View style={{ height: 40 }} />
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0B0F1A" },
  header: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: 20, paddingVertical: 16,
  },
  backBtn: {
    backgroundColor: "#161E2E", padding: 8, borderRadius: 12,
    borderWidth: 1, borderColor: "#262F3F",
  },
  headerTitle: { color: "white", fontSize: 18, fontWeight: "700" },
  scrollContent: { paddingHorizontal: 20, paddingBottom: 20 },
  avatarSection: { alignItems: "center", paddingVertical: 24 },
  avatarInitials: {
    width: 90, height: 90, borderRadius: 45, backgroundColor: "#1E3A5F",
    borderWidth: 3, borderColor: Colors.primary,
    alignItems: "center", justifyContent: "center", marginBottom: 10,
  },
  initialsText: { color: Colors.primary, fontSize: 32, fontWeight: "700" },
  avatarHint: { color: "#334155", fontSize: 12 },
  sectionLabel: { color: "#475569", fontSize: 11, fontWeight: "800", letterSpacing: 1, marginBottom: 14 },
  inputGroup: { marginBottom: 16 },
  label: { color: "#94A3B8", fontSize: 11, fontWeight: "800", letterSpacing: 1, marginBottom: 8 },
  inputWrapper: {
    flexDirection: "row", alignItems: "center",
    backgroundColor: "#161E2E", borderRadius: 12,
    borderWidth: 1, borderColor: "#262F3F",
  },
  inputDisabled: { backgroundColor: "#0F1623", borderColor: "#1A2235" },
  inputIcon: { marginLeft: 14, marginRight: 4 },
  input: { flex: 1, color: "white", padding: 16, fontSize: 15 },
  inputTextDisabled: { color: "#334155" },
  hint: { color: "#334155", fontSize: 11, marginTop: 6, marginLeft: 4 },
  infoBox: {
    flexDirection: "row", backgroundColor: "#1E3A5F20", borderRadius: 12, padding: 14,
    gap: 10, borderWidth: 1, borderColor: "#1E3A5F50", marginBottom: 24, marginTop: 4, alignItems: "flex-start",
  },
  infoText: { color: "#94A3B8", fontSize: 12, flex: 1, lineHeight: 18 },
});
