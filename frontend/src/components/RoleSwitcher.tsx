/**
 * frontend/src/components/RoleSwitcher.tsx
 *
 * Master plan Phase 6 (ADR-003). Renders a segmented control that
 * lets a multi-role user swap which role the next JWT carries. On
 * success the new token pair is persisted to SecureStore + Zustand
 * and navigation resets into the appropriate stack so the user lands
 * inside the correct role context.
 *
 * Rendered only when `availableRoles.length > 1` — a single-role user
 * has nothing to switch between, so the component returns null to
 * avoid taking real estate on their hub.
 */
import { Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";
import React, { useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import {
  switchActiveRole,
  type SwitchableRole,
} from "../services/active-role.service";
import { useAuthStore } from "../store/authStore";
import { Colors } from "../theme/colors";
import {
  getRefreshToken,
  saveRefreshToken,
  saveToken,
} from "../utils/storage";

interface RoleSwitcherProps {
  /** Roles the user actually holds (e.g. ["client", "detailer"]). */
  availableRoles: string[];
  /** Current active role from the JWT (or last switch). */
  currentRole: SwitchableRole;
  /**
   * Optional override for which stacks to navigate into for each role.
   * Defaults: client -> "Main", detailer -> "DetailerMain", mechanic ->
   * "Main" (no mechanic-specific shell yet — backend ships in E3, UI
   * lands later).
   */
  stackForRole?: Partial<Record<SwitchableRole, string>>;
}

const DEFAULT_STACKS: Record<SwitchableRole, string> = {
  client:   "Main",
  detailer: "DetailerMain",
  mechanic: "Main",
};

const ROLE_LABELS: Record<SwitchableRole, string> = {
  client:   "Customer",
  detailer: "Detailer",
  mechanic: "Mechanic",
};

const ROLE_ICONS: Record<SwitchableRole, {
  family: "ionicons" | "material";
  name: string;
}> = {
  client:   { family: "ionicons", name: "person-outline" },
  detailer: { family: "ionicons", name: "sparkles-outline" },
  mechanic: { family: "material", name: "wrench-outline" },
};

const SWITCHABLE: readonly SwitchableRole[] = ["client", "detailer", "mechanic"];


export default function RoleSwitcher({
  availableRoles,
  currentRole,
  stackForRole,
}: RoleSwitcherProps) {
  const navigation = useNavigation<any>();
  const [switching, setSwitching] = useState<SwitchableRole | null>(null);

  const switchable = useMemo<SwitchableRole[]>(
    () => SWITCHABLE.filter((r) => availableRoles.includes(r)),
    [availableRoles],
  );

  if (switchable.length < 2) {
    // Nothing to switch between.
    return null;
  }

  const handleSelect = async (target: SwitchableRole) => {
    if (target === currentRole || switching) return;

    setSwitching(target);
    try {
      const refresh = await getRefreshToken();
      if (!refresh) {
        throw new Error("Refresh token missing — please sign in again.");
      }
      const result = await switchActiveRole(target, refresh);

      // Persist BOTH tokens — the old refresh is dead after this call.
      await Promise.all([
        saveToken(result.access_token),
        saveRefreshToken(result.refresh_token),
      ]);
      // Zustand snapshot used by WebSocket + sync paths.
      useAuthStore.getState().setTokens(result.access_token, [result.active_role]);

      // Reset navigation into the destination stack so screens that
      // assume a particular role get a clean tree.
      const stacks = { ...DEFAULT_STACKS, ...(stackForRole ?? {}) };
      const dest = stacks[result.active_role] ?? "Main";
      navigation.reset({ index: 0, routes: [{ name: dest }] });
    } catch (err: any) {
      const code = err?.response?.data?.error?.code;
      const fallback = err?.message ?? "Could not switch role. Please try again.";
      const message =
        code === "permission_denied"
          ? `You don't have the ${target} role yet. Complete onboarding first.`
          : code === "kyc_required"
            ? "Complete identity verification before activating this role."
            : fallback;
      Alert.alert("Switch failed", message);
    } finally {
      setSwitching(null);
    }
  };

  return (
    <View style={styles.container}>
      {switchable.map((role) => {
        const isActive = role === currentRole;
        const isSwitching = switching === role;
        const icon = ROLE_ICONS[role];
        return (
          <TouchableOpacity
            key={role}
            style={[styles.segment, isActive && styles.segmentActive]}
            onPress={() => handleSelect(role)}
            disabled={isActive || switching !== null}
            activeOpacity={0.7}
          >
            {isSwitching ? (
              <ActivityIndicator size="small" color={Colors.primary} />
            ) : icon.family === "ionicons" ? (
              <Ionicons
                name={icon.name as any}
                size={18}
                color={isActive ? "#FFFFFF" : Colors.secondaryText}
              />
            ) : (
              <MaterialCommunityIcons
                name={icon.name as any}
                size={18}
                color={isActive ? "#FFFFFF" : Colors.secondaryText}
              />
            )}
            <Text
              style={[
                styles.label,
                isActive ? styles.labelActive : styles.labelInactive,
              ]}
            >
              {ROLE_LABELS[role]}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    backgroundColor: "#161E2E",
    borderRadius: 999,
    padding: 4,
    borderWidth: 1,
    borderColor: "#1E293B",
  },
  segment: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 999,
    gap: 6,
  },
  segmentActive: {
    backgroundColor: Colors.primary,
  },
  label: {
    fontSize: 13,
    fontWeight: "600",
  },
  labelActive: {
    color: "#FFFFFF",
  },
  labelInactive: {
    color: Colors.secondaryText,
  },
});
