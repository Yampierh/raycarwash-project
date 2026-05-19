// Schedule view — week grid with events
function ViewSchedule() {
  const [view, setView] = useS("week");
  const days = ["Tue 5", "Wed 6", "Thu 7", "Fri 8", "Sat 9", "Sun 10", "Mon 11"];
  const hours = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18];
  const events = dashData.schedule;

  return (
    <div className="dp">
      <div className="dp-head">
        <div>
          <h1 className="dp-h1">Schedule</h1>
          <div className="dp-sub">Manage availability, block time off, and view bookings</div>
        </div>
        <div className="dp-head-actions">
          <div className="seg">
            <button>Day</button>
            <button className="on">Week</button>
            <button>Month</button>
          </div>
          <button className="btn btn-outline btn-sm"><IconChevronLeft size={14}/></button>
          <button className="btn btn-outline btn-sm">Today</button>
          <button className="btn btn-outline btn-sm"><IconChevronRight size={14}/></button>
          <button className="btn btn-dark btn-sm"><IconPlus size={14}/> Block time</button>
        </div>
      </div>

      <div className="kpi-grid">
        <KpiCard label="Booked this week" value="18 jobs" delta={12} icon={<IconBriefcase size={14}/>} iconTone="brand" foot="62% slot fill rate"/>
        <KpiCard label="Available slots" value={11} icon={<IconClock size={14}/>} foot="Across 6 days"/>
        <KpiCard label="Off / blocked" value="1 day" icon={<IconCalendar size={14}/>} foot="Thursday — family"/>
        <KpiCard label="Forecast revenue" value={fmtMoney(2640)} delta={8} icon={<IconWallet size={14}/>} iconTone="ok" foot="If 80% slots fill"/>
      </div>

      <div className="card">
        <div className="card-head">
          <div className="card-title">May 5 – May 11, 2026</div>
          <div className="dp-head-actions">
            <div className="chart-legend" style={{ paddingTop: 0 }}>
              <span><span className="sw"></span> Booked</span>
              <span><span className="sw" style={{ background: "var(--ok)" }}></span> Confirmed</span>
              <span><span className="sw" style={{ background: "var(--warn)" }}></span> Tentative</span>
              <span><span className="sw" style={{ background: "white", border: "1px dashed var(--ink-300)" }}></span> Available</span>
            </div>
          </div>
        </div>
        <div className="card-body flush" style={{ overflowX: "auto" }}>
          <div className="sched-week" style={{ borderRadius: 0, border: 0 }}>
            <div className="sw-head"></div>
            {days.map((d, i) => (
              <div key={d} className={"sw-head " + (i === 0 ? "today" : "")}>
                <div>{d.split(" ")[0]}</div>
                <span className="num">{d.split(" ")[1]}</span>
              </div>
            ))}
            {hours.map((h) => (
              <React.Fragment key={h}>
                <div className="sw-time">{h > 12 ? h - 12 : h}{h >= 12 ? "p" : "a"}</div>
                {days.map((d, di) => (
                  <div key={di} className={"sw-cell " + (di === 0 && h === 13 ? "now" : "")} style={{ position: "relative" }}>
                    {events.filter(e => e.day === di && Math.floor(e.start) === h).map((e, idx) => {
                      const top = (e.start - h) * 48;
                      const height = (e.end - e.start) * 48 - 2;
                      return (
                        <div
                          key={idx}
                          className={"sw-event " + e.type}
                          style={{
                            top: top + "px",
                            height: height + "px",
                          }}
                        >
                          <div className="t">{Math.floor(e.start) > 12 ? Math.floor(e.start)-12 : Math.floor(e.start)}:{((e.start % 1) * 60).toString().padStart(2,"0")} · {e.label}</div>
                          <div className="s">{e.svc}</div>
                        </div>
                      );
                    })}
                  </div>
                ))}
              </React.Fragment>
            ))}
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-head">
            <div className="card-title">Working hours</div>
            <button className="btn-ghost">Edit</button>
          </div>
          <div className="card-body">
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {[
                ["Monday", "8:00 AM – 6:00 PM", true],
                ["Tuesday", "8:00 AM – 7:00 PM", true],
                ["Wednesday", "8:00 AM – 6:00 PM", true],
                ["Thursday", "Off", false],
                ["Friday", "8:00 AM – 6:00 PM", true],
                ["Saturday", "9:00 AM – 5:00 PM", true],
                ["Sunday", "Off", false],
              ].map(([d, h, on]) => (
                <div key={d} style={{ display: "flex", alignItems: "center", padding: "8px 12px", border: "1px solid var(--ink-100)", borderRadius: 8 }}>
                  <span style={{ fontWeight: 600, color: "var(--ink-900)", width: 100 }}>{d}</span>
                  <span style={{ flex: 1, color: on ? "var(--ink-700)" : "var(--ink-400)" }}>{h}</span>
                  <button className={"toggle " + (on ? "on" : "")}></button>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-head">
            <div className="card-title">Service zones</div>
            <button className="btn-ghost">Edit zones</button>
          </div>
          <div className="card-body">
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {[
                ["Aboite Township", "10 mi radius · primary", "ok"],
                ["Lakeside", "Within 5 mi · primary", "ok"],
                ["Northwood / Pine Valley", "Within 8 mi", "info"],
                ["Glenwood / Waynedale", "Within 12 mi", "info"],
                ["New Haven", "Surcharge +$15", "warn"],
                ["Huntertown", "Not serviced", "mute"],
              ].map(([n, m, k]) => (
                <div key={n} style={{ display: "flex", alignItems: "center", padding: "10px 12px", border: "1px solid var(--ink-100)", borderRadius: 8 }}>
                  <IconPin size={14} style={{ color: "var(--ink-500)", marginRight: 10 }}/>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, color: "var(--ink-900)", fontSize: 13 }}>{n}</div>
                    <div className="card-sub" style={{ marginTop: 0 }}>{m}</div>
                  </div>
                  <Pill kind={k}>{k === "ok" ? "Active" : k === "warn" ? "Surcharge" : k === "mute" ? "Off" : "Active"}</Pill>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

window.ViewSchedule = ViewSchedule;
