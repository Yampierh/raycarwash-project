import { Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Dimensions,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Button from "../components/Button";
import SectionHeader from "../components/SectionHeader";
import { Addon, getAddons } from "../services/addon.service";
import { getServices } from "../services/service.service";
import { Colors } from "../theme/colors";
import { getServicePrice as getVehiclePrice } from "../utils/pricing";

const { width } = Dimensions.get("window");

export default function BookingScreen({ route, navigation }: any) {
  const { selectedVehicles } = route.params || { selectedVehicles: [] };
  const [services, setServices] = useState<any[]>([]);
  const [addons, setAddons] = useState<Addon[]>([]);
  const [loading, setLoading] = useState(true);
  const [selections, setSelections] = useState<Record<string, any>>({});

  useEffect(() => { fetchCatalog(); }, []);

  const fetchCatalog = async () => {
    try {
      const [servicesData, addonsData] = await Promise.all([getServices(), getAddons()]);
      setServices(servicesData);
      setAddons(addonsData);
    } catch {
      Alert.alert("Error", "Could not load services catalog.");
    } finally {
      setLoading(false);
    }
  };

  const handleSelectBase = (vehicleId: string, service: any) => {
    setSelections((prev) => ({ ...prev, [vehicleId]: { base: service, addons: prev[vehicleId]?.addons || [] } }));
  };

  const toggleAddon = (vehicleId: string, addon: any) => {
    const currentSelection = selections[vehicleId];
    if (!currentSelection?.base) {
      Alert.alert("Select a Service First", "Please select a main service for this vehicle before adding extras.");
      return;
    }
    const alreadyHasIt = currentSelection.addons.some((a: any) => a.id === addon.id);
    const updatedAddons = alreadyHasIt
      ? currentSelection.addons.filter((a: any) => a.id !== addon.id)
      : [...currentSelection.addons, addon];
    setSelections((prev) => ({ ...prev, [vehicleId]: { ...currentSelection, addons: updatedAddons } }));
  };

  const getAddonPrice = (addon: Addon) => addon.price_cents / 100;

  const calculateVehicleTotal = (vehicleId: string) => {
    const sel = selections[vehicleId];
    if (!sel) return 0;
    const vehicle = selectedVehicles.find((v: any) => v.id === vehicleId);
    const baseP = getVehiclePrice(vehicle, sel.base);
    const addonsP = sel.addons.reduce((sum: number, a: Addon) => sum + getAddonPrice(a), 0);
    return baseP + addonsP;
  };

  const globalTotal = selectedVehicles.reduce((acc: number, v: any) => acc + calculateVehicleTotal(v.id), 0);
  const isReady = selectedVehicles.every((v: any) => selections[v.id]?.base);
  const mainServices = services.filter((s) => s.category !== undefined && s.category !== null);

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Ionicons name="chevron-back" size={24} color="white" />
        </TouchableOpacity>
        <View>
          <Text style={styles.headerTitle}>Services</Text>
          <Text style={styles.headerStep}>Step 2 of 4</Text>
        </View>
        <View style={{ width: 44 }} />
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scroll}>
        {loading ? (
          <ActivityIndicator color={Colors.primary} size="large" style={{ marginTop: 50 }} />
        ) : (
          selectedVehicles.map((vehicle: any) => {
            const hasBaseSelected = !!selections[vehicle.id]?.base;
            return (
              <View key={vehicle.id} style={styles.vehicleSection}>
                <View style={styles.vehicleHeader}>
                  <MaterialCommunityIcons name="car-wash" size={18} color={Colors.primary} />
                  <Text style={styles.vehicleHeaderText}>{vehicle.make} {vehicle.model}</Text>
                </View>

                <SectionHeader title="SELECT A SERVICE" style={styles.labelHeader} />
                <View style={styles.mainGrid}>
                  {mainServices.map((s) => {
                    const isSelected = selections[vehicle.id]?.base?.id === s.id;
                    return (
                      <TouchableOpacity
                        key={s.id}
                        onPress={() => handleSelectBase(vehicle.id, s)}
                        style={[styles.mainCard, isSelected && styles.mainCardActive]}
                      >
                        <View style={styles.mainCardTop}>
                          <Text style={styles.mainCardName}>{s.name}</Text>
                          <Text style={[styles.mainCardPrice, isSelected && { color: "white" }]}>
                            ${getVehiclePrice(vehicle, s).toFixed(0)}
                          </Text>
                        </View>
                        <Text style={styles.mainCardDesc} numberOfLines={2}>{s.description}</Text>
                      </TouchableOpacity>
                    );
                  })}
                </View>

                {hasBaseSelected && addons.length > 0 && (
                  <View style={styles.addonWrapper}>
                    <SectionHeader title="ADD-ONS" style={styles.labelHeader} />
                    <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                      {addons.map((addon) => {
                        const isSelected = selections[vehicle.id]?.addons.some((a: Addon) => a.id === addon.id);
                        return (
                          <TouchableOpacity
                            key={addon.id}
                            onPress={() => toggleAddon(vehicle.id, addon)}
                            style={[styles.addonChip, isSelected && styles.addonChipActive]}
                          >
                            <Ionicons
                              name={isSelected ? "checkmark-circle" : "add-circle-outline"}
                              size={16}
                              color={isSelected ? "#0B0F1A" : Colors.primary}
                            />
                            <Text style={[styles.addonChipText, isSelected && { color: "#0B0F1A" }]}>
                              {addon.name} (+${getAddonPrice(addon).toFixed(0)})
                            </Text>
                          </TouchableOpacity>
                        );
                      })}
                    </ScrollView>
                  </View>
                )}
                <View style={styles.divider} />
              </View>
            );
          })
        )}
      </ScrollView>

      <View style={styles.footer}>
        <View style={styles.footerInfo}>
          <Text style={styles.totalLabel}>ESTIMATED TOTAL</Text>
          <Text style={styles.totalValue}>${globalTotal.toFixed(2)}</Text>
        </View>
        <Button
          title={isReady ? "CONTINUE" : "SELECT A SERVICE"}
          onPress={() => navigation.navigate("Schedule", { selections, total: globalTotal, selectedVehicles })}
          variant="cta"
          size="lg"
          fullWidth
          disabled={!isReady}
          iconRight="chevron-forward"
        />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0B0F1A" },
  header: {
    flexDirection: "row", alignItems: "center",
    justifyContent: "space-between", padding: 20,
  },
  backBtn: {
    backgroundColor: "#161E2E", padding: 10,
    borderRadius: 12, borderWidth: 1, borderColor: "#262F3F",
  },
  headerTitle: { color: "white", fontSize: 20, fontWeight: "800", textAlign: "center" },
  headerStep: { color: Colors.primary, fontSize: 12, fontWeight: "600", textAlign: "center" },
  scroll: { paddingHorizontal: 20, paddingBottom: 150 },
  vehicleSection: { marginBottom: 20 },
  vehicleHeader: {
    flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 16,
    backgroundColor: "#1E293B", alignSelf: "flex-start",
    paddingHorizontal: 12, paddingVertical: 6, borderRadius: 8,
  },
  vehicleHeaderText: { color: "white", fontWeight: "700", fontSize: 13 },
  labelHeader: { paddingHorizontal: 0, marginBottom: 10 },
  mainGrid: { gap: 10 },
  mainCard: {
    backgroundColor: "#161E2E", borderRadius: 16, padding: 16,
    borderWidth: 1, borderColor: "#262F3F",
  },
  mainCardActive: { borderColor: Colors.primary, backgroundColor: "#1A2436" },
  mainCardTop: { flexDirection: "row", justifyContent: "space-between", marginBottom: 6 },
  mainCardName: { color: "white", fontWeight: "700", fontSize: 16 },
  mainCardPrice: { color: Colors.primary, fontWeight: "700", fontSize: 16 },
  mainCardDesc: { color: "#94A3B8", fontSize: 12 },
  addonWrapper: { marginTop: 14 },
  addonChip: {
    flexDirection: "row", alignItems: "center",
    backgroundColor: "#161E2E", paddingHorizontal: 14, paddingVertical: 10,
    borderRadius: 12, marginRight: 10, borderWidth: 1, borderColor: "#262F3F", gap: 6,
  },
  addonChipActive: { backgroundColor: Colors.primary, borderColor: Colors.primary },
  addonChipText: { color: "white", fontSize: 12, fontWeight: "600" },
  divider: { height: 1, backgroundColor: "#1E293B", marginTop: 24 },
  footer: {
    position: "absolute", bottom: 0, width: "100%",
    padding: 20, backgroundColor: "rgba(11, 15, 26, 0.98)",
    borderTopWidth: 1, borderTopColor: "#1E293B",
  },
  footerInfo: { marginBottom: 14 },
  totalLabel: { color: "#64748B", fontSize: 10, fontWeight: "700", letterSpacing: 1 },
  totalValue: { color: "white", fontSize: 28, fontWeight: "800" },
});
