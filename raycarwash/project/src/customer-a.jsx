// Customer page sections — part A: nav, hero, booking journey

function CustNavbar({ scrolled }) {
  const links = [
    { href: "#how", label: "How it works" },
    { href: "#services", label: "Services" },
    { href: "#safety", label: "Safety" },
    { href: "#reviews", label: "Reviews" },
    { href: "#faq", label: "FAQ" },
  ];
  const pages = [
    { href: "Detailers Page.html", label: "Detailers" },
    { href: "Mechanic Page.html", label: "Mechanic", badge: "new" },
  ];
  return (
    <header className={"nav " + (scrolled ? "nav-scrolled" : "")}>
      <div className="nav-inner">
        <a href="Landing Page.html" className="brand">
          <span className="brand-mark">R</span>
          <span className="brand-name">RayCarWash</span>
          <span className="brand-sub">/ riders</span>
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
          <a href="#book" className="btn btn-dark btn-sm">Get the app</a>
        </div>
      </div>
    </header>
  );
}

function CustHero() {
  return (
    <section id="top" className="cust-hero">
      <div className="hero-grid" aria-hidden></div>
      <div className="container cust-hero-inner">
        <div className="cust-hero-left">
          <div className="hero-kicker">
            <span className="kicker-dot"></span>
            <span>For riders · Fort Wayne, IN</span>
          </div>
          <h1 className="cust-hero-h1">
            Your driveway.
            <br/>
            <span className="hero-h1-accent">Their pro tools.</span>
          </h1>
          <p className="cust-hero-sub">
            Book a vetted mobile detailer to your home or office in minutes. Track them
            in real time, see before/after photos, pay flat-rate from your couch.
          </p>
          <div className="hero-ctas">
            <a href="#" className="btn btn-dark btn-lg">
              <IconApple size={18}/>
              <span>Download the app</span>
            </a>
            <a href="#book" className="btn btn-outline btn-lg">
              <IconAndroid size={18}/>
              <span>Get on Google Play</span>
            </a>
          </div>

          <div className="cust-hero-quick">
            <div className="qu-row">
              <span className="qu-ic"><IconClock size={18}/></span>
              <div>
                <div className="qu-t">Book in 90 seconds</div>
                <div className="qu-b">From service to payment in 6 taps.</div>
              </div>
            </div>
            <div className="qu-row">
              <span className="qu-ic"><IconShield size={18}/></span>
              <div>
                <div className="qu-t">Insured every wash</div>
                <div className="qu-b">Your vehicle is protected during the service.</div>
              </div>
            </div>
            <div className="qu-row">
              <span className="qu-ic"><IconWallet size={18}/></span>
              <div>
                <div className="qu-t">No surprise charges</div>
                <div className="qu-b">Flat quote up front. Pay only after the job's done.</div>
              </div>
            </div>
          </div>
        </div>

        <div className="cust-hero-right">
          <div className="cust-phone-row">
            <div className="cust-phone-side back">
              <PhoneFrame>
                <div className="ps-header">
                  <div className="ps-status">9:38</div>
                  <div className="ps-status-icons"><span className="ps-dot"></span><span className="ps-dot"></span><span className="ps-dot"></span></div>
                </div>
                <div className="ps-body">
                  <div className="ps-eyebrow">Step 1 of 3</div>
                  <div className="ps-title">When?</div>
                  <div className="cust-cal">
                    <div className="cc-mo">June 2026</div>
                    <div className="cc-grid">
                      {Array.from({length: 30}).map((_, i) => {
                        const d = i + 1;
                        const sel = d === 14;
                        const dis = d < 5 || d === 22;
                        return <div key={i} className={"cc-d " + (sel ? "sel " : "") + (dis ? "dis" : "")}>{d}</div>;
                      })}
                    </div>
                  </div>
                  <div className="cust-slots">
                    <div className="cs">9:00</div>
                    <div className="cs sel">11:30</div>
                    <div className="cs">2:00</div>
                    <div className="cs taken">4:30</div>
                  </div>
                </div>
              </PhoneFrame>
            </div>
            <div className="cust-phone-side front">
              <ClientPhone step={1} />
            </div>
          </div>
          <div className="cust-hero-credit">
            <span>★ 4.9</span>
            <span>·</span>
            <span>1,240+ reviews</span>
            <span>·</span>
            <span>22 min avg ETA</span>
          </div>
        </div>
      </div>
    </section>
  );
}

function BookingJourney() {
  const [step, setStep] = React.useState(0);
  const steps = [
    {
      kicker: "Step 1",
      title: "Pick a service",
      body: "Choose Exterior, Interior, or Full detail. Add your vehicle, choose add-ons. Get an instant flat quote before you commit to anything.",
      tags: ["Flat quote", "Add-ons", "Vehicle profile"],
    },
    {
      kicker: "Step 2",
      title: "Choose a time",
      body: "Pick from available slots in your neighborhood. We only show times that nearby detailers can actually work — no maybe-laters.",
      tags: ["Same day", "Weekends OK", "Recurring"],
    },
    {
      kicker: "Step 3",
      title: "Watch them arrive",
      body: "Once a detailer accepts, you see their profile, their truck, and a live ETA on the map. Get a push 10 min before they arrive.",
      tags: ["Live ETA", "Profile + photos", "Chat"],
    },
    {
      kicker: "Step 4",
      title: "Pay & rate",
      body: "Card is charged only after the job is marked complete. Tip in-app, rate the work, save your detailer for next time.",
      tags: ["Pay on completion", "Save detailer", "Tip"],
    },
  ];

  return (
    <section id="how" className="section section-alt">
      <div className="container">
        <div className="section-head">
          <span className="section-kicker">How a booking works</span>
          <h2 className="section-title">From dirty to spotless in four taps.</h2>
          <p className="section-sub">Pick a step — see what happens on your phone and what happens in your driveway.</p>
        </div>
        <div className="journey-tabs">
          {steps.map((s, i) => (
            <button
              key={i}
              className={"journey-tab " + (i === step ? "on" : "")}
              onClick={() => setStep(i)}
            >
              <span className="jt-num">{String(i + 1).padStart(2, "0")}</span>
              <span className="jt-lbl">{s.title}</span>
            </button>
          ))}
        </div>
        <div className="journey-stage">
          <div className="journey-phone">
            <ClientPhone step={step} />
          </div>
          <div className="journey-text">
            <span className="section-kicker">{steps[step].kicker}</span>
            <h3 className="journey-title">{steps[step].title}</h3>
            <p className="journey-body">{steps[step].body}</p>
            <div className="journey-tags">
              {steps[step].tags.map(t => <span key={t} className="journey-tag">{t}</span>)}
            </div>
            <div className="journey-progress">
              <div className="jp-track">
                {steps.map((_, i) => (
                  <div key={i} className={"jp-seg " + (i <= step ? "on" : "")}></div>
                ))}
              </div>
              <button
                className="btn btn-dark btn-sm"
                onClick={() => setStep((step + 1) % steps.length)}
              >
                {step === steps.length - 1 ? "Restart" : "Next step"}
                <IconArrowRight size={14}/>
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

window.CustNavbar = CustNavbar;
window.CustHero = CustHero;
window.BookingJourney = BookingJourney;
