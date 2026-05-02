import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import React, { useState } from "react";
import {
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Colors } from "../theme/colors";

interface ServiceType {
  key: string;
  label: string;
  icon: keyof typeof Ionicons.glyphMap;
  description: string;
  enabled: boolean;
}

const SERVICE_TYPES: ServiceType[] = [
  {
    key: "detailer",
    label: "Detailer",
    icon: "car-sport-outline",
    description: "Car care & detailing services",
    enabled: true,
  },
  {
    key: "mechanic",
    label: "Mechanic",
    icon: "construct-outline",
    description: "Vehicle repair & maintenance",
    enabled: false,
  },
  {
    key: "wash",
    label: "Car Wash",
    icon: "water-outline",
    description: "Mobile car wash services",
    enabled: false,
  },
];

export default function ProviderTypeScreen({ navigation }: any) {
  const [selectedType, setSelectedType] = useState<string | null>(null);

  const handleContinue = () => {
    if (!selectedType) return;
    navigation.navigate("CompleteProfile", { service_type: selectedType });
  };

  return (
    <View style={styles.container}>
      <LinearGradient
        colors={["#060A14", "#0B0F1A", "#101828"]}
        style={StyleSheet.absoluteFill}
      />
      <SafeAreaView style={{ flex: 1 }}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
            <Ionicons name="arrow-back" size={22} color={Colors.primary} />
          </TouchableOpacity>
        </View>

        <View style={styles.content}>
          <Text style={styles.title}>What service will{"\n"}you offer?</Text>
          <Text style={styles.subtitle}>
            Choose your primary service type to set up your provider account.
          </Text>

          <View style={styles.optionsList}>
            {SERVICE_TYPES.map((type) => {
              const isSelected = selectedType === type.key;
              return (
                <TouchableOpacity
                  key={type.key}
                  style={[
                    styles.optionCard,
                    isSelected && styles.optionCardSelected,
                    !type.enabled && styles.optionCardDisabled,
                  ]}
                  onPress={() => type.enabled && setSelectedType(type.key)}
                  activeOpacity={type.enabled ? 0.75 : 1}
                  disabled={!type.enabled}
                >
                  <View style={styles.optionIcon}>
                    <Ionicons
                      name={type.icon}
                      size={28}
                      color={
                        !type.enabled
                          ? "#334155"
                          : isSelected
                          ? Colors.primary
                          : "#64748B"
                      }
                    />
                  </View>

                  <View style={styles.optionText}>
                    <Text
                      style={[
                        styles.optionLabel,
                        isSelected && styles.optionLabelSelected,
                        !type.enabled && styles.optionLabelDisabled,
                      ]}
                    >
                      {type.label}
                    </Text>
                    <Text
                      style={[
                        styles.optionDesc,
                        !type.enabled && styles.optionDescDisabled,
                      ]}
                    >
                      {type.description}
                    </Text>
                  </View>

                  {!type.enabled ? (
                    <View style={styles.comingSoonBadge}>
                      <Text style={styles.comingSoonText}>Soon</Text>
                    </View>
                  ) : isSelected ? (
                    <Ionicons name="checkmark-circle" size={22} color={Colors.primary} />
                  ) : (
                    <Ionicons name="chevron-forward" size={18} color="#334155" />
                  )}
                </TouchableOpacity>
              );
            })}
          </View>

          <TouchableOpacity
            style={[styles.continueBtn, !selectedType && styles.continueBtnDisabled]}
            onPress={handleContinue}
            disabled={!selectedType}
          >
            <Text style={styles.continueBtnText}>CONTINUE</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.clientSkipBtn}
            onPress={() => navigation.navigate("CompleteProfile")}
          >
            <Text style={styles.clientSkipText}>Continue as client instead</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: {
    paddingHorizontal: 20,
    paddingTop: 8,
    paddingBottom: 4,
  },
  backBtn: { padding: 4, alignSelf: "flex-start" },
  content: {
    flex: 1,
    paddingHorizontal: 24,
    paddingTop: 20,
  },
  title: {
    color: "#FFFFFF",
    fontSize: 28,
    fontWeight: "800",
    lineHeight: 36,
    marginBottom: 10,
  },
  subtitle: {
    color: "#64748B",
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 36,
  },
  optionsList: { gap: 12, marginBottom: 40 },
  optionCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#111827",
    borderRadius: 16,
    borderWidth: 1.5,
    borderColor: "#1E293B",
    padding: 18,
    gap: 14,
  },
  optionCardSelected: {
    borderColor: Colors.primary,
    backgroundColor: "rgba(59,130,246,0.07)",
  },
  optionCardDisabled: {
    opacity: 0.4,
  },
  optionIcon: {
    width: 44,
    height: 44,
    borderRadius: 12,
    backgroundColor: "#0B0F1A",
    alignItems: "center",
    justifyContent: "center",
  },
  optionText: { flex: 1 },
  optionLabel: {
    color: "#CBD5E1",
    fontSize: 16,
    fontWeight: "700",
    marginBottom: 3,
  },
  optionLabelSelected: { color: "#FFFFFF" },
  optionLabelDisabled: { color: "#475569" },
  optionDesc: { color: "#475569", fontSize: 12, lineHeight: 16 },
  optionDescDisabled: { color: "#334155" },
  comingSoonBadge: {
    backgroundColor: "#1E293B",
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  comingSoonText: { color: "#64748B", fontSize: 10, fontWeight: "700" },
  continueBtn: {
    backgroundColor: Colors.primary,
    padding: 17,
    borderRadius: 14,
    alignItems: "center",
    shadowColor: Colors.primary,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.35,
    shadowRadius: 10,
    elevation: 6,
  },
  continueBtnDisabled: { opacity: 0.35 },
  continueBtnText: {
    color: "#fff",
    fontWeight: "800",
    fontSize: 15,
    letterSpacing: 1.5,
  },
  clientSkipBtn: {
    alignItems: "center",
    paddingVertical: 14,
    marginTop: 4,
  },
  clientSkipText: {
    color: "#475569",
    fontSize: 13,
    fontWeight: "600",
  },
});
