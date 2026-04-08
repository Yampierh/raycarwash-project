/**
 * Shared formatting helpers used across multiple screens.
 * Import from here instead of duplicating in each file.
 */

export const STATUS_COLORS: Record<string, string> = {
  pending:               "#F59E0B",
  confirmed:             "#3B82F6",
  in_progress:           "#10B981",
  completed:             "#94A3B8",
  cancelled_by_client:   "#EF4444",
  cancelled_by_detailer: "#EF4444",
  no_show:               "#64748B",
};

export const COLOR_MAP: Record<string, string> = {
  white:    "#F1F5F9",
  black:    "#1E293B",
  silver:   "#94A3B8",
  gray:     "#64748B",
  grey:     "#64748B",
  red:      "#EF4444",
  blue:     "#3B82F6",
  navy:     "#1E40AF",
  green:    "#10B981",
  yellow:   "#EAB308",
  orange:   "#F97316",
  brown:    "#78350F",
  gold:     "#D97706",
  charcoal: "#374151",
  pearl:    "#BAE6FD",
  burgundy: "#881337",
  purple:   "#7C3AED",
  teal:     "#0D9488",
  maroon:   "#7F1D1D",
  beige:    "#D4B896",
};

export function getInitials(name?: string): string {
  if (!name) return "U";
  return name.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase();
}

export function getMemberStatus(washes: number): { label: string; color: string } {
  if (washes >= 15) return { label: "Platinum", color: "#E2E8F0" };
  if (washes >= 8)  return { label: "Gold",     color: "#F59E0B" };
  if (washes >= 3)  return { label: "Silver",   color: "#94A3B8" };
  return                    { label: "Bronze",   color: "#B45309" };
}

export function getCarIcon(bodyClass = ""): string {
  const bc = bodyClass.toLowerCase();
  if (bc.includes("suv") || bc.includes("crossover")) return "car-estate";
  if (bc.includes("pickup") || bc.includes("truck"))  return "car-pickup";
  if (bc.includes("van"))                              return "van-utility";
  if (bc.includes("hatch"))                            return "car-hatchback";
  if (bc.includes("coupe") || bc.includes("sport"))   return "car-sports";
  return "car-side";
}

export function getColorDot(color = ""): string {
  return COLOR_MAP[color.toLowerCase()] ?? "#475569";
}

export function getCountdown(iso: string): string {
  const diff = new Date(iso).getTime() - Date.now();
  if (diff <= 0) return "Now";
  const d = Math.floor(diff / 86400000);
  const h = Math.floor((diff % 86400000) / 3600000);
  const m = Math.floor((diff % 3600000) / 60000);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

export function formatPrice(cents: number | null | undefined): string {
  return cents != null ? `$${(cents / 100).toFixed(0)}` : "—";
}

export function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

export function getFirstName(name?: string): string {
  return name?.split(" ")[0] || "there";
}
