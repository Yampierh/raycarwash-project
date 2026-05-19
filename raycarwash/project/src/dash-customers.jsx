// Customers view — CRM-style
function ViewCustomers() {
  const [filter, setFilter] = useS("all");
  const filtered = dashData.customers.filter(c => {
    if (filter === "vip") return c.vip;
    if (filter === "recent") return c.last === "Today" || c.last === "Tomorrow" || c.last.includes("d ago");
    if (filter === "dormant") return c.last.includes("w ago") || c.last.includes("mo");
    return true;
  });

  return (
    <div className="dp">
      <div className="dp-head">
        <div>
          <h1 className="dp-h1">Customers</h1>
          <div className="dp-sub">142 active · 22 repeat · 5 VIP. Build relationships, drive repeat business.</div>
        </div>
        <div className="dp-head-actions">
          <button className="btn btn-outline btn-sm"><IconMail size={14}/> Send campaign</button>
          <button className="btn btn-dark btn-sm"><IconPlus size={14}/> Add customer</button>
        </div>
      </div>

      <div className="kpi-grid">
        <KpiCard label="Total customers"   value={142} delta={6} icon={<IconUsers size={14}/>} iconTone="brand" foot="+12 this month"/>
        <KpiCard label="Repeat rate"       value="58%" delta={4} icon={<IconRefresh size={14}/>} iconTone="ok" foot="Within 60 days"/>
        <KpiCard label="VIPs (>10 jobs)"   value={5}   icon={<IconStar size={14}/>} iconTone="warn" foot="$11,420 lifetime"/>
        <KpiCard label="Avg lifetime value" value="$339" delta={9} icon={<IconWallet size={14}/>} foot="Across 142 customers"/>
      </div>

      <div className="card">
        <div className="card-head">
          <div className="seg">
            <button className={filter === "all" ? "on" : ""} onClick={() => setFilter("all")}>All</button>
            <button className={filter === "vip" ? "on" : ""} onClick={() => setFilter("vip")}>VIPs</button>
            <button className={filter === "recent" ? "on" : ""} onClick={() => setFilter("recent")}>Recent</button>
            <button className={filter === "dormant" ? "on" : ""} onClick={() => setFilter("dormant")}>Dormant</button>
          </div>
          <div className="dp-head-actions">
            <select style={{
              padding: "7px 10px",
              fontSize: 12.5,
              fontFamily: "inherit",
              border: "1px solid var(--ink-150)",
              borderRadius: 8,
              background: "white",
              color: "var(--ink-700)",
              fontWeight: 600,
            }}>
              <option>Sort: Lifetime value</option>
              <option>Last booking</option>
              <option>Total visits</option>
            </select>
            <button className="btn-ghost"><IconDownload size={14}/></button>
          </div>
        </div>
        <div className="card-body" style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 10 }}>
          {filtered.map((c) => (
            <div key={c.id} className="cust-card">
              <span className="cust-avatar" style={{ background: `linear-gradient(135deg, ${c.color}, ${c.color}cc)` }}>
                {c.init}
              </span>
              <div className="cust-text">
                <div className="cust-name">
                  {c.name}
                  {c.vip && <span className="vip-chip">VIP</span>}
                </div>
                <div className="cust-meta">
                  <span><IconPin size={11}/> {c.loc}</span>
                  <span><IconPhone size={11}/> {c.phone}</span>
                  <span><IconClock size={11}/> Last: {c.last}</span>
                </div>
              </div>
              <div className="cust-stats">
                <div className="v">${c.total.toLocaleString()}</div>
                <div className="l">{c.visits} visit{c.visits !== 1 ? "s" : ""}</div>
              </div>
              <button className="btn-ghost"><IconMore size={16}/></button>
            </div>
          ))}
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-head">
            <div className="card-title">Top customers · lifetime</div>
          </div>
          <div className="card-body" style={{ paddingTop: 0 }}>
            {[...dashData.customers].sort((a,b) => b.total - a.total).slice(0, 5).map((c, i) => (
              <div key={c.id} style={{
                display: "grid",
                gridTemplateColumns: "24px 1fr auto",
                gap: 12,
                alignItems: "center",
                padding: "12px 0",
                borderBottom: i === 4 ? 0 : "1px solid var(--ink-100)",
              }}>
                <span style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 700, color: "var(--ink-400)", fontSize: 13 }}>{i+1}.</span>
                <div>
                  <div style={{ fontWeight: 600, color: "var(--ink-900)", fontSize: 13.5 }}>{c.name}</div>
                  <div className="card-sub" style={{ marginTop: 0, fontSize: 11.5 }}>{c.visits} visits · {c.loc}</div>
                </div>
                <div style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 700, color: "var(--ink-900)", fontSize: 14 }}>
                  ${c.total.toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-head">
            <div className="card-title">Win-back targets</div>
            <span className="pill warn">3 dormant</span>
          </div>
          <div className="card-body">
            <div style={{ marginBottom: 12, fontSize: 13, color: "var(--ink-600)" }}>
              These customers haven't booked in 60+ days. Send a one-tap offer to bring them back.
            </div>
            {["Tara V. · 78d ago · $238 LTV", "Eric L. · 92d ago · $147 LTV", "Pat R. · 104d ago · $890 LTV"].map((s, i) => (
              <div key={i} style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "10px 0",
                borderBottom: i === 2 ? 0 : "1px solid var(--ink-100)",
              }}>
                <span style={{ fontSize: 13, color: "var(--ink-700)" }}>{s}</span>
                <button className="btn btn-outline btn-xs">Send 15% off</button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

window.ViewCustomers = ViewCustomers;
