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
import { useAppNavigation } from "../hooks/useAppNavigation";
import {
  loginWithApple,
  loginWithBackend,
  loginWithGoogle,
  requestPasswordReset,
} from "../services/auth.service";

import { Colors } from "../theme/colors";
import { navigateAfterAuth } from "../utils/auth-redirect";
import { saveRefreshToken, saveToken } from "../utils/storage";

WebBrowser.maybeCompleteAuthSession();

export default function LoginScreen() {
  const navigation = useAppNavigation();

  // Form State
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [socialLoading, setSocialLoading] = useState<"google" | "apple" | null>(
    null,
  );
  const [errors, setErrors] = useState<{ email?: string; password?: string; server?: string }>(
    {},
  );

  // ─── Google OAuth Hook ──────────────────────────────────────────────────────
  const [request, response, promptAsync] = Google.useAuthRequest({
    androidClientId: GOOGLE_CLIENT_IDS.android,
    iosClientId: GOOGLE_CLIENT_IDS.ios,
    webClientId: GOOGLE_CLIENT_IDS.web,
  });

  useEffect(() => {
    if (response?.type === "success") {
      const { authentication } = response;
      if (authentication?.accessToken) {
        handleSocialLogin("google", authentication.accessToken);
      }
    }
  }, [response]);

  const handleSocialLogin = async (
    provider: "google" | "apple",
    token: string,
    fullName?: string,
  ) => {
    setSocialLoading(provider);
    try {
      const data =
        provider === "google"
          ? await loginWithGoogle(token)
          : await loginWithApple(token, fullName);

      await saveToken(data.access_token);
      if (data.refresh_token) await saveRefreshToken(data.refresh_token);

      await navigateAfterAuth(navigation);
    } catch (error: any) {
      setErrors((prev) => ({ ...prev, server: error.message || "Something went wrong." }));
    } finally {
      setSocialLoading(null);
    }
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

      const data = await loginWithApple(
        credential.identityToken,
        fullName || undefined,
      );
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

  // ─── Email / Password ───────────────────────────────────────────────────────
  const validate = () => {
    const e: typeof errors = {};
    if (!email.trim()) e.email = "Email is required";
    else if (!/\S+@\S+\.\S+/.test(email)) e.email = "Enter a valid email";
    if (!password) e.password = "Password is required";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleLogin = async () => {
    if (!validate()) return;
    setLoading(true);
    try {
      const data = await loginWithBackend(email, password);
      await saveToken(data.access_token);
      await saveRefreshToken(data.refresh_token);
      await navigateAfterAuth(navigation);
    } catch (error: any) {
      const detail = error.response?.data?.detail;
      const msg = typeof detail === "string" ? detail : "Invalid email or password.";
      setErrors((prev) => ({ ...prev, server: msg }));
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = () => {
    if (!email.trim() || !/\S+@\S+\.\S+/.test(email)) {
      Alert.alert("Forgot Password", "Enter your email address above first.");
      return;
    }
    Alert.alert("Reset Password", `Send a link to ${email}?`, [
      { text: "Cancel", style: "cancel" },
      {
        text: "Send",
        onPress: async () => {
          try {
            await requestPasswordReset(email);
            Alert.alert("Email Sent", "Check your inbox.");
          } catch {
            Alert.alert("Error", "Could not send email.");
          }
        },
      },
    ]);
  };

  const isAnyLoading = loading || socialLoading !== null;

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
          <ScrollView
            contentContainerStyle={styles.scroll}
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
          >
            {/* Logo */}
            <View style={styles.logoContainer}>
              <View style={styles.logoCircle}>
                <Text style={styles.logoText}>R</Text>
              </View>
              <Text style={styles.appName}>RAYCARWASH</Text>
              <Text style={styles.tagline}>Premium Mobile Detailing</Text>
            </View>

            {/* Form */}
            <View style={styles.form}>
              {/* Email */}
              <View style={styles.fieldGroup}>
                <View style={styles.labelRow}>
                  <Text style={styles.label}>EMAIL ADDRESS</Text>
                </View>
                  <View
                    style={[
                      styles.inputWrapper,
                      errors.email && styles.inputError,
                    ]}
                  >
                  <Ionicons
                    name="mail-outline"
                    size={18}
                    color="#475569"
                    style={styles.inputIcon}
                  />
                  <TextInput
                    style={styles.input}
                    placeholder="you@example.com"
                    placeholderTextColor="#334155"
                    value={email}
                    onChangeText={(t) => {
                      setEmail(t);
                      setErrors((e) => ({ ...e, email: undefined, server: undefined }));
                    }}
                    keyboardType="email-address"
                    autoCapitalize="none"
                    returnKeyType="next"
                  />
                </View>
                {errors.email && (
                  <Text style={styles.errorText}>{errors.email}</Text>
                )}
              </View>

              {/* Password */}
              <View style={styles.fieldGroup}>
                <View style={styles.labelRow}>
                  <Text style={styles.label}>PASSWORD</Text>
                  <TouchableOpacity onPress={handleForgotPassword}>
                    <Text style={styles.forgotText}>Forgot password?</Text>
                  </TouchableOpacity>
                </View>
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
                    value={password}
                    onChangeText={(t) => {
                      setPassword(t);
                      setErrors((e) => ({ ...e, password: undefined, server: undefined }));
                    }}
                    secureTextEntry={!showPassword}
                    onSubmitEditing={handleLogin}
                  />
                  <TouchableOpacity
                    onPress={() => setShowPassword(!showPassword)}
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
                {errors.server && (
                  <Text style={styles.serverErrorText}>{errors.server}</Text>
                )}
              </View>

              {/* Primary Action */}
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

              {/* Divider */}
              <View style={styles.divider}>
                <View style={styles.dividerLine} />
                <Text style={styles.dividerText}>or continue with</Text>
                <View style={styles.dividerLine} />
              </View>

              {/* Social Buttons */}
              <View style={styles.socialRow}>
                <TouchableOpacity
                  style={[styles.socialBtn, isAnyLoading && styles.btnDisabled]}
                  onPress={() => promptAsync()}
                  disabled={isAnyLoading}
                >
                  {socialLoading === "google" ? (
                    <ActivityIndicator size="small" color="#fff" />
                  ) : (
                    <>
                      <Text style={styles.googleG}>G</Text>
                      <Text style={styles.socialBtnText}>Google</Text>
                    </>
                  )}
                </TouchableOpacity>

                {Platform.OS === "ios" && (
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
                        <Text style={styles.appleBtnText}>Apple</Text>
                      </>
                    )}
                  </TouchableOpacity>
                )}
              </View>

              {/* Footer */}
              <View style={styles.footerLinks}>
                <TouchableOpacity
                  style={styles.registerLink}
                  onPress={() => navigation.navigate("Register", { isDetailer: false })}
                >
                  <Text style={styles.registerText}>
                    Don't have an account?{" "}
                    <Text style={styles.registerTextBold}>Create one</Text>
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={styles.registerLink}
                  onPress={() => navigation.navigate("Register", { isDetailer: true })}
                >
                  <Text style={styles.registerText}>
                    Are you a detailer?{" "}
                    <Text style={styles.registerTextBold}>Register as Pro</Text>
                  </Text>
                </TouchableOpacity>
              </View>
            </View>
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { flexGrow: 1, padding: 28, justifyContent: "center" },
  logoContainer: { alignItems: "center", marginBottom: 44 },
  logoCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    borderWidth: 2,
    borderColor: Colors.primary,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "rgba(59,130,246,0.08)",
  },
  logoText: { color: Colors.primary, fontSize: 40, fontWeight: "bold" },
  appName: {
    color: "#fff",
    fontSize: 26,
    fontWeight: "bold",
    marginTop: 14,
    letterSpacing: 3,
  },
  tagline: { color: "#475569", fontSize: 12, marginTop: 5, letterSpacing: 1 },
  form: { gap: 4 },
  fieldGroup: { marginBottom: 18 },
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
  },
  forgotText: { color: Colors.primary, fontSize: 12, fontWeight: "600" },
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
  errorText: { color: "#EF4444", fontSize: 11, marginTop: 5, marginLeft: 4 },
  serverErrorText: { 
    color: "#EF4444", 
    fontSize: 13, 
    textAlign: "center", 
    marginTop: 12, 
    backgroundColor: "rgba(239,68,68,0.1)", 
    padding: 12, 
    borderRadius: 8,
  },
  primaryBtn: {
    backgroundColor: Colors.primary,
    padding: 17,
    borderRadius: 14,
    alignItems: "center",
    marginTop: 6,
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
    letterSpacing: 2,
  },
  divider: {
    flexDirection: "row",
    alignItems: "center",
    marginVertical: 24,
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
  registerLink: { marginTop: 16, alignItems: "center" },
  footerLinks: { gap: 8, alignItems: "center" },
  registerText: { color: "#475569", fontSize: 14 },
  registerTextBold: { color: Colors.primary, fontWeight: "700" },
});
