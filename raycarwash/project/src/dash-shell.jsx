// Provider Dashboard — app shell (sidebar + header + nav)
const { useState: useS, useEffect: useE, useMemo: useM, useRef: useR } = React;

const NAV_GROUPS = [
  {
    label: "Workspace",
    items: [
      { id: "overview",  label: "Overview",   icon: IconDash },
      { id: "jobs",      label: "Jobs",       icon: IconBriefcase, count: 3, countBrand: true },
      { id: "schedule",  label: "Schedule",   icon: IconCalendar },
      { id: "route",     label: "Today's route", icon: IconRoute },
    ],
  },
  {
    label: "Business",
    items: [
      { id: "earnings",  label: "Earnings",   icon: IconWallet },
      { id: "customers", label: "Customers",  icon: IconUsers, count: 142 },
      { id: "reviews",   label: "Reviews",    icon: IconStar, count: 2 },
      { id: "services",  label: "Services & pricing", icon: IconTag },
      { id: "supplies",  label: "Supplies",   icon: IconShoppingBag },
    ],
  },
  {
    label: "Account",
    items: [
      { id: "profile",   label: "Profile",    icon: IconUserCheck },
      { id: "settings",  label: "Settings",   icon: IconSettings },
      { id: "help",      label: "Help",       icon: IconHelp },
    ],
  },
];

const NAV_TITLES = {
  overview: "Overview",
  jobs: "Jobs",
  schedule: "Schedule",
  route: "Today's route",
  earnings: "Earnings",
  customers: "Customers",
  reviews: "Reviews",
  services: "Services & pricing",
  supplies: "Supplies",
  profile: "Profile",
  settings: "Settings",
  help: "Help",
};

function DashSidebar({ view, onView, online, setOnline }) {
  return (
    <aside className="dash-sidebar">
      <div className="ds-brand">
        <span className="ds-brand-mark">R</span>
        <div>
          <div className="ds-brand-name">RayCarWash</div>
          <div className="ds-brand-sub">Provider</div>
        </div>
      </div>

      {NAV_GROUPS.map((g) => (
        <React.Fragment key={g.label}>
          <div className="ds-section-label">{g.label}</div>
          {g.items.map((it) => {
            const Ico = it.icon;
            return (
              <button
                key={it.id}
                className={"ds-nav-btn " + (view === it.id ? "on" : "")}
                onClick={() => onView(it.id)}
              >
                <Ico size={17} className="ic" />
                <span>{it.label}</span>
                {it.count != null && (
                  <span className={"ds-nav-count " + (it.countBrand ? "brand" : "")}>
                    {it.count}
                  </span>
                )}
              </button>
            );
          })}
        </React.Fragment>
      ))}

      <div className="ds-foot">
        <div className="ds-status">
          <span className={"ds-status-dot " + (online ? "" : "off")}></span>
          <div className="ds-status-text">
            <span className="b">{online ? "Accepting jobs" : "Paused"}</span>
            <span className="m">{online ? "Within 8 mi" : "Not visible to riders"}</span>
          </div>
          <button
            className={"ds-switch " + (online ? "" : "off")}
            onClick={() => setOnline(!online)}
            aria-label="Toggle availability"
          ></button>
        </div>
        <div className="ds-user">
          <div className="ds-avatar">{dashData.me.initials}</div>
          <div className="ds-user-text">
            <div className="ds-user-name">{dashData.me.name}</div>
            <div className="ds-user-role">{dashData.me.role}</div>
          </div>
          <IconChevronDown size={14} style={{ color: "var(--ink-400)" }} />
        </div>
      </div>
    </aside>
  );
}

function DashHeader({ view, online }) {
  const [notifOpen, setNotifOpen] = useS(false);
  const wrapRef = useR(null);

  useE(() => {
    if (!notifOpen) return;
    const onClick = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setNotifOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [notifOpen]);

  const unread = dashData.notifs.filter(n => n.unread).length;

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
        <IconSearch size={15} className="dh-search-ic" />
        <input placeholder="Search jobs, customers, invoices…" />
        <span className="dh-kbd">⌘K</span>
      </div>

      <div className="dh-actions">
        <button className="dh-icon-btn" title="Refresh"><IconRefresh size={17} /></button>
        <button className="dh-icon-btn" title="Messages">
          <IconMessageSquare size={17} />
          <span className="badge">2</span>
        </button>
        <div style={{ position: "relative" }} ref={wrapRef}>
          <button
            className="dh-icon-btn"
            title="Notifications"
            onClick={() => setNotifOpen(o => !o)}
          >
            <IconBell size={17} />
            {unread > 0 && <span className="badge">{unread}</span>}
          </button>
          {notifOpen && <NotifPopover onClose={() => setNotifOpen(false)} />}
        </div>
        <div className="dh-divider"></div>
        <button className="btn btn-dark btn-sm">
          <IconPlus size={14} /> New job
        </button>
      </div>
    </header>
  );
}

function NotifPopover({ onClose }) {
  const iconMap = {
    brand: <IconBell size={15} />,
    ok: <IconCheck size={15} />,
    warn: <IconAlertTriangle size={15} />,
  };
  return (
    <div className="notif" role="dialog">
      <div className="notif-head">
        <span className="t">Notifications</span>
        <button className="btn-ghost" onClick={onClose}>Mark all read</button>
      </div>
      <div className="notif-list">
        {dashData.notifs.map((n) => (
          <div key={n.id} className={"notif-item " + (n.unread ? "unread" : "")}>
            <span className={"notif-ic-wrap " + n.kind}>{iconMap[n.kind] || <IconBell size={15} />}</span>
            <div className="notif-body">
              <div className="t">{n.t}</div>
              <div className="b">{n.b}</div>
              <div className="m">{n.m}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Small reusable bits used by views
function Pill({ children, kind = "" }) {
  return <span className={"pill " + kind}>{children}</span>;
}
function Delta({ v, suffix = "%" }) {
  if (v == null) return null;
  if (v === 0) return <span className="delta flat">±0{suffix}</span>;
  const up = v > 0;
  return (
    <span className={"delta " + (up ? "up" : "down")}>
      {up ? "▲" : "▼"} {Math.abs(v)}{suffix}
    </span>
  );
}
function fmtMoney(n, cents = false) {
  if (cents) return "$" + n.toFixed(2);
  return "$" + Math.round(n).toLocaleString();
}

window.DashSidebar = DashSidebar;
window.DashHeader = DashHeader;
window.NAV_TITLES = NAV_TITLES;
window.Pill = Pill;
window.Delta = Delta;
window.fmtMoney = fmtMoney;
