// Coverage map, For Detailers, Testimonials, FAQ, CTA, Footer

function Coverage() {
  // Fort Wayne, IN — coverage neighborhoods
  const neighborhoods = [
    { name: "Fort Wayne", cx: 50, cy: 50, r: 12, primary: true },
    { name: "Aboite", cx: 30, cy: 58, r: 6 },
    { name: "Huntertown", cx: 48, cy: 28, r: 5 },
    { name: "Leo-Cedarville", cx: 68, cy: 30, r: 5 },
    { name: "New Haven", cx: 70, cy: 56, r: 6 },
    { name: "Waynedale", cx: 40, cy: 70, r: 4 },
  ];
  return (
    <section id="coverage" className="section">
      <div className="container coverage-grid">
        <div className="coverage-text">
          <span className="section-kicker">Coverage</span>
          <h2 className="section-title">Live in Fort Wayne. Expanding fast.</h2>
          <p className="section-sub">We're operating across Fort Wayne and surrounding suburbs today. New neighborhoods every quarter — request yours below.</p>
          <ul className="coverage-list">
            {neighborhoods.map(n => (
              <li key={n.name}><IconMapPin size={14} /> {n.name}{n.primary && <span className="hub-pill">HQ</span>}</li>
            ))}
          </ul>
          <div className="coverage-cta">
            <input className="coverage-input" placeholder="Your ZIP code" defaultValue="" />
            <button className="btn btn-dark">Check coverage</button>
          </div>
        </div>
        <div className="coverage-map">
          <svg viewBox="0 0 100 100" className="map-svg" preserveAspectRatio="xMidYMid meet">
            <defs>
              <radialGradient id="hubGrad" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="var(--brand)" stopOpacity="0.35"/>
                <stop offset="60%" stopColor="var(--brand)" stopOpacity="0.10"/>
                <stop offset="100%" stopColor="var(--brand)" stopOpacity="0"/>
              </radialGradient>
              <pattern id="mapDots" x="0" y="0" width="4" height="4" patternUnits="userSpaceOnUse">
                <circle cx="0.7" cy="0.7" r="0.4" fill="#cbd5e1"/>
              </pattern>
            </defs>
            <rect width="100" height="100" fill="url(#mapDots)" />
            {/* river */}
            <path d="M0 60 Q20 50 35 55 T70 50 T100 55" stroke="#bfdbfe" strokeWidth="2" fill="none" opacity="0.7"/>
            {/* coverage halo */}
            <circle cx="50" cy="50" r="35" fill="url(#hubGrad)"/>
            <circle cx="50" cy="50" r="35" fill="none" stroke="var(--brand)" strokeWidth="0.4" strokeDasharray="1 1.2" opacity="0.55"/>
            {/* nodes */}
            {neighborhoods.map(n => (
              <g key={n.name}>
                <circle cx={n.cx} cy={n.cy} r={n.r/3 + 2} fill="white" opacity="0.95"/>
                <circle cx={n.cx} cy={n.cy} r={n.r/3} fill={n.primary ? "var(--brand)" : "#0f172a"}/>
                {n.primary && (
                  <circle cx={n.cx} cy={n.cy} r="4" fill="none" stroke="var(--brand)" strokeWidth="0.5">
                    <animate attributeName="r" from="3" to="9" dur="2.4s" repeatCount="indefinite"/>
                    <animate attributeName="opacity" from="0.7" to="0" dur="2.4s" repeatCount="indefinite"/>
                  </circle>
                )}
                <text x={n.cx} y={n.cy - 4} textAnchor="middle" fontSize="2.6" fontFamily="ui-monospace, monospace" fill="#0f172a" fontWeight="600">{n.name.toUpperCase()}</text>
              </g>
            ))}
          </svg>
          <div className="map-legend">
            <div><span className="leg-dot brand"></span>HQ</div>
            <div><span className="leg-dot"></span>Service area</div>
            <div><span className="leg-dot ring"></span>20 mi radius</div>
          </div>
        </div>
      </div>
    </section>
  );
}

function ForDetailersSplit() {
  const benefits = [
    { ic: <IconCalendar size={20}/>, t: "Own your schedule", b: "Accept or decline any job. Set your service area and your hours." },
    { ic: <IconWallet size={20}/>, t: "Instant payouts", b: "Funds hit your bank the same day a job is marked complete." },
    { ic: <IconShield size={20}/>, t: "Verified clients", b: "Every customer is identity-checked. No-shows are tracked." },
    { ic: <IconWrench size={20}/>, t: "Built-in tools", b: "Routing, before/after capture, and payout ledger in one app." },
  ];
  return (
    <section id="detailers" className="section dark-section">
      <div className="container detailers-grid">
        <div className="detailers-left">
          <span className="section-kicker accent">For detailers</span>
          <h2 className="section-title light">Run your own detailing business — without the marketing.</h2>
          <p className="section-sub light">Bring your skills. We bring the clients, the schedule, and same-day payouts.</p>

          <div className="earn-card">
            <div className="earn-row">
              <span className="earn-lbl">Median weekly earnings</span>
              <span className="earn-val">$1,840</span>
            </div>
            <div className="earn-row">
              <span className="earn-lbl">Top-quartile weekly</span>
              <span className="earn-val">$2,720</span>
            </div>
            <div className="earn-row">
              <span className="earn-lbl">Average per job</span>
              <span className="earn-val">$112</span>
            </div>
            <div className="earn-bar">
              <div className="earn-bar-fill"></div>
              <span className="earn-bar-tag">Top 10% earn $3,400+/wk</span>
            </div>
          </div>

          <a href="Detailers Page.html" className="btn btn-light btn-lg">
            Apply to detail
            <IconArrowRight size={16} />
          </a>
          <p className="apply-note">Average application takes 4 minutes · Decision in 48 hours</p>
        </div>
        <div className="detailers-right">
          <ul className="benefits-grid">
            {benefits.map(b => (
              <li key={b.t} className="benefit-card">
                <span className="benefit-ic">{b.ic}</span>
                <div className="benefit-t">{b.t}</div>
                <div className="benefit-b">{b.b}</div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

function Testimonials() {
  const items = [
    { quote: "Booked at 9 a.m., the truck was in my driveway by 11. Insanely convenient.", name: "Maria G.", city: "Fort Wayne, IN", rating: 5 },
    { quote: "My detailer sent before/after photos through the app. Felt extremely legit.", name: "Derrick P.", city: "Aboite, IN", rating: 5 },
    { quote: "Full detail on my F-150 — looks better than the day I bought it.", name: "Jonas R.", city: "New Haven, IN", rating: 5 },
    { quote: "Pricing is transparent up front. No surprise upcharges, no haggling.", name: "Anna L.", city: "Fort Wayne, IN", rating: 5 },
  ];
  return (
    <section className="section">
      <div className="container">
        <div className="section-head split">
          <div>
            <span className="section-kicker">What people say</span>
            <h2 className="section-title">Loved by people who'd rather not drive to a car wash.</h2>
          </div>
          <div className="rating-summary">
            <div className="rating-stars">★★★★★</div>
            <div className="rating-meta">4.9 from 1,240+ reviews</div>
          </div>
        </div>
        <div className="testi-grid">
          {items.map(t => (
            <figure key={t.name} className="testi-card">
              <div className="testi-stars">
                {Array.from({ length: t.rating }).map((_, i) => <IconStar key={i} size={14}/>) }
              </div>
              <blockquote>&ldquo;{t.quote}&rdquo;</blockquote>
              <figcaption>
                <div className="testi-name">{t.name}</div>
                <div className="testi-city">{t.city}</div>
              </figcaption>
            </figure>
          ))}
        </div>
      </div>
    </section>
  );
}

function FAQ() {
  const [open, setOpen] = React.useState(0);
  const items = [
    { q: "What area do you serve?", a: "Fort Wayne, IN and surrounding suburbs (Aboite, New Haven, Huntertown, Leo-Cedarville). We're expanding — drop us a line if you want us in your neighborhood." },
    { q: "Do detailers bring their own water and power?", a: "Yes. Every detailer arrives self-contained: water tanks, generators, and pro-grade products. You don't need to lift a finger." },
    { q: "How are detailers vetted?", a: "Identity verification, background check, and portfolio review before they take any job. We re-verify annually." },
    { q: "Is my vehicle insured during service?", a: "Yes. We carry commercial coverage for damage caused by the detailer during a service." },
    { q: "How does payment work?", a: "You get a flat quote up front. We authorize the card when you book and only charge once the job is complete." },
    { q: "What if I'm not satisfied?", a: "Open a dispute in the app within 48 hours. If the work doesn't meet the standard, we'll re-do it or refund you." },
    { q: "Can I tip my detailer?", a: "Absolutely — 100% of every tip goes to the detailer." },
    { q: "Do you offer recurring service?", a: "Yes. Save your vehicle and detailer to schedule weekly, bi-weekly, or monthly cleans with one tap." },
  ];
  return (
    <section id="faq" className="section section-alt">
      <div className="container faq-container">
        <div className="section-head centered">
          <span className="section-kicker">FAQ</span>
          <h2 className="section-title">Questions, answered.</h2>
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

function FinalCTA({ audience }) {
  const isClient = audience === "client";
  return (
    <section className="section final-cta">
      <div className="container">
        <div className="cta-card">
          <div className="cta-left">
            <span className="section-kicker accent">{isClient ? "Get the app" : "Become a detailer"}</span>
            <h2 className="cta-title">
              {isClient
                ? "Ready for a cleaner car?"
                : "Ready to start earning?"}
            </h2>
            <p className="cta-sub">
              {isClient
                ? "Download RayCarWash and book your first detail in under two minutes."
                : "Apply in 4 minutes. Get a decision in 48 hours. Start earning the next."}
            </p>
            <div className="cta-actions">
              {isClient ? (
                <>
                  <a href="#" className="btn btn-light btn-lg"><IconApple size={18}/> App Store</a>
                  <a href="#" className="btn btn-light-outline btn-lg"><IconAndroid size={18}/> Google Play</a>
                </>
              ) : (
                <a href="#" className="btn btn-light btn-lg">Apply now <IconArrowRight size={16}/></a>
              )}
            </div>
          </div>
          <div className="cta-right">
            <div className="cta-mosaic">
              <StripedPlaceholder label="HERO PHOTO" ratio="4/3" className="dark" />
              <StripedPlaceholder label="BEFORE" ratio="1/1" />
              <StripedPlaceholder label="AFTER" ratio="1/1" className="dark" />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Footer() {
  const cols = [
    { h: "Product", links: ["How it works", "Services", "Coverage", "Pricing", "FAQ"] },
    { h: "Company", links: ["About", "Become a detailer", "Press", "Careers", "Contact"] },
    { h: "Legal", links: ["Privacy Policy", "Terms of Service", "Insurance", "Cookies"] },
  ];
  return (
    <footer className="footer">
      <div className="container">
        <div className="footer-grid">
          <div className="footer-brand">
            <a href="#top" className="brand">
              <span className="brand-mark">R</span>
              <span className="brand-name">RayCarWash</span>
            </a>
            <p className="footer-tag">Mobile detailing, on demand. Fort Wayne, IN.</p>
            <div className="footer-stores">
              <a href="#" className="store-btn"><IconApple size={18}/><div><div className="sb-sm">Download on</div><div className="sb-lg">App Store</div></div></a>
              <a href="#" className="store-btn"><IconAndroid size={18}/><div><div className="sb-sm">Get it on</div><div className="sb-lg">Google Play</div></div></a>
            </div>
          </div>
          {cols.map(c => (
            <div key={c.h} className="footer-col">
              <h4>{c.h}</h4>
              <ul>
                {c.links.map(l => <li key={l}><a href="#">{l}</a></li>)}
              </ul>
            </div>
          ))}
        </div>
        <div className="footer-bottom">
          <div>© 2026 RayCarWash. All rights reserved.</div>
          <div className="footer-locale">EN · USD · Fort Wayne, IN</div>
        </div>
      </div>
    </footer>
  );
}

window.Coverage = Coverage;
window.ForDetailersSplit = ForDetailersSplit;
window.Testimonials = Testimonials;
window.FAQ = FAQ;
window.FinalCTA = FinalCTA;
window.Footer = Footer;
