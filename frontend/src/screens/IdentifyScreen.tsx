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
import { identify, IdentifyResponse } from "../services/auth.service";
import { Colors } from "../theme/colors";

WebBrowser.maybeCompleteAuthSession();

export default function IdentifyScreen({ navigation, route }: any) {
  const { isDetailer } = route?.params || {};
  
  const [identifier, setIdentifier] = useState("");
  const [identifierType, setIdentifierType] = useState<"email" | "phone">("email");
  const [loading, setLoading] = useState(false);
  const [socialLoading, setSocialLoading] = useState<"google" | "apple" | null>(null);
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

  const handleSocialAuth = async (provider: "google" | "apple", token: string) => {
    setSocialLoading(provider);
    try {
      const result = await identify(token.toLowerCase(), provider);
      
      if (result.is_new_user || !result.exists) {
        navigation.navigate("Verify", {
          identifier: token,
          identifierType: provider,
          isNewUser: true,
          isDetailer,
        });
      } else {
        navigation.navigate("Verify", {
          identifier: result.identifier,
          identifierType: result.identifier_type,
          isNewUser: false,
          isDetailer,
        });
      }
    } catch (err: any) {
      Alert.alert("Error", "Could not continue with social login.");
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

      handleSocialAuth("apple", credential.identityToken);
    } catch (error: any) {
      if (error.code !== "ERR_REQUEST_CANCELED") {
        Alert.alert("Apple Sign-In", "Could not sign in with Apple.");
      }
    } finally {
      setSocialLoading(null);
    }
  };

  const handleContinue = async () => {
    if (!identifier.trim()) {
      setError("This field is required");
      return;
    }

    const isEmail = identifier.includes("@");
    if (identifierType === "email" && isEmail && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(identifier)) {
      setError("Enter a valid email address");
      return;
    }

    setLoading(true);
    setError(undefined);

    try {
      const result = await identify(identifier.trim(), identifierType);
      
      navigation.navigate("Verify", {
        identifier: result.identifier,
        identifierType: result.identifier_type,
        isNewUser: result.is_new_user,
        isDetailer,
      });
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Could not verify. Please try again.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const toggleType = () => {
    setIdentifierType((prev) => (prev === "email" ? "phone" : "email"));
    setIdentifier("");
    setError(undefined);
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
              {isDetailer ? "Join as Pro" : "Continue"}
            </Text>
            <View style={{ width: 40 }} />
          </View>

          <ScrollView
            contentContainerStyle={styles.scroll}
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
          >
            <Text style={styles.subtitle}>
              {isDetailer
                ? "Enter your email or phone to get started"
                : "Enter your email or phone to continue"}
            </Text>

            {/* Toggle Type */}
            <View style={styles.toggleRow}>
              <TouchableOpacity
                style={[
                  styles.toggleBtn,
                  identifierType === "email" && styles.toggleBtnActive,
                ]}
                onPress={() => identifierType !== "email" && toggleType()}
              >
                <Text
                  style={[
                    styles.toggleBtnText,
                    identifierType === "email" && styles.toggleBtnTextActive,
                  ]}
                >
                  Email
                </Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[
                  styles.toggleBtn,
                  identifierType === "phone" && styles.toggleBtnActive,
                ]}
                onPress={() => identifierType !== "phone" && toggleType()}
              >
                <Text
                  style={[
                    styles.toggleBtnText,
                    identifierType === "phone" && styles.toggleBtnTextActive,
                  ]}
                >
                  Phone
                </Text>
              </TouchableOpacity>
            </View>

            {/* Input */}
            <View style={styles.fieldGroup}>
              <Text style={styles.label}>
                {identifierType === "email" ? "EMAIL ADDRESS" : "PHONE NUMBER"}
              </Text>
              <View
                style={[
                  styles.inputWrapper,
                  error && styles.inputError,
                ]}
              >
                <Ionicons
                  name={identifierType === "email" ? "mail-outline" : "call-outline"}
                  size={18}
                  color="#475569"
                  style={styles.inputIcon}
                />
                <TextInput
                  style={styles.input}
                  placeholder={identifierType === "email" ? "you@example.com" : "+1 555 123 4567"}
                  placeholderTextColor="#334155"
                  value={identifier}
                  onChangeText={(text) => {
                    setIdentifier(text);
                    setError(undefined);
                  }}
                  keyboardType={identifierType === "email" ? "email-address" : "phone-pad"}
                  autoCapitalize="none"
                  autoCorrect={false}
                  returnKeyType="done"
                  onSubmitEditing={handleContinue}
                />
              </View>
              {error && (
                <Text style={styles.errorText}>{error}</Text>
              )}
            </View>

            {/* Continue Button */}
            <TouchableOpacity
              style={[styles.primaryBtn, isAnyLoading && styles.btnDisabled]}
              onPress={handleContinue}
              disabled={isAnyLoading}
            >
              {loading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.primaryBtnText}>CONTINUE</Text>
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

            {/* Sign In Link */}
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
  toggleRow: {
    flexDirection: "row",
    backgroundColor: "#161E2E",
    borderRadius: 12,
    padding: 4,
    marginBottom: 20,
  },
  toggleBtn: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: "center",
  },
  toggleBtnActive: {
    backgroundColor: Colors.primary,
  },
  toggleBtnText: {
    color: "#64748B",
    fontWeight: "600",
    fontSize: 14,
  },
  toggleBtnTextActive: {
    color: "#fff",
  },
  label: {
    color: "#94A3B8",
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1,
    marginBottom: 8,
  },
  fieldGroup: { marginBottom: 20 },
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
  loginLink: { marginTop: 20, alignItems: "center" },
  loginLinkText: { color: "#475569", fontSize: 14 },
  loginLinkBold: { color: Colors.primary, fontWeight: "700" },
});