import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import React, { useState } from "react";
import {
  Dimensions,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { Calendar } from "react-native-calendars";
import { SafeAreaView } from "react-native-safe-area-context";
import { Colors } from "../theme/colors";

const { width } = Dimensions.get("window");

export default function ScheduleScreen({ route, navigation }: any) {
  const { selections, selectedVehicles, total } = route.params || {};

  const [selectedDate, setSelectedDate] = useState<string | null>(null);

  const handleContinue = (date: string | null) => {
    navigation.navigate("DetailerSelection", {
      selections,
      selectedVehicles,
      total,
      date,
    });
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          style={styles.backBtn}
        >
          <Ionicons name="chevron-back" size={24} color="white" />
        </TouchableOpacity>
        <View>
          <Text style={styles.headerTitle}>Schedule</Text>
          <Text style={styles.headerStep}>Step 3 of 4</Text>
        </View>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scroll}
      >
        <View style={styles.asapCard}>
          <View style={styles.asapLeft}>
            <Ionicons name="flash" size={22} color="#F59E0B" />
            <View style={{ marginLeft: 12 }}>
              <Text style={styles.asapTitle}>ASAP Mode</Text>
              <Text style={styles.asapSubtitle}>
                Skip scheduling — we'll find the nearest available detailer right now
              </Text>
            </View>
          </View>
          <TouchableOpacity
            style={styles.asapBtn}
            onPress={() => handleContinue(null)}
          >
            <Text style={styles.asapBtnText}>GO</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.dividerRow}>
          <View style={styles.dividerLine} />
          <Text style={styles.dividerText}>OR PICK A DATE</Text>
          <View style={styles.dividerLine} />
        </View>

        <View style={styles.sectionHeader}>
          <Ionicons name="calendar-outline" size={18} color={Colors.primary} />
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
              textMonthFontWeight: "bold",
              textDayHeaderFontWeight: "600",
              textDayFontSize: 14,
            }}
            minDate={new Date().toISOString().split("T")[0]}
            onDayPress={(day: any) => setSelectedDate(day.dateString)}
            markedDates={
              selectedDate
                ? { [selectedDate]: { selected: true, disableTouchEvent: true } }
                : {}
            }
          />
        </View>

        {selectedDate && (
          <View style={styles.selectionPreview}>
            <Ionicons name="checkmark-circle" size={20} color={Colors.primary} />
            <Text style={styles.previewText}>{selectedDate} selected</Text>
          </View>
        )}
      </ScrollView>

      <View style={styles.footer}>
        <TouchableOpacity
          disabled={!selectedDate}
          onPress={() => handleContinue(selectedDate)}
          style={styles.shadowWrapper}
        >
          <LinearGradient
            colors={
              selectedDate
                ? [Colors.primary, "#60A5FA"]
                : ["#1E293B", "#1E293B"]
            }
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={styles.nextBtn}
          >
            <Text
              style={[
                styles.nextText,
                !selectedDate && { color: "#475569" },
              ]}
            >
              {selectedDate ? "FIND DETAILERS" : "SELECT A DATE"}
            </Text>
            <Ionicons
              name="chevron-forward"
              size={20}
              color={selectedDate ? "#0F172A" : "#475569"}
            />
          </LinearGradient>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0B0F1A" },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingVertical: 15,
  },
  backBtn: {
    backgroundColor: "#161E2E",
    padding: 10,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#262F3F",
  },
  headerTitle: {
    color: "white",
    fontSize: 20,
    fontWeight: "800",
    textAlign: "center",
  },
  headerStep: {
    color: Colors.primary,
    fontSize: 12,
    fontWeight: "600",
    textAlign: "center",
  },
  scroll: { padding: 20, paddingBottom: 140 },
  asapCard: {
    backgroundColor: "#1C1A0E",
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "#F59E0B40",
    padding: 18,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 24,
  },
  asapLeft: { flex: 1, flexDirection: "row", alignItems: "center" },
  asapTitle: {
    color: "#F59E0B",
    fontWeight: "800",
    fontSize: 15,
  },
  asapSubtitle: {
    color: "#94A3B8",
    fontSize: 12,
    marginTop: 2,
    flexShrink: 1,
  },
  asapBtn: {
    backgroundColor: "#F59E0B",
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 12,
    marginLeft: 12,
  },
  asapBtnText: {
    color: "#0B0F1A",
    fontWeight: "900",
    fontSize: 13,
  },
  dividerRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 24,
    gap: 10,
  },
  dividerLine: { flex: 1, height: 1, backgroundColor: "#262F3F" },
  dividerText: {
    color: "#64748B",
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 1,
  },
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 15,
  },
  sectionTitle: {
    color: "#94A3B8",
    fontSize: 13,
    fontWeight: "800",
    letterSpacing: 1.5,
  },
  calendarContainer: {
    backgroundColor: "#161E2E",
    borderRadius: 24,
    padding: 10,
    borderWidth: 1,
    borderColor: "#262F3F",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.3,
    shadowRadius: 20,
  },
  selectionPreview: {
    marginTop: 20,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#1E293B",
    padding: 12,
    borderRadius: 12,
    gap: 10,
    borderWidth: 1,
    borderColor: Colors.primary + "40",
  },
  previewText: { color: "white", fontWeight: "600", fontSize: 14 },
  footer: {
    position: "absolute",
    bottom: 0,
    width: "100%",
    padding: 25,
    backgroundColor: "rgba(11, 15, 26, 0.95)",
    borderTopWidth: 1,
    borderTopColor: "#161E2E",
  },
  shadowWrapper: {
    shadowColor: Colors.primary,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
  },
  nextBtn: {
    padding: 20,
    borderRadius: 20,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: 10,
  },
  nextText: {
    color: "#0F172A",
    fontWeight: "900",
    fontSize: 17,
    letterSpacing: 0.5,
  },
});
