/**
 * frontend/src/screens/AddressFormScreen.tsx
 *
 * Create / edit a UserAddress. Route accepts an optional `address` param;
 * when present we PATCH the existing row, otherwise we POST a new one.
 *
 * Local-only validation: line1, city, state, zip required. Geocoding
 * happens server-side — if Nominatim is unavailable the row is saved
 * with NULL coordinates and the matching engine just skips it; the
 * user doesn't see the failure.
 */
import { Ionicons } from "@expo/vector-icons";
import React, { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import Button from "../components/Button";
import {
  useCreateAddress,
  useUpdateAddress,
} from "../hooks/useProfileResources";
import type { Address } from "../services/addresses.service";
import { Colors } from "../theme/colors";

interface FieldProps {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  maxLength?: number;
  autoCapitalize?: "none" | "characters" | "words";
  required?: boolean;
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  maxLength,
  autoCapitalize = "sentences" as any,
  required,
}: FieldProps) {
  return (
    <View style={styles.field}>
      <Text style={styles.fieldLabel}>
        {label} {required ? <Text style={styles.required}>*</Text> : null}
      </Text>
      <TextInput
        style={styles.input}
        value={value}
        onChangeText={onChange}
        placeholder={placeholder}
        placeholderTextColor="#475569"
        maxLength={maxLength}
        autoCapitalize={autoCapitalize}
      />
    </View>
  );
}

export default function AddressFormScreen({ navigation, route }: any) {
  const initial: Address | null = route.params?.address ?? null;
  const isEdit = Boolean(initial);

  const [label, setLabel] = useState(initial?.label ?? "Home");
  const [line1, setLine1] = useState(initial?.line1 ?? "");
  const [line2, setLine2] = useState(initial?.line2 ?? "");
  const [city, setCity] = useState(initial?.city ?? "");
  const [state, setState] = useState(initial?.state ?? "");
  const [zipCode, setZipCode] = useState(initial?.zip_code ?? "");
  const [country, setCountry] = useState(initial?.country ?? "US");
  const [notes, setNotes] = useState(initial?.notes ?? "");
  const [isDefault, setIsDefault] = useState(initial?.is_default ?? false);

  const createMutation = useCreateAddress();
  const updateMutation = useUpdateAddress(initial?.id ?? "");

  const submitting = createMutation.isPending || updateMutation.isPending;

  const handleSubmit = () => {
    if (!line1.trim() || !city.trim() || !state.trim() || !zipCode.trim()) {
      Alert.alert("Missing fields", "Street, city, state and ZIP are required.");
      return;
    }

    const payload = {
      label: label.trim() || null,
      line1: line1.trim(),
      line2: line2.trim() || null,
      city: city.trim(),
      state: state.trim(),
      zip_code: zipCode.trim(),
      country: country.trim() || "US",
      notes: notes.trim() || null,
      is_default: isDefault,
    };

    const onSuccess = () => navigation.goBack();
    const onError = () =>
      Alert.alert(
        "Could not save",
        "Please check the address details and try again.",
      );

    if (isEdit) {
      updateMutation.mutate(payload, { onSuccess, onError });
    } else {
      createMutation.mutate(payload, { onSuccess, onError });
    }
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
        <Text style={styles.headerTitle}>
          {isEdit ? "Edit address" : "Add address"}
        </Text>
        <View style={{ width: 32 }} />
      </View>

      <ScrollView contentContainerStyle={styles.body}>
        <Field
          label="Label"
          value={label}
          onChange={setLabel}
          placeholder="Home, Work, Mom's house"
          maxLength={40}
        />
        <Field
          label="Street address"
          value={line1}
          onChange={setLine1}
          placeholder="123 Main St"
          maxLength={200}
          required
        />
        <Field
          label="Apt / Suite / Floor"
          value={line2}
          onChange={setLine2}
          placeholder="Apt 4B"
          maxLength={200}
        />
        <Field
          label="City"
          value={city}
          onChange={setCity}
          placeholder="Indianapolis"
          maxLength={120}
          required
        />
        <View style={styles.row}>
          <View style={{ flex: 1 }}>
            <Field
              label="State"
              value={state}
              onChange={setState}
              placeholder="IN"
              maxLength={60}
              autoCapitalize="characters"
              required
            />
          </View>
          <View style={{ flex: 1 }}>
            <Field
              label="ZIP"
              value={zipCode}
              onChange={setZipCode}
              placeholder="46201"
              maxLength={20}
              required
            />
          </View>
        </View>
        <Field
          label="Country"
          value={country}
          onChange={setCountry}
          placeholder="US"
          maxLength={60}
          autoCapitalize="characters"
        />
        <Field
          label="Notes (gate code, parking)"
          value={notes}
          onChange={setNotes}
          placeholder="Buzzer 4B; park on the right"
        />

        <View style={styles.defaultRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.defaultTitle}>Set as default</Text>
            <Text style={styles.defaultHint}>
              Booking flows will pre-fill this address.
            </Text>
          </View>
          <Switch
            value={isDefault}
            onValueChange={setIsDefault}
            trackColor={{ false: "#1E293B", true: "rgba(59,130,246,0.45)" }}
            thumbColor={isDefault ? Colors.primary : "#94A3B8"}
          />
        </View>

        <Button
          title={isEdit ? "Save changes" : "Add address"}
          onPress={handleSubmit}
          loading={submitting}
          disabled={submitting}
          style={{ marginTop: 24 }}
        />
        {submitting ? (
          <ActivityIndicator style={{ marginTop: 12 }} color={Colors.primary} />
        ) : null}
      </ScrollView>
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
  row: { flexDirection: "row", gap: 12 },
  defaultRow: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colors.card,
    borderRadius: 12,
    padding: 14,
    marginTop: 12,
    borderWidth: 1,
    borderColor: "#1E293B",
  },
  defaultTitle: { color: Colors.text, fontSize: 15, fontWeight: "600" },
  defaultHint: { color: "#64748B", fontSize: 12, marginTop: 2 },
});
