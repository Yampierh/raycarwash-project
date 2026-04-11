import type { UserProfile as BaseUserProfile } from "../services/user.service";
import type { Vehicle } from "../services/vehicle.service";

/**
 * Role constants for convenience.
 * Note: Backend now uses roles as an array (e.g., ["client"], ["detailer"])
 */
export const UserRole = {
  CLIENT: "client",
  DETAILER: "detailer",
  ADMIN: "admin",
} as const;

export type UserRoleType = (typeof UserRole)[keyof typeof UserRole];

/**
 * Extendemos la interfaz del perfil para usar roles como array
 */
export interface UserProfile extends BaseUserProfile {
  roles: string[];
}

export type RootStackParamList = {
  // Splash
  Loading: undefined;

  // Auth flow
  Login: undefined;
  CompleteProfile: {
    tempToken: string;
    role?: string;
    identifier: string;
    identifierType: string;
  };

  // Flujo Principal de Clientes
  Main: undefined;

  // Flujo Principal de Detailers
  DetailerMain: undefined;

  // Pantallas de Proceso (Comunes o específicas)
  AddVehicle: undefined;
  VehicleDetail: { vehicle: Vehicle };
  SelectVehicles: undefined;
  Booking: { selectedVehicles: Vehicle[] };
  Schedule: {
    selections: Record<string, any>;
    selectedVehicles: Vehicle[];
    total: number;
  };
  DetailerSelection: {
    selections: Record<string, any>;
    selectedVehicles: Vehicle[];
    total: number;
    date: string | null;
  };
  BookingSummary: {
    selections: Record<string, any>;
    selectedVehicles: Vehicle[];
    total: number;
    detailerId: string;
    detailerName: string;
    scheduledTime: string; // ISO 8601 UTC
    serviceAddress: string;
    lat: number;
    lng: number;
  };
  EditProfile: { user: UserProfile; focusAddress?: boolean };
  // Detailer routes
  DetailerOnboarding: undefined;
  DetailerServices: undefined;
  // Client tabs
  Home: undefined;
  Vehicles: undefined;
  Profile: undefined;
  // Detailer tabs (nested inside DetailerMain)
  DetailerHome: undefined;
  DetailerProfile: undefined;
};
