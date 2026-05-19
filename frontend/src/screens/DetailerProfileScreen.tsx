import { Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
import { useFocusEffect } from "@react-navigation/native";
import { LinearGradient } from "expo-linear-gradient";
import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Button from "../components/Button";
import RoleSwitcher from "../components/RoleSwitcher";
import SectionHeader from "../components/SectionHeader";
import { APP_CONFIG } from "../config/app.config";
import { useAppNavigation } from "../hooks/useAppNavigation";
import { useMe } from "../hooks/useMe";
import type { SwitchableRole } from "../services/active-role.service";
import { logout } from "../services/auth.service";
import {
  getMyDetailerProfile,
  toggleAcceptingBookings,
} from "../services/detailer-private.service";
import { Colors } from "../theme/colors";
import { formatPrice, getInitials, getMemberStatus } from "../utils/formatters";

interface MenuRow { icon: string; label: string; value?: string; onPress: () => void; danger?: boolean; }

function MenuOption({ icon, label, value, onPress, danger }: MenuRow) {
  return (
    <TouchableOpacity style={styles.menuRow} onPress={onPress} activeOpacity={0.7}>
      <View style={[styles.menuIcon, danger && styles.menuIconDanger]}>
        <Ionicons name={icon as any} size={18} color={danger ? "#EF4444" : "#60A5FA"} />
      </View>
      <Text style={[styles.menuLabel, danger && styles.menuLabelDanger]}>{label}</Text>
      {value && <Text style={styles.menuValue}>{value}</Text>}
      {!danger && <Ionicons name="chevron-forward" size={16} color="#334155" />}
    </TouchableOpacity>
  );
}

export default function DetailerProfileScreen() {
  const navigation = useAppNavigation();

  // User name/email come from the Profile Hub (ADR-002b). Detailer-specific
  // stats (earnings, specialties, radius) still go through the legacy
  // /api/v1/detailers/me endpoint — Phase 5 promotes those into the Hub's
  // `provider` block.
  const meQuery = useMe(["profile"]);
  const userName  = meQuery.data?.data.profile?.full_name ?? undefined;
  const userEmail = meQuery.data?.data.user.email ?? undefined;

  const [accepting, setAccepting] = useState(false);
  const [togglingStatus, setTogglingStatus] = useState(false);
  const [stats, setStats] = useState({ earnings: 0, jobs: 0, rating: 0, reviews: 0, years: 0, radius: 10, specialties: [] as string[], since: "" });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  async function loadData() {
    try {
      const [profile] = await Promise.all([
        getMyDetailerProfile(),
        meQuery.refetch(),
      ]);
      setAccepting(profile.is_accepting_bookings);
      setStats({
        earnings: profile.total_earnings_cents, jobs: profile.total_services,
        rating: profile.average_rating ?? 0, reviews: profile.total_reviews,
        years: profile.years_of_experience ?? 0, radius: profile.service_radius_miles,
        specialties: profile.specialties, since: profile.created_at,
      });
    } catch {
      Alert.alert("Error", "Could not load your profile.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useFocusEffect(useCallback(() => { setLoading(true); loadData(); }, []));

  async function handleToggleStatus(val: boolean) {
    setTogglingStatus(true);
    try {
      await toggleAcceptingBookings(val);
      setAccepting(val);
    } catch {
      Alert.alert("Error", "Could not update your status.");
    } finally {
      setTogglingStatus(false);
    }
  }

  async function handleSignOut() {
    Alert.alert("Sign Out", "Are you sure you want to sign out?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Sign Out",
        style: "destructive",
        onPress: async () => {
          await logout();
          navigation.reset({ index: 0, routes: [{ name: "Login" }] });
        },
      },
    ]);
  }

  const memberBadge = getMemberStatus(stats.jobs);

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
          <RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadData(); }} tintColor={Colors.primary} />
        }
      >
        {/* Profile Header */}
        <LinearGradient colors={["#1E3A5F", "#0F172A"]} style={styles.profileCard}>
          <View style={styles.avatarWrap}>
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>{getInitials(userName)}</Text>
            </View>
            <View style={styles.verifiedBadge}>
              <MaterialCommunityIcons name="check-decagram" size={18} color="#60A5FA" />
            </View>
          </View>
          <Text style={styles.profileName}>{userName ?? "—"}</Text>
          <Text style={styles.profileEmail}>{userEmail ?? "—"}</Text>
          <View style={styles.memberRow}>
            <View style={[styles.memberBadge, { borderColor: memberBadge.color }]}>
              <MaterialCommunityIcons name="medal" size={13} color={memberBadge.color} />
              <Text style={[styles.memberText, { color: memberBadge.color }]}>{memberBadge.label} Pro</Text>
            </View>
          </View>
          <View style={styles.ratingRow}>
            <MaterialCommunityIcons name="star" size={18} color="#F59E0B" />
            <Text style={styles.ratingValue}>{stats.rating > 0 ? stats.rating.toFixed(1) : "New"}</Text>
            <Text style={styles.ratingReviews}>{stats.reviews > 0 ? `(${stats.reviews} reviews)` : "No reviews yet"}</Text>
          </View>
        </LinearGradient>

        {/* Role switcher (Phase 6, ADR-003) — hidden for single-role users. */}
        {meQuery.data && meQuery.data.data.user.available_roles.length > 1 && (
          <View style={styles.roleSwitcherWrapper}>
            <RoleSwitcher
              availableRoles={meQuery.data.data.user.available_roles}
              currentRole={(meQuery.data.data.user.role as SwitchableRole) ?? "detailer"}
            />
          </View>
        )}

        {/* Stats */}
        <View style={styles.statsRow}>
          <View style={styles.statCell}>
            <Text style={styles.statValue}>{formatPrice(stats.earnings)}</Text>
            <Text style={styles.statLabel}>Total Earned</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statCell}>
            <Text style={styles.statValue}>{stats.jobs}</Text>
            <Text style={styles.statLabel}>Jobs Done</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statCell}>
            <Text style={styles.statValue}>{stats.years}yr</Text>
            <Text style={styles.statLabel}>Experience</Text>
          </View>
        </View>

        {/* Status Toggle */}
        <LinearGradient colors={["#1E293B", "#0F172A"]} style={styles.statusCard}>
          <View>
            <Text style={styles.statusLabel}>Accept Bookings</Text>
            <Text style={styles.statusSub}>{accepting ? "You appear in client matching" : "Hidden from new clients"}</Text>
          </View>
          {togglingStatus
            ? <ActivityIndicator size="small" color={Colors.primary} />
            : <Switch value={accepting} onValueChange={handleToggleStatus} trackColor={{ false: "#334155", true: "#1D4ED8" }} thumbColor={accepting ? "#60A5FA" : "#64748B"} />}
        </LinearGradient>

        {/* Business */}
        <SectionHeader title="Business" style={{ marginTop: 8 }} />
        <LinearGradient colors={["#1E293B", "#0F172A"]} style={styles.menuCard}>
          <MenuOption icon="briefcase-outline" label="Provider hub" onPress={() => navigation.navigate("ProviderHub")} />
          <View style={styles.menuDivider} />
          <MenuOption icon="construct-outline" label="My Services" onPress={() => navigation.navigate("DetailerServices")} />
          <View style={styles.menuDivider} />
          <MenuOption icon="location-outline" label="Service Radius" value={`${stats.radius} mi`} onPress={() => navigation.navigate("DetailerServices")} />
          <View style={styles.menuDivider} />
          <MenuOption icon="ribbon-outline" label="Specialties" value={`${stats.specialties.length} selected`} onPress={() => navigation.navigate("DetailerServices")} />
        </LinearGradient>

        {stats.specialties.length > 0 && (
          <View style={styles.specialtiesWrap}>
            {stats.specialties.map((s) => (
              <View key={s} style={styles.specialtyChip}>
                <Text style={styles.specialtyText}>{s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}</Text>
              </View>
            ))}
          </View>
        )}

        {/* Support */}
        <SectionHeader title="Support" style={{ marginTop: 4 }} />
        <LinearGradient colors={["#1E293B", "#0F172A"]} style={styles.menuCard}>
          <MenuOption icon="mail-outline" label="Contact Support" value={APP_CONFIG.supportEmail} onPress={() => {}} />
          <View style={styles.menuDivider} />
          <MenuOption icon="document-text-outline" label="Terms of Service" onPress={() => {}} />
          <View style={styles.menuDivider} />
          <MenuOption icon="shield-checkmark-outline" label="Privacy Policy" onPress={() => {}} />
        </LinearGradient>

        <View style={{ paddingHorizontal: 20, marginTop: 8 }}>
          <Button title="Sign Out" onPress={handleSignOut} variant="danger" size="lg" fullWidth icon="log-out-outline" />
        </View>

        <View style={{ height: 40 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.background },
  scroll: { paddingHorizontal: 20, paddingTop: 12 },
  loader: { flex: 1, alignItems: "center", justifyContent: "center" },
  profileCard: { borderRadius: 20, padding: 24, alignItems: "center", marginBottom: 16 },
  avatarWrap: { position: "relative", marginBottom: 14 },
  avatar: {
    width: 80, height: 80, borderRadius: 40, backgroundColor: "#1D4ED8",
    alignItems: "center", justifyContent: "center", borderWidth: 3, borderColor: Colors.primary,
  },
  avatarText: { fontSize: 28, fontWeight: "700", color: "#FFFFFF" },
  verifiedBadge: { position: "absolute", bottom: 0, right: 0, backgroundColor: "#0F172A", borderRadius: 10, padding: 1 },
  profileName: { fontSize: 22, fontWeight: "700", color: "#F1F5F9", marginBottom: 4 },
  profileEmail: { fontSize: 13, color: "#64748B", marginBottom: 14 },
  memberRow: { flexDirection: "row", alignItems: "center", gap: 12, marginBottom: 14 },
  memberBadge: {
    flexDirection: "row", alignItems: "center", gap: 4,
    borderWidth: 1, borderRadius: 12, paddingHorizontal: 10, paddingVertical: 4,
  },
  memberText: { fontSize: 12, fontWeight: "600" },
  ratingRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  ratingValue: { fontSize: 18, fontWeight: "700", color: "#F1F5F9" },
  ratingReviews: { fontSize: 13, color: "#64748B" },
  roleSwitcherWrapper: { marginBottom: 16 },
  statsRow: {
    flexDirection: "row", backgroundColor: "#1E293B", borderRadius: 16,
    paddingVertical: 18, marginBottom: 16, borderWidth: 1, borderColor: "#262F3F",
  },
  statCell: { flex: 1, alignItems: "center" },
  statDivider: { width: 1, backgroundColor: "#334155", marginVertical: 4 },
  statValue: { fontSize: 20, fontWeight: "700", color: "#F1F5F9" },
  statLabel: { fontSize: 11, color: "#64748B", marginTop: 3 },
  statusCard: {
    borderRadius: 14, padding: 18, flexDirection: "row", alignItems: "center",
    justifyContent: "space-between", marginBottom: 16,
    borderWidth: 1, borderColor: "#262F3F",
  },
  statusLabel: { fontSize: 15, fontWeight: "600", color: "#F1F5F9" },
  statusSub: { fontSize: 12, color: "#64748B", marginTop: 2 },
  menuCard: { borderRadius: 14, marginBottom: 16, overflow: "hidden", borderWidth: 1, borderColor: "#1E293B" },
  menuRow: { flexDirection: "row", alignItems: "center", gap: 14, paddingHorizontal: 16, paddingVertical: 14 },
  menuIcon: { width: 34, height: 34, borderRadius: 10, backgroundColor: "rgba(96,165,250,0.1)", alignItems: "center", justifyContent: "center" },
  menuIconDanger: { backgroundColor: "rgba(239,68,68,0.1)" },
  menuLabel: { flex: 1, fontSize: 15, color: "#E2E8F0", fontWeight: "500" },
  menuLabelDanger: { color: "#EF4444" },
  menuValue: { fontSize: 13, color: "#475569", marginRight: 6 },
  menuDivider: { height: 1, backgroundColor: "#1E293B", marginLeft: 64 },
  specialtiesWrap: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: -8, marginBottom: 16 },
  specialtyChip: {
    backgroundColor: "rgba(96,165,250,0.1)", borderRadius: 20,
    paddingHorizontal: 12, paddingVertical: 6, borderWidth: 1, borderColor: "rgba(96,165,250,0.2)",
  },
  specialtyText: { fontSize: 12, color: "#60A5FA", fontWeight: "500" },
});
