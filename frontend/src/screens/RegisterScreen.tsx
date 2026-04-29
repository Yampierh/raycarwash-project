import * as AppleAuthentication from "expo-apple-authentication";
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
import AnimatedInput, { EyeToggle } from "../components/AnimatedInput";
import {
  loginWithApple,
  registerWithEmail,
  SocialAuthResponse,
} from "../services/auth.service";
import { Colors } from "../theme/colors";
import { saveRefreshToken, saveToken } from "../utils/storage";

export default function RegisterScreen({ navigation }: any) {
  const [form, setForm] = useState({
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [isProviderPath, setIsProviderPath] = useState(false);

  const update = (field: keyof typeof form) => (value: string) => {
    setForm((f) => ({ ...f, [field]: value }));
    setErrors((e) => ({ ...e, [field]: "" }));
  };

  const validate = () => {
    const e: Record<string, string> = {};
    if (!form.email.trim()) e.email = "Email is required";
    else if (!/\S+@\S+\.\S+/.test(form.email)) e.email = "Enter a valid email";
    if (!form.password) {
      e.password = "Password is required";
    } else if (form.password.length < 8) {
      e.password = "At least 8 characters";
    } else if (!/[A-Z]/.test(form.password)) {
      e.password = "Must include an uppercase letter";
    } else if (!/[0-9]/.test(form.password)) {
      e.password = "Must include a number";
    } else if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(form.password)) {
      e.password = "Must include a special character (!@#$%^&* etc.)";
    }
    if (form.password !== form.confirmPassword)
      e.confirmPassword = "Passwords do not match";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleRegister = async () => {
    if (!validate()) return;
    setLoading(true);
    try {
      const result = await registerWithEmail(form.email, form.password);
      if (result.onboarding_token) {
        await saveToken(result.onboarding_token);
        if (isProviderPath) {
          navigation.navigate("ProviderType");
        } else {
          navigation.navigate("CompleteProfile");
        }
      }
    } catch (err: any) {
      const status = err.response?.status;
      const detail = err.response?.data?.detail;
      // Pydantic 422 detail is an array of {msg} objects
      const msg =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
          ? detail.map((d: any) => d.msg?.replace(/^Value error, /, "")).join(". ")
          : "Registration failed. Please try again.";
      if (status === 409) {
        setErrors({ email: "An account with this email already exists." });
      } else {
        Alert.alert("Registration Failed", msg);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSocialAuth = async (result: SocialAuthResponse) => {
    if (result.onboarding_required && result.onboarding_token) {
      await saveToken(result.onboarding_token);
      if (isProviderPath) {
        navigation.navigate("ProviderType");
      } else {
        navigation.navigate("CompleteProfile");
      }
    } else if (result.access_token) {
      await saveToken(result.access_token);
      if (result.refresh_token) await saveRefreshToken(result.refresh_token);
      const role = result.active_role;
      navigation.reset({
        index: 0,
        routes: [{ name: role === "detailer" ? "DetailerMain" : "Main" }],
      });
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
            {/* Header */}
            <TouchableOpacity
              style={styles.backBtn}
              onPress={() => navigation.goBack()}
            >
              <Text style={styles.backText}>← Back</Text>
            </TouchableOpacity>

            <Text style={styles.title}>Create Account</Text>
            <Text style={styles.subtitle}>
              Join RayCarwash to book premium mobile detailing
            </Text>

            {/* Email */}
            <View style={styles.fieldGroup}>
              <AnimatedInput
                value={form.email}
                onChangeText={update("email")}
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
                value={form.password}
                onChangeText={update("password")}
                placeholder="Password (8+ chars, uppercase, number, symbol)"
                icon="lock-closed-outline"
                secureTextEntry={!showPassword}
                rightElement={
                  <EyeToggle
                    visible={showPassword}
                    onPress={() => setShowPassword((v) => !v)}
                  />
                }
                returnKeyType="next"
                error={!!errors.password}
              />
              {!!errors.password && (
                <Text style={styles.errorText}>{errors.password}</Text>
              )}
            </View>

            {/* Confirm Password */}
            <View style={styles.fieldGroup}>
              <AnimatedInput
                value={form.confirmPassword}
                onChangeText={update("confirmPassword")}
                placeholder="Confirm password"
                icon="lock-closed-outline"
                secureTextEntry={!showConfirm}
                rightElement={
                  <EyeToggle
                    visible={showConfirm}
                    onPress={() => setShowConfirm((v) => !v)}
                  />
                }
                returnKeyType="done"
                onSubmitEditing={handleRegister}
                error={!!errors.confirmPassword}
              />
              {!!errors.confirmPassword && (
                <Text style={styles.errorText}>{errors.confirmPassword}</Text>
              )}
            </View>

            {/* Sign Up button */}
            <TouchableOpacity
              style={[styles.primaryBtn, loading && styles.btnDisabled]}
              onPress={handleRegister}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.primaryBtnText}>SIGN UP</Text>
              )}
            </TouchableOpacity>

            {/* Divider */}
            <View style={styles.dividerRow}>
              <View style={styles.dividerLine} />
              <Text style={styles.dividerText}>or sign up with</Text>
              <View style={styles.dividerLine} />
            </View>

            {/* Social buttons */}
            <View style={styles.socialRow}>
              {/* Google — requires expo-auth-session PKCE setup in LoginScreen */}
              <TouchableOpacity
                style={styles.socialBtn}
                onPress={() => navigation.navigate("Login")}
              >
                <Text style={styles.socialBtnText}>G  Google</Text>
              </TouchableOpacity>

              <TouchableOpacity style={styles.socialBtn} onPress={handleApple}>
                <Text style={styles.socialBtnText}> Apple</Text>
              </TouchableOpacity>
            </View>

            {/* Link to Login */}
            <View style={styles.footer}>
              <Text style={styles.footerText}>Already have an account? </Text>
              <TouchableOpacity onPress={() => navigation.navigate("Login")}>
                <Text style={styles.footerLink}>Log In</Text>
              </TouchableOpacity>
            </View>

            {/* Provider path toggle */}
            <TouchableOpacity
              style={styles.providerToggle}
              onPress={() => setIsProviderPath((v) => !v)}
              activeOpacity={0.7}
            >
              <Text style={[styles.providerToggleText, isProviderPath && styles.providerToggleActive]}>
                {isProviderPath ? "✓ Joining as Service Provider →" : "Become a Service Provider →"}
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
  scroll: { paddingHorizontal: 24, paddingTop: 16, paddingBottom: 20 },
  backBtn: { marginBottom: 24 },
  backText: { color: Colors.primary, fontSize: 15 },
  title: {
    color: "#FFFFFF",
    fontSize: 28,
    fontWeight: "800",
    marginBottom: 8,
  },
  subtitle: {
    color: "#64748B",
    fontSize: 14,
    marginBottom: 32,
    lineHeight: 20,
  },
  fieldGroup: { marginBottom: 14 },
  errorText: { color: "#EF4444", fontSize: 11, marginTop: 5, marginLeft: 4 },
  primaryBtn: {
    backgroundColor: Colors.primary,
    padding: 17,
    borderRadius: 14,
    alignItems: "center",
    marginTop: 8,
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
  socialRow: { flexDirection: "row", gap: 12, marginBottom: 32 },
  socialBtn: {
    flex: 1,
    backgroundColor: "#111827",
    borderWidth: 1,
    borderColor: "#1E293B",
    borderRadius: 12,
    padding: 14,
    alignItems: "center",
  },
  socialBtnText: { color: "#CBD5E1", fontSize: 14, fontWeight: "600" },
  footer: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
  },
  footerText: { color: "#475569", fontSize: 14 },
  footerLink: { color: Colors.primary, fontSize: 14, fontWeight: "700" },
  providerToggle: {
    alignItems: "center",
    marginTop: 20,
    paddingVertical: 8,
  },
  providerToggleText: {
    color: "#475569",
    fontSize: 13,
    fontWeight: "600",
  },
  providerToggleActive: {
    color: Colors.primary,
  },
});
