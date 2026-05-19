// Detailers page app shell
const { useState: useStateD, useEffect: useEffectD } = React;

const DET_DEFAULTS = /*EDITMODE-BEGIN*/{
  "brand": "blue",
  "density": "comfortable"
}/*EDITMODE-END*/;

const DET_BRAND_COLORS = {
  blue:    { brand: "#2563eb", brand2: "#3b82f6", soft: "#dbeafe", softer: "#eff6ff", ink: "#1e3a8a" },
  emerald: { brand: "#059669", brand2: "#10b981", soft: "#d1fae5", softer: "#ecfdf5", ink: "#065f46" },
  orange:  { brand: "#ea580c", brand2: "#f97316", soft: "#fed7aa", softer: "#fff7ed", ink: "#9a3412" },
};

function applyDetBrand(name) {
  const c = DET_BRAND_COLORS[name] || DET_BRAND_COLORS.blue;
  const r = document.documentElement;
  r.style.setProperty("--brand", c.brand);
  r.style.setProperty("--brand-2", c.brand2);
  r.style.setProperty("--brand-soft", c.soft);
  r.style.setProperty("--brand-softer", c.softer);
  r.style.setProperty("--brand-ink", c.ink);
}
function applyDetDensity(d) {
  const r = document.documentElement;
  if (d === "compact") r.style.setProperty("--sec-pad", "72px");
  else if (d === "spacious") r.style.setProperty("--sec-pad", "144px");
  else r.style.setProperty("--sec-pad", "112px");
}

function DetApp() {
  const [t, setTweak] = useTweaks(DET_DEFAULTS);
  const [scrolled, setScrolled] = useStateD(false);

  useEffectD(() => { applyDetBrand(t.brand); }, [t.brand]);
  useEffectD(() => { applyDetDensity(t.density); }, [t.density]);

  useEffectD(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <>
      <DetNavbar scrolled={scrolled} />
      <main>
        <DetHero />
        <EarningsCalc />
        <WeekInLife />
        <Tools />
        <Requirements />
        <DetTestimonials />
        <DetFAQ />
        <DetCTA />
      </main>
      <Footer />

      <TweaksPanel title="Tweaks">
        <TweakSection label="Brand color" />
        <TweakRadio
          label="Accent"
          value={t.brand}
          options={[
            { value: "blue", label: "Blue" },
            { value: "emerald", label: "Green" },
            { value: "orange", label: "Orange" },
          ]}
          onChange={(v) => setTweak("brand", v)}
        />
        <TweakSection label="Density" />
        <TweakRadio
          label="Spacing"
          value={t.density}
          options={[
            { value: "compact", label: "Tight" },
            { value: "comfortable", label: "Default" },
            { value: "spacious", label: "Roomy" },
          ]}
          onChange={(v) => setTweak("density", v)}
        />
      </TweaksPanel>
    </>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<DetApp />);
