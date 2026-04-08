import { Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import React, { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { createAppointment } from "../services/appointment.service";
import { Colors } from "../theme/colors";
import { getServicePrice } from "../utils/pricing";

export default function BookingSummaryScreen({ route, navigation }: any) {
  const {
    selections = {},
    selectedVehicles = [],
    total = 0,
    detailerId = "",
    detailerName = "Your Detailer",
    scheduledTime = "",
    serviceAddress = "",
    lat = 0,
    lng = 0,
    estimatedDuration = 0,
  } = route.params || {};

  const [loading, setLoading] = useState(false);

  const formattedDate = scheduledTime
    ? new Date(scheduledTime).toLocaleDateString("en-US", {
        weekday: "short",
        month: "short",
        day: "numeric",
      })
    : "";

  const formattedTime = scheduledTime
    ? new Date(scheduledTime).toLocaleTimeString("en-US", {
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
      })
    : "";

  const handleConfirm = async () => {
    setLoading(true);
    try {
      // Sprint 5: single multi-vehicle appointment with addons
      const vehicles = selectedVehicles
        .filter((v: any) => selections[v.id]?.base)
        .map((v: any) => {
          const sel = selections[v.id];
          return {
            vehicle_id: v.id,
            service_id: sel.base.id,
            addon_ids: (sel.addons ?? []).map((a: any) => a.id),
          };
        });

      await createAppointment({
        detailer_id: detailerId,
        scheduled_time: scheduledTime,
        service_address: serviceAddress,
        service_latitude: lat,
        service_longitude: lng,
        vehicles,
      });

      Alert.alert(
        "Booking Confirmed!",
        `Your appointment with ${detailerName} has been scheduled.`,
        [
          {
            text: "Go Home",
            onPress: () =>
              navigation.reset({ index: 0, routes: [{ name: "Main" }] }),
          },
        ],
      );
    } catch (error: any) {
      const detail = error.response?.data?.detail;
      Alert.alert(
        "Booking Failed",
        typeof detail === "string" ? detail : "Please try again.",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          style={styles.backBtn}
        >
          <Ionicons name="chevron-back" size={24} color="white" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Review Booking</Text>
        <View style={{ width: 44 }} />
      </View>

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scroll}
      >
        {/* Ticket de cita */}
        <View style={styles.appointmentTicket}>
          <View style={styles.ticketLeft}>
            <Text style={styles.ticketLabel}>APPOINTMENT</Text>
            <Text style={styles.ticketDate}>{formattedDate}</Text>
            <Text style={styles.ticketTime}>{formattedTime}</Text>
            <View style={styles.ticketDetailerRow}>
              <Ionicons name="person-circle-outline" size={14} color="#0F172A" />
              <Text style={styles.ticketDetailerName}>{detailerName}</Text>
            </View>
            {estimatedDuration > 0 && (
              <View style={styles.ticketDetailerRow}>
                <Ionicons name="time-outline" size={14} color="#0F172A" />
                <Text style={styles.ticketDetailerName}>
                  ~{estimatedDuration} min
                </Text>
              </View>
            )}
          </View>
          <View style={styles.ticketDivider} />
          <View style={styles.ticketRight}>
            <MaterialCommunityIcons
              name="calendar-check"
              size={32}
              color="#0F172A"
            />
          </View>
        </View>

        {serviceAddress !== "" && (
          <View style={styles.addressRow}>
            <Ionicons name="location-outline" size={14} color="#64748B" />
            <Text style={styles.addressText}>{serviceAddress}</Text>
          </View>
        )}

        <Text style={styles.sectionLabel}>VEHICLES & SERVICES</Text>

        {selectedVehicles.map((vehicle: any) => {
          const sel = selections[vehicle.id];
          const basePrice = getServicePrice(vehicle, sel?.base);
          const addonsTotal =
            sel?.addons?.reduce(
              (s: number, a: any) => s + (a.price ?? 0) / 100,
              0,
            ) ?? 0;
          const subtotal = basePrice + addonsTotal;

          return (
            <View key={vehicle.id} style={styles.detailCard}>
              <View style={styles.carHeader}>
                <View style={styles.carIconBox}>
                  <MaterialCommunityIcons
                    name="car-side"
                    size={24}
                    color="white"
                  />
                </View>
                <View>
                  <Text style={styles.carName}>
                    {vehicle.make} {vehicle.model}
                  </Text>
                  <Text style={styles.carPlate}>
                    {vehicle.license_plate} · {vehicle.color}
                  </Text>
                </View>
              </View>

              <View style={styles.servicesContainer}>
                <View style={styles.serviceItem}>
                  <View style={styles.dotLine}>
                    <View style={styles.dot} />
                    <View style={styles.line} />
                  </View>
                  <View style={styles.serviceTextContent}>
                    <Text style={styles.serviceMainTitle}>
                      {sel?.base?.name}
                    </Text>
                    <Text style={styles.servicePrice}>
                      ${basePrice.toFixed(2)}
                    </Text>
                  </View>
                </View>

                {sel?.addons?.map((addon: any, index: number) => (
                  <View key={addon.id} style={styles.serviceItem}>
                    <View style={styles.dotLine}>
                      <View
                        style={[styles.dot, { backgroundColor: "#475569" }]}
                      />
                      {index !== sel.addons.length - 1 && (
                        <View style={styles.line} />
                      )}
                    </View>
                    <View style={styles.serviceTextContent}>
                      <Text style={styles.addonTitle}>{addon.name}</Text>
                      <Text style={styles.addonPrice}>
                        +${((addon.price ?? 0) / 100).toFixed(2)}
                      </Text>
                    </View>
                  </View>
                ))}
              </View>

              <View style={styles.cardSubtotal}>
                <Text style={styles.subtotalLabel}>Vehicle Subtotal</Text>
                <Text style={styles.subtotalValue}>${subtotal.toFixed(2)}</Text>
              </View>
            </View>
          );
        })}

        <View style={styles.totalBox}>
          <View style={styles.totalRow}>
            <Text style={styles.totalText}>Total Amount</Text>
            <Text style={styles.totalAmount}>${total.toFixed(2)}</Text>
          </View>
          <Text style={styles.taxNote}>
            * Final price depends on vehicle condition
          </Text>
        </View>
      </ScrollView>

      <View style={styles.footer}>
        <TouchableOpacity disabled={loading} onPress={handleConfirm}>
          <LinearGradient
            colors={[Colors.primary, "#60A5FA"]}
            style={styles.confirmBtn}
          >
            {loading ? (
              <ActivityIndicator color="#0F172A" />
            ) : (
              <Text style={styles.confirmBtnText}>CONFIRM BOOKING</Text>
            )}
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
    padding: 20,
  },
  backBtn: {
    backgroundColor: "#161E2E",
    padding: 10,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#262F3F",
  },
  headerTitle: { color: "white", fontSize: 18, fontWeight: "800" },
  scroll: { padding: 20, paddingBottom: 120 },

  appointmentTicket: {
    backgroundColor: Colors.primary,
    borderRadius: 20,
    flexDirection: "row",
    marginBottom: 16,
    overflow: "hidden",
  },
  ticketLeft: { flex: 1, padding: 20 },
  ticketLabel: {
    color: "#0F172A",
    fontSize: 10,
    fontWeight: "900",
    letterSpacing: 1,
  },
  ticketDate: {
    color: "#0F172A",
    fontSize: 20,
    fontWeight: "900",
    marginTop: 5,
  },
  ticketTime: { color: "#0F172A", fontSize: 14, fontWeight: "600" },
  ticketDetailerRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    marginTop: 6,
  },
  ticketDetailerName: {
    color: "#0F172A",
    fontSize: 12,
    fontWeight: "700",
  },
  ticketDivider: {
    width: 1,
    backgroundColor: "rgba(15, 23, 42, 0.1)",
    marginVertical: 15,
  },
  ticketRight: {
    padding: 20,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "rgba(255,255,255,0.1)",
  },
  addressRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginBottom: 20,
  },
  addressText: { color: "#64748B", fontSize: 12 },

  sectionLabel: {
    color: "#64748B",
    fontSize: 12,
    fontWeight: "900",
    letterSpacing: 1.5,
    marginBottom: 15,
  },
  detailCard: {
    backgroundColor: "#161E2E",
    borderRadius: 24,
    padding: 20,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: "#262F3F",
  },
  carHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    marginBottom: 20,
  },
  carIconBox: {
    width: 48,
    height: 48,
    borderRadius: 16,
    backgroundColor: "#0B0F1A",
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#262F3F",
  },
  carName: { color: "white", fontSize: 18, fontWeight: "800" },
  carPlate: { color: "#64748B", fontSize: 12, fontWeight: "600" },
  servicesContainer: { paddingLeft: 10 },
  serviceItem: { flexDirection: "row", gap: 15 },
  dotLine: { alignItems: "center", width: 20 },
  dot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: Colors.primary,
    marginTop: 6,
  },
  line: { width: 2, flex: 1, backgroundColor: "#262F3F", marginVertical: 4 },
  serviceTextContent: {
    flex: 1,
    flexDirection: "row",
    justifyContent: "space-between",
    paddingBottom: 15,
  },
  serviceMainTitle: { color: "white", fontWeight: "700", fontSize: 15 },
  servicePrice: { color: "white", fontWeight: "700" },
  addonTitle: { color: "#94A3B8", fontSize: 14 },
  addonPrice: { color: "#94A3B8", fontSize: 14 },
  cardSubtotal: {
    borderTopWidth: 1,
    borderTopColor: "#262F3F",
    paddingTop: 15,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  subtotalLabel: { color: "#64748B", fontSize: 12, fontWeight: "700" },
  subtotalValue: { color: "white", fontSize: 16, fontWeight: "800" },

  totalBox: {
    marginTop: 10,
    padding: 20,
    borderRadius: 20,
    backgroundColor: "#111827",
    borderStyle: "dashed",
    borderWidth: 1,
    borderColor: "#374151",
  },
  totalRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  totalText: { color: "white", fontSize: 16, fontWeight: "600" },
  totalAmount: { color: "white", fontSize: 32, fontWeight: "900" },
  taxNote: {
    color: "#4B5563",
    fontSize: 11,
    textAlign: "center",
    marginTop: 10,
  },

  footer: {
    position: "absolute",
    bottom: 0,
    width: "100%",
    padding: 25,
    backgroundColor: "#0B0F1A",
  },
  confirmBtn: { padding: 20, borderRadius: 20, alignItems: "center" },
  confirmBtnText: {
    color: "#0F172A",
    fontWeight: "900",
    fontSize: 16,
    letterSpacing: 1,
  },
});
