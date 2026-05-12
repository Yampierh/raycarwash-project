import React from "react";
import { StyleSheet, Text, View, ViewStyle } from "react-native";
import { Colors } from "../theme/colors";

interface StatusBadgeProps {
  status: string;
  size?: "sm" | "md";
  style?: ViewStyle;
  showDot?: boolean;
}

const FALLBACK = { bg: "#64748B22", text: "#64748B", border: "#64748B55" };

const STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  confirmed: "Confirmed",
  arrived: "Arrived",
  in_progress: "In Progress",
  completed: "Completed",
  cancelled_by_client: "Cancelled",
  cancelled_by_detailer: "Cancelled",
  no_show: "No Show",
  no_detailer_found: "No Detailer",
  searching: "Searching",
};

export default function StatusBadge({ status, size = "sm", style, showDot = false }: StatusBadgeProps) {
  const colors = (Colors.status as any)[status] ?? FALLBACK;
  const label = STATUS_LABELS[status] ?? status.replace(/_/g, " ").toUpperCase();
  const isLg = size === "md";

  return (
    <View
      style={[
        styles.badge,
        {
          backgroundColor: colors.bg,
          borderColor: colors.border,
          paddingHorizontal: isLg ? 12 : 9,
          paddingVertical: isLg ? 5 : 3,
        },
        style,
      ]}
    >
      {showDot && (
        <View style={[styles.dot, { backgroundColor: colors.text }]} />
      )}
      <Text
        style={[
          styles.text,
          { color: colors.text, fontSize: isLg ? 12 : 10 },
        ]}
      >
        {label.toUpperCase()}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: "row",
    alignItems: "center",
    borderRadius: 20,
    borderWidth: 1,
    alignSelf: "flex-start",
  },
  dot: { width: 6, height: 6, borderRadius: 3, marginRight: 5 },
  text: { fontWeight: "700", letterSpacing: 0.5 },
});
