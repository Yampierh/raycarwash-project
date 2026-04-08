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
import { upsertDetailerProfile } from "../services/detailer-private.service";
import { Colors } from "../theme/colors";
import { navigateAfterAuth } from "../utils/auth-redirect";

const RADIUS_OPTIONS = [5, 10, 15, 25];

const SPECIALTIES = [
  { key: "ceramic_coating",         label: "Ceramic Coating",          icon: "shield-check" },
  { key: "interior_deep_clean",     label: "Interior Deep Clean",      icon: "seat-recline-extra" },
  { key: "paint_correction",        label: "Paint Correction",         icon: "auto-fix" },
  { key: "headlight_restoration",   label: "Headlight Restoration",    icon: "car-light-high" },
  { key: "engine_bay",              label: "Engine Bay",               icon: "engine" },
  { key: "odor_elimination",        label: "Odor Elimination",         icon: "air-filter" },
  { key: "full_detail",             label: "Full Detail",              icon: "car-wash" },
  { key: "exterior_only",           label: "Exterior Only",            icon: "spray" },
];

export default function DetailerOnboardingScreen() {
  const navigation = useAppNavigation();

  const [bio, setBio] = useState("");
  const [years, setYears] = useState("");
  const [radius, setRadius] = useState<number>(10);
  const [specialties, setSpecialties] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);

  function toggleSpecialty(key: string) {
    setSpecialties((prev) =>
      prev.includes(key) ? prev.filter((s) => s !== key) : [...prev, key],
    );
  }

  async function handleSubmit() {
    if (!bio.trim()) {
      Alert.alert("Missing info", "Please write a short professional bio.");
      return;
    }
    const yearsNum = parseInt(years, 10);
    if (!years || isNaN(yearsNum) || yearsNum < 0 || yearsNum > 60) {
      Alert.alert("Missing info", "Please enter your years of experience (0–60).");
      return;
    }
    if (specialties.length === 0) {
      Alert.alert("Missing info", "Select at least one specialty.");
      return;
    }

    setSaving(true);
    try {
      await upsertDetailerProfile({
        bio: bio.trim(),
        years_of_experience: yearsNum,
        service_radius_miles: radius,
        specialties,
      });
      await navigateAfterAuth(navigation);
    } catch {
      Alert.alert("Error", "Could not save your profile. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <SafeAreaView style={styles.safe}>
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
          <LinearGradient
            colors={["#1E3A5F", "#0F172A"]}
            style={styles.header}
          >
            <View style={styles.logoWrap}>
              <MaterialCommunityIcons name="car-wash" size={36} color="#60A5FA" />
            </View>
            <Text style={styles.headerTitle}>Set Up Your Profile</Text>
            <Text style={styles.headerSub}>
              Tell clients what makes you the best detailer around.
            </Text>
          </LinearGradient>

          <View style={styles.body}>
            {/* Bio */}
            <View style={styles.section}>
              <Text style={styles.label}>Professional Bio</Text>
              <TextInput
                style={[styles.input, styles.textArea]}
                value={bio}
                onChangeText={setBio}
                placeholder="E.g. 7+ years specializing in ceramic coatings and paint correction. Mobile service throughout Fort Wayne..."
                placeholderTextColor="#475569"
                multiline
                numberOfLines={4}
                textAlignVertical="top"
                maxLength={400}
              />
              <Text style={styles.charCount}>{bio.length}/400</Text>
            </View>

            {/* Years of Experience */}
            <View style={styles.section}>
              <Text style={styles.label}>Years of Experience</Text>
              <View style={styles.inputRow}>
                <TextInput
                  style={[styles.input, styles.inputShort]}
                  value={years}
                  onChangeText={(v) => setYears(v.replace(/[^0-9]/g, ""))}
                  placeholder="0"
                  placeholderTextColor="#475569"
                  keyboardType="number-pad"
                  maxLength={2}
                />
                <Text style={styles.inputUnit}>years</Text>
              </View>
            </View>

            {/* Service Radius */}
            <View style={styles.section}>
              <Text style={styles.label}>Service Radius</Text>
              <Text style={styles.labelSub}>How far will you travel for a job?</Text>
              <View style={styles.pillRow}>
                {RADIUS_OPTIONS.map((r) => (
                  <TouchableOpacity
                    key={r}
                    style={[styles.pill, radius === r && styles.pillActive]}
                    onPress={() => setRadius(r)}
                  >
                    <Text style={[styles.pillText, radius === r && styles.pillTextActive]}>
                      {r} mi
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>

            {/* Specialties */}
            <View style={styles.section}>
              <Text style={styles.label}>Your Specialties</Text>
              <Text style={styles.labelSub}>Select all that apply</Text>
              <View style={styles.chipGrid}>
                {SPECIALTIES.map((s) => {
                  const active = specialties.includes(s.key);
                  return (
                    <TouchableOpacity
                      key={s.key}
                      style={[styles.chip, active && styles.chipActive]}
                      onPress={() => toggleSpecialty(s.key)}
                    >
                      <MaterialCommunityIcons
                        name={s.icon as any}
                        size={16}
                        color={active ? "#FFFFFF" : "#60A5FA"}
                        style={{ marginRight: 6 }}
                      />
                      <Text style={[styles.chipText, active && styles.chipTextActive]}>
                        {s.label}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </View>
            </View>

            {/* Submit */}
            <TouchableOpacity
              style={[styles.submitBtn, saving && styles.submitBtnDisabled]}
              onPress={handleSubmit}
              disabled={saving}
              activeOpacity={0.85}
            >
              {saving ? (
                <ActivityIndicator color="#FFFFFF" />
              ) : (
                <>
                  <Ionicons name="checkmark-circle-outline" size={20} color="#FFFFFF" style={{ marginRight: 8 }} />
                  <Text style={styles.submitText}>Launch My Profile</Text>
                </>
              )}
            </TouchableOpacity>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  scroll: {
    flexGrow: 1,
  },
  header: {
    paddingTop: 40,
    paddingBottom: 36,
    paddingHorizontal: 24,
    alignItems: "center",
  },
  logoWrap: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: "rgba(96,165,250,0.12)",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 16,
  },
  headerTitle: {
    fontSize: 26,
    fontWeight: "700",
    color: "#F1F5F9",
    textAlign: "center",
    marginBottom: 8,
  },
  headerSub: {
    fontSize: 14,
    color: "#94A3B8",
    textAlign: "center",
    lineHeight: 20,
  },
  body: {
    flex: 1,
    padding: 20,
  },
  section: {
    marginBottom: 28,
  },
  label: {
    fontSize: 14,
    fontWeight: "600",
    color: "#CBD5E1",
    marginBottom: 4,
    letterSpacing: 0.4,
  },
  labelSub: {
    fontSize: 12,
    color: "#64748B",
    marginBottom: 12,
  },
  input: {
    backgroundColor: "#1E293B",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#334155",
    color: "#F1F5F9",
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 15,
  },
  textArea: {
    minHeight: 100,
    paddingTop: 14,
  },
  charCount: {
    fontSize: 11,
    color: "#475569",
    textAlign: "right",
    marginTop: 4,
  },
  inputRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  inputShort: {
    width: 90,
    textAlign: "center",
    fontSize: 22,
    fontWeight: "700",
    color: "#60A5FA",
  },
  inputUnit: {
    fontSize: 16,
    color: "#64748B",
  },
  pillRow: {
    flexDirection: "row",
    gap: 10,
    flexWrap: "wrap",
  },
  pill: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 24,
    backgroundColor: "#1E293B",
    borderWidth: 1,
    borderColor: "#334155",
  },
  pillActive: {
    backgroundColor: "#1D4ED8",
    borderColor: "#3B82F6",
  },
  pillText: {
    color: "#94A3B8",
    fontSize: 14,
    fontWeight: "500",
  },
  pillTextActive: {
    color: "#FFFFFF",
    fontWeight: "700",
  },
  chipGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
  },
  chip: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 14,
    paddingVertical: 9,
    borderRadius: 20,
    backgroundColor: "#1E293B",
    borderWidth: 1,
    borderColor: "#334155",
  },
  chipActive: {
    backgroundColor: "#1D4ED8",
    borderColor: "#3B82F6",
  },
  chipText: {
    fontSize: 13,
    color: "#94A3B8",
    fontWeight: "500",
  },
  chipTextActive: {
    color: "#FFFFFF",
    fontWeight: "600",
  },
  submitBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#2563EB",
    borderRadius: 14,
    paddingVertical: 16,
    marginTop: 8,
    marginBottom: 32,
  },
  submitBtnDisabled: {
    opacity: 0.5,
  },
  submitText: {
    fontSize: 16,
    fontWeight: "700",
    color: "#FFFFFF",
  },
});
