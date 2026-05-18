/**
 * frontend/src/screens/AddressesScreen.tsx
 *
 * Profile → Addresses. Lists active UserAddress rows, lets the user
 * set a default, edit, delete, or add a new one.
 *
 * Consumes useAddresses + useSetDefaultAddress + useDeleteAddress from
 * useProfileResources. Adding / editing routes to AddressFormScreen
 * with the optional address payload as a param.
 */
import { Ionicons } from "@expo/vector-icons";
import React from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import EmptyState from "../components/EmptyState";
import {
  useAddresses,
  useDeleteAddress,
  useSetDefaultAddress,
} from "../hooks/useProfileResources";
import type { Address } from "../services/addresses.service";
import { Colors } from "../theme/colors";

function formatAddress(a: Address): string {
  const line2 = a.line2 ? `, ${a.line2}` : "";
  return `${a.line1}${line2}, ${a.city}, ${a.state} ${a.zip_code}`;
}

interface RowProps {
  address: Address;
  onEdit: () => void;
  onSetDefault: () => void;
  onDelete: () => void;
  busy: boolean;
}

function AddressRow({ address, onEdit, onSetDefault, onDelete, busy }: RowProps) {
  return (
    <View style={styles.card}>
      <View style={styles.cardHead}>
        <View style={styles.iconBox}>
          <Ionicons name="location" size={18} color={Colors.primary} />
        </View>
        <View style={styles.cardHeadText}>
          <View style={styles.titleRow}>
            <Text style={styles.label}>{address.label ?? "Address"}</Text>
            {address.is_default ? (
              <View style={styles.defaultBadge}>
                <Text style={styles.defaultBadgeText}>Default</Text>
              </View>
            ) : null}
          </View>
          <Text style={styles.body}>{formatAddress(address)}</Text>
          {address.notes ? (
            <Text style={styles.notes}>{address.notes}</Text>
          ) : null}
        </View>
      </View>

      <View style={styles.actions}>
        <TouchableOpacity style={styles.actionBtn} onPress={onEdit} disabled={busy}>
          <Ionicons name="create-outline" size={16} color={Colors.text} />
          <Text style={styles.actionText}>Edit</Text>
        </TouchableOpacity>
        {!address.is_default ? (
          <TouchableOpacity
            style={styles.actionBtn}
            onPress={onSetDefault}
            disabled={busy}
          >
            <Ionicons name="star-outline" size={16} color={Colors.text} />
            <Text style={styles.actionText}>Make default</Text>
          </TouchableOpacity>
        ) : null}
        <TouchableOpacity
          style={[styles.actionBtn, styles.actionBtnDanger]}
          onPress={onDelete}
          disabled={busy}
        >
          <Ionicons name="trash-outline" size={16} color="#EF4444" />
          <Text style={[styles.actionText, styles.actionTextDanger]}>Remove</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

export default function AddressesScreen({ navigation }: any) {
  const query = useAddresses();
  const setDefault = useSetDefaultAddress();
  const remove = useDeleteAddress();
  const busy = setDefault.isPending || remove.isPending;

  const handleSetDefault = (a: Address) => {
    setDefault.mutate(a.id, {
      onError: () => Alert.alert("Could not update", "Please try again."),
    });
  };

  const handleDelete = (a: Address) => {
    Alert.alert(
      "Remove address?",
      `${a.label ?? "This address"} will be removed from your saved list.`,
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Remove",
          style: "destructive",
          onPress: () =>
            remove.mutate(a.id, {
              onError: () =>
                Alert.alert("Could not remove", "Please try again."),
            }),
        },
      ],
    );
  };

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          style={styles.backBtn}
          hitSlop={12}
        >
          <Ionicons name="chevron-back" size={24} color={Colors.text} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Addresses</Text>
        <TouchableOpacity
          onPress={() => navigation.navigate("AddressForm", { address: null })}
          style={styles.addBtn}
          hitSlop={12}
        >
          <Ionicons name="add" size={24} color={Colors.primary} />
        </TouchableOpacity>
      </View>

      {query.isLoading ? (
        <View style={styles.center}>
          <ActivityIndicator color={Colors.primary} />
        </View>
      ) : query.isError ? (
        <View style={styles.center}>
          <Text style={styles.errorText}>Could not load your addresses.</Text>
          <TouchableOpacity onPress={() => query.refetch()}>
            <Text style={styles.retryText}>Try again</Text>
          </TouchableOpacity>
        </View>
      ) : !query.data || query.data.length === 0 ? (
        <EmptyState
          icon="map-marker-outline"
          title="No saved addresses"
          subtitle="Add an address so booking is one tap away."
          action={{
            label: "Add address",
            onPress: () =>
              navigation.navigate("AddressForm", { address: null }),
          }}
        />
      ) : (
        <FlatList
          contentContainerStyle={styles.list}
          data={query.data}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <AddressRow
              address={item}
              onEdit={() =>
                navigation.navigate("AddressForm", { address: item })
              }
              onSetDefault={() => handleSetDefault(item)}
              onDelete={() => handleDelete(item)}
              busy={busy}
            />
          )}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.background },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  backBtn: { padding: 4 },
  addBtn: { padding: 4 },
  headerTitle: {
    flex: 1,
    color: Colors.text,
    fontSize: 18,
    fontWeight: "600",
    textAlign: "center",
  },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  errorText: { color: Colors.secondaryText, marginBottom: 8 },
  retryText: { color: Colors.primary, fontWeight: "600" },
  list: { padding: 16, gap: 12 },
  card: {
    backgroundColor: Colors.card,
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: "#1E293B",
  },
  cardHead: { flexDirection: "row", gap: 12 },
  iconBox: {
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: "rgba(59,130,246,0.12)",
    alignItems: "center",
    justifyContent: "center",
  },
  cardHeadText: { flex: 1 },
  titleRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  label: { color: Colors.text, fontSize: 16, fontWeight: "600" },
  defaultBadge: {
    backgroundColor: "rgba(16,185,129,0.15)",
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 8,
  },
  defaultBadgeText: { color: "#10B981", fontSize: 11, fontWeight: "600" },
  body: { color: Colors.secondaryText, marginTop: 4, fontSize: 14 },
  notes: { color: "#64748B", marginTop: 4, fontSize: 12, fontStyle: "italic" },
  actions: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
    marginTop: 14,
  },
  actionBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 8,
    backgroundColor: "#1A2233",
  },
  actionBtnDanger: { backgroundColor: "rgba(239,68,68,0.1)" },
  actionText: { color: Colors.text, fontSize: 13, fontWeight: "500" },
  actionTextDanger: { color: "#EF4444" },
});
