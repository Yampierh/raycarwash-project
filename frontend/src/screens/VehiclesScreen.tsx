import { MaterialCommunityIcons } from "@expo/vector-icons";
import { useIsFocused } from "@react-navigation/native";
import { LinearGradient } from "expo-linear-gradient";
import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Button from "../components/Button";
import EmptyState from "../components/EmptyState";
import { getMyVehicles, Vehicle } from "../services/vehicle.service";
import { Colors } from "../theme/colors";

const COLOR_MAP: Record<string, string> = {
  white: "#F1F5F9", black: "#1E293B", silver: "#94A3B8", gray: "#64748B",
  grey: "#64748B", red: "#EF4444", blue: "#3B82F6", navy: "#1E40AF",
  green: "#10B981", yellow: "#EAB308", orange: "#F97316", brown: "#78350F",
  gold: "#D97706", charcoal: "#374151", pearl: "#BAE6FD",
};

function getCarIcon(bodyClass = "") {
  const bc = bodyClass.toLowerCase();
  if (bc.includes("suv") || bc.includes("crossover")) return "car-estate";
  if (bc.includes("pickup") || bc.includes("truck")) return "car-pickup";
  if (bc.includes("van")) return "van-utility";
  if (bc.includes("hatch")) return "car-hatchback";
  if (bc.includes("coupe") || bc.includes("sport")) return "car-sports";
  return "car-side";
}

function getColorDot(color = "") {
  return COLOR_MAP[color.toLowerCase()] ?? "#475569";
}

export default function MyVehiclesScreen({ navigation }: any) {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [loading, setLoading] = useState(true);
  const isFocused = useIsFocused();

  useEffect(() => {
    if (isFocused) loadVehicles();
  }, [isFocused]);

  const loadVehicles = async () => {
    setLoading(true);
    try {
      const data = await getMyVehicles();
      setVehicles(data);
    } catch {
      Alert.alert("Error", "Could not load your vehicles. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const renderVehicleCard = ({ item }: { item: any }) => {
    const colorHex = getColorDot(item.color);
    const needsBorder = item.color?.toLowerCase() === "white";
    return (
      <TouchableOpacity
        style={styles.card}
        onPress={() => (navigation as any).navigate("VehicleDetail", { vehicle: item })}
        activeOpacity={0.85}
      >
        <LinearGradient colors={[`${colorHex}15`, "transparent"]} style={StyleSheet.absoluteFill} />

        <View style={styles.cardHeader}>
          <View>
            <Text style={styles.carName}>{item.year} {item.make} {item.model}</Text>
            <Text style={styles.plateText}>{item.license_plate}</Text>
          </View>
          <View style={styles.bodyBadge}>
            <Text style={styles.bodyBadgeText}>{(item.body_class || "SEDAN").toUpperCase()}</Text>
          </View>
        </View>

        <View style={styles.visualContainer}>
          <MaterialCommunityIcons
            name={getCarIcon(item.body_class) as any}
            size={72}
            color={colorHex}
            style={{ opacity: 0.85 }}
          />
        </View>

        <View style={styles.cardFooter}>
          <View style={styles.infoRow}>
            <View style={[styles.colorDot, { backgroundColor: colorHex, borderWidth: needsBorder ? 1 : 0, borderColor: "#334155" }]} />
            <Text style={styles.infoPillText}>{item.color}</Text>
          </View>
          <Button
            title="BOOK NOW"
            onPress={() => navigation.navigate("Booking", { selectedVehicles: [item] })}
            variant="primary"
            size="sm"
            iconRight="chevron-forward"
          />
        </View>
      </TouchableOpacity>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.topBar}>
        <View style={{ width: 40 }} />
        <Text style={styles.headerTitle}>My Garage</Text>
        <TouchableOpacity
          style={styles.addBtn}
          onPress={() => navigation.navigate("AddVehicle")}
        >
          <MaterialCommunityIcons name="plus" size={22} color="#0F172A" />
        </TouchableOpacity>
      </View>

      {loading ? (
        <ActivityIndicator color={Colors.primary} size="large" style={{ marginTop: 60 }} />
      ) : (
        <FlatList
          data={vehicles}
          renderItem={renderVehicleCard}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.listContent}
          ListEmptyComponent={
            <EmptyState
              icon="car-off"
              title="Your garage is empty"
              subtitle="Add your first vehicle to get started"
              action={{ label: "Add My First Vehicle", onPress: () => navigation.navigate("AddVehicle") }}
              dashed={false}
              style={{ marginTop: 40 }}
            />
          }
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0B0F1A" },
  topBar: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingVertical: 16,
  },
  headerTitle: { color: "white", fontSize: 22, fontWeight: "800" },
  addBtn: {
    backgroundColor: Colors.primary,
    padding: 8,
    borderRadius: 12,
  },
  listContent: { paddingHorizontal: 20, paddingBottom: 120 },
  card: {
    backgroundColor: "#161E2E",
    borderRadius: 20,
    padding: 20,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: "#262F3F",
    overflow: "hidden",
  },
  cardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 4,
  },
  carName: { color: "white", fontSize: 18, fontWeight: "800" },
  plateText: { color: Colors.primary, fontSize: 13, fontWeight: "600", marginTop: 3 },
  bodyBadge: {
    backgroundColor: "#1E293B",
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 8,
  },
  bodyBadgeText: { color: "#94A3B8", fontSize: 10, fontWeight: "700" },
  visualContainer: { height: 100, justifyContent: "center", alignItems: "center", marginVertical: 4 },
  cardFooter: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 8,
  },
  infoRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  colorDot: { width: 12, height: 12, borderRadius: 6 },
  infoPillText: { color: "#94A3B8", fontSize: 13 },
});
