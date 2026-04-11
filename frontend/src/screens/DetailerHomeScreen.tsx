import { Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
import { useFocusEffect } from "@react-navigation/native";
import * as Location from "expo-location";
import { LinearGradient } from "expo-linear-gradient";
import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Linking,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useAppNavigation } from "../hooks/useAppNavigation";
import { useAppointmentSocket } from "../hooks/useAppointmentSocket";
import {
  getMyAppointments,
  patchAppointmentStatus,
} from "../services/appointment.service";
import {
  getMyDetailerProfile,
  toggleAcceptingBookings,
} from "../services/detailer-private.service";
import { getUserProfile } from "../services/user.service";
import { Colors } from "../theme/colors";
import {
  formatPrice,
  getCarIcon,
  getCountdown,
  getFirstName,
  getGreeting,
  getInitials,
} from "../utils/formatters";

interface Appointment {
  id: string;
  status: string;
  scheduled_time: string;
  service_address: string;
  client_notes?: string;
  client?: { full_name?: string; phone?: string };
  vehicles?: Array<{ vehicle?: { make?: string; model?: string; body_class?: string; color?: string } }>;
  estimated_price_cents?: number;
  actual_price_cents?: number;
}

const STATUS_LABEL: Record<string, string> = {
  pending: "Pending",
  confirmed: "Confirmed",
  arrived: "Arrived",
  in_progress: "In Progress",
  completed: "Completed",
  cancelled_by_client: "Cancelled",
  cancelled_by_detailer: "Cancelled",
};

const STATUS_COLOR: Record<string, string> = {
  pending: "#F59E0B",
  confirmed: "#3B82F6",
  arrived: "#A78BFA",
  in_progress: "#10B981",
  completed: "#94A3B8",
  cancelled_by_client: "#EF4444",
  cancelled_by_detailer: "#EF4444",
};

function formatJobTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatJobDate(iso: string): string {
  const d = new Date(iso);
  const today = new Date();
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);
  if (d.toDateString() === today.toDateString()) return "Today";
  if (d.toDateString() === tomorrow.toDateString()) return "Tomorrow";
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}

function isToday(iso: string): boolean {
  return new Date(iso).toDateString() === new Date().toDateString();
}

export default function DetailerHomeScreen() {
  const navigation = useAppNavigation();

  const [userName, setUserName] = useState<string | undefined>();
  const [accepting, setAccepting] = useState(false);
  const [togglingStatus, setTogglingStatus] = useState(false);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [stats, setStats] = useState({ earnings: 0, jobs: 0, rating: 0 });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Active job timer
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Active job = arrived OR in_progress (detailer is on-site or working)
  const activeJob = appointments.find(
    (a) => a.status === "arrived" || a.status === "in_progress",
  );
  const nextJob = appointments.find(
    (a) =>
      (a.status === "confirmed" || a.status === "pending") &&
      new Date(a.scheduled_time) > new Date(),
  );

  // WebSocket — connect to active job's room (or next confirmed job)
  const wsJobId = activeJob?.id ?? null;
  const { sendLocationUpdate } = useAppointmentSocket({
    appointmentId: wsJobId,
    onStatusChange: useCallback(
      (newStatus: string) => {
        // Optimistically update local state on WS broadcast
        setAppointments((prev) =>
          prev.map((a) => (a.id === wsJobId ? { ...a, status: newStatus } : a)),
        );
      },
      [wsJobId],
    ),
  });

  // Send GPS location every 5 s while an active job is open
  const locationIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(() => {
    if (!activeJob) {
      if (locationIntervalRef.current) {
        clearInterval(locationIntervalRef.current);
        locationIntervalRef.current = null;
      }
      return;
    }

    const pushLocation = async () => {
      try {
        const pos = await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.Balanced,
        });
        sendLocationUpdate(pos.coords.latitude, pos.coords.longitude);
      } catch {
        // Location unavailable — skip tick
      }
    };

    pushLocation(); // immediate first push
    locationIntervalRef.current = setInterval(pushLocation, 5_000);
    return () => {
      if (locationIntervalRef.current) {
        clearInterval(locationIntervalRef.current);
        locationIntervalRef.current = null;
      }
    };
  }, [activeJob?.id, sendLocationUpdate]);
  const todayJobs = appointments.filter(
    (a) => isToday(a.scheduled_time) && a.status !== "cancelled_by_client" && a.status !== "cancelled_by_detailer",
  );

  useEffect(() => {
    if (activeJob) {
      setElapsed(0);
      timerRef.current = setInterval(() => setElapsed((s) => s + 1), 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [activeJob?.id]);

  function formatElapsed(secs: number): string {
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = secs % 60;
    if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }

  async function loadData() {
    try {
      const [user, profile, appts] = await Promise.all([
        getUserProfile(),
        getMyDetailerProfile(),
        getMyAppointments(1, 50),
      ]);
      setUserName(user.full_name);
      setAccepting(profile.is_accepting_bookings);
      setStats({
        earnings: profile.total_earnings_cents,
        jobs: profile.total_services,
        rating: profile.average_rating ?? 0,
      });
      setAppointments(appts.items as Appointment[]);
    } catch {
      // non-critical refresh failures are silently ignored
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useFocusEffect(
    useCallback(() => {
      setLoading(true);
      loadData();
    }, []),
  );

  async function handleToggleStatus() {
    setTogglingStatus(true);
    try {
      const next = !accepting;
      await toggleAcceptingBookings(next);
      setAccepting(next);
    } catch {
      Alert.alert("Error", "Could not update your status. Try again.");
    } finally {
      setTogglingStatus(false);
    }
  }

  async function handleStatusChange(appt: Appointment, newStatus: string) {
    Alert.alert(
      "Update Job Status",
      `Mark this job as "${STATUS_LABEL[newStatus] ?? newStatus}"?`,
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Confirm",
          onPress: async () => {
            try {
              await patchAppointmentStatus(appt.id, { status: newStatus });
              await loadData();
            } catch {
              Alert.alert("Error", "Status update failed. Please try again.");
            }
          },
        },
      ],
    );
  }

  function callClient(phone?: string) {
    if (!phone) { Alert.alert("No phone", "Client phone not available."); return; }
    Linking.openURL(`tel:${phone}`);
  }

  if (loading) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.loader}>
          <ActivityIndicator size="large" color="#60A5FA" />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => { setRefreshing(true); loadData(); }}
            tintColor="#60A5FA"
          />
        }
      >
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.headerLeft}>
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>{getInitials(userName)}</Text>
            </View>
            <View>
              <Text style={styles.greeting}>{getGreeting()},</Text>
              <Text style={styles.name}>{getFirstName(userName)}</Text>
            </View>
          </View>
          <TouchableOpacity style={styles.bellBtn} onPress={() => {}}>
            <Ionicons name="notifications-outline" size={22} color="#94A3B8" />
          </TouchableOpacity>
        </View>

        {/* Online Toggle Card */}
        <LinearGradient
          colors={accepting ? ["#1E3A2F", "#0F2A1F"] : ["#2A1E1E", "#1A0F0F"]}
          style={styles.statusCard}
        >
          <View style={styles.statusCardLeft}>
            <View style={[styles.statusDot, { backgroundColor: accepting ? "#10B981" : "#EF4444" }]} />
            <View>
              <Text style={styles.statusLabel}>
                {accepting ? "You're Online" : "You're Offline"}
              </Text>
              <Text style={styles.statusSub}>
                {accepting ? "Clients can book you" : "Hidden from matching"}
              </Text>
            </View>
          </View>
          <TouchableOpacity
            style={[styles.toggleBtn, accepting && styles.toggleBtnOn]}
            onPress={handleToggleStatus}
            disabled={togglingStatus}
          >
            {togglingStatus ? (
              <ActivityIndicator size="small" color="#FFF" />
            ) : (
              <Text style={styles.toggleBtnText}>{accepting ? "Go Offline" : "Go Online"}</Text>
            )}
          </TouchableOpacity>
        </LinearGradient>

        {/* Today's Summary */}
        <Text style={styles.sectionTitle}>Today's Summary</Text>
        <View style={styles.statsRow}>
          <LinearGradient colors={["#1E293B", "#0F172A"]} style={styles.statCard}>
            <MaterialCommunityIcons name="currency-usd" size={22} color="#10B981" />
            <Text style={styles.statValue}>{formatPrice(stats.earnings)}</Text>
            <Text style={styles.statLabel}>Earned</Text>
          </LinearGradient>
          <LinearGradient colors={["#1E293B", "#0F172A"]} style={styles.statCard}>
            <MaterialCommunityIcons name="briefcase-check" size={22} color="#3B82F6" />
            <Text style={styles.statValue}>{stats.jobs}</Text>
            <Text style={styles.statLabel}>Total Jobs</Text>
          </LinearGradient>
          <LinearGradient colors={["#1E293B", "#0F172A"]} style={styles.statCard}>
            <MaterialCommunityIcons name="star" size={22} color="#F59E0B" />
            <Text style={styles.statValue}>
              {stats.rating > 0 ? stats.rating.toFixed(1) : "—"}
            </Text>
            <Text style={styles.statLabel}>Rating</Text>
          </LinearGradient>
        </View>

        {/* Active Job Banner */}
        {activeJob && (
          <>
            <Text style={styles.sectionTitle}>Active Job</Text>
            <LinearGradient
              colors={activeJob.status === "arrived" ? ["#1A0F2E", "#0F172A"] : ["#0F2A1F", "#0F172A"]}
              style={styles.activeCard}
            >
              <View style={styles.activeCardTop}>
                <View style={[styles.activePulse, activeJob.status === "arrived" && styles.activePulseArrived]}>
                  <View style={[styles.activePulseDot, activeJob.status === "arrived" && styles.activePulseDotArrived]} />
                </View>
                <Text style={[styles.activeTitle, activeJob.status === "arrived" && { color: "#A78BFA" }]}>
                  {activeJob.status === "arrived" ? "On Site" : "In Progress"}
                </Text>
                <Text style={styles.activeTimer}>{formatElapsed(elapsed)}</Text>
              </View>
              <Text style={styles.activeClient}>
                {activeJob.client?.full_name ?? "Client"}
              </Text>
              <Text style={styles.activeAddress} numberOfLines={1}>
                {activeJob.service_address}
              </Text>
              <View style={styles.actionRow}>
                <TouchableOpacity
                  style={[styles.actionBtn, styles.actionBtnSecondary]}
                  onPress={() => callClient(activeJob.client?.phone)}
                >
                  <Ionicons name="call-outline" size={16} color="#60A5FA" />
                  <Text style={[styles.actionBtnText, { color: "#60A5FA" }]}>Call Client</Text>
                </TouchableOpacity>
                {activeJob.status === "arrived" ? (
                  <TouchableOpacity
                    style={[styles.actionBtn, { backgroundColor: "#10B981" }]}
                    onPress={() => handleStatusChange(activeJob, "in_progress")}
                  >
                    <MaterialCommunityIcons name="play" size={16} color="#FFF" />
                    <Text style={styles.actionBtnText}>Start Job</Text>
                  </TouchableOpacity>
                ) : (
                  <TouchableOpacity
                    style={styles.actionBtn}
                    onPress={() => handleStatusChange(activeJob, "completed")}
                  >
                    <MaterialCommunityIcons name="check-circle-outline" size={16} color="#FFF" />
                    <Text style={styles.actionBtnText}>Mark Complete</Text>
                  </TouchableOpacity>
                )}
              </View>
            </LinearGradient>
          </>
        )}

        {/* Next Job */}
        {nextJob && (
          <>
            <Text style={styles.sectionTitle}>Next Job</Text>
            <LinearGradient colors={["#1E293B", "#0F172A"]} style={styles.nextCard}>
              <View style={styles.nextCardHeader}>
                <View style={styles.timeBlock}>
                  <Text style={styles.timeBlockDate}>{formatJobDate(nextJob.scheduled_time)}</Text>
                  <Text style={styles.timeBlockTime}>{formatJobTime(nextJob.scheduled_time)}</Text>
                </View>
                <View style={styles.countdownBadge}>
                  <Ionicons name="time-outline" size={14} color="#F59E0B" />
                  <Text style={styles.countdownText}>{getCountdown(nextJob.scheduled_time)}</Text>
                </View>
              </View>

              {nextJob.vehicles?.slice(0, 1).map((v, i) => (
                <View key={i} style={styles.vehicleRow}>
                  <MaterialCommunityIcons
                    name={getCarIcon(v.vehicle?.body_class) as any}
                    size={22}
                    color="#60A5FA"
                  />
                  <Text style={styles.vehicleText}>
                    {v.vehicle?.make} {v.vehicle?.model}
                    {nextJob.vehicles!.length > 1 ? ` +${nextJob.vehicles!.length - 1} more` : ""}
                  </Text>
                </View>
              ))}

              <Text style={styles.nextAddress} numberOfLines={1}>
                <Ionicons name="location-outline" size={13} color="#64748B" /> {nextJob.service_address}
              </Text>

              <View style={styles.actionRow}>
                <TouchableOpacity
                  style={[styles.actionBtn, styles.actionBtnSecondary]}
                  onPress={() => callClient(nextJob.client?.phone)}
                >
                  <Ionicons name="call-outline" size={16} color="#60A5FA" />
                  <Text style={[styles.actionBtnText, { color: "#60A5FA" }]}>Call</Text>
                </TouchableOpacity>
                {nextJob.status === "pending" && (
                  <TouchableOpacity
                    style={styles.actionBtn}
                    onPress={() => handleStatusChange(nextJob, "confirmed")}
                  >
                    <MaterialCommunityIcons name="check" size={16} color="#FFF" />
                    <Text style={styles.actionBtnText}>Confirm</Text>
                  </TouchableOpacity>
                )}
                {nextJob.status === "confirmed" && (
                  <TouchableOpacity
                    style={[styles.actionBtn, { backgroundColor: "#7C3AED" }]}
                    onPress={() => handleStatusChange(nextJob, "arrived")}
                  >
                    <Ionicons name="location" size={16} color="#FFF" />
                    <Text style={styles.actionBtnText}>I've Arrived</Text>
                  </TouchableOpacity>
                )}
              </View>
            </LinearGradient>
          </>
        )}

        {/* Upcoming Today */}
        {todayJobs.length > 0 && (
          <>
            <Text style={styles.sectionTitle}>Upcoming Today</Text>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.upcomingScroll}
            >
              {todayJobs.map((appt) => {
                const color = STATUS_COLOR[appt.status] ?? "#94A3B8";
                return (
                  <LinearGradient
                    key={appt.id}
                    colors={["#1E293B", "#0F172A"]}
                    style={styles.upcomingCard}
                  >
                    <View style={[styles.upcomingStatusBar, { backgroundColor: color }]} />
                    <Text style={styles.upcomingTime}>{formatJobTime(appt.scheduled_time)}</Text>
                    <Text style={styles.upcomingClient} numberOfLines={1}>
                      {appt.client?.full_name ?? "Client"}
                    </Text>
                    <Text style={[styles.upcomingBadge, { color }]}>
                      {STATUS_LABEL[appt.status] ?? appt.status}
                    </Text>
                  </LinearGradient>
                );
              })}
            </ScrollView>
          </>
        )}

        {!nextJob && !activeJob && (
          <View style={styles.emptyState}>
            <MaterialCommunityIcons name="calendar-blank" size={48} color="#334155" />
            <Text style={styles.emptyTitle}>No upcoming jobs</Text>
            <Text style={styles.emptySub}>
              {accepting ? "You're online — clients can find you." : "Go online to start receiving bookings."}
            </Text>
          </View>
        )}

        <View style={{ height: 32 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.background },
  scroll: { paddingHorizontal: 16, paddingTop: 8 },
  loader: { flex: 1, alignItems: "center", justifyContent: "center" },

  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 20,
  },
  headerLeft: { flexDirection: "row", alignItems: "center", gap: 12 },
  avatar: {
    width: 46,
    height: 46,
    borderRadius: 23,
    backgroundColor: "#1D4ED8",
    alignItems: "center",
    justifyContent: "center",
  },
  avatarText: { color: "#FFFFFF", fontSize: 16, fontWeight: "700" },
  greeting: { fontSize: 13, color: "#64748B" },
  name: { fontSize: 20, fontWeight: "700", color: "#F1F5F9" },
  bellBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "#1E293B",
    alignItems: "center",
    justifyContent: "center",
  },

  statusCard: {
    borderRadius: 16,
    padding: 18,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 24,
    borderWidth: 1,
    borderColor: "#1E3A2F",
  },
  statusCardLeft: { flexDirection: "row", alignItems: "center", gap: 12 },
  statusDot: { width: 10, height: 10, borderRadius: 5 },
  statusLabel: { fontSize: 15, fontWeight: "700", color: "#F1F5F9" },
  statusSub: { fontSize: 12, color: "#64748B", marginTop: 2 },
  toggleBtn: {
    backgroundColor: "#334155",
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
  },
  toggleBtnOn: { backgroundColor: "#1D4ED8" },
  toggleBtnText: { color: "#FFFFFF", fontSize: 13, fontWeight: "600" },

  sectionTitle: {
    fontSize: 13,
    fontWeight: "600",
    color: "#64748B",
    letterSpacing: 0.8,
    textTransform: "uppercase",
    marginBottom: 12,
  },

  statsRow: { flexDirection: "row", gap: 10, marginBottom: 28 },
  statCard: {
    flex: 1,
    borderRadius: 14,
    paddingVertical: 16,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#1E293B",
  },
  statValue: { fontSize: 20, fontWeight: "700", color: "#F1F5F9", marginTop: 6 },
  statLabel: { fontSize: 11, color: "#64748B", marginTop: 2 },

  activeCard: {
    borderRadius: 16,
    padding: 20,
    marginBottom: 28,
    borderWidth: 1,
    borderColor: "#1E3A2F",
  },
  activeCardTop: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 12 },
  activePulse: {
    width: 18,
    height: 18,
    borderRadius: 9,
    backgroundColor: "rgba(16,185,129,0.2)",
    alignItems: "center",
    justifyContent: "center",
  },
  activePulseArrived: { backgroundColor: "rgba(167,139,250,0.2)" },
  activePulseDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: "#10B981" },
  activePulseDotArrived: { backgroundColor: "#A78BFA" },
  activeTitle: { flex: 1, fontSize: 15, fontWeight: "700", color: "#10B981" },
  activeTimer: { fontSize: 20, fontWeight: "700", color: "#F1F5F9", fontVariant: ["tabular-nums"] },
  activeClient: { fontSize: 18, fontWeight: "700", color: "#F1F5F9", marginBottom: 4 },
  activeAddress: { fontSize: 13, color: "#64748B", marginBottom: 16 },

  nextCard: {
    borderRadius: 16,
    padding: 20,
    marginBottom: 28,
    borderWidth: 1,
    borderColor: "#1E293B",
  },
  nextCardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 16,
  },
  timeBlock: {},
  timeBlockDate: { fontSize: 13, color: "#94A3B8", marginBottom: 2 },
  timeBlockTime: { fontSize: 24, fontWeight: "700", color: "#F1F5F9" },
  countdownBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: "rgba(245,158,11,0.12)",
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  countdownText: { fontSize: 13, fontWeight: "600", color: "#F59E0B" },
  vehicleRow: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 8 },
  vehicleText: { fontSize: 15, color: "#F1F5F9", fontWeight: "500" },
  nextAddress: { fontSize: 13, color: "#64748B", marginBottom: 16 },

  actionRow: { flexDirection: "row", gap: 10 },
  actionBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    backgroundColor: "#2563EB",
    paddingVertical: 10,
    borderRadius: 10,
  },
  actionBtnSecondary: { backgroundColor: "rgba(96,165,250,0.12)" },
  actionBtnText: { color: "#FFFFFF", fontSize: 14, fontWeight: "600" },

  upcomingScroll: { paddingBottom: 4, paddingRight: 4, gap: 10, marginBottom: 28 },
  upcomingCard: {
    width: 130,
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: "#1E293B",
    overflow: "hidden",
  },
  upcomingStatusBar: { position: "absolute", top: 0, left: 0, right: 0, height: 3 },
  upcomingTime: { fontSize: 16, fontWeight: "700", color: "#F1F5F9", marginTop: 6, marginBottom: 4 },
  upcomingClient: { fontSize: 12, color: "#94A3B8", marginBottom: 8 },
  upcomingBadge: { fontSize: 11, fontWeight: "600" },

  emptyState: { alignItems: "center", paddingVertical: 48, gap: 10 },
  emptyTitle: { fontSize: 16, fontWeight: "600", color: "#475569" },
  emptySub: { fontSize: 13, color: "#334155", textAlign: "center", maxWidth: 260 },
});
