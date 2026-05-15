import { Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
import { useFocusEffect } from "@react-navigation/native";
import { LinearGradient } from "expo-linear-gradient";
import React, { useCallback } from "react";
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
import Button from "../components/Button";
import { APP_CONFIG } from "../config/app.config";
import { useMe } from "../hooks/useMe";
import { Colors } from "../theme/colors";
import { clearAuthTokens } from "../utils/storage";

export default function ProfileScreen({ navigation }: any) {
  // Profile Hub (ADR-002b): one call gives us name + verification badges
  // + stats (washes total, vehicles total, member-since). Replaces the
  // three legacy fetches (getUserProfile, getMyVehicles, getMyAppointments).
  const meQuery = useMe(["profile", "stats"]);

  // Refetch when the screen regains focus — the Hub is staleTime 5 min so
  // most navigations hit the cache, but explicit refocus picks up edits
  // made elsewhere in the app.
  useFocusEffect(
    useCallback(() => {
      meQuery.refetch();
    }, [meQuery]),
  );

  const hub = meQuery.data?.data;
  const user = hub?.user;
  const profile = hub?.profile;
  const stats = hub?.stats;
  const badges = hub?.verification_badges;

  const completedWashes = stats?.total_bookings ?? 0;
  const vehiclesTotal = stats?.vehicles_total ?? 0;

  const getMemberStatus = (washes: number) => {
    if (washes >= 15) return { label: "Platinum", color: "#E2E8F0" };
    if (washes >= 8) return { label: "Gold", color: "#F59E0B" };
    if (washes >= 3) return { label: "Silver", color: "#94A3B8" };
    return { label: "Bronze", color: "#B45309" };
  };

  const getInitials = (fullName: string | undefined) => {
    if (!fullName) return "U";
    return fullName.split(" ").map((n: string) => n[0]).join("").slice(0, 2).toUpperCase();
  };

  const getMemberSince = (memberSince: string | null | undefined) => {
    if (!memberSince) return "—";
    return new Date(memberSince).toLocaleDateString("en-US", { month: "long", year: "numeric" });
  };

  const handleLogout = () => {
    Alert.alert("Sign Out", "Are you sure you want to sign out?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Sign Out",
        style: "destructive",
        onPress: async () => {
          await clearAuthTokens();
          navigation.reset({ index: 0, routes: [{ name: "Login" }] });
        },
      },
    ]);
  };

  const handleDeleteAccount = () => {
    Alert.alert(
      "Delete Account",
      "This will permanently delete your account and all associated data. This action cannot be undone.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete Account",
          style: "destructive",
          onPress: () => Alert.alert("Contact Support", `To delete your account, please contact us at ${APP_CONFIG.supportEmail}`),
        },
      ],
    );
  };

  const memberStatus = getMemberStatus(completedWashes);

  const MenuOption = ({ icon, title, subtitle, onPress, color = "#94A3B8", badge, isLast = false }: any) => (
    <TouchableOpacity
      style={[styles.menuItem, isLast && { borderBottomWidth: 0 }]}
      onPress={onPress}
    >
      <View style={[styles.iconBox, { backgroundColor: `${color}18` }]}>
        <Ionicons name={icon} size={20} color={color} />
      </View>
      <View style={styles.menuText}>
        <Text style={styles.menuTitle}>{title}</Text>
        {subtitle && <Text style={styles.menuSubtitle}>{subtitle}</Text>}
      </View>
      {badge && (
        <View style={[styles.badge, { backgroundColor: `${color}20` }]}>
          <Text style={[styles.badgeText, { color }]}>{badge}</Text>
        </View>
      )}
      <Ionicons name="chevron-forward" size={16} color="#334155" style={{ marginLeft: 6 }} />
    </TouchableOpacity>
  );

  if (meQuery.isLoading) {
    return (
      <View style={[styles.container, { justifyContent: "center" }]}>
        <ActivityIndicator size="large" color={Colors.primary} />
      </View>
    );
  }

  if (meQuery.isError && !hub) {
    return (
      <View style={[styles.container, { justifyContent: "center", padding: 20 }]}>
        <Text style={{ color: "#94A3B8", textAlign: "center", marginBottom: 16 }}>
          Could not load your profile. Please try again.
        </Text>
        <Button title="Retry" onPress={() => meQuery.refetch()} variant="primary" />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>My Profile</Text>

          <View style={styles.profileCard}>
            <LinearGradient colors={["#3B82F620", "transparent"]} style={StyleSheet.absoluteFill} />

            <View style={styles.avatarWrapper}>
              <View style={styles.avatarInitials}>
                <Text style={styles.initialsText}>{getInitials(profile?.full_name ?? undefined)}</Text>
              </View>
              <TouchableOpacity
                style={styles.editBadge}
                onPress={() => navigation.navigate("EditProfile")}
              >
                <Ionicons name="pencil" size={14} color="white" />
              </TouchableOpacity>
            </View>

            <View style={styles.nameRow}>
              <Text style={styles.userName}>{profile?.full_name || "User"}</Text>
              {badges?.email && (
                <Ionicons name="checkmark-circle" size={18} color="#10B981" style={{ marginLeft: 6 }} />
              )}
            </View>
            <Text style={styles.userEmail}>{user?.email || "—"}</Text>
            <Text style={styles.memberSince}>Member since {getMemberSince(stats?.member_since)}</Text>

            <View style={styles.tagsRow}>
              <View style={[styles.tag, { borderColor: memberStatus.color + "50" }]}>
                <MaterialCommunityIcons name="star-circle" size={13} color={memberStatus.color} />
                <Text style={[styles.tagText, { color: memberStatus.color }]}>{memberStatus.label}</Text>
              </View>
              {badges?.email && (
                <View style={[styles.tag, { borderColor: "#10B98150" }]}>
                  <Ionicons name="shield-checkmark" size={13} color="#10B981" />
                  <Text style={[styles.tagText, { color: "#10B981" }]}>Verified</Text>
                </View>
              )}
              {user?.phone && (
                <View style={[styles.tag, { borderColor: "#3B82F650" }]}>
                  <Ionicons name="call" size={13} color={Colors.primary} />
                  <Text style={[styles.tagText, { color: Colors.primary }]}>{user.phone}</Text>
                </View>
              )}
            </View>
          </View>
        </View>

        {/* Stats */}
        <View style={styles.statsRow}>
          <View style={styles.statItem}>
            <Text style={styles.statNum}>{completedWashes}</Text>
            <Text style={styles.statLabel}>Washes</Text>
          </View>
          <View style={[styles.statItem, styles.statBorder]}>
            <Text style={styles.statNum}>{vehiclesTotal}</Text>
            <Text style={styles.statLabel}>Vehicles</Text>
          </View>
          <View style={styles.statItem}>
            <Text style={[styles.statNum, { color: memberStatus.color }]}>{memberStatus.label}</Text>
            <Text style={styles.statLabel}>Status</Text>
          </View>
        </View>

        {/* Account */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>ACCOUNT</Text>
          <View style={styles.menuCard}>
            <MenuOption icon="person-outline" title="Personal Info" subtitle="Name, email, phone" color={Colors.primary}
              onPress={() => navigation.navigate("EditProfile")} />
            <MenuOption icon="car-outline" title="My Vehicles" subtitle={`${vehiclesTotal} vehicle${vehiclesTotal !== 1 ? "s" : ""} registered`}
              color="#8B5CF6" badge={vehiclesTotal > 0 ? String(vehiclesTotal) : undefined}
              onPress={() => navigation.navigate("Vehicles")} />
            <MenuOption icon="card-outline" title="Payment Methods" subtitle="Add or manage payment cards"
              color="#10B981" onPress={() => Alert.alert("Payment Methods", "This feature is coming soon.")} isLast />
          </View>
        </View>

        {/* Preferences */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>PREFERENCES</Text>
          <View style={styles.menuCard}>
            <MenuOption icon="notifications-outline" title="Notifications" subtitle="Wash status, offers, reminders"
              color="#F59E0B" onPress={() => Alert.alert("Notifications", "Notification preferences coming soon.")} />
            <MenuOption icon="location-outline" title="Default Service Address" subtitle="Set your home or work address"
              color="#EC4899" onPress={() => navigation.navigate("EditProfile", { focusAddress: true })} />
            <MenuOption icon="lock-closed-outline" title="Change Password" subtitle="Update your account password"
              color="#94A3B8" onPress={() => Alert.alert("Change Password", `To change your password, please contact us at ${APP_CONFIG.supportEmail}`)} isLast />
          </View>
        </View>

        {/* Support */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>SUPPORT</Text>
          <View style={styles.menuCard}>
            <MenuOption icon="help-buoy-outline" title="Help Center" subtitle="FAQs and contact"
              color="#94A3B8" onPress={() => Alert.alert("Help Center", `Email us at ${APP_CONFIG.supportEmail}`)} />
            <MenuOption icon="star-outline" title="Rate the App" subtitle="Share your feedback"
              color="#F59E0B" onPress={() => Alert.alert("Rate Us", "Thank you! App store rating coming soon.")} />
            <MenuOption icon="shield-checkmark-outline" title="Privacy Policy"
              color="#94A3B8" onPress={() => Alert.alert("Privacy Policy", APP_CONFIG.privacyUrl)} isLast />
          </View>
        </View>

        <View style={styles.footerActions}>
          <Button title="Sign Out" onPress={handleLogout} variant="danger" size="lg" fullWidth icon="log-out-outline" />
          <TouchableOpacity style={styles.deleteBtn} onPress={handleDeleteAccount}>
            <Text style={styles.deleteText}>Delete Account</Text>
          </TouchableOpacity>
        </View>

        <View style={{ height: 100 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0B0F1A" },
  header: { padding: 20, alignItems: "center" },
  headerTitle: { color: "white", fontSize: 24, fontWeight: "800", alignSelf: "flex-start", marginBottom: 20 },
  profileCard: {
    width: "100%", backgroundColor: "#161E2E", borderRadius: 24, padding: 24,
    alignItems: "center", borderWidth: 1, borderColor: "#262F3F", overflow: "hidden",
  },
  avatarWrapper: { position: "relative", marginBottom: 14 },
  avatarInitials: {
    width: 100, height: 100, borderRadius: 50, backgroundColor: "#1E3A5F",
    borderWidth: 3, borderColor: Colors.primary, alignItems: "center", justifyContent: "center",
  },
  initialsText: { color: Colors.primary, fontSize: 36, fontWeight: "700" },
  editBadge: {
    position: "absolute", bottom: 0, right: 0, backgroundColor: Colors.primary,
    padding: 8, borderRadius: 20, borderWidth: 3, borderColor: "#161E2E",
  },
  nameRow: { flexDirection: "row", alignItems: "center", marginBottom: 4 },
  userName: { color: "white", fontSize: 20, fontWeight: "700" },
  userEmail: { color: "#475569", fontSize: 14 },
  memberSince: { color: "#334155", fontSize: 11, marginTop: 6 },
  tagsRow: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 14, justifyContent: "center" },
  tag: {
    flexDirection: "row", alignItems: "center", gap: 4,
    borderWidth: 1, borderRadius: 20, paddingHorizontal: 10, paddingVertical: 4,
    backgroundColor: "#0B0F1A50",
  },
  tagText: { fontSize: 11, fontWeight: "700" },
  statsRow: {
    flexDirection: "row", backgroundColor: "#161E2E",
    marginHorizontal: 20, borderRadius: 20, paddingVertical: 18,
    marginBottom: 28, borderWidth: 1, borderColor: "#262F3F",
  },
  statItem: { flex: 1, alignItems: "center" },
  statBorder: { borderColor: "#1E293B", borderLeftWidth: 1, borderRightWidth: 1 },
  statNum: { color: "white", fontSize: 18, fontWeight: "800" },
  statLabel: { color: "#475569", fontSize: 11, fontWeight: "600", marginTop: 2 },
  section: { paddingHorizontal: 20, marginBottom: 24 },
  sectionLabel: { color: "#475569", fontSize: 11, fontWeight: "800", letterSpacing: 1, marginBottom: 12 },
  menuCard: { backgroundColor: "#161E2E", borderRadius: 20, borderWidth: 1, borderColor: "#262F3F", overflow: "hidden" },
  menuItem: {
    flexDirection: "row", alignItems: "center", padding: 16,
    borderBottomWidth: 1, borderBottomColor: "#262F3F",
  },
  iconBox: { width: 40, height: 40, borderRadius: 12, justifyContent: "center", alignItems: "center", marginRight: 14 },
  menuText: { flex: 1 },
  menuTitle: { color: "white", fontSize: 15, fontWeight: "600" },
  menuSubtitle: { color: "#475569", fontSize: 12, marginTop: 2 },
  badge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 10, marginRight: 6 },
  badgeText: { fontSize: 11, fontWeight: "800" },
  footerActions: { paddingHorizontal: 20, gap: 4 },
  deleteBtn: { alignItems: "center", paddingVertical: 14 },
  deleteText: { color: "#475569", fontSize: 13, textDecorationLine: "underline" },
});
