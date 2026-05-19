// Mechanic page — coming-soon vertical

function MechNavbar({ scrolled }) {
  const links = [
    { href: "#services", label: "Services" },
    { href: "#how", label: "How it'll work" },
    { href: "#waitlist", label: "Waitlist" },
    { href: "#faq", label: "FAQ" },
  ];
  const pages = [
    { href: "Customer Page.html", label: "Riders" },
    { href: "Detailers Page.html", label: "Detailers" },
  ];
  return (
    <header className={"nav " + (scrolled ? "nav-scrolled" : "")}>
      <div className="nav-inner">
        <a href="Landing Page.html" className="brand">
          <span className="brand-mark">R</span>
          <span className="brand-name">RayCarWash</span>
          <span className="brand-sub">/ mechanic</span>
        </a>
        <nav className="nav-links">
          {links.map(l => (
            <a key={l.href} href={l.href}>{l.label}</a>
          ))}
          <span className="nav-sep"></span>
          {pages.map(p => (
            <a key={p.href} href={p.href} className="nav-page">{p.label}</a>
          ))}
        </nav>
        <div className="nav-right">
          <a href="#waitlist" className="btn btn-dark btn-sm">Join waitlist</a>
        </div>
      </div>
    </header>
  );
}

function MechHero() {
  const [count, setCount] = React.useState(347);
  // Auto-tick counter every few seconds for liveliness
  React.useEffect(() => {
    const id = setInterval(() => setCount(c => c + 1), 14000);
    return () => clearInterval(id);
  }, []);
  return (
    <section className="mech-hero">
      <div className="hero-grid" aria-hidden></div>
      <div className="container mech-hero-inner">
        <div className="mech-hero-text">
          <div className="mech-badge">
            <span className="mb-dot"></span>
            Q4 2026 · Beta launching in Fort Wayne
          </div>
          <h1 className="mech-h1">
            Mobile mechanic.
            <br/>
            <span className="hero-h1-accent">In your driveway.</span>
          </h1>
          <p className="mech-sub">
            Oil changes, brake jobs, diagnostics, battery swaps — done where your car
            actually lives. No towing. No waiting rooms. No "we'll call you when it's ready."
          </p>

          <form className="waitlist-form" onSubmit={(e) => { e.preventDefault(); setCount(c => c + 1); e.target.reset(); }}>
            <input type="email" required placeholder="you@example.com" className="waitlist-input" />
            <button type="submit" className="btn btn-dark btn-lg">
              Join waitlist
              <IconArrowRight size={16}/>
            </button>
          </form>
          <div className="waitlist-meta">
            <strong>{count}</strong> people in line · Fort Wayne first, expanding from there.
          </div>

          <div className="mech-bullets">
            <div><span className="mb-check"><IconCheck size={12}/></span>No upfront commitment</div>
            <div><span className="mb-check"><IconCheck size={12}/></span>Early-access pricing</div>
            <div><span className="mb-check"><IconCheck size={12}/></span>Help shape the service</div>
          </div>
        </div>
        <div className="mech-hero-art">
          <ToolboxArt />
        </div>
      </div>
    </section>
  );
}

function ToolboxArt() {
  // Stylized "service van + wrench grid" composition using SVG primitives only
  return (
    <div className="toolbox-art">
      <div className="ta-glow"></div>
      <div className="ta-grid">
        <div className="ta-tile big">
          <svg viewBox="0 0 60 60" className="ta-svg">
            <rect x="6" y="20" width="48" height="28" rx="3" fill="currentColor"/>
            <rect x="10" y="8" width="44" height="14" rx="2" fill="currentColor" opacity="0.6"/>
            <rect x="14" y="24" width="14" height="8" rx="1" fill="white"/>
            <rect x="32" y="24" width="14" height="8" rx="1" fill="white"/>
            <circle cx="18" cy="50" r="5" fill="white"/>
            <circle cx="42" cy="50" r="5" fill="white"/>
            <circle cx="18" cy="50" r="2" fill="currentColor"/>
            <circle cx="42" cy="50" r="2" fill="currentColor"/>
          </svg>
          <div className="ta-lbl">Service van</div>
        </div>
        <div className="ta-tile">
          <svg viewBox="0 0 60 60" className="ta-svg">
            <path d="M20 14 a8 8 0 0 1 12 12 l16 16 -8 8 -16-16 a8 8 0 0 1 -12-12 z" fill="currentColor"/>
          </svg>
          <div className="ta-lbl">Tools</div>
        </div>
        <div className="ta-tile">
          <svg viewBox="0 0 60 60" className="ta-svg">
            <circle cx="30" cy="30" r="20" fill="none" stroke="currentColor" strokeWidth="4"/>
            <line x1="30" y1="14" x2="30" y2="30" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/>
            <line x1="30" y1="30" x2="42" y2="36" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/>
          </svg>
          <div className="ta-lbl">~30 min</div>
        </div>
        <div className="ta-tile">
          <svg viewBox="0 0 60 60" className="ta-svg">
            <path d="M30 8 c8 0 12 6 12 12 v6 h4 v22 h-32 v-22 h4 v-6 c0-6 4-12 12-12z" fill="none" stroke="currentColor" strokeWidth="3.5"/>
            <circle cx="30" cy="38" r="3" fill="currentColor"/>
          </svg>
          <div className="ta-lbl">Insured</div>
        </div>
        <div className="ta-tile">
          <svg viewBox="0 0 60 60" className="ta-svg">
            <path d="M14 38 l8-12 8 6 8-14 8 10" fill="none" stroke="currentColor" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M14 46 l32 0" stroke="currentColor" strokeWidth="3" strokeLinecap="round" opacity="0.4"/>
          </svg>
          <div className="ta-lbl">Diagnostics</div>
        </div>
        <div className="ta-tile">
          <svg viewBox="0 0 60 60" className="ta-svg">
            <rect x="18" y="22" width="24" height="20" rx="2" fill="currentColor"/>
            <rect x="22" y="18" width="6" height="6" fill="currentColor"/>
            <rect x="32" y="18" width="6" height="6" fill="currentColor"/>
            <text x="30" y="36" textAnchor="middle" fontSize="10" fontWeight="700" fill="white">12V</text>
          </svg>
          <div className="ta-lbl">Battery</div>
        </div>
      </div>
    </div>
  );
}

function MechServices() {
  const services = [
    { name: "Oil change", price: 65, dur: "30 min", body: "Full-synthetic. Fresh filter. Disposal included." },
    { name: "Brake pads + rotors", price: 280, dur: "90 min", body: "Front or rear axle. OEM-equivalent parts." },
    { name: "Battery replacement", price: 180, dur: "20 min", body: "AGM or standard lead-acid. Includes core return." },
    { name: "Diagnostics scan", price: 75, dur: "30 min", body: "Full OBD-II read. Detailed report in the app." },
    { name: "Tire rotation", price: 35, dur: "25 min", body: "All four. Torque-spec'd. Pressure adjusted." },
    { name: "Wiper blades", price: 35, dur: "10 min", body: "Pair, installed. Right-fit guaranteed." },
    { name: "Air + cabin filters", price: 55, dur: "20 min", body: "Both replaced. Recommended every 15k miles." },
    { name: "Spark plug replacement", price: 220, dur: "60 min", body: "Full set. Iridium or platinum, your choice." },
  ];
  return (
    <section id="services" className="section section-alt">
      <div className="container">
        <div className="section-head">
          <span className="section-kicker">Services at launch</span>
          <h2 className="section-title">Eight things we'll do in your driveway.</h2>
          <p className="section-sub">Starting with the most-requested. We'll add categories based on what waitlist members ask for first.</p>
        </div>
        <div className="mech-svc-grid">
          {services.map(s => (
            <div key={s.name} className="mech-svc">
              <div className="mech-svc-head">
                <span className="mech-svc-name">{s.name}</span>
                <span className="mech-svc-price">${s.price}</span>
              </div>
              <div className="mech-svc-meta"><IconClock size={12}/> {s.dur}</div>
              <div className="mech-svc-body">{s.body}</div>
            </div>
          ))}
        </div>
        <div className="mech-svc-foot">
          <span>Don't see what you need?</span>
          <a href="#waitlist" className="link-arrow">Tell us in the waitlist form <IconArrowRight size={14}/></a>
        </div>
      </div>
    </section>
  );
}

function MechHow() {
  const steps = [
    { t: "Book in the app", b: "Pick a service. Tell us your car's year/make/model. Get a flat quote — including parts." },
    { t: "Pick a window", b: "2-hour service windows. Mechanic confirms within an hour. Same-day for emergencies." },
    { t: "We show up loaded", b: "Service van arrives with parts pre-pulled, tools racked, and a portable lift if needed." },
    { t: "Watch or walk away", b: "Live mechanic profile, certifications, photo updates. Pay only when the work passes inspection." },
  ];
  return (
    <section id="how" className="section">
      <div className="container">
        <div className="section-head">
          <span className="section-kicker">How it'll work</span>
          <h2 className="section-title">Same as detailing. Different toolkit.</h2>
          <p className="section-sub">If you've used RayCarWash for a detail, mechanic bookings will feel identical — same app, same trust system, just deeper diagnostics.</p>
        </div>
        <ol className="mech-steps">
          {steps.map((s, i) => (
            <li key={s.t}>
              <div className="ms-num">{String(i + 1).padStart(2, "0")}</div>
              <div className="ms-body">
                <div className="ms-t">{s.t}</div>
                <div className="ms-b">{s.b}</div>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

function MechProviderCTA() {
  return (
    <section className="section dark-section">
      <div className="container mech-prov-grid">
        <div>
          <span className="section-kicker accent">For mechanics</span>
          <h2 className="section-title light">Are you the mechanic?</h2>
          <p className="section-sub light">
            We're recruiting our first 20 mobile mechanics in Fort Wayne. ASE-certified, your
            own van, ready to operate. Founding-member pricing on platform fees for the first
            six months.
          </p>
          <ul className="mech-req">
            <li><span className="req-ic"><IconCheck size={14}/></span>ASE certification (any specialty)</li>
            <li><span className="req-ic"><IconCheck size={14}/></span>Own service van + portable lift</li>
            <li><span className="req-ic"><IconCheck size={14}/></span>2+ years mobile or shop experience</li>
            <li><span className="req-ic"><IconCheck size={14}/></span>Commercial liability insurance</li>
          </ul>
          <a href="#waitlist" className="btn btn-light btn-lg" style={{ marginTop: "32px" }}>
            Apply as founding mechanic
            <IconArrowRight size={16}/>
          </a>
        </div>
        <div className="founders-card">
          <div className="founders-tag">Founding mechanic perks</div>
          <div className="founders-row">
            <span className="fr-l">Platform fee · first 6 mo</span>
            <span className="fr-v">
              <s>15%</s>
              <strong>0%</strong>
            </span>
          </div>
          <div className="founders-row">
            <span className="fr-l">Onboarding cost</span>
            <span className="fr-v"><strong>Free</strong></span>
          </div>
          <div className="founders-row">
            <span className="fr-l">Equipment financing</span>
            <span className="fr-v"><strong>Available</strong></span>
          </div>
          <div className="founders-row">
            <span className="fr-l">Guaranteed minimum</span>
            <span className="fr-v"><strong>$1,200/wk</strong></span>
          </div>
          <div className="founders-row total">
            <span className="fr-l">Spots remaining</span>
            <span className="fr-v"><strong className="accent">12 / 20</strong></span>
          </div>
        </div>
      </div>
    </section>
  );
}

function MechFAQ() {
  const [open, setOpen] = React.useState(0);
  const items = [
    { q: "When will mechanic services actually launch?", a: "Beta in Q4 2026 with our first cohort of founding mechanics. Public launch in Q1 2027, starting in Fort Wayne and surrounding suburbs." },
    { q: "Will mechanic prices be different from the detailing side?", a: "Each service has a flat parts-plus-labor price. You'll see the full quote before booking — no hourly meter, no surprise diagnostic fees." },
    { q: "What if my car needs work I can't get done in a driveway?", a: "Some jobs (transmission, body work, alignment) need a shop. We'll diagnose and refer you out — and your diagnostic fee is credited toward that shop work." },
    { q: "Do you carry the parts on the van?", a: "Common parts for your make/model are pulled before the appointment. If we need something obscure, we'll come back the next day with no second trip fee." },
    { q: "Is your work guaranteed?", a: "Yes. 12-month or 12,000-mile warranty on parts and labor — whichever comes first. If something we fixed fails, we come back free." },
    { q: "Can I get on the founding-customer list separately?", a: "Yes — that's what the waitlist above is. Founding customers get 20% off their first three appointments and priority booking during beta." },
  ];
  return (
    <section id="faq" className="section">
      <div className="container faq-container">
        <div className="section-head centered">
          <span className="section-kicker">FAQ</span>
          <h2 className="section-title">Questions about the mechanic vertical.</h2>
        </div>
        <div className="faq-list">
          {items.map((it, i) => (
            <details
              key={it.q}
              open={open === i}
              onClick={(e) => { e.preventDefault(); setOpen(open === i ? -1 : i); }}
              className={"faq-item " + (open === i ? "open" : "")}
            >
              <summary>
                <span>{it.q}</span>
                <span className="faq-ic"><IconPlus size={16}/></span>
              </summary>
              <div className="faq-a">{it.a}</div>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

function MechCTA() {
  return (
    <section id="waitlist" className="section final-cta">
      <div className="container">
        <div className="cta-card mech-cta-card">
          <div className="cta-left">
            <span className="section-kicker accent">Get in line</span>
            <h2 className="cta-title">First 500 people in, first 500 served.</h2>
            <p className="cta-sub">Beta access in Q4. 20% off your first three appointments. We'll email you the moment your ZIP code goes live.</p>
            <form className="waitlist-form light" onSubmit={(e) => { e.preventDefault(); e.target.reset(); alert("Welcome to the waitlist."); }}>
              <input type="email" required placeholder="you@example.com" className="waitlist-input light" />
              <button type="submit" className="btn btn-light btn-lg">
                Join the waitlist
                <IconArrowRight size={16}/>
              </button>
            </form>
            <div className="cta-footnotes" style={{ marginTop: 18 }}>
              <span>347 people ahead of you</span>
              <span>·</span>
              <span>Avg wait: 4 weeks</span>
            </div>
          </div>
          <div className="cta-right">
            <div className="rollout">
              <div className="rollout-t">Rollout plan</div>
              <div className="rollout-row done">
                <span className="rr-q">Q2 2026</span>
                <span className="rr-l">Hire founding mechanic team</span>
              </div>
              <div className="rollout-row done">
                <span className="rr-q">Q3 2026</span>
                <span className="rr-l">Service van fleet · gear procurement</span>
              </div>
              <div className="rollout-row active">
                <span className="rr-q">Q4 2026</span>
                <span className="rr-l">Closed beta · waitlist invites</span>
              </div>
              <div className="rollout-row">
                <span className="rr-q">Q1 2027</span>
                <span className="rr-l">Public launch in Fort Wayne</span>
              </div>
              <div className="rollout-row">
                <span className="rr-q">Q3 2027</span>
                <span className="rr-l">Expand to 5 cities</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function MechApp() {
  const [scrolled, setScrolled] = React.useState(false);
  React.useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const [t, setTweak] = useTweaks(/*EDITMODE-BEGIN*/{
    "brand": "blue",
    "density": "comfortable"
  }/*EDITMODE-END*/);

  const M_BRAND = {
    blue:    { brand: "#2563eb", brand2: "#3b82f6", soft: "#dbeafe", softer: "#eff6ff", ink: "#1e3a8a" },
    emerald: { brand: "#059669", brand2: "#10b981", soft: "#d1fae5", softer: "#ecfdf5", ink: "#065f46" },
    orange:  { brand: "#ea580c", brand2: "#f97316", soft: "#fed7aa", softer: "#fff7ed", ink: "#9a3412" },
  };
  React.useEffect(() => {
    const c = M_BRAND[t.brand] || M_BRAND.blue;
    const r = document.documentElement;
    r.style.setProperty("--brand", c.brand);
    r.style.setProperty("--brand-2", c.brand2);
    r.style.setProperty("--brand-soft", c.soft);
    r.style.setProperty("--brand-softer", c.softer);
    r.style.setProperty("--brand-ink", c.ink);
  }, [t.brand]);
  React.useEffect(() => {
    const r = document.documentElement;
    if (t.density === "compact") r.style.setProperty("--sec-pad", "72px");
    else if (t.density === "spacious") r.style.setProperty("--sec-pad", "144px");
    else r.style.setProperty("--sec-pad", "112px");
  }, [t.density]);

  return (
    <>
      <MechNavbar scrolled={scrolled} />
      <main>
        <MechHero />
        <MechServices />
        <MechHow />
        <MechProviderCTA />
        <MechFAQ />
        <MechCTA />
      </main>
      <Footer />

      <TweaksPanel title="Tweaks">
        <TweakSection label="Brand color" />
        <TweakRadio label="Accent" value={t.brand}
          options={[
            { value: "blue", label: "Blue" },
            { value: "emerald", label: "Green" },
            { value: "orange", label: "Orange" },
          ]}
          onChange={(v) => setTweak("brand", v)} />
        <TweakSection label="Density" />
        <TweakRadio label="Spacing" value={t.density}
          options={[
            { value: "compact", label: "Tight" },
            { value: "comfortable", label: "Default" },
            { value: "spacious", label: "Roomy" },
          ]}
          onChange={(v) => setTweak("density", v)} />
      </TweaksPanel>
    </>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<MechApp />);
