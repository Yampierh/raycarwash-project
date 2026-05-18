/**
 * frontend/src/screens/PaymentMethodsScreen.tsx
 *
 * Profile → Payment methods. Lists Stripe-mirrored cards, lets the
 * user set a default, remove, or add a new card via the Stripe SDK
 * SetupIntent flow.
 *
 * Add flow:
 *   1. Tap "Add card" → useCreateSetupIntent posts to backend with a
 *      fresh Idempotency-Key. Backend mints a SetupIntent at Stripe and
 *      returns client_secret + publishable key.
 *   2. We render the Stripe <CardField/> + "Save card" button.
 *   3. confirmSetupIntent(client_secret) on the SDK.
 *   4. Stripe fires payment_method.attached → backend webhook → local
 *      PaymentMethod row materializes; React Query refetches on focus.
 *
 * Stripe SDK is lazy-required like in App.tsx so Expo Go (no custom dev
 * client) doesn't crash on import.
 *
 * Delete + setup-intent are step-up gated server-side. The apiClient
 * interceptor surfaces StepUpRequiredError; this screen forwards the
 * user to the security re-auth flow then retries.
 */
import { Ionicons } from "@expo/vector-icons";
import React, { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Modal,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import Button from "../components/Button";
import EmptyState from "../components/EmptyState";
import {
  useCreateSetupIntent,
  useDeletePaymentMethod,
  usePaymentMethods,
  useSetDefaultPaymentMethod,
} from "../hooks/useProfileResources";
import { StepUpRequiredError } from "../lib/api-error";
import type { PaymentMethod } from "../services/payment-methods.service";
import { Colors } from "../theme/colors";

// Lazy-require the Stripe SDK so Expo Go doesn't crash on import.
let StripeSDK: any = null;
try {
  StripeSDK = require("@stripe/stripe-react-native");
} catch {
  StripeSDK = null;
}

function brandIcon(brand: string | null): keyof typeof Ionicons.glyphMap {
  if (!brand) return "card-outline";
  return "card-outline";
}

function formatExpiry(month: number | null, year: number | null): string {
  if (!month || !year) return "";
  return `${String(month).padStart(2, "0")}/${String(year).slice(-2)}`;
}

interface RowProps {
  pm: PaymentMethod;
  onSetDefault: () => void;
  onDelete: () => void;
  busy: boolean;
}

function PaymentRow({ pm, onSetDefault, onDelete, busy }: RowProps) {
  return (
    <View style={styles.card}>
      <View style={styles.cardHead}>
        <View style={styles.iconBox}>
          <Ionicons name={brandIcon(pm.brand)} size={20} color={Colors.primary} />
        </View>
        <View style={styles.cardHeadText}>
          <View style={styles.titleRow}>
            <Text style={styles.brand}>
              {pm.brand ? pm.brand.toUpperCase() : "Card"}
              {pm.last4 ? ` •••• ${pm.last4}` : ""}
            </Text>
            {pm.is_default ? (
              <View style={styles.defaultBadge}>
                <Text style={styles.defaultBadgeText}>Default</Text>
              </View>
            ) : null}
          </View>
          <Text style={styles.expiry}>
            {formatExpiry(pm.exp_month, pm.exp_year) || "—"}
          </Text>
        </View>
      </View>

      <View style={styles.actions}>
        {!pm.is_default ? (
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

// ─── Add-card modal ───────────────────────────────────────────────────────────

interface AddCardModalProps {
  visible: boolean;
  onClose: () => void;
  onSaved: () => void;
}

function AddCardModal({ visible, onClose, onSaved }: AddCardModalProps) {
  const setupIntent = useCreateSetupIntent();
  const [cardComplete, setCardComplete] = useState(false);
  const [confirming, setConfirming] = useState(false);

  const confirmHook = StripeSDK?.useConfirmSetupIntent?.();
  const CardField = StripeSDK?.CardField;

  // Reset on close.
  React.useEffect(() => {
    if (!visible) {
      setCardComplete(false);
      setupIntent.reset();
    }
  }, [visible]);

  React.useEffect(() => {
    if (visible && !setupIntent.data && !setupIntent.isPending) {
      // Idempotency-Key only needs to be unique per (user, endpoint,
      // body-hash) — H2 also hashes the request body server-side, so a
      // collision here is harmless. ts+random is plenty.
      const key = `pm-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
      setupIntent.mutate(key);
    }
  }, [visible]);

  const handleConfirm = async () => {
    if (!setupIntent.data || !confirmHook) {
      Alert.alert(
        "Stripe SDK unavailable",
        "Saved cards require a custom dev client build of the app.",
      );
      return;
    }
    setConfirming(true);
    try {
      const { setupIntent: si, error } = await confirmHook.confirmSetupIntent(
        setupIntent.data.client_secret,
        { paymentMethodType: "Card" },
      );
      if (error) {
        Alert.alert("Card could not be saved", error.message);
        return;
      }
      if (si?.status === "Succeeded") {
        onSaved();
      }
    } catch (exc: any) {
      Alert.alert("Card could not be saved", exc?.message ?? "Unknown error.");
    } finally {
      setConfirming(false);
    }
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent
      onRequestClose={onClose}
    >
      <View style={styles.modalBackdrop}>
        <View style={styles.modalBody}>
          <View style={styles.modalHead}>
            <Text style={styles.modalTitle}>Add card</Text>
            <TouchableOpacity onPress={onClose} hitSlop={12}>
              <Ionicons name="close" size={22} color={Colors.text} />
            </TouchableOpacity>
          </View>

          {setupIntent.isPending ? (
            <View style={styles.center}>
              <ActivityIndicator color={Colors.primary} />
              <Text style={styles.modalHint}>Preparing secure form…</Text>
            </View>
          ) : setupIntent.isError ? (
            <View style={styles.center}>
              <Text style={styles.errorText}>
                {setupIntent.error instanceof StepUpRequiredError
                  ? "We need to verify it's you before saving a card."
                  : "Could not prepare the form. Please try again."}
              </Text>
            </View>
          ) : !CardField ? (
            <View style={styles.center}>
              <Text style={styles.errorText}>
                The Stripe card form is not available in Expo Go. Build a
                custom dev client to test saved cards.
              </Text>
            </View>
          ) : (
            <View>
              <CardField
                postalCodeEnabled
                placeholders={{ number: "4242 4242 4242 4242" }}
                cardStyle={cardFieldStyle}
                style={styles.cardField}
                onCardChange={(d: any) => setCardComplete(!!d?.complete)}
              />
              <Button
                title="Save card"
                onPress={handleConfirm}
                disabled={!cardComplete || confirming}
                loading={confirming}
                style={{ marginTop: 16 }}
              />
              <Text style={styles.modalHint}>
                Your card details go directly to Stripe — we never see your
                full number.
              </Text>
            </View>
          )}
        </View>
      </View>
    </Modal>
  );
}

const cardFieldStyle = {
  backgroundColor: "#FFFFFF",
  textColor: "#0B0F1A",
  placeholderColor: "#9CA3AF",
  borderRadius: 10,
  fontSize: 16,
};

// ─── Main screen ──────────────────────────────────────────────────────────────

export default function PaymentMethodsScreen({ navigation }: any) {
  const query = usePaymentMethods();
  const setDefault = useSetDefaultPaymentMethod();
  const remove = useDeletePaymentMethod();
  const [addOpen, setAddOpen] = useState(false);
  const busy = setDefault.isPending || remove.isPending;

  const handleSetDefault = (pm: PaymentMethod) => {
    setDefault.mutate(pm.id, {
      onError: () => Alert.alert("Could not update", "Please try again."),
    });
  };

  const handleDelete = (pm: PaymentMethod) => {
    Alert.alert(
      "Remove card?",
      `Card ending in ${pm.last4 ?? "····"} will be detached from your account.`,
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Remove",
          style: "destructive",
          onPress: () =>
            remove.mutate(pm.id, {
              onError: (err) => {
                if (err instanceof StepUpRequiredError) {
                  Alert.alert(
                    "Verification required",
                    "Confirm it's you to remove a saved card.",
                  );
                  return;
                }
                Alert.alert("Could not remove", "Please try again.");
              },
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
        <Text style={styles.headerTitle}>Payment methods</Text>
        <TouchableOpacity
          onPress={() => setAddOpen(true)}
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
          <Text style={styles.errorText}>Could not load your cards.</Text>
        </View>
      ) : !query.data || query.data.length === 0 ? (
        <EmptyState
          icon="credit-card-outline"
          title="No saved cards"
          subtitle="Add a card so booking is one tap."
          action={{ label: "Add card", onPress: () => setAddOpen(true) }}
        />
      ) : (
        <FlatList
          contentContainerStyle={styles.list}
          data={query.data}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <PaymentRow
              pm={item}
              onSetDefault={() => handleSetDefault(item)}
              onDelete={() => handleDelete(item)}
              busy={busy}
            />
          )}
        />
      )}

      <AddCardModal
        visible={addOpen}
        onClose={() => setAddOpen(false)}
        onSaved={() => {
          setAddOpen(false);
          // Webhook materializes the row asynchronously; refetch a few
          // seconds later to surface it without manual pull-to-refresh.
          setTimeout(() => query.refetch(), 1500);
        }}
      />
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
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: 24 },
  errorText: { color: Colors.secondaryText, textAlign: "center" },
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
  brand: { color: Colors.text, fontSize: 16, fontWeight: "600" },
  expiry: { color: Colors.secondaryText, marginTop: 4, fontSize: 13 },
  defaultBadge: {
    backgroundColor: "rgba(16,185,129,0.15)",
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 8,
  },
  defaultBadgeText: { color: "#10B981", fontSize: 11, fontWeight: "600" },
  actions: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 14 },
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

  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.55)",
    justifyContent: "flex-end",
  },
  modalBody: {
    backgroundColor: Colors.card,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 20,
    minHeight: 320,
  },
  modalHead: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 16,
  },
  modalTitle: { color: Colors.text, fontSize: 18, fontWeight: "700" },
  modalHint: {
    color: "#64748B",
    fontSize: 12,
    marginTop: 12,
    textAlign: "center",
  },
  cardField: {
    width: "100%",
    height: 50,
    marginTop: 8,
  },
});
