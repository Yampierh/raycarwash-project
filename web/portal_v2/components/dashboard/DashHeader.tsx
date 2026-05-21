"use client";
import { useState, useRef, useEffect } from "react";
import { Search, Bell, MessageSquare, RefreshCw, Plus, Check, AlertTriangle } from "lucide-react";

const NAV_TITLES: Record<string, string> = {
  overview: "Overview", jobs: "Jobs", schedule: "Schedule", route: "Today's route",
  earnings: "Earnings", customers: "Customers", reviews: "Reviews",
  services: "Services & pricing", supplies: "Supplies", profile: "Profile",
  settings: "Settings", help: "Help",
};

const notifs = [
  { id: 1, kind: "brand", t: "New job request", b: "Full detail · Honda Pilot · $179", m: "2 min ago", unread: true },
  { id: 2, kind: "ok", t: "Payment received", b: "Job #JR-1038 · $149 deposited", m: "1hr ago", unread: true },
  { id: 3, kind: "warn", t: "Reminder", b: "Job #JR-1040 starts in 30 minutes", m: "30 min ago", unread: false },
];

interface Props { view: string; online: boolean; }

export default function DashHeader({ view, online }: Props) {
  const [notifOpen, setNotifOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const unread = notifs.filter(n => n.unread).length;

  useEffect(() => {
    if (!notifOpen) return;
    const fn = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setNotifOpen(false);
    };
    document.addEventListener("mousedown", fn);
    return () => document.removeEventListener("mousedown", fn);
  }, [notifOpen]);

  return (
    <header className="dh">
      <div>
        <div className="dh-crumb">
          <span>Workspace</span>
          <span className="sep">›</span>
          <span style={{ color: "var(--ink-700)", fontWeight: 600 }}>{NAV_TITLES[view] || "Overview"}</span>
        </div>
      </div>

      <div className="dh-search">
        <Search size={15} className="dh-search-ic" />
        <input placeholder="Search jobs, customers, invoices…" />
        <span className="dh-kbd">⌘K</span>
      </div>

      <div className="dh-actions">
        <button className="dh-icon-btn" title="Refresh"><RefreshCw size={17} /></button>
        <button className="dh-icon-btn" title="Messages">
          <MessageSquare size={17} />
          <span className="badge">2</span>
        </button>
        <div style={{ position: "relative" }} ref={wrapRef}>
          <button className="dh-icon-btn" title="Notifications" onClick={() => setNotifOpen(o => !o)}>
            <Bell size={17} />
            {unread > 0 && <span className="badge">{unread}</span>}
          </button>
          {notifOpen && (
            <div className="notif" role="dialog">
              <div className="notif-head">
                <span className="t">Notifications</span>
                <button className="btn-ghost" onClick={() => setNotifOpen(false)}>Mark all read</button>
              </div>
              <div className="notif-list">
                {notifs.map(n => (
                  <div key={n.id} className={`notif-item${n.unread ? " unread" : ""}`}>
                    <span className={`notif-ic-wrap ${n.kind}`}>
                      {n.kind === "ok" ? <Check size={15} /> : n.kind === "warn" ? <AlertTriangle size={15} /> : <Bell size={15} />}
                    </span>
                    <div className="notif-body">
                      <div className="t">{n.t}</div>
                      <div className="b">{n.b}</div>
                      <div className="m">{n.m}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
        <div className="dh-divider" />
        <button className="btn btn-dark btn-sm"><Plus size={14} /> New job</button>
      </div>
    </header>
  );
}
