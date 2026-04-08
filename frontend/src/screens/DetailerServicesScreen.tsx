import { Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
import { useFocusEffect } from "@react-navigation/native";
import { LinearGradient } from "expo-linear-gradient";
import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useAppNavigation } from "../hooks/useAppNavigation";
import {
  DetailerServiceItem,
  getMyDetailerServices,
  updateDetailerService,
} from "../services/detailer-private.service";
import { Colors } from "../theme/colors";
import { formatPrice } from "../utils/formatters";

interface ServiceDraft extends DetailerServiceItem {
  draftPrice: string;   // cents string during editing, e.g. "1500"
  dirty: boolean;
}

function centsFromDollarString(s: string): number | null {
  const num = parseFloat(s.replace(/[^0-9.]/g, ""));
  if (isNaN(num) || num < 0) return null;
  return Math.round(num * 100);
}

export default function DetailerServicesScreen() {
  const navigation = useAppNavigation();

  const [services, setServices] = useState<ServiceDraft[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const isDirty = services.some((s) => s.dirty);

  async function loadServices() {
    setLoading(true);
    try {
      const items = await getMyDetailerServices();
      setServices(
        items.map((item) => ({
          ...item,
          draftPrice:
            item.custom_price_cents != null
              ? (item.custom_price_cents / 100).toFixed(0)
              : "",
          dirty: false,
        })),
      );
    } catch {
      Alert.alert("Error", "Could not load your services.");
    } finally {
      setLoading(false);
    }
  }

  useFocusEffect(
    useCallback(() => {
      loadServices();
    }, []),
  );

  function toggleActive(serviceId: string, val: boolean) {
    setServices((prev) =>
      prev.map((s) =>
        s.service_id === serviceId ? { ...s, is_active: val, dirty: true } : s,
      ),
    );
  }

  function setPrice(serviceId: string, val: string) {
    setServices((prev) =>
      prev.map((s) =>
        s.service_id === serviceId
          ? { ...s, draftPrice: val, dirty: true }
          : s,
      ),
    );
  }

  async function handleSave() {
    const dirtyServices = services.filter((s) => s.dirty);

    // Validate all custom prices
    for (const s of dirtyServices) {
      if (s.draftPrice !== "") {
        const cents = centsFromDollarString(s.draftPrice);
        if (cents === null) {
          Alert.alert("Invalid Price", `Enter a valid price for "${s.name}" or leave it blank to use the default.`);
          return;
        }
      }
    }

    setSaving(true);
    try {
      await Promise.all(
        dirtyServices.map((s) => {
          const custom =
            s.draftPrice !== "" ? centsFromDollarString(s.draftPrice) : null;
          return updateDetailerService(s.service_id, {
            is_active: s.is_active,
            custom_price_cents: custom,
          });
        }),
      );
      setServices((prev) => prev.map((s) => ({ ...s, dirty: false })));
      Alert.alert("Saved", "Your service catalog has been updated.");
    } catch {
      Alert.alert("Error", "Could not save changes. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.loader}>
          <ActivityIndicator size="large" color="#60A5FA" />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        keyboardVerticalOffset={80}
      >
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity
            style={styles.backBtn}
            onPress={() => navigation.goBack()}
          >
            <Ionicons name="arrow-back" size={22} color="#F1F5F9" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>My Services</Text>
          <View style={{ width: 40 }} />
        </View>

        <ScrollView
          contentContainerStyle={styles.scroll}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <Text style={styles.hint}>
            Toggle services on/off and set your own custom price. Leave the price blank to use the platform default.
          </Text>

          {services.map((svc, idx) => {
            const baseDisplay = `$${(svc.base_price_cents / 100).toFixed(0)}+`;
            return (
              <LinearGradient
                key={svc.service_id}
                colors={["#1E293B", "#0F172A"]}
                style={[styles.serviceCard, svc.dirty && styles.serviceCardDirty]}
              >
                {/* Card Header */}
                <View style={styles.cardHeader}>
                  <View style={styles.iconWrap}>
                    <MaterialCommunityIcons
                      name="car-wash"
                      size={20}
                      color={svc.is_active ? "#60A5FA" : "#334155"}
                    />
                  </View>
                  <View style={styles.cardTitleBlock}>
                    <Text style={[styles.cardTitle, !svc.is_active && styles.cardTitleInactive]}>
                      {svc.name}
                    </Text>
                    <Text style={styles.cardBase}>Base: {baseDisplay}</Text>
                  </View>
                  <Switch
                    value={svc.is_active}
                    onValueChange={(val) => toggleActive(svc.service_id, val)}
                    trackColor={{ false: "#1E293B", true: "#1D4ED8" }}
                    thumbColor={svc.is_active ? "#60A5FA" : "#475569"}
                  />
                </View>

                {/* Description */}
                {svc.description && (
                  <Text style={styles.cardDesc}>{svc.description}</Text>
                )}

                {/* Custom Price Row */}
                {svc.is_active && (
                  <View style={styles.priceRow}>
                    <Text style={styles.priceLabel}>My Price</Text>
                    <View style={styles.priceInputWrap}>
                      <Text style={styles.priceDollar}>$</Text>
                      <TextInput
                        style={styles.priceInput}
                        value={svc.draftPrice}
                        onChangeText={(v) => setPrice(svc.service_id, v.replace(/[^0-9.]/g, ""))}
                        placeholder={`${(svc.base_price_cents / 100).toFixed(0)}`}
                        placeholderTextColor="#334155"
                        keyboardType="decimal-pad"
                        maxLength={6}
                      />
                    </View>
                    {svc.draftPrice === "" && (
                      <Text style={styles.priceDefault}>using default</Text>
                    )}
                  </View>
                )}

                {svc.dirty && (
                  <View style={styles.dirtyBadge}>
                    <Text style={styles.dirtyText}>unsaved</Text>
                  </View>
                )}
              </LinearGradient>
            );
          })}

          <View style={{ height: 120 }} />
        </ScrollView>

        {/* Save Footer */}
        {isDirty && (
          <View style={styles.footer}>
            <TouchableOpacity
              style={[styles.saveBtn, saving && styles.saveBtnDisabled]}
              onPress={handleSave}
              disabled={saving}
            >
              {saving ? (
                <ActivityIndicator color="#FFFFFF" />
              ) : (
                <>
                  <Ionicons name="checkmark-circle-outline" size={18} color="#FFFFFF" />
                  <Text style={styles.saveBtnText}>Save Changes</Text>
                </>
              )}
            </TouchableOpacity>
          </View>
        )}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.background },
  loader: { flex: 1, alignItems: "center", justifyContent: "center" },

  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 12,
    justifyContent: "space-between",
  },
  backBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "#1E293B",
    alignItems: "center",
    justifyContent: "center",
  },
  headerTitle: { fontSize: 18, fontWeight: "700", color: "#F1F5F9" },

  scroll: { paddingHorizontal: 16, paddingTop: 4 },
  hint: {
    fontSize: 13,
    color: "#64748B",
    lineHeight: 18,
    marginBottom: 16,
  },

  serviceCard: {
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: "#1E293B",
  },
  serviceCardDirty: { borderColor: "#2563EB" },

  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    marginBottom: 8,
  },
  iconWrap: {
    width: 38,
    height: 38,
    borderRadius: 10,
    backgroundColor: "#0F172A",
    alignItems: "center",
    justifyContent: "center",
  },
  cardTitleBlock: { flex: 1 },
  cardTitle: { fontSize: 15, fontWeight: "700", color: "#F1F5F9" },
  cardTitleInactive: { color: "#475569" },
  cardBase: { fontSize: 12, color: "#475569", marginTop: 2 },

  cardDesc: {
    fontSize: 13,
    color: "#64748B",
    lineHeight: 18,
    marginBottom: 12,
    marginLeft: 50,
  },

  priceRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    marginTop: 8,
    marginLeft: 50,
  },
  priceLabel: { fontSize: 13, color: "#94A3B8", fontWeight: "500", width: 68 },
  priceInputWrap: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#0F172A",
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#334155",
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  priceDollar: { fontSize: 15, color: "#64748B", marginRight: 2 },
  priceInput: {
    fontSize: 15,
    fontWeight: "600",
    color: "#60A5FA",
    minWidth: 60,
    padding: 0,
  },
  priceDefault: { fontSize: 12, color: "#334155", fontStyle: "italic" },

  dirtyBadge: {
    position: "absolute",
    top: 12,
    right: 70,
    backgroundColor: "rgba(37,99,235,0.15)",
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  dirtyText: { fontSize: 10, color: "#3B82F6", fontWeight: "600" },

  footer: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    padding: 16,
    backgroundColor: Colors.background,
    borderTopWidth: 1,
    borderTopColor: "#1E293B",
  },
  saveBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: "#2563EB",
    borderRadius: 14,
    paddingVertical: 16,
  },
  saveBtnDisabled: { opacity: 0.5 },
  saveBtnText: { fontSize: 16, fontWeight: "700", color: "#FFFFFF" },
});
