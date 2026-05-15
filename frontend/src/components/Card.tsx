import React from "react";
import {
  StyleProp,
  StyleSheet,
  TouchableOpacity,
  View,
  ViewStyle,
} from "react-native";

interface CardProps {
  children: React.ReactNode;
  onPress?: () => void;
  padding?: number;
  // StyleProp<ViewStyle> accepts a single style object OR an array of them
  // (with `null`/`false`/`undefined` short-circuits) — same as every other
  // React Native built-in. The bare `ViewStyle` previously here broke
  // composed-style callers like `style={[styles.x, isOn && styles.y]}`.
  style?: StyleProp<ViewStyle>;
  activeOpacity?: number;
}

export default function Card({ children, onPress, padding = 16, style, activeOpacity = 0.8 }: CardProps) {
  const cardStyle = [styles.card, { padding }, style];

  if (onPress) {
    return (
      <TouchableOpacity onPress={onPress} style={cardStyle} activeOpacity={activeOpacity}>
        {children}
      </TouchableOpacity>
    );
  }

  return <View style={cardStyle}>{children}</View>;
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#161E2E",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#262F3F",
  },
});
