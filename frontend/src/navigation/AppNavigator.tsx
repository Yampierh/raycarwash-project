import { Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import React from "react";

// Client screens
import AddVehicleScreen from "../screens/AddVehicleScreen";
import BookingScreen from "../screens/BookingScreen";
import BookingSummaryScreen from "../screens/BookingSummaryScreen";
import DetailerSelectionScreen from "../screens/DetailerSelectionScreen";
import EditProfileScreen from "../screens/EditProfileScreen";
import HomeScreen from "../screens/HomeScreen";
import LoginScreen from "../screens/LoginScreen";
import ProfileScreen from "../screens/ProfileScreen";
import RegisterScreen from "../screens/RegisterScreen";
import ScheduleScreen from "../screens/ScheduleScreen";
import SelectVehiclesScreen from "../screens/SelectVehiclesScreen";
import VehicleDetailScreen from "../screens/VehicleDetailScreen";
import VehiclesScreen from "../screens/VehiclesScreen";
// Detailer screens
import DetailerHomeScreen from "../screens/DetailerHomeScreen";
import DetailerOnboardingScreen from "../screens/DetailerOnboardingScreen";
import DetailerProfileScreen from "../screens/DetailerProfileScreen";
import DetailerServicesScreen from "../screens/DetailerServicesScreen";
import { Colors } from "../theme/colors";
import { navigationRef } from "./navigationRef";
import { RootStackParamList } from "./types";

const Stack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator();

// Client tab navigator
function TabNavigator() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: "#0B0F19",
          borderTopColor: "#1E293B",
          height: 60,
          paddingBottom: 8,
        },
        tabBarActiveTintColor: Colors.primary,
        tabBarInactiveTintColor: "#475569",
      }}
    >
      <Tab.Screen
        name="Home"
        component={HomeScreen}
        options={{
          tabBarIcon: ({ color }) => (
            <Ionicons name="home" size={24} color={color} />
          ),
        }}
      />
      <Tab.Screen
        name="Vehicles"
        component={VehiclesScreen}
        options={{
          tabBarIcon: ({ color }) => (
            <Ionicons name="car" size={26} color={color} />
          ),
        }}
      />
      <Tab.Screen
        name="Profile"
        component={ProfileScreen}
        options={{
          tabBarIcon: ({ color }) => (
            <Ionicons name="person" size={24} color={color} />
          ),
        }}
      />
    </Tab.Navigator>
  );
}

// Detailer tab navigator
function DetailerTabNavigator() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: "#0B0F1A",
          borderTopColor: "#1E293B",
          height: 85,
          paddingBottom: 25,
        },
        tabBarActiveTintColor: Colors.primary,
        tabBarInactiveTintColor: "#475569",
      }}
    >
      <Tab.Screen
        name="DetailerHome"
        component={DetailerHomeScreen}
        options={{
          tabBarLabel: "Operations",
          tabBarIcon: ({ color }) => (
            <MaterialCommunityIcons name="briefcase-check" size={24} color={color} />
          ),
        }}
      />
      <Tab.Screen
        name="DetailerProfile"
        component={DetailerProfileScreen}
        options={{
          tabBarLabel: "Profile",
          tabBarIcon: ({ color }) => (
            <Ionicons name="person" size={24} color={color} />
          ),
        }}
      />
    </Tab.Navigator>
  );
}

// Root stack navigator
export default function AppNavigator() {
  return (
    <NavigationContainer ref={navigationRef}>
      <Stack.Navigator
        initialRouteName="Login"
        screenOptions={{ headerShown: false }}
      >
        {/* Flujo de Autenticación */}
        <Stack.Screen name="Login" component={LoginScreen} />
        <Stack.Screen name="Register" component={RegisterScreen} />

        {/* Client tabs */}
        <Stack.Screen name="Main" component={TabNavigator} />
        {/* Detailer tabs */}
        <Stack.Screen name="DetailerMain" component={DetailerTabNavigator} />
        <Stack.Screen name="DetailerOnboarding" component={DetailerOnboardingScreen} />
        <Stack.Screen name="DetailerServices" component={DetailerServicesScreen} />
        {/* Shared overlay screens (client booking flow + profile) */}
        <Stack.Screen name="AddVehicle" component={AddVehicleScreen} />
        <Stack.Screen name="VehicleDetail" component={VehicleDetailScreen} />
        <Stack.Screen name="SelectVehicles" component={SelectVehiclesScreen} />
        <Stack.Screen name="Schedule" component={ScheduleScreen} />
        <Stack.Screen
          name="DetailerSelection"
          component={DetailerSelectionScreen}
        />
        <Stack.Screen name="BookingSummary" component={BookingSummaryScreen} />
        <Stack.Screen name="Booking" component={BookingScreen} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
