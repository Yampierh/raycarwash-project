import { Ionicons } from "@expo/vector-icons";
import React, { useEffect, useRef } from "react";
import { Animated, StyleSheet, TextInput, TouchableOpacity, View } from "react-native";
import { Colors } from "../theme/colors";

export interface AnimatedInputProps {
  value: string;
  onChangeText: (t: string) => void;
  placeholder: string;
  icon: keyof typeof Ionicons.glyphMap;
  secureTextEntry?: boolean;
  keyboardType?: "email-address" | "phone-pad" | "default";
  autoCapitalize?: "none" | "words" | "sentences";
  returnKeyType?: "next" | "done" | "go";
  onSubmitEditing?: () => void;
  error?: boolean;
  editable?: boolean;
  rightElement?: React.ReactNode;
  autoFocus?: boolean;
}

/**
 * TextInput with animated border glow on focus.
 * Border transitions: dark (#1E293B) → primary blue on focus, red on error.
 */
export default function AnimatedInput({
  value,
  onChangeText,
  placeholder,
  icon,
  secureTextEntry = false,
  keyboardType = "default",
  autoCapitalize = "none",
  returnKeyType,
  onSubmitEditing,
  error,
  editable = true,
  rightElement,
  autoFocus,
}: AnimatedInputProps) {
  // -1 = error (red), 0 = idle (dark), 1 = focused (primary)
  const borderAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (error) {
      Animated.timing(borderAnim, {
        toValue: -1,
        duration: 150,
        useNativeDriver: false,
      }).start();
    } else {
      Animated.timing(borderAnim, {
        toValue: 0,
        duration: 150,
        useNativeDriver: false,
      }).start();
    }
  }, [error]);

  const borderColor = borderAnim.interpolate({
    inputRange: [-1, 0, 1],
    outputRange: ["#EF4444", "#1E293B", Colors.primary],
  });

  const handleFocus = () =>
    !error &&
    Animated.timing(borderAnim, {
      toValue: 1,
      duration: 180,
      useNativeDriver: false,
    }).start();

  const handleBlur = () =>
    !error &&
    Animated.timing(borderAnim, {
      toValue: 0,
      duration: 180,
      useNativeDriver: false,
    }).start();

  return (
    <Animated.View
      style={[
        styles.inputWrapper,
        { borderColor },
        !editable && styles.inputDisabled,
      ]}
    >
      <Ionicons
        name={icon}
        size={18}
        color={editable ? "#475569" : "#334155"}
        style={styles.inputIcon}
      />
      <TextInput
        style={[styles.input, !editable && styles.inputDisabledText]}
        placeholder={placeholder}
        placeholderTextColor="#334155"
        value={value}
        onChangeText={onChangeText}
        secureTextEntry={secureTextEntry}
        keyboardType={keyboardType}
        autoCapitalize={autoCapitalize}
        returnKeyType={returnKeyType}
        onSubmitEditing={onSubmitEditing}
        onFocus={handleFocus}
        onBlur={handleBlur}
        editable={editable}
        autoFocus={autoFocus}
      />
      {rightElement}
    </Animated.View>
  );
}

// ── Eye toggle helper ─────────────────────────────────────────────────────────

interface EyeBtnProps {
  visible: boolean;
  onPress: () => void;
}

export function EyeToggle({ visible, onPress }: EyeBtnProps) {
  return (
    <TouchableOpacity onPress={onPress} style={styles.eyeBtn}>
      <Ionicons
        name={visible ? "eye-off-outline" : "eye-outline"}
        size={18}
        color="#475569"
      />
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  inputWrapper: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#111827",
    borderRadius: 14,
    borderWidth: 1,
  },
  inputDisabled: { backgroundColor: "#1E293B" },
  inputIcon: { marginLeft: 14 },
  input: { flex: 1, color: "#fff", padding: 15, fontSize: 15 },
  inputDisabledText: { color: "#64748B" },
  eyeBtn: { padding: 14 },
});
