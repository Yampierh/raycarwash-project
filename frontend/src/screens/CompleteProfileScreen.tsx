import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import React, { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import AnimatedInput from "../components/AnimatedInput";
import { completeProfile, VerifyResponse } from "../services/auth.service";
import { Colors } from "../theme/colors";
import { navigateAfterAuth } from "../utils/auth-redirect";
import { saveRefreshToken, saveToken } from "../utils/storage";

export default function CompleteProfileScreen({ navigation }: any) {
  const [selectedRole, setSelectedRole] = useState<"client" | "detailer" | null>(null);
  const [form, setForm] = useState({ full_name: "", phone_number: "" });
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<{
    full_name?: string;
    terms?: string;
    role?: string;
  }>({});

  const update = (field: keyof typeof form) => (value: string) => {
    setForm((f) => ({ ...f, [field]: value }));
    setErrors((e) => ({ ...e, [field]: undefined }));
  };

  const validate = () => {
    const e: typeof errors = {};
    if (!form.full_name.trim()) e.full_name = "Full name is required";
    if (!selectedRole) e.role = "Please choose your account type";
    if (!acceptedTerms) e.terms = "You must accept the Terms & Conditions";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleComplete = async () => {
    if (!validate()) return;
    setLoading(true);
    try {
      const result: VerifyResponse = await completeProfile({
        full_name: form.full_name.trim(),
        phone_number: form.phone_number.trim() || undefined,
        role: selectedRole!,
      });

      if (result.access_token) {
        await saveToken(result.access_token);
        if (result.refresh_token) await saveRefreshToken(result.refresh_token);
      }

      if (result.next_step === "detailer_onboarding" || selectedRole === "detailer") {
        navigation.reset({ index: 0, routes: [{ name: "DetailerOnboarding" }] });
      } else {
        await navigateAfterAuth(navigation);
      }
    } catch (error: any) {
      const detail = error.response?.data?.detail;
      const msg =
        typeof detail === "string"
          ? detail
          : detail?.message ?? "Could not complete profile. Please try again.";
      Alert.alert("Error", msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <LinearGradient
        colors={["#060A14", "#0B0F1A", "#101828"]}
        style={StyleSheet.absoluteFill}
      />
      <SafeAreaView style={{ flex: 1 }}>
        <KeyboardAvoidingView
          style={{ flex: 1 }}
          behavior={Platform.OS === "ios" ? "padding" : undefined}
        >
          <View style={styles.header}>
            <View style={{ width: 40 }} />
            <Text style={styles.headerTitle}>Almost There!</Text>
            <View style={{ width: 40 }} />
          </View>

          <ScrollView
            contentContainerStyle={styles.scroll}
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
          >
            <Text style={styles.subtitle}>
              {selectedRole === "detailer"
                ? "Complete your professional profile to start accepting jobs"
                : "Complete your profile to get started"}
            </Text>

            {/* Role selector */}
            <View style={styles.fieldGroup}>
              <Text style={styles.label}>I AM A</Text>
              <View style={styles.roleRow}>
                <TouchableOpacity
                  style={[styles.roleBtn, selectedRole === "client" && styles.roleBtnActive]}
                  onPress={() => {
                    setSelectedRole("client");
                    setErrors((e) => ({ ...e, role: undefined }));
                  }}
                  activeOpacity={0.75}
                >
                  <Ionicons
                    name="person-outline"
                    size={22}
                    color={selectedRole === "client" ? Colors.primary : "#475569"}
                  />
                  <Text
                    style={[
                      styles.roleBtnText,
                      selectedRole === "client" && styles.roleBtnTextActive,
                    ]}
                  >
                    Client
                  </Text>
                  <Text
                    style={[
                      styles.roleBtnDesc,
                      selectedRole === "client" && styles.roleBtnDescActive,
                    ]}
                  >
                    Book car wash services
                  </Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={[styles.roleBtn, selectedRole === "detailer" && styles.roleBtnActive]}
                  onPress={() => {
                    setSelectedRole("detailer");
                    setErrors((e) => ({ ...e, role: undefined }));
                  }}
                  activeOpacity={0.75}
                >
                  <Ionicons
                    name="car-sport-outline"
                    size={22}
                    color={selectedRole === "detailer" ? Colors.primary : "#475569"}
                  />
                  <Text
                    style={[
                      styles.roleBtnText,
                      selectedRole === "detailer" && styles.roleBtnTextActive,
                    ]}
                  >
                    Detailer Pro
                  </Text>
                  <Text
                    style={[
                      styles.roleBtnDesc,
                      selectedRole === "detailer" && styles.roleBtnDescActive,
                    ]}
                  >
                    Offer detailing services
                  </Text>
                </TouchableOpacity>
              </View>
              {errors.role && (
                <Text style={styles.errorText}>{errors.role}</Text>
              )}
            </View>

            {/* Full Name */}
            <View style={styles.fieldGroup}>
              <Text style={styles.label}>FULL NAME</Text>
              <AnimatedInput
                value={form.full_name}
                onChangeText={update("full_name")}
                placeholder="Your full name"
                icon="person-outline"
                autoCapitalize="words"
                returnKeyType="next"
                error={!!errors.full_name}
              />
              {errors.full_name && (
                <Text style={styles.errorText}>{errors.full_name}</Text>
              )}
            </View>

            {/* Phone — optional */}
            <View style={styles.fieldGroup}>
              <View style={styles.labelRow}>
                <Text style={styles.label}>PHONE NUMBER</Text>
                <Text style={styles.optionalLabel}>Optional</Text>
              </View>
              <AnimatedInput
                value={form.phone_number}
                onChangeText={update("phone_number")}
                placeholder="+1 555 123 4567"
                icon="call-outline"
                keyboardType="phone-pad"
                returnKeyType="done"
              />
            </View>

            {/* Terms */}
            <TouchableOpacity
              style={styles.termsRow}
              onPress={() => {
                setAcceptedTerms((v) => !v);
                setErrors((e) => ({ ...e, terms: undefined }));
              }}
              activeOpacity={0.7}
            >
              <View style={[styles.checkbox, acceptedTerms && styles.checkboxChecked]}>
                {acceptedTerms && (
                  <Ionicons name="checkmark" size={14} color="#fff" />
                )}
              </View>
              <Text style={styles.termsText}>
                I agree to the{" "}
                <Text style={styles.termsLink}>Terms & Conditions</Text>
                {" "}and{" "}
                <Text style={styles.termsLink}>Privacy Policy</Text>
              </Text>
            </TouchableOpacity>
            {errors.terms && (
              <Text style={[styles.errorText, { marginTop: -8, marginBottom: 12 }]}>
                {errors.terms}
              </Text>
            )}

            <TouchableOpacity
              style={[styles.primaryBtn, loading && styles.btnDisabled]}
              onPress={handleComplete}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.primaryBtnText}>
                  {selectedRole === "detailer" ? "CONTINUE" : "GET STARTED"}
                </Text>
              )}
            </TouchableOpacity>

            <View style={{ height: 30 }} />
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingTop: 8,
    paddingBottom: 4,
  },
  headerTitle: { color: "white", fontSize: 18, fontWeight: "bold" },
  scroll: { paddingHorizontal: 24, paddingTop: 8, paddingBottom: 20 },
  subtitle: {
    color: "#475569",
    fontSize: 14,
    marginBottom: 28,
    textAlign: "center",
  },
  fieldGroup: { marginBottom: 16 },
  labelRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  label: {
    color: "#94A3B8",
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1,
    marginBottom: 8,
  },
  optionalLabel: { color: "#64748B", fontSize: 10, fontWeight: "600" },
  errorText: { color: "#EF4444", fontSize: 11, marginTop: 5, marginLeft: 4 },
  roleRow: { flexDirection: "row", gap: 12 },
  roleBtn: {
    flex: 1,
    backgroundColor: "#111827",
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#1E293B",
    padding: 16,
    alignItems: "center",
    gap: 6,
  },
  roleBtnActive: {
    borderColor: Colors.primary,
    backgroundColor: "rgba(59,130,246,0.08)",
  },
  roleBtnText: { color: "#64748B", fontSize: 14, fontWeight: "700" },
  roleBtnTextActive: { color: Colors.primary },
  roleBtnDesc: {
    color: "#334155",
    fontSize: 11,
    textAlign: "center",
    lineHeight: 15,
  },
  roleBtnDescActive: { color: "#475569" },
  termsRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 12,
    marginBottom: 20,
    marginTop: 6,
  },
  checkbox: {
    width: 22,
    height: 22,
    borderRadius: 6,
    borderWidth: 2,
    borderColor: "#334155",
    alignItems: "center",
    justifyContent: "center",
    marginTop: 1,
  },
  checkboxChecked: {
    backgroundColor: Colors.primary,
    borderColor: Colors.primary,
  },
  termsText: { flex: 1, color: "#64748B", fontSize: 13, lineHeight: 20 },
  termsLink: { color: Colors.primary, fontWeight: "600" },
  primaryBtn: {
    backgroundColor: Colors.primary,
    padding: 17,
    borderRadius: 14,
    alignItems: "center",
    shadowColor: Colors.primary,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.35,
    shadowRadius: 10,
    elevation: 6,
  },
  btnDisabled: { opacity: 0.5 },
  primaryBtnText: {
    color: "#fff",
    fontWeight: "800",
    fontSize: 15,
    letterSpacing: 1.5,
  },
});
