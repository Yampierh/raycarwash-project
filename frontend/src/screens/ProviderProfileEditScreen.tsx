/**
 * frontend/src/screens/ProviderProfileEditScreen.tsx
 *
 * Edit the detailer's public-facing profile. business_name, display
 * name, tagline, bio, years, service radius. Working hours + social
 * links land as a follow-up — the form would balloon otherwise and
 * the backend already accepts them in the PATCH body.
 *
 * The "Pause provider mode" CTA at the bottom routes to the
 * deactivate flow (which is step-up gated server-side).
 */
import { Ionicons } from "@expo/vector-icons";
import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import Button from "../components/Button";
import {
  useDeactivateProvider,
  useProviderProfile,
  useUpdateProvider,
} from "../hooks/useProviderResources";
import { StepUpRequiredError } from "../lib/api-error";
import { Colors } from "../theme/colors";

interface FieldProps {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  maxLength?: number;
  multiline?: boolean;
  required?: boolean;
  keyboardType?: "default" | "numeric";
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  maxLength,
  multiline,
  required,
  keyboardType = "default",
}: FieldProps) {
  return (
    <View style={styles.field}>
      <Text style={styles.fieldLabel}>
        {label} {required ? <Text style={styles.required}>*</Text> : null}
      </Text>
      <TextInput
        style={[styles.input, multiline && styles.inputMultiline]}
        value={value}
        onChangeText={onChange}
        placeholder={placeholder}
        placeholderTextColor="#475569"
        maxLength={maxLength}
        multiline={multiline}
        numberOfLines={multiline ? 4 : 1}
        keyboardType={keyboardType}
      />
    </View>
  );
}

export default function ProviderProfileEditScreen({ navigation }: any) {
  const profileQuery = useProviderProfile();
  const update = useUpdateProvider();
  const deactivate = useDeactivateProvider();

  const [businessName, setBusinessName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [tagline, setTagline] = useState("");
  const [bio, setBio] = useState("");
  const [years, setYears] = useState("");
  const [radius, setRadius] = useState("25");
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    if (profileQuery.data && !hydrated) {
      setBusinessName(profileQuery.data.business_name ?? "");
      setDisplayName(profileQuery.data.display_name ?? "");
      setTagline(profileQuery.data.tagline ?? "");
      setBio(profileQuery.data.bio ?? "");
      setYears(
        profileQuery.data.years_of_experience !== null
          ? String(profileQuery.data.years_of_experience)
          : "",
      );
      setRadius(String(profileQuery.data.service_radius_miles ?? 25));
      setHydrated(true);
    }
  }, [profileQuery.data, hydrated]);

  const handleSave = () => {
    if (!businessName.trim()) {
      Alert.alert("Missing field", "Business name is required.");
      return;
    }

    const parsedYears = years.trim() ? Number.parseInt(years, 10) : null;
    if (years.trim() && (isNaN(parsedYears!) || parsedYears! < 0)) {
      Alert.alert("Invalid value", "Years of experience must be a positive number.");
      return;
    }
    const parsedRadius = Number.parseInt(radius, 10);
    if (isNaN(parsedRadius) || parsedRadius < 1 || parsedRadius > 200) {
      Alert.alert("Invalid value", "Service radius must be between 1 and 200 miles.");
      return;
    }

    update.mutate(
      {
        business_name: businessName.trim(),
        display_name: displayName.trim() || null,
        tagline: tagline.trim() || null,
        bio: bio.trim() || null,
        years_of_experience: parsedYears,
        service_radius_miles: parsedRadius,
      },
      {
        onSuccess: () => navigation.goBack(),
        onError: () => Alert.alert("Could not save", "Please try again."),
      },
    );
  };

  const handleDeactivate = () => {
    Alert.alert(
      "Pause provider mode?",
      "Your profile + KYC stay saved. You can re-activate any time.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Pause",
          style: "destructive",
          onPress: () =>
            deactivate.mutate(undefined, {
              onSuccess: () => navigation.goBack(),
              onError: (err) => {
                if (err instanceof StepUpRequiredError) {
                  Alert.alert(
                    "Verification required",
                    "Confirm it's you to pause provider mode.",
                  );
                  return;
                }
                Alert.alert("Could not pause", "Please try again.");
              },
            }),
        },
      ],
    );
  };

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          style={styles.backBtn}
          hitSlop={12}
        >
          <Ionicons name="chevron-back" size={24} color={Colors.text} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Edit business</Text>
        <View style={{ width: 32 }} />
      </View>

      {profileQuery.isLoading || !hydrated ? (
        <View style={styles.center}>
          <ActivityIndicator color={Colors.primary} />
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.body}>
          <Field
            label="Business name"
            value={businessName}
            onChange={setBusinessName}
            placeholder="Yampi Detailing LLC"
            maxLength={120}
            required
          />
          <Field
            label="Display name"
            value={displayName}
            onChange={setDisplayName}
            placeholder="Yampi"
            maxLength={80}
          />
          <Field
            label="Tagline"
            value={tagline}
            onChange={setTagline}
            placeholder="Ceramic specialist · Fort Wayne"
            maxLength={140}
          />
          <Field
            label="About"
            value={bio}
            onChange={setBio}
            placeholder="Tell clients about your background, certifications, what makes your work different..."
            multiline
          />
          <View style={styles.row}>
            <View style={{ flex: 1 }}>
              <Field
                label="Years experience"
                value={years}
                onChange={setYears}
                placeholder="5"
                keyboardType="numeric"
                maxLength={3}
              />
            </View>
            <View style={{ flex: 1 }}>
              <Field
                label="Service radius (mi)"
                value={radius}
                onChange={setRadius}
                placeholder="25"
                keyboardType="numeric"
                maxLength={3}
                required
              />
            </View>
          </View>

          <Button
            title="Save changes"
            onPress={handleSave}
            loading={update.isPending}
            disabled={update.isPending}
            style={{ marginTop: 24 }}
          />

          <TouchableOpacity
            style={styles.deactivateBtn}
            onPress={handleDeactivate}
            disabled={deactivate.isPending}
          >
            <Text style={styles.deactivateText}>
              {deactivate.isPending ? "Pausing…" : "Pause provider mode"}
            </Text>
          </TouchableOpacity>
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.background },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  backBtn: { padding: 4 },
  headerTitle: {
    flex: 1,
    color: Colors.text,
    fontSize: 18,
    fontWeight: "600",
    textAlign: "center",
  },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  body: { padding: 16, paddingBottom: 48 },
  field: { marginBottom: 14 },
  fieldLabel: {
    color: Colors.secondaryText,
    fontSize: 12,
    fontWeight: "600",
    marginBottom: 6,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  required: { color: "#EF4444" },
  input: {
    backgroundColor: "#111827",
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 12,
    color: Colors.text,
    borderWidth: 1,
    borderColor: "#1E293B",
    fontSize: 15,
  },
  inputMultiline: {
    minHeight: 100,
    textAlignVertical: "top",
  },
  row: { flexDirection: "row", gap: 12 },
  deactivateBtn: {
    marginTop: 24,
    padding: 12,
    alignItems: "center",
  },
  deactivateText: { color: "#EF4444", fontSize: 13, fontWeight: "500" },
});
