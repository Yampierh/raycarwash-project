"use client";
import { useState } from "react";
import Link from "next/link";
import { Home, Car, Calendar, User, Plus, ArrowRight, MapPin, Clock, Star, ChevronRight } from "lucide-react";

const tabs = [
  { id: "home", label: "Home", icon: Home },
  { id: "appointments", label: "Appointments", icon: Calendar },
  { id: "garage", label: "My Garage", icon: Car },
  { id: "profile", label: "Profile", icon: User },
];

const appointments = [
  { id: "A-2041", svc: "Full detail", car: "2020 Toyota Camry", date: "May 8, 2026", time: "10:00 AM", detailer: "Marcus T.", rating: 4.9, status: "upcoming", price: 149 },
  { id: "A-2040", svc: "Exterior wash", car: "2018 Honda Civic", date: "May 1, 2026", time: "2:00 PM", detailer: "Trey W.", rating: 4.8, status: "completed", price: 49 },
  { id: "A-2039", svc: "Interior detail", car: "2020 Toyota Camry", date: "Apr 22, 2026", time: "11:30 AM", detailer: "Jamal R.", rating: 5.0, status: "completed", price: 89 },
];

const vehicles = [
  { id: "V1", year: 2020, make: "Toyota", model: "Camry", color: "Silver", plate: "FW·4823", services: 7, lastVisit: "May 1" },
  { id: "V2", year: 2018, make: "Honda", model: "Civic", color: "Blue", plate: "FW·1104", services: 3, lastVisit: "Apr 22" },
];

function StatusPill({ status }: { status: string }) {
  const styles: Record<string, { bg: string; color: string }> = {
    upcoming: { bg: "#dbeafe", color: "#1e3a8a" },
    completed: { bg: "#d1fae5", color: "#065f46" },
    cancelled: { bg: "#fee2e2", color: "#991b1b" },
  };
  const s = styles[status] || { bg: "#f4f4f5", color: "#52525b" };
  return <span style={{ padding: "3px 8px", borderRadius: "5px", fontSize: "11px", fontWeight: 600, background: s.bg, color: s.color, textTransform: "capitalize" }}>{status}</span>;
}

function HomeTab() {
  const next = appointments.find(a => a.status === "upcoming");
  return (
    <div style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Next booking */}
      {next && (
        <div className="next-booking-card">
          <div className="nbc-label">Next appointment</div>
          <div className="nbc-service">{next.svc}</div>
          <div className="nbc-meta">{next.car} · {next.date} at {next.time}</div>
          <div className="nbc-detailer">
            <div className="nbc-avatar">{next.detailer.split(" ").map(w => w[0]).join("")}</div>
            <div>
              <div className="nbc-dname">{next.detailer}</div>
              <div className="nbc-drating">★ {next.rating} · Verified pro</div>
            </div>
            <button style={{ marginLeft: "auto", background: "rgba(255,255,255,0.15)", border: "none", borderRadius: "7px", padding: "6px 12px", color: "white", fontSize: "12px", fontWeight: 600, cursor: "pointer" }}>Track</button>
          </div>
        </div>
      )}

      {/* Quick actions */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
        {[
          { label: "Book a detail", icon: "✨", desc: "Schedule your next clean", href: "/book", primary: true },
          { label: "My vehicles", icon: "🚗", desc: `${vehicles.length} vehicle${vehicles.length !== 1 ? "s" : ""} saved` },
          { label: "Appointments", icon: "📅", desc: `${appointments.length} total` },
          { label: "Favorites", icon: "⭐", desc: "2 saved detailers" },
        ].map(a => (
          <div key={a.label} style={{ padding: "18px", borderRadius: "12px", background: a.primary ? "var(--brand)" : "white", border: "1px solid", borderColor: a.primary ? "var(--brand)" : "#e4e4e7", cursor: "pointer" }}>
            <div style={{ fontSize: "20px", marginBottom: "6px" }}>{a.icon}</div>
            <div style={{ fontWeight: 700, fontSize: "14px", color: a.primary ? "white" : "#09090b" }}>{a.label}</div>
            <div style={{ fontSize: "12px", color: a.primary ? "rgba(255,255,255,0.7)" : "#a1a1aa" }}>{a.desc}</div>
          </div>
        ))}
      </div>

      {/* Recent */}
      <div style={{ background: "white", borderRadius: "12px", border: "1px solid #e4e4e7", overflow: "hidden" }}>
        <div style={{ padding: "14px 16px", borderBottom: "1px solid #f4f4f5", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ fontSize: "14px", fontWeight: 600 }}>Recent appointments</div>
          <button style={{ fontSize: "12px", color: "#2563eb", background: "none", border: "none", cursor: "pointer" }}>See all →</button>
        </div>
        {appointments.slice(0, 2).map(a => (
          <div key={a.id} style={{ display: "flex", alignItems: "center", gap: "12px", padding: "12px 16px", borderBottom: "1px solid #fafafa" }}>
            <div style={{ width: "36px", height: "36px", borderRadius: "8px", background: "#eff6ff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "16px" }}>✨</div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: "13px", fontWeight: 600 }}>{a.svc}</div>
              <div style={{ fontSize: "11px", color: "#a1a1aa" }}>{a.car} · {a.date}</div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: "13px", fontWeight: 700 }}>${a.price}</div>
              <StatusPill status={a.status} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function AppointmentsTab() {
  return (
    <div style={{ padding: "24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <h2 style={{ fontSize: "18px", fontWeight: 700, margin: 0 }}>My Appointments</h2>
        <button className="btn btn-dark btn-sm"><Plus size={14} /> Book new</button>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        {appointments.map(a => (
          <div key={a.id} style={{ background: "white", border: "1px solid #e4e4e7", borderRadius: "12px", padding: "18px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "10px" }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: "16px", marginBottom: "2px" }}>{a.svc}</div>
                <div style={{ fontSize: "13px", color: "#71717a" }}>{a.car}</div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: "18px", fontWeight: 800 }}>${a.price}</div>
                <StatusPill status={a.status} />
              </div>
            </div>
            <div style={{ display: "flex", gap: "16px", fontSize: "13px", color: "#52525b", marginBottom: "12px", flexWrap: "wrap" }}>
              <span style={{ display: "flex", alignItems: "center", gap: "4px" }}><Calendar size={13} />{a.date} at {a.time}</span>
              <span>Detailer: {a.detailer} ★{a.rating}</span>
            </div>
            {a.status === "completed" && (
              <div style={{ display: "flex", gap: "8px" }}>
                <button className="btn btn-outline btn-sm">View receipt</button>
                <button className="btn btn-outline btn-sm">Book again</button>
              </div>
            )}
            {a.status === "upcoming" && (
              <div style={{ display: "flex", gap: "8px" }}>
                <button className="btn btn-dark btn-sm">Track live</button>
                <button className="btn btn-outline btn-sm">Cancel</button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function GarageTab() {
  return (
    <div style={{ padding: "24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <h2 style={{ fontSize: "18px", fontWeight: 700, margin: 0 }}>My Garage</h2>
        <button className="btn btn-dark btn-sm"><Plus size={14} /> Add vehicle</button>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: "16px" }}>
        {vehicles.map(v => (
          <div key={v.id} className="vehicle-card">
            <div className="veh-img">🚗</div>
            <div className="veh-info">
              <div className="veh-name">{v.year} {v.make} {v.model}</div>
              <div className="veh-meta">{v.color} · {v.plate}</div>
              <div className="veh-stats">
                <div className="veh-stat"><div className="veh-stat-n">{v.services}</div><div className="veh-stat-l">Services</div></div>
                <div className="veh-stat"><div className="veh-stat-n">{v.lastVisit}</div><div className="veh-stat-l">Last visit</div></div>
              </div>
            </div>
          </div>
        ))}
        <div style={{ border: "2px dashed #e4e4e7", borderRadius: "12px", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "8px", padding: "32px", cursor: "pointer", minHeight: "180px" }}>
          <div style={{ width: "36px", height: "36px", borderRadius: "50%", background: "#f4f4f5", display: "flex", alignItems: "center", justifyContent: "center" }}><Plus size={18} color="#a1a1aa" /></div>
          <div style={{ fontSize: "13px", fontWeight: 600, color: "#52525b" }}>Add vehicle</div>
          <div style={{ fontSize: "12px", color: "#a1a1aa" }}>VIN lookup supported</div>
        </div>
      </div>
    </div>
  );
}

function ProfileTab() {
  return (
    <div style={{ padding: "24px" }}>
      <h2 style={{ fontSize: "18px", fontWeight: 700, margin: "0 0 20px" }}>My Profile</h2>
      <div style={{ maxWidth: "480px", display: "flex", flexDirection: "column", gap: "16px" }}>
        <div style={{ background: "white", border: "1px solid #e4e4e7", borderRadius: "12px", padding: "24px", display: "flex", alignItems: "center", gap: "16px" }}>
          <div style={{ width: "56px", height: "56px", borderRadius: "50%", background: "#eff6ff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "20px", fontWeight: 800, color: "#2563eb", flexShrink: 0 }}>SM</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700, fontSize: "17px" }}>Sarah M.</div>
            <div style={{ fontSize: "13px", color: "#71717a" }}>sarah@example.com</div>
          </div>
          <button className="btn btn-outline btn-sm">Edit</button>
        </div>
        {[
          { label: "Personal info", items: [["Full name", "Sarah Martinez"], ["Email", "sarah@example.com"], ["Phone", "+1 (260) 555-0198"]] },
          { label: "Saved addresses", items: [["Home", "1234 Maple Ave, Fort Wayne IN"], ["Work", "567 Jefferson St, Fort Wayne IN"]] },
          { label: "Payment method", items: [["Card on file", "Visa ending in 4242"], ["Billing zip", "46802"]] },
        ].map(section => (
          <div key={section.label} style={{ background: "white", border: "1px solid #e4e4e7", borderRadius: "12px", overflow: "hidden" }}>
            <div style={{ padding: "12px 16px", borderBottom: "1px solid #f4f4f5", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ fontSize: "14px", fontWeight: 600 }}>{section.label}</div>
              <button style={{ fontSize: "12px", color: "#2563eb", background: "none", border: "none", cursor: "pointer" }}>Edit</button>
            </div>
            {section.items.map(([l, v]) => (
              <div key={l} style={{ display: "flex", justifyContent: "space-between", padding: "10px 16px", fontSize: "14px", borderBottom: "1px solid #fafafa" }}>
                <span style={{ color: "#71717a" }}>{l}</span>
                <span style={{ fontWeight: 500 }}>{v}</span>
              </div>
            ))}
          </div>
        ))}
        <button className="btn btn-outline btn-block" style={{ color: "#ef4444", borderColor: "#fecaca" }}>Sign out</button>
      </div>
    </div>
  );
}

const TAB_VIEWS: Record<string, React.ComponentType> = {
  home: HomeTab,
  appointments: AppointmentsTab,
  garage: GarageTab,
  profile: ProfileTab,
};

export default function ClientDashboard() {
  const [activeTab, setActiveTab] = useState("home");
  const Active = TAB_VIEWS[activeTab];

  return (
    <div style={{ minHeight: "100vh", background: "#f4f4f5" }}>
      {/* Top bar */}
      <header style={{ background: "white", borderBottom: "1px solid #e4e4e7", position: "sticky", top: 0, zIndex: 10 }}>
        <div style={{ maxWidth: "800px", margin: "0 auto", padding: "0 20px", display: "flex", alignItems: "center", justifyContent: "space-between", height: "56px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ width: "26px", height: "26px", borderRadius: "7px", background: "#09090b", color: "white", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: "14px" }}>R</span>
            <span style={{ fontWeight: 700, fontSize: "15px" }}>RayCarWash</span>
          </div>
          <button className="btn btn-dark btn-sm"><Plus size={14} /> Book now</button>
        </div>
        <div style={{ maxWidth: "800px", margin: "0 auto", padding: "0 20px" }}>
          <div style={{ display: "flex", borderBottom: "none" }}>
            {tabs.map(t => {
              const Ico = t.icon;
              return (
                <button
                  key={t.id}
                  onClick={() => setActiveTab(t.id)}
                  style={{
                    display: "flex", alignItems: "center", gap: "6px", padding: "10px 14px",
                    color: activeTab === t.id ? "var(--brand)" : "#71717a",
                    fontWeight: activeTab === t.id ? 600 : 400, fontSize: "13px",
                    background: "none", border: "none",
                    borderBottom: `2px solid ${activeTab === t.id ? "var(--brand)" : "transparent"}`,
                    cursor: "pointer", transition: "all 0.15s",
                  }}
                >
                  <Ico size={15} />
                  {t.label}
                </button>
              );
            })}
          </div>
        </div>
      </header>

      <div style={{ maxWidth: "800px", margin: "0 auto" }}>
        <Active />
      </div>
    </div>
  );
}
