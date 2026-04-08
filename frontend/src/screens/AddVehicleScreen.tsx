import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import React, { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Modal,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { addVehicle, decodeVehicleVin } from "../services/vehicle.service";
import { Colors } from "../theme/colors";

const COLORS = [
  "White",
  "Black",
  "Silver",
  "Gray",
  "Red",
  "Blue",
  "Brown",
  "Green",
  "Yellow",
  "Orange",
];
const YEARS = Array.from({ length: 40 }, (_, i) =>
  (new Date().getFullYear() - i).toString(),
);
const BODY_TYPES = [
  "Sedan",
  "SUV",
  "Pickup",
  "Coupe",
  "Van",
  "Hatchback",
  "Convertible",
];

export default function AddVehicleScreen({ navigation }: any) {
  const [loading, setLoading] = useState(false);
  const [decoding, setDecoding] = useState(false);

  const [modalType, setModalType] = useState<"year" | "color" | "body" | null>(
    null,
  );

  const [formData, setFormData] = useState({
    vin: "",
    make: "",
    model: "",
    year: new Date().getFullYear().toString(),
    body_class: "Sedan",
    color: "White",
    license_plate: "",
  });

  const handleVinLookup = async () => {
    if (formData.vin.length !== 17) {
      Alert.alert("Invalid VIN", "Please enter a 17-character VIN.");
      return;
    }
    setDecoding(true);
    try {
      const data = await decodeVehicleVin(formData.vin);
      setFormData((prev) => ({
        ...prev,
        make: data.make || prev.make,
        model: data.model || prev.model,
        year: data.year?.toString() || prev.year,
        body_class: data.body_class || prev.body_class,
      }));
    } catch (error) {
      Alert.alert(
        "VIN Error",
        "Could not auto-fill details. Please enter manually.",
      );
    } finally {
      setDecoding(false);
    }
  };

  const handleSave = async () => {
    // 1. Frontend validation
    if (formData.vin && formData.vin.length !== 17) {
      Alert.alert("Error", "VIN must be exactly 17 characters.");
      return;
    }
    if (!formData.make || !formData.model || !formData.license_plate) {
      Alert.alert(
        "Missing Fields",
        "Make, Model, and License Plate are required.",
      );
      return;
    }

    setLoading(true);
    try {
      // 2. Build payload for VehicleCreate
      const payload = {
        vin: formData.vin ? formData.vin.toUpperCase() : null,
        make: formData.make.toUpperCase(),
        model: formData.model.toUpperCase(),
        year: parseInt(formData.year, 10),
        body_class: formData.body_class,
        color: formData.color,
        license_plate: formData.license_plate.toUpperCase(),
        series: (formData as any).series || "", // Empty string if field not available
        notes: (formData as any).notes || "",
      };

      await addVehicle(payload);

      Alert.alert("Success", "Vehicle saved!", [
        { text: "OK", onPress: () => navigation.goBack() },
      ]);
    } catch (error: any) {
      const detail = error.response?.data?.detail;
      const msg = Array.isArray(detail)
        ? `${detail[0].loc[1]}: ${detail[0].msg}`
        : "Server Error";

      Alert.alert("Save Failed", msg);
    } finally {
      setLoading(false);
    }
  };

  // Render each option in the modal list
  const renderOption = ({ item }: { item: string }) => (
    <TouchableOpacity
      style={styles.optionItem}
      onPress={() => {
        if (modalType === "year") setFormData({ ...formData, year: item });
        if (modalType === "color") setFormData({ ...formData, color: item });
        if (modalType === "body")
          setFormData({ ...formData, body_class: item });
        setModalType(null); // Close modal on selection
      }}
    >
      <Text style={styles.optionText}>{item}</Text>
      {(formData.year === item ||
        formData.color === item ||
        formData.body_class === item) && (
        <Ionicons name="checkmark-circle" size={20} color={Colors.primary} />
      )}
    </TouchableOpacity>
  );

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          style={styles.backBtn}
        >
          <Ionicons name="close" size={24} color="white" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>New Vehicle</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* VIN Card */}
        <View style={styles.vinCard}>
          <Text style={styles.label}>VIN DECODER (AUTO-FILL)</Text>
          <View style={styles.vinRow}>
            <TextInput
              style={styles.vinInput}
              placeholder="Enter 17-digit VIN"
              placeholderTextColor="#475569"
              autoCapitalize="characters"
              value={formData.vin}
              onChangeText={(t) => setFormData({ ...formData, vin: t })}
            />
            <TouchableOpacity
              style={styles.decodeBtn}
              onPress={handleVinLookup}
            >
              {decoding ? (
                <ActivityIndicator color="#0F172A" size="small" />
              ) : (
                <Ionicons name="flash" size={18} color="#0F172A" />
              )}
            </TouchableOpacity>
          </View>
        </View>

        {/* Inputs */}
        <View style={styles.form}>
          <View style={styles.row}>
            <View style={styles.field}>
              <Text style={styles.label}>MAKE</Text>
              <TextInput
                style={styles.input}
                value={formData.make}
                autoCapitalize="characters"
                onChangeText={(t) => setFormData({ ...formData, make: t })}
                placeholder="Ford"
                placeholderTextColor="#475569"
              />
            </View>
            <View style={styles.field}>
              <Text style={styles.label}>MODEL</Text>
              <TextInput
                style={styles.input}
                value={formData.model}
                autoCapitalize="characters"
                onChangeText={(t) => setFormData({ ...formData, model: t })}
                placeholder="Edge"
                placeholderTextColor="#475569"
              />
            </View>
          </View>

          <View style={styles.row}>
            
            <TouchableOpacity
              style={styles.field}
              onPress={() => setModalType("year")}
            >
              <Text style={styles.label}>YEAR</Text>
              <View style={styles.selector}>
                <Text style={styles.selectorText}>{formData.year}</Text>
                <Ionicons
                  name="chevron-down"
                  size={16}
                  color={Colors.primary}
                />
              </View>
            </TouchableOpacity>

            
            <TouchableOpacity
              style={styles.field}
              onPress={() => setModalType("color")}
            >
              <Text style={styles.label}>COLOR</Text>
              <View style={styles.selector}>
                <Text style={styles.selectorText}>{formData.color}</Text>
                <Ionicons
                  name="chevron-down"
                  size={16}
                  color={Colors.primary}
                />
              </View>
            </TouchableOpacity>
          </View>

          
          <TouchableOpacity
            style={styles.fullField}
            onPress={() => setModalType("body")}
          >
            <Text style={styles.label}>BODY TYPE</Text>
            <View style={styles.selector}>
              <Text style={styles.selectorText}>{formData.body_class}</Text>
              <Ionicons name="chevron-down" size={16} color={Colors.primary} />
            </View>
          </TouchableOpacity>

          <View style={styles.fullField}>
            <Text style={styles.label}>LICENSE PLATE</Text>
            <TextInput
              style={styles.input}
              value={formData.license_plate}
              autoCapitalize="characters"
              onChangeText={(t) =>
                setFormData({ ...formData, license_plate: t })
              }
              placeholder="ABC-123"
              placeholderTextColor="#475569"
            />
          </View>
        </View>

        <TouchableOpacity style={styles.saveBtn} onPress={handleSave}>
          <LinearGradient
            colors={[Colors.primary, "#60A5FA"]}
            style={styles.saveGradient}
          >
            {loading ? (
              <ActivityIndicator color="#0F172A" />
            ) : (
              <Text style={styles.saveBtnText}>ADD TO GARAGE</Text>
            )}
          </LinearGradient>
        </TouchableOpacity>
      </ScrollView>

      
      <Modal visible={modalType !== null} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>
                Select {modalType?.toUpperCase()}
              </Text>
              <TouchableOpacity onPress={() => setModalType(null)}>
                <Ionicons name="close-circle" size={28} color="#475569" />
              </TouchableOpacity>
            </View>
            <FlatList
              data={
                modalType === "year"
                  ? YEARS
                  : modalType === "color"
                    ? COLORS
                    : BODY_TYPES
              }
              renderItem={renderOption}
              keyExtractor={(item) => item}
              style={{ maxHeight: 400 }}
            />
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0B0F1A" },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    padding: 20,
  },
  backBtn: { backgroundColor: "#1E293B", padding: 8, borderRadius: 12 },
  headerTitle: { color: "white", fontSize: 20, fontWeight: "bold" },
  scrollContent: { padding: 20 },
  vinCard: {
    backgroundColor: "#161E2E",
    padding: 20,
    borderRadius: 20,
    marginBottom: 25,
    borderWidth: 1,
    borderColor: "#262F3F",
  },
  vinRow: { flexDirection: "row", gap: 10, marginTop: 10 },
  vinInput: {
    flex: 1,
    backgroundColor: "#0B0F1A",
    color: "white",
    padding: 15,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#334155",
  },
  decodeBtn: {
    backgroundColor: Colors.primary,
    width: 50,
    borderRadius: 12,
    justifyContent: "center",
    alignItems: "center",
  },
  label: {
    color: "#94A3B8",
    fontSize: 11,
    fontWeight: "bold",
    marginBottom: 8,
    letterSpacing: 1,
  },
  form: { gap: 20 },
  row: { flexDirection: "row", gap: 15 },
  field: { flex: 1 },
  fullField: { width: "100%" },
  input: {
    backgroundColor: "#161E2E",
    color: "white",
    padding: 15,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#262F3F",
  },
  selector: {
    backgroundColor: "#161E2E",
    padding: 15,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#262F3F",
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  selectorText: { color: "white" },
  saveBtn: { marginTop: 40, borderRadius: 15, overflow: "hidden" },
  saveGradient: { padding: 20, alignItems: "center" },
  saveBtnText: { color: "#0F172A", fontWeight: "900", fontSize: 16 },
  // Modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.8)",
    justifyContent: "flex-end",
  },
  modalContent: {
    backgroundColor: "#161E2E",
    borderTopLeftRadius: 30,
    borderTopRightRadius: 30,
    padding: 25,
  },
  modalHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 20,
  },
  modalTitle: { color: "white", fontSize: 18, fontWeight: "bold" },
  optionItem: {
    paddingVertical: 15,
    borderBottomWidth: 1,
    borderBottomColor: "#262F3F",
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  optionText: { color: "#94A3B8", fontSize: 16 },
});
