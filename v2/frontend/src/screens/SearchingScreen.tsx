import React, { useEffect, useRef, useState } from 'react';
import {
  Animated,
  Easing,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';

interface Props {
  route: {
    params: {
      appointmentId: string;
    };
  };
}

export default function SearchingScreen({ route }: Props) {
  const { appointmentId } = route.params;
  const navigation = useNavigation<any>();
  const [status, setStatus] = useState<'searching' | 'confirmed' | 'no_detailer_found'>('searching');

  // Pulsing animation
  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 1.25, duration: 700, useNativeDriver: true, easing: Easing.inOut(Easing.ease) }),
        Animated.timing(pulseAnim, { toValue: 1,    duration: 700, useNativeDriver: true, easing: Easing.inOut(Easing.ease) }),
      ])
    ).start();
  }, []);

  // WebSocket: listen for assignment status changes
  useEffect(() => {
    // Import WS_BASE_URL from your api service
    // Using placeholder — replace with actual import in your project
    const wsUrl = `ws://localhost:8000/ws/appointments/${appointmentId}?token=YOUR_TOKEN`;
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === 'status_change') {
        if (msg.status === 'confirmed') {
          setStatus('confirmed');
          setTimeout(() => navigation.replace('AppointmentTracking', { appointmentId }), 1000);
        } else if (msg.status === 'no_detailer_found') {
          setStatus('no_detailer_found');
        }
      }
    };

    ws.onerror = () => {};
    return () => ws.close();
  }, [appointmentId]);

  if (status === 'confirmed') {
    return (
      <View style={styles.container}>
        <Text style={styles.confirmedEmoji}>✓</Text>
        <Text style={styles.confirmedText}>Detailer Found!</Text>
        <Text style={styles.subText}>Connecting you now...</Text>
      </View>
    );
  }

  if (status === 'no_detailer_found') {
    return (
      <View style={styles.container}>
        <Text style={styles.noDetailerTitle}>No Detailers Available</Text>
        <Text style={styles.noDetailerSub}>
          There are no detailers available in your area right now.
          Please try again in a few minutes.
        </Text>
        <TouchableOpacity style={styles.retryButton} onPress={() => navigation.goBack()}>
          <Text style={styles.retryButtonText}>Try Again</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Animated.View style={[styles.pulse, { transform: [{ scale: pulseAnim }] }]}>
        <View style={styles.innerCircle}>
          <Text style={styles.carEmoji}>🚗</Text>
        </View>
      </Animated.View>

      <Text style={styles.title}>Finding Your Detailer</Text>
      <Text style={styles.subText}>
        We're matching you with the best available detailer nearby.
      </Text>

      <View style={styles.dotsContainer}>
        <AnimatedDot delay={0} />
        <AnimatedDot delay={200} />
        <AnimatedDot delay={400} />
      </View>
    </View>
  );
}

function AnimatedDot({ delay }: { delay: number }) {
  const anim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    setTimeout(() => {
      Animated.loop(
        Animated.sequence([
          Animated.timing(anim, { toValue: 1, duration: 500, useNativeDriver: true }),
          Animated.timing(anim, { toValue: 0, duration: 500, useNativeDriver: true }),
        ])
      ).start();
    }, delay);
  }, []);

  return (
    <Animated.View style={[styles.dot, { opacity: anim }]} />
  );
}

const styles = StyleSheet.create({
  container:         { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#fff', padding: 32 },
  pulse:             { width: 120, height: 120, borderRadius: 60, backgroundColor: '#EDE9FE', justifyContent: 'center', alignItems: 'center', marginBottom: 32 },
  innerCircle:       { width: 80, height: 80, borderRadius: 40, backgroundColor: '#6B46C1', justifyContent: 'center', alignItems: 'center' },
  carEmoji:          { fontSize: 36 },
  title:             { fontSize: 24, fontWeight: '700', color: '#1a1a1a', textAlign: 'center', marginBottom: 12 },
  subText:           { fontSize: 15, color: '#666', textAlign: 'center', lineHeight: 22 },
  dotsContainer:     { flexDirection: 'row', marginTop: 32, gap: 8 },
  dot:               { width: 10, height: 10, borderRadius: 5, backgroundColor: '#6B46C1' },
  confirmedEmoji:    { fontSize: 72, color: '#22C55E', textAlign: 'center' },
  confirmedText:     { fontSize: 28, fontWeight: '700', color: '#22C55E', textAlign: 'center', marginTop: 16 },
  noDetailerTitle:   { fontSize: 24, fontWeight: '700', color: '#DC2626', textAlign: 'center', marginBottom: 12 },
  noDetailerSub:     { fontSize: 15, color: '#666', textAlign: 'center', lineHeight: 22, marginBottom: 32 },
  retryButton:       { backgroundColor: '#6B46C1', borderRadius: 12, padding: 16, alignItems: 'center', width: '100%' },
  retryButtonText:   { color: '#fff', fontSize: 17, fontWeight: '700' },
});
