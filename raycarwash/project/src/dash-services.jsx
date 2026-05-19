// Services / Supplies / Profile / Settings / Help

function ViewServices() {
  return (
    <div className="dp">
      <div className="dp-head">
        <div>
          <h1 className="dp-h1">Services & pricing</h1>
          <div className="dp-sub">Manage what you offer, how long it takes, and what you charge</div>
        </div>
        <div className="dp-head-actions">
          <button className="btn btn-outline btn-sm"><IconCamera size={14}/> Add photos</button>
          <button className="btn btn-dark btn-sm"><IconPlus size={14}/> New service</button>
        </div>
      </div>

      <div className="kpi-grid">
        <KpiCard label="Active services" value={5} icon={<IconTag size={14}/>} iconTone="brand" foot="1 draft"/>
        <KpiCard label="Top seller"      value="Full detail" icon={<IconStar size={14}/>} iconTone="warn" foot="16 bookings · 30d"/>
        <KpiCard label="Avg ticket"      value="$153" delta={5} icon={<IconWallet size={14}/>} foot="Up from $146"/>
        <KpiCard label="Add-on attach rate" value="41%" delta={8} icon={<IconTrending size={14}/>} iconTone="ok" foot="Platform avg: 28%"/>
      </div>

      <div className="card">
        <div className="card-head">
          <div className="card-title">Service catalog</div>
          <div className="dp-head-actions">
            <div className="seg">
              <button className="on">All</button>
              <button>Active</button>
              <button>Add-ons</button>
              <button>Drafts</button>
            </div>
          </div>
        </div>
        <div className="card-body">
          <div className="svc-grid-dash">
            {dashData.services.map((s) => (
              <div key={s.id} className={"svc-tile " + (s.draft ? "draft " : "") + (!s.active ? "off " : "")}>
                {s.popular && <span className="vip-chip" style={{ position: "absolute", top: -8, right: 14 }}>★ Top seller</span>}
                {s.addon && <span className="pill mute" style={{ position: "absolute", top: 12, right: 12, fontSize: 10 }}>Add-on</span>}
                <div className="svc-tile-top">
                  <div>
                    <div className="svc-tile-name">{s.name}</div>
                    <div className="svc-tile-dur">{s.dur} min · ${Math.round(s.price * (60/s.dur))}/hr</div>
                  </div>
                  <div className="svc-tile-price">
                    {s.draft ? "—" : "$" + s.price}
                  </div>
                </div>
                <ul className="svc-tile-feats">
                  {s.feats.map((f, i) => (
                    <li key={i}><IconCheck size={12}/> {f}</li>
                  ))}
                </ul>
                <div className="svc-tile-foot">
                  <span>{s.bookings30d} bookings · 30d</span>
                  <div style={{ display: "flex", gap: 4 }}>
                    <button className={"toggle " + (s.active ? "on" : "")}></button>
                    <button className="btn-ghost"><IconMore size={14}/></button>
                  </div>
                </div>
              </div>
            ))}
            <div className="svc-tile draft" style={{ alignItems: "center", justifyContent: "center", textAlign: "center", minHeight: 230, cursor: "pointer" }}>
              <IconPlus size={28} style={{ color: "var(--ink-400)", margin: "0 auto" }}/>
              <div style={{ fontWeight: 600, color: "var(--ink-700)" }}>Create a new service</div>
              <div className="card-sub" style={{ marginTop: 0 }}>Set price, duration, included features</div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-head">
            <div className="card-title">Promo codes</div>
            <button className="btn btn-outline btn-xs"><IconPlus size={12}/> New code</button>
          </div>
          <div className="card-body">
            {[
              ["FIRST20", "20% off first wash", 24, "Active"],
              ["SPRING50", "$50 off premium ceramic", 6, "Active"],
              ["REFER15", "15% for referrers", 31, "Active"],
              ["WELCOME10", "10% off · expired", 142, "Expired"],
            ].map(([code, desc, uses, status], i) => (
              <div key={code} style={{
                display: "grid",
                gridTemplateColumns: "100px 1fr auto auto",
                gap: 12,
                alignItems: "center",
                padding: "12px 0",
                borderBottom: i === 3 ? 0 : "1px solid var(--ink-100)",
              }}>
                <span style={{ fontFamily: "JetBrains Mono, monospace", fontWeight: 600, fontSize: 12, padding: "3px 8px", background: "var(--ink-100)", borderRadius: 6, color: "var(--ink-900)" }}>
                  {code}
                </span>
                <span style={{ fontSize: 13, color: "var(--ink-700)" }}>{desc}</span>
                <span className="card-sub" style={{ marginTop: 0, fontSize: 11.5 }}>{uses} uses</span>
                <Pill kind={status === "Active" ? "ok" : "mute"}>{status}</Pill>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-head">
            <div className="card-title">Service area & pricing rules</div>
          </div>
          <div className="card-body">
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {[
                ["Travel surcharge", "Beyond 8 mi", "+$15"],
                ["Weekend premium", "Sat & Sun", "+10%"],
                ["Same-day booking", "Within 4 hours", "+$20"],
                ["Loyalty discount", "After 10 bookings", "−10%"],
                ["Group / fleet", "3+ vehicles same address", "−15%"],
              ].map(([n, m, v], i) => (
                <div key={n} style={{ display: "flex", alignItems: "center", padding: "10px 12px", border: "1px solid var(--ink-100)", borderRadius: 8 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, color: "var(--ink-900)", fontSize: 13 }}>{n}</div>
                    <div className="card-sub" style={{ marginTop: 0 }}>{m}</div>
                  </div>
                  <span style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 700, color: v.startsWith("−") ? "var(--ok)" : "var(--ink-900)", marginRight: 12 }}>
                    {v}
                  </span>
                  <button className="toggle on"></button>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Supplies
function ViewSupplies() {
  const items = [
    { n: "Wheel cleaner",            stock: 1,  par: 4,  unit: "bottle",  cost: 14, last: "Apr 22", supplier: "Chemical Guys" },
    { n: "Microfiber towels",        stock: 18, par: 30, unit: "towel",   cost: 2,  last: "Apr 18", supplier: "Costco" },
    { n: "Carnauba wax",             stock: 3,  par: 2,  unit: "tin",     cost: 28, last: "Apr 12", supplier: "Meguiar's" },
    { n: "Glass cleaner concentrate",stock: 2,  par: 3,  unit: "gallon",  cost: 22, last: "Apr 9",  supplier: "Stoner" },
    { n: "Interior shampoo",         stock: 4,  par: 4,  unit: "gallon",  cost: 31, last: "Apr 4",  supplier: "Chemical Guys" },
    { n: "Pet hair brush",           stock: 5,  par: 4,  unit: "tool",    cost: 12, last: "Mar 28", supplier: "Amazon" },
    { n: "Foam cannon soap",         stock: 6,  par: 5,  unit: "gallon",  cost: 26, last: "Mar 22", supplier: "Adam's" },
  ];

  const lowCount = items.filter(i => i.stock < i.par).length;

  return (
    <div className="dp">
      <div className="dp-head">
        <div>
          <h1 className="dp-h1">Supplies</h1>
          <div className="dp-sub">Track inventory, reorder, claim supply credits</div>
        </div>
        <div className="dp-head-actions">
          <button className="btn btn-outline btn-sm"><IconUpload size={14}/> Scan receipt</button>
          <button className="btn btn-dark btn-sm"><IconShoppingBag size={14}/> Reorder all low</button>
        </div>
      </div>

      <div className="kpi-grid">
        <KpiCard label="Below par"     value={lowCount}    icon={<IconAlertTriangle size={14}/>} iconTone="warn" foot="Reorder recommended"/>
        <KpiCard label="Inventory value" value="$486" icon={<IconShoppingBag size={14}/>} foot="At current stock"/>
        <KpiCard label="Spent · 30d"   value="$214" delta={-6} icon={<IconWallet size={14}/>} foot="Below $250 budget"/>
        <KpiCard label="Supply credits" value="$84"  icon={<IconWallet size={14}/>} iconTone="ok" foot="Partner discount available"/>
      </div>

      <div className="card">
        <div className="card-head">
          <div className="card-title">Inventory</div>
          <div className="dp-head-actions">
            <button className="btn-ghost"><IconFilter size={14}/> Filter</button>
          </div>
        </div>
        <div className="card-body flush">
          <table className="tbl">
            <thead>
              <tr>
                <th>Item</th>
                <th>Stock</th>
                <th>Par</th>
                <th>Status</th>
                <th>Cost</th>
                <th>Last bought</th>
                <th>Supplier</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map(i => {
                const low = i.stock < i.par;
                return (
                  <tr key={i.n}>
                    <td className="b">{i.n}</td>
                    <td className="num">{i.stock} {i.unit}{i.stock !== 1 ? "s" : ""}</td>
                    <td className="num m">{i.par}</td>
                    <td>
                      <Pill kind={low ? "warn" : "ok"}>{low ? "Low" : "OK"}</Pill>
                    </td>
                    <td className="num">${i.cost}</td>
                    <td className="m">{i.last}</td>
                    <td className="m">{i.supplier}</td>
                    <td>
                      <button className="btn btn-outline btn-xs"><IconPlus size={12}/> Reorder</button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// Profile
function ViewProfile() {
  return (
    <div className="dp">
      <div className="dp-head">
        <div>
          <h1 className="dp-h1">Profile</h1>
          <div className="dp-sub">This is what customers see when they book you</div>
        </div>
        <div className="dp-head-actions">
          <button className="btn btn-outline btn-sm"><IconShare size={14}/> Share link</button>
          <button className="btn btn-dark btn-sm">Save changes</button>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-head">
            <div className="card-title">Public profile</div>
          </div>
          <div className="card-body">
            <div style={{ display: "flex", gap: 18, alignItems: "center" }}>
              <div style={{
                width: 84, height: 84, borderRadius: "50%",
                background: "linear-gradient(135deg, #2563eb, #1e3a8a)",
                color: "white",
                display: "inline-flex", alignItems: "center", justifyContent: "center",
                fontFamily: "Space Grotesk, sans-serif",
                fontWeight: 700, fontSize: 28,
              }}>MT</div>
              <div style={{ flex: 1 }}>
                <button className="btn btn-outline btn-sm"><IconCamera size={14}/> Upload photo</button>
                <div className="card-sub" style={{ marginTop: 8 }}>
                  Pro tip: detailers with a real photo book 2.4× more jobs.
                </div>
              </div>
            </div>

            <div style={{ marginTop: 20, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <FormField label="Display name" value="Marcus Tate"/>
              <FormField label="Business name" value="MT Mobile Detailing"/>
              <FormField label="Phone" value="(260) 555-0162"/>
              <FormField label="Email" value="marcus@mtdetail.co"/>
              <div style={{ gridColumn: "1 / -1" }}>
                <FormField label="Bio" value="10-year detailer based in Fort Wayne. Specialized in interior deep cleans and ceramic coats. Mobile water + power. Family-owned." textarea/>
              </div>
            </div>

            <div style={{ marginTop: 20 }}>
              <div className="ps-eyebrow muted">Specialties</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
                {["Ceramic coating", "Pet hair", "Leather restoration", "Headlight restoration", "Boats / RVs"].map(t => (
                  <Pill key={t} kind="info">{t}</Pill>
                ))}
                <button className="btn-ghost btn-xs">+ Add</button>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-head">
            <div className="card-title">Verifications & badges</div>
          </div>
          <div className="card-body">
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {[
                ["Identity verified",        "ID checked · Onfido", "ok"],
                ["Background check",         "Clear · renews Jan 2027", "ok"],
                ["Insurance on file",        "$2M liability · State Farm", "ok"],
                ["W-9 submitted",            "Tax year 2025", "ok"],
                ["Pro certification",        "IDA-certified detailer", "ok"],
                ["Eco-friendly products",    "Self-attested", "info"],
              ].map(([t, m, k], i) => (
                <div key={t} style={{ display: "flex", alignItems: "center", padding: "10px 12px", border: "1px solid var(--ink-100)", borderRadius: 8, gap: 12 }}>
                  <span className={"kpi-ic " + k}>{k === "ok" ? <IconShield size={14}/> : <IconCheck size={14}/>}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, color: "var(--ink-900)", fontSize: 13 }}>{t}</div>
                    <div className="card-sub" style={{ marginTop: 0 }}>{m}</div>
                  </div>
                  <Pill kind={k}>{k === "ok" ? "Verified" : "Self"}</Pill>
                </div>
              ))}
            </div>

            <div style={{ marginTop: 20 }}>
              <div className="ps-eyebrow muted">Achievement badges</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8, marginTop: 10 }}>
                {[
                  ["🏆", "300 Jobs"],
                  ["⭐", "4.9+ Rating"],
                  ["⚡", "Quick Responder"],
                  ["💎", "Gold Tier"],
                ].map(([e, l]) => (
                  <div key={l} style={{ textAlign: "center", padding: 12, border: "1px solid var(--ink-150)", borderRadius: 10, background: "white" }}>
                    <div style={{ fontSize: 22 }}>{e}</div>
                    <div style={{ fontSize: 11, fontWeight: 600, color: "var(--ink-700)", marginTop: 4 }}>{l}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <div className="card-title">Portfolio · before / after</div>
          <button className="btn-ghost"><IconPlus size={14}/> Add gallery</button>
        </div>
        <div className="card-body">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
            {["Full detail · Q5", "Interior · Model Y", "Ceramic · M3", "Pet hair · Pilot", "Headlight resto", "Engine bay", "Leather resto", "Wax + clay"].map((t, i) => (
              <div key={i} style={{ aspectRatio: "1/1", borderRadius: 10, overflow: "hidden", position: "relative" }}>
                <div className="striped-ph" style={{ width: "100%", height: "100%" }}>{t}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function FormField({ label, value, textarea }) {
  const baseStyle = {
    width: "100%",
    padding: "9px 12px",
    border: "1px solid var(--ink-200)",
    borderRadius: 8,
    font: "inherit",
    fontSize: 13.5,
    color: "var(--ink-900)",
    background: "white",
  };
  return (
    <div>
      <label style={{ display: "block", fontSize: 11.5, fontWeight: 600, color: "var(--ink-500)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6 }}>{label}</label>
      {textarea ? (
        <textarea defaultValue={value} style={{ ...baseStyle, minHeight: 80, resize: "vertical" }} />
      ) : (
        <input defaultValue={value} style={baseStyle}/>
      )}
    </div>
  );
}

// Settings
function ViewSettings() {
  return (
    <div className="dp">
      <div className="dp-head">
        <div>
          <h1 className="dp-h1">Settings</h1>
          <div className="dp-sub">Notifications, security, and account preferences</div>
        </div>
      </div>
      <div className="grid-2">
        <SettingsCard title="Notifications" rows={[
          ["New job requests", "Push + SMS", true],
          ["Customer messages", "Push only", true],
          ["Daily summary", "Email at 7am", true],
          ["Weekly payout", "Push + email", true],
          ["Reviews", "Email only", true],
          ["Marketing & tips", "Email", false],
        ]}/>
        <SettingsCard title="Auto-accept rules" rows={[
          ["Auto-accept repeat customers", "VIP only", true],
          ["Auto-decline beyond 10 mi", "Save travel time", false],
          ["Auto-decline below $40", "Min ticket size", true],
          ["Snooze new jobs", "Daily 8pm – 7am", true],
        ]}/>
        <SettingsCard title="Security" rows={[
          ["Two-factor authentication", "Phone · ••62", true],
          ["Active sessions", "2 devices", null, "Manage"],
          ["Login alerts", "New device", true],
          ["Change password", "Last set 4 months ago", null, "Change"],
        ]}/>
        <SettingsCard title="Account & data" rows={[
          ["Export all data", "ZIP · jobs, reviews, photos", null, "Request"],
          ["Connected apps", "QuickBooks, Stripe", null, "Manage"],
          ["Pause account", "Hide profile temporarily", null, "Pause"],
          ["Delete account", "Permanent removal", null, "Delete"],
        ]}/>
      </div>
    </div>
  );
}

function SettingsCard({ title, rows }) {
  return (
    <div className="card">
      <div className="card-head">
        <div className="card-title">{title}</div>
      </div>
      <div className="card-body" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {rows.map(([n, m, on, action], i) => (
          <div key={n} style={{ display: "flex", alignItems: "center", padding: "10px 12px", border: "1px solid var(--ink-100)", borderRadius: 8 }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, color: "var(--ink-900)", fontSize: 13 }}>{n}</div>
              <div className="card-sub" style={{ marginTop: 0 }}>{m}</div>
            </div>
            {action ? (
              <button className={"btn btn-outline btn-xs " + (action === "Delete" ? "danger" : "")}>{action}</button>
            ) : (
              <button className={"toggle " + (on ? "on" : "")}></button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// Help
function ViewHelp() {
  return (
    <div className="dp">
      <div className="dp-head">
        <div>
          <h1 className="dp-h1">Help & support</h1>
          <div className="dp-sub">Get answers fast, or talk to a human</div>
        </div>
      </div>

      <div className="grid-3">
        {[
          ["💬", "Live chat",     "Avg response: 2 min",  "Online · 9a–9p"],
          ["📞", "Call dispatch", "(260) 555-WASH",       "24/7 for urgent"],
          ["📧", "Email support", "pros@raycarwash.com",  "Reply in 4hr"],
        ].map(([e, t, sub, m]) => (
          <div key={t} className="card">
            <div className="card-body" style={{ textAlign: "center" }}>
              <div style={{ fontSize: 28 }}>{e}</div>
              <div style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 700, fontSize: 16, marginTop: 8 }}>{t}</div>
              <div className="card-sub" style={{ marginTop: 4 }}>{sub}</div>
              <Pill kind="ok" style={{ marginTop: 10 }}>{m}</Pill>
            </div>
          </div>
        ))}
      </div>

      <div className="card">
        <div className="card-head">
          <div className="card-title">Common questions</div>
        </div>
        <div className="card-body" style={{ paddingTop: 0 }}>
          {[
            ["When do payouts arrive?", "Auto-payouts run every Friday at 5pm. Instant payouts arrive in <30 min for a $0.50 fee."],
            ["What's the platform fee?", "15% per completed job. This covers payments, insurance, dispatch, customer support, and marketing."],
            ["How does insurance work?", "Every job is covered up to $2M while you're working through the platform. Damage claims are filed in-app."],
            ["What if a customer cancels?", "If they cancel less than 2 hours before, you get 50% of the ticket as a cancellation fee."],
            ["How do I get more bookings?", "Respond fast (<5 min), keep your rating high, and add good before/after photos. We surface high responders first."],
          ].map(([q, a], i) => (
            <details key={i} style={{ borderBottom: i === 4 ? 0 : "1px solid var(--ink-100)", padding: "12px 0" }}>
              <summary style={{ fontWeight: 600, color: "var(--ink-900)", fontSize: 13.5, cursor: "pointer", listStyle: "none", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                {q}
                <IconChevronDown size={16} style={{ color: "var(--ink-400)" }}/>
              </summary>
              <div style={{ marginTop: 8, color: "var(--ink-600)", fontSize: 13, lineHeight: 1.55 }}>{a}</div>
            </details>
          ))}
        </div>
      </div>
    </div>
  );
}

window.ViewServices = ViewServices;
window.ViewSupplies = ViewSupplies;
window.ViewProfile = ViewProfile;
window.ViewSettings = ViewSettings;
window.ViewHelp = ViewHelp;
