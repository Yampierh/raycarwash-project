// ── Legacy keys (kept for backward compatibility) ──────────────────── //
export const Colors = {
  background: "#0B0F1A",
  card: "#121826",
  primary: "#3B82F6",
  text: "#FFFFFF",
  secondaryText: "#9CA3AF",

  // ── Semantic background tokens ──────────────────────────────────── //
  bg: {
    primary: "#0B0F1A",
    secondary: "#121826",
    elevated: "#161E2E",
    input: "#111827",
  },

  // ── Text tokens ─────────────────────────────────────────────────── //
  textColor: {
    primary: "#FFFFFF",
    secondary: "#9CA3AF",
    tertiary: "#475569",
    muted: "#334155",
  },

  // ── Border tokens ────────────────────────────────────────────────── //
  border: {
    default: "#262F3F",
    subtle: "#1E293B",
  },

  // ── Status tokens (for badges, pills, accents) ───────────────────── //
  status: {
    pending: { bg: "#F59E0B22", text: "#F59E0B", border: "#F59E0B55" },
    confirmed: { bg: "#3B82F622", text: "#3B82F6", border: "#3B82F655" },
    arrived: { bg: "#A78BFA22", text: "#A78BFA", border: "#A78BFA55" },
    in_progress: { bg: "#10B98122", text: "#10B981", border: "#10B98155" },
    completed: { bg: "#94A3B822", text: "#94A3B8", border: "#94A3B855" },
    cancelled_by_client: { bg: "#EF444422", text: "#EF4444", border: "#EF444455" },
    cancelled_by_detailer: { bg: "#EF444422", text: "#EF4444", border: "#EF444455" },
    no_show: { bg: "#64748B22", text: "#64748B", border: "#64748B55" },
    no_detailer_found: { bg: "#64748B22", text: "#64748B", border: "#64748B55" },
    searching: { bg: "#A78BFA22", text: "#A78BFA", border: "#A78BFA55" },
  },
} as const;

// ── Spacing scale (in px) ─────────────────────────────────────────── //
export const Spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
} as const;

// ── Border radius scale ───────────────────────────────────────────── //
export const Radius = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
} as const;

// ── Typography scale ──────────────────────────────────────────────── //
export const TypographyScale = {
  h1: { fontSize: 32, fontWeight: "900" as const },
  h2: { fontSize: 22, fontWeight: "800" as const },
  h3: { fontSize: 18, fontWeight: "700" as const },
  h4: { fontSize: 15, fontWeight: "700" as const },
  body: { fontSize: 14, fontWeight: "400" as const },
  label: { fontSize: 13, fontWeight: "600" as const },
  caption: { fontSize: 11, fontWeight: "400" as const },
} as const;
