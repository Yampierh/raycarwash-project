import { MaterialCommunityIcons } from "@expo/vector-icons";
import React from "react";
import { StyleSheet, Text, View, ViewStyle } from "react-native";
import Button from "./Button";
import { Colors } from "../theme/colors";

interface EmptyStateProps {
  icon: string;
  title: string;
  subtitle?: string;
  action?: { label: string; onPress: () => void };
  style?: ViewStyle;
  /** Use dashed border (default true) */
  dashed?: boolean;
}

export default function EmptyState({ icon, title, subtitle, action, style, dashed = true }: EmptyStateProps) {
  return (
    <View
      style={[
        styles.container,
        dashed && styles.dashed,
        style,
      ]}
    >
      <MaterialCommunityIcons name={icon as any} size={44} color="#334155" />
      <Text style={styles.title}>{title}</Text>
      {subtitle && <Text style={styles.subtitle}>{subtitle}</Text>}
      {action && (
        <Button
          title={action.label}
          onPress={action.onPress}
          variant="primary"
          size="md"
          style={{ marginTop: 8 }}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginHorizontal: 20,
    backgroundColor: "#161E2E",
    borderRadius: 20,
    padding: 32,
    alignItems: "center",
    gap: 8,
    borderWidth: 1,
    borderColor: "#1E293B",
  },
  dashed: {
    borderStyle: "dashed",
  },
  title: {
    color: "#475569",
    fontSize: 15,
    fontWeight: "700",
    textAlign: "center",
  },
  subtitle: {
    color: "#334155",
    fontSize: 12,
    textAlign: "center",
  },
});
