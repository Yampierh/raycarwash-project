/**
 * frontend/src/screens/SecurityScreen.tsx
 *
 * Profile → Security center. Reads /auth/security for the summary
 * (2FA / passkeys / sessions / last login) and surfaces entry points
 * for each sub-flow.
 *
 * Phase 3 wires the summary and provides navigation hooks for:
 *   - Change email      → ChangeEmailScreen      (Phase 3 chunk Q)
 *   - Change phone      → ChangePhoneScreen      (Phase 3 chunk Q)
 *   - Toggle 2FA        → TwoFactorSetupScreen   (TODO — Phase 3 follow-up)
 *   - Manage passkeys   → PasskeysScreen         (TODO — Phase 3 follow-up)
 *   - View sessions     → SessionsScreen         (TODO — Phase 3 follow-up)
 *
 * Activity tab consumes /auth/history.
 */
import { Ionicons } from "@expo/vector-icons";
import React, { useState } from "react";
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { useSecurityHistory, useSecuritySummary } from "../hooks/useAuthSecurity";
import { Colors } from "../theme/colors";

function formatRelative(iso: string | null): string {
  if (!iso) return "Never";
  const ms = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(ms / 60_000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}

interface RowProps {
  icon: keyof typeof Ionicons.glyphMap;
  title: string;
  subtitle?: string;
  badge?: string;
  warning?: boolean;
  onPress?: () => void;
}

function MenuRow({ icon, title, subtitle, badge, warning, onPress }: RowProps) {
  return (
    <TouchableOpacity style={styles.row} onPress={onPress} disabled={!onPress}>
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
      {onPress ? <Ionicons name="chevron-forward" size={16} color="#334155" /> : null}
    </TouchableOpacity>
  );
}

export default function SecurityScreen({ navigation }: any) {
  const summaryQuery = useSecuritySummary();
  const historyQuery = useSecurityHistory(20);
  const [tab, setTab] = useState<"general" | "activity">("general");

  const summary = summaryQuery.data;

  if (summaryQuery.isLoading) {
    return (
      <View style={[styles.container, styles.center]}>
        <ActivityIndicator color={Colors.primary} />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Ionicons name="chevron-back" size={22} color="white" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Security</Text>
        <View style={{ width: 40 }} />
      </View>

      <View style={styles.tabs}>
        <TouchableOpacity
          style={[styles.tab, tab === "general" && styles.tabActive]}
          onPress={() => setTab("general")}
        >
          <Text style={[styles.tabText, tab === "general" && styles.tabTextActive]}>General</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, tab === "activity" && styles.tabActive]}
          onPress={() => setTab("activity")}
        >
          <Text style={[styles.tabText, tab === "activity" && styles.tabTextActive]}>Activity</Text>
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {tab === "general" ? (
          <>
            <Text style={styles.sectionLabel}>SIGN-IN METHODS</Text>
            <View style={styles.card}>
              <MenuRow
                icon="key-outline"
                title="Password"
                subtitle={
                  summary?.last_password_change
                    ? `Changed ${formatRelative(summary.last_password_change)}`
                    : "Set at sign-up"
                }
                onPress={() => navigation.navigate("ChangePassword")}
              />
              <MenuRow
                icon="shield-checkmark-outline"
                title="Two-factor authentication"
                subtitle={summary?.two_factor_enabled ? "Enabled" : "Not enabled"}
                badge={summary?.two_factor_enabled ? "ON" : "OFF"}
                warning={!summary?.two_factor_enabled}
                onPress={() => navigation.navigate("TwoFactorSetup")}
              />
              <MenuRow
                icon="finger-print-outline"
                title="Passkeys"
                subtitle={`${summary?.passkeys_count ?? 0} registered`}
                onPress={() => navigation.navigate("Passkeys")}
              />
            </View>

            <Text style={[styles.sectionLabel, { marginTop: 24 }]}>CONTACT</Text>
            <View style={styles.card}>
              <MenuRow
                icon="mail-outline"
                title="Change email"
                subtitle="Verify the new address before it takes effect"
                onPress={() => navigation.navigate("ChangeEmail")}
              />
              <MenuRow
                icon="call-outline"
                title="Change phone number"
                subtitle="6-digit SMS code"
                onPress={() => navigation.navigate("ChangePhone")}
              />
            </View>

            <Text style={[styles.sectionLabel, { marginTop: 24 }]}>SESSIONS</Text>
            <View style={styles.card}>
              <MenuRow
                icon="phone-portrait-outline"
                title="Active sessions"
                subtitle={`${summary?.active_sessions_count ?? 0} device(s)`}
                onPress={() => navigation.navigate("Sessions")}
              />
              <MenuRow
                icon="time-outline"
                title="Last successful sign-in"
                subtitle={formatRelative(summary?.last_login_at ?? null)}
              />
              <MenuRow
                icon="alert-circle-outline"
                title="Recent failed attempts"
                subtitle={`${summary?.recent_failed_attempts ?? 0} total`}
                warning={(summary?.recent_failed_attempts ?? 0) > 0}
              />
            </View>
          </>
        ) : (
          <ActivityFeed
            loading={historyQuery.isLoading}
            items={historyQuery.data ?? []}
          />
        )}
        <View style={{ height: 40 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

function ActivityFeed({
  loading,
  items,
}: {
  loading: boolean;
  items: ReturnType<typeof useSecurityHistory>["data"] extends infer T
    ? Exclude<T, undefined>
    : never;
}) {
  if (loading) {
    return (
      <View style={[styles.center, { paddingVertical: 40 }]}>
        <ActivityIndicator color={Colors.primary} />
      </View>
    );
  }
  if (!items || items.length === 0) {
    return (
      <View style={[styles.center, { paddingVertical: 40 }]}>
        <Text style={{ color: "#475569" }}>No security events yet.</Text>
      </View>
    );
  }
  return (
    <View style={styles.card}>
      {items.map((item, idx) => (
        <View
          key={item.id}
          style={[
            styles.activityRow,
            idx === items.length - 1 && { borderBottomWidth: 0 },
          ]}
        >
          <Ionicons
            name={
              item.type === "login"
                ? item.was_successful
                  ? "log-in-outline"
                  : "warning-outline"
                : "document-text-outline"
            }
            size={18}
            color={item.was_successful === false ? "#F59E0B" : Colors.primary}
            style={{ marginRight: 12 }}
          />
          <View style={{ flex: 1 }}>
            <Text style={styles.activityTitle}>{item.summary}</Text>
            <Text style={styles.activitySub}>
              {formatRelative(item.occurred_at)}
              {item.ip_address ? ` · ${item.ip_address}` : ""}
            </Text>
          </View>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0B0F1A" },
  center: { alignItems: "center", justifyContent: "center" },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingVertical: 16,
  },
  backBtn: {
    backgroundColor: "#161E2E",
    padding: 8,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#262F3F",
  },
  headerTitle: { color: "white", fontSize: 18, fontWeight: "700" },
  tabs: {
    flexDirection: "row",
    paddingHorizontal: 20,
    gap: 12,
    marginBottom: 12,
  },
  tab: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 10,
    backgroundColor: "#161E2E",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#262F3F",
  },
  tabActive: { borderColor: Colors.primary, backgroundColor: "#1E3A5F" },
  tabText: { color: "#94A3B8", fontSize: 13, fontWeight: "600" },
  tabTextActive: { color: "white" },
  scroll: { paddingHorizontal: 20 },
  sectionLabel: {
    color: "#475569",
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1,
    marginBottom: 12,
  },
  card: {
    backgroundColor: "#161E2E",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#262F3F",
    overflow: "hidden",
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    padding: 14,
    borderBottomWidth: 1,
    borderBottomColor: "#262F3F",
  },
  iconBox: {
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: "#1E3A5F30",
    alignItems: "center",
    justifyContent: "center",
    marginRight: 12,
  },
  iconWarning: { backgroundColor: "#F59E0B22" },
  rowText: { flex: 1 },
  rowTitle: { color: "white", fontSize: 15, fontWeight: "600" },
  rowSub: { color: "#64748B", fontSize: 12, marginTop: 2 },
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: 10,
    backgroundColor: "#10B98122",
    marginRight: 6,
  },
  badgeWarn: { backgroundColor: "#F59E0B22" },
  badgeText: { color: "#10B981", fontSize: 11, fontWeight: "800" },
  badgeTextWarn: { color: "#F59E0B" },
  activityRow: {
    flexDirection: "row",
    alignItems: "center",
    padding: 14,
    borderBottomWidth: 1,
    borderBottomColor: "#262F3F",
  },
  activityTitle: { color: "white", fontSize: 14, fontWeight: "500" },
  activitySub: { color: "#64748B", fontSize: 11, marginTop: 2 },
});
