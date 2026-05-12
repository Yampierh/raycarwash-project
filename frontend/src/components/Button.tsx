import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import React from "react";
import {
  ActivityIndicator,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  ViewStyle,
} from "react-native";
import { Colors } from "../theme/colors";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "cta";
type Size = "sm" | "md" | "lg";

interface ButtonProps {
  title: string;
  onPress: () => void;
  variant?: Variant;
  size?: Size;
  disabled?: boolean;
  loading?: boolean;
  icon?: keyof typeof Ionicons.glyphMap;
  iconRight?: keyof typeof Ionicons.glyphMap;
  fullWidth?: boolean;
  style?: ViewStyle;
}

const SIZE_STYLES = {
  sm: { paddingVertical: 10, paddingHorizontal: 14, fontSize: 13, iconSize: 16, borderRadius: 12 },
  md: { paddingVertical: 13, paddingHorizontal: 16, fontSize: 14, iconSize: 18, borderRadius: 12 },
  lg: { paddingVertical: 17, paddingHorizontal: 20, fontSize: 15, iconSize: 20, borderRadius: 14 },
} as const;

export default function Button({
  title,
  onPress,
  variant = "primary",
  size = "md",
  disabled = false,
  loading = false,
  icon,
  iconRight,
  fullWidth = false,
  style,
}: ButtonProps) {
  const s = SIZE_STYLES[size];
  const isDisabled = disabled || loading;

  const inner = (
    <View style={styles.inner}>
      {loading ? (
        <ActivityIndicator
          color={variant === "primary" || variant === "cta" ? "#fff" : Colors.primary}
          size="small"
        />
      ) : (
        <>
          {icon && (
            <Ionicons
              name={icon}
              size={s.iconSize}
              color={getIconColor(variant)}
              style={{ marginRight: 6 }}
            />
          )}
          <Text
            style={[
              styles.text,
              { fontSize: s.fontSize },
              getTextStyle(variant),
              size === "lg" && { fontWeight: "800", letterSpacing: 1.5 },
              isDisabled && styles.textDisabled,
            ]}
          >
            {title}
          </Text>
          {iconRight && (
            <Ionicons
              name={iconRight}
              size={s.iconSize}
              color={getIconColor(variant)}
              style={{ marginLeft: 6 }}
            />
          )}
        </>
      )}
    </View>
  );

  if (variant === "cta") {
    return (
      <TouchableOpacity
        onPress={onPress}
        disabled={isDisabled}
        style={[fullWidth && styles.fullWidth, style]}
        activeOpacity={0.85}
      >
        <LinearGradient
          colors={isDisabled ? ["#1E293B", "#1E293B"] : [Colors.primary, "#60A5FA"]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 0 }}
          style={[
            styles.base,
            { paddingVertical: s.paddingVertical, paddingHorizontal: s.paddingHorizontal, borderRadius: s.borderRadius },
            fullWidth && styles.fullWidth,
          ]}
        >
          {inner}
        </LinearGradient>
      </TouchableOpacity>
    );
  }

  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={isDisabled}
      activeOpacity={0.85}
      style={[
        styles.base,
        getContainerStyle(variant),
        {
          paddingVertical: s.paddingVertical,
          paddingHorizontal: s.paddingHorizontal,
          borderRadius: s.borderRadius,
        },
        variant === "primary" && styles.shadowPrimary,
        fullWidth && styles.fullWidth,
        isDisabled && styles.disabled,
        style,
      ]}
    >
      {inner}
    </TouchableOpacity>
  );
}

function getContainerStyle(variant: Variant) {
  switch (variant) {
    case "primary":
      return { backgroundColor: Colors.primary };
    case "secondary":
      return { backgroundColor: "#161E2E", borderWidth: 1, borderColor: "#262F3F" };
    case "ghost":
      return { backgroundColor: "transparent" };
    case "danger":
      return { backgroundColor: "rgba(127,29,29,0.12)", borderWidth: 1, borderColor: "rgba(239,68,68,0.4)" };
    default:
      return {};
  }
}

function getTextStyle(variant: Variant) {
  switch (variant) {
    case "primary":
    case "cta":
      return { color: "#fff", fontWeight: "700" as const };
    case "secondary":
      return { color: "#FFFFFF", fontWeight: "600" as const };
    case "ghost":
      return { color: "#9CA3AF", fontWeight: "600" as const };
    case "danger":
      return { color: "#EF4444", fontWeight: "700" as const };
    default:
      return {};
  }
}

function getIconColor(variant: Variant): string {
  switch (variant) {
    case "primary":
    case "cta":
      return "#fff";
    case "secondary":
      return "#FFFFFF";
    case "ghost":
      return "#9CA3AF";
    case "danger":
      return "#EF4444";
    default:
      return "#fff";
  }
}

const styles = StyleSheet.create({
  base: { alignItems: "center", justifyContent: "center" },
  fullWidth: { width: "100%" },
  inner: { flexDirection: "row", alignItems: "center", justifyContent: "center" },
  text: { fontWeight: "600" as const },
  textDisabled: { opacity: 0.5 },
  disabled: { opacity: 0.45 },
  shadowPrimary: {
    shadowColor: Colors.primary,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.35,
    shadowRadius: 10,
    elevation: 6,
  },
});
