// Detailers page sections

function DetNavbar({ scrolled }) {
  const links = [
    { href: "#earnings", label: "Earnings" },
    { href: "#week", label: "A week" },
    { href: "#tools", label: "Tools" },
    { href: "#requirements", label: "Requirements" },
    { href: "#faq", label: "FAQ" },
  ];
  const pages = [
    { href: "Customer Page.html", label: "Riders" },
    { href: "Mechanic Page.html", label: "Mechanic", badge: "new" },
  ];
  return (
    <header className={"nav " + (scrolled ? "nav-scrolled" : "")}>
      <div className="nav-inner">
        <a href="Landing Page.html" className="brand">
          <span className="brand-mark">R</span>
          <span className="brand-name">RayCarWash</span>
          <span className="brand-sub">/ detailers</span>
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
          <a href="#apply" className="btn btn-accent btn-sm">Apply to detail</a>
        </div>
      </div>
    </header>
  );
}

function DetHero() {
  return (
    <section id="top" className="det-hero">
      <div className="hero-grid" aria-hidden></div>
      <div className="container det-hero-inner">
        <div className="det-hero-text">
          <div className="hero-kicker">
            <span className="kicker-dot"></span>
            <span>Detail with RayCarWash · Fort Wayne, IN</span>
          </div>
          <h1 className="det-hero-h1">
            Your hands.
            <br/>
            <span className="hero-h1-accent">Our pipeline.</span>
          </h1>
          <p className="det-hero-sub">
            Stop spending Sundays running ads. Plug into a steady flow of vetted clients,
            set your own schedule, and get paid the day you finish the job.
          </p>
          <div className="hero-ctas">
            <a href="#apply" className="btn btn-accent btn-lg">
              Start application
              <IconArrowRight size={16} />
            </a>
            <a href="#earnings" className="btn btn-outline btn-lg">See earnings</a>
          </div>
          <div className="det-trust-strip">
            <div><strong>4 min</strong><span>average application</span></div>
            <div><strong>48 hrs</strong><span>decision turnaround</span></div>
            <div><strong>Same day</strong><span>payouts to bank</span></div>
          </div>
        </div>
        <div className="det-hero-card">
          <div className="payout-sticker">
            <div className="ps-eyebrow muted">Last 7 days · Marcus T.</div>
            <div className="payout-amt"><span className="dollar">$</span>2,148<span className="cents">.50</span></div>
            <div className="payout-meta">
              <span className="payout-up">▲ +18%</span>
              <span>vs prior week</span>
            </div>
            <div className="payout-row">
              <span>Jobs completed</span>
              <span className="b">14</span>
            </div>
            <div className="payout-row">
              <span>Avg per job</span>
              <span className="b">$153.46</span>
            </div>
            <div className="payout-row">
              <span>Tips earned</span>
              <span className="b">$248</span>
            </div>
            <div className="payout-row total">
              <span>Cash out now</span>
              <span className="b accent">$412.00 →</span>
            </div>
            <div className="payout-mini-bars">
              {[40, 65, 30, 80, 55, 90, 70].map((h, i) => (
                <div key={i} className="pmb" style={{ height: h + "%" }}></div>
              ))}
            </div>
            <div className="payout-mini-labels">
              <span>M</span><span>T</span><span>W</span><span>T</span><span>F</span><span>S</span><span>S</span>
            </div>
          </div>
          <div className="det-hero-orbit">
            <div className="orbit-chip">★ 4.9 rating</div>
            <div className="orbit-chip">312 jobs</div>
            <div className="orbit-chip">98% on-time</div>
          </div>
        </div>
      </div>
    </section>
  );
}

function EarningsCalc() {
  const [jobs, setJobs] = React.useState(12);
  const [avg, setAvg] = React.useState(140);
  const [days, setDays] = React.useState(5);

  const weekly = jobs * avg;
  const monthly = Math.round(weekly * 4.33);
  const yearly = weekly * 52;
  const platformFee = 0.15;
  const net = weekly * (1 - platformFee);

  const fmt = (n) => "$" + Math.round(n).toLocaleString();

  return (
    <section id="earnings" className="section section-alt">
      <div className="container">
        <div className="section-head split">
          <div>
            <span className="section-kicker">Earnings calculator</span>
            <h2 className="section-title">See what your week looks like.</h2>
            <p className="section-sub">Drag the sliders. We do the math — including our 15% platform fee, so the take-home is already net.</p>
          </div>
        </div>
        <div className="calc-grid">
          <div className="calc-controls">
            <div className="calc-control">
              <div className="calc-label">
                <span>Jobs per week</span>
                <span className="calc-val">{jobs}</span>
              </div>
              <input
                type="range" min="3" max="25" step="1"
                value={jobs}
                onChange={(e) => setJobs(+e.target.value)}
                className="range"
                style={{ "--p": ((jobs - 3) / (25 - 3) * 100) + "%" }}
              />
              <div className="range-track">
                <span>3</span><span>25</span>
              </div>
            </div>
            <div className="calc-control">
              <div className="calc-label">
                <span>Average ticket</span>
                <span className="calc-val">${avg}</span>
              </div>
              <input
                type="range" min="49" max="299" step="1"
                value={avg}
                onChange={(e) => setAvg(+e.target.value)}
                className="range"
                style={{ "--p": ((avg - 49) / (299 - 49) * 100) + "%" }}
              />
              <div className="range-track">
                <span>$49</span><span>$299</span>
              </div>
            </div>
            <div className="calc-control">
              <div className="calc-label">
                <span>Days worked</span>
                <span className="calc-val">{days} / week</span>
              </div>
              <input
                type="range" min="1" max="7" step="1"
                value={days}
                onChange={(e) => setDays(+e.target.value)}
                className="range"
                style={{ "--p": ((days - 1) / (7 - 1) * 100) + "%" }}
              />
              <div className="range-track">
                <span>1</span><span>7</span>
              </div>
            </div>
            <div className="calc-fineprint">
              <strong>Platform fee:</strong> 15% covers payment processing, insurance coverage, dispatch, customer support, and marketing.
            </div>
          </div>

          <div className="calc-output">
            <div className="calc-big">
              <div className="calc-big-lbl">Net per week</div>
              <div className="calc-big-val">{fmt(net)}</div>
              <div className="calc-big-sub">Take-home · after 15% platform fee</div>
            </div>
            <div className="calc-meta">
              <div>
                <div className="calc-meta-l">Gross weekly</div>
                <div className="calc-meta-v">{fmt(weekly)}</div>
              </div>
              <div>
                <div className="calc-meta-l">Per day</div>
                <div className="calc-meta-v">{fmt(weekly / days)}</div>
              </div>
              <div>
                <div className="calc-meta-l">Monthly</div>
                <div className="calc-meta-v">{fmt(monthly)}</div>
              </div>
              <div>
                <div className="calc-meta-l">Yearly</div>
                <div className="calc-meta-v">{fmt(yearly)}</div>
              </div>
            </div>
            <div className="calc-bench">
              <div className="calc-bench-row">
                <span>Median Fort Wayne detailer</span>
                <span>$1,840 / wk</span>
              </div>
              <div className="calc-bench-row">
                <span>Top quartile</span>
                <span>$2,720 / wk</span>
              </div>
              <div className="calc-bench-row hi">
                <span>Top 10%</span>
                <span>$3,400+ / wk</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function WeekInLife() {
  const days = [
    {
      d: "Mon", date: "Jun 3",
      jobs: [
        { t: "9:00", svc: "Exterior wash · M3", pay: 49 },
        { t: "11:30", svc: "Full detail · Civic", pay: 149 },
        { t: "3:00", svc: "Interior · F-150", pay: 89 },
      ],
    },
    {
      d: "Tue", date: "Jun 4",
      jobs: [
        { t: "10:00", svc: "Full detail · CX-5", pay: 149 },
        { t: "2:00", svc: "Exterior · Camry", pay: 49 },
      ],
    },
    {
      d: "Wed", date: "Jun 5",
      jobs: [
        { t: "9:00", svc: "Interior · Pilot", pay: 89 },
        { t: "1:00", svc: "Full detail · Wrangler", pay: 189 },
        { t: "4:30", svc: "Ext + interior · Sienna", pay: 169 },
      ],
    },
    {
      d: "Thu", date: "Jun 6",
      off: true,
    },
    {
      d: "Fri", date: "Jun 7",
      jobs: [
        { t: "8:30", svc: "Full detail · Model Y", pay: 159 },
        { t: "12:00", svc: "Full detail · Tacoma", pay: 189 },
        { t: "4:00", svc: "Interior · Outback", pay: 89 },
      ],
    },
    {
      d: "Sat", date: "Jun 8",
      jobs: [
        { t: "9:00", svc: "Full detail · CR-V", pay: 149 },
        { t: "1:00", svc: "Full detail · Q5", pay: 179 },
      ],
    },
    {
      d: "Sun", date: "Jun 9",
      off: true,
    },
  ];

  const total = days.reduce((s, d) => s + (d.jobs?.reduce((a, j) => a + j.pay, 0) || 0), 0);
  const jobsCount = days.reduce((s, d) => s + (d.jobs?.length || 0), 0);

  return (
    <section id="week" className="section">
      <div className="container">
        <div className="section-head split">
          <div>
            <span className="section-kicker">A real week</span>
            <h2 className="section-title">Marcus's week in June.</h2>
            <p className="section-sub">Sample schedule from one of our top 20% detailers. Two days off. Thirteen jobs. No cold calls.</p>
          </div>
          <div className="week-total">
            <div className="week-total-lbl">Week total</div>
            <div className="week-total-amt">${total.toLocaleString()}</div>
            <div className="week-total-sub">{jobsCount} jobs · 5 days worked</div>
          </div>
        </div>
        <div className="week-grid">
          {days.map(d => (
            <div key={d.d} className={"week-day " + (d.off ? "off" : "")}>
              <div className="week-day-head">
                <span className="week-d">{d.d}</span>
                <span className="week-date">{d.date}</span>
              </div>
              {d.off ? (
                <div className="week-off">
                  <span className="off-tag">Off</span>
                  <span className="off-meta">Family · errands</span>
                </div>
              ) : (
                <>
                  <div className="week-jobs">
                    {d.jobs.map((j, i) => (
                      <div key={i} className="week-job">
                        <span className="wj-t">{j.t}</span>
                        <span className="wj-svc">{j.svc}</span>
                        <span className="wj-pay">${j.pay}</span>
                      </div>
                    ))}
                  </div>
                  <div className="week-day-foot">
                    <span>${d.jobs.reduce((a, j) => a + j.pay, 0)}</span>
                    <span className="wf-sub">{d.jobs.length} job{d.jobs.length > 1 ? "s" : ""}</span>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

window.DetNavbar = DetNavbar;
window.DetHero = DetHero;
window.EarningsCalc = EarningsCalc;
window.WeekInLife = WeekInLife;
