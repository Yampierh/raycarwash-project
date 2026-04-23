import { Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
import { useFocusEffect } from "@react-navigation/native";
import { LinearGradient } from "expo-linear-gradient";
import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Dimensions,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useAppNavigation } from "../hooks/useAppNavigation";
import { useAppointmentSocket } from "../hooks/useAppointmentSocket";
import { useDeadReckoning, KnownPosition } from "../hooks/useDeadReckoning";
import { useLocation } from "../hooks/useLocation";
import { useWeather } from "../hooks/useWeather";
import { getMyAppointments } from "../services/appointment.service";
import { getUserProfile } from "../services/user.service";
import { getMyVehicles } from "../services/vehicle.service";
import { Colors } from "../theme/colors";

const { width } = Dimensions.get("window");
const FLEET_CARD_W = width * 0.63;

// ─── Static data ─────────────────────────────────────────────────────────────

const QUICK_SERVICES = [
  {
    key: "full",
    label: "Full Detail",
    icon: "car-wash",
    color: "#3B82F6",
    desc: "Inside & out",
  },
  {
    key: "ext",
    label: "Exterior",
    icon: "spray",
    color: "#10B981",
    desc: "Wash & wax",
  },
  {
    key: "int",
    label: "Interior",
    icon: "seat-recline-extra",
    color: "#8B5CF6",
    desc: "Deep clean",
  },
  {
    key: "head",
    label: "Headlights",
    icon: "car-light-high",
    color: "#F59E0B",
    desc: "UV restore",
  },
];

const STATUS_COLORS: Record<string, string> = {
  pending: "#F59E0B",
  confirmed: "#3B82F6",
  arrived: "#A78BFA",
  in_progress: "#10B981",
  completed: "#94A3B8",
  cancelled_by_client: "#EF4444",
  cancelled_by_detailer: "#EF4444",
  no_show: "#64748B",
};

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
  burgundy: "#881337",
  purple: "#7C3AED",
  teal: "#0D9488",
  maroon: "#7F1D1D",
  beige: "#D4B896",
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

function getInitials(name?: string) {
  if (!name) return "U";
  return name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function getFirstName(name?: string) {
  return name?.split(" ")[0] || "there";
}

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

function getCountdown(iso: string) {
  const diff = new Date(iso).getTime() - Date.now();
  if (diff <= 0) return "Now";
  const d = Math.floor(diff / 86400000);
  const h = Math.floor((diff % 86400000) / 3600000);
  const m = Math.floor((diff % 3600000) / 60000);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function formatPrice(apt: any) {
  const cents = apt.estimated_price ?? apt.total_price;
  return cents != null ? `$${(cents / 100).toFixed(0)}` : "—";
}

function getMemberStatus(washes: number) {
  if (washes >= 15) return { label: "Platinum", color: "#E2E8F0" };
  if (washes >= 8) return { label: "Gold", color: "#F59E0B" };
  if (washes >= 3) return { label: "Silver", color: "#94A3B8" };
  return { label: "Bronze", color: "#B45309" };
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function HomeScreen() {
  const [userData, setUserData] = useState<any>(null);
  const [vehicles, setVehicles] = useState<any[]>([]);
  const [appointments, setAppointments] = useState<any[]>([]);
  const [completedWashes, setCompletedWashes] = useState(0);
  const [loading, setLoading] = useState(true);
  const [detailerLocation, setDetailerLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [lastKnownPosition, setLastKnownPosition] = useState<KnownPosition | null>(null);
  const estimatedPosition = useDeadReckoning(lastKnownPosition);

  const navigation = useAppNavigation();
  const { city, region, lat, lng, loading: locLoading } = useLocation();
  const weather = useWeather(lat, lng);

  useFocusEffect(
    useCallback(() => {
      (async () => {
        setLoading(true);
        try {
          const [profile, myCars, myApts] = await Promise.all([
            getUserProfile(),
            getMyVehicles(),
            getMyAppointments(1, 20),
          ]);
          setUserData(profile);
          setVehicles(myCars || []);
          const items: any[] = myApts?.items || [];
          setAppointments(items);
          setCompletedWashes(
            items.filter((a) => a.status === "completed").length,
          );
        } catch (e) {
          console.error("HomeScreen load error:", e);
        } finally {
          setLoading(false);
        }
      })();
    }, []),
  );

  if (loading) {
    return (
      <View style={[styles.container, { justifyContent: "center" }]}>
        <ActivityIndicator size="large" color={Colors.primary} />
      </View>
    );
  }

  const activeApt = appointments.find((a) =>
    ["confirmed", "arrived", "in_progress"].includes(a.status),
  );
  const upcomingApts = appointments.filter((a) =>
    ["pending", "confirmed"].includes(a.status),
  );

  // Real-time updates via WebSocket — subscribe to the active appointment's room
  useAppointmentSocket({
    appointmentId: activeApt?.id ?? null,
    onStatusChange: useCallback(
      (newStatus: string) => {
        setAppointments((prev) =>
          prev.map((a) => (a.id === activeApt?.id ? { ...a, status: newStatus } : a)),
        );
      },
      [activeApt?.id],
    ),
    onLocationUpdate: useCallback(
      (payload: { lat: number; lng: number; ts: string }) => {
        setDetailerLocation({ lat: payload.lat, lng: payload.lng });
        // Update Dead Reckoning anchor with every new real GPS fix
        setLastKnownPosition({
          lat: payload.lat,
          lng: payload.lng,
          heading: 0, // heading not provided by current WS protocol
          timestamp: Date.now(),
        });
      },
      [],
    ),
  });
  const nextApt = upcomingApts[0] ?? null;
  const memberStatus = getMemberStatus(completedWashes);

  const locationLine = locLoading
    ? "Detecting…"
    : city
      ? `${city}, ${region}`
      : "Location unavailable";

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
      >
        {/* ── HEADER ──────────────────────────────────────────────────── */}
        <View style={styles.header}>
          <View style={{ flex: 1 }}>
            <Text style={styles.greeting}>{getGreeting()},</Text>
            <Text style={styles.userName}>
              {getFirstName(userData?.full_name).toUpperCase()}
            </Text>
            <View style={styles.locationRow}>
              <Ionicons
                name="location-sharp"
                size={13}
                color={Colors.primary}
              />
              <Text style={styles.locationText}>{locationLine}</Text>
            </View>
          </View>
          <TouchableOpacity
            onPress={() => (navigation as any).navigate("Profile")}
            style={styles.avatarWrap}
          >
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>
                {getInitials(userData?.full_name)}
              </Text>
            </View>
            <View style={styles.onlineDot} />
          </TouchableOpacity>
        </View>

        {/* ── WEATHER CARD ────────────────────────────────────────────── */}
        {!weather.loading && (
          <LinearGradient
            colors={
              weather.isGoodForDetailing
                ? ["#0C2340", "#0B0F1A"]
                : ["#1C1917", "#0B0F1A"]
            }
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={styles.weatherCard}
          >
            <View style={styles.weatherLeft}>
              <MaterialCommunityIcons
                name={weather.icon as any}
                size={36}
                color={weather.isGoodForDetailing ? "#FCD34D" : "#94A3B8"}
              />
              <View style={{ marginLeft: 12 }}>
                <Text style={styles.weatherTemp}>
                  {weather.temperature !== null
                    ? `${weather.temperature}°F`
                    : "—"}
                </Text>
                <Text style={styles.weatherCond}>{weather.condition}</Text>
              </View>
            </View>
            <View style={styles.weatherRight}>
              <View
                style={[
                  styles.weatherBadge,
                  {
                    backgroundColor: weather.isGoodForDetailing
                      ? "#10B98120"
                      : "#EF444420",
                  },
                ]}
              >
                <Ionicons
                  name={
                    weather.isGoodForDetailing
                      ? "checkmark-circle"
                      : "close-circle"
                  }
                  size={12}
                  color={weather.isGoodForDetailing ? "#10B981" : "#EF4444"}
                />
                <Text
                  style={[
                    styles.weatherBadgeText,
                    {
                      color: weather.isGoodForDetailing ? "#10B981" : "#EF4444",
                    },
                  ]}
                >
                  {weather.isGoodForDetailing
                    ? "Great day to detail!"
                    : "Rain expected"}
                </Text>
              </View>
              <Text style={styles.weatherSub}>
                {weather.isGoodForDetailing
                  ? "Book your service today"
                  : "Schedule for another day"}
              </Text>
            </View>
          </LinearGradient>
        )}

        {/* ── ACTIVE APPOINTMENT BANNER ───────────────────────────────── */}
        {activeApt && (
          <TouchableOpacity style={styles.activeBanner} activeOpacity={0.85}>
            <View
              style={[
                styles.activeBannerAccent,
                { backgroundColor: STATUS_COLORS[activeApt.status] },
              ]}
            />
            <View style={styles.activeBannerBody}>
              <View style={styles.activeBannerRow}>
                <View
                  style={[
                    styles.activeStatusPill,
                    { backgroundColor: `${STATUS_COLORS[activeApt.status]}20` },
                  ]}
                >
                  <View
                    style={[
                      styles.activePulse,
                      { backgroundColor: STATUS_COLORS[activeApt.status] },
                    ]}
                  />
                  <Text
                    style={[
                      styles.activeStatusText,
                      { color: STATUS_COLORS[activeApt.status] },
                    ]}
                  >
                    {activeApt.status === "in_progress"
                      ? "IN PROGRESS"
                      : activeApt.status === "arrived"
                        ? "DETAILER ARRIVED"
                        : "CONFIRMED"}
                  </Text>
                </View>
                <Text style={styles.activeBannerTime}>
                  {new Date(activeApt.scheduled_time).toLocaleTimeString(
                    "en-US",
                    {
                      hour: "numeric",
                      minute: "2-digit",
                      hour12: true,
                    },
                  )}
                </Text>
              </View>
              <Text style={styles.activeBannerTitle}>
                {activeApt.status === "in_progress"
                  ? "Your detail is in progress"
                  : activeApt.status === "arrived"
                    ? "Your detailer is on site!"
                    : "Your detailer is confirmed"}
              </Text>
              {activeApt.vehicle && (
                <Text style={styles.activeBannerSub}>
                  {activeApt.vehicle.year} {activeApt.vehicle.make}{" "}
                  {activeApt.vehicle.model}
                  {activeApt.service_name
                    ? `  ·  ${activeApt.service_name}`
                    : ""}
                </Text>
              )}
            </View>
            <Ionicons name="chevron-forward" size={18} color="#334155" />
          </TouchableOpacity>
        )}

        {/* ── DETAILER TRACKING (Dead Reckoning) ──────────────────────── */}
        {activeApt && estimatedPosition && (
          <View style={styles.trackingCard}>
            <View style={styles.trackingRow}>
              <View style={styles.trackingDot} />
              <Text style={styles.trackingLabel}>Detailer Location (Live)</Text>
            </View>
            <Text style={styles.trackingCoords}>
              {estimatedPosition.lat.toFixed(5)}°N, {Math.abs(estimatedPosition.lng).toFixed(5)}°W
            </Text>
            <Text style={styles.trackingNote}>Interpolated at 60 fps — no teleportation</Text>
          </View>
        )}

        {/* ── HERO CTA ────────────────────────────────────────────────── */}
        <TouchableOpacity
          activeOpacity={0.88}
          onPress={() => navigation.navigate("SelectVehicles")}
        >
          <LinearGradient
            colors={["#1D4ED8", "#1E3A5F", "#0B1525"]}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={styles.heroCta}
          >
            <View style={styles.heroLeft}>
              <MaterialCommunityIcons
                name="car-wash"
                size={32}
                color="#60A5FA"
              />
              <View style={{ marginLeft: 14 }}>
                <Text style={styles.heroTitle}>BOOK A DETAIL</Text>
                <Text style={styles.heroSub}>
                  Mobile detailing at your door
                </Text>
              </View>
            </View>
            <View style={styles.heroArrow}>
              <Ionicons name="arrow-forward" size={18} color="#fff" />
            </View>
          </LinearGradient>
        </TouchableOpacity>

        {/* ── STATS ROW ───────────────────────────────────────────────── */}
        <View style={styles.statsCard}>
          <View style={styles.statItem}>
            <Text style={styles.statNum}>{completedWashes}</Text>
            <Text style={styles.statLabel}>Washes</Text>
          </View>
          <View style={[styles.statItem, styles.statBorder]}>
            <Text style={styles.statNum}>{vehicles.length}</Text>
            <Text style={styles.statLabel}>Vehicles</Text>
          </View>
          <View style={styles.statItem}>
            <Text style={[styles.statNum, { color: memberStatus.color }]}>
              {memberStatus.label}
            </Text>
            <Text style={styles.statLabel}>Status</Text>
          </View>
        </View>

        {/* ── QUICK ACTIONS ────────────────────────────────────────────── */}
        <View style={styles.quickActions}>
          {[
            {
              icon: "car-outline",
              label: "My Fleet",
              onPress: () => (navigation as any).navigate("Vehicles"),
            },
            {
              icon: "calendar-outline",
              label: "Schedule",
              onPress: () => navigation.navigate("SelectVehicles"),
            },
            {
              icon: "time-outline",
              label: "History",
              onPress: () => (navigation as any).navigate("Appointments"),
            },
            {
              icon: "person-outline",
              label: "Profile",
              onPress: () => (navigation as any).navigate("Profile"),
            },
          ].map((action) => (
            <TouchableOpacity
              key={action.label}
              style={styles.quickAction}
              onPress={action.onPress}
            >
              <View style={styles.quickActionIcon}>
                <Ionicons
                  name={action.icon as any}
                  size={22}
                  color={Colors.primary}
                />
              </View>
              <Text style={styles.quickActionLabel}>{action.label}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* ── YOUR FLEET ──────────────────────────────────────────────── */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>
            YOUR FLEET ({vehicles.length})
          </Text>
          <TouchableOpacity
            onPress={() => (navigation as any).navigate("Vehicles")}
          >
            <Text style={styles.viewAll}>View all</Text>
          </TouchableOpacity>
        </View>

        {vehicles.length > 0 ? (
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={{ paddingRight: 20 }}
          >
            {vehicles.map((car) => {
              const colorHex = getColorDot(car.color);
              const needsBorder = car.color?.toLowerCase() === "white";
              return (
                <View
                  key={car.id}
                  style={[styles.fleetCard, { width: FLEET_CARD_W }]}
                >
                  <LinearGradient
                    colors={[`${colorHex}18`, "transparent"]}
                    style={StyleSheet.absoluteFillObject}
                  />
                  {/* Body class badge */}
                  <View style={styles.fleetBadge}>
                    <Text style={styles.fleetBadgeText}>
                      {(car.body_class || "SEDAN").toUpperCase()}
                    </Text>
                  </View>

                  {/* Car icon */}
                  <View style={styles.carIconWrap}>
                    <MaterialCommunityIcons
                      name={getCarIcon(car.body_class) as any}
                      size={56}
                      color={colorHex}
                      style={{ opacity: 0.9 }}
                    />
                  </View>

                  {/* Info */}
                  <Text style={styles.carName}>
                    {car.year} {car.make} {car.model}
                  </Text>

                  <View style={styles.carMeta}>
                    <View style={styles.carMetaItem}>
                      <Ionicons name="card-outline" size={11} color="#475569" />
                      <Text style={styles.carMetaText}>
                        {car.license_plate}
                      </Text>
                    </View>
                    <View style={styles.carMetaItem}>
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
                      <Text style={styles.carMetaText}>
                        {car.color?.charAt(0).toUpperCase() +
                          car.color?.slice(1)}
                      </Text>
                    </View>
                  </View>

                  <TouchableOpacity
                    style={styles.bookNowBtn}
                    onPress={() =>
                      navigation.navigate("Booking", {
                        selectedVehicles: [car],
                      })
                    }
                  >
                    <Text style={styles.bookNowText}>BOOK NOW</Text>
                  </TouchableOpacity>
                </View>
              );
            })}

            {/* Add vehicle card */}
            <TouchableOpacity
              style={[
                styles.fleetCard,
                styles.addFleetCard,
                { width: FLEET_CARD_W * 0.55 },
              ]}
              onPress={() => navigation.navigate("AddVehicle")}
            >
              <MaterialCommunityIcons
                name="plus-circle-outline"
                size={32}
                color="#334155"
              />
              <Text style={styles.addFleetText}>Add{"\n"}Vehicle</Text>
            </TouchableOpacity>
          </ScrollView>
        ) : (
          <TouchableOpacity
            style={styles.emptyFleet}
            onPress={() => navigation.navigate("AddVehicle")}
          >
            <MaterialCommunityIcons name="car" size={36} color="#334155" />
            <Text style={styles.emptyFleetTitle}>No vehicles yet</Text>
            <Text style={styles.emptyFleetSub}>
              Tap to add your first vehicle
            </Text>
          </TouchableOpacity>
        )}

        {/* ── NEXT APPOINTMENT ────────────────────────────────────────── */}
        <View style={[styles.sectionHeader, { marginTop: 28 }]}>
          <Text style={styles.sectionTitle}>UPCOMING</Text>
          {upcomingApts.length > 1 && (
            <Text style={styles.viewAll}>{upcomingApts.length} scheduled</Text>
          )}
        </View>

        {nextApt ? (
          <View style={styles.aptCard}>
            <View
              style={[
                styles.aptAccent,
                { backgroundColor: STATUS_COLORS[nextApt.status] ?? "#3B82F6" },
              ]}
            />
            <View style={styles.aptBody}>
              <View style={styles.aptTopRow}>
                <View
                  style={[
                    styles.aptStatusPill,
                    {
                      backgroundColor: `${STATUS_COLORS[nextApt.status] ?? "#3B82F6"}20`,
                    },
                  ]}
                >
                  <Text
                    style={[
                      styles.aptStatusText,
                      { color: STATUS_COLORS[nextApt.status] ?? "#3B82F6" },
                    ]}
                  >
                    {nextApt.status.replace(/_/g, " ").toUpperCase()}
                  </Text>
                </View>
                <Text style={styles.aptCountdown}>
                  {getCountdown(nextApt.scheduled_time)}
                </Text>
              </View>

              <View style={styles.aptMidRow}>
                <View>
                  <Text style={styles.aptDate}>
                    {new Date(nextApt.scheduled_time).toLocaleDateString(
                      "en-US",
                      {
                        weekday: "long",
                        month: "short",
                        day: "numeric",
                      },
                    )}
                  </Text>
                  <Text style={styles.aptTime}>
                    {new Date(nextApt.scheduled_time).toLocaleTimeString(
                      "en-US",
                      {
                        hour: "numeric",
                        minute: "2-digit",
                        hour12: true,
                      },
                    )}
                  </Text>
                </View>
                <Text style={styles.aptPrice}>{formatPrice(nextApt)}</Text>
              </View>

              {(nextApt.vehicle || nextApt.service_name) && (
                <Text style={styles.aptMeta}>
                  {nextApt.vehicle
                    ? `${nextApt.vehicle.year} ${nextApt.vehicle.make} ${nextApt.vehicle.model}`
                    : ""}
                  {nextApt.vehicle && nextApt.service_name ? "  ·  " : ""}
                  {nextApt.service_name ?? ""}
                </Text>
              )}
            </View>
          </View>
        ) : (
          <View style={styles.emptyApt}>
            <MaterialCommunityIcons
              name="calendar-blank-outline"
              size={48}
              color="#1E293B"
            />
            <Text style={styles.emptyAptTitle}>No upcoming appointments</Text>
            <TouchableOpacity
              style={styles.emptyAptBtn}
              onPress={() => navigation.navigate("SelectVehicles")}
            >
              <Text style={styles.emptyAptBtnText}>BOOK NOW</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* ── OUR SERVICES ────────────────────────────────────────────── */}
        <Text
          style={[styles.sectionTitle, { marginTop: 28, marginBottom: 14 }]}
        >
          OUR SERVICES
        </Text>
        <View style={styles.servicesGrid}>
          {QUICK_SERVICES.map((s) => (
            <TouchableOpacity
              key={s.key}
              style={styles.serviceCard}
              onPress={() => navigation.navigate("SelectVehicles")}
            >
              <View
                style={[
                  styles.serviceIconWrap,
                  { backgroundColor: `${s.color}18` },
                ]}
              >
                <MaterialCommunityIcons
                  name={s.icon as any}
                  size={26}
                  color={s.color}
                />
              </View>
              <Text style={styles.serviceLabel}>{s.label}</Text>
              <Text style={styles.serviceDesc}>{s.desc}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* ── SPECIAL OFFERS ──────────────────────────────────────────── */}
        <Text
          style={[styles.sectionTitle, { marginTop: 28, marginBottom: 14 }]}
        >
          SPECIAL OFFERS
        </Text>
        <LinearGradient
          colors={["#1D4ED8", "#1E3A5F"]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={styles.offerCard}
        >
          <View style={styles.offerContent}>
            <View style={styles.offerBadge}>
              <Text style={styles.offerBadgeText}>LIMITED</Text>
            </View>
            <Text style={styles.offerTitle}>Summer Shine Special</Text>
            <Text style={styles.offerDesc}>
              $20 off any Full Detail service this season
            </Text>
            <TouchableOpacity
              style={styles.offerBtn}
              onPress={() => navigation.navigate("SelectVehicles")}
            >
              <Text style={styles.offerBtnText}>CLAIM OFFER</Text>
            </TouchableOpacity>
          </View>
          <MaterialCommunityIcons
            name="ticket-percent"
            size={80}
            color="#ffffff10"
            style={styles.offerBgIcon}
          />
        </LinearGradient>

        <View style={{ height: 110 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

// ─── Styles ──────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0B0F1A" },
  scroll: { paddingTop: 8 },

  // Header
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingBottom: 20,
  },
  greeting: { color: "#475569", fontSize: 13, fontWeight: "600" },
  userName: {
    color: "#fff",
    fontSize: 22,
    fontWeight: "900",
    letterSpacing: 0.5,
  },
  locationRow: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 3,
    gap: 4,
  },
  locationText: { color: Colors.primary, fontSize: 12, fontWeight: "600" },
  avatarWrap: { position: "relative", marginLeft: 12 },
  avatar: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: "#1E3A5F",
    borderWidth: 2,
    borderColor: Colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  avatarText: { color: Colors.primary, fontWeight: "bold", fontSize: 18 },
  onlineDot: {
    position: "absolute",
    bottom: 2,
    right: 2,
    width: 13,
    height: 13,
    borderRadius: 7,
    backgroundColor: "#10B981",
    borderWidth: 2,
    borderColor: "#0B0F1A",
  },

  // Weather
  weatherCard: {
    flexDirection: "row",
    alignItems: "center",
    marginHorizontal: 20,
    borderRadius: 18,
    padding: 16,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: "#1E293B",
  },
  weatherLeft: { flexDirection: "row", alignItems: "center", flex: 1 },
  weatherTemp: { color: "#fff", fontSize: 20, fontWeight: "800" },
  weatherCond: { color: "#64748B", fontSize: 11, marginTop: 2 },
  weatherRight: { alignItems: "flex-end", gap: 4 },
  weatherBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 20,
  },
  weatherBadgeText: { fontSize: 11, fontWeight: "800" },
  weatherSub: { color: "#334155", fontSize: 10, textAlign: "right" },

  // Detailer tracking card (Dead Reckoning)
  trackingCard: {
    marginHorizontal: 20, marginBottom: 14,
    backgroundColor: "#0F2234", borderRadius: 14, padding: 14,
    borderWidth: 1, borderColor: "#1E3A5F",
  },
  trackingRow: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 6 },
  trackingDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: "#22C55E" },
  trackingLabel: { color: "#22C55E", fontWeight: "600", fontSize: 12 },
  trackingCoords: { color: "#F8FAFC", fontFamily: "monospace", fontSize: 13, marginBottom: 4 },
  trackingNote: { color: "#475569", fontSize: 11 },

  // Active banner
  activeBanner: {
    flexDirection: "row",
    alignItems: "center",
    marginHorizontal: 20,
    marginBottom: 14,
    backgroundColor: "#161E2E",
    borderRadius: 18,
    borderWidth: 1,
    borderColor: "#262F3F",
    overflow: "hidden",
  },
  activeBannerAccent: { width: 4, alignSelf: "stretch" },
  activeBannerBody: { flex: 1, padding: 14, gap: 4 },
  activeBannerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  activeStatusPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: 20,
  },
  activePulse: { width: 7, height: 7, borderRadius: 4 },
  activeStatusText: { fontSize: 10, fontWeight: "800", letterSpacing: 0.8 },
  activeBannerTime: { color: "#475569", fontSize: 12 },
  activeBannerTitle: { color: "#fff", fontSize: 14, fontWeight: "700" },
  activeBannerSub: { color: "#475569", fontSize: 12 },

  // Hero CTA
  heroCta: {
    flexDirection: "row",
    alignItems: "center",
    marginHorizontal: 20,
    borderRadius: 22,
    padding: 20,
    marginBottom: 14,
  },
  heroLeft: { flexDirection: "row", alignItems: "center", flex: 1 },
  heroTitle: {
    color: "#fff",
    fontSize: 18,
    fontWeight: "900",
    letterSpacing: 0.5,
  },
  heroSub: { color: "#93C5FD", fontSize: 12, marginTop: 2 },
  heroArrow: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: "#ffffff15",
    alignItems: "center",
    justifyContent: "center",
  },

  // Stats
  statsCard: {
    flexDirection: "row",
    backgroundColor: "#161E2E",
    marginHorizontal: 20,
    borderRadius: 18,
    paddingVertical: 18,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: "#262F3F",
  },
  statItem: { flex: 1, alignItems: "center" },
  statBorder: {
    borderLeftWidth: 1,
    borderRightWidth: 1,
    borderColor: "#1E293B",
  },
  statNum: { color: "#fff", fontSize: 18, fontWeight: "800" },
  statLabel: {
    color: "#475569",
    fontSize: 11,
    fontWeight: "600",
    marginTop: 2,
  },

  // Quick actions
  quickActions: {
    flexDirection: "row",
    paddingHorizontal: 20,
    gap: 10,
    marginBottom: 24,
  },
  quickAction: { flex: 1, alignItems: "center", gap: 6 },
  quickActionIcon: {
    width: 50,
    height: 50,
    borderRadius: 16,
    backgroundColor: "#161E2E",
    borderWidth: 1,
    borderColor: "#262F3F",
    alignItems: "center",
    justifyContent: "center",
  },
  quickActionLabel: { color: "#64748B", fontSize: 10, fontWeight: "700" },

  // Section header
  sectionHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 20,
    marginBottom: 14,
  },
  sectionTitle: {
    color: "#fff",
    fontSize: 13,
    fontWeight: "800",
    letterSpacing: 0.6,
    paddingHorizontal: 20,
  },
  viewAll: { color: Colors.primary, fontSize: 13 },

  // Fleet
  fleetCard: {
    backgroundColor: "#161E2E",
    borderRadius: 22,
    padding: 16,
    marginLeft: 20,
    borderWidth: 1,
    borderColor: "#262F3F",
    overflow: "hidden",
  },
  fleetBadge: {
    backgroundColor: "#1E293B",
    alignSelf: "flex-start",
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
    marginBottom: 10,
  },
  fleetBadgeText: {
    color: "#64748B",
    fontSize: 9,
    fontWeight: "800",
    letterSpacing: 0.5,
  },
  carIconWrap: { alignItems: "center", marginVertical: 10 },
  carName: { color: "#fff", fontSize: 15, fontWeight: "800" },
  carMeta: { flexDirection: "row", gap: 12, marginTop: 6, marginBottom: 12 },
  carMetaItem: { flexDirection: "row", alignItems: "center", gap: 4 },
  carMetaText: { color: "#475569", fontSize: 11 },
  colorDot: { width: 10, height: 10, borderRadius: 5 },
  bookNowBtn: {
    backgroundColor: Colors.primary,
    paddingVertical: 10,
    borderRadius: 12,
    alignItems: "center",
  },
  bookNowText: {
    color: "#fff",
    fontWeight: "800",
    fontSize: 12,
    letterSpacing: 0.5,
  },
  addFleetCard: {
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    borderStyle: "dashed",
    backgroundColor: "transparent",
  },
  addFleetText: {
    color: "#334155",
    fontSize: 12,
    fontWeight: "700",
    textAlign: "center",
  },
  emptyFleet: {
    marginHorizontal: 20,
    backgroundColor: "#161E2E",
    borderRadius: 22,
    padding: 32,
    alignItems: "center",
    gap: 8,
    borderWidth: 1,
    borderColor: "#262F3F",
    borderStyle: "dashed",
  },
  emptyFleetTitle: { color: "#475569", fontSize: 15, fontWeight: "700" },
  emptyFleetSub: { color: "#334155", fontSize: 12 },

  // Appointment card
  aptCard: {
    flexDirection: "row",
    marginHorizontal: 20,
    backgroundColor: "#161E2E",
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "#262F3F",
    overflow: "hidden",
  },
  aptAccent: { width: 4 },
  aptBody: { flex: 1, padding: 16, gap: 8 },
  aptTopRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  aptStatusPill: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 20,
  },
  aptStatusText: { fontSize: 10, fontWeight: "800", letterSpacing: 0.8 },
  aptCountdown: { color: "#475569", fontSize: 12, fontWeight: "700" },
  aptMidRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-end",
  },
  aptDate: { color: "#fff", fontSize: 16, fontWeight: "800" },
  aptTime: { color: "#64748B", fontSize: 13 },
  aptPrice: { color: "#fff", fontSize: 22, fontWeight: "900" },
  aptMeta: { color: "#475569", fontSize: 12 },
  emptyApt: {
    marginHorizontal: 20,
    backgroundColor: "#161E2E",
    borderRadius: 20,
    padding: 32,
    alignItems: "center",
    gap: 10,
    borderWidth: 1,
    borderColor: "#1E293B",
  },
  emptyAptTitle: { color: "#334155", fontSize: 14 },
  emptyAptBtn: {
    backgroundColor: Colors.primary,
    paddingVertical: 14,
    paddingHorizontal: 36,
    borderRadius: 14,
    marginTop: 4,
  },
  emptyAptBtnText: { color: "#fff", fontWeight: "800", letterSpacing: 1 },

  // Services grid
  servicesGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    paddingHorizontal: 20,
    gap: 12,
  },
  serviceCard: {
    width: (width - 52) / 2,
    backgroundColor: "#161E2E",
    borderRadius: 18,
    padding: 16,
    gap: 8,
    borderWidth: 1,
    borderColor: "#262F3F",
  },
  serviceIconWrap: {
    width: 48,
    height: 48,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
  },
  serviceLabel: { color: "#fff", fontSize: 14, fontWeight: "800" },
  serviceDesc: { color: "#475569", fontSize: 12 },

  // Offer card
  offerCard: {
    marginHorizontal: 20,
    borderRadius: 22,
    padding: 22,
    overflow: "hidden",
  },
  offerContent: { gap: 8, maxWidth: "80%" },
  offerBadge: {
    backgroundColor: "#ffffff20",
    alignSelf: "flex-start",
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: 20,
  },
  offerBadgeText: {
    color: "#93C5FD",
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 1,
  },
  offerTitle: { color: "#fff", fontSize: 18, fontWeight: "900" },
  offerDesc: { color: "#93C5FD", fontSize: 13, lineHeight: 18 },
  offerBtn: {
    backgroundColor: "#fff",
    alignSelf: "flex-start",
    paddingHorizontal: 18,
    paddingVertical: 10,
    borderRadius: 12,
    marginTop: 4,
  },
  offerBtnText: { color: "#1D4ED8", fontWeight: "900", fontSize: 13 },
  offerBgIcon: {
    position: "absolute",
    right: -10,
    bottom: -10,
  },
});
