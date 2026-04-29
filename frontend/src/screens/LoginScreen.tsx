import * as AppleAuthentication from "expo-apple-authentication";
import * as LocalAuthentication from "expo-local-authentication";
import { LinearGradient } from "expo-linear-gradient";
import React, { useCallback, useEffect, useState } from "react";
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
import AnimatedInput, { EyeToggle } from "../components/AnimatedInput";
import {
  loginWithApple,
  loginWithEmail,
  refreshAccessToken,
  SocialAuthResponse,
} from "../services/auth.service";
import { Colors } from "../theme/colors";
import { navigateAfterAuth } from "../utils/auth-redirect";
import {
  getBiometricEnabled,
  getRefreshToken,
  saveRefreshToken,
  saveToken,
} from "../utils/storage";

export default function LoginScreen({ navigation }: any) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  const [loading, setLoading] = useState(false);
  const [biometricAvailable, setBiometricAvailable] = useState(false);

  useEffect(() => {
    checkBiometricAvailability();
  }, []);

  const checkBiometricAvailability = async () => {
    const hasHardware = await LocalAuthentication.hasHardwareAsync();
    const isEnrolled = await LocalAuthentication.isEnrolledAsync();
    const isEnabled = await getBiometricEnabled();
    const hasRefreshToken = !!(await getRefreshToken());
    setBiometricAvailable(hasHardware && isEnrolled && isEnabled && hasRefreshToken);
  };

  const validate = () => {
    const e: typeof errors = {};
    if (!email.trim()) e.email = "Email is required";
    else if (!/\S+@\S+\.\S+/.test(email)) e.email = "Enter a valid email";
    if (!password) e.password = "Password is required";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleAfterLogin = useCallback(
    async (accessToken: string, refreshToken: string | null, roles: string[]) => {
      await saveToken(accessToken);
      if (refreshToken) await saveRefreshToken(refreshToken);
      const role = roles[0];
      if (role === "detailer") {
        navigation.reset({ index: 0, routes: [{ name: "DetailerMain" }] });
      } else {
        navigation.reset({ index: 0, routes: [{ name: "Main" }] });
      }
    },
    [navigation],
  );

  const handleLogin = async () => {
    if (!validate()) return;
    setLoading(true);
    try {
      const result = await loginWithEmail(email, password);
      if (!result.onboarding_completed && result.onboarding_token) {
        await saveToken(result.onboarding_token);
        navigation.navigate("CompleteProfile");
        return;
      }
      if (result.access_token) {
        await handleAfterLogin(result.access_token, result.refresh_token, result.roles);
      }
    } catch (err: any) {
      const status = err.response?.status;
      if (status === 401 || status === 400) {
        setErrors({ password: "Incorrect email or password." });
        Alert.alert(
          "Login Failed",
          "Incorrect email or password. Don't have an account? Tap Sign Up.",
        );
      } else if (status === 429) {
        Alert.alert(
          "Too Many Attempts",
          "Your account is temporarily locked. Please try again later.",
        );
      } else if (!err.response) {
        Alert.alert(
          "Connection Error",
          "Cannot reach the server. Make sure your device is on the same Wi-Fi as the backend.",
        );
      } else {
        Alert.alert("Login Failed", "An unexpected error occurred. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleBiometric = async () => {
    try {
      const result = await LocalAuthentication.authenticateAsync({
        promptMessage: "Sign in to RayCarwash",
        fallbackLabel: "Use password",
      });
      if (!result.success) return;

      const storedRefresh = await getRefreshToken();
      if (!storedRefresh) {
        Alert.alert("Session Expired", "Please sign in with your password.");
        return;
      }

      setLoading(true);
      const tokens = await refreshAccessToken(storedRefresh);
      await saveToken(tokens.access_token);
      await saveRefreshToken(tokens.refresh_token);
      await navigateAfterAuth(navigation);
    } catch {
      Alert.alert("Biometric Failed", "Please sign in with your password.");
    } finally {
      setLoading(false);
    }
  };

  const handleSocialAuth = async (result: SocialAuthResponse) => {
    if (result.onboarding_required && result.onboarding_token) {
      await saveToken(result.onboarding_token);
      navigation.navigate("CompleteProfile");
    } else if (result.access_token) {
      await handleAfterLogin(
        result.access_token,
        result.refresh_token ?? null,
        result.active_role ? [result.active_role] : [],
      );
    }
  };

  const handleApple = async () => {
    try {
      const credential = await AppleAuthentication.signInAsync({
        requestedScopes: [
          AppleAuthentication.AppleAuthenticationScope.FULL_NAME,
          AppleAuthentication.AppleAuthenticationScope.EMAIL,
        ],
      });
      const fullName = [
        credential.fullName?.givenName,
        credential.fullName?.familyName,
      ]
        .filter(Boolean)
        .join(" ");
      const result = await loginWithApple(
        credential.identityToken!,
        fullName || undefined,
      );
      await handleSocialAuth(result);
    } catch (err: any) {
      if (err.code !== "ERR_REQUEST_CANCELED") {
        Alert.alert("Apple Sign In Failed", "Please try again.");
      }
    }
  };

  const handlePasskey = async () => {
    if (!email.trim()) {
      setErrors({ email: "Enter your email to use a passkey" });
      return;
    }
    // Passkey authentication requires react-native-passkey or a FIDO2 native module.
    // Backend endpoints are ready:
    //   POST /auth/webauthn/authenticate/begin  { email }
    //   POST /auth/webauthn/authenticate/complete  { challenge_token, credential }
    Alert.alert(
      "Passkeys",
      "Passkey support requires a native FIDO2 module. Coming soon.",
    );
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
          <ScrollView
            contentContainerStyle={styles.scroll}
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
          >
            {/* Logo / headline */}
            <View style={styles.headerSection}>
              <Text style={styles.brand}>RayCarwash</Text>
              <Text style={styles.tagline}>Premium mobile detailing, on demand</Text>
            </View>

            {/* Biometric quick-login (only shown after first login with biometrics enabled) */}
            {biometricAvailable && (
              <TouchableOpacity
                style={styles.biometricBtn}
                onPress={handleBiometric}
                disabled={loading}
              >
                <Text style={styles.biometricBtnText}>
                  Sign in with Face ID / Touch ID
                </Text>
              </TouchableOpacity>
            )}

            {/* Email */}
            <View style={styles.fieldGroup}>
              <AnimatedInput
                value={email}
                onChangeText={(v) => {
                  setEmail(v);
                  setErrors((e) => ({ ...e, email: undefined }));
                }}
                placeholder="Email address"
                icon="mail-outline"
                keyboardType="email-address"
                autoCapitalize="none"
                autoComplete="email"
                returnKeyType="next"
                error={!!errors.email}
              />
              {!!errors.email && (
                <Text style={styles.errorText}>{errors.email}</Text>
              )}
            </View>

            {/* Password */}
            <View style={styles.fieldGroup}>
              <AnimatedInput
                value={password}
                onChangeText={(v) => {
                  setPassword(v);
                  setErrors((e) => ({ ...e, password: undefined }));
                }}
                placeholder="Password"
                icon="lock-closed-outline"
                secureTextEntry={!showPassword}
                rightElement={
                  <EyeToggle
                    visible={showPassword}
                    onPress={() => setShowPassword((v) => !v)}
                  />
                }
                returnKeyType="done"
                onSubmitEditing={handleLogin}
                error={!!errors.password}
              />
              {!!errors.password && (
                <Text style={styles.errorText}>{errors.password}</Text>
              )}
            </View>

            {/* Forgot password */}
            <TouchableOpacity
              style={styles.forgotBtn}
              onPress={() => navigation.navigate("ForgotPassword")}
            >
              <Text style={styles.forgotText}>Forgot password?</Text>
            </TouchableOpacity>

            {/* Log In button */}
            <TouchableOpacity
              style={[styles.primaryBtn, loading && styles.btnDisabled]}
              onPress={handleLogin}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.primaryBtnText}>LOG IN</Text>
              )}
            </TouchableOpacity>

            {/* Divider */}
            <View style={styles.dividerRow}>
              <View style={styles.dividerLine} />
              <Text style={styles.dividerText}>or continue with</Text>
              <View style={styles.dividerLine} />
            </View>

            {/* Social + Passkey */}
            <View style={styles.altAuthRow}>
              <TouchableOpacity style={styles.altBtn} onPress={handleApple}>
                <Text style={styles.altBtnText}> Apple</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.altBtn} onPress={handlePasskey}>
                <Text style={styles.altBtnText}>🔑 Passkey</Text>
              </TouchableOpacity>
            </View>

            {/* Sign up link */}
            <View style={styles.footer}>
              <Text style={styles.footerText}>Don't have an account? </Text>
              <TouchableOpacity onPress={() => navigation.navigate("Register")}>
                <Text style={styles.footerLink}>Sign Up</Text>
              </TouchableOpacity>
            </View>

            <View style={{ height: 30 }} />
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { paddingHorizontal: 24, paddingTop: 40, paddingBottom: 20 },
  headerSection: { alignItems: "center", marginBottom: 40 },
  brand: {
    color: "#FFFFFF",
    fontSize: 32,
    fontWeight: "900",
    letterSpacing: 1,
  },
  tagline: { color: "#475569", fontSize: 14, marginTop: 6 },
  biometricBtn: {
    backgroundColor: "rgba(59,130,246,0.12)",
    borderWidth: 1,
    borderColor: Colors.primary,
    borderRadius: 14,
    padding: 14,
    alignItems: "center",
    marginBottom: 24,
  },
  biometricBtnText: {
    color: Colors.primary,
    fontSize: 14,
    fontWeight: "700",
  },
  fieldGroup: { marginBottom: 14 },
  errorText: { color: "#EF4444", fontSize: 11, marginTop: 5, marginLeft: 4 },
  forgotBtn: { alignSelf: "flex-end", marginBottom: 20 },
  forgotText: { color: Colors.primary, fontSize: 13 },
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
  dividerRow: {
    flexDirection: "row",
    alignItems: "center",
    marginVertical: 24,
    gap: 12,
  },
  dividerLine: { flex: 1, height: 1, backgroundColor: "#1E293B" },
  dividerText: { color: "#475569", fontSize: 12 },
  altAuthRow: { flexDirection: "row", gap: 12, marginBottom: 32 },
  altBtn: {
    flex: 1,
    backgroundColor: "#111827",
    borderWidth: 1,
    borderColor: "#1E293B",
    borderRadius: 12,
    padding: 14,
    alignItems: "center",
  },
  altBtnText: { color: "#CBD5E1", fontSize: 14, fontWeight: "600" },
  footer: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
  },
  footerText: { color: "#475569", fontSize: 14 },
  footerLink: { color: Colors.primary, fontSize: 14, fontWeight: "700" },
});
