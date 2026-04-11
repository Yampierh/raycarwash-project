import { Ionicons } from "@expo/vector-icons";
import * as AppleAuthentication from "expo-apple-authentication";
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
import { UserRole, UserRoleType } from "../navigation/types";
import {
  checkEmail,
  loginWithApple,
  loginWithBackend,
  loginWithGoogle,
  registerUser,
} from "../services/auth.service";
import { Colors } from "../theme/colors";
import { navigateAfterAuth } from "../utils/auth-redirect";
import { saveRefreshToken, saveToken } from "../utils/storage";

WebBrowser.maybeCompleteAuthSession();

type AuthMethod = "password" | "google" | "apple" | "both" | "none";
type FlowState = "email" | "password" | "social_options" | "register";

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

export default function RegisterScreen({ navigation, route }: any) {
  const { isDetailer } = route?.params || {};
  const [flowState, setFlowState] = useState<FlowState>("email");
  const [identifierType, setIdentifierType] = useState<"email" | "phone">("email");
  const [checkedIdentifier, setCheckedIdentifier] = useState("");
  const [authMethod, setAuthMethod] = useState<AuthMethod>("none");
  
  const [form, setForm] = useState({
    email: "",
    password: "",
    confirm_password: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [loading, setLoading] = useState(false);
  const [socialLoading, setSocialLoading] = useState<"google" | "apple" | null>(null);
  const [errors, setErrors] = useState<Partial<typeof form & { terms: string }>>({});

  const strength = getPasswordStrength(form.password);
  const strengthCfg = STRENGTH_CONFIG[strength];

  // Google OAuth
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
      setSocialLoading(null);
      Alert.alert("Google Sign-In", "Authentication failed. Please try again.");
    }
  }, [googleResponse]);

  const handleGoogleToken = async (accessToken: string) => {
    try {
      const data = await loginWithGoogle(accessToken);
      await saveToken(data.access_token);
      await saveRefreshToken(data.refresh_token);
      await navigateAfterAuth(navigation);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (detail?.includes("not registered")) {
        setFlowState("register");
      } else {
        Alert.alert(
          "Google Sign-In",
          "Could not sign in with Google. Please try again.",
        );
      }
    } finally {
      setSocialLoading(null);
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
        "Add your Google Client IDs in src/config/oauth.ts to enable Google Sign-In.",
      );
      return;
    }
    setSocialLoading("google");
    await googlePromptAsync();
  };

  const handleApplePress = async () => {
    try {
      const credential = await AppleAuthentication.signInAsync({
        requestedScopes: [
          AppleAuthentication.AppleAuthenticationScope.FULL_NAME,
          AppleAuthentication.AppleAuthenticationScope.EMAIL,
        ],
      });

      if (!credential.identityToken) throw new Error("No identity token");

      const fullName = [
        credential.fullName?.givenName,
        credential.fullName?.familyName,
      ]
        .filter(Boolean)
        .join(" ");

      const data = await loginWithApple(credential.identityToken, fullName || undefined);
      await saveToken(data.access_token);
      await saveRefreshToken(data.refresh_token);
      await navigateAfterAuth(navigation);
    } catch (error: any) {
      if (error.code !== "ERR_REQUEST_CANCELED") {
        Alert.alert("Apple Sign-In", "Could not sign in with Apple.");
      }
    } finally {
      setSocialLoading(null);
    }
  };

  const handleCheckIdentifier = async () => {
    const identifier = form.email.trim();
    
    if (!identifier) {
      setErrors((e) => ({ ...e, email: identifierType === "email" ? "Email is required" : "Phone number is required" }));
      return;
    }

    // Validate based on type
    if (identifierType === "email") {
      if (!/\S+@\S+\.\S+/.test(identifier)) {
        setErrors((e) => ({ ...e, email: "Enter a valid email" }));
        return;
      }
    } else {
      const cleanPhone = identifier.replace(/[\s\-\(\)]/g, "");
      if (!/^\+?\d{10,}$/.test(cleanPhone)) {
        setErrors((e) => ({ ...e, email: "Enter a valid phone number" }));
        return;
      }
    }

    setLoading(true);
    try {
      const result = await checkEmail(identifier.toLowerCase());
      setCheckedIdentifier(identifier);
      
      if (result.suggested_action === "login" || result.auth_method === "password" || result.auth_method === "both") {
        setFlowState("password");
      } else if (result.suggested_action === "social_login") {
        setAuthMethod(result.auth_method);
        setFlowState("social_options");
      } else {
        setFlowState("register");
      }
    } catch (error: any) {
      const msg = error.response?.data?.detail || "Could not verify. Please try again.";
      Alert.alert("Error", msg);
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async () => {
    if (!form.password) {
      setErrors((e) => ({ ...e, password: "Password is required" }));
      return;
    }
    setLoading(true);
    try {
      const data = await loginWithBackend(checkedIdentifier, form.password);
      await saveToken(data.access_token);
      await saveRefreshToken(data.refresh_token);
      await navigateAfterAuth(navigation);
    } catch (error: any) {
      Alert.alert("Sign In Failed", "Incorrect email or password.");
    } finally {
      setLoading(false);
    }
  };

  const validate = () => {
    const e: typeof errors = {};
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

  const handleRegister = async () => {
    if (!validate()) return;
    setLoading(true);
    try {
      await registerUser({
        email: checkedIdentifier,
        password: form.password,
        role_names: isDetailer ? ["detailer"] : ["client"],
      });
      
      if (isDetailer) {
        navigation.reset({
          index: 0,
          routes: [{ name: "DetailerOnboarding" }],
        });
      } else {
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
      }
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

  const isAnyLoading = loading || socialLoading !== null;

  const goBack = () => {
    if (flowState === "email") {
      navigation.goBack();
    } else if (flowState === "password") {
      setFlowState("email");
      setForm((f) => ({ ...f, password: "" }));
      setErrors((e) => ({ ...e, password: undefined }));
    } else if (flowState === "social_options") {
      setFlowState("email");
    } else if (flowState === "register") {
      setFlowState("email");
    }
  };

  const getTitle = () => {
    if (isDetailer) {
      switch (flowState) {
        case "email":
          return "Join as Pro";
        case "password":
          return "Welcome Back";
        case "social_options":
          return "Continue";
        case "register":
          return "Create Pro Account";
      }
    }
    switch (flowState) {
      case "email":
        return "Continue";
      case "password":
        return "Welcome Back";
      case "social_options":
        return "Continue";
      case "register":
        return "Create Account";
    }
  };

  const getSubtitle = () => {
    if (isDetailer) {
      switch (flowState) {
        case "email":
          return identifierType === "email" 
            ? "Enter your email to register as a detailer" 
            : "Enter your phone to register as a detailer";
        case "password":
          return `Sign in to ${checkedIdentifier}`;
        case "social_options":
          return "You previously signed in with a social account";
        case "register":
          return "Join RayCarWash as a professional detailer";
      }
    }
    switch (flowState) {
      case "email":
        return identifierType === "email" 
          ? "Enter your email to get started" 
          : "Enter your phone to get started";
      case "password":
        return `Sign in to ${checkedIdentifier}`;
      case "social_options":
        return "You previously signed in with a social account";
      case "register":
        return "Create your account";
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
            {flowState !== "email" && (
              <TouchableOpacity onPress={goBack} style={styles.backBtn}>
                <Ionicons name="chevron-back" size={22} color="white" />
              </TouchableOpacity>
            )}
            <Text style={styles.headerTitle}>{getTitle()}</Text>
            <View style={{ width: flowState === "email" ? 40 : 40 }} />
          </View>

          <ScrollView
            contentContainerStyle={styles.scroll}
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
          >
            <Text style={styles.subtitle}>{getSubtitle()}</Text>

            {/* SOCIAL BUTTONS - Shown before email input */}
            {flowState === "email" && (
              <>
                <View style={styles.socialRow}>
                  <TouchableOpacity
                    style={[styles.socialBtn, isAnyLoading && styles.btnDisabled]}
                    onPress={handleGooglePress}
                    disabled={isAnyLoading}
                  >
                    {socialLoading === "google" ? (
                      <ActivityIndicator size="small" color="#fff" />
                    ) : (
                      <>
                        <Text style={styles.googleG}>G</Text>
                        <Text style={styles.socialBtnText}>Continue with Google</Text>
                      </>
                    )}
                  </TouchableOpacity>

                  {Platform.OS === "ios" && (
                    <TouchableOpacity
                      style={[styles.socialBtn, styles.appleBtn, isAnyLoading && styles.btnDisabled]}
                      onPress={handleApplePress}
                      disabled={isAnyLoading}
                    >
                      {socialLoading === "apple" ? (
                        <ActivityIndicator size="small" color="#000" />
                      ) : (
                        <>
                          <Ionicons name="logo-apple" size={18} color="#000" />
                          <Text style={styles.appleBtnText}>Apple</Text>
                        </>
                      )}
                    </TouchableOpacity>
                  )}
                </View>

                <View style={styles.divider}>
                  <View style={styles.dividerLine} />
                  <Text style={styles.dividerText}>or</Text>
                  <View style={styles.dividerLine} />
                </View>
              </>
            )}

            {/* IDENTIFIER INPUT (email or phone) */}
            <View style={styles.fieldGroup}>
              <Text style={styles.label}>
                {identifierType === "email" ? "EMAIL ADDRESS" : "PHONE NUMBER"}
              </Text>
              <View
                style={[
                  styles.inputWrapper,
                  errors.email && styles.inputError,
                ]}
              >
                <Ionicons
                  name={identifierType === "email" ? "mail-outline" : "call-outline"}
                  size={18}
                  color="#475569"
                  style={styles.inputIcon}
                />
                <TextInput
                  style={[styles.input, flowState !== "email" && styles.inputDisabled]}
                  placeholder={identifierType === "email" ? "you@example.com" : "+1 (555) 000-0000"}
                  placeholderTextColor="#334155"
                  value={form.email}
                  onChangeText={(text) => {
                    update("email")(text);
                    // Auto-detect identifier type
                    const cleanText = text.replace(/[\s\-\(\)]/g, "");
                    if (/^\+?\d{10,}$/.test(cleanText)) {
                      setIdentifierType("phone");
                    } else if (text.includes("@")) {
                      setIdentifierType("email");
                    } else {
                      setIdentifierType("email");
                    }
                  }}
                  keyboardType={identifierType === "email" ? "email-address" : "phone-pad"}
                  autoCapitalize="none"
                  editable={flowState === "email"}
                />
              </View>
              {errors.email && (
                <Text style={styles.errorText}>{errors.email}</Text>
              )}
            </View>

            {/* PASSWORD (only if exists with password) */}
            {flowState === "password" && (
              <>
                <View style={styles.fieldGroup}>
                  <Text style={styles.label}>PASSWORD</Text>
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
                      placeholder="••••••••"
                      placeholderTextColor="#334155"
                      value={form.password}
                      onChangeText={update("password")}
                      secureTextEntry={!showPassword}
                      onSubmitEditing={handleLogin}
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
                </View>

                <TouchableOpacity
                  style={[styles.primaryBtn, isAnyLoading && styles.btnDisabled]}
                  onPress={handleLogin}
                  disabled={isAnyLoading}
                >
                  {loading ? (
                    <ActivityIndicator color="#fff" />
                  ) : (
                    <Text style={styles.primaryBtnText}>SIGN IN</Text>
                  )}
                </TouchableOpacity>
              </>
            )}

            {/* SOCIAL OPTIONS (only if exists with social only) */}
            {flowState === "social_options" && (
              <>
                <Text style={styles.socialMsg}>
                  It looks like you previously signed in with{" "}
                  {authMethod === "google" ? "Google" : "Apple"}. 
                  Continue with that account below.
                </Text>

                <View style={styles.socialRow}>
                  {authMethod === "google" || authMethod === "both" ? (
                    <TouchableOpacity
                      style={[styles.socialBtn, isAnyLoading && styles.btnDisabled]}
                      onPress={handleGooglePress}
                      disabled={isAnyLoading}
                    >
                      {socialLoading === "google" ? (
                        <ActivityIndicator size="small" color="#fff" />
                      ) : (
                        <>
                          <Text style={styles.googleG}>G</Text>
                          <Text style={styles.socialBtnText}>Continue with Google</Text>
                        </>
                      )}
                    </TouchableOpacity>
                  ) : null}

                  {authMethod === "apple" || authMethod === "both" ? (
                    Platform.OS === "ios" && (
                      <TouchableOpacity
                        style={[
                          styles.socialBtn,
                          styles.appleBtn,
                          isAnyLoading && styles.btnDisabled,
                        ]}
                        onPress={handleApplePress}
                        disabled={isAnyLoading}
                      >
                        {socialLoading === "apple" ? (
                          <ActivityIndicator size="small" color="#000" />
                        ) : (
                          <>
                            <Ionicons name="logo-apple" size={18} color="#000" />
                            <Text style={styles.appleBtnText}>Continue with Apple</Text>
                          </>
                        )}
                      </TouchableOpacity>
                    )
                  ) : null}
                </View>

                <TouchableOpacity
                  style={styles.switchMethod}
                  onPress={() => setFlowState("register")}
                >
                  <Text style={styles.switchMethodText}>
                    Or create a new account with email
                  </Text>
                </TouchableOpacity>
              </>
            )}

            {/* REGISTER FORM (only if doesn't exist) */}
            {flowState === "register" && (
              <>
                {/* Readonly identifier */}
                <View style={styles.fieldGroup}>
                  <Text style={styles.label}>
                    {identifierType === "email" ? "EMAIL" : "PHONE"}
                  </Text>
                  <View style={[styles.inputWrapper, styles.inputDisabled]}>
                    <Ionicons
                      name={identifierType === "email" ? "mail-outline" : "call-outline"}
                      size={18}
                      color="#475569"
                      style={styles.inputIcon}
                    />
                    <TextInput
                      style={[styles.input, styles.inputDisabledText]}
                      value={checkedIdentifier}
                      editable={false}
                    />
                  </View>
                </View>

                <Text style={styles.sectionLabel}>SECURITY</Text>

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
                </View>

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
              </>
            )}

            {/* CONTINUE BUTTON (for identifier step) */}
            {flowState === "email" && (
              <TouchableOpacity
                style={[styles.primaryBtn, isAnyLoading && styles.btnDisabled]}
                onPress={handleCheckIdentifier}
                disabled={isAnyLoading}
              >
                {loading ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={styles.primaryBtnText}>CONTINUE</Text>
                )}
              </TouchableOpacity>
            )}

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
  label: {
    color: "#94A3B8",
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1,
    marginBottom: 8,
  },
  sectionLabel: {
    color: "#475569",
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1,
    marginBottom: 14,
  },
  fieldGroup: { marginBottom: 16 },
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
  inputDisabled: { backgroundColor: "#1E293B" },
  inputDisabledText: { color: "#64748B" },
  eyeBtn: { padding: 14 },
  errorText: { color: "#EF4444", fontSize: 11, marginTop: 5, marginLeft: 4 },
  optionalBadge: {
    backgroundColor: "#1E293B",
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
    marginRight: 12,
  },
  optionalText: { color: "#475569", fontSize: 10, fontWeight: "700" },
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
  socialRow: { flexDirection: "row", gap: 12 },
  socialBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: "#161E2E",
    padding: 14,
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
  socialBtnText: { color: "#fff", fontWeight: "600", fontSize: 14 },
  appleBtn: { backgroundColor: "#fff" },
  appleBtnText: { color: "#000", fontWeight: "600", fontSize: 14 },
  socialMsg: {
    color: "#64748B",
    fontSize: 13,
    textAlign: "center",
    marginBottom: 16,
    lineHeight: 20,
  },
  switchMethod: { marginTop: 16, alignItems: "center" },
  switchMethodText: { color: Colors.primary, fontSize: 14, fontWeight: "600" },
  loginLink: { marginTop: 20, alignItems: "center" },
  loginLinkText: { color: "#475569", fontSize: 14 },
  loginLinkBold: { color: Colors.primary, fontWeight: "700" },
});