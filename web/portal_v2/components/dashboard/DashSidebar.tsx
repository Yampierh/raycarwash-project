"use client";
import { LayoutDashboard, Briefcase, Calendar, Route, Wallet, Users, Star, Tag, ShoppingBag, UserCheck, Settings, HelpCircle, ChevronDown } from "lucide-react";

const NAV_GROUPS = [
  {
    label: "Workspace",
    items: [
      { id: "overview", label: "Overview", icon: LayoutDashboard },
      { id: "jobs", label: "Jobs", icon: Briefcase, count: 3, brand: true },
      { id: "schedule", label: "Schedule", icon: Calendar },
      { id: "route", label: "Today's route", icon: Route },
    ],
  },
  {
    label: "Business",
    items: [
      { id: "earnings", label: "Earnings", icon: Wallet },
      { id: "customers", label: "Customers", icon: Users, count: 142 },
      { id: "reviews", label: "Reviews", icon: Star, count: 2 },
      { id: "services", label: "Services & pricing", icon: Tag },
      { id: "supplies", label: "Supplies", icon: ShoppingBag },
    ],
  },
  {
    label: "Account",
    items: [
      { id: "profile", label: "Profile", icon: UserCheck },
      { id: "settings", label: "Settings", icon: Settings },
      { id: "help", label: "Help", icon: HelpCircle },
    ],
  },
];

interface Props {
  view: string;
  onView: (v: string) => void;
  online: boolean;
  setOnline: (b: boolean) => void;
}

export default function DashSidebar({ view, onView, online, setOnline }: Props) {
  return (
    <aside className="dash-sidebar">
      <div className="ds-brand">
        <span className="ds-brand-mark">R</span>
        <div>
          <div className="ds-brand-name">RayCarWash</div>
          <div className="ds-brand-sub">Provider</div>
        </div>
      </div>

      {NAV_GROUPS.map(g => (
        <div key={g.label}>
          <div className="ds-section-label">{g.label}</div>
          {g.items.map(it => {
            const Ico = it.icon;
            return (
              <button
                key={it.id}
                className={`ds-nav-btn${view === it.id ? " on" : ""}`}
                onClick={() => onView(it.id)}
              >
                <Ico size={17} className="ic" />
                <span>{it.label}</span>
                {"count" in it && it.count != null && (
                  <span className={`ds-nav-count${"brand" in it && it.brand ? " brand" : ""}`}>{it.count}</span>
                )}
              </button>
            );
          })}
        </div>
      ))}

      <div className="ds-foot">
        <div className="ds-status">
          <span className={`ds-status-dot${online ? "" : " off"}`} />
          <div className="ds-status-text">
            <span className="b">{online ? "Accepting jobs" : "Paused"}</span>
            <span className="m">{online ? "Within 8 mi" : "Not visible to riders"}</span>
          </div>
          <button
            className={`ds-switch${online ? "" : " off"}`}
            onClick={() => setOnline(!online)}
            aria-label="Toggle availability"
          />
        </div>
        <div className="ds-user">
          <div className="ds-avatar">MT</div>
          <div className="ds-user-text">
            <div className="ds-user-name">Marcus Tate</div>
            <div className="ds-user-role">Detailer · L3 Pro</div>
          </div>
          <ChevronDown size={14} style={{ color: "var(--ink-400)" }} />
        </div>
      </div>
    </aside>
  );
}
