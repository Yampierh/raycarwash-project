// Overview view — KPI grid, route, incoming, insights, recent reviews
function ViewOverview({ onView }) {
  const k = dashData.kpis;

  return (
    <div className="dp">
      <div className="dp-head">
        <div>
          <h1 className="dp-h1">Good morning, Marcus 👋</h1>
          <div className="dp-sub">
            Tuesday, May 5, 2026 · 5 jobs scheduled · {fmtMoney(412)} expected today
          </div>
        </div>
        <div className="dp-head-actions">
          <div className="seg">
            <button className="on">Today</button>
            <button>Week</button>
            <button>Month</button>
            <button>Year</button>
          </div>
          <button className="btn btn-outline btn-sm"><IconDownload size={14}/> Export</button>
        </div>
      </div>

      {/* KPI Row */}
      <div className="kpi-grid">
        <KpiCard
          label="Today's jobs"
          value={k.todayJobs.v}
          delta={k.todayJobs.deltaPct}
          icon={<IconBriefcase size={14}/>}
          iconTone="brand"
          foot="2 done · 1 in progress · 2 upcoming"
        />
        <KpiCard
          label="Today's earnings"
          value={fmtMoney(k.todayEarnings.v)}
          delta={k.todayEarnings.deltaPct}
          icon={<IconWallet size={14}/>}
          iconTone="ok"
          foot={`+${fmtMoney(k.todayEarnings.delta)} vs avg Tuesday`}
        />
        <KpiCard
          label="Week earnings"
          value={fmtMoney(k.weekEarnings.v)}
          delta={k.weekEarnings.deltaPct}
          icon={<IconChart size={14}/>}
          spark
        />
        <KpiCard
          label="Rating · last 30d"
          value={k.rating.v.toFixed(2)}
          unit="★"
          delta={k.rating.delta}
          deltaSuffix=""
          icon={<IconStar size={14}/>}
          iconTone="warn"
          foot="Based on 38 reviews"
        />
      </div>

      {/* Route + Incoming */}
      <div className="grid-2">
        <div className="card">
          <div className="card-head">
            <div>
              <div className="card-title">Today's route</div>
              <div className="card-sub">5 stops · 23 miles · ends 7:00 PM</div>
            </div>
            <div className="dp-head-actions">
              <button className="btn-ghost"><IconWaze size={14}/> Open in Waze</button>
              <button className="btn-ghost" onClick={() => onView("route")}>
                Full route <IconChevronRight size={14}/>
              </button>
            </div>
          </div>
          <div className="route-card">
            <RouteMap />
            <div className="route-stops">
              {dashData.route.map((s) => (
                <div key={s.id} className={"route-stop " + s.status}>
                  <span className={"route-pin " + s.status}>{s.status === "done" ? "✓" : s.id}</span>
                  <span className="route-time">{s.time}</span>
                  <div className="route-info">
                    <div className="nm">{s.who}</div>
                    <div className="sv">{s.svc} · {s.where}</div>
                  </div>
                  <Pill kind={s.status === "done" ? "ok" : s.status === "now" ? "info" : "mute"}>
                    {s.status === "done" ? "Done" : s.status === "now" ? "In progress" : `$${s.pay}`}
                  </Pill>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-head">
            <div>
              <div className="card-title">Incoming requests</div>
              <div className="card-sub">3 new · respond within 5 min for priority</div>
            </div>
            <button className="btn-ghost" onClick={() => onView("jobs")}>See all</button>
          </div>
          <div className="card-body">
            {dashData.incoming.slice(0, 2).map((j) => (
              <JobReqCard key={j.id} j={j} />
            ))}
          </div>
        </div>
      </div>

      {/* Quick actions */}
      <div className="card">
        <div className="card-head">
          <div className="card-title">Quick actions</div>
        </div>
        <div className="card-body">
          <div className="qa-grid">
            <button className="qa-btn">
              <IconPlus size={18} className="ic"/>
              <span className="t">Add a job manually</span>
              <span className="m">Off-platform booking</span>
            </button>
            <button className="qa-btn">
              <IconCalendar size={18} className="ic"/>
              <span className="t">Block off time</span>
              <span className="m">Set vacation or break</span>
            </button>
            <button className="qa-btn">
              <IconTag size={18} className="ic"/>
              <span className="t">Create promo code</span>
              <span className="m">Offer discounts to regulars</span>
            </button>
            <button className="qa-btn">
              <IconDownload size={18} className="ic"/>
              <span className="t">Tax statements</span>
              <span className="m">2025 · 1099-NEC ready</span>
            </button>
          </div>
        </div>
      </div>

      {/* Insights + Recent reviews */}
      <div className="grid-2">
        <div className="card">
          <div className="card-head">
            <div>
              <div className="card-title">Insights</div>
              <div className="card-sub">Tailored to your last 30 days</div>
            </div>
            <span className="pill mute">Auto-generated</span>
          </div>
          <div className="card-body">
            <div className="rail-list">
              {dashData.insights.map((i, idx) => (
                <div className="rail-row" key={idx}>
                  <span className={"rail-dot " + (i.icon === "warn" ? "warn" : i.icon === "ok" ? "ok" : "brand")}></span>
                  <div className="rail-text">
                    <strong>{i.t}</strong>
                    <div className="t">{i.b}</div>
                  </div>
                  <button className="btn-ghost"><IconChevronRight size={14}/></button>
                </div>
              ))}
              <div className="rail-row">
                <span className="rail-dot"></span>
                <div className="rail-text">
                  <strong>Drive efficiency: 4.2 mi avg between stops</strong>
                  <div className="t">Cluster bookings by neighborhood to save ~$28/week in gas</div>
                </div>
                <button className="btn-ghost"><IconChevronRight size={14}/></button>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-head">
            <div>
              <div className="card-title">Recent reviews</div>
              <div className="card-sub">Last 7 days</div>
            </div>
            <button className="btn-ghost" onClick={() => onView("reviews")}>All reviews</button>
          </div>
          <div className="card-body flush">
            {dashData.reviews.slice(0, 2).map(r => (
              <div className="rv-item" key={r.id}>
                <div className="rv-item-head">
                  <span className="rv-item-stars">{"★".repeat(r.stars)}{"☆".repeat(5-r.stars)}</span>
                  <span className="rv-item-name">{r.name}</span>
                  <span className="rv-item-meta">{r.svc} · {r.when}</span>
                </div>
                <div className="rv-item-body" style={{ display: "-webkit-box", WebkitBoxOrient: "vertical", WebkitLineClamp: 2, overflow: "hidden" }}>
                  {r.body}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Mini earnings preview */}
      <div className="card">
        <div className="card-head">
          <div>
            <div className="card-title">Last 14 days</div>
            <div className="card-sub">Net earnings · base + tips</div>
          </div>
          <div className="dp-head-actions">
            <div className="chart-legend">
              <span><span className="sw"></span> Base</span>
              <span><span className="sw t"></span> Tips</span>
            </div>
            <button className="btn-ghost" onClick={() => onView("earnings")}>
              Full report <IconChevronRight size={14}/>
            </button>
          </div>
        </div>
        <div className="card-body">
          <EarningsBars data={dashData.earnings14d} />
        </div>
      </div>
    </div>
  );
}

function KpiCard({ label, value, unit, delta, deltaSuffix = "%", icon, iconTone = "", foot, spark }) {
  return (
    <div className="kpi">
      <div className="kpi-top">
        <span className={"kpi-ic " + iconTone}>{icon}</span>
        <span>{label}</span>
      </div>
      <div className="kpi-big">
        {value}
        {unit && <span className="unit">{unit}</span>}
      </div>
      {spark ? (
        <SparkLine values={[140, 180, 0, 260, 320, 180, 0, 200, 240, 170, 290, 340, 220, 0]}/>
      ) : (
        <div className="kpi-foot">
          <span>{foot}</span>
          <Delta v={delta} suffix={deltaSuffix} />
        </div>
      )}
    </div>
  );
}

function SparkLine({ values, color = "var(--brand)" }) {
  const max = Math.max(...values, 1);
  const w = 200, h = 36;
  const step = w / (values.length - 1);
  const pts = values.map((v, i) => [i * step, h - (v / max) * (h - 4) - 2]);
  const d = pts.map((p, i) => (i === 0 ? "M" : "L") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
  const area = d + ` L${w} ${h} L0 ${h} Z`;
  return (
    <svg className="spark" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
      <path d={area} fill={color} fillOpacity="0.12" />
      <path d={d} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function JobReqCard({ j, onAccept, onDecline }) {
  return (
    <div className={"job-req " + (j.new ? "new" : "")}>
      <div>
        <div className="jr-svc">
          {j.svc}
          {j.surge && <span className="vip-chip" style={{ marginLeft: 8 }}>Surge +20%</span>}
        </div>
        <div className="jr-meta">
          <span><IconCar size={12}/> {j.car}</span>
          <span><IconMapPin size={12}/> {j.where}</span>
          <span><IconClock size={12}/> {j.when}</span>
          <span><IconStar size={12}/> {j.customer} · {j.rating.toFixed(1)}</span>
        </div>
        {j.addOns.length > 0 && (
          <div style={{ marginTop: 6, display: "flex", gap: 6, flexWrap: "wrap" }}>
            {j.addOns.map(a => <Pill key={a} kind="mute">+ {a}</Pill>)}
          </div>
        )}
      </div>
      <div>
        <div className="jr-pay">${j.pay}</div>
        <div className="jr-meta" style={{ justifyContent: "flex-end", marginTop: 2 }}>
          <span>{j.duration}m</span>
        </div>
      </div>
      <div className="jr-actions">
        <button className="btn btn-dark btn-xs" onClick={onAccept}>Accept</button>
        <button className="btn btn-outline btn-xs" onClick={onDecline}>Decline</button>
        <button className="btn-ghost"><IconMessageSquare size={14}/> Message</button>
        <button className="btn-ghost"><IconMapPin size={14}/> Map</button>
      </div>
    </div>
  );
}

function RouteMap() {
  return (
    <div className="route-map" aria-hidden>
      <svg viewBox="0 0 200 220" preserveAspectRatio="none" width="100%" height="100%">
        <defs>
          <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="rgba(99,102,241,0.18)" strokeWidth="0.5"/>
          </pattern>
        </defs>
        <rect width="200" height="220" fill="url(#grid)"/>
        {/* roads */}
        <path d="M0 60 L200 60" stroke="white" strokeWidth="6" opacity="0.7"/>
        <path d="M40 0 L40 220" stroke="white" strokeWidth="4" opacity="0.7"/>
        <path d="M0 140 L200 140" stroke="white" strokeWidth="4" opacity="0.6"/>
        <path d="M140 0 L140 220" stroke="white" strokeWidth="4" opacity="0.5"/>
        {/* route path */}
        <path d="M30 200 Q60 160 70 130 T100 80 Q130 60 150 40" fill="none" stroke="#1e3a8a" strokeWidth="2.5" strokeDasharray="4 3"/>
        {/* pins */}
        <circle cx="30" cy="200" r="6" fill="#10b981"/>
        <circle cx="70" cy="130" r="6" fill="#10b981"/>
        <circle cx="100" cy="80" r="8" fill="#2563eb" stroke="white" strokeWidth="2"/>
        <circle cx="130" cy="55" r="5" fill="#27272a"/>
        <circle cx="150" cy="40" r="5" fill="#27272a"/>
      </svg>
    </div>
  );
}

function EarningsBars({ data }) {
  const max = Math.max(...data.map(d => d.base + d.tips));
  return (
    <div className="bar-chart">
      {data.map((d, i) => {
        const total = d.base + d.tips;
        const tipsPct = d.tips / max * 100;
        const basePct = d.base / max * 100;
        return (
          <div className="bar-col" key={i}>
            <span className="num">${total}</span>
            <div className="vals" style={{ height: `${basePct + tipsPct}%` }}>
              {d.tips > 0 && <div className="bar tips top" style={{ height: `${tipsPct/(basePct+tipsPct)*100}%` }}></div>}
              {d.base > 0 && <div className="bar" style={{ flex: 1 }}></div>}
            </div>
            <span className="lbl">{d.d.split(" ")[1]}</span>
          </div>
        );
      })}
    </div>
  );
}

window.ViewOverview = ViewOverview;
window.JobReqCard = JobReqCard;
window.EarningsBars = EarningsBars;
window.SparkLine = SparkLine;
