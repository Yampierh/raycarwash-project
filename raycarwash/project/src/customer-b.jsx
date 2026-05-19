// Customer page sections — part B: services compare, safety, reviews, FAQ, CTA

function ServicesCompare() {
  const services = [
    {
      name: "Exterior wash",
      price: 49,
      duration: "45–60 min",
      tag: "Quick clean",
      features: {
        "Hand wash & dry": true,
        "Wheels & tires": true,
        "Spray wax finish": true,
        "Vacuum & wipe-down": false,
        "Steam-clean upholstery": false,
        "Dashboard & door panels": false,
        "Clay-bar decontamination": false,
        "Tire dressing": false,
      },
    },
    {
      name: "Interior detail",
      price: 89,
      duration: "1.5–2 hr",
      tag: "Inside-out",
      features: {
        "Hand wash & dry": false,
        "Wheels & tires": false,
        "Spray wax finish": false,
        "Vacuum & wipe-down": true,
        "Steam-clean upholstery": true,
        "Dashboard & door panels": true,
        "Clay-bar decontamination": false,
        "Tire dressing": false,
      },
    },
    {
      name: "Full detail",
      price: 149,
      duration: "3–4 hr",
      tag: "Most popular",
      featured: true,
      features: {
        "Hand wash & dry": true,
        "Wheels & tires": true,
        "Spray wax finish": true,
        "Vacuum & wipe-down": true,
        "Steam-clean upholstery": true,
        "Dashboard & door panels": true,
        "Clay-bar decontamination": true,
        "Tire dressing": true,
      },
    },
  ];
  const addons = [
    { name: "Pet hair removal", price: 25 },
    { name: "Headlight restoration", price: 40 },
    { name: "Ceramic spray sealant", price: 60 },
    { name: "Engine bay cleaning", price: 35 },
    { name: "Odor neutralizer", price: 20 },
    { name: "Leather conditioning", price: 35 },
  ];
  const featureRows = Object.keys(services[0].features);
  return (
    <section id="services" className="section">
      <div className="container">
        <div className="section-head split">
          <div>
            <span className="section-kicker">Services</span>
            <h2 className="section-title">Pick the level of clean.</h2>
            <p className="section-sub">Three core packages, plus add-ons for the specifics. Final quote depends on vehicle size & condition.</p>
          </div>
        </div>

        <div className="compare-wrap">
          <table className="compare">
            <thead>
              <tr>
                <th></th>
                {services.map(s => (
                  <th key={s.name} className={s.featured ? "feat" : ""}>
                    <div className="ct-tag">{s.tag}</div>
                    <div className="ct-name">{s.name}</div>
                    <div className="ct-price"><span className="ct-from">from</span> ${s.price}</div>
                    <div className="ct-dur"><IconClock size={12}/> {s.duration}</div>
                    <a href="#book" className={"btn btn-sm " + (s.featured ? "btn-dark" : "btn-outline")}>Book</a>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {featureRows.map(f => (
                <tr key={f}>
                  <td>{f}</td>
                  {services.map(s => (
                    <td key={s.name} className={s.featured ? "feat" : ""}>
                      {s.features[f] ? <span className="check"><IconCheck size={14}/></span> : <span className="dash">—</span>}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="addons">
          <div className="addons-head">
            <span className="section-kicker">Add-ons</span>
            <h3 className="addons-title">Tack any of these onto your service.</h3>
          </div>
          <div className="addons-grid">
            {addons.map(a => (
              <div key={a.name} className="addon">
                <span className="addon-name">{a.name}</span>
                <span className="addon-price">+${a.price}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function TrustSafety() {
  const pillars = [
    {
      step: "01",
      title: "Identity verified",
      body: "Every detailer is verified through Stripe Identity. We see government ID, biometric selfie match, and proof of address before approval.",
      meta: "Avg approval: 36 hours",
    },
    {
      step: "02",
      title: "Background checked",
      body: "Criminal background check via our partner Checkr. Annual re-screening for all active providers.",
      meta: "100% of active detailers",
    },
    {
      step: "03",
      title: "Insured every job",
      body: "Commercial general liability ($1M per occurrence) covers damage caused by a detailer during your service. No-fault re-service for missed spots.",
      meta: "$1M / occurrence",
    },
    {
      step: "04",
      title: "Documented work",
      body: "Detailers capture before/after photos at every job. Auto-attached to your receipt and audit trail.",
      meta: "6+ photos / job",
    },
  ];
  return (
    <section id="safety" className="section dark-section">
      <div className="container">
        <div className="section-head">
          <span className="section-kicker accent">Trust & safety</span>
          <h2 className="section-title light">Four checks before they touch your car.</h2>
          <p className="section-sub light">We won't dispatch a detailer who can't clear all four. Anyone shows up who shouldn't be there, you tell us and they're off the platform.</p>
        </div>
        <div className="pillars">
          {pillars.map(p => (
            <div key={p.title} className="pillar">
              <div className="pillar-step">{p.step}</div>
              <h3 className="pillar-title">{p.title}</h3>
              <p className="pillar-body">{p.body}</p>
              <div className="pillar-meta">{p.meta}</div>
            </div>
          ))}
        </div>
        <div className="dispute-card">
          <div className="dispute-left">
            <span className="section-kicker accent">Something went wrong?</span>
            <h3 className="dispute-h3">48-hour dispute window. We re-do or refund.</h3>
            <p className="dispute-body">Open a dispute in the app within 48 hours of the job. Most cases settle with a free re-service. We never side blindly with detailers — the photo audit trail keeps everyone honest.</p>
            <a href="#" className="link-arrow light">See our policy <IconArrowRight size={14}/></a>
          </div>
          <div className="dispute-right">
            <div className="dispute-stat">
              <div className="ds-n">94%</div>
              <div className="ds-l">of disputes resolved within 24 hrs</div>
            </div>
            <div className="dispute-stat">
              <div className="ds-n">$0</div>
              <div className="ds-l">cost to you to re-service</div>
            </div>
            <div className="dispute-stat">
              <div className="ds-n">3.2 yrs</div>
              <div className="ds-l">avg detailer tenure on platform</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function ReviewsWall() {
  // Mixed sizes, masonry-ish
  const reviews = [
    { quote: "Booked at 9 a.m., the truck was in my driveway by 11. Insanely convenient.", name: "Maria G.", city: "Fort Wayne, IN", rating: 5, size: "lg" },
    { quote: "My detailer sent before/after photos through the app. Felt extremely legit.", name: "Derrick P.", city: "Aboite, IN", rating: 5, size: "md" },
    { quote: "Full detail on my F-150 — looks better than the day I bought it.", name: "Jonas R.", city: "New Haven, IN", rating: 5, size: "md" },
    { quote: "Pricing is transparent up front. No surprise upcharges.", name: "Anna L.", city: "Fort Wayne, IN", rating: 5, size: "sm" },
    { quote: "Set up a monthly recurring detail in 30 seconds. My car is permanently clean now.", name: "Sarah K.", city: "Huntertown, IN", rating: 5, size: "md" },
    { quote: "Detailer arrived in a branded truck with everything he needed. Zero hassle from me.", name: "Mike D.", city: "Leo-Cedarville, IN", rating: 5, size: "sm" },
    { quote: "I had a stain from a coffee spill that I thought would never come out. It did. The steam cleaning is real.", name: "Priya N.", city: "Fort Wayne, IN", rating: 5, size: "lg" },
    { quote: "Cancelled an appointment last minute. Full refund, no questions.", name: "Tomás A.", city: "Aboite, IN", rating: 5, size: "sm" },
  ];
  return (
    <section id="reviews" className="section">
      <div className="container">
        <div className="section-head split">
          <div>
            <span className="section-kicker">Reviews</span>
            <h2 className="section-title">1,240+ five-star reviews and counting.</h2>
          </div>
          <div className="rating-summary">
            <div className="rating-stars">★★★★★</div>
            <div className="rating-meta">4.9 average · 96% would book again</div>
          </div>
        </div>
        <div className="reviews-wall">
          {reviews.map((r, i) => (
            <figure key={i} className={"rw-card rw-" + r.size}>
              <div className="rw-stars">
                {Array.from({length: r.rating}).map((_, j) => <IconStar key={j} size={14}/>)}
              </div>
              <blockquote>&ldquo;{r.quote}&rdquo;</blockquote>
              <figcaption>
                <div className="rw-avatar"></div>
                <div>
                  <div className="rw-name">{r.name}</div>
                  <div className="rw-city">{r.city}</div>
                </div>
              </figcaption>
            </figure>
          ))}
        </div>
      </div>
    </section>
  );
}

function CustFAQ() {
  const [open, setOpen] = React.useState(0);
  const items = [
    { q: "How much does a typical wash cost?", a: "Exterior washes start at $49, interior details at $89, full details at $149. Final price depends on vehicle size (sedan vs SUV vs truck), condition, and any add-ons. You always see a flat quote before you book." },
    { q: "Do I need to be home during the service?", a: "Nope. Plenty of customers leave the keys (or have us work on the car while it's parked at their office). We'll send you photos and a notification when it's done." },
    { q: "How long does a detail take?", a: "Exterior wash: 45–60 minutes. Interior detail: 1.5–2 hours. Full detail: 3–4 hours. Add-ons extend by 20–40 minutes each. We give you a finish-time estimate when you book." },
    { q: "Do detailers bring water and power?", a: "Yes. Every detailer arrives self-contained with water tanks, generators, and pro-grade products. You don't need to provide a hose, outlet, or anything." },
    { q: "What happens if it rains?", a: "We'll reach out 2–3 hours before the appointment to either reschedule (free) or proceed if you're OK with that. Indoor parking? Service goes ahead as planned." },
    { q: "Can I tip in the app?", a: "Yes. After the job, you can add a tip in any amount. 100% goes to the detailer." },
    { q: "How do recurring bookings work?", a: "After your first detail, you can save the detailer and book recurring weekly, bi-weekly, or monthly cleans with one tap. You can pause or cancel anytime." },
    { q: "Is my data and payment info safe?", a: "Yes. Payments are processed by Stripe (PCI-DSS Level 1). We never store your card number — only a token. Your address is shared with the detailer only after they accept the job." },
  ];
  return (
    <section id="faq" className="section section-alt">
      <div className="container faq-container">
        <div className="section-head centered">
          <span className="section-kicker">FAQ</span>
          <h2 className="section-title">Rider questions.</h2>
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

function CustCTA() {
  return (
    <section id="book" className="section final-cta">
      <div className="container">
        <div className="cta-card">
          <div className="cta-left">
            <span className="section-kicker accent">Get the app</span>
            <h2 className="cta-title">Ready for a cleaner car?</h2>
            <p className="cta-sub">Download RayCarWash and book your first detail in under two minutes. Free to download, only pay for the service you book.</p>
            <div className="cta-actions">
              <a href="#" className="btn btn-light btn-lg"><IconApple size={18}/> App Store</a>
              <a href="#" className="btn btn-light-outline btn-lg"><IconAndroid size={18}/> Google Play</a>
            </div>
            <div className="cta-footnotes">
              <span>✓ Free to download</span>
              <span>✓ No subscription</span>
              <span>✓ Cancel any booking free 24h+ out</span>
            </div>
          </div>
          <div className="cta-right">
            <div className="qr-card">
              <div className="qr">
                <svg viewBox="0 0 100 100" width="100" height="100">
                  {/* Simple QR placeholder grid */}
                  <rect width="100" height="100" fill="white"/>
                  {Array.from({length: 12}).map((_, r) => (
                    Array.from({length: 12}).map((_, c) => {
                      const fill = (r + c * 3 + r * c) % 3 === 0;
                      return fill ? <rect key={r+'-'+c} x={c*8+2} y={r*8+2} width="6" height="6" fill="#0f0f10"/> : null;
                    })
                  ))}
                  <rect x="2" y="2" width="22" height="22" fill="none" stroke="#0f0f10" strokeWidth="3"/>
                  <rect x="76" y="2" width="22" height="22" fill="none" stroke="#0f0f10" strokeWidth="3"/>
                  <rect x="2" y="76" width="22" height="22" fill="none" stroke="#0f0f10" strokeWidth="3"/>
                  <rect x="9" y="9" width="8" height="8" fill="#0f0f10"/>
                  <rect x="83" y="9" width="8" height="8" fill="#0f0f10"/>
                  <rect x="9" y="83" width="8" height="8" fill="#0f0f10"/>
                </svg>
              </div>
              <div className="qr-text">
                <div className="qr-t">Scan to download</div>
                <div className="qr-b">Open your camera, point it at the code, tap the link.</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

window.ServicesCompare = ServicesCompare;
window.TrustSafety = TrustSafety;
window.ReviewsWall = ReviewsWall;
window.CustFAQ = CustFAQ;
window.CustCTA = CustCTA;
