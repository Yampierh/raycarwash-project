import * as LocalAuthentication from "expo-local-authentication";
import { LinearGradient } from "expo-linear-gradient";
import * as SplashScreen from "expo-splash-screen";
import React, { useEffect, useRef } from "react";
import { Animated, StyleSheet, Text, View } from "react-native";
import { useAppNavigation } from "../hooks/useAppNavigation";
import { refreshAccessToken, webAuthnAuthenticateBegin, webAuthnAuthenticateComplete } from "../services/auth.service";
import { Colors } from "../theme/colors";
import { navigateAfterAuth } from "../utils/auth-redirect";
import {
  getBiometricEnabled,
  getLastEmail,
  getPasskeyEnabled,
  getRefreshToken,
  getToken,
  saveRefreshToken,
  saveToken,
} from "../utils/storage";

// Lazy import — not available in Expo Go or web
let Passkey: typeof import("react-native-passkey").Passkey | null = null;
try {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  Passkey = require("react-native-passkey").Passkey;
} catch {}

// Keep native splash visible until we're ready
SplashScreen.preventAutoHideAsync().catch(() => {});

export default function LoadingScreen() {
  const navigation = useAppNavigation();

  const fadeAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(0.85)).current;
  const ringAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    // Animate logo in
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 500,
        useNativeDriver: true,
      }),
      Animated.spring(scaleAnim, {
        toValue: 1,
        tension: 60,
        friction: 8,
        useNativeDriver: true,
      }),
    ]).start();

    // Subtle ring pulse loop
    Animated.loop(
      Animated.sequence([
        Animated.timing(ringAnim, {
          toValue: 1,
          duration: 1200,
          useNativeDriver: true,
        }),
        Animated.timing(ringAnim, {
          toValue: 0,
          duration: 1200,
          useNativeDriver: true,
        }),
      ]),
    ).start();

    checkAuthAndNavigate();
  }, []);

  const checkAuthAndNavigate = async () => {
    try {
      await SplashScreen.hideAsync();
    } catch {}

    try {
      const accessToken = await getToken();

      if (!accessToken) {
        goToLogin();
        return;
      }

      // Try passkey quick-unlock first (uses stored email from last login)
      const passkeyEnabled = await getPasskeyEnabled();
      const lastEmail = await getLastEmail();
      if (passkeyEnabled && lastEmail && Passkey?.isSupported()) {
        try {
          const { challenge_token, options } = await webAuthnAuthenticateBegin(lastEmail);
          const assertion = await Passkey.authenticate(options as any);
          const { access_token, refresh_token } = await webAuthnAuthenticateComplete(
            challenge_token,
            assertion as any,
          );
          await saveToken(access_token);
          await saveRefreshToken(refresh_token);
          await navigateAfterAuth(navigation);
          return;
        } catch {
          // Passkey cancelled or failed — fall through to biometric / token refresh
        }
      }

      // Try biometric quick-unlock if enabled
      const biometricEnabled = await getBiometricEnabled();
      if (biometricEnabled) {
        const hardwareAvailable = await LocalAuthentication.hasHardwareAsync();
        const enrolled = await LocalAuthentication.isEnrolledAsync();

        if (hardwareAvailable && enrolled) {
          const result = await LocalAuthentication.authenticateAsync({
            promptMessage: "Sign in to RayCarWash",
            cancelLabel: "Use password",
            disableDeviceFallback: false,
          });

          if (!result.success) {
            // User cancelled biometric → go to login screen
            goToLogin();
            return;
          }
        }
      }

      // Validate stored token by trying to navigate
      await navigateAfterAuth(navigation);
    } catch (err: any) {
      // Token expired or invalid → try refresh
      try {
        const refreshToken = await getRefreshToken();
        if (!refreshToken) {
          goToLogin();
          return;
        }
        const { access_token, refresh_token } = await refreshAccessToken(refreshToken);
        await saveToken(access_token);
        await saveRefreshToken(refresh_token);
        await navigateAfterAuth(navigation);
      } catch {
        goToLogin();
      }
    }
  };

  const goToLogin = () => {
    navigation.reset({ index: 0, routes: [{ name: "Login" }] });
  };

  const ringOpacity = ringAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [0.15, 0.45],
  });
  const ringScale = ringAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [1, 1.18],
  });

  return (
    <View style={styles.container}>
      <LinearGradient
        colors={["#060A14", "#0B0F1A", "#101828"]}
        style={StyleSheet.absoluteFill}
      />

      <Animated.View
        style={[
          styles.logoWrapper,
          { opacity: fadeAnim, transform: [{ scale: scaleAnim }] },
        ]}
      >
        {/* Pulse ring */}
        <Animated.View
          style={[
            styles.ring,
            { opacity: ringOpacity, transform: [{ scale: ringScale }] },
          ]}
        />

        {/* Logo circle */}
        <View style={styles.logoCircle}>
          <Text style={styles.logoText}>R</Text>
        </View>

        <Text style={styles.appName}>RAYCARWASH</Text>
        <Text style={styles.tagline}>Premium Mobile Detailing</Text>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  logoWrapper: { alignItems: "center" },
  ring: {
    position: "absolute",
    width: 120,
    height: 120,
    borderRadius: 60,
    borderWidth: 2,
    borderColor: Colors.primary,
  },
  logoCircle: {
    width: 88,
    height: 88,
    borderRadius: 44,
    borderWidth: 2,
    borderColor: Colors.primary,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "rgba(59,130,246,0.1)",
  },
  logoText: { color: Colors.primary, fontSize: 44, fontWeight: "bold" },
  appName: {
    color: "#fff",
    fontSize: 26,
    fontWeight: "bold",
    marginTop: 20,
    letterSpacing: 3,
  },
  tagline: { color: "#475569", fontSize: 12, marginTop: 6, letterSpacing: 1 },
});
