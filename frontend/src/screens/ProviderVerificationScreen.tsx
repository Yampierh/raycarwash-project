/**
 * frontend/src/screens/ProviderVerificationScreen.tsx
 *
 * Identity verification dashboard. Shows current status, lists earned
 * badges, and surfaces the "Start verification" CTA (or "Resume
 * verification" if a session is mid-flight).
 *
 * Real Stripe Identity launch is delegated to the existing
 * DetailerOnboardingScreen flow (which already wires
 * @stripe/stripe-react-native's useStripeIdentity hook). This screen
 * only handles the dev-bypass path inline — the auto-approve via
 * /detailers/verification/submit so onboarding can flow end-to-end
 * locally without Stripe SDK plumbing.
 *
 * Status / approved → just show the "You're verified" celebration +
 * "View badges" CTA.
 */
import { Ionicons } from "@expo/vector-icons";
import React from "react";
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
import {
  useAchievements,
  useStartVerification,
  useVerificationStatus,
} from "../hooks/useProviderResources";
import { Colors } from "../theme/colors";

function formatStatus(status: string): {
  title: string;
  body: string;
  icon: keyof typeof Ionicons.glyphMap;
  color: string;
} {
  switch (status) {
    case "approved":
      return {
        title: "You're verified",
        body: "Clients can book you and your verified badge is live on your public profile.",
        icon: "shield-checkmark",
        color: "#10B981",
      };
    case "pending":
      return {
        title: "Verification in progress",
        body: "Stripe is reviewing your documents. This usually takes a few minutes; we'll notify you once it's done.",
        icon: "time-outline",
        color: "#F59E0B",
      };
    case "rejected":
      return {
        title: "Verification rejected",
        body: "Stripe couldn't verify your identity. Re-run the flow with a clearer photo of your ID.",
        icon: "alert-circle",
        color: "#EF4444",
      };
    default:
      return {
        title: "Not started",
        body: "Verify your identity to start accepting bookings. Takes about 2 minutes.",
        icon: "shield-outline",
        color: "#94A3B8",
      };
  }
}

export default function ProviderVerificationScreen({ navigation }: any) {
  const statusQuery = useVerificationStatus();
  const achievementsQuery = useAchievements();
  const start = useStartVerification();

  const handleStart = () => {
    start.mutate(undefined, {
      onSuccess: (data) => {
        if (data.is_dev_bypass) {
          // Dev bypass: route the user to the legacy
          // DetailerOnboardingScreen which collects legal info and
          // auto-approves via /detailers/verification/submit.
          Alert.alert(
            "Dev bypass",
            "Stripe Identity is in test mode. Continue to enter your details and we'll auto-approve.",
            [
              { text: "Cancel", style: "cancel" },
              {
                text: "Continue",
                onPress: () => navigation.navigate("DetailerOnboarding"),
              },
            ],
          );
          return;
        }
        // Real Stripe path — DetailerOnboardingScreen already wires
        // useStripeIdentity to consume the client_secret. Reuse it
        // rather than duplicate the SDK plumbing here.
        navigation.navigate("DetailerOnboarding");
      },
      onError: () =>
        Alert.alert(
          "Could not start verification",
          "Please try again in a moment.",
        ),
    });
  };

  if (statusQuery.isLoading) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.center}>
          <ActivityIndicator color={Colors.primary} />
        </View>
      </SafeAreaView>
    );
  }

  const status = statusQuery.data;
  const fmt = formatStatus(status?.verification_status ?? "not_submitted");
  const approved = status?.verification_status === "approved";

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
        <Text style={styles.headerTitle}>Identity verification</Text>
        <View style={{ width: 32 }} />
      </View>

      <ScrollView contentContainerStyle={styles.body}>
        <View
          style={[
            styles.statusCard,
            { backgroundColor: `${fmt.color}15`, borderColor: `${fmt.color}55` },
          ]}
        >
          <Ionicons name={fmt.icon} size={40} color={fmt.color} />
          <Text style={[styles.statusTitle, { color: fmt.color }]}>
            {fmt.title}
          </Text>
          <Text style={styles.statusBody}>{fmt.body}</Text>

          {status?.rejection_reason && status.verification_status === "rejected" ? (
            <Text style={styles.rejection}>{status.rejection_reason}</Text>
          ) : null}

          {!approved ? (
            <Button
              title={
                status?.has_active_session
                  ? "Resume verification"
                  : "Start verification"
              }
              onPress={handleStart}
              loading={start.isPending}
              disabled={start.isPending}
              style={{ marginTop: 16, width: "100%" }}
            />
          ) : null}
        </View>

        <Text style={styles.sectionLabel}>EARNED BADGES</Text>
        {achievementsQuery.isLoading ? (
          <ActivityIndicator color={Colors.primary} />
        ) : !achievementsQuery.data || achievementsQuery.data.length === 0 ? (
          <View style={styles.empty}>
            <Ionicons name="ribbon-outline" size={28} color="#475569" />
            <Text style={styles.emptyText}>
              Badges show up as you reach milestones — complete your first job
              to unlock the "First job" badge.
            </Text>
          </View>
        ) : (
          <View style={styles.badgeGrid}>
            {achievementsQuery.data.map((badge) => (
              <View key={badge.id} style={styles.badgeCard}>
                <Ionicons name="ribbon" size={20} color="#FBBF24" />
                <Text style={styles.badgeName}>
                  {badge.achievement_type.replace(/_/g, " ")}
                </Text>
                <Text style={styles.badgeDate}>
                  {new Date(badge.awarded_at).toLocaleDateString()}
                </Text>
              </View>
            ))}
          </View>
        )}
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

  statusCard: {
    alignItems: "center",
    borderWidth: 1,
    borderRadius: 16,
    padding: 24,
    marginBottom: 24,
  },
  statusTitle: { fontSize: 18, fontWeight: "700", marginTop: 12 },
  statusBody: {
    color: Colors.secondaryText,
    fontSize: 13,
    marginTop: 8,
    textAlign: "center",
    lineHeight: 19,
  },
  rejection: {
    color: "#EF4444",
    fontSize: 12,
    marginTop: 12,
    fontStyle: "italic",
    textAlign: "center",
  },

  sectionLabel: {
    color: Colors.secondaryText,
    fontSize: 11,
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: 0.5,
    marginBottom: 12,
  },
  empty: {
    backgroundColor: Colors.card,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#1E293B",
    padding: 20,
    alignItems: "center",
    gap: 8,
  },
  emptyText: {
    color: Colors.secondaryText,
    fontSize: 13,
    textAlign: "center",
    lineHeight: 19,
  },
  badgeGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 12,
  },
  badgeCard: {
    flexBasis: "31%",
    flexGrow: 1,
    backgroundColor: Colors.card,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#1E293B",
    padding: 14,
    alignItems: "center",
  },
  badgeName: {
    color: Colors.text,
    fontSize: 12,
    fontWeight: "600",
    textTransform: "capitalize",
    marginTop: 8,
    textAlign: "center",
  },
  badgeDate: {
    color: Colors.secondaryText,
    fontSize: 11,
    marginTop: 4,
  },
});
