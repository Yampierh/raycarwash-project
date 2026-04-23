import { Ionicons } from "@expo/vector-icons";
import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useAppNavigation } from "../hooks/useAppNavigation";
import { useLocation } from "../hooks/useLocation";
import { apiClient } from "../services/api";
import { Colors } from "../theme/colors";

interface FareEstimate {
  fare_token: string;
  base_price_cents: number;
  surge_multiplier: number;
  estimated_price_cents: number;
  nearby_detailers_count: number;
  expires_at: string;
}

const formatCents = (cents: number) => `$${(cents / 100).toFixed(2)}`;

export default function FareEstimateScreen() {
  const navigation = useAppNavigation();
  const { lat, lng } = useLocation();

  const [loading, setLoading] = useState(true);
  const [fare, setFare] = useState<FareEstimate | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [serviceId, setServiceId] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const { data: services } = await apiClient.get("/services");
        const first = services?.[0];
        if (!first) { setError("No services available."); return; }
        setServiceId(first.id);

        const { data } = await apiClient.post<FareEstimate>("/fares/estimate", {
          service_id: first.id,
          vehicle_sizes: ["medium"],
          client_lat: lat ?? 25.6866,
          client_lng: lng ?? -100.3161,
        });
        setFare(data);
      } catch {
        setError("Could not load fare estimate.");
      } finally {
        setLoading(false);
      }
    })();
  }, [lat, lng]);

  const handleConfirm = () => {
    if (!fare) return;
    navigation.navigate("ConfirmBooking", { fare_token: fare.fare_token });
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <ActivityIndicator size="large" color={Colors.primary} />
        <Text style={styles.loadingText}>Estimating fare…</Text>
      </SafeAreaView>
    );
  }

  if (error || !fare) {
    return (
      <SafeAreaView style={styles.container}>
        <Text style={styles.errorText}>{error ?? "Unknown error"}</Text>
        <TouchableOpacity style={styles.btn} onPress={() => navigation.goBack()}>
          <Text style={styles.btnText}>Go Back</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  const hasSurge = Number(fare.surge_multiplier) > 1.0;

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Ionicons name="arrow-back" size={24} color="#F8FAFC" />
        </TouchableOpacity>
        <Text style={styles.title}>Fare Estimate</Text>
        <View style={{ width: 24 }} />
      </View>

      <View style={styles.card}>
        <Text style={styles.priceLabel}>Estimated Total</Text>
        <Text style={styles.price}>{formatCents(fare.estimated_price_cents)}</Text>
        <Text style={styles.basePrice}>Base: {formatCents(fare.base_price_cents)}</Text>

        {hasSurge && (
          <View style={styles.surgeBadge}>
            <Ionicons name="flash" size={14} color="#1E293B" />
            <Text style={styles.surgeText}>
              Surge ×{Number(fare.surge_multiplier).toFixed(1)}
            </Text>
          </View>
        )}

        <View style={styles.detailRow}>
          <Ionicons name="people-outline" size={16} color="#94A3B8" />
          <Text style={styles.detailText}>
            {fare.nearby_detailers_count} detailer{fare.nearby_detailers_count !== 1 ? "s" : ""} nearby
          </Text>
        </View>

        <Text style={styles.expiry}>
          Expires: {new Date(fare.expires_at).toLocaleTimeString()}
        </Text>
      </View>

      <TouchableOpacity style={styles.confirmBtn} onPress={handleConfirm}>
        <Text style={styles.confirmBtnText}>Confirm Estimate</Text>
        <Ionicons name="arrow-forward" size={20} color="#0B0F19" />
      </TouchableOpacity>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0B0F19", padding: 20 },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 32 },
  title: { color: "#F8FAFC", fontSize: 18, fontWeight: "700" },
  card: { backgroundColor: "#1E293B", borderRadius: 16, padding: 24, alignItems: "center", gap: 12 },
  priceLabel: { color: "#94A3B8", fontSize: 14 },
  price: { color: "#F8FAFC", fontSize: 48, fontWeight: "800" },
  basePrice: { color: "#64748B", fontSize: 14 },
  surgeBadge: {
    flexDirection: "row", alignItems: "center", gap: 4,
    backgroundColor: "#F59E0B", borderRadius: 20, paddingHorizontal: 12, paddingVertical: 4,
  },
  surgeText: { color: "#1E293B", fontWeight: "700", fontSize: 13 },
  detailRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  detailText: { color: "#94A3B8", fontSize: 13 },
  expiry: { color: "#475569", fontSize: 12, marginTop: 4 },
  confirmBtn: {
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8,
    backgroundColor: Colors.primary, borderRadius: 14, padding: 18, marginTop: 32,
  },
  confirmBtnText: { color: "#0B0F19", fontWeight: "800", fontSize: 16 },
  loadingText: { color: "#94A3B8", marginTop: 16, textAlign: "center" },
  errorText: { color: "#EF4444", textAlign: "center", marginBottom: 20 },
  btn: { backgroundColor: "#1E293B", borderRadius: 12, padding: 14, alignItems: "center" },
  btnText: { color: "#F8FAFC", fontWeight: "600" },
});
