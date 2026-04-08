import { Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Dimensions,
  FlatList,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { getMyVehicles } from "../services/vehicle.service";
import { Colors } from "../theme/colors";

const { width } = Dimensions.get("window");

export default function SelectVehiclesScreen({ navigation }: any) {
  const [vehicles, setVehicles] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  useEffect(() => {
    fetchVehicles();
  }, []);

  const fetchVehicles = async () => {
    try {
      const data = await getMyVehicles();
      setVehicles(data);
    } catch {
      Alert.alert("Error", "Could not load your vehicles. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const toggleVehicle = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id],
    );
  };

  const handleNext = () => {
    const selectedVehicles = vehicles.filter((v) => selectedIds.includes(v.id));
    navigation.navigate("Booking", { selectedVehicles });
  };

  const renderItem = ({ item }: any) => {
    const isSelected = selectedIds.includes(item.id);
    return (
      <TouchableOpacity
        activeOpacity={0.8}
        style={[styles.card, isSelected && styles.cardSelected]}
        onPress={() => toggleVehicle(item.id)}
      >
        <View style={styles.cardContent}>
          <View style={[styles.iconContainer, isSelected && styles.iconActive]}>
            <MaterialCommunityIcons
              name="car-info"
              size={28}
              color={isSelected ? "#0B0F1A" : Colors.primary}
            />
          </View>

          <View style={{ flex: 1 }}>
            <Text style={styles.vTitle}>
              {item.make} {item.model}
            </Text>
            <View style={styles.plateBadge}>
              <Text style={styles.vPlate}>{item.license_plate}</Text>
            </View>
          </View>

          <View style={[styles.radio, isSelected && styles.radioActive]}>
            {isSelected && (
              <Ionicons name="checkmark-sharp" size={16} color="#0B0F1A" />
            )}
          </View>
        </View>
      </TouchableOpacity>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          style={styles.backBtn}
        >
          <Ionicons name="close" size={24} color="white" />
        </TouchableOpacity>
        <View>
          <Text style={styles.headerTitle}>Your Garage</Text>
          <Text style={styles.headerStep}>Step 1 of 4</Text>
        </View>
        <TouchableOpacity
          style={styles.addBtn}
          onPress={() => navigation.navigate("AddVehicle")}
        >
          <Ionicons name="add" size={24} color={Colors.primary} />
        </TouchableOpacity>
      </View>

      <View style={{ flex: 1, paddingHorizontal: 20 }}>
        <View style={styles.introBox}>
          <Text style={styles.title}>Select Vehicles</Text>
          <Text style={styles.subtitle}>
            Which cars are we detailing today?
          </Text>
        </View>

        {loading ? (
          <ActivityIndicator
            color={Colors.primary}
            size="large"
            style={{ marginTop: 50 }}
          />
        ) : (
          <FlatList
            data={vehicles}
            renderItem={renderItem}
            keyExtractor={(item) => item.id}
            showsVerticalScrollIndicator={false}
            contentContainerStyle={{ paddingBottom: 120 }}
            ListEmptyComponent={
              <View style={{ alignItems: "center", marginTop: 40 }}>
                <Text style={styles.emptyText}>No vehicles in your garage.</Text>
                <Text style={[styles.emptyText, { fontSize: 13, marginTop: 8 }]}>
                  Tap + above to add your first vehicle.
                </Text>
              </View>
            }
          />
        )}
      </View>

      <View style={styles.footer}>
        <TouchableOpacity
          disabled={selectedIds.length === 0}
          onPress={handleNext}
          style={selectedIds.length === 0 && { opacity: 0.5 }}
        >
          <LinearGradient
            colors={
              selectedIds.length > 0
                ? [Colors.primary, "#60A5FA"]
                : ["#1E293B", "#1E293B"]
            }
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={styles.btn}
          >
            <Text style={styles.btnText}>
              {selectedIds.length > 0
                ? `CONTINUE WITH ${selectedIds.length} ${selectedIds.length === 1 ? "CAR" : "CARS"}`
                : "SELECT A VEHICLE"}
            </Text>
            <Ionicons name="arrow-forward" size={20} color="#0B0F1A" />
          </LinearGradient>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0B0F1A" },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingVertical: 15,
  },
  backBtn: {
    backgroundColor: "#161E2E",
    padding: 10,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#262F3F",
  },
  addBtn: {
    backgroundColor: "#161E2E",
    padding: 10,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#262F3F",
  },
  headerTitle: {
    color: "white",
    fontSize: 18,
    fontWeight: "800",
    textAlign: "center",
  },
  headerStep: {
    color: Colors.primary,
    fontSize: 11,
    fontWeight: "600",
    textAlign: "center",
  },
  introBox: { marginVertical: 25 },
  title: { color: "white", fontSize: 28, fontWeight: "900" },
  subtitle: { color: "#64748B", fontSize: 15, marginTop: 5, fontWeight: "500" },
  card: {
    backgroundColor: "#161E2E",
    padding: 20,
    borderRadius: 22,
    marginBottom: 15,
    borderWidth: 1.5,
    borderColor: "#262F3F",
  },
  cardSelected: { borderColor: Colors.primary, backgroundColor: "#1A2436" },
  cardContent: { flexDirection: "row", alignItems: "center", gap: 18 },
  iconContainer: {
    width: 55,
    height: 55,
    borderRadius: 18,
    backgroundColor: "#0B0F1A",
    justifyContent: "center",
    alignItems: "center",
  },
  iconActive: { backgroundColor: Colors.primary },
  vTitle: { color: "white", fontWeight: "800", fontSize: 18, marginBottom: 4 },
  plateBadge: {
    backgroundColor: "#262F3F",
    alignSelf: "flex-start",
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
  },
  vPlate: {
    color: "#94A3B8",
    fontSize: 12,
    fontWeight: "bold",
    letterSpacing: 1,
  },
  radio: {
    width: 28,
    height: 28,
    borderRadius: 14,
    borderWidth: 2,
    borderColor: "#334155",
    justifyContent: "center",
    alignItems: "center",
  },
  radioActive: { backgroundColor: Colors.primary, borderColor: Colors.primary },
  emptyText: {
    color: "#475569",
    textAlign: "center",
    marginTop: 40,
    fontSize: 16,
  },
  footer: {
    position: "absolute",
    bottom: 0,
    width: "100%",
    padding: 25,
    backgroundColor: "rgba(11, 15, 26, 0.98)",
    borderTopWidth: 1,
    borderTopColor: "#161E2E",
  },
  btn: {
    padding: 20,
    borderRadius: 20,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: 12,
  },
  btnText: {
    fontWeight: "900",
    color: "#0F172A",
    fontSize: 16,
    letterSpacing: 0.5,
  },
});
