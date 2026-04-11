// DetailerOnboardingScreen.tsx
//
// 4-step identity verification wizard for new detailers.
//
// Step 1 — Personal Info   : legal name, DOB, address
// Step 2 — ID Verification : Stripe Identity sheet (or dev bypass)
// Step 3 — Consent         : background check + detailer ToS
// Step 4 — Submitted       : confirmation / "under review" state
//
// DEV BYPASS:
//   When the backend returns is_dev_bypass=true, we skip the Stripe sheet
//   entirely and auto-advance to the Consent step. On submit the backend
//   immediately marks the detailer as "approved".

import { Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
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
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useAppNavigation } from "../hooks/useAppNavigation";
import {
  VerificationSubmitPayload,
  verificationStart,
  verificationSubmit,
} from "../services/detailer-private.service";
import { Colors } from "../theme/colors";
import { navigateAfterAuth } from "../utils/auth-redirect";

// Lazy-load Stripe Identity — not available in Expo Go
let useStripeIdentity: any = null;
try {
  useStripeIdentity = require("@stripe/stripe-react-native").useStripeIdentity;
} catch {
  // Expo Go — will rely on dev bypass
}

const TOTAL_STEPS = 4;

// ------------------------------------------------------------------ //
//  Progress Bar                                                       //
// ------------------------------------------------------------------ //

function ProgressBar({ step }: { step: number }) {
  return (
    <View style={pStyles.container}>
      {Array.from({ length: TOTAL_STEPS }).map((_, i) => (
        <View
          key={i}
          style={[
            pStyles.segment,
            i < step ? pStyles.filled : i === step - 1 ? pStyles.active : pStyles.empty,
          ]}
        />
      ))}
    </View>
  );
}

const pStyles = StyleSheet.create({
  container: {
    flexDirection: "row",
    gap: 6,
    paddingHorizontal: 24,
    paddingBottom: 8,
  },
  segment: {
    flex: 1,
    height: 4,
    borderRadius: 2,
  },
  filled: { backgroundColor: Colors.primary },
  active: { backgroundColor: Colors.primary },
  empty: { backgroundColor: "#1E293B" },
});

// ------------------------------------------------------------------ //
//  Form helpers                                                       //
// ------------------------------------------------------------------ //

type FormData = {
  legal_full_name: string;
  date_of_birth: string;    // "MM/DD/YYYY" display → "YYYY-MM-DD" on submit
  address_line1: string;
  city: string;
  state: string;
  zip_code: string;
};

function formatDOB(raw: string): string {
  // Auto-insert slashes: MM/DD/YYYY
  const digits = raw.replace(/\D/g, "").slice(0, 8);
  if (digits.length <= 2) return digits;
  if (digits.length <= 4) return `${digits.slice(0, 2)}/${digits.slice(2)}`;
  return `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4)}`;
}

function parseDOBtoISO(display: string): string | null {
  // "MM/DD/YYYY" → "YYYY-MM-DD"
  const parts = display.split("/");
  if (parts.length !== 3 || parts[2].length !== 4) return null;
  return `${parts[2]}-${parts[0].padStart(2, "0")}-${parts[1].padStart(2, "0")}`;
}

// ------------------------------------------------------------------ //
//  Main Screen                                                        //
// ------------------------------------------------------------------ //

export default function DetailerOnboardingScreen() {
  const navigation = useAppNavigation();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);

  // Step 1 form
  const [form, setForm] = useState<FormData>({
    legal_full_name: "",
    date_of_birth: "",
    address_line1: "",
    city: "",
    state: "",
    zip_code: "",
  });
  const [formErrors, setFormErrors] = useState<Partial<FormData>>({});

  // Step 2 — Stripe Identity state
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isDevBypass, setIsDevBypass] = useState(false);
  const [identityStatus, setIdentityStatus] = useState<
    "idle" | "started" | "completed" | "failed"
  >("idle");

  // Step 3 — Consent
  const [consentBg, setConsentBg] = useState(false);
  const [consentTerms, setConsentTerms] = useState(false);

  // Stripe Identity hook (no-op if unavailable)
  const stripeIdentity = useStripeIdentity
    ? useStripeIdentity(async () => {
        const res = await verificationStart();
        if (res.is_dev_bypass) {
          setIsDevBypass(true);
          return "dev_bypass_secret"; // Stripe hook won't be called in dev
        }
        setSessionId(res.session_id ?? null);
        return res.client_secret!;
      })
    : null;

  // ---------------------------------------------------------------- //
  //  Step 1 — validate personal info                                 //
  // ---------------------------------------------------------------- //

  function validateStep1(): boolean {
    const errors: Partial<FormData> = {};
    if (!form.legal_full_name.trim())
      errors.legal_full_name = "Legal full name is required";
    if (!parseDOBtoISO(form.date_of_birth))
      errors.date_of_birth = "Enter a valid date (MM/DD/YYYY)";
    if (!form.address_line1.trim())
      errors.address_line1 = "Address is required";
    if (!form.city.trim())
      errors.city = "City is required";
    if (!form.state.trim())
      errors.state = "State is required";
    if (!form.zip_code.trim())
      errors.zip_code = "ZIP code is required";
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  }

  function goStep2() {
    if (!validateStep1()) return;
    setStep(2);
  }

  // ---------------------------------------------------------------- //
  //  Step 2 — launch Stripe Identity (or dev bypass)                 //
  // ---------------------------------------------------------------- //

  async function handleStartVerification() {
    setLoading(true);
    try {
      const res = await verificationStart();

      if (res.is_dev_bypass) {
        setIsDevBypass(true);
        setIdentityStatus("completed");
        setStep(3);
        return;
      }

      // Real Stripe Identity sheet
      if (!stripeIdentity) {
        // Stripe hook not available (Expo Go without custom client)
        Alert.alert(
          "Stripe Identity unavailable",
          "You need a custom dev client to use Stripe Identity. Switching to dev bypass.",
        );
        setIsDevBypass(true);
        setIdentityStatus("completed");
        setStep(3);
        return;
      }

      setSessionId(res.session_id ?? null);
      const result = await stripeIdentity.present();

      if (result.error) {
        Alert.alert("Verification failed", result.error.message);
        setIdentityStatus("failed");
        return;
      }

      setIdentityStatus("completed");
      setStep(3);
    } catch (err: any) {
      Alert.alert("Error", err?.response?.data?.detail ?? "Could not start verification.");
      setIdentityStatus("failed");
    } finally {
      setLoading(false);
    }
  }

  // ---------------------------------------------------------------- //
  //  Step 3 — submit everything                                      //
  // ---------------------------------------------------------------- //

  async function handleSubmit() {
    if (!consentBg || !consentTerms) {
      Alert.alert("Consent required", "Please accept both consent checkboxes to continue.");
      return;
    }

    const isoDate = parseDOBtoISO(form.date_of_birth)!;

    const payload: VerificationSubmitPayload = {
      legal_full_name: form.legal_full_name.trim(),
      date_of_birth: isoDate,
      address_line1: form.address_line1.trim(),
      city: form.city.trim(),
      state: form.state.trim().toUpperCase(),
      zip_code: form.zip_code.trim(),
      background_check_consent: true,
      session_id: isDevBypass ? null : sessionId,
    };

    setLoading(true);
    try {
      await verificationSubmit(payload);
      setStep(4);
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? "Could not submit your application. Please try again.";
      Alert.alert("Error", msg);
    } finally {
      setLoading(false);
    }
  }

  // ---------------------------------------------------------------- //
  //  Step 4 — go to dashboard                                        //
  // ---------------------------------------------------------------- //

  async function handleGoToDashboard() {
    await navigateAfterAuth(navigation);
  }

  // ---------------------------------------------------------------- //
  //  Render helpers                                                   //
  // ---------------------------------------------------------------- //

  function Field({
    label,
    field,
    placeholder,
    keyboardType = "default",
    autoCapitalize = "words",
    maxLength,
    onChangeText,
  }: {
    label: string;
    field: keyof FormData;
    placeholder: string;
    keyboardType?: any;
    autoCapitalize?: any;
    maxLength?: number;
    onChangeText?: (v: string) => void;
  }) {
    return (
      <View style={styles.fieldWrap}>
        <Text style={styles.fieldLabel}>{label}</Text>
        <TextInput
          style={[styles.input, !!formErrors[field] && styles.inputError]}
          value={form[field]}
          onChangeText={(v) => {
            const val = onChangeText ? (onChangeText(v), v) : v;
            setForm((f) => ({ ...f, [field]: val }));
            setFormErrors((e) => ({ ...e, [field]: undefined }));
          }}
          placeholder={placeholder}
          placeholderTextColor="#475569"
          keyboardType={keyboardType}
          autoCapitalize={autoCapitalize}
          maxLength={maxLength}
        />
        {!!formErrors[field] && (
          <Text style={styles.errorText}>{formErrors[field]}</Text>
        )}
      </View>
    );
  }

  // ---------------------------------------------------------------- //
  //  STEP 1 — Personal Info                                          //
  // ---------------------------------------------------------------- //

  const Step1 = () => (
    <ScrollView
      contentContainerStyle={styles.stepContent}
      keyboardShouldPersistTaps="handled"
      showsVerticalScrollIndicator={false}
    >
      <Text style={styles.stepTitle}>Personal Information</Text>
      <Text style={styles.stepSubtitle}>
        This must match your government-issued ID exactly.
      </Text>

      <Field
        label="Legal Full Name"
        field="legal_full_name"
        placeholder="As it appears on your ID"
      />
      <Field
        label="Date of Birth"
        field="date_of_birth"
        placeholder="MM/DD/YYYY"
        keyboardType="number-pad"
        autoCapitalize="none"
        maxLength={10}
        onChangeText={(v) => {
          const formatted = formatDOB(v);
          setForm((f) => ({ ...f, date_of_birth: formatted }));
          setFormErrors((e) => ({ ...e, date_of_birth: undefined }));
        }}
      />
      <Field
        label="Address"
        field="address_line1"
        placeholder="123 Main St"
      />

      <View style={styles.rowFields}>
        <View style={{ flex: 2 }}>
          <Field
            label="City"
            field="city"
            placeholder="Fort Wayne"
          />
        </View>
        <View style={{ flex: 1, marginLeft: 12 }}>
          <Field
            label="State"
            field="state"
            placeholder="IN"
            maxLength={2}
          />
        </View>
      </View>

      <Field
        label="ZIP Code"
        field="zip_code"
        placeholder="46802"
        keyboardType="number-pad"
        autoCapitalize="none"
        maxLength={10}
      />

      <View style={styles.infoBanner}>
        <Ionicons name="lock-closed-outline" size={15} color="#60A5FA" />
        <Text style={styles.infoBannerText}>
          Your information is encrypted and used only for identity verification.
        </Text>
      </View>

      <TouchableOpacity style={styles.primaryBtn} onPress={goStep2} activeOpacity={0.85}>
        <Text style={styles.primaryBtnText}>Continue</Text>
        <Ionicons name="arrow-forward" size={18} color="#fff" style={{ marginLeft: 8 }} />
      </TouchableOpacity>
    </ScrollView>
  );

  // ---------------------------------------------------------------- //
  //  STEP 2 — ID Verification                                        //
  // ---------------------------------------------------------------- //

  const Step2 = () => (
    <View style={styles.centerStep}>
      <View style={styles.idIconWrap}>
        <MaterialCommunityIcons name="card-account-details-outline" size={56} color="#60A5FA" />
      </View>
      <Text style={styles.stepTitle}>Verify Your Identity</Text>
      <Text style={styles.stepSubtitle}>
        We use Stripe Identity to securely verify your government-issued ID and take a
        quick selfie. This takes about 2 minutes.
      </Text>

      <View style={styles.checkList}>
        {[
          "Driver's license or passport",
          "Photo must be clear and unobstructed",
          "Selfie to match your ID",
        ].map((item) => (
          <View key={item} style={styles.checkItem}>
            <Ionicons name="checkmark-circle" size={18} color="#22C55E" />
            <Text style={styles.checkItemText}>{item}</Text>
          </View>
        ))}
      </View>

      {identityStatus === "failed" && (
        <View style={styles.errorBanner}>
          <Ionicons name="alert-circle-outline" size={16} color="#EF4444" />
          <Text style={styles.errorBannerText}>
            Verification failed. Please try again with a clear photo.
          </Text>
        </View>
      )}

      <TouchableOpacity
        style={[styles.primaryBtn, loading && styles.btnDisabled]}
        onPress={handleStartVerification}
        disabled={loading}
        activeOpacity={0.85}
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <>
            <Ionicons name="shield-checkmark-outline" size={18} color="#fff" style={{ marginRight: 8 }} />
            <Text style={styles.primaryBtnText}>
              {identityStatus === "failed" ? "Try Again" : "Start Verification"}
            </Text>
          </>
        )}
      </TouchableOpacity>
    </View>
  );

  // ---------------------------------------------------------------- //
  //  STEP 3 — Consent                                                //
  // ---------------------------------------------------------------- //

  const Step3 = () => (
    <ScrollView
      contentContainerStyle={styles.stepContent}
      keyboardShouldPersistTaps="handled"
      showsVerticalScrollIndicator={false}
    >
      <Text style={styles.stepTitle}>Final Consent</Text>
      <Text style={styles.stepSubtitle}>
        Read and accept the following to complete your application.
      </Text>

      {/* Background Check */}
      <TouchableOpacity
        style={styles.consentCard}
        onPress={() => setConsentBg((v) => !v)}
        activeOpacity={0.8}
      >
        <View style={[styles.checkbox, consentBg && styles.checkboxChecked]}>
          {consentBg && <Ionicons name="checkmark" size={14} color="#fff" />}
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.consentTitle}>Background Check Consent</Text>
          <Text style={styles.consentBody}>
            I authorize RayCarwash and its partners to conduct a criminal background
            check as part of the detailer onboarding process. I understand results
            may affect my eligibility.
          </Text>
        </View>
      </TouchableOpacity>

      {/* Detailer Terms */}
      <TouchableOpacity
        style={[styles.consentCard, { marginTop: 12 }]}
        onPress={() => setConsentTerms((v) => !v)}
        activeOpacity={0.8}
      >
        <View style={[styles.checkbox, consentTerms && styles.checkboxChecked]}>
          {consentTerms && <Ionicons name="checkmark" size={14} color="#fff" />}
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.consentTitle}>Detailer Terms of Service</Text>
          <Text style={styles.consentBody}>
            I agree to the{" "}
            <Text style={{ color: Colors.primary }}>Detailer Terms of Service</Text>
            {" "}and{" "}
            <Text style={{ color: Colors.primary }}>Privacy Policy</Text>.
            I confirm that all information provided is accurate and truthful.
          </Text>
        </View>
      </TouchableOpacity>

      <View style={styles.infoBanner}>
        <Ionicons name="information-circle-outline" size={15} color="#60A5FA" />
        <Text style={styles.infoBannerText}>
          {isDevBypass
            ? "Dev mode: your profile will be approved immediately."
            : "Your application will be reviewed within 24–48 hours after submission."}
        </Text>
      </View>

      <TouchableOpacity
        style={[
          styles.primaryBtn,
          (!consentBg || !consentTerms || loading) && styles.btnDisabled,
        ]}
        onPress={handleSubmit}
        disabled={!consentBg || !consentTerms || loading}
        activeOpacity={0.85}
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.primaryBtnText}>Submit Application</Text>
        )}
      </TouchableOpacity>
    </ScrollView>
  );

  // ---------------------------------------------------------------- //
  //  STEP 4 — Submitted                                              //
  // ---------------------------------------------------------------- //

  const Step4 = () => (
    <View style={styles.centerStep}>
      <View style={[styles.idIconWrap, { backgroundColor: "rgba(34,197,94,0.12)" }]}>
        <Ionicons name="checkmark-circle" size={56} color="#22C55E" />
      </View>
      <Text style={[styles.stepTitle, { marginTop: 20 }]}>
        {isDevBypass ? "Profile Approved!" : "Application Submitted!"}
      </Text>
      <Text style={styles.stepSubtitle}>
        {isDevBypass
          ? "Your profile is active. You can start accepting bookings right away."
          : "We'll review your information and send you an email within 24–48 hours once approved."}
      </Text>

      {!isDevBypass && (
        <View style={styles.statusCard}>
          <View style={styles.statusRow}>
            <View style={[styles.statusDot, { backgroundColor: "#F59E0B" }]} />
            <Text style={styles.statusText}>Identity Verification — Pending</Text>
          </View>
          <View style={styles.statusRow}>
            <View style={[styles.statusDot, { backgroundColor: "#64748B" }]} />
            <Text style={styles.statusText}>Background Check — Queued</Text>
          </View>
          <View style={styles.statusRow}>
            <View style={[styles.statusDot, { backgroundColor: "#64748B" }]} />
            <Text style={styles.statusText}>Profile Approval — Waiting</Text>
          </View>
        </View>
      )}

      <TouchableOpacity
        style={[styles.primaryBtn, { marginTop: 32 }]}
        onPress={handleGoToDashboard}
        activeOpacity={0.85}
      >
        <Text style={styles.primaryBtnText}>Go to Dashboard</Text>
      </TouchableOpacity>
    </View>
  );

  // ---------------------------------------------------------------- //
  //  Root render                                                      //
  // ---------------------------------------------------------------- //

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        {/* Header */}
        <LinearGradient colors={["#0F172A", "#1E293B"]} style={styles.header}>
          <View style={styles.headerRow}>
            {step > 1 && step < 4 ? (
              <TouchableOpacity onPress={() => setStep((s) => s - 1)} style={styles.backBtn}>
                <Ionicons name="arrow-back" size={20} color="#94A3B8" />
              </TouchableOpacity>
            ) : (
              <View style={{ width: 36 }} />
            )}
            <Text style={styles.headerTitle}>
              {step === 1 && "Identity"}
              {step === 2 && "Verification"}
              {step === 3 && "Consent"}
              {step === 4 && "Complete"}
            </Text>
            <Text style={styles.stepCounter}>{step} / {TOTAL_STEPS}</Text>
          </View>
          <ProgressBar step={step} />
        </LinearGradient>

        {/* Step content */}
        <View style={styles.body}>
          {step === 1 && <Step1 />}
          {step === 2 && <Step2 />}
          {step === 3 && <Step3 />}
          {step === 4 && <Step4 />}
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

// ------------------------------------------------------------------ //
//  Styles                                                             //
// ------------------------------------------------------------------ //

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: "#0B0F1A",
  },
  header: {
    paddingTop: 8,
    paddingBottom: 12,
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    marginBottom: 12,
  },
  backBtn: {
    width: 36,
    height: 36,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 18,
    backgroundColor: "rgba(255,255,255,0.06)",
  },
  headerTitle: {
    color: "#F1F5F9",
    fontSize: 16,
    fontWeight: "700",
    letterSpacing: 0.3,
  },
  stepCounter: {
    color: "#475569",
    fontSize: 12,
    fontWeight: "600",
    width: 36,
    textAlign: "right",
  },
  body: {
    flex: 1,
    backgroundColor: "#0B0F1A",
  },
  // ---- Steps ----
  stepContent: {
    padding: 24,
    paddingBottom: 40,
  },
  centerStep: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: 32,
  },
  stepTitle: {
    color: "#F1F5F9",
    fontSize: 22,
    fontWeight: "700",
    marginBottom: 8,
    textAlign: "center",
  },
  stepSubtitle: {
    color: "#64748B",
    fontSize: 14,
    lineHeight: 21,
    textAlign: "center",
    marginBottom: 28,
  },
  // ---- Form fields ----
  fieldWrap: {
    marginBottom: 16,
  },
  fieldLabel: {
    color: "#94A3B8",
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 0.8,
    marginBottom: 6,
    textTransform: "uppercase",
  },
  input: {
    backgroundColor: "#1E293B",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#334155",
    color: "#F1F5F9",
    paddingHorizontal: 16,
    paddingVertical: 13,
    fontSize: 15,
  },
  inputError: {
    borderColor: "#EF4444",
  },
  errorText: {
    color: "#EF4444",
    fontSize: 11,
    marginTop: 4,
    marginLeft: 4,
  },
  rowFields: {
    flexDirection: "row",
    alignItems: "flex-start",
  },
  infoBanner: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 8,
    backgroundColor: "rgba(96,165,250,0.08)",
    borderRadius: 10,
    padding: 12,
    marginBottom: 24,
    marginTop: 4,
  },
  infoBannerText: {
    flex: 1,
    color: "#93C5FD",
    fontSize: 12,
    lineHeight: 18,
  },
  // ---- Step 2 ----
  idIconWrap: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: "rgba(96,165,250,0.1)",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 24,
  },
  checkList: {
    alignSelf: "stretch",
    marginBottom: 32,
    gap: 10,
  },
  checkItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  checkItemText: {
    color: "#CBD5E1",
    fontSize: 14,
  },
  errorBanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: "rgba(239,68,68,0.08)",
    borderRadius: 10,
    padding: 12,
    marginBottom: 20,
    alignSelf: "stretch",
  },
  errorBannerText: {
    flex: 1,
    color: "#FCA5A5",
    fontSize: 12,
    lineHeight: 18,
  },
  // ---- Step 3 — Consent ----
  consentCard: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 14,
    backgroundColor: "#1E293B",
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#334155",
    padding: 16,
  },
  checkbox: {
    width: 22,
    height: 22,
    borderRadius: 6,
    borderWidth: 2,
    borderColor: "#475569",
    alignItems: "center",
    justifyContent: "center",
    marginTop: 1,
    flexShrink: 0,
  },
  checkboxChecked: {
    backgroundColor: Colors.primary,
    borderColor: Colors.primary,
  },
  consentTitle: {
    color: "#CBD5E1",
    fontSize: 13,
    fontWeight: "700",
    marginBottom: 4,
  },
  consentBody: {
    color: "#64748B",
    fontSize: 12,
    lineHeight: 18,
  },
  // ---- Step 4 — Status ----
  statusCard: {
    alignSelf: "stretch",
    backgroundColor: "#1E293B",
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#334155",
    padding: 16,
    gap: 12,
    marginTop: 8,
  },
  statusRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  statusDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  statusText: {
    color: "#94A3B8",
    fontSize: 13,
  },
  // ---- CTA ----
  primaryBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: Colors.primary,
    borderRadius: 14,
    paddingVertical: 16,
    marginTop: 8,
    shadowColor: Colors.primary,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 10,
    elevation: 6,
    alignSelf: "stretch",
  },
  btnDisabled: {
    opacity: 0.4,
  },
  primaryBtnText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "700",
    letterSpacing: 0.5,
  },
});
