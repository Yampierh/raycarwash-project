import { Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
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
import {
  MatchedDetailer,
  TimeSlotRead,
  getMatching,
} from "../services/detailer.service";
import { useLocation } from "../hooks/useLocation";
import { APP_CONFIG } from "../config/app.config";
import { Colors } from "../theme/colors";

const { width } = Dimensions.get("window");

/** Maps body_class → backend vehicle size bucket */
function getVehicleSize(bodyClass = ""): string {
  const b = bodyClass.toLowerCase();
  if (b.includes("sedan") || b.includes("coupe")) return "small";
  if (b.includes("suv") || b.includes("hatchback")) return "medium";
  if (b.includes("pickup") || b.includes("truck")) return "large";
  if (b.includes("van")) return "xl";
  return "medium";
}

export default function DetailerSelectionScreen({ route, navigation }: any) {
  const { selections, selectedVehicles, total, date } = route.params || {};

  const { lat, lng, city, region, zipcode, loading: locationLoading } = useLocation();

  const [matched, setMatched] = useState<MatchedDetailer[]>([]);
  const [loadingMatch, setLoadingMatch] = useState(true);

  const [selectedDetailer, setSelectedDetailer] = useState<MatchedDetailer | null>(null);
  const [selectedSlot, setSelectedSlot] = useState<TimeSlotRead | null>(null);

  // Derive service_id, vehicle_sizes, and addon_ids from selections
  const firstServiceId: string | undefined = Object.values(selections || {})[0]
    ? (Object.values(selections)[0] as any).base?.id
    : undefined;

  const vehicleSizes: string[] = (selectedVehicles ?? []).map((v: any) =>
    getVehicleSize(v.body_class),
  );

  const allAddonIds: string[] = Object.values(selections || {}).flatMap(
    (sel: any) => (sel.addons ?? []).map((a: any) => a.id),
  );
  const uniqueAddonIds = [...new Set(allAddonIds)];

  // Fallback to configured default city when GPS is unavailable
  const resolvedLat = lat ?? APP_CONFIG.fallbackCoords.lat;
  const resolvedLng = lng ?? APP_CONFIG.fallbackCoords.lng;
  const resolvedAddress = city
    ? `${city}, ${region}${zipcode ? ` ${zipcode}` : ""}`
    : APP_CONFIG.fallbackCoords.address;

  useEffect(() => {
    if (!locationLoading && firstServiceId) fetchMatching();
  }, [locationLoading]);

  const fetchMatching = async () => {
    try {
      const data = await getMatching({
        lat: resolvedLat,
        lng: resolvedLng,
        date: date ?? new Date().toISOString().split("T")[0],
        service_id: firstServiceId!,
        vehicle_sizes: vehicleSizes,
        addon_ids: uniqueAddonIds.length > 0 ? uniqueAddonIds : undefined,
      });
      setMatched(data);
    } catch {
      Alert.alert("Error", "Could not find matching detailers. Please try again.");
    } finally {
      setLoadingMatch(false);
    }
  };

  const handleSelectDetailer = (detailer: MatchedDetailer) => {
    setSelectedDetailer(detailer);
    setSelectedSlot(null);
  };

  const handleConfirm = () => {
    if (!selectedDetailer || !selectedSlot) return;

    navigation.navigate("BookingSummary", {
      selections,
      selectedVehicles,
      total: selectedDetailer.estimated_price / 100, // backend returns cents
      detailerId: selectedDetailer.user_id,
      detailerName: selectedDetailer.full_name,
      scheduledTime: selectedSlot.start_time,
      serviceAddress: resolvedAddress,
      lat: resolvedLat,
      lng: resolvedLng,
      estimatedDuration: selectedDetailer.estimated_duration,
    });
  };

  const formatTime = (isoString: string): string => {
    const d = new Date(isoString);
    return d.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
  };

  const renderStars = (rating: number | null) => {
    const stars = Math.round(rating ?? 0);
    return (
      <View style={styles.starsRow}>
        {[1, 2, 3, 4, 5].map((i) => (
          <Ionicons
            key={i}
            name={i <= stars ? "star" : "star-outline"}
            size={12}
            color="#F59E0B"
          />
        ))}
        {rating !== null && (
          <Text style={styles.ratingText}>{rating.toFixed(1)}</Text>
        )}
      </View>
    );
  };

  const availableSlots = selectedDetailer?.available_slots?.filter((s) => s.is_available) ?? [];

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          style={styles.backBtn}
        >
          <Ionicons name="chevron-back" size={24} color="white" />
        </TouchableOpacity>
        <View>
          <Text style={styles.headerTitle}>Choose Detailer</Text>
          <Text style={styles.headerStep}>Step 4 of 4</Text>
        </View>
        <View style={{ width: 40 }} />
      </View>

      {date && (
        <View style={styles.dateBanner}>
          <Ionicons name="calendar-outline" size={14} color={Colors.primary} />
          <Text style={styles.dateBannerText}>
            Showing availability for{" "}
            <Text style={{ color: "white" }}>{date}</Text>
          </Text>
        </View>
      )}

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scroll}
      >
        <View style={styles.sectionHeader}>
          <MaterialCommunityIcons
            name="account-search"
            size={18}
            color={Colors.primary}
          />
          <Text style={styles.sectionTitle}>MATCHED DETAILERS</Text>
        </View>

        {loadingMatch ? (
          <ActivityIndicator color={Colors.primary} style={{ marginTop: 30 }} />
        ) : matched.length === 0 ? (
          <View style={styles.emptyState}>
            <Text style={styles.emptyText}>
              No detailers available for your booking.
            </Text>
          </View>
        ) : (
          matched.map((detailer) => {
            const isSelected = selectedDetailer?.user_id === detailer.user_id;
            return (
              <TouchableOpacity
                key={detailer.user_id}
                style={[
                  styles.detailerCard,
                  isSelected && styles.detailerCardActive,
                ]}
                onPress={() => handleSelectDetailer(detailer)}
                activeOpacity={0.8}
              >
                <View style={styles.detailerAvatar}>
                  <MaterialCommunityIcons
                    name="account-circle"
                    size={44}
                    color={isSelected ? Colors.primary : "#475569"}
                  />
                </View>
                <View style={styles.detailerInfo}>
                  <Text style={styles.detailerName}>{detailer.full_name}</Text>
                  {renderStars(detailer.average_rating)}
                  <View style={styles.detailerMeta}>
                    {detailer.years_of_experience !== null && (
                      <Text style={styles.metaText}>
                        {detailer.years_of_experience} yrs exp
                      </Text>
                    )}
                    {detailer.distance_miles !== null && (
                      <Text style={styles.metaText}>
                        · {detailer.distance_miles.toFixed(1)} mi
                      </Text>
                    )}
                    <Text style={styles.metaText}>
                      · {detailer.total_reviews} reviews
                    </Text>
                  </View>
                  {/* Price + duration from smart matching */}
                  <View style={styles.priceDurationRow}>
                    <Text style={styles.matchPrice}>
                      ${(detailer.estimated_price / 100).toFixed(0)}
                    </Text>
                    <Text style={styles.matchDuration}>
                      · ~{detailer.estimated_duration} min
                    </Text>
                  </View>
                </View>
                {detailer.available_slots.length > 0 ? (
                  <View style={styles.availableBadge}>
                    <Text style={styles.availableBadgeText}>
                      {detailer.available_slots.filter((s) => s.is_available).length} slots
                    </Text>
                  </View>
                ) : (
                  <View style={styles.unavailableBadge}>
                    <Text style={styles.unavailableBadgeText}>Full</Text>
                  </View>
                )}
              </TouchableOpacity>
            );
          })
        )}

        {/* Time slots for the selected detailer (pre-loaded from matching) */}
        {selectedDetailer && (
          <View style={{ marginTop: 28 }}>
            <View style={styles.sectionHeader}>
              <Ionicons name="time-outline" size={18} color={Colors.primary} />
              <Text style={styles.sectionTitle}>
                SLOTS — {selectedDetailer.full_name.split(" ")[0].toUpperCase()}
              </Text>
            </View>

            {availableSlots.length === 0 ? (
              <View style={styles.noSlotsCard}>
                <Ionicons
                  name="calendar-clear-outline"
                  size={28}
                  color="#475569"
                />
                <Text style={styles.noSlotsText}>
                  No available slots
                  {date ? ` on ${date}` : " today"}.
                </Text>
                <Text style={styles.noSlotsHint}>
                  Try selecting a different date or detailer.
                </Text>
              </View>
            ) : (
              <View style={styles.slotsGrid}>
                {availableSlots.map((slot) => {
                  const isSlotSelected =
                    selectedSlot?.start_time === slot.start_time;
                  return (
                    <TouchableOpacity
                      key={slot.start_time}
                      style={[
                        styles.slotChip,
                        isSlotSelected && styles.slotChipSelected,
                      ]}
                      onPress={() => setSelectedSlot(slot)}
                      activeOpacity={0.8}
                    >
                      <Text
                        style={[
                          styles.slotText,
                          isSlotSelected && styles.slotTextSelected,
                        ]}
                      >
                        {formatTime(slot.start_time)}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </View>
            )}
          </View>
        )}

        <View style={{ height: 120 }} />
      </ScrollView>

      {/* Footer */}
      <View style={styles.footer}>
        <TouchableOpacity
          disabled={!selectedDetailer || !selectedSlot}
          onPress={handleConfirm}
          style={styles.shadowWrapper}
        >
          <LinearGradient
            colors={
              selectedDetailer && selectedSlot
                ? [Colors.primary, "#60A5FA"]
                : ["#1E293B", "#1E293B"]
            }
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={styles.confirmBtn}
          >
            <Text
              style={[
                styles.confirmText,
                (!selectedDetailer || !selectedSlot) && { color: "#475569" },
              ]}
            >
              {selectedDetailer && selectedSlot
                ? "REVIEW BOOKING"
                : "SELECT DETAILER & TIME"}
            </Text>
            <Ionicons
              name="chevron-forward"
              size={20}
              color={
                selectedDetailer && selectedSlot ? "#0F172A" : "#475569"
              }
            />
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
  headerTitle: {
    color: "white",
    fontSize: 20,
    fontWeight: "800",
    textAlign: "center",
  },
  headerStep: {
    color: Colors.primary,
    fontSize: 12,
    fontWeight: "600",
    textAlign: "center",
  },
  dateBanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginHorizontal: 20,
    marginBottom: 8,
    backgroundColor: "#161E2E",
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#262F3F",
  },
  dateBannerText: { color: "#94A3B8", fontSize: 12 },
  scroll: { paddingHorizontal: 20, paddingTop: 10, paddingBottom: 100 },
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 14,
  },
  sectionTitle: {
    color: "#94A3B8",
    fontSize: 12,
    fontWeight: "800",
    letterSpacing: 1.5,
  },
  detailerCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#161E2E",
    borderRadius: 18,
    padding: 14,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: "#262F3F",
  },
  detailerCardActive: {
    borderColor: Colors.primary,
    backgroundColor: "#0F1F33",
  },
  detailerAvatar: {
    marginRight: 12,
  },
  detailerInfo: { flex: 1 },
  detailerName: {
    color: "white",
    fontWeight: "700",
    fontSize: 15,
    marginBottom: 4,
  },
  starsRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 2,
    marginBottom: 4,
  },
  ratingText: { color: "#F59E0B", fontSize: 11, marginLeft: 4 },
  detailerMeta: { flexDirection: "row", flexWrap: "wrap", gap: 2 },
  metaText: { color: "#64748B", fontSize: 11 },
  priceDurationRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    marginTop: 4,
  },
  matchPrice: {
    color: Colors.primary,
    fontWeight: "800",
    fontSize: 14,
  },
  matchDuration: {
    color: "#64748B",
    fontSize: 12,
  },
  availableBadge: {
    backgroundColor: "#10B981" + "22",
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#10B981" + "55",
  },
  availableBadgeText: { color: "#10B981", fontSize: 10, fontWeight: "700" },
  unavailableBadge: {
    backgroundColor: "#EF4444" + "22",
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#EF4444" + "55",
  },
  unavailableBadgeText: { color: "#EF4444", fontSize: 10, fontWeight: "700" },
  emptyState: {
    alignItems: "center",
    paddingVertical: 40,
  },
  emptyText: { color: "#64748B", fontSize: 14 },
  noSlotsCard: {
    backgroundColor: "#161E2E",
    borderRadius: 16,
    padding: 24,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#262F3F",
  },
  noSlotsText: {
    color: "#94A3B8",
    fontSize: 14,
    fontWeight: "600",
    marginTop: 10,
  },
  noSlotsHint: { color: "#475569", fontSize: 12, marginTop: 4 },
  slotsGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
  },
  slotChip: {
    width: (width - 60) / 3,
    backgroundColor: "#161E2E",
    paddingVertical: 14,
    borderRadius: 14,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#262F3F",
  },
  slotChipSelected: {
    borderColor: Colors.primary,
    backgroundColor: Colors.primary,
  },
  slotText: { color: "#94A3B8", fontWeight: "700", fontSize: 13 },
  slotTextSelected: { color: "#0B0F1A" },
  footer: {
    position: "absolute",
    bottom: 0,
    width: "100%",
    padding: 25,
    backgroundColor: "rgba(11, 15, 26, 0.95)",
    borderTopWidth: 1,
    borderTopColor: "#161E2E",
  },
  shadowWrapper: {
    shadowColor: Colors.primary,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
  },
  confirmBtn: {
    padding: 20,
    borderRadius: 20,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: 10,
  },
  confirmText: {
    color: "#0F172A",
    fontWeight: "900",
    fontSize: 16,
    letterSpacing: 0.5,
  },
});
