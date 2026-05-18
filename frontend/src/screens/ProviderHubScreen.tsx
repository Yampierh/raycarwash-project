/**
 * frontend/src/screens/ProviderHubScreen.tsx
 *
 * Detailer dashboard for managing their own provider profile, KYC,
 * portfolio, and earned badges.
 *
 * Layout:
 *   - Status banner: verification state + accepting-bookings toggle
 *     (toggle is disabled when KYC is not approved — the backend
 *     gates this with 403 kyc_required and we mirror the UX).
 *   - Stats strip: lifetime jobs, rating, earnings.
 *   - Achievements (newest first, last 3 inline + "view all").
 *   - Menu: routes to ProviderProfileEdit, ProviderPortfolio,
 *     ProviderDocuments, ProviderVerification.
 *
 * The Activate / "Become a detailer" CTA is OWNED by ProfileScreen
 * for client-only users; this screen is reached only after activation.
 * If the user lands here without an activated profile (e.g. via deep
 * link), we show the activate-first empty state.
 */
import { Ionicons } from "@expo/vector-icons";
import React, { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import Button from "../components/Button";
import {
  useAchievements,
  useActivateProvider,
  useProviderProfile,
  useSetProviderStatus,
} from "../hooks/useProviderResources";
import { ApiError, StepUpRequiredError } from "../lib/api-error";
import { Colors } from "../theme/colors";

// ─── Inline activation form (shown when no provider profile exists) ─────────


interface ActivationFormProps {
  onCancel: () => void;
}

function ActivationForm({ onCancel }: ActivationFormProps) {
  const [businessName, setBusinessName] = useState("");
  const [radius, setRadius] = useState("25");
  const activate = useActivateProvider();

  const submit = () => {
    const trimmed = businessName.trim();
    if (trimmed.length < 2) {
      Alert.alert("Missing field", "Business name is required (at least 2 chars).");
      return;
    }
    const parsedRadius = Number.parseInt(radius, 10);
    if (isNaN(parsedRadius) || parsedRadius < 1 || parsedRadius > 200) {
      Alert.alert("Invalid value", "Service radius must be between 1 and 200 miles.");
      return;
    }
    activate.mutate(
      { business_name: trimmed, service_radius_miles: parsedRadius },
      {
        onError: (err) => {
          if (err instanceof StepUpRequiredError) {
            Alert.alert(
              "Verification required",
              "Confirm it's you to activate provider mode.",
            );
            return;
          }
          Alert.alert("Could not activate", "Please try again.");
        },
      },
    );
  };

  return (
    <ScrollView contentContainerStyle={styles.activateBody}>
      <View style={styles.activateHero}>
        <Ionicons name="briefcase" size={36} color={Colors.primary} />
        <Text style={styles.activateTitle}>Earn detailing on RayCarWash</Text>
        <Text style={styles.activateBlurb}>
          Set up your business profile in 1 minute. You'll verify your identity
          and add documents in the next steps — bookings start once you're
          approved.
        </Text>
      </View>

      <Text style={styles.fieldLabel}>BUSINESS NAME *</Text>
      <TextInput
        style={styles.input}
        value={businessName}
        onChangeText={setBusinessName}
        placeholder="Yampi Detailing LLC"
        placeholderTextColor="#475569"
        maxLength={120}
      />

      <Text style={styles.fieldLabel}>SERVICE RADIUS (mi) *</Text>
      <TextInput
        style={styles.input}
        value={radius}
        onChangeText={setRadius}
        placeholder="25"
        placeholderTextColor="#475569"
        keyboardType="numeric"
        maxLength={3}
      />

      <Button
        title="Activate provider mode"
        onPress={submit}
        loading={activate.isPending}
        disabled={activate.isPending}
        style={{ marginTop: 24 }}
      />
      <TouchableOpacity
        style={styles.cancelBtn}
        onPress={onCancel}
        disabled={activate.isPending}
      >
        <Text style={styles.cancelText}>Cancel</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}


interface MenuRowProps {
  icon: keyof typeof Ionicons.glyphMap;
  title: string;
  subtitle?: string;
  badge?: string;
  warning?: boolean;
  onPress: () => void;
}

function MenuRow({ icon, title, subtitle, badge, warning, onPress }: MenuRowProps) {
  return (
    <TouchableOpacity style={styles.row} onPress={onPress}>
      <View style={[styles.iconBox, warning && styles.iconWarning]}>
        <Ionicons
          name={icon}
          size={18}
          color={warning ? "#F59E0B" : Colors.primary}
        />
      </View>
      <View style={styles.rowText}>
        <Text style={styles.rowTitle}>{title}</Text>
        {subtitle ? <Text style={styles.rowSub}>{subtitle}</Text> : null}
      </View>
      {badge ? (
        <View style={[styles.badge, warning && styles.badgeWarn]}>
          <Text style={[styles.badgeText, warning && styles.badgeTextWarn]}>{badge}</Text>
        </View>
      ) : null}
      <Ionicons name="chevron-forward" size={16} color="#334155" />
    </TouchableOpacity>
  );
}

function formatVerification(status: string): {
  label: string;
  color: string;
  warning: boolean;
} {
  switch (status) {
    case "approved":
      return { label: "Verified", color: "#10B981", warning: false };
    case "pending":
      return { label: "Pending review", color: "#F59E0B", warning: true };
    case "rejected":
      return { label: "Rejected", color: "#EF4444", warning: true };
    default:
      return { label: "Not submitted", color: "#94A3B8", warning: true };
  }
}

export default function ProviderHubScreen({ navigation }: any) {
  const profileQuery = useProviderProfile();
  const achievementsQuery = useAchievements();
  const statusMutation = useSetProviderStatus();

  const handleToggleBookings = (next: boolean) => {
    statusMutation.mutate(next, {
      onError: (err) => {
        if (err instanceof ApiError && err.code === "kyc_required") {
          Alert.alert(
            "Verification required",
            "Complete identity verification before accepting bookings.",
          );
          return;
        }
        Alert.alert("Could not update", "Please try again.");
      },
    });
  };

  if (profileQuery.isLoading) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.center}>
          <ActivityIndicator color={Colors.primary} />
        </View>
      </SafeAreaView>
    );
  }

  if (profileQuery.isError || !profileQuery.data) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.header}>
          <TouchableOpacity
            onPress={() => navigation.goBack()}
            style={styles.backBtn}
            hitSlop={12}
          >
            <Ionicons name="chevron-back" size={24} color={Colors.text} />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Become a detailer</Text>
          <View style={{ width: 32 }} />
        </View>
        <ActivationForm onCancel={() => navigation.goBack()} />
      </SafeAreaView>
    );
  }

  const profile = profileQuery.data;
  const verification = formatVerification(profile.verification_status);
  const recentAchievements = achievementsQuery.data?.slice(0, 3) ?? [];
  const kycApproved = profile.verification_status === "approved";

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          style={styles.backBtn}
          hitSlop={12}
        >
          <Ionicons name="chevron-back" size={24} color={Colors.text} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Provider Hub</Text>
        <View style={{ width: 32 }} />
      </View>

      <ScrollView contentContainerStyle={styles.body}>
        <View style={styles.hero}>
          <Text style={styles.heroName}>
            {profile.display_name || profile.business_name || "Your business"}
          </Text>
          {profile.tagline ? (
            <Text style={styles.heroTagline}>{profile.tagline}</Text>
          ) : null}

          <View
            style={[
              styles.verifBadge,
              { backgroundColor: `${verification.color}22`, borderColor: verification.color },
            ]}
          >
            <Ionicons
              name={kycApproved ? "shield-checkmark" : "shield-outline"}
              size={14}
              color={verification.color}
            />
            <Text style={[styles.verifBadgeText, { color: verification.color }]}>
              {verification.label}
            </Text>
          </View>
        </View>

        <View style={styles.statusCard}>
          <View style={{ flex: 1 }}>
            <Text style={styles.statusLabel}>Accepting bookings</Text>
            <Text style={styles.statusHint}>
              {kycApproved
                ? "Clients can request you when this is on."
                : "Verify your identity first to start accepting bookings."}
            </Text>
          </View>
          <Switch
            value={profile.is_accepting_bookings}
            disabled={!kycApproved || statusMutation.isPending}
            onValueChange={handleToggleBookings}
            trackColor={{ false: "#1E293B", true: "rgba(16,185,129,0.4)" }}
            thumbColor={profile.is_accepting_bookings ? "#10B981" : "#94A3B8"}
          />
        </View>

        <View style={styles.statsRow}>
          <View style={styles.statCell}>
            <Text style={styles.statValue}>{profile.total_services_completed}</Text>
            <Text style={styles.statLabel}>Jobs</Text>
          </View>
          <View style={styles.statCell}>
            <Text style={styles.statValue}>
              {profile.average_rating !== null
                ? profile.average_rating.toFixed(1)
                : "—"}
            </Text>
            <Text style={styles.statLabel}>
              Rating ({profile.total_reviews})
            </Text>
          </View>
          <View style={styles.statCell}>
            <Text style={styles.statValue}>
              ${(profile.earnings_lifetime_cents / 100).toFixed(0)}
            </Text>
            <Text style={styles.statLabel}>Earned</Text>
          </View>
        </View>

        {recentAchievements.length > 0 ? (
          <View style={styles.section}>
            <Text style={styles.sectionLabel}>RECENT BADGES</Text>
            <View style={styles.badgeStrip}>
              {recentAchievements.map((badge) => (
                <View key={badge.id} style={styles.badgePill}>
                  <Ionicons name="ribbon-outline" size={14} color="#FBBF24" />
                  <Text style={styles.badgePillText}>{badge.achievement_type.replace(/_/g, " ")}</Text>
                </View>
              ))}
            </View>
          </View>
        ) : null}

        <Text style={styles.sectionLabel}>MANAGE</Text>
        <View style={styles.menuCard}>
          <MenuRow
            icon="person-circle-outline"
            title="Edit profile"
            subtitle="Business name, bio, hours, social links"
            onPress={() => navigation.navigate("ProviderProfileEdit")}
          />
          <MenuRow
            icon="images-outline"
            title="Portfolio"
            subtitle="Before / after photos shown publicly"
            onPress={() => navigation.navigate("ProviderPortfolio")}
          />
          <MenuRow
            icon="document-text-outline"
            title="KYC documents"
            subtitle="Insurance, license, certifications"
            onPress={() => navigation.navigate("ProviderDocuments")}
          />
          <MenuRow
            icon={kycApproved ? "shield-checkmark-outline" : "shield-outline"}
            title="Identity verification"
            subtitle={verification.label}
            warning={!kycApproved}
            onPress={() => navigation.navigate("ProviderVerification")}
          />
        </View>

        <TouchableOpacity
          style={styles.deactivateBtn}
          onPress={() =>
            Alert.alert(
              "Pause provider mode?",
              "Your profile + KYC stay saved. You can re-activate any time.",
              [
                { text: "Cancel", style: "cancel" },
                {
                  text: "Pause",
                  style: "destructive",
                  onPress: () => navigation.navigate("ProviderProfileEdit", { focusDeactivate: true }),
                },
              ],
            )
          }
        >
          <Ionicons name="pause-circle-outline" size={18} color="#94A3B8" />
          <Text style={styles.deactivateText}>Pause provider mode</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.background },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  backBtn: { padding: 4 },
  headerTitle: {
    flex: 1,
    color: Colors.text,
    fontSize: 18,
    fontWeight: "600",
    textAlign: "center",
  },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  body: { padding: 16, paddingBottom: 48 },

  hero: { marginBottom: 16 },
  heroName: { color: Colors.text, fontSize: 22, fontWeight: "700" },
  heroTagline: { color: Colors.secondaryText, fontSize: 14, marginTop: 4 },
  verifBadge: {
    alignSelf: "flex-start",
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 4,
    marginTop: 10,
  },
  verifBadgeText: { fontSize: 12, fontWeight: "600" },

  statusCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colors.card,
    borderRadius: 14,
    padding: 14,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: "#1E293B",
  },
  statusLabel: { color: Colors.text, fontSize: 15, fontWeight: "600" },
  statusHint: { color: "#64748B", fontSize: 12, marginTop: 2 },

  statsRow: {
    flexDirection: "row",
    backgroundColor: Colors.card,
    borderRadius: 14,
    paddingVertical: 14,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: "#1E293B",
  },
  statCell: { flex: 1, alignItems: "center" },
  statValue: { color: Colors.text, fontSize: 18, fontWeight: "700" },
  statLabel: { color: Colors.secondaryText, fontSize: 11, marginTop: 4 },

  section: { marginBottom: 16 },
  sectionLabel: {
    color: Colors.secondaryText,
    fontSize: 11,
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: 0.5,
    marginBottom: 8,
    marginTop: 8,
  },
  badgeStrip: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  badgePill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: "rgba(251,191,36,0.12)",
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
  },
  badgePillText: {
    color: "#FBBF24",
    fontSize: 12,
    fontWeight: "600",
    textTransform: "capitalize",
  },

  menuCard: {
    backgroundColor: Colors.card,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#1E293B",
    overflow: "hidden",
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 14,
    paddingVertical: 14,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: "#1E293B",
  },
  iconBox: {
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: "rgba(59,130,246,0.12)",
    alignItems: "center",
    justifyContent: "center",
    marginRight: 12,
  },
  iconWarning: { backgroundColor: "rgba(245,158,11,0.12)" },
  rowText: { flex: 1 },
  rowTitle: { color: Colors.text, fontSize: 14, fontWeight: "500" },
  rowSub: { color: Colors.secondaryText, fontSize: 12, marginTop: 2 },
  badge: {
    backgroundColor: "#1A2233",
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 8,
    marginRight: 8,
  },
  badgeWarn: { backgroundColor: "rgba(245,158,11,0.15)" },
  badgeText: { color: Colors.text, fontSize: 11, fontWeight: "600" },
  badgeTextWarn: { color: "#F59E0B" },

  deactivateBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    marginTop: 24,
    padding: 12,
  },
  deactivateText: { color: "#94A3B8", fontSize: 13, fontWeight: "500" },

  // ─── Activation form ───────────────────────────────────────────────
  activateBody: { padding: 24, paddingBottom: 48 },
  activateHero: { alignItems: "center", marginBottom: 28 },
  activateTitle: {
    color: Colors.text,
    fontSize: 20,
    fontWeight: "700",
    marginTop: 12,
    textAlign: "center",
  },
  activateBlurb: {
    color: Colors.secondaryText,
    fontSize: 13,
    marginTop: 8,
    textAlign: "center",
    lineHeight: 19,
  },
  fieldLabel: {
    color: Colors.secondaryText,
    fontSize: 12,
    fontWeight: "600",
    marginBottom: 6,
    marginTop: 12,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  input: {
    backgroundColor: "#111827",
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 12,
    color: Colors.text,
    borderWidth: 1,
    borderColor: "#1E293B",
    fontSize: 15,
  },
  cancelBtn: { marginTop: 12, padding: 10, alignItems: "center" },
  cancelText: { color: "#94A3B8", fontSize: 13, fontWeight: "500" },
});
