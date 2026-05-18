/**
 * frontend/src/screens/ClientPreferencesScreen.tsx
 *
 * Profile → Client preferences. Surfaces the four ClientProfile fields
 * (default vehicle, default address, marketing opt-in, frequency) and
 * lets the user pick from their own resources.
 *
 * The default_vehicle_id / default_address_id are picked from the
 * existing /addresses + /vehicles lists. Server-side validation
 * rejects unowned IDs with 404 — we let that bubble up as a generic
 * error since the picker should only show owned options anyway.
 */
import { Ionicons } from "@expo/vector-icons";
import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Modal,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import Button from "../components/Button";
import {
  useAddresses,
  useClientPreferences,
  usePutClientPreferences,
} from "../hooks/useProfileResources";
import type { Address } from "../services/addresses.service";
import { getMyVehicles, Vehicle } from "../services/vehicle.service";
import { Colors } from "../theme/colors";

const FREQUENCIES = [
  { value: null as string | null, label: "No preference" },
  { value: "weekly", label: "Weekly" },
  { value: "biweekly", label: "Every two weeks" },
  { value: "monthly", label: "Monthly" },
];

// ─── Resource picker modal (shared for vehicle + address) ────────────────────

interface PickerOption {
  id: string | null;
  title: string;
  subtitle?: string;
}

interface PickerProps {
  visible: boolean;
  title: string;
  options: PickerOption[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  onClose: () => void;
}

function PickerModal({
  visible,
  title,
  options,
  selectedId,
  onSelect,
  onClose,
}: PickerProps) {
  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
      <View style={styles.modalBackdrop}>
        <View style={styles.modalBody}>
          <View style={styles.modalHead}>
            <Text style={styles.modalTitle}>{title}</Text>
            <TouchableOpacity onPress={onClose} hitSlop={12}>
              <Ionicons name="close" size={22} color={Colors.text} />
            </TouchableOpacity>
          </View>
          <ScrollView>
            {options.map((opt) => {
              const active = opt.id === selectedId;
              return (
                <TouchableOpacity
                  key={String(opt.id)}
                  style={[styles.option, active && styles.optionActive]}
                  onPress={() => {
                    onSelect(opt.id);
                    onClose();
                  }}
                >
                  <View style={{ flex: 1 }}>
                    <Text style={styles.optionTitle}>{opt.title}</Text>
                    {opt.subtitle ? (
                      <Text style={styles.optionSub}>{opt.subtitle}</Text>
                    ) : null}
                  </View>
                  {active ? (
                    <Ionicons name="checkmark" size={20} color={Colors.primary} />
                  ) : null}
                </TouchableOpacity>
              );
            })}
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

// ─── Main screen ──────────────────────────────────────────────────────────────

export default function ClientPreferencesScreen({ navigation }: any) {
  const prefsQuery = useClientPreferences();
  const addressesQuery = useAddresses();
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [vehicleLoading, setVehicleLoading] = useState(true);
  const putPrefs = usePutClientPreferences();

  const [defaultVehicleId, setDefaultVehicleId] = useState<string | null>(null);
  const [defaultAddressId, setDefaultAddressId] = useState<string | null>(null);
  const [marketingOptIn, setMarketingOptIn] = useState(false);
  const [frequency, setFrequency] = useState<string | null>(null);

  const [pickerOpen, setPickerOpen] = useState<"vehicle" | "address" | "frequency" | null>(null);

  // Hydrate local state from server response (one-time on first load).
  useEffect(() => {
    if (prefsQuery.data) {
      setDefaultVehicleId(prefsQuery.data.default_vehicle_id);
      setDefaultAddressId(prefsQuery.data.default_address_id);
      setMarketingOptIn(prefsQuery.data.marketing_opt_in);
      setFrequency(prefsQuery.data.frequency_preference);
    }
  }, [prefsQuery.data]);

  // Vehicles list — pulled from the legacy service, since we don't have
  // a useVehicles hook yet and this is a side-info concern.
  useEffect(() => {
    let cancelled = false;
    setVehicleLoading(true);
    getMyVehicles()
      .then((rows) => {
        if (!cancelled) setVehicles(rows);
      })
      .catch(() => {
        if (!cancelled) setVehicles([]);
      })
      .finally(() => {
        if (!cancelled) setVehicleLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSave = () => {
    putPrefs.mutate(
      {
        default_vehicle_id: defaultVehicleId,
        default_address_id: defaultAddressId,
        marketing_opt_in: marketingOptIn,
        frequency_preference: frequency,
      },
      {
        onSuccess: () => navigation.goBack(),
        onError: () =>
          Alert.alert("Could not save", "Please try again."),
      },
    );
  };

  const vehicleOptions: PickerOption[] = [
    { id: null, title: "No default vehicle" },
    ...vehicles.map((v) => ({
      id: v.id,
      title: `${v.year} ${v.make} ${v.model}`,
      subtitle: v.license_plate,
    })),
  ];

  const addressOptions: PickerOption[] = [
    { id: null, title: "No default address" },
    ...(addressesQuery.data ?? []).map((a: Address) => ({
      id: a.id,
      title: a.label ?? "Address",
      subtitle: `${a.line1}, ${a.city}`,
    })),
  ];

  const frequencyOptions: PickerOption[] = FREQUENCIES.map((f) => ({
    id: f.value,
    title: f.label,
  }));

  const currentVehicle = vehicles.find((v) => v.id === defaultVehicleId);
  const currentAddress = addressesQuery.data?.find(
    (a: Address) => a.id === defaultAddressId,
  );
  const currentFrequency = FREQUENCIES.find((f) => f.value === frequency);

  const initialLoading =
    prefsQuery.isLoading || addressesQuery.isLoading || vehicleLoading;

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
        <Text style={styles.headerTitle}>Preferences</Text>
        <View style={{ width: 32 }} />
      </View>

      {initialLoading ? (
        <View style={styles.center}>
          <ActivityIndicator color={Colors.primary} />
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.body}>
          <Text style={styles.sectionLabel}>Defaults</Text>

          <TouchableOpacity
            style={styles.pickerRow}
            onPress={() => setPickerOpen("vehicle")}
          >
            <Ionicons name="car-outline" size={20} color={Colors.primary} />
            <View style={{ flex: 1 }}>
              <Text style={styles.pickerLabel}>Default vehicle</Text>
              <Text style={styles.pickerValue}>
                {currentVehicle
                  ? `${currentVehicle.year} ${currentVehicle.make} ${currentVehicle.model}`
                  : "Not set"}
              </Text>
            </View>
            <Ionicons name="chevron-forward" size={18} color="#475569" />
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.pickerRow}
            onPress={() => setPickerOpen("address")}
          >
            <Ionicons name="location-outline" size={20} color={Colors.primary} />
            <View style={{ flex: 1 }}>
              <Text style={styles.pickerLabel}>Default address</Text>
              <Text style={styles.pickerValue}>
                {currentAddress
                  ? `${currentAddress.label ?? "Address"} — ${currentAddress.line1}`
                  : "Not set"}
              </Text>
            </View>
            <Ionicons name="chevron-forward" size={18} color="#475569" />
          </TouchableOpacity>

          <Text style={styles.sectionLabel}>Cadence</Text>

          <TouchableOpacity
            style={styles.pickerRow}
            onPress={() => setPickerOpen("frequency")}
          >
            <Ionicons name="calendar-outline" size={20} color={Colors.primary} />
            <View style={{ flex: 1 }}>
              <Text style={styles.pickerLabel}>Service frequency</Text>
              <Text style={styles.pickerValue}>
                {currentFrequency?.label ?? "No preference"}
              </Text>
            </View>
            <Ionicons name="chevron-forward" size={18} color="#475569" />
          </TouchableOpacity>

          <Text style={styles.sectionLabel}>Communication</Text>

          <View style={styles.toggleRow}>
            <View style={{ flex: 1 }}>
              <Text style={styles.toggleLabel}>Marketing emails</Text>
              <Text style={styles.toggleHint}>
                Tips, promotions, and seasonal reminders.
              </Text>
            </View>
            <Switch
              value={marketingOptIn}
              onValueChange={setMarketingOptIn}
              trackColor={{ false: "#1E293B", true: "rgba(59,130,246,0.45)" }}
              thumbColor={marketingOptIn ? Colors.primary : "#94A3B8"}
            />
          </View>

          <Button
            title="Save preferences"
            onPress={handleSave}
            loading={putPrefs.isPending}
            disabled={putPrefs.isPending}
            style={{ marginTop: 28 }}
          />
        </ScrollView>
      )}

      <PickerModal
        visible={pickerOpen === "vehicle"}
        title="Choose default vehicle"
        options={vehicleOptions}
        selectedId={defaultVehicleId}
        onSelect={(id) => setDefaultVehicleId(id)}
        onClose={() => setPickerOpen(null)}
      />
      <PickerModal
        visible={pickerOpen === "address"}
        title="Choose default address"
        options={addressOptions}
        selectedId={defaultAddressId}
        onSelect={(id) => setDefaultAddressId(id)}
        onClose={() => setPickerOpen(null)}
      />
      <PickerModal
        visible={pickerOpen === "frequency"}
        title="Service frequency"
        options={frequencyOptions}
        selectedId={frequency}
        onSelect={(id) => setFrequency(id)}
        onClose={() => setPickerOpen(null)}
      />
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
  sectionLabel: {
    color: Colors.secondaryText,
    fontSize: 12,
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: 0.5,
    marginTop: 16,
    marginBottom: 8,
  },
  pickerRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    backgroundColor: Colors.card,
    borderRadius: 12,
    padding: 14,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: "#1E293B",
  },
  pickerLabel: { color: Colors.text, fontSize: 14, fontWeight: "500" },
  pickerValue: { color: Colors.secondaryText, fontSize: 12, marginTop: 2 },
  toggleRow: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colors.card,
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: "#1E293B",
  },
  toggleLabel: { color: Colors.text, fontSize: 14, fontWeight: "500" },
  toggleHint: { color: "#64748B", fontSize: 12, marginTop: 2 },

  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.55)",
    justifyContent: "flex-end",
  },
  modalBody: {
    backgroundColor: Colors.card,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 20,
    maxHeight: "70%",
  },
  modalHead: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 12,
  },
  modalTitle: { color: Colors.text, fontSize: 18, fontWeight: "700" },
  option: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 14,
    paddingHorizontal: 4,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: "#1E293B",
  },
  optionActive: { backgroundColor: "rgba(59,130,246,0.06)" },
  optionTitle: { color: Colors.text, fontSize: 15 },
  optionSub: { color: Colors.secondaryText, fontSize: 12, marginTop: 2 },
});
