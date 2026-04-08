import { Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
import { useFocusEffect } from "@react-navigation/native";
import { LinearGradient } from "expo-linear-gradient";
import React, { useCallback, useState } from "react";
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
import { getMyAppointments } from "../services/appointment.service";
import { getUserProfile } from "../services/user.service";
import { getMyVehicles } from "../services/vehicle.service";
import { Colors } from "../theme/colors";
import { APP_CONFIG } from "../config/app.config";
import { clearAuthTokens } from "../utils/storage";

export default function ProfileScreen({ navigation }: any) {
  const [userData, setUserData] = useState<any>(null);
  const [vehicles, setVehicles] = useState<any[]>([]);
  const [completedWashes, setCompletedWashes] = useState(0);
  const [loading, setLoading] = useState(true);

  useFocusEffect(
    useCallback(() => {
      loadProfile();
    }, []),
  );

  const loadProfile = async () => {
    setLoading(true);
    try {
      const [profile, myVehicles, myApts] = await Promise.all([
        getUserProfile(),
        getMyVehicles(),
        getMyAppointments(1, 100),
      ]);
      setUserData(profile);
      setVehicles(myVehicles || []);
      const done = (myApts?.items || []).filter(
        (a: any) => a.status === "completed",
      ).length;
      setCompletedWashes(done);
    } catch {
      Alert.alert("Error", "Could not load your profile. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const getMemberStatus = (washes: number) => {
    if (washes >= 15) return { label: "Platinum", color: "#E2E8F0" };
    if (washes >= 8) return { label: "Gold", color: "#F59E0B" };
    if (washes >= 3) return { label: "Silver", color: "#94A3B8" };
    return { label: "Bronze", color: "#B45309" };
  };

  const getInitials = (fullName: string | undefined) => {
    if (!fullName) return "U";
    return fullName
      .split(" ")
      .map((n: string) => n[0])
      .join("")
      .slice(0, 2)
      .toUpperCase();
  };

  const getMemberSince = (createdAt: string | undefined) => {
    if (!createdAt) return "—";
    return new Date(createdAt).toLocaleDateString("en-US", {
      month: "long",
      year: "numeric",
    });
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
          onPress: () =>
            Alert.alert(
              "Contact Support",
              `To delete your account, please contact us at ${APP_CONFIG.supportEmail}`,
            ),
        },
      ],
    );
  };

  const memberStatus = getMemberStatus(completedWashes);

  const MenuOption = ({
    icon,
    title,
    subtitle,
    onPress,
    color = "#94A3B8",
    badge,
    isLast = false,
  }: any) => (
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

  if (loading) {
    return (
      <View style={[styles.container, { justifyContent: "center" }]}>
        <ActivityIndicator size="large" color={Colors.primary} />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.headerTitle}>My Profile</Text>

          <View style={styles.profileCard}>
            <LinearGradient
              colors={["#3B82F620", "transparent"]}
              style={StyleSheet.absoluteFill}
            />

            {/* Avatar con iniciales */}
            <View style={styles.avatarWrapper}>
              <View style={styles.avatarInitials}>
                <Text style={styles.initialsText}>
                  {getInitials(userData?.full_name)}
                </Text>
              </View>
              <TouchableOpacity
                style={styles.editBadge}
                onPress={() => navigation.navigate("EditProfile", { user: userData })}
              >
                <Ionicons name="pencil" size={14} color="white" />
              </TouchableOpacity>
            </View>

            {/* Nombre y email */}
            <View style={styles.nameRow}>
              <Text style={styles.userName}>
                {userData?.full_name || "User"}
              </Text>
              {userData?.is_verified && (
                <Ionicons
                  name="checkmark-circle"
                  size={18}
                  color="#10B981"
                  style={{ marginLeft: 6 }}
                />
              )}
            </View>
            <Text style={styles.userEmail}>{userData?.email || "—"}</Text>

            {/* Member since */}
            <Text style={styles.memberSince}>
              Member since {getMemberSince(userData?.created_at)}
            </Text>

            {/* Tags de estado */}
            <View style={styles.tagsRow}>
              <View style={[styles.tag, { borderColor: memberStatus.color + "50" }]}>
                <MaterialCommunityIcons
                  name="star-circle"
                  size={13}
                  color={memberStatus.color}
                />
                <Text style={[styles.tagText, { color: memberStatus.color }]}>
                  {memberStatus.label}
                </Text>
              </View>
              {userData?.is_verified && (
                <View style={[styles.tag, { borderColor: "#10B98150" }]}>
                  <Ionicons name="shield-checkmark" size={13} color="#10B981" />
                  <Text style={[styles.tagText, { color: "#10B981" }]}>Verified</Text>
                </View>
              )}
              {userData?.phone_number && (
                <View style={[styles.tag, { borderColor: "#3B82F650" }]}>
                  <Ionicons name="call" size={13} color={Colors.primary} />
                  <Text style={[styles.tagText, { color: Colors.primary }]}>
                    {userData.phone_number}
                  </Text>
                </View>
              )}
            </View>
          </View>
        </View>

        {/* Stats reales */}
        <View style={styles.statsRow}>
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

        {/* ACCOUNT SETTINGS */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>ACCOUNT</Text>
          <View style={styles.menuCard}>
            <MenuOption
              icon="person-outline"
              title="Personal Info"
              subtitle="Name, email, phone"
              color={Colors.primary}
              onPress={() => navigation.navigate("EditProfile", { user: userData })}
            />
            <MenuOption
              icon="car-outline"
              title="My Vehicles"
              subtitle={`${vehicles.length} vehicle${vehicles.length !== 1 ? "s" : ""} registered`}
              color="#8B5CF6"
              badge={vehicles.length > 0 ? String(vehicles.length) : undefined}
              onPress={() => navigation.navigate("Vehicles")}
            />
            <MenuOption
              icon="card-outline"
              title="Payment Methods"
              subtitle="Add or manage payment cards"
              color="#10B981"
              onPress={() =>
                Alert.alert("Payment Methods", "This feature is coming soon.")
              }
              isLast
            />
          </View>
        </View>

        {/* PREFERENCES */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>PREFERENCES</Text>
          <View style={styles.menuCard}>
            <MenuOption
              icon="notifications-outline"
              title="Notifications"
              subtitle="Wash status, offers, reminders"
              color="#F59E0B"
              onPress={() =>
                Alert.alert("Notifications", "Notification preferences coming soon.")
              }
            />
            <MenuOption
              icon="location-outline"
              title="Default Service Address"
              subtitle="Set your home or work address"
              color="#EC4899"
              onPress={() => navigation.navigate("EditProfile", { user: userData, focusAddress: true })}
            />
            <MenuOption
              icon="lock-closed-outline"
              title="Change Password"
              subtitle="Update your account password"
              color="#94A3B8"
              onPress={() =>
                Alert.alert(
                  "Change Password",
                  `To change your password, please contact us at ${APP_CONFIG.supportEmail}`,
                )
              }
              isLast
            />
          </View>
        </View>

        {/* SUPPORT */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>SUPPORT</Text>
          <View style={styles.menuCard}>
            <MenuOption
              icon="help-buoy-outline"
              title="Help Center"
              subtitle="FAQs and contact"
              color="#94A3B8"
              onPress={() =>
                Alert.alert("Help Center", `Email us at ${APP_CONFIG.supportEmail}`)
              }
            />
            <MenuOption
              icon="star-outline"
              title="Rate the App"
              subtitle="Share your feedback"
              color="#F59E0B"
              onPress={() =>
                Alert.alert("Rate Us", "Thank you! App store rating coming soon.")
              }
            />
            <MenuOption
              icon="shield-checkmark-outline"
              title="Privacy Policy"
              color="#94A3B8"
              onPress={() =>
                Alert.alert("Privacy Policy", APP_CONFIG.privacyUrl)
              }
              isLast
            />
          </View>
        </View>

        {/* Sign Out */}
        <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
          <Ionicons name="log-out-outline" size={20} color="#EF4444" />
          <Text style={styles.logoutText}>Sign Out</Text>
        </TouchableOpacity>

        {/* Delete Account */}
        <TouchableOpacity style={styles.deleteBtn} onPress={handleDeleteAccount}>
          <Text style={styles.deleteText}>Delete Account</Text>
        </TouchableOpacity>

        <View style={{ height: 100 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0B0F1A" },
  header: { padding: 20, alignItems: "center" },
  headerTitle: {
    color: "white",
    fontSize: 24,
    fontWeight: "bold",
    alignSelf: "flex-start",
    marginBottom: 20,
  },
  profileCard: {
    width: "100%",
    backgroundColor: "#161E2E",
    borderRadius: 30,
    padding: 25,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#262F3F",
    overflow: "hidden",
  },
  avatarWrapper: { position: "relative", marginBottom: 15 },
  avatarInitials: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: "#1E3A5F",
    borderWidth: 3,
    borderColor: Colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  initialsText: { color: Colors.primary, fontSize: 36, fontWeight: "bold" },
  editBadge: {
    position: "absolute",
    bottom: 0,
    right: 0,
    backgroundColor: Colors.primary,
    padding: 8,
    borderRadius: 20,
    borderWidth: 3,
    borderColor: "#161E2E",
  },
  nameRow: { flexDirection: "row", alignItems: "center", marginBottom: 4 },
  userName: { color: "white", fontSize: 20, fontWeight: "bold" },
  userEmail: { color: "#475569", fontSize: 14 },
  memberSince: { color: "#334155", fontSize: 11, marginTop: 6 },
  tagsRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
    marginTop: 14,
    justifyContent: "center",
  },
  tag: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    borderWidth: 1,
    borderRadius: 20,
    paddingHorizontal: 10,
    paddingVertical: 4,
    backgroundColor: "#0B0F1A50",
  },
  tagText: { fontSize: 11, fontWeight: "700" },
  statsRow: {
    flexDirection: "row",
    backgroundColor: "#161E2E",
    marginHorizontal: 20,
    borderRadius: 20,
    paddingVertical: 18,
    marginBottom: 30,
    borderWidth: 1,
    borderColor: "#262F3F",
  },
  statItem: { flex: 1, alignItems: "center" },
  statBorder: {
    borderColor: "#1E293B",
    borderLeftWidth: 1,
    borderRightWidth: 1,
  },
  statNum: { color: "white", fontSize: 18, fontWeight: "bold" },
  statLabel: { color: "#475569", fontSize: 11, fontWeight: "600", marginTop: 2 },
  section: { paddingHorizontal: 20, marginBottom: 25 },
  sectionLabel: {
    color: "#475569",
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1,
    marginBottom: 12,
  },
  menuCard: {
    backgroundColor: "#161E2E",
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "#262F3F",
    overflow: "hidden",
  },
  menuItem: {
    flexDirection: "row",
    alignItems: "center",
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: "#262F3F",
  },
  iconBox: {
    width: 40,
    height: 40,
    borderRadius: 12,
    justifyContent: "center",
    alignItems: "center",
    marginRight: 14,
  },
  menuText: { flex: 1 },
  menuTitle: { color: "white", fontSize: 15, fontWeight: "600" },
  menuSubtitle: { color: "#475569", fontSize: 12, marginTop: 2 },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 10,
    marginRight: 6,
  },
  badgeText: { fontSize: 11, fontWeight: "800" },
  logoutBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    marginHorizontal: 20,
    padding: 18,
    borderRadius: 20,
    backgroundColor: "rgba(239, 68, 68, 0.08)",
    gap: 10,
    borderWidth: 1,
    borderColor: "rgba(239, 68, 68, 0.15)",
  },
  logoutText: { color: "#EF4444", fontWeight: "bold", fontSize: 16 },
  deleteBtn: {
    alignItems: "center",
    marginTop: 14,
    marginBottom: 4,
    padding: 12,
  },
  deleteText: { color: "#475569", fontSize: 13, textDecorationLine: "underline" },
});
