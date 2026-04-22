import DateTimePicker from '@react-native-community/datetimepicker';
import { useNavigation } from '@react-navigation/native';
import React, { useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Platform,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';

interface Props {
  route: {
    params: {
      fareId: string;
      fareToken: string;
      estimatedPriceCents: number;
      surgeMultiplier: number;
      serviceId: string;
      vehicleSizes: string[];
      clientLat: number;
      clientLng: number;
    };
  };
}

type BookingMode = 'asap' | 'scheduled';

export default function ConfirmBookingScreen({ route }: Props) {
  const {
    fareId,
    fareToken,
    estimatedPriceCents,
    surgeMultiplier,
    clientLat,
    clientLng,
  } = route.params;

  const navigation = useNavigation<any>();
  const [mode, setMode] = useState<BookingMode>('asap');
  const [scheduledTime, setScheduledTime] = useState(new Date(Date.now() + 60 * 60 * 1000));
  const [showPicker, setShowPicker] = useState(false);
  const [loading, setLoading] = useState(false);

  const price = (estimatedPriceCents / 100).toFixed(2);
  const isSurge = surgeMultiplier > 1.0;

  const handleConfirm = async () => {
    setLoading(true);
    try {
      const body: Record<string, unknown> = {
        fare_token:  fareToken,
        mode,
        client_lat:  clientLat,
        client_lng:  clientLng,
      };
      if (mode === 'scheduled') {
        body.preferred_time = scheduledTime.toISOString();
      }

      const response = await fetch('/api/v2/rides/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail?.message ?? 'Booking failed');
      }

      const data = await response.json();
      navigation.replace('Searching', { appointmentId: data.appointment_id });
    } catch (err: any) {
      Alert.alert('Booking Error', err.message ?? 'Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Confirm Booking</Text>

      {/* Price summary */}
      <View style={styles.priceCard}>
        <Text style={styles.priceLabel}>Estimated Total</Text>
        <Text style={styles.price}>${price}</Text>
        {isSurge && (
          <Text style={styles.surgeNote}>
            Includes {surgeMultiplier.toFixed(1)}× surge pricing
          </Text>
        )}
      </View>

      {/* Mode selector */}
      <Text style={styles.sectionLabel}>When do you need service?</Text>
      <View style={styles.modeRow}>
        <TouchableOpacity
          style={[styles.modeButton, mode === 'asap' && styles.modeButtonActive]}
          onPress={() => setMode('asap')}
        >
          <Text style={[styles.modeButtonText, mode === 'asap' && styles.modeButtonTextActive]}>
            ASAP
          </Text>
          <Text style={[styles.modeSubText, mode === 'asap' && styles.modeButtonTextActive]}>
            Now
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.modeButton, mode === 'scheduled' && styles.modeButtonActive]}
          onPress={() => setMode('scheduled')}
        >
          <Text style={[styles.modeButtonText, mode === 'scheduled' && styles.modeButtonTextActive]}>
            Schedule
          </Text>
          <Text style={[styles.modeSubText, mode === 'scheduled' && styles.modeButtonTextActive]}>
            Pick a time
          </Text>
        </TouchableOpacity>
      </View>

      {/* Scheduled time picker */}
      {mode === 'scheduled' && (
        <TouchableOpacity style={styles.timeRow} onPress={() => setShowPicker(true)}>
          <Text style={styles.timeLabel}>Selected time</Text>
          <Text style={styles.timeValue}>
            {scheduledTime.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
          </Text>
        </TouchableOpacity>
      )}

      {showPicker && (
        <DateTimePicker
          value={scheduledTime}
          mode="datetime"
          minimumDate={new Date()}
          onChange={(_evt, date) => {
            setShowPicker(Platform.OS === 'ios');
            if (date) setScheduledTime(date);
          }}
        />
      )}

      {/* Confirm button */}
      <TouchableOpacity
        style={[styles.confirmButton, loading && styles.confirmButtonDisabled]}
        onPress={handleConfirm}
        disabled={loading}
      >
        {loading
          ? <ActivityIndicator color="#fff" />
          : <Text style={styles.confirmButtonText}>Book Now — ${price}</Text>
        }
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container:              { flex: 1, padding: 24, backgroundColor: '#fff' },
  title:                  { fontSize: 26, fontWeight: '700', marginBottom: 24, color: '#1a1a1a' },
  priceCard:              { backgroundColor: '#F5F3FF', borderRadius: 16, padding: 20, alignItems: 'center', marginBottom: 28 },
  priceLabel:             { color: '#6B46C1', fontSize: 14, fontWeight: '600', marginBottom: 4 },
  price:                  { fontSize: 48, fontWeight: '800', color: '#1a1a1a' },
  surgeNote:              { color: '#856404', fontSize: 13, marginTop: 6 },
  sectionLabel:           { fontSize: 16, fontWeight: '600', color: '#1a1a1a', marginBottom: 12 },
  modeRow:                { flexDirection: 'row', gap: 12, marginBottom: 24 },
  modeButton:             { flex: 1, borderWidth: 2, borderColor: '#E5E7EB', borderRadius: 12, padding: 16, alignItems: 'center' },
  modeButtonActive:       { borderColor: '#6B46C1', backgroundColor: '#F5F3FF' },
  modeButtonText:         { fontSize: 17, fontWeight: '700', color: '#666' },
  modeButtonTextActive:   { color: '#6B46C1' },
  modeSubText:            { fontSize: 12, color: '#999', marginTop: 2 },
  timeRow:                { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 16, backgroundColor: '#F9FAFB', borderRadius: 12, marginBottom: 16 },
  timeLabel:              { color: '#666', fontSize: 15 },
  timeValue:              { color: '#6B46C1', fontWeight: '600', fontSize: 15 },
  confirmButton:          { backgroundColor: '#6B46C1', borderRadius: 14, padding: 18, alignItems: 'center', marginTop: 'auto' },
  confirmButtonDisabled:  { opacity: 0.6 },
  confirmButtonText:      { color: '#fff', fontSize: 18, fontWeight: '700' },
});
