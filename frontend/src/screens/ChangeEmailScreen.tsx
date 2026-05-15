/**
 * frontend/src/screens/ChangeEmailScreen.tsx
 *
 * Two-step flow:
 *   1. The user types the new email + current password and we hit
 *      /users/me/email/change-request. The backend mails a verification
 *      link to the NEW address; the response carries a `dev_token` in
 *      development so the test menu can paste it without scraping logs.
 *   2. After clicking the link (or pasting the dev token), the user
 *      confirms by hitting /users/me/email/change-confirm.
 *
 * Both halves share this screen with internal state (no separate route).
 * Confirm flow forces sign-out because the backend bumps token_version.
 */
import { Ionicons } from "@expo/vector-icons";
import React, { useState } from "react";
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
import { useQueryClient } from "@tanstack/react-query";

import Button from "../components/Button";
import { ApiError } from "../lib/api-error";
import {
  confirmEmailChange,
  requestEmailChange,
} from "../services/contact-change.service";
import { Colors } from "../theme/colors";
import { clearAuthTokens } from "../utils/storage";

type Stage = "request" | "confirm";

export default function ChangeEmailScreen({ navigation }: any) {
  const queryClient = useQueryClient();
  const [stage, setStage] = useState<Stage>("request");
  const [loading, setLoading] = useState(false);

  // Stage 1
  const [newEmail, setNewEmail] = useState("");
  const [password, setPassword] = useState("");

  // Stage 2
  const [token, setToken] = useState("");

  async function handleRequest() {
    if (!newEmail.trim() || !password) {
      Alert.alert("Missing fields", "Enter the new email and your current password.");
      return;
    }
    setLoading(true);
    try {
      const ack = await requestEmailChange(newEmail.trim(), password);
      if (ack.dev_token) {
        // Development convenience — paste it straight into the confirm field
        // so the test harness doesn't need to read backend logs.
        setToken(ack.dev_token);
      }
      setStage("confirm");
      Alert.alert(
        "Check your inbox",
        `We sent a verification link to ${newEmail.trim()}. Open it to finish the change.`,
      );
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Could not start the email change.";
      Alert.alert("Error", msg);
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirm() {
    if (!token.trim()) {
      Alert.alert("Missing token", "Paste the verification token from your email.");
      return;
    }
    setLoading(true);
    try {
      const ok = await confirmEmailChange(token.trim());
      Alert.alert(
        "Email updated",
        `Your account email is now ${ok.new_value_masked}. Please sign in again.`,
        [
          {
            text: "Sign out",
            onPress: async () => {
              queryClient.clear();
              await clearAuthTokens();
              navigation.reset({ index: 0, routes: [{ name: "Login" }] });
            },
          },
        ],
      );
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Could not confirm the email change.";
      Alert.alert("Error", msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
            <Ionicons name="chevron-back" size={22} color="white" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Change Email</Text>
          <View style={{ width: 40 }} />
        </View>

        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <View style={styles.steps}>
            <Step active={stage === "request"} number={1} label="Send link" />
            <View style={styles.stepLine} />
            <Step active={stage === "confirm"} number={2} label="Verify" />
          </View>

          {stage === "request" ? (
            <>
              <Text style={styles.label}>NEW EMAIL</Text>
              <View style={styles.inputWrap}>
                <Ionicons name="mail-outline" size={18} color="#475569" style={styles.inputIcon} />
                <TextInput
                  style={styles.input}
                  value={newEmail}
                  onChangeText={setNewEmail}
                  placeholder="new@example.com"
                  placeholderTextColor="#334155"
                  keyboardType="email-address"
                  autoCapitalize="none"
                  autoCorrect={false}
                />
              </View>

              <Text style={[styles.label, { marginTop: 16 }]}>CURRENT PASSWORD</Text>
              <View style={styles.inputWrap}>
                <Ionicons name="lock-closed-outline" size={18} color="#475569" style={styles.inputIcon} />
                <TextInput
                  style={styles.input}
                  value={password}
                  onChangeText={setPassword}
                  placeholder="Your current password"
                  placeholderTextColor="#334155"
                  secureTextEntry
                  autoCapitalize="none"
                />
              </View>

              <Text style={styles.hint}>
                We&apos;ll send a verification link to the new email. Your address
                only changes after you click it.
              </Text>

              <Button
                title="SEND VERIFICATION LINK"
                onPress={handleRequest}
                variant="primary"
                size="lg"
                fullWidth
                loading={loading}
              />
            </>
          ) : (
            <>
              <Text style={styles.label}>VERIFICATION TOKEN</Text>
              <View style={styles.inputWrap}>
                <Ionicons name="key-outline" size={18} color="#475569" style={styles.inputIcon} />
                <TextInput
                  style={styles.input}
                  value={token}
                  onChangeText={setToken}
                  placeholder="Paste the link's token here"
                  placeholderTextColor="#334155"
                  autoCapitalize="none"
                />
              </View>

              <Text style={styles.hint}>
                The link expires in 1 hour. Confirming will sign you out of every
                device — you&apos;ll need to log in again with the new email.
              </Text>

              <Button
                title="CONFIRM CHANGE"
                onPress={handleConfirm}
                variant="primary"
                size="lg"
                fullWidth
                loading={loading}
              />
              <TouchableOpacity
                onPress={() => setStage("request")}
                style={styles.linkBtn}
                disabled={loading}
              >
                <Text style={styles.linkText}>Re-send link</Text>
              </TouchableOpacity>
            </>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function Step({ active, number, label }: { active: boolean; number: number; label: string }) {
  return (
    <View style={styles.step}>
      <View style={[styles.stepCircle, active && styles.stepCircleActive]}>
        <Text style={[styles.stepNumber, active && styles.stepNumberActive]}>{number}</Text>
      </View>
      <Text style={[styles.stepLabel, active && styles.stepLabelActive]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0B0F1A" },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingVertical: 16,
  },
  backBtn: {
    backgroundColor: "#161E2E",
    padding: 8,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#262F3F",
  },
  headerTitle: { color: "white", fontSize: 18, fontWeight: "700" },
  scroll: { padding: 20 },
  steps: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 24,
  },
  step: { alignItems: "center", width: 80 },
  stepCircle: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: "#161E2E",
    borderWidth: 1,
    borderColor: "#262F3F",
    alignItems: "center",
    justifyContent: "center",
  },
  stepCircleActive: { backgroundColor: "#1E3A5F", borderColor: Colors.primary },
  stepNumber: { color: "#475569", fontWeight: "700" },
  stepNumberActive: { color: "white" },
  stepLabel: { color: "#475569", fontSize: 11, marginTop: 6, fontWeight: "600" },
  stepLabelActive: { color: "white" },
  stepLine: { flex: 1, height: 1, backgroundColor: "#262F3F" },
  label: {
    color: "#94A3B8",
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1,
    marginBottom: 8,
  },
  inputWrap: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#161E2E",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#262F3F",
  },
  inputIcon: { marginLeft: 14, marginRight: 4 },
  input: { flex: 1, color: "white", padding: 14, fontSize: 15 },
  hint: { color: "#475569", fontSize: 12, marginTop: 14, marginBottom: 20, lineHeight: 18 },
  linkBtn: { alignSelf: "center", paddingVertical: 12 },
  linkText: { color: "#94A3B8", fontSize: 13, textDecorationLine: "underline" },
});
