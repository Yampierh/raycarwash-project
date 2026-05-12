import React from "react";
import { StyleSheet, Text, TextStyle } from "react-native";
import { TypographyScale } from "../theme/colors";

type Variant = keyof typeof TypographyScale | "muted";

interface TypographyProps {
  variant?: Variant;
  color?: string;
  style?: TextStyle;
  children: React.ReactNode;
  numberOfLines?: number;
}

const DEFAULT_COLORS: Record<string, string> = {
  h1: "#FFFFFF",
  h2: "#FFFFFF",
  h3: "#FFFFFF",
  h4: "#FFFFFF",
  body: "#FFFFFF",
  label: "#94A3B8",
  caption: "#475569",
  muted: "#334155",
};

export default function Typography({
  variant = "body",
  color,
  style,
  children,
  numberOfLines,
}: TypographyProps) {
  const scale = variant === "muted"
    ? { fontSize: 13, fontWeight: "400" as const }
    : TypographyScale[variant as keyof typeof TypographyScale];

  return (
    <Text
      style={[
        scale,
        { color: color ?? DEFAULT_COLORS[variant] ?? "#FFFFFF" },
        style,
      ]}
      numberOfLines={numberOfLines}
    >
      {children}
    </Text>
  );
}
