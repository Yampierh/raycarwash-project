/**
 * frontend/src/screens/FavoritesScreen.tsx
 *
 * Profile → Favorite providers. Pinned detailers surfaced for fast
 * re-booking. Tap → opens DetailerSelection (existing screen) with the
 * provider pre-selected. Long-press → unfavorite confirmation.
 *
 * Adding a favorite happens from the booking-completion flow, not
 * here — so this screen is read-mostly + delete.
 */
import { Ionicons } from "@expo/vector-icons";
import React from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Image,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import EmptyState from "../components/EmptyState";
import {
  useFavorites,
  useRemoveFavorite,
} from "../hooks/useProfileResources";
import type { FavoriteProvider } from "../services/favorites.service";
import { Colors } from "../theme/colors";

interface RowProps {
  fav: FavoriteProvider;
  onUnfavorite: () => void;
}

function FavoriteRow({ fav, onUnfavorite }: RowProps) {
  const title = fav.display_name ?? fav.business_name ?? "Detailer";
  return (
    <View style={styles.card}>
      {fav.avatar_url ? (
        <Image source={{ uri: fav.avatar_url }} style={styles.avatar} />
      ) : (
        <View style={[styles.avatar, styles.avatarPlaceholder]}>
          <Ionicons name="person" size={22} color="#475569" />
        </View>
      )}
      <View style={styles.text}>
        <Text style={styles.name}>{title}</Text>
        {fav.business_name && fav.display_name && fav.business_name !== title ? (
          <Text style={styles.business}>{fav.business_name}</Text>
        ) : null}
        {fav.rating ? (
          <View style={styles.ratingRow}>
            <Ionicons name="star" size={12} color="#FBBF24" />
            <Text style={styles.rating}>{fav.rating.toFixed(1)}</Text>
          </View>
        ) : null}
      </View>
      <TouchableOpacity onPress={onUnfavorite} style={styles.unfavBtn} hitSlop={10}>
        <Ionicons name="heart-dislike-outline" size={20} color="#EF4444" />
      </TouchableOpacity>
    </View>
  );
}

export default function FavoritesScreen({ navigation }: any) {
  const query = useFavorites();
  const remove = useRemoveFavorite();

  const handleRemove = (fav: FavoriteProvider) => {
    const name = fav.display_name ?? fav.business_name ?? "this provider";
    Alert.alert(
      "Unpin provider?",
      `${name} will no longer appear in your favorites.`,
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Remove",
          style: "destructive",
          onPress: () =>
            remove.mutate(fav.provider_user_id, {
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
        <Text style={styles.headerTitle}>Favorites</Text>
        <View style={{ width: 32 }} />
      </View>

      {query.isLoading ? (
        <View style={styles.center}>
          <ActivityIndicator color={Colors.primary} />
        </View>
      ) : query.isError ? (
        <View style={styles.center}>
          <Text style={styles.errorText}>Could not load favorites.</Text>
        </View>
      ) : !query.data || query.data.length === 0 ? (
        <EmptyState
          icon="heart-outline"
          title="No favorite providers yet"
          subtitle="Detailers you book regularly will appear here so you can re-book in one tap."
        />
      ) : (
        <FlatList
          contentContainerStyle={styles.list}
          data={query.data}
          keyExtractor={(item) => item.provider_user_id}
          renderItem={({ item }) => (
            <FavoriteRow fav={item} onUnfavorite={() => handleRemove(item)} />
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
  headerTitle: {
    flex: 1,
    color: Colors.text,
    fontSize: 18,
    fontWeight: "600",
    textAlign: "center",
  },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  errorText: { color: Colors.secondaryText },
  list: { padding: 16, gap: 10 },
  card: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    backgroundColor: Colors.card,
    borderRadius: 14,
    padding: 12,
    borderWidth: 1,
    borderColor: "#1E293B",
  },
  avatar: { width: 48, height: 48, borderRadius: 24 },
  avatarPlaceholder: {
    backgroundColor: "#1A2233",
    alignItems: "center",
    justifyContent: "center",
  },
  text: { flex: 1 },
  name: { color: Colors.text, fontSize: 15, fontWeight: "600" },
  business: { color: Colors.secondaryText, fontSize: 12, marginTop: 2 },
  ratingRow: { flexDirection: "row", alignItems: "center", gap: 4, marginTop: 4 },
  rating: { color: "#FBBF24", fontSize: 12, fontWeight: "600" },
  unfavBtn: { padding: 6 },
});
