import { Ionicons } from "@expo/vector-icons";
import React, { useState } from "react";
import {
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
import Button from "../components/Button";
import { deleteVehicle, updateVehicle } from "../services/vehicle.service";
import { Colors } from "../theme/colors";

const COLORS = ["White", "Black", "Silver", "Gray", "Red", "Blue", "Brown", "Green", "Yellow", "Orange"];
const YEARS = Array.from({ length: 40 }, (_, i) => (new Date().getFullYear() - i).toString());
const BODY_TYPES = ["Sedan", "SUV", "Pickup", "Coupe", "Van", "Hatchback", "Convertible"];

export default function VehicleDetailScreen({ route, navigation }: any) {
  const { vehicle } = route.params;
  const [loadingSave, setLoadingSave] = useState(false);
  const [loadingDelete, setLoadingDelete] = useState(false);
  const [modalType, setModalType] = useState<"year" | "color" | "body" | null>(null);
  const [form, setForm] = useState({
    vin: vehicle.vin || "",
    make: vehicle.make || "",
    model: vehicle.model || "",
    year: vehicle.year?.toString() || new Date().getFullYear().toString(),
    body_class: vehicle.body_class || "Sedan",
    color: vehicle.color || "White",
    license_plate: vehicle.license_plate || "",
    notes: vehicle.notes || "",
  });

  const handleSaveChanges = async () => {
    setLoadingSave(true);
    try {
      await updateVehicle(vehicle.id, {
        vin: form.vin ? form.vin.toUpperCase().trim() : null,
        make: form.make.trim(),
        model: form.model.trim(),
        year: parseInt(form.year.toString(), 10),
        body_class: form.body_class,
        color: form.color,
        license_plate: form.license_plate.toUpperCase().trim(),
        series: vehicle.series || "",
        notes: form.notes || "",
      });
      Alert.alert("Success", "Vehicle updated!", [{ text: "OK", onPress: () => navigation.goBack() }]);
    } catch (error: any) {
      const detail = error.response?.data?.detail;
      const msg = Array.isArray(detail)
        ? `${detail[0].loc?.slice(-1)[0]}: ${detail[0].msg}`
        : typeof detail === "string" ? detail : "Check your connection and try again.";
      Alert.alert("Update Failed", msg);
    } finally {
      setLoadingSave(false);
    }
  };

  const handleDelete = () => {
    Alert.alert("Delete Vehicle", `Are you sure you want to remove the ${vehicle.make} ${vehicle.model}?`, [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: async () => {
          setLoadingDelete(true);
          try {
            await deleteVehicle(vehicle.id);
            navigation.goBack();
          } catch {
            Alert.alert("Error", "Could not delete vehicle.");
          } finally {
            setLoadingDelete(false);
          }
        },
      },
    ]);
  };

  const renderOption = ({ item }: { item: string }) => (
    <TouchableOpacity
      style={styles.optionItem}
      onPress={() => {
        if (modalType === "year") setForm({ ...form, year: item });
        if (modalType === "color") setForm({ ...form, color: item });
        if (modalType === "body") setForm({ ...form, body_class: item });
        setModalType(null);
      }}
    >
      <Text style={styles.optionText}>{item}</Text>
      {(form.year === item || form.color === item || form.body_class === item) && (
        <Ionicons name="checkmark-circle" size={20} color={Colors.primary} />
      )}
    </TouchableOpacity>
  );

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Ionicons name="close" size={24} color="white" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Vehicle Details</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        {/* VIN */}
        <View style={styles.vinCard}>
          <Text style={styles.label}>VEHICLE IDENTIFICATION NUMBER (VIN)</Text>
          <View style={styles.vinRow}>
            <Ionicons name="barcode-outline" size={20} color="#94A3B8" />
            <TextInput
              style={styles.vinInput}
              placeholder="17-digit VIN"
              placeholderTextColor="#475569"
              autoCapitalize="characters"
              maxLength={17}
              value={form.vin}
              onChangeText={(t) => setForm({ ...form, vin: t })}
            />
          </View>
        </View>

        {/* Form card */}
        <View style={styles.formCard}>
          <Text style={styles.cardLabel}>CORE INFORMATION</Text>

          <View style={styles.row}>
            <View style={styles.field}>
              <Text style={styles.label}>MAKE</Text>
              <TextInput style={styles.input} value={form.make} autoCapitalize="characters"
                onChangeText={(t) => setForm({ ...form, make: t })} placeholder="Ford" placeholderTextColor="#475569" />
            </View>
            <View style={styles.field}>
              <Text style={styles.label}>MODEL</Text>
              <TextInput style={styles.input} value={form.model} autoCapitalize="characters"
                onChangeText={(t) => setForm({ ...form, model: t })} placeholder="Edge" placeholderTextColor="#475569" />
            </View>
          </View>

          <View style={styles.row}>
            <TouchableOpacity style={styles.field} onPress={() => setModalType("year")}>
              <Text style={styles.label}>YEAR</Text>
              <View style={styles.selector}>
                <Text style={styles.selectorText}>{form.year}</Text>
                <Ionicons name="chevron-down" size={16} color={Colors.primary} />
              </View>
            </TouchableOpacity>
            <TouchableOpacity style={styles.field} onPress={() => setModalType("color")}>
              <Text style={styles.label}>COLOR</Text>
              <View style={styles.selector}>
                <Text style={styles.selectorText}>{form.color}</Text>
                <Ionicons name="chevron-down" size={16} color={Colors.primary} />
              </View>
            </TouchableOpacity>
          </View>

          <TouchableOpacity style={styles.fullField} onPress={() => setModalType("body")}>
            <Text style={styles.label}>BODY TYPE</Text>
            <View style={styles.selector}>
              <Text style={styles.selectorText}>{form.body_class}</Text>
              <Ionicons name="chevron-down" size={16} color={Colors.primary} />
            </View>
          </TouchableOpacity>

          <View style={styles.fullField}>
            <Text style={styles.label}>LICENSE PLATE</Text>
            <TextInput style={styles.input} value={form.license_plate} autoCapitalize="characters"
              onChangeText={(t) => setForm({ ...form, license_plate: t })} placeholder="ABC-123" placeholderTextColor="#475569" />
          </View>

          <View style={styles.fullField}>
            <Text style={styles.label}>NOTES (OPTIONAL)</Text>
            <TextInput
              style={[styles.input, styles.notesInput]}
              value={form.notes}
              multiline
              numberOfLines={3}
              onChangeText={(t) => setForm({ ...form, notes: t })}
              placeholder="Additional details..."
              placeholderTextColor="#475569"
            />
          </View>
        </View>

        {/* Phase 4 chunk W — vehicle photos entry point */}
        <View style={{ paddingHorizontal: 24, marginTop: 8 }}>
          <Button
            title="Manage photos"
            onPress={() =>
              navigation.navigate("VehiclePhotos", {
                vehicleId: vehicle.id,
                vehicleLabel: `${vehicle.year} ${vehicle.make} ${vehicle.model}`,
              })
            }
            variant="secondary"
            size="md"
            icon="images-outline"
            fullWidth
          />
        </View>

        <View style={{ height: 120 }} />
      </ScrollView>

      <View style={styles.footer}>
        <View style={styles.actionRow}>
          <Button
            title=""
            onPress={handleDelete}
            variant="danger"
            size="lg"
            icon="trash-outline"
            disabled={loadingDelete || loadingSave}
            loading={loadingDelete}
            style={{ width: 60 }}
          />
          <Button
            title="SAVE CHANGES"
            onPress={handleSaveChanges}
            variant="cta"
            size="lg"
            icon="cloud-upload-outline"
            loading={loadingSave}
            disabled={loadingSave || loadingDelete}
            style={{ flex: 1 }}
          />
        </View>
      </View>

      <Modal visible={modalType !== null} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Select {modalType?.toUpperCase()}</Text>
              <TouchableOpacity onPress={() => setModalType(null)}>
                <Ionicons name="close-circle" size={28} color="#475569" />
              </TouchableOpacity>
            </View>
            <FlatList
              data={modalType === "year" ? YEARS : modalType === "color" ? COLORS : BODY_TYPES}
              renderItem={renderOption}
              keyExtractor={(item) => item}
              style={{ maxHeight: 400 }}
              contentContainerStyle={{ paddingBottom: 30 }}
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
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: 20, paddingVertical: 15,
    borderBottomWidth: 1, borderBottomColor: "#161E2E",
  },
  backBtn: {
    backgroundColor: "#161E2E", padding: 8, borderRadius: 12,
    borderWidth: 1, borderColor: "#262F3F",
  },
  headerTitle: { color: "white", fontSize: 20, fontWeight: "800" },
  scrollContent: { padding: 20 },
  label: { color: "#94A3B8", fontSize: 11, fontWeight: "800", marginBottom: 8, letterSpacing: 1 },
  cardLabel: { color: Colors.primary, fontSize: 14, fontWeight: "800", marginBottom: 20, letterSpacing: 0.5 },
  vinCard: {
    backgroundColor: "#161E2E", padding: 20, borderRadius: 16,
    marginBottom: 16, borderWidth: 1, borderColor: "#262F3F",
  },
  vinRow: {
    flexDirection: "row", alignItems: "center", gap: 12, marginTop: 5,
    backgroundColor: "#0B0F1A", paddingHorizontal: 14, paddingVertical: 4,
    borderRadius: 12, borderWidth: 1, borderColor: "#334155",
  },
  vinInput: { flex: 1, color: "white", paddingVertical: 12, fontSize: 15, fontWeight: "600" },
  formCard: {
    backgroundColor: "#161E2E", padding: 20, borderRadius: 16,
    marginBottom: 20, borderWidth: 1, borderColor: "#262F3F", gap: 16,
  },
  row: { flexDirection: "row", gap: 14 },
  field: { flex: 1 },
  fullField: { width: "100%" },
  input: {
    backgroundColor: "#0B0F1A", color: "white", padding: 14,
    borderRadius: 12, borderWidth: 1, borderColor: "#334155", fontSize: 15,
  },
  notesInput: { height: 80, textAlignVertical: "top", paddingTop: 14 },
  selector: {
    backgroundColor: "#0B0F1A", padding: 14, borderRadius: 12,
    borderWidth: 1, borderColor: "#334155",
    flexDirection: "row", justifyContent: "space-between", alignItems: "center",
  },
  selectorText: { color: "white", fontSize: 15 },
  footer: {
    position: "absolute", bottom: 0, left: 0, right: 0,
    padding: 20, paddingBottom: 28, backgroundColor: "#0B0F1A",
    borderTopWidth: 1, borderTopColor: "#161E2E",
  },
  actionRow: { flexDirection: "row", gap: 12, alignItems: "center" },
  modalOverlay: { flex: 1, backgroundColor: "rgba(0,0,0,0.85)", justifyContent: "flex-end" },
  modalContent: {
    backgroundColor: "#161E2E", borderTopLeftRadius: 24, borderTopRightRadius: 24,
    padding: 24, borderWidth: 1, borderColor: "#262F3F",
  },
  modalHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 20 },
  modalTitle: { color: "white", fontSize: 18, fontWeight: "700" },
  optionItem: {
    paddingVertical: 16, borderBottomWidth: 1, borderBottomColor: "#262F3F",
    flexDirection: "row", justifyContent: "space-between", alignItems: "center",
  },
  optionText: { color: "#94A3B8", fontSize: 16, fontWeight: "500" },
});
