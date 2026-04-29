import { Ionicons, MaterialCommunityIcons } from "@expo/vector-icons";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import React from "react";

import AddVehicleScreen from "../screens/AddVehicleScreen";
import BookingScreen from "../screens/BookingScreen";
import BookingSummaryScreen from "../screens/BookingSummaryScreen";
import CompleteProfileScreen from "../screens/CompleteProfileScreen";
import ProviderTypeScreen from "../screens/ProviderTypeScreen";
import DetailerHomeScreen from "../screens/DetailerHomeScreen";
import DetailerOnboardingScreen from "../screens/DetailerOnboardingScreen";
import DetailerProfileScreen from "../screens/DetailerProfileScreen";
import DetailerSelectionScreen from "../screens/DetailerSelectionScreen";
import DetailerServicesScreen from "../screens/DetailerServicesScreen";
import EditProfileScreen from "../screens/EditProfileScreen";
import ForgotPasswordScreen from "../screens/ForgotPasswordScreen";
import HomeScreen from "../screens/HomeScreen";
import LoadingScreen from "../screens/LoadingScreen";
import LoginScreen from "../screens/LoginScreen";
import ProfileScreen from "../screens/ProfileScreen";
import RegisterScreen from "../screens/RegisterScreen";
import ScheduleScreen from "../screens/ScheduleScreen";
import SelectVehiclesScreen from "../screens/SelectVehiclesScreen";
import VehicleDetailScreen from "../screens/VehicleDetailScreen";
import VehiclesScreen from "../screens/VehiclesScreen";
import { Colors } from "../theme/colors";
import { navigationRef } from "./navigationRef";
import { RootStackParamList } from "./types";

const Stack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator();

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

export default function AppNavigator() {
  return (
    <NavigationContainer ref={navigationRef}>
      <Stack.Navigator
        initialRouteName="Loading"
        screenOptions={{ headerShown: false }}
      >
        {/* Splash */}
        <Stack.Screen name="Loading" component={LoadingScreen} />

        {/* Auth flow */}
        <Stack.Screen name="Login" component={LoginScreen} />
        <Stack.Screen name="Register" component={RegisterScreen} />
        <Stack.Screen name="ForgotPassword" component={ForgotPasswordScreen} />
        <Stack.Screen name="CompleteProfile" component={CompleteProfileScreen} />
        <Stack.Screen name="ProviderType" component={ProviderTypeScreen} />

        {/* Client tabs */}
        <Stack.Screen name="Main" component={TabNavigator} />

        {/* Detailer tabs + onboarding */}
        <Stack.Screen name="DetailerMain" component={DetailerTabNavigator} />
        <Stack.Screen name="DetailerOnboarding" component={DetailerOnboardingScreen} />
        <Stack.Screen name="DetailerServices" component={DetailerServicesScreen} />

        {/* Shared overlay screens */}
        <Stack.Screen name="AddVehicle" component={AddVehicleScreen} />
        <Stack.Screen name="VehicleDetail" component={VehicleDetailScreen} />
        <Stack.Screen name="SelectVehicles" component={SelectVehiclesScreen} />
        <Stack.Screen name="Booking" component={BookingScreen} />
        <Stack.Screen name="Schedule" component={ScheduleScreen} />
        <Stack.Screen name="DetailerSelection" component={DetailerSelectionScreen} />
        <Stack.Screen name="BookingSummary" component={BookingSummaryScreen} />
        <Stack.Screen name="EditProfile" component={EditProfileScreen} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
