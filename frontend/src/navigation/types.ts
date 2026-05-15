import type { UserProfile as BaseUserProfile } from "../services/user.service";
import type { Vehicle } from "../services/vehicle.service";

export const UserRole = {
  CLIENT: "client",
  DETAILER: "detailer",
  ADMIN: "admin",
} as const;

export type UserRoleType = (typeof UserRole)[keyof typeof UserRole];

export interface UserProfile extends BaseUserProfile {
  roles: string[];
}

export type RootStackParamList = {
  // Splash
  Loading: undefined;

  // Auth flow
  Login: undefined;
  Register: undefined;
  ForgotPassword: undefined;
  CompleteProfile: { service_type?: string };
  ProviderType: undefined;

  // Client tabs
  Main: undefined;

  // Detailer tabs
  DetailerMain: undefined;

  // Shared booking flow (client)
  AddVehicle: undefined;
  VehicleDetail: { vehicle: Vehicle };
  SelectVehicles: undefined;
  Booking: { selectedVehicles: Vehicle[] };
  Schedule: {
    selections: Record<string, unknown>;
    selectedVehicles: Vehicle[];
    total: number;
  };
  DetailerSelection: {
    selections: Record<string, unknown>;
    selectedVehicles: Vehicle[];
    total: number;
    date: string | null;
  };
  BookingSummary: {
    selections: Record<string, unknown>;
    selectedVehicles: Vehicle[];
    total: number;
    detailerId: string;
    detailerName: string;
    scheduledTime: string;
    serviceAddress: string;
    lat: number;
    lng: number;
  };
  EditProfile: { user?: UserProfile; focusAddress?: boolean } | undefined;

  // Security center (Phase 3)
  Security: undefined;
  ChangeEmail: undefined;
  ChangePhone: undefined;
  // TODO(phase 3 follow-up): add ChangePassword, TwoFactorSetup,
  // Passkeys, Sessions screens. SecurityScreen already navigates to
  // these names; they need the routes to exist before that compiles.
  ChangePassword: undefined;
  TwoFactorSetup: undefined;
  Passkeys: undefined;
  Sessions: undefined;

  // Detailer onboarding / services
  DetailerOnboarding: undefined;
  DetailerServices: undefined;

  // Tab screen names (nested inside Main / DetailerMain)
  Home: undefined;
  Vehicles: undefined;
  Profile: undefined;
  DetailerHome: undefined;
  DetailerProfile: undefined;
};
