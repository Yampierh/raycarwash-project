import { Ionicons } from "@expo/vector-icons";
import * as AppleAuthentication from "expo-apple-authentication";
import * as Google from "expo-auth-session/providers/google";
import * as LocalAuthentication from "expo-local-authentication";
import { LinearGradient } from "expo-linear-gradient";
import * as WebBrowser from "expo-web-browser";
import React, { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Animated,
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
import { GOOGLE_CLIENT_IDS } from "../config/oauth";
import { useAppNavigation } from "../hooks/useAppNavigation";
import {
  IdentifyResponse,
  identify,
  loginWithApple,
  loginWithGoogle,
  refreshAccessToken,
  requestPasswordReset,
  verify,
  webAuthnAuthenticateBegin,
  webAuthnAuthenticateComplete,
  webAuthnRegisterBegin,
  webAuthnRegisterComplete,
} from "../services/auth.service";
import { Colors } from "../theme/colors";
import { navigateAfterAuth } from "../utils/auth-redirect";
import {
  getBiometricEnabled,
  getPasskeyEnabled,
  getRefreshToken,
  saveLastEmail,
  saveRefreshToken,
  saveToken,
  setBiometricEnabled,
  setPasskeyEnabled,
} from "../utils/storage";

// Lazy import to avoid hard crash on devices/builds without native passkey support
let Passkey: typeof import("react-native-passkey").Passkey | null = null;
try {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  Passkey = require("react-native-passkey").Passkey;
} catch {
  // Not available (Expo Go, web, or unsupported OS) — passkey UI will be hidden
}

WebBrowser.maybeCompleteAuthSession();

type FlowStep = "identifier" | "existing_password" | "new_user" | "social_only";

function getPasswordStrength(pwd: string) {
  if (!pwd) return { label: "", color: "#1E293B", bars: 0 };
  const hasUpper = /[A-Z]/.test(pwd);
  const hasNumber = /[0-9]/.test(pwd);
  const hasSpecial = /[^A-Za-z0-9]/.test(pwd);
  if (pwd.length >= 12 && hasUpper && hasNumber && hasSpecial)
    return { label: "Strong", color: "#10B981", bars: 4 };
  if (pwd.length >= 8 && (hasUpper || hasNumber))
    return { label: "Good", color: "#3B82F6", bars: 3 };
  if (pwd.length >= 6) return { label: "Fair", color: "#F59E0B", bars: 2 };
  return { label: "Weak", color: "#EF4444", bars: 1 };
}

// ── Step Dots ─────────────────────────────────────────────────────────────────

function StepDots({ current }: { current: 1 | 2 }) {
  return (
    <View style={styles.stepDots}>
      <View style={[styles.dot, current === 1 && styles.dotActive]} />
      <View style={[styles.dot, current === 2 && styles.dotActive]} />
    </View>
  );
}

// ── Main Screen ───────────────────────────────────────────────────────────────

export default function LoginScreen() {
  const navigation = useAppNavigation();

  const [step, setStep] = useState<FlowStep>("identifier");
  const [identifier, setIdentifier] = useState("");
  const [identifierType, setIdentifierType] = useState<"email" | "phone">("email");
  const [identifyData, setIdentifyData] = useState<IdentifyResponse | null>(null);

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  // Detailer mode — same flow, different role assignment
  const [isDetailerMode, setIsDetailerMode] = useState(false);

  // Biometric state
  const [biometricAvailable, setBiometricAvailable] = useState(false);
  const [biometricEnabled, setBiometricEnabledState] = useState(false);

  // Passkey state
  const [passkeyAvailable, setPasskeyAvailable] = useState(false);
  const [passkeyEnabled, setPasskeyEnabledState] = useState(false);
  const [passkeyLoading, setPasskeyLoading] = useState(false);

  const [loading, setLoading] = useState(false);
  const [biometricLoading, setBiometricLoading] = useState(false);
  const [socialLoading, setSocialLoading] = useState<"google" | "apple" | null>(null);
  const [errors, setErrors] = useState<{
    identifier?: string;
    password?: string;
    confirm?: string;
    server?: string;
  }>({});

  // Slide animation
  const slideAnim = useRef(new Animated.Value(0)).current;
  const slideToNext = () => {
    slideAnim.setValue(320);
    Animated.spring(slideAnim, {
      toValue: 0,
      useNativeDriver: true,
      tension: 65,
      friction: 11,
    }).start();
  };

  useEffect(() => {
    checkBiometricAvailability();
    checkPasskeyAvailability();
  }, []);

  const checkBiometricAvailability = async () => {
    const hardware = await LocalAuthentication.hasHardwareAsync();
    const enrolled = await LocalAuthentication.isEnrolledAsync();
    const enabled = await getBiometricEnabled();
    setBiometricAvailable(hardware && enrolled);
    setBiometricEnabledState(enabled);
  };

  const checkPasskeyAvailability = async () => {
    if (!Passkey) return;
    try {
      const supported = Passkey.isSupported();
      const enabled = await getPasskeyEnabled();
      setPasskeyAvailable(supported);
      setPasskeyEnabledState(enabled);
    } catch {
      // Passkey not supported on this device/OS version
    }
  };

  // ── Google OAuth ──────────────────────────────────────────────────────────────
  const [, googleResponse, googlePromptAsync] = Google.useAuthRequest({
    androidClientId: GOOGLE_CLIENT_IDS.android,
    iosClientId: GOOGLE_CLIENT_IDS.ios,
    webClientId: GOOGLE_CLIENT_IDS.web,
  });

  useEffect(() => {
    if (googleResponse?.type === "success") {
      const token = googleResponse.authentication?.accessToken;
      if (token) handleSocialLogin("google", token);
    }
  }, [googleResponse]);

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
      await offerPasskeySetup();
      await offerBiometricSetup();
      await navigateAfterAuth(navigation);
    } catch (err: any) {
      setErrors({ server: err.response?.data?.detail || "Social login failed." });
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
      await handleSocialLogin("apple", credential.identityToken, fullName || undefined);
    } catch (err: any) {
      if (err.code !== "ERR_REQUEST_CANCELED")
        Alert.alert("Apple Sign-In", "Could not sign in with Apple.");
    }
  };

  // ── Biometric login ───────────────────────────────────────────────────────────
  const handleBiometricLogin = async () => {
    setBiometricLoading(true);
    try {
      const result = await LocalAuthentication.authenticateAsync({
        promptMessage: "Sign in to RayCarWash",
        cancelLabel: "Cancel",
        disableDeviceFallback: false,
      });

      if (!result.success) return;

      // Use stored refresh token to get a fresh access token
      const refreshToken = await getRefreshToken();
      if (!refreshToken) {
        Alert.alert("Session expired", "Please sign in with your password.");
        return;
      }
      const { access_token, refresh_token } = await refreshAccessToken(refreshToken);
      await saveToken(access_token);
      await saveRefreshToken(refresh_token);
      await navigateAfterAuth(navigation);
    } catch {
      Alert.alert("Biometric Error", "Could not authenticate. Please use your password.");
    } finally {
      setBiometricLoading(false);
    }
  };

  // ── Passkey login ─────────────────────────────────────────────────────────────
  const handlePasskeyLogin = async () => {
    if (!Passkey) return;
    const id = identifier.trim();
    if (!id || !/\S+@\S+\.\S+/.test(id)) {
      Alert.alert("Passkey", "Enter your email first, then tap the passkey button.");
      return;
    }
    setPasskeyLoading(true);
    try {
      const { challenge_token, options } = await webAuthnAuthenticateBegin(id);
      const assertion = await Passkey.authenticate(options as any);
      const { access_token, refresh_token } = await webAuthnAuthenticateComplete(
        challenge_token,
        assertion as any,
      );
      await saveToken(access_token);
      await saveRefreshToken(refresh_token);
      await navigateAfterAuth(navigation);
    } catch (err: any) {
      if (err?.error !== "UserCancelled") {
        Alert.alert("Passkey Error", err.response?.data?.detail || "Passkey authentication failed.");
      }
    } finally {
      setPasskeyLoading(false);
    }
  };

  const offerPasskeySetup = async () => {
    if (!Passkey || !passkeyAvailable || passkeyEnabled) return;
    return new Promise<void>((resolve) => {
      Alert.alert(
        "Save a Passkey?",
        "Sign in faster next time with Face ID or fingerprint — no password needed.",
        [
          { text: "Not now", style: "cancel", onPress: () => resolve() },
          {
            text: "Save Passkey",
            onPress: async () => {
              try {
                const deviceName =
                  Platform.OS === "ios" ? "iPhone" : "Android Device";
                const { challenge_token, options } = await webAuthnRegisterBegin();
                const attestation = await Passkey.register(options as any);
                await webAuthnRegisterComplete(
                  challenge_token,
                  attestation as any,
                  deviceName,
                );
                await setPasskeyEnabled(true);
                setPasskeyEnabledState(true);
              } catch {
                // User cancelled or registration failed — silently skip
              }
              resolve();
            },
          },
        ],
      );
    });
  };

  const offerBiometricSetup = async () => {
    if (!biometricAvailable || biometricEnabled) return;
    const types = await LocalAuthentication.supportedAuthenticationTypesAsync();
    const hasFaceId = types.includes(
      LocalAuthentication.AuthenticationType.FACIAL_RECOGNITION,
    );
    const label = hasFaceId ? "Face ID" : "fingerprint";

    return new Promise<void>((resolve) => {
      Alert.alert(
        `Enable ${hasFaceId ? "Face ID" : "Biometric"} login?`,
        `Sign in faster next time using your ${label}.`,
        [
          {
            text: "Not now",
            style: "cancel",
            onPress: () => resolve(),
          },
          {
            text: "Enable",
            onPress: async () => {
              await setBiometricEnabled(true);
              setBiometricEnabledState(true);
              resolve();
            },
          },
        ],
      );
    });
  };

  // ── Step 1: Identify ──────────────────────────────────────────────────────────
  const handleIdentify = async () => {
    const id = identifier.trim();
    if (!id) {
      setErrors({
        identifier:
          identifierType === "email" ? "Email is required" : "Phone is required",
      });
      return;
    }
    if (identifierType === "email" && !/\S+@\S+\.\S+/.test(id)) {
      setErrors({ identifier: "Enter a valid email address" });
      return;
    }

    setLoading(true);
    setErrors({});
    try {
      const result = await identify(id, identifierType);
      setIdentifyData(result);

      let next: FlowStep;
      if (result.is_new_user) {
        next = "new_user";
      } else if (result.auth_methods.includes("password")) {
        next = "existing_password";
      } else {
        next = "social_only";
      }
      setStep(next);
      slideToNext();
    } catch (err: any) {
      const msg =
        err.response?.data?.detail || "Could not verify. Please try again.";
      setErrors({ server: msg });
    } finally {
      setLoading(false);
    }
  };

  // ── Step 2a: Login existing user ──────────────────────────────────────────────
  const handleLogin = async () => {
    if (!password) {
      setErrors({ password: "Password is required" });
      return;
    }
    setLoading(true);
    setErrors({});
    try {
      const result = await verify(identifier.trim(), identifierType, { password });
      await handleVerifyResult(result);
    } catch {
      setErrors({ password: "Incorrect password. Please try again." });
    } finally {
      setLoading(false);
    }
  };

  // ── Step 2b: Register new user ────────────────────────────────────────────────
  const handleCreateAccount = async () => {
    const e: typeof errors = {};
    if (!password) e.password = "Password is required";
    else if (password.length < 8) e.password = "Password must be at least 8 characters";
    if (!confirmPassword) e.confirm = "Please confirm your password";
    else if (password !== confirmPassword) e.confirm = "Passwords do not match";
    if (Object.keys(e).length) {
      setErrors(e);
      return;
    }

    setLoading(true);
    setErrors({});
    try {
      const result = await verify(identifier.trim(), identifierType, { password });
      await handleVerifyResult(result);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      const msg = typeof detail === "string" ? detail : "Could not create account.";
      setErrors({ server: msg });
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyResult = async (result: Awaited<ReturnType<typeof verify>>) => {
    if (result.access_token) {
      await saveToken(result.access_token);
      if (result.refresh_token) await saveRefreshToken(result.refresh_token);
      await saveLastEmail(identifier.trim().toLowerCase());
    }

    if (result.needs_profile_completion && result.temp_token) {
      navigation.navigate("CompleteProfile", {
        tempToken: result.temp_token,
        role: isDetailerMode ? "detailer" : result.assigned_role,
        identifier: identifier.trim(),
        identifierType,
      });
      return;
    }

    await offerPasskeySetup();
    await offerBiometricSetup();

    if (result.next_step === "detailer_onboarding" || isDetailerMode) {
      navigation.reset({ index: 0, routes: [{ name: "DetailerOnboarding" }] });
      return;
    }
    await navigateAfterAuth(navigation);
  };

  const handleForgotPassword = () => {
    const id = identifier.trim();
    if (!id || !/\S+@\S+\.\S+/.test(id)) {
      Alert.alert("Reset Password", "Please go back and enter your email first.");
      return;
    }
    Alert.alert("Reset Password", `Send a reset link to ${id}?`, [
      { text: "Cancel", style: "cancel" },
      {
        text: "Send",
        onPress: async () => {
          try {
            await requestPasswordReset(id);
            Alert.alert("Email Sent", "Check your inbox for the reset link.");
          } catch {
            Alert.alert("Error", "Could not send reset email.");
          }
        },
      },
    ]);
  };

  const toggleDetailerMode = () => {
    setIsDetailerMode((v) => !v);
  };

  const goBack = () => {
    setStep("identifier");
    setPassword("");
    setConfirmPassword("");
    setErrors({});
  };

  const isAnyLoading = loading || biometricLoading || passkeyLoading || socialLoading !== null;
  const currentStep: 1 | 2 = step === "identifier" ? 1 : 2;
  const pwStrength = getPasswordStrength(password);
  const showBiometric = biometricAvailable && biometricEnabled && step === "identifier";
  const showPasskey = passkeyAvailable && passkeyEnabled && step === "identifier";

  const getBiometricIcon = () => {
    // iOS Face ID vs Touch ID vs Android fingerprint
    if (Platform.OS === "ios") return "scan-outline";
    return "finger-print-outline";
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
          {/* Header */}
          <View style={styles.header}>
            {step !== "identifier" ? (
              <TouchableOpacity onPress={goBack} style={styles.backBtn}>
                <Ionicons name="chevron-back" size={22} color="white" />
              </TouchableOpacity>
            ) : (
              <View style={{ width: 40 }} />
            )}
            <StepDots current={currentStep} />
            <View style={{ width: 40 }} />
          </View>

          <ScrollView
            contentContainerStyle={styles.scroll}
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
          >
            {/* Logo + detailer mode badge — step 1 only */}
            {step === "identifier" && (
              <View style={styles.logoContainer}>
                <View style={styles.logoCircle}>
                  <Text style={styles.logoText}>R</Text>
                </View>
                <Text style={styles.appName}>RAYCARWASH</Text>
                {isDetailerMode ? (
                  <View style={styles.proBadge}>
                    <Ionicons name="car-sport-outline" size={12} color={Colors.primary} />
                    <Text style={styles.proBadgeText}>DETAILER PRO MODE</Text>
                  </View>
                ) : (
                  <Text style={styles.tagline}>Premium Mobile Detailing</Text>
                )}
              </View>
            )}

            <Animated.View style={{ transform: [{ translateX: slideAnim }] }}>
              {/* ── STEP 1: Identifier ── */}
              {step === "identifier" && (
                <>
                  {/* Email input */}
                  <View style={styles.fieldGroup}>
                    <Text style={styles.label}>
                      {identifierType === "email" ? "EMAIL ADDRESS" : "PHONE NUMBER"}
                    </Text>
                    <AnimatedInput
                      value={identifier}
                      onChangeText={(t) => {
                        setIdentifier(t);
                        setErrors({});
                        const clean = t.replace(/[\s\-\(\)]/g, "");
                        if (/^\+?\d{8,}$/.test(clean)) setIdentifierType("phone");
                        else setIdentifierType("email");
                      }}
                      placeholder={
                        identifierType === "email"
                          ? "you@example.com"
                          : "+1 555 000 0000"
                      }
                      icon={
                        identifierType === "email" ? "mail-outline" : "call-outline"
                      }
                      keyboardType={
                        identifierType === "email" ? "email-address" : "phone-pad"
                      }
                      returnKeyType="go"
                      onSubmitEditing={handleIdentify}
                      error={!!errors.identifier}
                    />
                    {errors.identifier && (
                      <Text style={styles.errorText}>{errors.identifier}</Text>
                    )}
                    {errors.server && (
                      <Text style={styles.serverError}>{errors.server}</Text>
                    )}
                  </View>

                  <TouchableOpacity
                    style={[styles.primaryBtn, isAnyLoading && styles.btnDisabled]}
                    onPress={handleIdentify}
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

                  {/* Social buttons — full-width, stacked */}
                  <View style={styles.socialStack}>
                    {/* Google */}
                    <TouchableOpacity
                      style={[styles.googleBtn, isAnyLoading && styles.btnDisabled]}
                      onPress={() => googlePromptAsync()}
                      disabled={isAnyLoading}
                      activeOpacity={0.85}
                    >
                      {socialLoading === "google" ? (
                        <ActivityIndicator size="small" color="#1a1a1a" />
                      ) : (
                        <>
                          {/* Colorful Google G */}
                          <View style={styles.googleIconBox}>
                            <Text style={styles.googleGBlue}>G</Text>
                          </View>
                          <Text style={styles.googleBtnText}>Continue with Google</Text>
                        </>
                      )}
                    </TouchableOpacity>

                    {/* Apple (iOS only) */}
                    {Platform.OS === "ios" && (
                      <TouchableOpacity
                        style={[styles.appleFullBtn, isAnyLoading && styles.btnDisabled]}
                        onPress={handleApplePress}
                        disabled={isAnyLoading}
                        activeOpacity={0.85}
                      >
                        {socialLoading === "apple" ? (
                          <ActivityIndicator size="small" color="#fff" />
                        ) : (
                          <>
                            <Ionicons name="logo-apple" size={20} color="#fff" style={styles.socialIcon} />
                            <Text style={styles.appleFullBtnText}>Continue with Apple</Text>
                          </>
                        )}
                      </TouchableOpacity>
                    )}

                    {/* Quick-access row: Biometric + Passkey (conditional) */}
                    {(showBiometric || showPasskey) && (
                      <View style={styles.quickRow}>
                        {showBiometric && (
                          <TouchableOpacity
                            style={[styles.quickBtn, isAnyLoading && styles.btnDisabled]}
                            onPress={handleBiometricLogin}
                            disabled={isAnyLoading}
                            activeOpacity={0.8}
                          >
                            {biometricLoading ? (
                              <ActivityIndicator size="small" color={Colors.primary} />
                            ) : (
                              <>
                                <Ionicons
                                  name={getBiometricIcon()}
                                  size={20}
                                  color={Colors.primary}
                                />
                                <Text style={styles.quickBtnText}>
                                  {Platform.OS === "ios" ? "Face ID" : "Biometric"}
                                </Text>
                              </>
                            )}
                          </TouchableOpacity>
                        )}
                        {showPasskey && (
                          <TouchableOpacity
                            style={[styles.quickBtn, isAnyLoading && styles.btnDisabled]}
                            onPress={handlePasskeyLogin}
                            disabled={isAnyLoading}
                            activeOpacity={0.8}
                          >
                            {passkeyLoading ? (
                              <ActivityIndicator size="small" color={Colors.primary} />
                            ) : (
                              <>
                                <Ionicons name="key-outline" size={20} color={Colors.primary} />
                                <Text style={styles.quickBtnText}>Passkey</Text>
                              </>
                            )}
                          </TouchableOpacity>
                        )}
                      </View>
                    )}
                  </View>

                  {/* Detailer mode toggle */}
                  <TouchableOpacity
                    style={styles.detailerLink}
                    onPress={toggleDetailerMode}
                  >
                    {isDetailerMode ? (
                      <Text style={styles.detailerLinkText}>
                        <Text style={styles.linkAccent}>← Back to Client mode</Text>
                      </Text>
                    ) : (
                      <Text style={styles.detailerLinkText}>
                        Joining as a professional detailer?{" "}
                        <Text style={styles.linkAccent}>Register as Pro →</Text>
                      </Text>
                    )}
                  </TouchableOpacity>
                </>
              )}

              {/* ── STEP 2a: Existing user — enter password ── */}
              {step === "existing_password" && (
                <>
                  <Text style={styles.stepTitle}>Welcome back</Text>
                  <Text style={styles.stepSubtitle}>{identifier.trim()}</Text>

                  <View style={styles.fieldGroup}>
                    <View style={styles.labelRow}>
                      <Text style={styles.label}>PASSWORD</Text>
                      <TouchableOpacity onPress={handleForgotPassword}>
                        <Text style={styles.forgotText}>Forgot password?</Text>
                      </TouchableOpacity>
                    </View>
                    <AnimatedInput
                      value={password}
                      onChangeText={(t) => {
                        setPassword(t);
                        setErrors({});
                      }}
                      placeholder="••••••••"
                      icon="lock-closed-outline"
                      secureTextEntry={!showPassword}
                      returnKeyType="done"
                      onSubmitEditing={handleLogin}
                      error={!!errors.password}
                      autoFocus
                      rightElement={
                        <EyeToggle
                          visible={showPassword}
                          onPress={() => setShowPassword((v) => !v)}
                        />
                      }
                    />
                    {errors.password && (
                      <Text style={styles.errorText}>{errors.password}</Text>
                    )}
                    {errors.server && (
                      <Text style={styles.serverError}>{errors.server}</Text>
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

              {/* ── STEP 2b: New user — create password ── */}
              {step === "new_user" && (
                <>
                  <Text style={styles.stepTitle}>
                    {isDetailerMode ? "Join as Pro" : "Create your account"}
                  </Text>
                  <Text style={styles.stepSubtitle}>{identifier.trim()}</Text>

                  <View style={styles.fieldGroup}>
                    <Text style={styles.label}>CREATE PASSWORD</Text>
                    <AnimatedInput
                      value={password}
                      onChangeText={(t) => {
                        setPassword(t);
                        setErrors({});
                      }}
                      placeholder="Min 8 characters"
                      icon="lock-closed-outline"
                      secureTextEntry={!showPassword}
                      returnKeyType="next"
                      error={!!errors.password}
                      autoFocus
                      rightElement={
                        <EyeToggle
                          visible={showPassword}
                          onPress={() => setShowPassword((v) => !v)}
                        />
                      }
                    />
                    {errors.password && (
                      <Text style={styles.errorText}>{errors.password}</Text>
                    )}
                    {password.length > 0 && (
                      <View style={styles.strengthContainer}>
                        <View style={styles.strengthBars}>
                          {[1, 2, 3, 4].map((i) => (
                            <View
                              key={i}
                              style={[
                                styles.strengthBar,
                                {
                                  backgroundColor:
                                    i <= pwStrength.bars ? pwStrength.color : "#1E293B",
                                },
                              ]}
                            />
                          ))}
                        </View>
                        <Text
                          style={[styles.strengthLabel, { color: pwStrength.color }]}
                        >
                          {pwStrength.label}
                        </Text>
                      </View>
                    )}
                  </View>

                  <View style={styles.fieldGroup}>
                    <Text style={styles.label}>CONFIRM PASSWORD</Text>
                    <AnimatedInput
                      value={confirmPassword}
                      onChangeText={(t) => {
                        setConfirmPassword(t);
                        setErrors({});
                      }}
                      placeholder="Repeat your password"
                      icon="shield-checkmark-outline"
                      secureTextEntry={!showConfirm}
                      returnKeyType="done"
                      onSubmitEditing={handleCreateAccount}
                      error={!!errors.confirm}
                      rightElement={
                        <EyeToggle
                          visible={showConfirm}
                          onPress={() => setShowConfirm((v) => !v)}
                        />
                      }
                    />
                    {errors.confirm && (
                      <Text style={styles.errorText}>{errors.confirm}</Text>
                    )}
                    {errors.server && (
                      <Text style={styles.serverError}>{errors.server}</Text>
                    )}
                  </View>

                  <TouchableOpacity
                    style={[styles.primaryBtn, isAnyLoading && styles.btnDisabled]}
                    onPress={handleCreateAccount}
                    disabled={isAnyLoading}
                  >
                    {loading ? (
                      <ActivityIndicator color="#fff" />
                    ) : (
                      <Text style={styles.primaryBtnText}>
                        {isDetailerMode ? "JOIN AS PRO" : "CREATE ACCOUNT"}
                      </Text>
                    )}
                  </TouchableOpacity>
                </>
              )}

              {/* ── STEP 2c: Social-only existing user ── */}
              {step === "social_only" && (
                <>
                  <Text style={styles.stepTitle}>Continue with social</Text>
                  <Text style={styles.stepSubtitle}>
                    Your account uses{" "}
                    {identifyData?.auth_methods.includes("google") ? "Google" : "Apple"}{" "}
                    sign-in
                  </Text>

                  <View style={[styles.socialRow, { marginTop: 24 }]}>
                    {identifyData?.auth_methods.includes("google") && (
                      <TouchableOpacity
                        style={[styles.socialBtn, isAnyLoading && styles.btnDisabled]}
                        onPress={() => googlePromptAsync()}
                        disabled={isAnyLoading}
                      >
                        {socialLoading === "google" ? (
                          <ActivityIndicator size="small" color="#fff" />
                        ) : (
                          <>
                            <Text style={styles.googleG}>G</Text>
                            <Text style={styles.socialBtnText}>
                              Continue with Google
                            </Text>
                          </>
                        )}
                      </TouchableOpacity>
                    )}
                    {identifyData?.auth_methods.includes("apple") &&
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
                      )}
                  </View>
                  {errors.server && (
                    <Text style={[styles.serverError, { marginTop: 16 }]}>
                      {errors.server}
                    </Text>
                  )}
                </>
              )}
            </Animated.View>

            <View style={{ height: 40 }} />
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
  stepDots: { flexDirection: "row", gap: 6, alignItems: "center" },
  dot: { width: 6, height: 6, borderRadius: 3, backgroundColor: "#1E293B" },
  dotActive: { width: 20, height: 6, borderRadius: 3, backgroundColor: Colors.primary },
  scroll: { flexGrow: 1, paddingHorizontal: 24, paddingTop: 8, paddingBottom: 20 },
  logoContainer: { alignItems: "center", marginBottom: 32 },
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
  proBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    marginTop: 8,
    backgroundColor: "rgba(59,130,246,0.12)",
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "rgba(59,130,246,0.3)",
  },
  proBadgeText: {
    color: Colors.primary,
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 1.5,
  },
  stepTitle: {
    color: "#fff",
    fontSize: 24,
    fontWeight: "bold",
    marginBottom: 6,
    marginTop: 8,
  },
  stepSubtitle: { color: "#64748B", fontSize: 14, marginBottom: 28 },
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
  forgotText: { color: Colors.primary, fontSize: 12, fontWeight: "600" },
  errorText: { color: "#EF4444", fontSize: 11, marginTop: 5, marginLeft: 4 },
  serverError: {
    color: "#EF4444",
    fontSize: 13,
    textAlign: "center",
    marginTop: 12,
    backgroundColor: "rgba(239,68,68,0.1)",
    padding: 12,
    borderRadius: 8,
  },
  strengthContainer: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    marginTop: 8,
  },
  strengthBars: { flexDirection: "row", gap: 4, flex: 1 },
  strengthBar: { flex: 1, height: 3, borderRadius: 2 },
  strengthLabel: { fontSize: 11, fontWeight: "700", width: 44, textAlign: "right" },
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
  primaryBtnText: { color: "#fff", fontWeight: "800", fontSize: 15, letterSpacing: 2 },
  divider: {
    flexDirection: "row",
    alignItems: "center",
    marginVertical: 20,
    gap: 12,
  },
  dividerLine: { flex: 1, height: 1, backgroundColor: "#1E293B" },
  dividerText: { color: "#334155", fontSize: 12 },
  // ── Step 1: full-width social stack ──────────────────────────────────────────
  socialStack: { gap: 10 },
  googleBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#fff",
    borderRadius: 14,
    padding: 15,
    gap: 10,
  },
  googleIconBox: {
    width: 22,
    height: 22,
    alignItems: "center",
    justifyContent: "center",
  },
  googleGBlue: {
    color: "#4285F4",
    fontWeight: "900",
    fontSize: 17,
    fontStyle: "italic",
  },
  googleBtnText: { color: "#1a1a1a", fontWeight: "600", fontSize: 15 },
  appleFullBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#000",
    borderRadius: 14,
    padding: 15,
    gap: 10,
    borderWidth: 1,
    borderColor: "#333",
  },
  appleFullBtnText: { color: "#fff", fontWeight: "600", fontSize: 15 },
  socialIcon: { marginRight: 2 },
  quickRow: { flexDirection: "row", gap: 10 },
  quickBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 7,
    backgroundColor: "#0D1421",
    borderRadius: 14,
    padding: 13,
    borderWidth: 1,
    borderColor: "rgba(59,130,246,0.25)",
  },
  quickBtnText: { color: Colors.primary, fontWeight: "600", fontSize: 13 },

  // ── Step 2c: social-only row (compact, existing style) ────────────────────────
  socialRow: { flexDirection: "row", gap: 10 },
  socialBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    backgroundColor: "#161E2E",
    padding: 13,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#262F3F",
  },
  googleG: { color: "#fff", fontWeight: "900", fontSize: 16, fontStyle: "italic" },
  socialBtnText: { color: "#fff", fontWeight: "600", fontSize: 13 },
  appleBtn: { backgroundColor: "#fff" },
  appleBtnText: { color: "#000", fontWeight: "600", fontSize: 13 },

  detailerLink: { marginTop: 24, alignItems: "center" },
  detailerLinkText: { color: "#475569", fontSize: 14, textAlign: "center" },
  linkAccent: { color: Colors.primary, fontWeight: "700" },
});
