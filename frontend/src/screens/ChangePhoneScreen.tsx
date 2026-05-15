/**
 * frontend/src/screens/ChangePhoneScreen.tsx
 *
 * Same two-step shape as ChangeEmailScreen but the verification token is
 * a 6-digit SMS OTP with a 10-minute TTL and a 5-attempt cap. The
 * service surfaces the OTP as `dev_token` in dev so tests can autofill.
 */
import { Ionicons } from "@expo/vector-icons";
import React, { useState } from "react";
import {
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
  requestPhoneChange,
  verifyPhoneChange,
} from "../services/contact-change.service";
import { Colors } from "../theme/colors";
import { clearAuthTokens } from "../utils/storage";

type Stage = "request" | "verify";

export default function ChangePhoneScreen({ navigation }: any) {
  const queryClient = useQueryClient();
  const [stage, setStage] = useState<Stage>("request");
  const [loading, setLoading] = useState(false);

  const [newPhone, setNewPhone] = useState("+1");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");

  async function handleRequest() {
    if (!newPhone.trim() || !password) {
      Alert.alert("Missing fields", "Enter the new phone number and your current password.");
      return;
    }
    setLoading(true);
    try {
      const ack = await requestPhoneChange(newPhone.trim(), password);
      if (ack.dev_token) {
        setOtp(ack.dev_token);
      }
      setStage("verify");
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Could not start the phone change.";
      Alert.alert("Error", msg);
    } finally {
      setLoading(false);
    }
  }

  async function handleVerify() {
    if (otp.trim().length !== 6) {
      Alert.alert("Invalid code", "Enter the 6-digit code from the text message.");
      return;
    }
    setLoading(true);
    try {
      const ok = await verifyPhoneChange(otp.trim());
      Alert.alert(
        "Phone updated",
        `Your phone number is now ${ok.new_value_masked}. Please sign in again.`,
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
      const msg = err instanceof ApiError ? err.message : "Could not verify the code.";
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
          <Text style={styles.headerTitle}>Change Phone</Text>
          <View style={{ width: 40 }} />
        </View>

        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          {stage === "request" ? (
            <>
              <Text style={styles.label}>NEW PHONE</Text>
              <View style={styles.inputWrap}>
                <Ionicons name="call-outline" size={18} color="#475569" style={styles.inputIcon} />
                <TextInput
                  style={styles.input}
                  value={newPhone}
                  onChangeText={setNewPhone}
                  placeholder="+1 555 000 0000"
                  placeholderTextColor="#334155"
                  keyboardType="phone-pad"
                  autoCapitalize="none"
                />
              </View>

              <Text style={[styles.label, { marginTop: 16 }]}>CURRENT PASSWORD</Text>
              <View style={styles.inputWrap}>
                <Ionicons
                  name="lock-closed-outline"
                  size={18}
                  color="#475569"
                  style={styles.inputIcon}
                />
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
                We&apos;ll text a 6-digit code to the new phone. It expires in 10
                minutes and you have 5 attempts before the request locks.
              </Text>

              <Button
                title="SEND CODE"
                onPress={handleRequest}
                variant="primary"
                size="lg"
                fullWidth
                loading={loading}
              />
            </>
          ) : (
            <>
              <Text style={styles.label}>VERIFICATION CODE</Text>
              <View style={styles.inputWrap}>
                <Ionicons name="keypad-outline" size={18} color="#475569" style={styles.inputIcon} />
                <TextInput
                  style={[styles.input, { letterSpacing: 8 }]}
                  value={otp}
                  onChangeText={setOtp}
                  placeholder="000000"
                  placeholderTextColor="#334155"
                  keyboardType="number-pad"
                  maxLength={6}
                />
              </View>

              <Text style={styles.hint}>
                Verifying will sign you out of every device. You&apos;ll need to
                log in again with your new phone.
              </Text>

              <Button
                title="VERIFY"
                onPress={handleVerify}
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
                <Text style={styles.linkText}>Re-send code</Text>
              </TouchableOpacity>
            </>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
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
