// Earnings view — KPIs + chart + ledger + payouts
function ViewEarnings() {
  return (
    <div className="dp">
      <div className="dp-head">
        <div>
          <h1 className="dp-h1">Earnings</h1>
          <div className="dp-sub">Track payouts, fees, and tax-ready reports</div>
        </div>
        <div className="dp-head-actions">
          <div className="seg">
            <button>7d</button>
            <button className="on">30d</button>
            <button>90d</button>
            <button>YTD</button>
            <button>All</button>
          </div>
          <button className="btn btn-outline btn-sm"><IconDownload size={14}/> Statement PDF</button>
          <button className="btn btn-dark btn-sm"><IconWallet size={14}/> Cash out · $412</button>
        </div>
      </div>

      <div className="kpi-grid">
        <KpiCard label="Available to cash out" value="$412.00" delta={null} icon={<IconWallet size={14}/>} iconTone="ok" foot="Instant payout · $0.50 fee" />
        <KpiCard label="Pending settlement"   value="$786.40" icon={<IconClock size={14}/>} foot="Auto-deposits Friday" />
        <KpiCard label="This month gross"     value="$8,642"  delta={14} icon={<IconChart size={14}/>} iconTone="brand" foot="73% to monthly goal" />
        <KpiCard label="Lifetime earnings"    value="$48,231" icon={<IconTrending size={14}/>} foot="312 jobs · since Jan 2024" />
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-head">
            <div>
              <div className="card-title">Earnings — last 14 days</div>
              <div className="card-sub">Base service + tips · after platform fee</div>
            </div>
            <div className="chart-legend" style={{ paddingTop: 0 }}>
              <span><span className="sw"></span> Base</span>
              <span><span className="sw t"></span> Tips</span>
            </div>
          </div>
          <div className="card-body">
            <EarningsBars data={dashData.earnings14d} />
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginTop: 18 }}>
              <Stat lbl="14d gross"       val="$2,891" />
              <Stat lbl="Platform fee 15%" val="−$434" />
              <Stat lbl="Tips earned"      val="$356" />
              <Stat lbl="Net to bank"      val="$2,813" big />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-head">
            <div>
              <div className="card-title">Breakdown</div>
              <div className="card-sub">By service · 30 days</div>
            </div>
          </div>
          <div className="card-body">
            <DonutBreakdown
              parts={[
                { lbl: "Full detail",   v: 4520, color: "#2563eb" },
                { lbl: "Interior",      v: 1980, color: "#3b82f6" },
                { lbl: "Express",       v: 880,  color: "#93c5fd" },
                { lbl: "Premium ceramic", v: 896, color: "#1e3a8a" },
                { lbl: "Add-ons",       v: 366,  color: "#10b981" },
              ]}
            />
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-head">
            <div className="card-title">Activity ledger</div>
            <div className="dp-head-actions">
              <button className="btn-ghost"><IconFilter size={14}/> Filter</button>
              <button className="btn-ghost"><IconDownload size={14}/> CSV</button>
            </div>
          </div>
          <div className="card-body" style={{ paddingTop: 0 }}>
            {dashData.payouts.map((p, i) => (
              <div key={i} className="ledger-row">
                <span className={"ledger-ic " + p.kind}>
                  {p.kind === "in" ? <IconArrowDownRight size={14}/> :
                   p.kind === "out" ? <IconArrowUpRight size={14}/> :
                   <IconAlertTriangle size={14}/>}
                </span>
                <div>
                  <div className="ledger-lbl">{p.lbl}</div>
                  <div className="ledger-sub">{p.d}</div>
                </div>
                <div className={"ledger-amt " + (p.kind === "in" ? "in" : "out")}>
                  {p.kind === "in" ? "+" : "−"}${p.amt.toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-head">
            <div className="card-title">Payout & taxes</div>
          </div>
          <div className="card-body">
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div style={{ padding: 14, border: "1px solid var(--ink-150)", borderRadius: 10 }}>
                <div className="card-sub" style={{ marginTop: 0 }}>Deposit account</div>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 6 }}>
                  <span style={{ width: 36, height: 24, borderRadius: 4, background: "linear-gradient(135deg, #117ACA, #0a4d80)" }}></span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, fontSize: 13 }}>Chase Checking · ••2847</div>
                    <div className="card-sub" style={{ marginTop: 0, fontSize: 11.5 }}>Default · since Jan 2024</div>
                  </div>
                  <button className="btn-ghost">Change</button>
                </div>
              </div>

              <div style={{ padding: 14, border: "1px solid var(--ink-150)", borderRadius: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 13, color: "var(--ink-900)" }}>Auto-payout</div>
                    <div className="card-sub" style={{ marginTop: 0, fontSize: 11.5 }}>Every Friday at 5pm</div>
                  </div>
                  <button className="toggle on"></button>
                </div>
              </div>

              <div style={{ padding: 14, border: "1px solid var(--ink-150)", borderRadius: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 13, color: "var(--ink-900)" }}>2025 tax forms</div>
                    <div className="card-sub" style={{ marginTop: 0, fontSize: 11.5 }}>1099-NEC ready for download</div>
                  </div>
                  <button className="btn btn-outline btn-xs"><IconFile size={12}/> Download</button>
                </div>
              </div>

              <div style={{ padding: 14, border: "1px solid var(--ink-150)", borderRadius: 10 }}>
                <div style={{ fontWeight: 600, fontSize: 13, color: "var(--ink-900)" }}>Estimated tax set-aside</div>
                <div className="card-sub" style={{ marginTop: 0, fontSize: 11.5 }}>30% of gross · ~$2,592 this month</div>
                <div className="ps-prog-bar" style={{ marginTop: 10 }}>
                  <div className="ps-prog-fill" style={{ width: "62%" }}></div>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6, fontSize: 11.5, color: "var(--ink-500)" }}>
                  <span>Saved: $1,610</span>
                  <span>Goal: $2,592</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Stat({ lbl, val, big }) {
  return (
    <div>
      <div className="ps-eyebrow muted">{lbl}</div>
      <div style={{
        fontFamily: "Space Grotesk, sans-serif",
        fontSize: big ? 22 : 17,
        fontWeight: 700,
        letterSpacing: "-0.02em",
        color: "var(--ink-900)",
        marginTop: 4,
      }}>{val}</div>
    </div>
  );
}

function DonutBreakdown({ parts }) {
  const total = parts.reduce((a, p) => a + p.v, 0);
  let acc = 0;
  const r = 60, c = 80;
  const ringSegments = parts.map((p) => {
    const frac = p.v / total;
    const start = acc;
    const end = acc + frac;
    acc = end;
    const startAngle = start * 2 * Math.PI - Math.PI/2;
    const endAngle = end * 2 * Math.PI - Math.PI/2;
    const x1 = c + r * Math.cos(startAngle);
    const y1 = c + r * Math.sin(startAngle);
    const x2 = c + r * Math.cos(endAngle);
    const y2 = c + r * Math.sin(endAngle);
    const large = frac > 0.5 ? 1 : 0;
    return { d: `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`, color: p.color };
  });
  return (
    <div style={{ display: "grid", gridTemplateColumns: "160px 1fr", gap: 18, alignItems: "center" }}>
      <svg viewBox="0 0 160 160" width="100%">
        {ringSegments.map((s, i) => (
          <path key={i} d={s.d} fill="none" stroke={s.color} strokeWidth="22"/>
        ))}
        <text x="80" y="78" textAnchor="middle" style={{ fontFamily: "Space Grotesk, sans-serif", fontSize: 22, fontWeight: 700, fill: "var(--ink-900)" }}>
          ${(total/1000).toFixed(1)}k
        </text>
        <text x="80" y="96" textAnchor="middle" style={{ fontSize: 10, fill: "var(--ink-500)", fontWeight: 600, letterSpacing: "0.05em", textTransform: "uppercase" }}>
          30d gross
        </text>
      </svg>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {parts.map((p) => (
          <div key={p.lbl} style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13 }}>
            <span style={{ width: 10, height: 10, borderRadius: 3, background: p.color, flexShrink: 0 }}></span>
            <span style={{ flex: 1, color: "var(--ink-700)", fontWeight: 500 }}>{p.lbl}</span>
            <span style={{ color: "var(--ink-500)", fontSize: 12 }}>{Math.round(p.v / total * 100)}%</span>
            <span style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 700, color: "var(--ink-900)", minWidth: 60, textAlign: "right" }}>
              ${p.v.toLocaleString()}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

window.ViewEarnings = ViewEarnings;
