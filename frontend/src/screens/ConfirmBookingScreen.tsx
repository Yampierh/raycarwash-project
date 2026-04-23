import { Ionicons } from "@expo/vector-icons";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import React, { useState } from "react";
import {
  ActivityIndicator,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useAppNavigation } from "../hooks/useAppNavigation";
import { requestRide } from "../services/rides.service";
import { Colors } from "../theme/colors";
import type { RootStackParamList } from "../navigation/types";

type Props = NativeStackScreenProps<RootStackParamList, "ConfirmBooking">;

export default function ConfirmBookingScreen({ route }: Props) {
  const { fare_token } = route.params;
  const navigation = useAppNavigation();

  const [asap, setAsap] = useState(true);
  const [scheduledText, setScheduledText] = useState(""); // ISO or human-readable
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleBook = async () => {
    try {
      setError(null);
      setLoading(true);
      const ride = await requestRide(fare_token);
      navigation.navigate("Searching", { appointment_id: ride.appointment_id });
    } catch {
      setError("Booking failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Ionicons name="arrow-back" size={24} color="#F8FAFC" />
        </TouchableOpacity>
        <Text style={styles.title}>Confirm Booking</Text>
        <View style={{ width: 24 }} />
      </View>

      {/* ASAP / Scheduled toggle */}
      <View style={styles.toggleRow}>
        <TouchableOpacity
          style={[styles.toggleBtn, asap && styles.toggleActive]}
          onPress={() => setAsap(true)}
        >
          <Ionicons name="flash" size={16} color={asap ? "#0B0F19" : "#94A3B8"} />
          <Text style={[styles.toggleText, asap && styles.toggleTextActive]}>ASAP</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.toggleBtn, !asap && styles.toggleActive]}
          onPress={() => setAsap(false)}
        >
          <Ionicons name="calendar-outline" size={16} color={!asap ? "#0B0F19" : "#94A3B8"} />
          <Text style={[styles.toggleText, !asap && styles.toggleTextActive]}>Schedule</Text>
        </TouchableOpacity>
      </View>

      {!asap && (
        <View style={styles.dateCard}>
          <Ionicons name="time-outline" size={20} color={Colors.primary} />
          <TextInput
            style={styles.dateInput}
            placeholder="e.g. Tomorrow 10:00 AM"
            placeholderTextColor="#475569"
            value={scheduledText}
            onChangeText={setScheduledText}
          />
        </View>
      )}

      {error && <Text style={styles.error}>{error}</Text>}

      <View style={{ flex: 1 }} />

      <TouchableOpacity
        style={[styles.bookBtn, loading && styles.bookBtnDisabled]}
        onPress={handleBook}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color="#0B0F19" />
        ) : (
          <>
            <Text style={styles.bookBtnText}>
              {asap ? "Book Now — ASAP" : "Book for Selected Time"}
            </Text>
            <Ionicons name="checkmark-circle" size={20} color="#0B0F19" />
          </>
        )}
      </TouchableOpacity>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0B0F19", padding: 20 },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 32 },
  title: { color: "#F8FAFC", fontSize: 18, fontWeight: "700" },
  toggleRow: { flexDirection: "row", gap: 12, marginBottom: 24 },
  toggleBtn: {
    flex: 1, flexDirection: "row", alignItems: "center", justifyContent: "center",
    gap: 6, borderRadius: 12, padding: 14, backgroundColor: "#1E293B",
  },
  toggleActive: { backgroundColor: Colors.primary },
  toggleText: { color: "#94A3B8", fontWeight: "600", fontSize: 15 },
  toggleTextActive: { color: "#0B0F19" },
  dateCard: {
    flexDirection: "row", alignItems: "center", gap: 10,
    backgroundColor: "#1E293B", borderRadius: 12, padding: 16, marginBottom: 16,
  },
  dateInput: { flex: 1, color: "#F8FAFC", fontSize: 14 },
  error: { color: "#EF4444", textAlign: "center", marginBottom: 12 },
  bookBtn: {
    flexDirection: "row", alignItems: "center", justifyContent: "center",
    gap: 8, backgroundColor: Colors.primary, borderRadius: 14, padding: 18,
  },
  bookBtnDisabled: { opacity: 0.6 },
  bookBtnText: { color: "#0B0F19", fontWeight: "800", fontSize: 16 },
});
