import { Ionicons } from "@expo/vector-icons";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import React, { useEffect, useRef, useState } from "react";
import {
  Animated,
  Easing,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useAppNavigation } from "../hooks/useAppNavigation";
import { useAppointmentSocket } from "../hooks/useAppointmentSocket";
import { useAuthStore } from "../store/authStore";
import { Colors } from "../theme/colors";
import type { RootStackParamList } from "../navigation/types";

type Props = NativeStackScreenProps<RootStackParamList, "Searching">;

export default function SearchingScreen({ route }: Props) {
  const { appointment_id } = route.params;
  const navigation = useAppNavigation();
  const token = useAuthStore((s) => s.token);

  const [statusMsg, setStatusMsg] = useState("Finding your detailer…");
  const [failed, setFailed] = useState(false);

  const pulse = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, { toValue: 1.3, duration: 700, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
        Animated.timing(pulse, { toValue: 1,   duration: 700, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [pulse]);

  useAppointmentSocket({
    appointmentId: appointment_id,
    onStatusChange: (newStatus) => {
      if (newStatus === "confirmed") {
        setStatusMsg("Detailer confirmed!");
        setTimeout(() => navigation.navigate("Main"), 800);
      } else if (newStatus === "no_detailer_found") {
        setFailed(true);
        setStatusMsg("No detailer available right now.");
      }
    },
  });

  return (
    <SafeAreaView style={styles.container}>
      {!failed ? (
        <>
          <Animated.View style={[styles.pulseRing, { transform: [{ scale: pulse }] }]}>
            <View style={styles.innerCircle}>
              <Ionicons name="car-sport" size={40} color={Colors.primary} />
            </View>
          </Animated.View>
          <Text style={styles.title}>{statusMsg}</Text>
          <Text style={styles.sub}>We're matching you with the best detailer nearby.</Text>
          <Text style={styles.apptId}>ID: {appointment_id.slice(0, 8).toUpperCase()}</Text>
        </>
      ) : (
        <>
          <Ionicons name="sad-outline" size={64} color="#EF4444" />
          <Text style={styles.failTitle}>No Detailer Found</Text>
          <Text style={styles.sub}>All nearby detailers are unavailable right now. Please try again soon.</Text>
          <TouchableOpacity style={styles.retryBtn} onPress={() => navigation.navigate("Main")}>
            <Text style={styles.retryText}>Back to Home</Text>
          </TouchableOpacity>
        </>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0B0F19", alignItems: "center", justifyContent: "center", gap: 20, padding: 32 },
  pulseRing: {
    width: 140, height: 140, borderRadius: 70,
    backgroundColor: `${Colors.primary}22`,
    alignItems: "center", justifyContent: "center",
  },
  innerCircle: {
    width: 100, height: 100, borderRadius: 50,
    backgroundColor: `${Colors.primary}44`,
    alignItems: "center", justifyContent: "center",
  },
  title: { color: "#F8FAFC", fontSize: 22, fontWeight: "700", textAlign: "center" },
  failTitle: { color: "#EF4444", fontSize: 22, fontWeight: "700", textAlign: "center" },
  sub: { color: "#64748B", fontSize: 14, textAlign: "center", lineHeight: 22 },
  apptId: { color: "#334155", fontSize: 12 },
  retryBtn: { backgroundColor: Colors.primary, borderRadius: 12, paddingHorizontal: 28, paddingVertical: 14, marginTop: 8 },
  retryText: { color: "#0B0F19", fontWeight: "700", fontSize: 15 },
});
