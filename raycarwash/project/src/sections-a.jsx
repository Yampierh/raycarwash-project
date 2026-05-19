// All landing page sections.

function Navbar({ audience, setAudience, scrolled }) {
  const links = [
    { href: "#how", label: "How it works" },
    { href: "#services", label: "Services" },
    { href: "#coverage", label: "Coverage" },
    { href: "#faq", label: "FAQ" },
  ];
  const pages = [
    { href: "Customer Page.html", label: "Riders" },
    { href: "Detailers Page.html", label: "Detailers" },
    { href: "Mechanic Page.html", label: "Mechanic", badge: "new" },
  ];
  return (
    <header className={"nav " + (scrolled ? "nav-scrolled" : "")}>
      <div className="nav-inner">
        <a href="#top" className="brand">
          <span className="brand-mark">R</span>
          <span className="brand-name">RayCarWash</span>
        </a>
        <nav className="nav-links">
          {links.map(l => (
            <a key={l.href} href={l.href}>{l.label}</a>
          ))}
          <span className="nav-sep"></span>
          {pages.map(p => (
            <a key={p.href} href={p.href} className="nav-page">
              {p.label}
              {p.badge && <span className="nav-badge">{p.badge}</span>}
            </a>
          ))}
        </nav>
        <div className="nav-right">
          <div className="aud-toggle nav-aud">
            <button
              className={audience === "client" ? "on" : ""}
              onClick={() => setAudience("client")}
            >Riders</button>
            <button
              className={audience === "detailer" ? "on" : ""}
              onClick={() => setAudience("detailer")}
            >Detailers</button>
          </div>
          <a href="#login" className="link-quiet">Log in</a>
          <a href="#signup" className="btn btn-dark btn-sm">Get the app</a>
        </div>
      </div>
    </header>
  );
}

function Hero({ audience, setAudience }) {
  const [step, setStep] = React.useState(0);
  React.useEffect(() => {
    const id = setInterval(() => setStep(s => (s + 1) % 4), 3200);
    return () => clearInterval(id);
  }, []);

  const isClient = audience === "client";
  const Phone = isClient ? ClientPhone : DetailerPhone;
  const stepLabels = isClient
    ? ["Book", "Detailer en route", "In progress", "Complete"]
    : ["Job offered", "Today's schedule", "Earnings", "Profile"];

  return (
    <section id="top" className="hero">
      <div className="hero-grid" aria-hidden></div>
      <div className="hero-inner">
        <div className="hero-left">
          <div className="hero-kicker">
            <span className="kicker-dot"></span>
            <span>Mobile detailing · Fort Wayne, IN</span>
          </div>
          {isClient ? (
            <h1 className="hero-h1">
              A spotless car,
              <br />
              <span className="hero-h1-accent">at your door.</span>
            </h1>
          ) : (
            <h1 className="hero-h1">
              Detail cars.
              <br />
              <span className="hero-h1-accent">Skip the office.</span>
            </h1>
          )}
          <p className="hero-sub">
            {isClient
              ? "Book a vetted detailer to your driveway in minutes. They bring water, power, and pro-grade products — you keep your day."
              : "Bring the skills. We bring the clients, the schedule, and same-day payouts straight to your bank."}
          </p>

          <div className="hero-ctas">
            {isClient ? (
              <>
                <a href="#book" className="btn btn-dark">
                  <IconApple size={18} />
                  <span>Download the app</span>
                </a>
                <a href="#book" className="btn btn-outline">
                  <IconAndroid size={18} />
                  <span>Get on Google Play</span>
                </a>
              </>
            ) : (
              <>
                <a href="#apply" className="btn btn-accent">
                  Apply to detail
                  <IconArrowRight size={16} />
                </a>
                <a href="#earnings" className="btn btn-outline">
                  See earnings
                </a>
              </>
            )}
          </div>

          <ul className="hero-bullets">
            {isClient ? (
              <>
                <li><span className="bul-ic"><IconShield size={14} /></span>Vetted & insured pros</li>
                <li><span className="bul-ic"><IconWallet size={14} /></span>Flat-rate pricing, no surprises</li>
                <li><span className="bul-ic"><IconMapPin size={14} /></span>Live ETA + before/after photos</li>
              </>
            ) : (
              <>
                <li><span className="bul-ic"><IconCalendar size={14} /></span>Set your own hours & service area</li>
                <li><span className="bul-ic"><IconWallet size={14} /></span>Same-day payouts to your bank</li>
                <li><span className="bul-ic"><IconUserCheck size={14} /></span>Verified clients, tracked no-shows</li>
              </>
            )}
          </ul>

          <div className="hero-stats">
            <div><div className="hs-n">{isClient ? "2,400+" : "85"}</div><div className="hs-l">{isClient ? "details delivered" : "active detailers"}</div></div>
            <div><div className="hs-n">{isClient ? "22 min" : "$42/hr"}</div><div className="hs-l">{isClient ? "avg detailer ETA" : "median earnings"}</div></div>
            <div><div className="hs-n">{isClient ? "4.9★" : "Same day"}</div><div className="hs-l">{isClient ? "average rating" : "payouts"}</div></div>
          </div>
        </div>

        <div className="hero-right">
          <div className="hero-phone-stack">
            <Phone step={step} />
            <div className="hero-step-track">
              {stepLabels.map((l, i) => (
                <button
                  key={i}
                  className={"hero-step-dot " + (i === step ? "on" : "")}
                  onClick={() => setStep(i)}
                  aria-label={l}
                >
                  <span className="hero-step-num">{i + 1}</span>
                  <span className="hero-step-lbl">{l}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function TrustStrip() {
  const items = [
    { ic: <IconUserCheck size={20} />, t: "Verified detailers", b: "Identity + background check before any job." },
    { ic: <IconShield size={20} />, t: "Insured service", b: "Your vehicle is protected during every visit." },
    { ic: <IconStar size={20} />, t: "Satisfaction guarantee", b: "Not happy? We'll re-do it or refund." },
  ];
  return (
    <section className="trust">
      <div className="container">
        <div className="trust-grid">
          {items.map(it => (
            <div key={it.t} className="trust-card">
              <span className="trust-ic">{it.ic}</span>
              <div>
                <div className="trust-title">{it.t}</div>
                <div className="trust-body">{it.b}</div>
              </div>
              <span className="trust-arrow"><IconArrowRight size={14} /></span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function HowItWorks({ audience }) {
  const isClient = audience === "client";
  const clientSteps = [
    { t: "Book in seconds", b: "Pick a service, add your vehicle, choose a time. Get an instant flat quote." },
    { t: "We come to you", b: "A nearby vetted detailer is dispatched. Track them live in the app." },
    { t: "Work happens", b: "They bring water, power, and pro products. You don't lift a finger." },
    { t: "Pay & review", b: "Pay securely after the job. Rate your detailer in two taps." },
  ];
  const detailerSteps = [
    { t: "Apply", b: "Tell us about your experience and the services you offer." },
    { t: "Verify", b: "Identity, background check, and portfolio review — all in-app." },
    { t: "Accept jobs", b: "Set your area. Get matched. Decline anything that doesn't fit." },
    { t: "Get paid same day", b: "Funds hit your bank the day you mark the job complete." },
  ];
  const steps = isClient ? clientSteps : detailerSteps;
  const icons = [IconPhone, IconCar, IconDroplet, IconStar];

  return (
    <section id="how" className="section">
      <div className="container">
        <div className="section-head">
          <span className="section-kicker">How it works</span>
          <h2 className="section-title">
            {isClient ? "Simple. Fast. Done right." : "Onboard in a week. Earn the next."}
          </h2>
          <p className="section-sub">
            {isClient
              ? "From booking to a clean car, everything is built around your time."
              : "We handle the admin so you spend your hours on the work."}
          </p>
        </div>
        <ol className="how-grid">
          {steps.map((s, i) => {
            const Icon = icons[i];
            return (
              <li key={s.t} className="how-card">
                <div className="how-card-top">
                  <span className="how-ic"><Icon size={20} /></span>
                  <span className="how-num">{String(i + 1).padStart(2, "0")}</span>
                </div>
                <h3 className="how-title">{s.t}</h3>
                <p className="how-body">{s.b}</p>
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}

function Services() {
  const items = [
    {
      name: "Exterior wash",
      price: 49,
      duration: "45–60 min",
      features: ["Hand wash & dry", "Wheels and tires", "Spray wax finish"],
    },
    {
      name: "Full detail",
      price: 149,
      duration: "3–4 hours",
      features: ["Everything in exterior + interior", "Clay-bar decontamination", "Tire dressing", "Showroom-grade finish"],
      featured: true,
    },
    {
      name: "Interior detail",
      price: 89,
      duration: "1.5–2 hours",
      features: ["Full vacuum", "Steam-clean upholstery", "Dashboard & door panels", "Glass cleaning"],
    },
  ];
  return (
    <section id="services" className="section section-alt">
      <div className="container">
        <div className="section-head split">
          <div>
            <span className="section-kicker">Services</span>
            <h2 className="section-title">Pick the level of clean.</h2>
            <p className="section-sub">Three core packages, with add-ons for pet hair, headlight restoration, and ceramic spray sealant inside the app.</p>
          </div>
          <a href="#book" className="link-arrow">See all add-ons <IconArrowRight size={14} /></a>
        </div>
        <div className="svc-grid">
          {items.map(s => (
            <div key={s.name} className={"svc-card " + (s.featured ? "featured" : "")}>
              {s.featured && <span className="svc-badge">Most popular</span>}
              <h3 className="svc-name">{s.name}</h3>
              <div className="svc-price-row">
                <span className="svc-from">from</span>
                <span className="svc-price">${s.price}</span>
              </div>
              <div className="svc-duration"><IconClock size={14} /> {s.duration}</div>
              <ul className="svc-features">
                {s.features.map(f => (
                  <li key={f}><IconCheck size={14} /> <span>{f}</span></li>
                ))}
              </ul>
              <a href="#book" className={"btn btn-block " + (s.featured ? "btn-dark" : "btn-outline")}>Book this</a>
            </div>
          ))}
        </div>
        <p className="svc-footnote">Starting prices for sedan-class vehicles. Final quote is generated in-app based on size, condition, and add-ons.</p>
      </div>
    </section>
  );
}

window.Navbar = Navbar;
window.Hero = Hero;
window.TrustStrip = TrustStrip;
window.HowItWorks = HowItWorks;
window.Services = Services;
