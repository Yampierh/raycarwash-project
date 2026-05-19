// Detailers page — part B: Tools, Requirements, How to start, Testimonials, FAQ, CTA

function Tools() {
  // Three phone mocks side by side, each showing a different tool
  const tools = [
    {
      title: "Smart job dispatcher",
      body: "Get matched only to jobs in your service area and price range. Auto-decline filters keep junk off your screen.",
      phone: "dispatcher",
    },
    {
      title: "Route + day planner",
      body: "See every job for the day on one map. We optimize the order so you spend less time driving and more time billing.",
      phone: "planner",
    },
    {
      title: "Before/after capture",
      body: "Snap photos as you work. We attach them to the receipt and the dispute audit trail — no he-said-she-said.",
      phone: "capture",
    },
  ];
  return (
    <section id="tools" className="section dark-section">
      <div className="container">
        <div className="section-head">
          <span className="section-kicker accent">Tools you get</span>
          <h2 className="section-title light">Built by people who've held a clay bar.</h2>
          <p className="section-sub light">The detailer app isn't a re-skin of the rider app. It's a separate workflow built for the work.</p>
        </div>
        <div className="tools-grid">
          {tools.map(t => (
            <div key={t.title} className="tool-card">
              <div className="tool-phone-wrap">
                <ToolPhone variant={t.phone} />
              </div>
              <div className="tool-body">
                <h3 className="tool-title">{t.title}</h3>
                <p className="tool-text">{t.body}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function ToolPhone({ variant }) {
  return (
    <div className="tool-phone">
      <div className="tool-phone-notch"></div>
      <div className="tool-phone-screen">
        {variant === "dispatcher" && (
          <>
            <div className="tp-head">
              <span className="tp-eb">3 jobs nearby</span>
              <span className="tp-pill">Live</span>
            </div>
            <div className="tp-job">
              <div className="tp-job-top">
                <span className="tp-job-t">Full detail · Civic</span>
                <span className="tp-job-pay">$149</span>
              </div>
              <div className="tp-job-meta">2.1 mi · Today 2:30 PM</div>
              <div className="tp-job-fit"><span className="fit-dot"></span>Great fit</div>
            </div>
            <div className="tp-job">
              <div className="tp-job-top">
                <span className="tp-job-t">Interior · Wrangler</span>
                <span className="tp-job-pay">$129</span>
              </div>
              <div className="tp-job-meta">3.4 mi · Tomorrow 10:00 AM</div>
              <div className="tp-job-fit"><span className="fit-dot"></span>Good fit</div>
            </div>
            <div className="tp-job dim">
              <div className="tp-job-top">
                <span className="tp-job-t">Exterior · Outside area</span>
                <span className="tp-job-pay">$49</span>
              </div>
              <div className="tp-job-meta">12 mi · Auto-filtered</div>
            </div>
          </>
        )}
        {variant === "planner" && (
          <>
            <div className="tp-head">
              <span className="tp-eb">Today · 4 stops</span>
              <span className="tp-pill green">Optimized</span>
            </div>
            <div className="tp-map">
              <svg viewBox="0 0 200 140" preserveAspectRatio="none">
                <rect width="200" height="140" fill="#1a1a1f"/>
                <path d="M20 110 Q60 80 90 100 T160 60 L180 30" stroke="#3b82f6" strokeWidth="2" fill="none" strokeDasharray="3 3"/>
                <g>
                  <circle cx="20" cy="110" r="5" fill="#3b82f6"/>
                  <text x="20" y="113" textAnchor="middle" fontSize="6" fill="white" fontWeight="700">1</text>
                </g>
                <g>
                  <circle cx="90" cy="100" r="5" fill="#3b82f6"/>
                  <text x="90" y="103" textAnchor="middle" fontSize="6" fill="white" fontWeight="700">2</text>
                </g>
                <g>
                  <circle cx="140" cy="80" r="5" fill="#3b82f6"/>
                  <text x="140" y="83" textAnchor="middle" fontSize="6" fill="white" fontWeight="700">3</text>
                </g>
                <g>
                  <circle cx="180" cy="30" r="5" fill="#3b82f6"/>
                  <text x="180" y="33" textAnchor="middle" fontSize="6" fill="white" fontWeight="700">4</text>
                </g>
              </svg>
            </div>
            <div className="tp-route">
              <div className="tp-route-row"><span>1</span><span>9:00 · M3 Exterior</span></div>
              <div className="tp-route-row"><span>2</span><span>11:30 · Civic Full</span></div>
              <div className="tp-route-row"><span>3</span><span>2:00 · F-150 Int.</span></div>
              <div className="tp-route-row"><span>4</span><span>4:30 · Sienna Full</span></div>
            </div>
            <div className="tp-foot">Saved 22 min vs unsorted</div>
          </>
        )}
        {variant === "capture" && (
          <>
            <div className="tp-head">
              <span className="tp-eb">Capture · step 3 / 6</span>
              <span className="tp-pill">●&nbsp;REC</span>
            </div>
            <div className="tp-cap-grid">
              <div className="tp-cap">
                <div className="tp-cap-img dark"></div>
                <span className="tp-cap-lbl">Before</span>
                <span className="tp-cap-check">✓</span>
              </div>
              <div className="tp-cap">
                <div className="tp-cap-img"></div>
                <span className="tp-cap-lbl">After</span>
                <span className="tp-cap-check">✓</span>
              </div>
              <div className="tp-cap">
                <div className="tp-cap-img dark"></div>
                <span className="tp-cap-lbl">Wheels</span>
                <span className="tp-cap-check">✓</span>
              </div>
              <div className="tp-cap active">
                <div className="tp-cap-img stripe"></div>
                <span className="tp-cap-lbl">Interior</span>
              </div>
              <div className="tp-cap pending">
                <span className="tp-cap-plus">+</span>
                <span className="tp-cap-lbl">Engine</span>
              </div>
              <div className="tp-cap pending">
                <span className="tp-cap-plus">+</span>
                <span className="tp-cap-lbl">Final</span>
              </div>
            </div>
            <div className="tp-foot">Auto-attached to receipt</div>
          </>
        )}
      </div>
    </div>
  );
}

function Requirements() {
  const reqs = [
    "Own vehicle with cargo space for equipment",
    "Pro-grade detailing tools and products",
    "Smartphone with data plan (iOS 16+ or Android 10+)",
    "Valid driver's license & auto insurance",
    "Pass background check + identity verification",
    "Stripe-eligible bank account for payouts",
  ];
  const steps = [
    { t: "Apply", b: "Tell us about your experience, your gear, and the services you offer." },
    { t: "Verify", b: "Identity verification via Stripe + background check. Usually under 48 hours." },
    { t: "Setup", b: "Set your service area, hours, and per-service prices. We provide starting templates." },
    { t: "Earn", b: "Jobs route to you automatically. Get paid the day you complete each one." },
  ];
  return (
    <section id="requirements" className="section">
      <div className="container">
        <div className="req-grid">
          <div className="req-left">
            <span className="section-kicker">Requirements</span>
            <h2 className="section-title">What you'll need to get started.</h2>
            <p className="section-sub">We maintain high standards so every client experience is consistent. Here's the minimum bar.</p>
            <ul className="req-list">
              {reqs.map(r => (
                <li key={r}>
                  <span className="req-ic"><IconCheck size={14}/></span>
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="req-right">
            <span className="section-kicker">How to start</span>
            <h3 className="req-h3">Four steps to your first paycheck.</h3>
            <ol className="req-steps">
              {steps.map((s, i) => (
                <li key={s.t}>
                  <span className="req-step-num">{String(i + 1).padStart(2, "0")}</span>
                  <div>
                    <div className="req-step-t">{s.t}</div>
                    <div className="req-step-b">{s.b}</div>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </div>
    </section>
  );
}

function DetTestimonials() {
  const items = [
    {
      quote: "I left my dealership job in March. By July I was making more, and I'm home for dinner every night.",
      name: "Marcus T.",
      meta: "Detailer · 312 jobs · ★ 4.9",
    },
    {
      quote: "The app routes me to jobs I would have spent days finding on Facebook. I just show up and work.",
      name: "Trey W.",
      meta: "Detailer · 198 jobs · ★ 4.8",
    },
    {
      quote: "Same-day payouts changed everything. I don't have to wait two weeks for an invoice to clear.",
      name: "Jamal R.",
      meta: "Detailer · 421 jobs · ★ 5.0",
    },
  ];
  return (
    <section className="section section-alt">
      <div className="container">
        <div className="section-head">
          <span className="section-kicker">From detailers</span>
          <h2 className="section-title">People who'd never go back.</h2>
        </div>
        <div className="dt-grid">
          {items.map(t => (
            <figure key={t.name} className="dt-card">
              <div className="dt-quote">&ldquo;{t.quote}&rdquo;</div>
              <figcaption>
                <div className="dt-avatar"></div>
                <div>
                  <div className="dt-name">{t.name}</div>
                  <div className="dt-meta">{t.meta}</div>
                </div>
              </figcaption>
            </figure>
          ))}
        </div>
      </div>
    </section>
  );
}

function DetFAQ() {
  const [open, setOpen] = React.useState(0);
  const items = [
    { q: "How much does it really cost to join?", a: "Nothing up front. We deduct a 15% platform fee from each completed job — that covers payment processing, insurance coverage during service, dispatch, support, and marketing. You keep the rest, including 100% of tips." },
    { q: "Do I need to be a full-time detailer?", a: "No. About 30% of our detailers work part-time or weekends only. Set your hours and we'll route jobs to fit." },
    { q: "Can I bring my existing clients?", a: "Yes. We have a referral code system — anyone you refer who books through the app gets $20 off and you get a $40 bonus on top of your usual cut." },
    { q: "What about insurance?", a: "We carry commercial general liability that covers damage caused by you during a service. Your personal auto policy still covers transit. We strongly recommend you also carry your own business liability." },
    { q: "How fast do I actually get paid?", a: "Funds initiate transfer the same day a job is marked complete. Most banks post within 1–2 business days; instant payouts (eligible debit cards) hit in minutes." },
    { q: "Can I decline jobs?", a: "Always. Decline rate doesn't affect your standing as long as you don't ghost. The app shows you the full job details before you accept." },
    { q: "What happens if a customer disputes the work?", a: "We use the before/after photos you captured, the timeline of the job, and the customer's complaint. Most disputes are resolved with a re-service rather than a refund." },
  ];
  return (
    <section id="faq" className="section">
      <div className="container faq-container">
        <div className="section-head centered">
          <span className="section-kicker">FAQ</span>
          <h2 className="section-title">Detailer questions, answered.</h2>
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

function DetCTA() {
  return (
    <section id="apply" className="section final-cta">
      <div className="container">
        <div className="cta-card">
          <div className="cta-left">
            <span className="section-kicker accent">Become a detailer</span>
            <h2 className="cta-title">Ready to apply?</h2>
            <p className="cta-sub">It takes about 4 minutes. We'll get back to you within 48 hours with a decision.</p>
            <div className="cta-actions">
              <a href="#" className="btn btn-light btn-lg">Start application <IconArrowRight size={16}/></a>
              <a href="Landing Page.html" className="btn btn-light-outline btn-lg">Back to home</a>
            </div>
            <div className="cta-footnotes">
              <span>✓ No upfront cost</span>
              <span>✓ Cancel anytime</span>
              <span>✓ 15% platform fee · keep 100% of tips</span>
            </div>
          </div>
          <div className="cta-right">
            <div className="apply-preview">
              <div className="ap-step done">1 · Personal info</div>
              <div className="ap-step done">2 · Identity verification</div>
              <div className="ap-step active">3 · Services & pricing</div>
              <div className="ap-step">4 · Service area</div>
              <div className="ap-progress">
                <div className="ap-progress-fill" style={{ width: "62%" }}></div>
              </div>
              <div className="ap-progress-meta">62% complete · ~2 min remaining</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

window.Tools = Tools;
window.Requirements = Requirements;
window.DetTestimonials = DetTestimonials;
window.DetFAQ = DetFAQ;
window.DetCTA = DetCTA;
