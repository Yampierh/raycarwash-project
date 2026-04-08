import { Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
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
import { getMyVehicles, Vehicle } from "../services/vehicle.service";
import { Colors } from "../theme/colors";

const COLOR_MAP: Record<string, string> = {
  white: "#F1F5F9",
  black: "#1E293B",
  silver: "#94A3B8",
  gray: "#64748B",
  grey: "#64748B",
  red: "#EF4444",
  blue: "#3B82F6",
  navy: "#1E40AF",
  green: "#10B981",
  yellow: "#EAB308",
  orange: "#F97316",
  brown: "#78350F",
  gold: "#D97706",
  charcoal: "#374151",
  pearl: "#BAE6FD",
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
        onPress={() =>
          (navigation as any).navigate("VehicleDetail", { vehicle: item })
        }
        activeOpacity={0.85}
      >
        <LinearGradient
          colors={[`${colorHex}15`, "transparent"]}
          style={StyleSheet.absoluteFill}
        />

        <View style={styles.cardHeader}>
          <View>
            <Text style={styles.carName}>
              {item.year} {item.make} {item.model}
            </Text>
            <Text style={styles.plateText}>{item.license_plate}</Text>
          </View>
          <View style={styles.bodyBadge}>
            <Text style={styles.bodyBadgeText}>
              {(item.body_class || "SEDAN").toUpperCase()}
            </Text>
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
            <View
              style={[
                styles.colorDot,
                {
                  backgroundColor: colorHex,
                  borderWidth: needsBorder ? 1 : 0,
                  borderColor: "#334155",
                },
              ]}
            />
            <Text style={styles.infoPillText}>{item.color}</Text>
          </View>
          <TouchableOpacity
            style={styles.actionBtn}
            onPress={() =>
              navigation.navigate("Booking", { selectedVehicles: [item] })
            }
          >
            <Text style={styles.actionBtnText}>BOOK NOW</Text>
            <Ionicons name="chevron-forward" size={16} color="#0F172A" />
          </TouchableOpacity>
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
          <Ionicons name="add" size={24} color="#0F172A" />
        </TouchableOpacity>
      </View>

      {loading ? (
        <ActivityIndicator
          color={Colors.primary}
          size="large"
          style={{ marginTop: 60 }}
        />
      ) : (
        <FlatList
          data={vehicles}
          renderItem={renderVehicleCard}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.listContent}
          ListEmptyComponent={
            <View style={styles.emptyState}>
              <MaterialCommunityIcons
                name="car-off"
                size={80}
                color="#1E293B"
              />
              <Text style={styles.emptyTitle}>Your garage is empty</Text>
              <Text style={styles.emptySubtitle}>
                Add your first vehicle to get started
              </Text>
              <TouchableOpacity
                style={styles.emptyAddBtn}
                onPress={() => navigation.navigate("AddVehicle")}
              >
                <Text style={styles.emptyAddBtnText}>Add My First Vehicle</Text>
              </TouchableOpacity>
            </View>
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
  headerTitle: { color: "white", fontSize: 22, fontWeight: "bold" },
  addBtn: { backgroundColor: Colors.primary, padding: 8, borderRadius: 12 },
  listContent: { padding: 20, paddingBottom: 120 },
  card: {
    backgroundColor: "#161E2E",
    borderRadius: 24,
    padding: 20,
    marginBottom: 18,
    borderWidth: 1,
    borderColor: "#262F3F",
    overflow: "hidden",
  },
  cardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
  },
  carName: { color: "white", fontSize: 18, fontWeight: "bold" },
  plateText: {
    color: Colors.primary,
    fontSize: 13,
    fontWeight: "600",
    marginTop: 3,
  },
  bodyBadge: {
    backgroundColor: "#1E293B",
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 8,
  },
  bodyBadgeText: { color: "#94A3B8", fontSize: 10, fontWeight: "bold" },
  visualContainer: {
    height: 110,
    justifyContent: "center",
    alignItems: "center",
    marginVertical: 8,
  },
  cardFooter: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 8,
  },
  infoRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  colorDot: { width: 12, height: 12, borderRadius: 6 },
  infoPillText: { color: "#94A3B8", fontSize: 13 },
  actionBtn: {
    backgroundColor: Colors.primary,
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 12,
    gap: 5,
  },
  actionBtnText: { color: "#0F172A", fontWeight: "bold", fontSize: 12 },
  emptyState: { alignItems: "center", marginTop: 80, paddingHorizontal: 20 },
  emptyTitle: {
    color: "#94A3B8",
    fontSize: 20,
    fontWeight: "700",
    marginTop: 20,
  },
  emptySubtitle: {
    color: "#475569",
    fontSize: 14,
    marginTop: 8,
    marginBottom: 30,
  },
  emptyAddBtn: {
    backgroundColor: Colors.primary,
    padding: 18,
    borderRadius: 16,
    width: "100%",
    alignItems: "center",
  },
  emptyAddBtnText: { color: "#0F172A", fontWeight: "bold", fontSize: 15 },
});
