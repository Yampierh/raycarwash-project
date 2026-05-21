"use client";
import { useState } from "react";
import DashSidebar from "@/components/dashboard/DashSidebar";
import DashHeader from "@/components/dashboard/DashHeader";
import { Briefcase, Wallet, Star, Clock, ArrowRight, Check, X, MapPin, Calendar, TrendingUp } from "lucide-react";

const kpis = [
  { label: "Today's jobs", value: "5", delta: "+25%", sub: "2 done · 1 in progress · 2 upcoming", tone: "up" },
  { label: "Today's earnings", value: "$412", delta: "+18%", sub: "+$78 vs avg Tuesday", tone: "up" },
  { label: "Week earnings", value: "$2,148", delta: "+15%", sub: "5 days worked", tone: "up" },
  { label: "Rating · last 30d", value: "4.92★", delta: "+0.04", sub: "Based on 38 reviews", tone: "up" },
];

const jobs = [
  { id: "JR-1042", svc: "Full detail · interior + ext", car: "2022 Honda Pilot", where: "Aboite Twp · 4.2 mi", when: "Today · 2:00 PM", pay: 179, customer: "Sarah K.", rating: 5.0, status: "new" },
  { id: "JR-1041", svc: "Exterior wash", car: "2019 Subaru Outback", where: "Northwood · 2.1 mi", when: "Tomorrow · 9:30 AM", pay: 65, customer: "Dan O.", rating: 4.8, status: "new", surge: true },
  { id: "JR-1040", svc: "Interior deep clean", car: "2021 Toyota Tacoma", where: "Waynedale · 5.6 mi", when: "Thu, May 8 · 11:00 AM", pay: 119, customer: "Priya M.", rating: 4.9, status: "accepted" },
  { id: "JR-1039", svc: "Full detail", car: "2020 BMW M3", where: "Downtown · 1.8 mi", when: "Fri, May 9 · 9:00 AM", pay: 189, customer: "Tyler B.", rating: 4.7, status: "accepted" },
];

const todayRoute = [
  { id: 1, time: "9:00 AM", who: "Maria G.", svc: "Full detail", where: "Aboite", pay: 149, status: "done" },
  { id: 2, time: "12:30 PM", who: "Dan O.", svc: "Exterior wash", where: "Northwood", pay: 65, status: "done" },
  { id: 3, time: "2:00 PM", who: "Sarah K.", svc: "Full detail", where: "Aboite Twp", pay: 179, status: "now" },
  { id: 4, time: "4:30 PM", who: "Priya M.", svc: "Interior", where: "Waynedale", pay: 119, status: "pending" },
  { id: 5, time: "6:30 PM", who: "Tyler B.", svc: "Exterior", where: "Downtown", pay: 65, status: "pending" },
];

const reviews = [
  { name: "Maria G.", rating: 5, text: "Marcus was incredibly professional and detail-oriented. My car looks brand new!", date: "May 4, 2026" },
  { name: "Tyler B.", rating: 5, text: "Great job on the M3. Paint correction was flawless.", date: "May 3, 2026" },
  { name: "Dan O.", rating: 4, text: "Very good work, showed up exactly on time.", date: "May 2, 2026" },
];

const earnings14d = [0, 124, 198, 0, 247, 312, 198, 0, 178, 224, 156, 268, 312, 198];
const maxE = Math.max(...earnings14d);

function ViewOverview({ onView }: { onView: (v: string) => void }) {
  return (
    <div className="view">
      <div className="view-header">
        <div>
          <h1 className="view-title">Good morning, Marcus 👋</h1>
          <p className="view-sub">Tuesday, May 5, 2026 · 5 jobs scheduled · $412 expected today</p>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          <button className="btn btn-outline btn-sm">Export</button>
          <button className="btn btn-dark btn-sm">+ New job</button>
        </div>
      </div>

      <div className="stat-grid">
        {kpis.map(k => (
          <div key={k.label} className="stat-card">
            <div className="stat-lbl">{k.label}</div>
            <div className="stat-val">{k.value}</div>
            <span className={`delta ${k.tone}`}>{k.delta}</span>
            <div style={{ fontSize: "12px", color: "#a1a1aa", marginTop: "6px" }}>{k.sub}</div>
          </div>
        ))}
      </div>

      <div className="two-col" style={{ marginBottom: "16px" }}>
        {/* Today's Route */}
        <div className="card">
          <div className="card-head">
            <div>
              <div className="card-head-t">Today&apos;s route</div>
              <div style={{ fontSize: "12px", color: "#a1a1aa" }}>5 stops · 23 miles · ends 7:00 PM</div>
            </div>
            <button className="btn-ghost" onClick={() => onView("route")}>Full route →</button>
          </div>
          <div style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "10px" }}>
            {todayRoute.map(s => (
              <div key={s.id} style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <span style={{
                  width: "22px", height: "22px", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: "11px", fontWeight: 700, flexShrink: 0,
                  background: s.status === "done" ? "#d1fae5" : s.status === "now" ? "#dbeafe" : "#f4f4f5",
                  color: s.status === "done" ? "#059669" : s.status === "now" ? "#2563eb" : "#a1a1aa",
                }}>
                  {s.status === "done" ? "✓" : s.id}
                </span>
                <span style={{ fontSize: "12px", color: "#a1a1aa", minWidth: "56px" }}>{s.time}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: "13px", fontWeight: 600 }}>{s.who}</div>
                  <div style={{ fontSize: "11px", color: "#a1a1aa" }}>{s.svc} · {s.where}</div>
                </div>
                <span className={`pill${s.status === "done" ? " ok" : s.status === "now" ? " info" : ""}`}>
                  {s.status === "done" ? "Done" : s.status === "now" ? "In progress" : `$${s.pay}`}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Incoming */}
        <div className="card">
          <div className="card-head">
            <div>
              <div className="card-head-t">Incoming requests</div>
              <div style={{ fontSize: "12px", color: "#a1a1aa" }}>3 new · respond within 5 min for priority</div>
            </div>
            <button className="btn-ghost" onClick={() => onView("jobs")}>See all</button>
          </div>
          <div style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "12px" }}>
            {jobs.filter(j => j.status === "new").slice(0, 2).map(j => (
              <div key={j.id} style={{ padding: "14px", borderRadius: "10px", border: "1px solid #e4e4e7", background: "#fafafa" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                  <span style={{ fontSize: "13px", fontWeight: 700 }}>{j.svc}</span>
                  <span style={{ fontSize: "15px", fontWeight: 800, color: "#2563eb" }}>${j.pay}</span>
                </div>
                <div style={{ fontSize: "12px", color: "#71717a", marginBottom: "8px" }}>{j.car} · {j.where} · {j.when}</div>
                <div style={{ display: "flex", gap: "8px" }}>
                  <button className="btn btn-dark btn-sm" style={{ flex: 1 }}><Check size={13} /> Accept</button>
                  <button className="btn btn-outline btn-sm"><X size={13} /></button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Earnings chart */}
      <div className="card">
        <div className="card-head">
          <div className="card-head-t">Earnings — last 14 days</div>
          <button className="btn-ghost" onClick={() => onView("earnings")}>Full report →</button>
        </div>
        <div style={{ padding: "20px 24px" }}>
          <div style={{ display: "flex", gap: "3px", alignItems: "flex-end", height: "80px" }}>
            {earnings14d.map((v, i) => (
              <div key={i} style={{
                flex: 1, borderRadius: "3px 3px 0 0",
                height: `${maxE > 0 ? (v / maxE) * 100 : 0}%`,
                background: v === 0 ? "#f4f4f5" : i === earnings14d.length - 1 ? "#2563eb" : "#dbeafe",
                minHeight: v === 0 ? "4px" : "8px",
                transition: "height 0.3s",
              }} />
            ))}
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "#a1a1aa", marginTop: "6px" }}>
            <span>Apr 21</span><span>May 4</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function ViewJobs() {
  const [tab, setTab] = useState<"incoming" | "scheduled" | "history">("incoming");
  return (
    <div className="view">
      <div className="view-header">
        <div>
          <h1 className="view-title">Jobs</h1>
          <p className="view-sub">3 new requests · 2 scheduled this week</p>
        </div>
      </div>
      <div style={{ display: "flex", gap: "4px", marginBottom: "20px" }}>
        {(["incoming", "scheduled", "history"] as const).map(t => (
          <button key={t} onClick={() => setTab(t)} style={{ padding: "7px 14px", borderRadius: "7px", border: "1px solid #e4e4e7", background: tab === t ? "#09090b" : "white", color: tab === t ? "white" : "#71717a", fontSize: "13px", fontWeight: 500, cursor: "pointer", textTransform: "capitalize" }}>{t}</button>
        ))}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        {jobs.filter(j => tab === "incoming" ? j.status === "new" : j.status === "accepted").map(j => (
          <div key={j.id} className="card" style={{ padding: "20px" }}>
            <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "12px" }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                  <span style={{ fontSize: "16px", fontWeight: 700 }}>{j.svc}</span>
                  {j.status === "new" && <span className="pill info">New</span>}
                  {"surge" in j && j.surge && <span className="pill warn">Surge</span>}
                </div>
                <div style={{ fontSize: "13px", color: "#71717a" }}>{j.car} · {j.where}</div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: "24px", fontWeight: 800, letterSpacing: "-0.03em", color: "#2563eb" }}>${j.pay}</div>
                <div style={{ fontSize: "12px", color: "#a1a1aa" }}>{j.id}</div>
              </div>
            </div>
            <div style={{ display: "flex", gap: "16px", fontSize: "13px", color: "#52525b", marginBottom: "14px" }}>
              <span style={{ display: "flex", alignItems: "center", gap: "4px" }}><Calendar size={13} />{j.when}</span>
              <span style={{ display: "flex", alignItems: "center", gap: "4px" }}><MapPin size={13} />{j.where}</span>
              <span>Customer: {j.customer} ★{j.rating}</span>
            </div>
            {j.status === "new" && (
              <div style={{ display: "flex", gap: "8px" }}>
                <button className="btn btn-dark btn-sm"><Check size={13} /> Accept job</button>
                <button className="btn btn-outline btn-sm"><X size={13} /> Decline</button>
              </div>
            )}
          </div>
        ))}
        {jobs.filter(j => tab === "incoming" ? j.status === "new" : j.status === "accepted").length === 0 && (
          <div style={{ textAlign: "center", padding: "48px", color: "#a1a1aa", fontSize: "14px" }}>No {tab} jobs right now.</div>
        )}
      </div>
    </div>
  );
}

function ViewEarnings() {
  return (
    <div className="view">
      <div className="view-header">
        <div>
          <h1 className="view-title">Earnings</h1>
          <p className="view-sub">May 2026 · $8,642 · on track for best month</p>
        </div>
        <button className="btn btn-outline btn-sm">Export CSV</button>
      </div>
      <div className="stat-grid" style={{ gridTemplateColumns: "repeat(4,1fr)" }}>
        {[
          { l: "This week", v: "$2,148", d: "+15%" },
          { l: "This month", v: "$8,642", d: "-4.7%" },
          { l: "Avg ticket", v: "$153", d: "+$7" },
          { l: "Total tips", v: "$386", d: "+$48" },
        ].map(s => (
          <div key={s.l} className="stat-card">
            <div className="stat-lbl">{s.l}</div>
            <div className="stat-val">{s.v}</div>
            <span className={`delta ${s.d.startsWith("+") ? "up" : "down"}`}>{s.d}</span>
          </div>
        ))}
      </div>
      <div className="card">
        <div className="card-head"><div className="card-head-t">Daily earnings — last 14 days</div></div>
        <div style={{ padding: "24px" }}>
          <div style={{ display: "flex", gap: "4px", alignItems: "flex-end", height: "120px" }}>
            {earnings14d.map((v, i) => (
              <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", gap: "2px", alignItems: "center" }}>
                <div style={{ width: "100%", borderRadius: "3px 3px 0 0", height: `${maxE > 0 ? (v / maxE) * 100 : 0}%`, background: v === 0 ? "#f4f4f5" : "#dbeafe", minHeight: "4px" }} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function ViewReviews() {
  return (
    <div className="view">
      <div className="view-header">
        <div>
          <h1 className="view-title">Reviews</h1>
          <p className="view-sub">4.92★ average · 312 reviews</p>
        </div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        {reviews.map(r => (
          <div key={r.name} className="card" style={{ padding: "20px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
              <div>
                <div style={{ fontWeight: 700, marginBottom: "2px" }}>{r.name}</div>
                <div style={{ color: "#f59e0b", fontSize: "14px" }}>{"★".repeat(r.rating)}</div>
              </div>
              <div style={{ fontSize: "12px", color: "#a1a1aa" }}>{r.date}</div>
            </div>
            <div style={{ fontSize: "14px", color: "#52525b", fontStyle: "italic" }}>&ldquo;{r.text}&rdquo;</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ViewProfile() {
  return (
    <div className="view">
      <h1 className="view-title">Profile</h1>
      <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: "24px" }}>
        <div className="card" style={{ padding: "24px", textAlign: "center" }}>
          <div style={{ width: "72px", height: "72px", borderRadius: "50%", background: "#eff6ff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "24px", fontWeight: 800, color: "#2563eb", margin: "0 auto 12px" }}>MT</div>
          <div style={{ fontWeight: 700, fontSize: "18px", marginBottom: "4px" }}>Marcus Tate</div>
          <div style={{ color: "#71717a", fontSize: "13px", marginBottom: "16px" }}>Detailer · L3 Pro · Gold Tier</div>
          <div style={{ display: "flex", justifyContent: "center", gap: "20px", padding: "16px 0", borderTop: "1px solid #f4f4f5", borderBottom: "1px solid #f4f4f5", marginBottom: "16px" }}>
            {[["4.92★", "Rating"], ["312", "Jobs"], ["98%", "On-time"]].map(([n, l]) => (
              <div key={l} style={{ textAlign: "center" }}>
                <div style={{ fontWeight: 800, fontSize: "18px" }}>{n}</div>
                <div style={{ fontSize: "11px", color: "#a1a1aa" }}>{l}</div>
              </div>
            ))}
          </div>
          <button className="btn btn-outline btn-sm btn-block">Edit profile</button>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {[
            { label: "Personal info", fields: [["Full name", "Marcus Tate"], ["Email", "marcus@example.com"], ["Phone", "+1 (260) 555-0147"], ["Member since", "January 2024"]] },
            { label: "Service area", fields: [["Base area", "Fort Wayne, IN"], ["Radius", "8 miles"], ["Zip codes", "46802, 46804, 46808"]] },
          ].map(section => (
            <div key={section.label} className="card">
              <div className="card-head"><div className="card-head-t">{section.label}</div><button className="btn-ghost">Edit</button></div>
              <div style={{ padding: "16px 20px", display: "flex", flexDirection: "column", gap: "12px" }}>
                {section.fields.map(([l, v]) => (
                  <div key={l} style={{ display: "flex", justifyContent: "space-between", fontSize: "14px" }}>
                    <span style={{ color: "#71717a" }}>{l}</span>
                    <span style={{ fontWeight: 500 }}>{v}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function GenericView({ title, sub }: { title: string; sub: string }) {
  return (
    <div className="view">
      <h1 className="view-title">{title}</h1>
      <p className="view-sub" style={{ marginBottom: "32px" }}>{sub}</p>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "80px", color: "#a1a1aa", fontSize: "14px", background: "white", borderRadius: "14px", border: "1px solid #e4e4e7" }}>
        <div style={{ fontSize: "32px", marginBottom: "12px" }}>🚧</div>
        <div style={{ fontWeight: 600, color: "#52525b", marginBottom: "4px" }}>{title} coming soon</div>
        <div>This view is under construction.</div>
      </div>
    </div>
  );
}

const VIEWS: Record<string, React.ComponentType<any>> = {
  overview: ViewOverview,
  jobs: ViewJobs,
  earnings: ViewEarnings,
  reviews: ViewReviews,
  profile: ViewProfile,
};

export default function DetailerDashboard() {
  const [view, setView] = useState("overview");
  const [online, setOnline] = useState(true);

  const Active = VIEWS[view];

  return (
    <div className="dash">
      <DashSidebar view={view} onView={setView} online={online} setOnline={setOnline} />
      <div className="dash-main">
        <DashHeader view={view} online={online} />
        {Active ? (
          <Active onView={setView} />
        ) : (
          <GenericView title={view.charAt(0).toUpperCase() + view.slice(1)} sub="Coming soon" />
        )}
      </div>
    </div>
  );
}
