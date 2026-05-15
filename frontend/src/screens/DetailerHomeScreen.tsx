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
import Button from "../components/Button";
import Card from "../components/Card";
import EmptyState from "../components/EmptyState";
import SectionHeader from "../components/SectionHeader";
import StatusBadge from "../components/StatusBadge";
import { useAppNavigation } from "../hooks/useAppNavigation";
import { useAppointmentSocket } from "../hooks/useAppointmentSocket";
import { acceptRide, declineRide } from "../services/rides.service";
import { useAuthStore } from "../store/authStore";
import { WS_BASE_URL } from "../services/api";
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

function formatJobTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
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

interface OfferCard {
  appointmentId: string;
  assignmentId: string;
  expiresAt: string;
}

export default function DetailerHomeScreen() {
  const navigation = useAppNavigation();
  const token = useAuthStore((s) => s.token);

  const [userName, setUserName] = useState<string | undefined>();
  const [userId, setUserId] = useState<string | null>(null);
  const [accepting, setAccepting] = useState(false);
  const [togglingStatus, setTogglingStatus] = useState(false);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [stats, setStats] = useState({ earnings: 0, jobs: 0, rating: 0 });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const [offer, setOffer] = useState<OfferCard | null>(null);
  const [offerCountdown, setOfferCountdown] = useState(15);
  const offerTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const personalWsRef = useRef<WebSocket | null>(null);
  useEffect(() => {
    if (!userId || !token) return;
    const ws = new WebSocket(`${WS_BASE_URL}/ws/user/${userId}?token=${token}`);
    personalWsRef.current = ws;
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data as string);
        if (msg.type === "offer") {
          setOffer({ appointmentId: msg.appointment_id, assignmentId: msg.assignment_id, expiresAt: msg.offer_expires_at });
          setOfferCountdown(15);
          if (offerTimerRef.current) clearInterval(offerTimerRef.current);
          offerTimerRef.current = setInterval(() => {
            setOfferCountdown((n) => {
              if (n <= 1) { clearInterval(offerTimerRef.current!); setOffer(null); return 0; }
              return n - 1;
            });
          }, 1000);
        }
      } catch { /* ignore */ }
    };
    return () => { ws.close(); if (offerTimerRef.current) clearInterval(offerTimerRef.current); };
  }, [userId, token]);

  const activeJob = appointments.find((a) => a.status === "arrived" || a.status === "in_progress");
  const nextJob = appointments.find(
    (a) => (a.status === "confirmed" || a.status === "pending") && new Date(a.scheduled_time) > new Date(),
  );

  const wsJobId = activeJob?.id ?? null;
  const { sendLocationUpdate } = useAppointmentSocket({
    appointmentId: wsJobId,
    onStatusChange: useCallback(
      (newStatus: string) => {
        setAppointments((prev) => prev.map((a) => (a.id === wsJobId ? { ...a, status: newStatus } : a)));
      },
      [wsJobId],
    ),
  });

  const locationIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(() => {
    if (!activeJob) {
      if (locationIntervalRef.current) { clearInterval(locationIntervalRef.current); locationIntervalRef.current = null; }
      return;
    }
    const pushLocation = async () => {
      try {
        const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
        sendLocationUpdate(pos.coords.latitude, pos.coords.longitude);
      } catch { /* skip */ }
    };
    pushLocation();
    locationIntervalRef.current = setInterval(pushLocation, 5_000);
    return () => { if (locationIntervalRef.current) { clearInterval(locationIntervalRef.current); locationIntervalRef.current = null; } };
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

  const handleAcceptOffer = async () => {
    if (!offer) return;
    try {
      await acceptRide(offer.appointmentId);
      setOffer(null);
      if (offerTimerRef.current) clearInterval(offerTimerRef.current);
      loadData();
    } catch { /* show alert in production */ }
  };

  const handleDeclineOffer = async () => {
    if (!offer) return;
    try { await declineRide(offer.appointmentId); } catch { /* ignore */ }
    finally { setOffer(null); if (offerTimerRef.current) clearInterval(offerTimerRef.current); }
  };

  async function loadData() {
    try {
      const [user, profile, appts] = await Promise.all([
        getUserProfile(), getMyDetailerProfile(), getMyAppointments(1, 50),
      ]);
      setUserName(user.full_name);
      setUserId(user.id);
      setAccepting(profile.is_accepting_bookings);
      setStats({ earnings: profile.total_earnings_cents, jobs: profile.total_services, rating: profile.average_rating ?? 0 });
      setAppointments(appts.items as Appointment[]);
    } catch { /* non-critical */ }
    finally { setLoading(false); setRefreshing(false); }
  }

  useFocusEffect(useCallback(() => { setLoading(true); loadData(); }, []));

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
    Alert.alert("Update Job Status", `Mark this job as "${STATUS_LABEL[newStatus] ?? newStatus}"?`, [
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
    ]);
  }

  function callClient(phone?: string) {
    if (!phone) { Alert.alert("No phone", "Client phone not available."); return; }
    Linking.openURL(`tel:${phone}`);
  }

  if (loading) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.loader}><ActivityIndicator size="large" color={Colors.primary} /></View>
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
            tintColor={Colors.primary}
          />
        }
      >
        {/* ── HEADER ──────────────────────────────────────────────────── */}
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

        {/* ── OFFER CARD ──────────────────────────────────────────────── */}
        {offer && (
          <Card style={{ marginBottom: 16, borderColor: "#F59E0B44" }}>
            <View style={styles.offerHeader}>
              <View style={styles.offerBadge}>
                <Ionicons name="flash" size={14} color="#0B0F19" />
                <Text style={styles.offerBadgeText}>NEW OFFER</Text>
              </View>
              <View style={styles.countdownPill}>
                <Text style={[styles.countdownText, offerCountdown <= 5 && { color: "#EF4444" }]}>
                  {offerCountdown}s
                </Text>
              </View>
            </View>
            <Text style={styles.offerTitle}>Incoming Job Request</Text>
            <Text style={styles.offerSub}>ID: {offer.appointmentId.slice(0, 8).toUpperCase()}</Text>
            <View style={styles.offerBtns}>
              <Button
                title="Decline"
                onPress={handleDeclineOffer}
                variant="danger"
                size="md"
                icon="close"
                style={{ flex: 1 }}
              />
              <Button
                title="Accept"
                onPress={handleAcceptOffer}
                variant="primary"
                size="md"
                icon="checkmark"
                style={{ flex: 1 }}
              />
            </View>
          </Card>
        )}

        {/* ── ONLINE TOGGLE ───────────────────────────────────────────── */}
        <LinearGradient
          colors={accepting ? ["#1E3A2F", "#0F2A1F"] : ["#2A1E1E", "#1A0F0F"]}
          style={styles.statusCard}
        >
          <View style={styles.statusCardLeft}>
            <View style={[styles.statusDot, { backgroundColor: accepting ? "#10B981" : "#EF4444" }]} />
            <View>
              <Text style={styles.statusLabel}>{accepting ? "You're Online" : "You're Offline"}</Text>
              <Text style={styles.statusSub}>{accepting ? "Clients can book you" : "Hidden from matching"}</Text>
            </View>
          </View>
          <Button
            title={accepting ? "Go Offline" : "Go Online"}
            onPress={handleToggleStatus}
            variant={accepting ? "secondary" : "primary"}
            size="sm"
            loading={togglingStatus}
          />
        </LinearGradient>

        {/* ── TODAY'S SUMMARY ─────────────────────────────────────────── */}
        <SectionHeader title="Today's Summary" style={{ marginTop: 24 }} />
        <View style={styles.statsRow}>
          {[
            { icon: "currency-usd", color: "#10B981", value: formatPrice(stats.earnings), label: "Earned" },
            { icon: "briefcase-check", color: Colors.primary, value: String(stats.jobs), label: "Total Jobs" },
            { icon: "star", color: "#F59E0B", value: stats.rating > 0 ? stats.rating.toFixed(1) : "—", label: "Rating" },
          ].map(({ icon, color, value, label }) => (
            <LinearGradient key={label} colors={["#1E293B", "#0F172A"]} style={styles.statCard}>
              <MaterialCommunityIcons name={icon as any} size={22} color={color} />
              <Text style={styles.statValue}>{value}</Text>
              <Text style={styles.statLabel}>{label}</Text>
            </LinearGradient>
          ))}
        </View>

        {/* ── ACTIVE JOB ──────────────────────────────────────────────── */}
        {activeJob && (
          <>
            <SectionHeader title="Active Job" style={{ marginTop: 4 }} />
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
              <Text style={styles.activeClient}>{activeJob.client?.full_name ?? "Client"}</Text>
              <Text style={styles.activeAddress} numberOfLines={1}>{activeJob.service_address}</Text>
              <View style={styles.actionRow}>
                <Button
                  title="Call Client"
                  onPress={() => callClient(activeJob.client?.phone)}
                  variant="secondary"
                  size="md"
                  icon="call-outline"
                  style={{ flex: 1 }}
                />
                {activeJob.status === "arrived" ? (
                  <Button
                    title="Start Job"
                    onPress={() => handleStatusChange(activeJob, "in_progress")}
                    variant="primary"
                    size="md"
                    icon="play"
                    style={{ flex: 1, backgroundColor: "#10B981" }}
                  />
                ) : (
                  <Button
                    title="Mark Complete"
                    onPress={() => handleStatusChange(activeJob, "completed")}
                    variant="primary"
                    size="md"
                    icon="checkmark-circle-outline"
                    style={{ flex: 1 }}
                  />
                )}
              </View>
            </LinearGradient>
          </>
        )}

        {/* ── NEXT JOB ────────────────────────────────────────────────── */}
        {nextJob && (
          <>
            <SectionHeader title="Next Job" style={{ marginTop: 4 }} />
            <LinearGradient colors={["#1E293B", "#0F172A"]} style={styles.nextCard}>
              <View style={styles.nextCardHeader}>
                <View>
                  <Text style={styles.timeBlockDate}>{formatJobDate(nextJob.scheduled_time)}</Text>
                  <Text style={styles.timeBlockTime}>{formatJobTime(nextJob.scheduled_time)}</Text>
                </View>
                <View style={styles.countdownBadge}>
                  <Ionicons name="time-outline" size={14} color="#F59E0B" />
                  <Text style={styles.jobCountdownText}>{getCountdown(nextJob.scheduled_time)}</Text>
                </View>
              </View>

              <StatusBadge status={nextJob.status} size="md" style={{ marginBottom: 12 }} />

              {nextJob.vehicles?.slice(0, 1).map((v, i) => (
                <View key={i} style={styles.vehicleRow}>
                  <MaterialCommunityIcons name={getCarIcon(v.vehicle?.body_class) as any} size={22} color="#60A5FA" />
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
                <Button
                  title="Call"
                  onPress={() => callClient(nextJob.client?.phone)}
                  variant="secondary"
                  size="md"
                  icon="call-outline"
                  style={{ flex: 1 }}
                />
                {nextJob.status === "pending" && (
                  <Button
                    title="Confirm"
                    onPress={() => handleStatusChange(nextJob, "confirmed")}
                    variant="primary"
                    size="md"
                    icon="checkmark"
                    style={{ flex: 1 }}
                  />
                )}
                {nextJob.status === "confirmed" && (
                  <Button
                    title="I've Arrived"
                    onPress={() => handleStatusChange(nextJob, "arrived")}
                    variant="primary"
                    size="md"
                    icon="location"
                    style={{ flex: 1, backgroundColor: "#7C3AED" }}
                  />
                )}
              </View>
            </LinearGradient>
          </>
        )}

        {/* ── UPCOMING TODAY ──────────────────────────────────────────── */}
        {todayJobs.length > 0 && (
          <>
            <SectionHeader title="Upcoming Today" style={{ marginTop: 4 }} />
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.upcomingScroll}>
              {todayJobs.map((appt) => (
                <LinearGradient key={appt.id} colors={["#1E293B", "#0F172A"]} style={styles.upcomingCard}>
                  <StatusBadge status={appt.status} style={styles.upcomingBadge} />
                  <Text style={styles.upcomingTime}>{formatJobTime(appt.scheduled_time)}</Text>
                  <Text style={styles.upcomingClient} numberOfLines={1}>{appt.client?.full_name ?? "Client"}</Text>
                </LinearGradient>
              ))}
            </ScrollView>
          </>
        )}

        {!nextJob && !activeJob && (
          <EmptyState
            icon="calendar-blank"
            title="No upcoming jobs"
            subtitle={accepting ? "You're online — clients can find you." : "Go online to start receiving bookings."}
            dashed={false}
            style={{ marginTop: 16 }}
          />
        )}

        <View style={{ height: 32 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.background },
  scroll: { paddingHorizontal: 20, paddingTop: 8 },
  loader: { flex: 1, alignItems: "center", justifyContent: "center" },

  header: {
    flexDirection: "row", alignItems: "center",
    justifyContent: "space-between", marginBottom: 20,
  },
  headerLeft: { flexDirection: "row", alignItems: "center", gap: 12 },
  avatar: {
    width: 52, height: 52, borderRadius: 26,
    backgroundColor: "#1D4ED8", alignItems: "center", justifyContent: "center",
  },
  avatarText: { color: "#FFFFFF", fontSize: 18, fontWeight: "700" },
  greeting: { fontSize: 13, color: "#64748B" },
  name: { fontSize: 20, fontWeight: "700", color: "#F1F5F9" },
  bellBtn: {
    width: 40, height: 40, borderRadius: 20,
    backgroundColor: "#1E293B", alignItems: "center", justifyContent: "center",
  },

  offerHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 10 },
  offerBadge: {
    flexDirection: "row", alignItems: "center", gap: 4,
    backgroundColor: "#F59E0B", borderRadius: 20, paddingHorizontal: 10, paddingVertical: 4,
  },
  offerBadgeText: { color: "#0B0F19", fontWeight: "800", fontSize: 11 },
  countdownPill: { backgroundColor: "#0F172A", borderRadius: 20, paddingHorizontal: 12, paddingVertical: 4 },
  countdownText: { color: "#F8FAFC", fontWeight: "700", fontSize: 16 },
  offerTitle: { color: "#F8FAFC", fontSize: 17, fontWeight: "700", marginBottom: 4 },
  offerSub: { color: "#64748B", fontSize: 12, marginBottom: 16 },
  offerBtns: { flexDirection: "row", gap: 12 },

  statusCard: {
    borderRadius: 16, padding: 18,
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    marginBottom: 4, borderWidth: 1, borderColor: "#1E3A2F",
  },
  statusCardLeft: { flexDirection: "row", alignItems: "center", gap: 12 },
  statusDot: { width: 10, height: 10, borderRadius: 5 },
  statusLabel: { fontSize: 15, fontWeight: "700", color: "#F1F5F9" },
  statusSub: { fontSize: 12, color: "#64748B", marginTop: 2 },

  statsRow: { flexDirection: "row", gap: 10, marginBottom: 4 },
  statCard: {
    flex: 1, borderRadius: 14, paddingVertical: 16,
    alignItems: "center", borderWidth: 1, borderColor: "#1E293B",
  },
  statValue: { fontSize: 20, fontWeight: "700", color: "#F1F5F9", marginTop: 6 },
  statLabel: { fontSize: 11, color: "#64748B", marginTop: 2 },

  activeCard: {
    borderRadius: 16, padding: 20, marginBottom: 4,
    borderWidth: 1, borderColor: "#1E3A2F",
  },
  activeCardTop: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 12 },
  activePulse: {
    width: 18, height: 18, borderRadius: 9,
    backgroundColor: "rgba(16,185,129,0.2)", alignItems: "center", justifyContent: "center",
  },
  activePulseArrived: { backgroundColor: "rgba(167,139,250,0.2)" },
  activePulseDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: "#10B981" },
  activePulseDotArrived: { backgroundColor: "#A78BFA" },
  activeTitle: { flex: 1, fontSize: 15, fontWeight: "700", color: "#10B981" },
  activeTimer: { fontSize: 20, fontWeight: "700", color: "#F1F5F9", fontVariant: ["tabular-nums"] },
  activeClient: { fontSize: 18, fontWeight: "700", color: "#F1F5F9", marginBottom: 4 },
  activeAddress: { fontSize: 13, color: "#64748B", marginBottom: 16 },

  nextCard: {
    borderRadius: 16, padding: 20, marginBottom: 4,
    borderWidth: 1, borderColor: "#1E293B",
  },
  nextCardHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 },
  timeBlockDate: { fontSize: 13, color: "#94A3B8", marginBottom: 2 },
  timeBlockTime: { fontSize: 24, fontWeight: "700", color: "#F1F5F9" },
  countdownBadge: {
    flexDirection: "row", alignItems: "center", gap: 4,
    backgroundColor: "rgba(245,158,11,0.12)", paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12,
  },
  jobCountdownText: { fontSize: 13, fontWeight: "600", color: "#F59E0B" },
  vehicleRow: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 8 },
  vehicleText: { fontSize: 15, color: "#F1F5F9", fontWeight: "500" },
  nextAddress: { fontSize: 13, color: "#64748B", marginBottom: 16 },

  actionRow: { flexDirection: "row", gap: 10 },

  upcomingScroll: { paddingBottom: 4, paddingRight: 4, gap: 10, marginBottom: 4 },
  upcomingCard: {
    width: 130, borderRadius: 14, padding: 14,
    borderWidth: 1, borderColor: "#1E293B", overflow: "hidden",
  },
  upcomingBadge: { marginBottom: 8 },
  upcomingTime: { fontSize: 16, fontWeight: "700", color: "#F1F5F9", marginBottom: 4 },
  upcomingClient: { fontSize: 12, color: "#94A3B8" },
});
