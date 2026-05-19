// Root app
const { useState, useEffect, useRef } = React;

const DEFAULTS = /*EDITMODE-BEGIN*/{
  "brand": "blue",
  "audience": "client",
  "density": "comfortable"
}/*EDITMODE-END*/;

const BRAND_COLORS = {
  blue:    { brand: "#2563eb", brand2: "#3b82f6", soft: "#dbeafe", softer: "#eff6ff", ink: "#1e3a8a" },
  emerald: { brand: "#059669", brand2: "#10b981", soft: "#d1fae5", softer: "#ecfdf5", ink: "#065f46" },
  orange:  { brand: "#ea580c", brand2: "#f97316", soft: "#fed7aa", softer: "#fff7ed", ink: "#9a3412" },
};

function applyBrand(name) {
  const c = BRAND_COLORS[name] || BRAND_COLORS.blue;
  const r = document.documentElement;
  r.style.setProperty("--brand", c.brand);
  r.style.setProperty("--brand-2", c.brand2);
  r.style.setProperty("--brand-soft", c.soft);
  r.style.setProperty("--brand-softer", c.softer);
  r.style.setProperty("--brand-ink", c.ink);
}

function applyDensity(d) {
  const r = document.documentElement;
  if (d === "compact") {
    r.style.setProperty("--sec-pad", "72px");
  } else if (d === "spacious") {
    r.style.setProperty("--sec-pad", "144px");
  } else {
    r.style.setProperty("--sec-pad", "112px");
  }
}

function App() {
  const [t, setTweak] = useTweaks(DEFAULTS);
  const [audience, setAudience] = useState(t.audience || "client");
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => { applyBrand(t.brand); }, [t.brand]);
  useEffect(() => { applyDensity(t.density); }, [t.density]);
  useEffect(() => { setAudience(t.audience); }, [t.audience]);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const handleSetAudience = (a) => {
    setAudience(a);
    setTweak("audience", a);
  };

  return (
    <>
      <Navbar audience={audience} setAudience={handleSetAudience} scrolled={scrolled} />
      <main>
        <Hero audience={audience} setAudience={handleSetAudience} />
        <TrustStrip />
        <HowItWorks audience={audience} />
        <Services />
        <Coverage />
        <ForDetailersSplit />
        <Testimonials />
        <FAQ />
        <FinalCTA audience={audience} />
      </main>
      <Footer />

      <TweaksPanel title="Tweaks">
        <TweakSection label="Audience" />
        <TweakRadio
          label="Default view"
          value={t.audience}
          options={[
            { value: "client", label: "Riders" },
            { value: "detailer", label: "Detailers" },
          ]}
          onChange={(v) => { setTweak("audience", v); }}
        />
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

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
