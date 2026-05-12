import React from "react";
import { StyleSheet, Text, TouchableOpacity, View, ViewStyle } from "react-native";
import { Colors } from "../theme/colors";

interface SectionHeaderProps {
  title: string;
  action?: { label: string; onPress: () => void };
  style?: ViewStyle;
  /** When true, title is uppercase with letter spacing (default) */
  uppercase?: boolean;
}

export default function SectionHeader({ title, action, style, uppercase = true }: SectionHeaderProps) {
  return (
    <View style={[styles.row, style]}>
      <Text style={[styles.title, uppercase && styles.titleUpper]}>{title}</Text>
      {action && (
        <TouchableOpacity onPress={action.onPress} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
          <Text style={styles.action}>{action.label}</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 20,
    marginBottom: 14,
  },
  title: {
    color: "#FFFFFF",
    fontSize: 13,
    fontWeight: "800",
  },
  titleUpper: {
    letterSpacing: 0.6,
    textTransform: "uppercase",
  },
  action: {
    color: Colors.primary,
    fontSize: 13,
  },
});
