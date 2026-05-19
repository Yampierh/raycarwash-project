// Main app — wires sidebar, header, and active view
const DASH_DEFAULTS = /*EDITMODE-BEGIN*/{
  "brand": "blue",
  "density": "comfortable",
  "startView": "overview"
}/*EDITMODE-END*/;

const DASH_BRAND_COLORS = {
  blue:    { brand: "#2563eb", brand2: "#3b82f6", soft: "#dbeafe", softer: "#eff6ff", ink: "#1e3a8a" },
  emerald: { brand: "#059669", brand2: "#10b981", soft: "#d1fae5", softer: "#ecfdf5", ink: "#065f46" },
  orange:  { brand: "#ea580c", brand2: "#f97316", soft: "#fed7aa", softer: "#fff7ed", ink: "#9a3412" },
  violet:  { brand: "#7c3aed", brand2: "#8b5cf6", soft: "#ede9fe", softer: "#f5f3ff", ink: "#5b21b6" },
};

function applyDashBrand(name) {
  const c = DASH_BRAND_COLORS[name] || DASH_BRAND_COLORS.blue;
  const r = document.documentElement;
  r.style.setProperty("--brand", c.brand);
  r.style.setProperty("--brand-2", c.brand2);
  r.style.setProperty("--brand-soft", c.soft);
  r.style.setProperty("--brand-softer", c.softer);
  r.style.setProperty("--brand-ink", c.ink);
}

function DashApp() {
  const [t, setTweak] = useTweaks(DASH_DEFAULTS);
  const [view, setView] = useS(t.startView || "overview");
  const [online, setOnline] = useS(true);

  useE(() => { applyDashBrand(t.brand); }, [t.brand]);

  // Sync view when tweak changes
  useE(() => {
    if (t.startView && t.startView !== view) {
      setView(t.startView);
    }
  }, [t.startView]);

  const VIEWS = {
    overview: ViewOverview,
    jobs: ViewJobs,
    route: ViewRoute,
    schedule: ViewSchedule,
    earnings: ViewEarnings,
    customers: ViewCustomers,
    reviews: ViewReviews,
    services: ViewServices,
    supplies: ViewSupplies,
    profile: ViewProfile,
    settings: ViewSettings,
    help: ViewHelp,
  };

  const Active = VIEWS[view] || ViewOverview;

  return (
    <>
      <div className="dash">
        <DashSidebar
          view={view}
          onView={setView}
          online={online}
          setOnline={setOnline}
        />
        <div className="dash-main">
          <DashHeader view={view} online={online} />
          <Active onView={setView} />
        </div>
      </div>

      <TweaksPanel title="Tweaks">
        <TweakSection label="Brand color" />
        <TweakRadio
          label="Accent"
          value={t.brand}
          options={[
            { value: "blue", label: "Blue" },
            { value: "emerald", label: "Green" },
            { value: "orange", label: "Orange" },
            { value: "violet", label: "Violet" },
          ]}
          onChange={(v) => setTweak("brand", v)}
        />
        <TweakSection label="Quick jump" />
        <TweakSelect
          label="Start view"
          value={t.startView}
          options={[
            { value: "overview", label: "Overview" },
            { value: "jobs", label: "Jobs" },
            { value: "route", label: "Today's route" },
            { value: "schedule", label: "Schedule" },
            { value: "earnings", label: "Earnings" },
            { value: "customers", label: "Customers" },
            { value: "reviews", label: "Reviews" },
            { value: "services", label: "Services" },
            { value: "supplies", label: "Supplies" },
            { value: "profile", label: "Profile" },
            { value: "settings", label: "Settings" },
            { value: "help", label: "Help" },
          ]}
          onChange={(v) => setTweak("startView", v)}
        />
      </TweaksPanel>
    </>
  );
}

// TweakColor falls back to plain hex strings; convert to swatch hexes
const _origColorHexes = {
  blue: "#2563eb",
  emerald: "#059669",
  orange: "#ea580c",
  violet: "#7c3aed",
};

ReactDOM.createRoot(document.getElementById("root")).render(<DashApp />);
