import React from "react";
import {
  StyleSheet,
  TouchableOpacity,
  View,
  ViewStyle,
} from "react-native";

interface CardProps {
  children: React.ReactNode;
  onPress?: () => void;
  padding?: number;
  style?: ViewStyle;
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
