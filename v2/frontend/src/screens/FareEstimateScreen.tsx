import React, { useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';

interface FareEstimate {
  fareId: string;
  fareToken: string;
  basePriceCents: number;
  surgeMultiplier: number;
  estimatedPriceCents: number;
  nearbyDetailersCount: number;
  expiresAt: string;
  expiresInSeconds: number;
}

interface Props {
  route: {
    params: {
      serviceId: string;
      vehicleSizes: string[];
      clientLat: number;
      clientLng: number;
      addonIds?: string[];
    };
  };
}

export default function FareEstimateScreen({ route }: Props) {
  const { serviceId, vehicleSizes, clientLat, clientLng, addonIds = [] } = route.params;
  const navigation = useNavigation<any>();
  const [estimate, setEstimate] = useState<FareEstimate | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchEstimate = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v2/fares/estimate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          service_id:   serviceId,
          vehicle_sizes: vehicleSizes,
          client_lat:   clientLat,
          client_lng:   clientLng,
          addon_ids:    addonIds,
        }),
      });
      if (!response.ok) throw new Error('Failed to fetch estimate');
      const data = await response.json();
      setEstimate({
        fareId:               data.fare_id,
        fareToken:            data.fare_token,
        basePriceCents:       data.base_price_cents,
        surgeMultiplier:      parseFloat(data.surge_multiplier),
        estimatedPriceCents:  data.estimated_price_cents,
        nearbyDetailersCount: data.nearby_detailers_count,
        expiresAt:            data.expires_at,
        expiresInSeconds:     data.expires_in_seconds,
      });
    } catch {
      Alert.alert('Error', 'Could not get fare estimate. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    fetchEstimate();
  }, []);

  const handleConfirm = () => {
    if (!estimate) return;
    navigation.navigate('ConfirmBooking', {
      fareId:              estimate.fareId,
      fareToken:           estimate.fareToken,
      estimatedPriceCents: estimate.estimatedPriceCents,
      surgeMultiplier:     estimate.surgeMultiplier,
      serviceId,
      vehicleSizes,
      clientLat,
      clientLng,
    });
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#6B46C1" />
        <Text style={styles.loadingText}>Getting your price...</Text>
      </View>
    );
  }

  if (!estimate) return null;

  const isSurge = estimate.surgeMultiplier > 1.0;
  const price = (estimate.estimatedPriceCents / 100).toFixed(2);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Your Estimate</Text>

      {isSurge && (
        <View style={styles.surgeBadge}>
          <Text style={styles.surgeText}>
            {estimate.surgeMultiplier.toFixed(1)}× High Demand
          </Text>
        </View>
      )}

      <Text style={styles.price}>${price}</Text>

      <View style={styles.infoRow}>
        <Text style={styles.infoLabel}>Detailers nearby</Text>
        <Text style={styles.infoValue}>{estimate.nearbyDetailersCount}</Text>
      </View>
      <View style={styles.infoRow}>
        <Text style={styles.infoLabel}>Offer expires in</Text>
        <Text style={styles.infoValue}>{Math.round(estimate.expiresInSeconds / 60)} min</Text>
      </View>

      <TouchableOpacity style={styles.confirmButton} onPress={handleConfirm}>
        <Text style={styles.confirmButtonText}>Confirm Price</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.refreshButton} onPress={fetchEstimate}>
        <Text style={styles.refreshButtonText}>Refresh Estimate</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container:         { flex: 1, padding: 24, backgroundColor: '#fff', justifyContent: 'center' },
  center:            { flex: 1, justifyContent: 'center', alignItems: 'center' },
  loadingText:       { marginTop: 12, color: '#666', fontSize: 16 },
  title:             { fontSize: 28, fontWeight: '700', textAlign: 'center', marginBottom: 12 },
  price:             { fontSize: 56, fontWeight: '800', textAlign: 'center', color: '#1a1a1a', marginBottom: 24 },
  surgeBadge:        { backgroundColor: '#FFF3CD', borderRadius: 8, padding: 8, alignSelf: 'center', marginBottom: 12 },
  surgeText:         { color: '#856404', fontWeight: '700', fontSize: 14 },
  infoRow:           { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: '#f0f0f0' },
  infoLabel:         { color: '#666', fontSize: 15 },
  infoValue:         { color: '#1a1a1a', fontWeight: '600', fontSize: 15 },
  confirmButton:     { backgroundColor: '#6B46C1', borderRadius: 12, padding: 16, marginTop: 32, alignItems: 'center' },
  confirmButtonText: { color: '#fff', fontSize: 18, fontWeight: '700' },
  refreshButton:     { marginTop: 12, alignItems: 'center' },
  refreshButtonText: { color: '#6B46C1', fontSize: 15 },
});
