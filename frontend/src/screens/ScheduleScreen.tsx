import { Ionicons } from "@expo/vector-icons";
import React, { useState } from "react";
import {
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { Calendar } from "react-native-calendars";
import { SafeAreaView } from "react-native-safe-area-context";
import Button from "../components/Button";
import { Colors } from "../theme/colors";

export default function ScheduleScreen({ route, navigation }: any) {
  const { selections, selectedVehicles, total } = route.params || {};
  const [selectedDate, setSelectedDate] = useState<string | null>(null);

  const handleContinue = (date: string | null) => {
    navigation.navigate("DetailerSelection", { selections, selectedVehicles, total, date });
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Ionicons name="chevron-back" size={24} color="white" />
        </TouchableOpacity>
        <View>
          <Text style={styles.headerTitle}>Schedule</Text>
          <Text style={styles.headerStep}>Step 3 of 4</Text>
        </View>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scroll}>
        {/* ASAP card */}
        <View style={styles.asapCard}>
          <View style={styles.asapLeft}>
            <Ionicons name="flash" size={22} color="#F59E0B" />
            <View style={{ marginLeft: 12, flex: 1 }}>
              <Text style={styles.asapTitle}>ASAP Mode</Text>
              <Text style={styles.asapSubtitle}>
                Skip scheduling — we'll find the nearest available detailer right now
              </Text>
            </View>
          </View>
          <Button title="GO" onPress={() => handleContinue(null)} variant="primary" size="sm" style={{ backgroundColor: "#F59E0B", minWidth: 56 }} />
        </View>

        <View style={styles.dividerRow}>
          <View style={styles.dividerLine} />
          <Text style={styles.dividerText}>OR PICK A DATE</Text>
          <View style={styles.dividerLine} />
        </View>

        <View style={styles.sectionHeader}>
          <Ionicons name="calendar-outline" size={16} color={Colors.primary} />
          <Text style={styles.sectionTitle}>SELECT DATE</Text>
        </View>

        <View style={styles.calendarContainer}>
          <Calendar
            theme={{
              backgroundColor: "transparent",
              calendarBackground: "transparent",
              textSectionTitleColor: "#64748B",
              selectedDayBackgroundColor: Colors.primary,
              selectedDayTextColor: "#0B0F1A",
              todayTextColor: Colors.primary,
              dayTextColor: "#F8FAFC",
              textDisabledColor: "#334155",
              monthTextColor: "#F8FAFC",
              arrowColor: Colors.primary,
              textDayFontWeight: "500",
              textMonthFontWeight: "700",
              textDayHeaderFontWeight: "600",
              textDayFontSize: 14,
            }}
            minDate={new Date().toISOString().split("T")[0]}
            onDayPress={(day: any) => setSelectedDate(day.dateString)}
            markedDates={selectedDate ? { [selectedDate]: { selected: true, disableTouchEvent: true } } : {}}
          />
        </View>

        {selectedDate && (
          <View style={styles.selectionPreview}>
            <Ionicons name="checkmark-circle" size={18} color={Colors.primary} />
            <Text style={styles.previewText}>{selectedDate} selected</Text>
          </View>
        )}
      </ScrollView>

      <View style={styles.footer}>
        <Button
          title={selectedDate ? "FIND DETAILERS" : "SELECT A DATE"}
          onPress={() => handleContinue(selectedDate)}
          variant="cta"
          size="lg"
          fullWidth
          disabled={!selectedDate}
          iconRight="chevron-forward"
        />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0B0F1A" },
  header: {
    flexDirection: "row", alignItems: "center",
    justifyContent: "space-between", paddingHorizontal: 20, paddingVertical: 15,
  },
  backBtn: {
    backgroundColor: "#161E2E", padding: 10,
    borderRadius: 12, borderWidth: 1, borderColor: "#262F3F",
  },
  headerTitle: { color: "white", fontSize: 20, fontWeight: "800", textAlign: "center" },
  headerStep: { color: Colors.primary, fontSize: 12, fontWeight: "600", textAlign: "center" },
  scroll: { paddingHorizontal: 20, paddingBottom: 140 },
  asapCard: {
    backgroundColor: "#1C1A0E", borderRadius: 16,
    borderWidth: 1, borderColor: "#F59E0B40",
    padding: 18, flexDirection: "row",
    alignItems: "center", justifyContent: "space-between", marginBottom: 24,
  },
  asapLeft: { flex: 1, flexDirection: "row", alignItems: "center" },
  asapTitle: { color: "#F59E0B", fontWeight: "800", fontSize: 15 },
  asapSubtitle: { color: "#94A3B8", fontSize: 12, marginTop: 2 },
  dividerRow: { flexDirection: "row", alignItems: "center", marginBottom: 24, gap: 10 },
  dividerLine: { flex: 1, height: 1, backgroundColor: "#262F3F" },
  dividerText: { color: "#64748B", fontSize: 11, fontWeight: "700", letterSpacing: 1 },
  sectionHeader: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 14 },
  sectionTitle: { color: "#94A3B8", fontSize: 12, fontWeight: "700", letterSpacing: 1.5 },
  calendarContainer: {
    backgroundColor: "#161E2E", borderRadius: 20, padding: 10,
    borderWidth: 1, borderColor: "#262F3F",
  },
  selectionPreview: {
    marginTop: 16, flexDirection: "row", alignItems: "center",
    justifyContent: "center", backgroundColor: "#1E293B",
    padding: 12, borderRadius: 12, gap: 10,
    borderWidth: 1, borderColor: Colors.primary + "40",
  },
  previewText: { color: "white", fontWeight: "600", fontSize: 14 },
  footer: {
    position: "absolute", bottom: 0, width: "100%",
    paddingHorizontal: 20, paddingVertical: 20,
    backgroundColor: "rgba(11, 15, 26, 0.95)",
    borderTopWidth: 1, borderTopColor: "#1E293B",
  },
});
