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
import { verify, VerifyResponse } from "../services/auth.service";
import { Colors } from "../theme/colors";
import { navigateAfterAuth } from "../utils/auth-redirect";
import { saveRefreshToken, saveToken } from "../utils/storage";

WebBrowser.maybeCompleteAuthSession();

export default function VerifyScreen({ navigation, route }: any) {
  const { identifier, identifierType, isNewUser, isDetailer } = route.params || {};

  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [socialLoading, setSocialLoading] = useState<"google" | "apple" | null>(
    null,
  );
  const [error, setError] = useState<string | undefined>();

  // Google OAuth
  const [, googleResponse, googlePromptAsync] = Google.useAuthRequest({
    clientId: GOOGLE_CLIENT_IDS.web,
    iosClientId: GOOGLE_CLIENT_IDS.ios,
    androidClientId: GOOGLE_CLIENT_IDS.android,
  });

  useEffect(() => {
    if (googleResponse?.type === "success") {
      const token = googleResponse.authentication?.accessToken;
      if (token) handleSocialAuth("google", token);
    }
    if (googleResponse?.type === "error") {
      setSocialLoading(null);
      Alert.alert("Google Sign-In", "Authentication failed. Please try again.");
    }
  }, [googleResponse]);

  const handleSocialAuth = async (
    provider: "google" | "apple",
    token: string,
  ) => {
    setSocialLoading(provider);
    try {
      const result = await verify(identifier, identifierType, {
        accessToken: token,
      });
      await handleVerifyResponse(result);
    } catch (err: any) {
      Alert.alert("Error", "Could not continue with social login.");
    } finally {
      setSocialLoading(null);
    }
  };

  const handleVerifyResponse = async (result: VerifyResponse) => {
    if (result.access_token) {
      await saveToken(result.access_token);
      if (result.refresh_token) {
        await saveRefreshToken(result.refresh_token);
      }
    }

    if (result.needs_profile_completion && result.temp_token) {
      navigation.navigate("CompleteProfile", {
        tempToken: result.temp_token,
        role: result.assigned_role || (isDetailer ? "detailer" : "client"),
        identifier,
        identifierType,
      });
    } else if (result.next_step === "detailer_onboarding") {
      navigation.reset({
        index: 0,
        routes: [{ name: "DetailerOnboarding" }],
      });
    } else if (result.access_token) {
      await navigateAfterAuth(navigation);
    } else {
      setError("Authentication failed. Please try again.");
    }
  };

  const handleLogin = async () => {
    if (!password) {
      setError("Password is required");
      return;
    }

    setLoading(true);
    setError(undefined);

    try {
      const result = await verify(identifier, identifierType, {
        password,
      });
      await handleVerifyResponse(result);
    } catch (err: any) {
      setError("Incorrect password. Please try again.");
    } finally {
      setLoading(false);
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

      handleSocialAuth("apple", credential.identityToken);
    } catch (error: any) {
      if (error.code !== "ERR_REQUEST_CANCELED") {
        Alert.alert("Apple Sign-In", "Could not sign in with Apple.");
      }
    } finally {
      setSocialLoading(null);
    }
  };

  const handleForgotPassword = () => {
    navigation.navigate("PasswordReset", { identifier });
  };

  const handleCreateAccount = () => {
    navigation.navigate("Register", { isDetailer });
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
          <View style={styles.header}>
            <TouchableOpacity
              onPress={() => navigation.goBack()}
              style={styles.backBtn}
            >
              <Ionicons name="chevron-back" size={22} color="white" />
            </TouchableOpacity>
            <Text style={styles.headerTitle}>
              {isNewUser ? "Create Account" : "Welcome Back"}
            </Text>
            <View style={{ width: 40 }} />
          </View>

          <ScrollView
            contentContainerStyle={styles.scroll}
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
          >
            <Text style={styles.subtitle}>
              {isNewUser
                ? `Create account with ${identifier}`
                : `Sign in to ${identifier}`}
            </Text>

            {/* Show identifier */}
            <View style={styles.identifierRow}>
              <Ionicons
                name={identifierType === "email" ? "mail-outline" : "call-outline"}
                size={18}
                color={Colors.primary}
              />
              <Text style={styles.identifierText}>{identifier}</Text>
            </View>

            {/* Password Input (only for password auth) */}
            {!isNewUser && (
              <>
                <View style={styles.fieldGroup}>
                  <Text style={styles.label}>PASSWORD</Text>
                  <View
                    style={[
                      styles.inputWrapper,
                      error && styles.inputError,
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
                      onChangeText={(text) => {
                        setPassword(text);
                        setError(undefined);
                      }}
                      secureTextEntry={!showPassword}
                      returnKeyType="done"
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
                  {error && <Text style={styles.errorText}>{error}</Text>}
                </View>

                <TouchableOpacity
                  style={[
                    styles.primaryBtn,
                    isAnyLoading && styles.btnDisabled,
                  ]}
                  onPress={handleLogin}
                  disabled={isAnyLoading}
                >
                  {loading ? (
                    <ActivityIndicator color="#fff" />
                  ) : (
                    <Text style={styles.primaryBtnText}>SIGN IN</Text>
                  )}
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.forgotLink}
                  onPress={handleForgotPassword}
                >
                  <Text style={styles.forgotLinkText}>Forgot password?</Text>
                </TouchableOpacity>

                <View style={styles.divider}>
                  <View style={styles.dividerLine} />
                  <Text style={styles.dividerText}>or continue with</Text>
                  <View style={styles.dividerLine} />
                </View>
              </>
            )}

            {/* Social Buttons */}
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

            {/* Create Account Link (for new users) */}
            {isNewUser && (
              <TouchableOpacity
                style={styles.switchMethod}
                onPress={handleCreateAccount}
              >
                <Text style={styles.switchMethodText}>
                  Or create a new account
                </Text>
              </TouchableOpacity>
            )}

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
    marginBottom: 20,
    textAlign: "center",
  },
  identifierRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    marginBottom: 24,
    backgroundColor: "#161E2E",
    padding: 12,
    borderRadius: 12,
  },
  identifierText: { color: "#fff", fontSize: 15, fontWeight: "500" },
  label: {
    color: "#94A3B8",
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1,
    marginBottom: 8,
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
  eyeBtn: { padding: 14 },
  errorText: { color: "#EF4444", fontSize: 11, marginTop: 5, marginLeft: 4 },
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
  forgotLink: { alignItems: "center", marginTop: 12 },
  forgotLinkText: { color: Colors.primary, fontSize: 13, fontWeight: "500" },
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
  switchMethod: { marginTop: 20, alignItems: "center" },
  switchMethodText: { color: Colors.primary, fontSize: 14, fontWeight: "600" },
});