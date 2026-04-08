import type { UserProfile as BaseUserProfile } from "../services/user.service";
import type { Vehicle } from "../services/vehicle.service";

/**
 * Coincide exactamente con UserRole de FastAPI en el backend.
 * Usamos un Enum para evitar errores de escritura ("client" vs "Client").
 */
export enum UserRole {
  CLIENT = "client",
  DETAILER = "detailer",
  ADMIN = "admin",
}

/**
 * Extendemos la interfaz del perfil para asegurar que el rol sea tipado
 */
export interface UserProfile extends BaseUserProfile {
  role: UserRole;
}

export type RootStackParamList = {
  Login: undefined;
  // Register puede recibir un rol sugerido (opcional)
  Register: { initialRole?: UserRole } | undefined;

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
