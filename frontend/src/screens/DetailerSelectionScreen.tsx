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
import Card from "../components/Card";
import EmptyState from "../components/EmptyState";
import SectionHeader from "../components/SectionHeader";
import { APP_CONFIG } from "../config/app.config";
import { useLocation } from "../hooks/useLocation";
import {
  MatchedDetailer,
  TimeSlotRead,
  getMatching,
} from "../services/detailer.service";
import { Colors } from "../theme/colors";

const { width } = Dimensions.get("window");

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

  const firstServiceId: string | undefined = Object.values(selections || {})[0]
    ? (Object.values(selections)[0] as any).base?.id
    : undefined;
  const vehicleSizes: string[] = (selectedVehicles ?? []).map((v: any) => getVehicleSize(v.body_class));
  const allAddonIds: string[] = Object.values(selections || {}).flatMap(
    (sel: any) => (sel.addons ?? []).map((a: any) => a.id),
  );
  const uniqueAddonIds = [...new Set(allAddonIds)];

  const resolvedLat = lat ?? APP_CONFIG.fallbackCoords.lat;
  const resolvedLng = lng ?? APP_CONFIG.fallbackCoords.lng;
  const resolvedAddress = city
    ? `${city}, ${region}${zipcode ? ` ${zipcode}` : ""}`
    : APP_CONFIG.fallbackCoords.address;

  useEffect(() => { if (!locationLoading && firstServiceId) fetchMatching(); }, [locationLoading]);

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
      total: selectedDetailer.estimated_price / 100,
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
    return new Date(isoString).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true });
  };

  const renderStars = (rating: number | null) => {
    const stars = Math.round(rating ?? 0);
    return (
      <View style={styles.starsRow}>
        {[1, 2, 3, 4, 5].map((i) => (
          <Ionicons key={i} name={i <= stars ? "star" : "star-outline"} size={12} color="#F59E0B" />
        ))}
        {rating !== null && <Text style={styles.ratingText}>{rating.toFixed(1)}</Text>}
      </View>
    );
  };

  const availableSlots = selectedDetailer?.available_slots?.filter((s) => s.is_available) ?? [];

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
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
            Showing availability for <Text style={{ color: "white" }}>{date}</Text>
          </Text>
        </View>
      )}

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scroll}>
        <SectionHeader title="MATCHED DETAILERS" style={styles.sectionHeaderRow} />

        {loadingMatch ? (
          <ActivityIndicator color={Colors.primary} style={{ marginTop: 30 }} />
        ) : matched.length === 0 ? (
          <EmptyState icon="account-search" title="No detailers available" subtitle="Try a different date or service area." dashed={false} />
        ) : (
          matched.map((detailer) => {
            const isSelected = selectedDetailer?.user_id === detailer.user_id;
            return (
              <Card
                key={detailer.user_id}
                onPress={() => handleSelectDetailer(detailer)}
                style={[styles.detailerCard, isSelected ? styles.detailerCardActive : null]}
              >
                <View style={styles.detailerRow}>
                  <View style={styles.detailerAvatar}>
                    <MaterialCommunityIcons name="account-circle" size={44} color={isSelected ? Colors.primary : "#475569"} />
                  </View>
                  <View style={styles.detailerInfo}>
                    <Text style={styles.detailerName}>{detailer.full_name}</Text>
                    {renderStars(detailer.average_rating)}
                    <View style={styles.detailerMeta}>
                      {detailer.years_of_experience !== null && (
                        <Text style={styles.metaText}>{detailer.years_of_experience} yrs exp</Text>
                      )}
                      {detailer.distance_miles !== null && (
                        <Text style={styles.metaText}>· {detailer.distance_miles.toFixed(1)} mi</Text>
                      )}
                      <Text style={styles.metaText}>· {detailer.total_reviews} reviews</Text>
                    </View>
                    <View style={styles.priceDurationRow}>
                      <Text style={styles.matchPrice}>${(detailer.estimated_price / 100).toFixed(0)}</Text>
                      <Text style={styles.matchDuration}>· ~{detailer.estimated_duration} min</Text>
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
                </View>
              </Card>
            );
          })
        )}

        {selectedDetailer && (
          <View style={{ marginTop: 28 }}>
            <SectionHeader
              title={`SLOTS — ${selectedDetailer.full_name.split(" ")[0].toUpperCase()}`}
              style={styles.sectionHeaderRow}
            />
            {availableSlots.length === 0 ? (
              <Card style={{ alignItems: "center", gap: 8 }}>
                <Ionicons name="calendar-clear-outline" size={28} color="#475569" />
                <Text style={styles.noSlotsText}>No available slots{date ? ` on ${date}` : " today"}.</Text>
                <Text style={styles.noSlotsHint}>Try selecting a different date or detailer.</Text>
              </Card>
            ) : (
              <View style={styles.slotsGrid}>
                {availableSlots.map((slot) => {
                  const isSlotSelected = selectedSlot?.start_time === slot.start_time;
                  return (
                    <TouchableOpacity
                      key={slot.start_time}
                      style={[styles.slotChip, isSlotSelected && styles.slotChipSelected]}
                      onPress={() => setSelectedSlot(slot)}
                    >
                      <Text style={[styles.slotText, isSlotSelected && styles.slotTextSelected]}>
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

      <View style={styles.footer}>
        <Button
          title={selectedDetailer && selectedSlot ? "REVIEW BOOKING" : "SELECT DETAILER & TIME"}
          onPress={handleConfirm}
          variant="cta"
          size="lg"
          fullWidth
          disabled={!selectedDetailer || !selectedSlot}
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
    justifyContent: "space-between", paddingHorizontal: 20, paddingVertical: 15,
  },
  backBtn: {
    backgroundColor: "#161E2E", padding: 10,
    borderRadius: 12, borderWidth: 1, borderColor: "#262F3F",
  },
  headerTitle: { color: "white", fontSize: 20, fontWeight: "800", textAlign: "center" },
  headerStep: { color: Colors.primary, fontSize: 12, fontWeight: "600", textAlign: "center" },
  dateBanner: {
    flexDirection: "row", alignItems: "center", gap: 6,
    marginHorizontal: 20, marginBottom: 8,
    backgroundColor: "#161E2E", paddingHorizontal: 14, paddingVertical: 8,
    borderRadius: 10, borderWidth: 1, borderColor: "#262F3F",
  },
  dateBannerText: { color: "#94A3B8", fontSize: 12 },
  scroll: { paddingHorizontal: 20, paddingTop: 10, paddingBottom: 100 },
  sectionHeaderRow: { paddingHorizontal: 0, marginBottom: 14 },
  detailerCard: { marginBottom: 12 },
  detailerCardActive: { borderColor: Colors.primary, backgroundColor: "#0F1F33" },
  detailerRow: { flexDirection: "row", alignItems: "center" },
  detailerAvatar: { marginRight: 12 },
  detailerInfo: { flex: 1 },
  detailerName: { color: "white", fontWeight: "700", fontSize: 15, marginBottom: 4 },
  starsRow: { flexDirection: "row", alignItems: "center", gap: 2, marginBottom: 4 },
  ratingText: { color: "#F59E0B", fontSize: 11, marginLeft: 4 },
  detailerMeta: { flexDirection: "row", flexWrap: "wrap", gap: 2 },
  metaText: { color: "#64748B", fontSize: 11 },
  priceDurationRow: { flexDirection: "row", alignItems: "center", gap: 4, marginTop: 4 },
  matchPrice: { color: Colors.primary, fontWeight: "800", fontSize: 14 },
  matchDuration: { color: "#64748B", fontSize: 12 },
  availableBadge: {
    backgroundColor: "#10B98122", paddingHorizontal: 10, paddingVertical: 4,
    borderRadius: 8, borderWidth: 1, borderColor: "#10B98155",
  },
  availableBadgeText: { color: "#10B981", fontSize: 10, fontWeight: "700" },
  unavailableBadge: {
    backgroundColor: "#EF444422", paddingHorizontal: 10, paddingVertical: 4,
    borderRadius: 8, borderWidth: 1, borderColor: "#EF444455",
  },
  unavailableBadgeText: { color: "#EF4444", fontSize: 10, fontWeight: "700" },
  noSlotsText: { color: "#94A3B8", fontSize: 14, fontWeight: "600", marginTop: 8 },
  noSlotsHint: { color: "#475569", fontSize: 12 },
  slotsGrid: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  slotChip: {
    width: (width - 60) / 3, backgroundColor: "#161E2E",
    paddingVertical: 14, borderRadius: 12, alignItems: "center",
    borderWidth: 1, borderColor: "#262F3F",
  },
  slotChipSelected: { borderColor: Colors.primary, backgroundColor: Colors.primary },
  slotText: { color: "#94A3B8", fontWeight: "700", fontSize: 13 },
  slotTextSelected: { color: "#0B0F1A" },
  footer: {
    position: "absolute", bottom: 0, width: "100%",
    paddingHorizontal: 20, paddingVertical: 20,
    backgroundColor: "rgba(11, 15, 26, 0.95)",
    borderTopWidth: 1, borderTopColor: "#1E293B",
  },
});
