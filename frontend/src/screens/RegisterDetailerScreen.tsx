import { Ionicons } from "@expo/vector-icons";
import * as Google from "expo-auth-session/providers/google";
import { LinearGradient } from "expo-linear-gradient";
import * as WebBrowser from "expo-web-browser";
import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
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
import { GOOGLE_CLIENT_IDS } from "../config/oauth";
import { UserRole, UserRoleType } from "../navigation/types"; // <-- Importación del Enum de Roles
import { loginWithGoogle, registerUser } from "../services/auth.service";
import { Colors } from "../theme/colors";
import { navigateAfterAuth } from "../utils/auth-redirect";
import { saveRefreshToken, saveToken } from "../utils/storage";

WebBrowser.maybeCompleteAuthSession();

type PasswordStrength = "empty" | "weak" | "fair" | "good" | "strong";

function getPasswordStrength(pwd: string): PasswordStrength {
  if (!pwd) return "empty";
  if (pwd.length < 6) return "weak";
  const hasUpper = /[A-Z]/.test(pwd);
  const hasNumber = /[0-9]/.test(pwd);
  const hasSpecial = /[^A-Za-z0-9]/.test(pwd);
  if (pwd.length >= 12 && hasUpper && hasNumber && hasSpecial) return "strong";
  if (pwd.length >= 8 && (hasUpper || hasNumber)) return "good";
  return "fair";
}

const STRENGTH_CONFIG: Record<
  PasswordStrength,
  { label: string; color: string; bars: number }
> = {
  empty: { label: "", color: "#1E293B", bars: 0 },
  weak: { label: "Weak", color: "#EF4444", bars: 1 },
  fair: { label: "Fair", color: "#F59E0B", bars: 2 },
  good: { label: "Good", color: "#3B82F6", bars: 3 },
  strong: { label: "Strong", color: "#10B981", bars: 4 },
};

export default function RegisterDetailerScreen({ navigation, route }: any) {
  // ─── Estado del Rol ─────────────────────────────────────────────────────────
  const [role, setRole] = useState<UserRoleType>(UserRole.DETAILER);

  const [form, setForm] = useState({
    full_name: "",
    email: "",
    phone_number: "",
    password: "",
    confirm_password: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [loading, setLoading] = useState(false);
  const [socialLoading, setSocialLoading] = useState(false);
  const [errors, setErrors] = useState<
    Partial<typeof form & { terms: string }>
  >({});

  const strength = getPasswordStrength(form.password);
  const strengthCfg = STRENGTH_CONFIG[strength];

  // ─── Google OAuth ───────────────────────────────────────────────────────────
  const [, googleResponse, googlePromptAsync] = Google.useAuthRequest({
    clientId: GOOGLE_CLIENT_IDS.web,
    iosClientId: GOOGLE_CLIENT_IDS.ios,
    androidClientId: GOOGLE_CLIENT_IDS.android,
  });

  useEffect(() => {
    if (googleResponse?.type === "success") {
      const token = googleResponse.authentication?.accessToken;
      if (token) handleGoogleToken(token);
    }
    if (googleResponse?.type === "error") {
      setSocialLoading(false);
      Alert.alert("Google Sign-Up", "Authentication failed. Please try again.");
    }
  }, [googleResponse]);

  const handleGoogleToken = async (accessToken: string) => {
    try {
      const data = await loginWithGoogle(accessToken);
      await saveToken(data.access_token);
      await saveRefreshToken(data.refresh_token);
      await navigateAfterAuth(navigation);
    } catch {
      Alert.alert(
        "Google Sign-Up",
        "Could not create account with Google. Please try again.",
      );
    } finally {
      setSocialLoading(false);
    }
  };

  const handleGooglePress = async () => {
    if (
      !GOOGLE_CLIENT_IDS.web &&
      !GOOGLE_CLIENT_IDS.ios &&
      !GOOGLE_CLIENT_IDS.android
    ) {
      Alert.alert(
        "Setup Required",
        "Add your Google Client IDs in src/config/oauth.ts to enable Google Sign-Up.",
      );
      return;
    }
    setSocialLoading(true);
    await googlePromptAsync();
  };

  // ─── Validation ─────────────────────────────────────────────────────────────
  const validate = () => {
    const e: typeof errors = {};
    if (!form.full_name.trim()) e.full_name = "Full name is required";
    if (!form.email.trim()) e.email = "Email is required";
    else if (!/\S+@\S+\.\S+/.test(form.email)) e.email = "Enter a valid email";
    if (!form.password) e.password = "Password is required";
    else if (form.password.length < 8)
      e.password = "Password must be at least 8 characters";
    if (!form.confirm_password)
      e.confirm_password = "Please confirm your password";
    else if (form.password !== form.confirm_password)
      e.confirm_password = "Passwords do not match";
    if (!acceptedTerms) e.terms = "You must accept the Terms & Conditions";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  // ─── Register ────────────────────────────────────────────────────────────────
  const handleRegister = async () => {
    if (!validate()) return;
    setLoading(true);
    try {
      // RBAC: send role_names as array instead of single role
      const roleNames = role === UserRole.DETAILER 
        ? ["detailer"] 
        : ["client"];
      
      await registerUser({
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        password: form.password,
        phone_number: form.phone_number.trim() || undefined,
        role_names: roleNames,
      });
      Alert.alert(
        "Account Created!",
        "Welcome to RayCarWash. Please sign in.",
        [
          {
            text: "Sign In",
            onPress: () =>
              navigation.reset({ index: 0, routes: [{ name: "Login" }] }),
          },
        ],
      );
    } catch (error: any) {
      const detail = error.response?.data?.detail;
      const msg = Array.isArray(detail)
        ? detail[0]?.msg
        : typeof detail === "string"
          ? detail
          : "Registration failed. Please check your details.";
      Alert.alert("Registration Failed", msg);
    } finally {
      setLoading(false);
    }
  };

  const update = (field: keyof typeof form) => (value: string) => {
    setForm((f) => ({ ...f, [field]: value }));
    setErrors((e) => ({ ...e, [field]: undefined }));
  };

  const isAnyLoading = loading || socialLoading;

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
          {/* Header */}
          <View style={styles.header}>
            <TouchableOpacity
              onPress={() => navigation.goBack()}
              style={styles.backBtn}
            >
              <Ionicons name="chevron-back" size={22} color="white" />
            </TouchableOpacity>
            <Text style={styles.headerTitle}>Create Account</Text>
            <View style={{ width: 40 }} />
          </View>

          <ScrollView
            contentContainerStyle={styles.scroll}
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
          >
            <Text style={styles.subtitle}>Join RayCarWash today</Text>

            {/* ─── Role Selector ───────────────────────────────────────────── */}
            <Text style={styles.sectionLabel}>I AM A...</Text>
            <View style={styles.roleRow}>
              <TouchableOpacity
                style={[
                  styles.roleBtn,
                  role === UserRole.CLIENT && styles.roleBtnActive,
                ]}
                onPress={() => setRole(UserRole.CLIENT)}
              >
                <Ionicons
                  name="person-outline"
                  size={18}
                  color={role === UserRole.CLIENT ? "#0F172A" : "#94A3B8"}
                />
                <Text
                  style={[
                    styles.roleBtnText,
                    role === UserRole.CLIENT && styles.roleBtnTextActive,
                  ]}
                >
                  Client
                </Text>
                <Text
                  style={[
                    styles.roleBtnSub,
                    role === UserRole.CLIENT && { color: "#0F172A80" },
                  ]}
                >
                  Book detailing
                </Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[
                  styles.roleBtn,
                  role === UserRole.DETAILER && styles.roleBtnActive,
                ]}
                onPress={() => setRole(UserRole.DETAILER)}
              >
                <Ionicons
                  name="construct-outline"
                  size={18}
                  color={role === UserRole.DETAILER ? "#0F172A" : "#94A3B8"}
                />
                <Text
                  style={[
                    styles.roleBtnText,
                    role === UserRole.DETAILER && styles.roleBtnTextActive,
                  ]}
                >
                  Professional
                </Text>
                <Text
                  style={[
                    styles.roleBtnSub,
                    role === UserRole.DETAILER && { color: "#0F172A80" },
                  ]}
                >
                  Offer services
                </Text>
              </TouchableOpacity>
            </View>

            {/* ─── Personal Info ───────────────────────────────────────────── */}
            <Text style={[styles.sectionLabel, { marginTop: 20 }]}>
              PERSONAL INFORMATION
            </Text>

            {/* Full Name */}
            <View style={styles.fieldGroup}>
              <View
                style={[
                  styles.inputWrapper,
                  errors.full_name && styles.inputError,
                ]}
              >
                <Ionicons
                  name="person-outline"
                  size={18}
                  color="#475569"
                  style={styles.inputIcon}
                />
                <TextInput
                  style={styles.input}
                  placeholder="Full Name"
                  placeholderTextColor="#334155"
                  value={form.full_name}
                  onChangeText={update("full_name")}
                  autoCapitalize="words"
                  returnKeyType="next"
                />
              </View>
              {errors.full_name && (
                <Text style={styles.errorText}>{errors.full_name}</Text>
              )}
            </View>

            {/* Email */}
            <View style={styles.fieldGroup}>
              <View
                style={[styles.inputWrapper, errors.email && styles.inputError]}
              >
                <Ionicons
                  name="mail-outline"
                  size={18}
                  color="#475569"
                  style={styles.inputIcon}
                />
                <TextInput
                  style={styles.input}
                  placeholder="Email Address"
                  placeholderTextColor="#334155"
                  value={form.email}
                  onChangeText={update("email")}
                  keyboardType="email-address"
                  autoCapitalize="none"
                  autoCorrect={false}
                  returnKeyType="next"
                />
              </View>
              {errors.email && (
                <Text style={styles.errorText}>{errors.email}</Text>
              )}
            </View>

            {/* Phone (optional) */}
            <View style={styles.fieldGroup}>
              <View style={styles.inputWrapper}>
                <Ionicons
                  name="call-outline"
                  size={18}
                  color="#475569"
                  style={styles.inputIcon}
                />
                <TextInput
                  style={styles.input}
                  placeholder="Phone Number (optional)"
                  placeholderTextColor="#334155"
                  value={form.phone_number}
                  onChangeText={update("phone_number")}
                  keyboardType="phone-pad"
                  returnKeyType="next"
                />
                <View style={styles.optionalBadge}>
                  <Text style={styles.optionalText}>Optional</Text>
                </View>
              </View>
            </View>

            {/* ─── Security ────────────────────────────────────────────────── */}
            <Text style={[styles.sectionLabel, { marginTop: 20 }]}>
              SECURITY
            </Text>

            {/* Password */}
            <View style={styles.fieldGroup}>
              <View
                style={[
                  styles.inputWrapper,
                  errors.password && styles.inputError,
                ]}
              >
                <Ionicons
                  name="lock-closed-outline"
                  size={18}
                  color="#475569"
                  style={styles.inputIcon}
                />
                <TextInput
                  style={styles.input}
                  placeholder="Password (min 8 characters)"
                  placeholderTextColor="#334155"
                  value={form.password}
                  onChangeText={update("password")}
                  secureTextEntry={!showPassword}
                  returnKeyType="next"
                />
                <TouchableOpacity
                  onPress={() => setShowPassword((v) => !v)}
                  style={styles.eyeBtn}
                >
                  <Ionicons
                    name={showPassword ? "eye-off-outline" : "eye-outline"}
                    size={18}
                    color="#475569"
                  />
                </TouchableOpacity>
              </View>
              {errors.password && (
                <Text style={styles.errorText}>{errors.password}</Text>
              )}

              {/* Password strength */}
              {form.password.length > 0 && (
                <View style={styles.strengthContainer}>
                  <View style={styles.strengthBars}>
                    {[1, 2, 3, 4].map((i) => (
                      <View
                        key={i}
                        style={[
                          styles.strengthBar,
                          {
                            backgroundColor:
                              i <= strengthCfg.bars
                                ? strengthCfg.color
                                : "#1E293B",
                          },
                        ]}
                      />
                    ))}
                  </View>
                  <Text
                    style={[styles.strengthLabel, { color: strengthCfg.color }]}
                  >
                    {strengthCfg.label}
                  </Text>
                </View>
              )}
            </View>

            {/* Confirm Password */}
            <View style={styles.fieldGroup}>
              <View
                style={[
                  styles.inputWrapper,
                  errors.confirm_password && styles.inputError,
                ]}
              >
                <Ionicons
                  name="shield-checkmark-outline"
                  size={18}
                  color="#475569"
                  style={styles.inputIcon}
                />
                <TextInput
                  style={styles.input}
                  placeholder="Confirm Password"
                  placeholderTextColor="#334155"
                  value={form.confirm_password}
                  onChangeText={update("confirm_password")}
                  secureTextEntry={!showConfirm}
                  returnKeyType="done"
                />
                <TouchableOpacity
                  onPress={() => setShowConfirm((v) => !v)}
                  style={styles.eyeBtn}
                >
                  <Ionicons
                    name={showConfirm ? "eye-off-outline" : "eye-outline"}
                    size={18}
                    color="#475569"
                  />
                </TouchableOpacity>
              </View>
              {errors.confirm_password && (
                <Text style={styles.errorText}>{errors.confirm_password}</Text>
              )}
              {/* Match indicator */}
              {form.confirm_password.length > 0 && (
                <View style={styles.matchRow}>
                  <Ionicons
                    name={
                      form.password === form.confirm_password
                        ? "checkmark-circle"
                        : "close-circle"
                    }
                    size={14}
                    color={
                      form.password === form.confirm_password
                        ? "#10B981"
                        : "#EF4444"
                    }
                  />
                  <Text
                    style={[
                      styles.matchText,
                      {
                        color:
                          form.password === form.confirm_password
                            ? "#10B981"
                            : "#EF4444",
                      },
                    ]}
                  >
                    {form.password === form.confirm_password
                      ? "Passwords match"
                      : "Passwords do not match"}
                  </Text>
                </View>
              )}
            </View>

            {/* Terms & Conditions */}
            <TouchableOpacity
              style={styles.termsRow}
              onPress={() => {
                setAcceptedTerms((v) => !v);
                setErrors((e) => ({ ...e, terms: undefined }));
              }}
              activeOpacity={0.7}
            >
              <View
                style={[
                  styles.checkbox,
                  acceptedTerms && styles.checkboxChecked,
                ]}
              >
                {acceptedTerms && (
                  <Ionicons name="checkmark" size={14} color="#fff" />
                )}
              </View>
              <Text style={styles.termsText}>
                I agree to the{" "}
                <Text
                  style={styles.termsLink}
                  onPress={() =>
                    Alert.alert(
                      "Terms & Conditions",
                      "Available at raycarwash.com/terms",
                    )
                  }
                >
                  Terms & Conditions
                </Text>{" "}
                and{" "}
                <Text
                  style={styles.termsLink}
                  onPress={() =>
                    Alert.alert(
                      "Privacy Policy",
                      "Available at raycarwash.com/privacy",
                    )
                  }
                >
                  Privacy Policy
                </Text>
              </Text>
            </TouchableOpacity>
            {errors.terms && (
              <Text
                style={[styles.errorText, { marginTop: -8, marginBottom: 12 }]}
              >
                {errors.terms}
              </Text>
            )}

            {/* Create Account button */}
            <TouchableOpacity
              style={[styles.primaryBtn, isAnyLoading && styles.btnDisabled]}
              onPress={handleRegister}
              disabled={isAnyLoading}
            >
              {loading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.primaryBtnText}>CREATE ACCOUNT</Text>
              )}
            </TouchableOpacity>

            {/* Divider */}
            <View style={styles.divider}>
              <View style={styles.dividerLine} />
              <Text style={styles.dividerText}>or sign up with</Text>
              <View style={styles.dividerLine} />
            </View>

            {/* Google */}
            <TouchableOpacity
              style={[styles.googleBtn, isAnyLoading && styles.btnDisabled]}
              onPress={handleGooglePress}
              disabled={isAnyLoading}
            >
              {socialLoading ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <>
                  <Text style={styles.googleG}>G</Text>
                  <Text style={styles.googleBtnText}>Continue with Google</Text>
                </>
              )}
            </TouchableOpacity>

            {/* Sign in link */}
            <TouchableOpacity
              style={styles.loginLink}
              onPress={() => navigation.navigate("Login")}
            >
              <Text style={styles.loginLinkText}>
                Already have an account?{" "}
                <Text style={styles.loginLinkBold}>Sign In</Text>
              </Text>
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
  backBtn: { backgroundColor: "#161E2E", padding: 8, borderRadius: 12 },
  headerTitle: { color: "white", fontSize: 18, fontWeight: "bold" },
  scroll: { paddingHorizontal: 24, paddingTop: 8, paddingBottom: 20 },
  subtitle: {
    color: "#475569",
    fontSize: 14,
    marginBottom: 28,
    textAlign: "center",
  },

  // ─── Estilos Nuevos para el Selector de Rol ───
  roleContainer: {
    flexDirection: "row",
    backgroundColor: "#161E2E",
    padding: 6,
    borderRadius: 16,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: "#262F3F",
  },
  roleTab: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 12,
    borderRadius: 12,
    gap: 8,
  },
  activeTab: {
    backgroundColor: Colors.primary,
    shadowColor: Colors.primary,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  roleTabText: {
    color: "#475569",
    fontSize: 14,
    fontWeight: "700",
  },
  activeTabText: {
    color: "#fff",
  },
  // ──────────────────────────────────────────────

  sectionLabel: {
    color: "#475569",
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1,
    marginBottom: 14,
  },
  fieldGroup: { marginBottom: 14 },
  inputWrapper: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#111827",
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#1E293B",
  },
  inputError: { borderColor: "#EF4444" },
  inputIcon: { marginLeft: 14 },
  input: { flex: 1, color: "#fff", padding: 15, fontSize: 15 },
  eyeBtn: { padding: 14 },
  optionalBadge: {
    backgroundColor: "#1E293B",
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
    marginRight: 12,
  },
  optionalText: { color: "#475569", fontSize: 10, fontWeight: "700" },
  errorText: { color: "#EF4444", fontSize: 11, marginTop: 5, marginLeft: 4 },
  strengthContainer: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    marginTop: 8,
  },
  strengthBars: { flexDirection: "row", gap: 4, flex: 1 },
  strengthBar: { flex: 1, height: 3, borderRadius: 2 },
  strengthLabel: {
    fontSize: 11,
    fontWeight: "700",
    width: 44,
    textAlign: "right",
  },
  matchRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    marginTop: 6,
  },
  matchText: { fontSize: 11 },
  termsRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 12,
    marginBottom: 16,
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
  divider: {
    flexDirection: "row",
    alignItems: "center",
    marginVertical: 20,
    gap: 12,
  },
  dividerLine: { flex: 1, height: 1, backgroundColor: "#1E293B" },
  dividerText: { color: "#334155", fontSize: 12 },
  googleBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    backgroundColor: "#161E2E",
    padding: 15,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#262F3F",
  },
  googleG: {
    color: "#fff",
    fontWeight: "900",
    fontSize: 16,
    fontStyle: "italic",
  },
  googleBtnText: { color: "#fff", fontWeight: "600", fontSize: 15 },
  loginLink: { marginTop: 20, alignItems: "center" },
  loginLinkText: { color: "#475569", fontSize: 14 },
  loginLinkBold: { color: Colors.primary, fontWeight: "700" },
  // Role selector
  roleRow: { flexDirection: "row", gap: 12, marginBottom: 20 },
  roleBtn: {
    flex: 1,
    backgroundColor: "#161E2E",
    borderRadius: 16,
    padding: 16,
    alignItems: "center",
    gap: 4,
    borderWidth: 1,
    borderColor: "#262F3F",
  },
  roleBtnActive: {
    backgroundColor: Colors.primary,
    borderColor: Colors.primary,
  },
  roleBtnText: { color: "#94A3B8", fontWeight: "700", fontSize: 15 },
  roleBtnTextActive: { color: "#0F172A" },
  roleBtnSub: { color: "#475569", fontSize: 11 },
});
