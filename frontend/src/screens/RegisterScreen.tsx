import * as AppleAuthentication from "expo-apple-authentication";
import { LinearGradient } from "expo-linear-gradient";
import React, { useEffect, useState } from "react";
import {
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
import Button from "../components/Button";
import {
  loginWithApple,
  registerWithEmail,
  SocialAuthResponse,
} from "../services/auth.service";
import { Colors } from "../theme/colors";
import { navigateAfterAuth } from "../utils/auth-redirect";
import { saveOnboardingToken, saveRefreshToken, saveToken, setRegistrationPath, getRegistrationPath, removeRegistrationPath } from "../utils/storage";

export default function RegisterScreen({ navigation }: any) {
  const [form, setForm] = useState({ email: "", password: "", confirmPassword: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [isProviderPath, setIsProviderPath] = useState(false);

  useEffect(() => {
    getRegistrationPath().then((path) => setIsProviderPath(path === "provider"));
  }, []);

  const update = (field: keyof typeof form) => (value: string) => {
    setForm((f) => ({ ...f, [field]: value }));
    setErrors((e) => ({ ...e, [field]: "" }));
  };

  const handleProviderToggle = () => {
    const next = !isProviderPath;
    setIsProviderPath(next);
    setRegistrationPath(next);
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
    if (form.password !== form.confirmPassword) e.confirmPassword = "Passwords do not match";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

const handleRegister = async () => {
    if (!validate()) return;
    setLoading(true);
    try {
      const result = await registerWithEmail(form.email, form.password);
      if (result.onboarding_token) {
        await saveOnboardingToken(result.onboarding_token);
        navigation.navigate(isProviderPath ? "ProviderType" : "CompleteProfile");
      }
    } catch (err: any) {
      await removeRegistrationPath();
      const status = err.response?.status;
      const detail = err.response?.data?.detail;
      const msg =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
          ? detail.map((d: any) => d.msg?.replace(/^Value error, /, "")).join(". ")
          : "Registration failed. Please try again.";
      if (status === 409) {
        setErrors({ email: "An account with this email already exists." });
        Alert.alert("Account Already Exists", isProviderPath
          ? "Your account was already created. Log in to finish setting up your provider profile."
          : "An account with this email already exists.", [
          { text: "Log In", onPress: () => navigation.navigate("Login") },
          { text: "OK", style: "cancel" },
        ]);
      } else {
        Alert.alert("Registration Failed", msg);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSocialAuth = async (result: SocialAuthResponse) => {
    if (result.onboarding_required && result.onboarding_token) {
      await saveOnboardingToken(result.onboarding_token);
      navigation.navigate(isProviderPath ? "ProviderType" : "CompleteProfile");
    } else if (result.access_token) {
      await saveToken(result.access_token);
      if (result.refresh_token) await saveRefreshToken(result.refresh_token);
      await removeRegistrationPath();
      await navigateAfterAuth(navigation);
    }
  };

  const handleGoogle = () => {
    Alert.alert(
      "Google Sign In",
      "Google Sign In requires OAuth credentials to be configured. Please set GOOGLE_CLIENT_IDS in src/config/oauth.ts and configure the Google Cloud project.",
      [{ text: "OK", style: "default" }],
    );
  };

  const handleApple = async () => {
    try {
      const credential = await AppleAuthentication.signInAsync({
        requestedScopes: [
          AppleAuthentication.AppleAuthenticationScope.FULL_NAME,
          AppleAuthentication.AppleAuthenticationScope.EMAIL,
        ],
      });
      const fullName = [credential.fullName?.givenName, credential.fullName?.familyName]
        .filter(Boolean).join(" ");
      const result = await loginWithApple(credential.identityToken!, fullName || undefined);
      await handleSocialAuth(result);
    } catch (err: any) {
      if (err.code !== "ERR_REQUEST_CANCELED") {
        Alert.alert("Apple Sign In Failed", "Please try again.");
      }
    }
  };

  return (
    <View style={styles.container}>
      <LinearGradient colors={["#060A14", "#0B0F1A", "#101828"]} style={StyleSheet.absoluteFill} />
      <SafeAreaView style={{ flex: 1 }}>
        <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
          <ScrollView
            contentContainerStyle={styles.scroll}
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
          >
            <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
              <Text style={styles.backText}>← Back</Text>
            </TouchableOpacity>

            <Text style={styles.title}>Create Account</Text>
            <Text style={styles.subtitle}>Join RayCarwash to book premium mobile detailing</Text>

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
              {!!errors.email && <Text style={styles.errorText}>{errors.email}</Text>}
            </View>

            <View style={styles.fieldGroup}>
              <AnimatedInput
                value={form.password}
                onChangeText={update("password")}
                placeholder="Password (8+ chars, uppercase, number, symbol)"
                icon="lock-closed-outline"
                secureTextEntry={!showPassword}
                rightElement={<EyeToggle visible={showPassword} onPress={() => setShowPassword((v) => !v)} />}
                returnKeyType="next"
                error={!!errors.password}
              />
              {!!errors.password && <Text style={styles.errorText}>{errors.password}</Text>}
            </View>

            <View style={styles.fieldGroup}>
              <AnimatedInput
                value={form.confirmPassword}
                onChangeText={update("confirmPassword")}
                placeholder="Confirm password"
                icon="lock-closed-outline"
                secureTextEntry={!showConfirm}
                rightElement={<EyeToggle visible={showConfirm} onPress={() => setShowConfirm((v) => !v)} />}
                returnKeyType="done"
                onSubmitEditing={handleRegister}
                error={!!errors.confirmPassword}
              />
              {!!errors.confirmPassword && <Text style={styles.errorText}>{errors.confirmPassword}</Text>}
            </View>

            <Button
              title="SIGN UP"
              onPress={handleRegister}
              variant="primary"
              size="lg"
              fullWidth
              loading={loading}
              style={{ marginTop: 8 }}
            />

            <View style={styles.dividerRow}>
              <View style={styles.dividerLine} />
              <Text style={styles.dividerText}>or sign up with</Text>
              <View style={styles.dividerLine} />
            </View>

            <View style={styles.socialRow}>
              <Button title="G  Google" onPress={handleGoogle} variant="secondary" size="md" style={{ flex: 1 }} />
              <Button title=" Apple" onPress={handleApple} variant="secondary" size="md" style={{ flex: 1 }} />
            </View>

            <View style={styles.footer}>
              <Text style={styles.footerText}>Already have an account? </Text>
              <TouchableOpacity onPress={() => navigation.navigate("Login")}>
                <Text style={styles.footerLink}>Log In</Text>
              </TouchableOpacity>
            </View>

            <TouchableOpacity
              style={styles.providerToggle}
              onPress={handleProviderToggle}
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
  title: { color: "#FFFFFF", fontSize: 28, fontWeight: "800", marginBottom: 8 },
  subtitle: { color: "#64748B", fontSize: 14, marginBottom: 32, lineHeight: 20 },
  fieldGroup: { marginBottom: 14 },
  errorText: { color: "#EF4444", fontSize: 11, marginTop: 5, marginLeft: 4 },
  dividerRow: { flexDirection: "row", alignItems: "center", marginVertical: 24, gap: 12 },
  dividerLine: { flex: 1, height: 1, backgroundColor: "#1E293B" },
  dividerText: { color: "#475569", fontSize: 12 },
  socialRow: { flexDirection: "row", gap: 12, marginBottom: 32 },
  footer: { flexDirection: "row", justifyContent: "center", alignItems: "center" },
  footerText: { color: "#475569", fontSize: 14 },
  footerLink: { color: Colors.primary, fontSize: 14, fontWeight: "700" },
  providerToggle: { alignItems: "center", marginTop: 20, paddingVertical: 8 },
  providerToggleText: { color: "#475569", fontSize: 13, fontWeight: "600" },
  providerToggleActive: { color: Colors.primary },
});
