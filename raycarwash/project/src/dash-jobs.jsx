// Jobs view — list + filters + tabs + table
function ViewJobs() {
  const [tab, setTab] = useS("incoming");
  const [filter, setFilter] = useS("all");

  const tabs = [
    { id: "incoming", label: "Incoming", count: 3 },
    { id: "today",    label: "Today",    count: 5 },
    { id: "upcoming", label: "Upcoming", count: 12 },
    { id: "completed",label: "Completed",count: 312 },
    { id: "canceled", label: "Canceled", count: 4 },
  ];

  // build flat list of all jobs from route + incoming
  const allJobs = [
    ...dashData.route.map((r, i) => ({
      id: `J-${1100 + i}`,
      customer: r.who,
      svc: r.svc,
      where: r.where,
      when: `Today · ${r.time}`,
      pay: r.pay,
      status: r.status === "done" ? "Completed" : r.status === "now" ? "In progress" : "Scheduled",
    })),
    ...dashData.incoming.map(j => ({
      id: j.id, customer: j.customer, svc: j.svc, where: j.where, when: j.when, pay: j.pay,
      status: "Pending",
    })),
    { id: "J-1093", customer: "Tom W.",       svc: "Premium ceramic · M3",   where: "Lakeside · 3.1 mi",  when: "Thu, May 7 · 9:00 AM",  pay: 299, status: "Scheduled" },
    { id: "J-1092", customer: "Kelly P.",     svc: "Full detail · Q3",       where: "Aboite · 4.4 mi",    when: "Thu, May 7 · 2:00 PM",  pay: 149, status: "Scheduled" },
    { id: "J-1088", customer: "M. Ortiz",     svc: "Full detail · CX-5",     where: "Lakeside · 2.8 mi",  when: "Apr 30 · 10:00 AM",     pay: 149, status: "Completed" },
    { id: "J-1085", customer: "Eric L.",      svc: "Express · Sentra",       where: "Waynedale · 6.0 mi", when: "Apr 28 · 4:30 PM",      pay: 49,  status: "Canceled" },
    { id: "J-1084", customer: "Tara V.",      svc: "Interior · Highlander",  where: "Glenwood · 5.2 mi",  when: "Apr 28 · 11:00 AM",     pay: 89,  status: "Completed" },
  ];

  const tabMatch = (j) => {
    if (tab === "incoming") return j.status === "Pending";
    if (tab === "today") return j.when.startsWith("Today");
    if (tab === "upcoming") return j.status === "Scheduled" && !j.when.startsWith("Today");
    if (tab === "completed") return j.status === "Completed";
    if (tab === "canceled") return j.status === "Canceled";
    return true;
  };
  const list = allJobs.filter(tabMatch);

  return (
    <div className="dp">
      <div className="dp-head">
        <div>
          <h1 className="dp-h1">Jobs</h1>
          <div className="dp-sub">Manage incoming requests, today's work, and your job history</div>
        </div>
        <div className="dp-head-actions">
          <button className="btn btn-outline btn-sm"><IconFilter size={14}/> Filters</button>
          <button className="btn btn-outline btn-sm"><IconDownload size={14}/> Export CSV</button>
          <button className="btn btn-dark btn-sm"><IconPlus size={14}/> Manual job</button>
        </div>
      </div>

      <div className="card">
        <div className="card-head" style={{ padding: 0, borderBottom: 0 }}>
          <div style={{ display: "flex", padding: "0 16px", flex: 1, overflow: "auto" }}>
            {tabs.map(t => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className="job-tab"
                style={{
                  padding: "16px 14px",
                  border: 0,
                  background: "transparent",
                  fontSize: 13,
                  fontWeight: 600,
                  color: tab === t.id ? "var(--ink-900)" : "var(--ink-500)",
                  cursor: "pointer",
                  borderBottom: "2px solid " + (tab === t.id ? "var(--ink-900)" : "transparent"),
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  whiteSpace: "nowrap",
                }}
              >
                {t.label}
                <span className={"ds-nav-count " + (tab === t.id ? "" : "")} style={{ marginLeft: 0 }}>
                  {t.count}
                </span>
              </button>
            ))}
          </div>
          <div style={{ paddingRight: 14, display: "flex", gap: 8, alignItems: "center" }}>
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              style={{
                padding: "7px 10px",
                fontSize: 12.5,
                fontFamily: "inherit",
                border: "1px solid var(--ink-150)",
                borderRadius: 8,
                background: "white",
                color: "var(--ink-700)",
                fontWeight: 600,
              }}
            >
              <option value="all">All services</option>
              <option value="ex">Exterior</option>
              <option value="int">Interior</option>
              <option value="full">Full detail</option>
              <option value="cer">Ceramic</option>
            </select>
          </div>
        </div>
        <div className="card-body flush">
          {tab === "incoming" ? (
            <div style={{ padding: 18 }}>
              {dashData.incoming.map(j => <JobReqCard key={j.id} j={j}/>)}
              <div className="empty" style={{ marginTop: 12 }}>
                3 of 3 requests shown. Average response 1.4 min — keep it under 5 to stay priority.
              </div>
            </div>
          ) : (
            <table className="tbl">
              <thead>
                <tr>
                  <th>Job</th>
                  <th>Customer</th>
                  <th>Service</th>
                  <th>Where</th>
                  <th>When</th>
                  <th style={{ textAlign: "right" }}>Pay</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {list.map(j => (
                  <tr key={j.id}>
                    <td className="num m">{j.id}</td>
                    <td className="b">{j.customer}</td>
                    <td>{j.svc}</td>
                    <td className="m">{j.where}</td>
                    <td className="m">{j.when}</td>
                    <td className="num b" style={{ textAlign: "right" }}>${j.pay}</td>
                    <td><Pill kind={
                      j.status === "Completed" ? "ok" :
                      j.status === "In progress" ? "info" :
                      j.status === "Canceled" ? "danger" : "mute"
                    }>{j.status}</Pill></td>
                    <td>
                      <button className="btn-ghost"><IconMore size={16}/></button>
                    </td>
                  </tr>
                ))}
                {list.length === 0 && (
                  <tr><td colSpan={8}><div className="empty">No jobs in this view.</div></td></tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

// Today's route view — focused on the day's stops + nav
function ViewRoute() {
  return (
    <div className="dp">
      <div className="dp-head">
        <div>
          <h1 className="dp-h1">Today's route</h1>
          <div className="dp-sub">Tuesday, May 5 · 5 stops · 23 miles · 7h 30m on the clock</div>
        </div>
        <div className="dp-head-actions">
          <button className="btn btn-outline btn-sm"><IconWaze size={14}/> Waze</button>
          <button className="btn btn-outline btn-sm"><IconPin size={14}/> Apple Maps</button>
          <button className="btn btn-dark btn-sm"><IconRoute size={14}/> Optimize</button>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-head">
            <div className="card-title">Map</div>
            <span className="pill info">Live · ETA 1:08 PM</span>
          </div>
          <div style={{ height: 340 }}>
            <RouteMap />
          </div>
        </div>

        <div className="card">
          <div className="card-head">
            <div className="card-title">Stops</div>
            <button className="btn-ghost"><IconShare size={14}/> Share live ETA</button>
          </div>
          <div className="card-body" style={{ paddingTop: 6 }}>
            <div className="route-stops" style={{ padding: 0 }}>
              {dashData.route.map((s, i) => (
                <div key={s.id} className={"route-stop " + s.status}>
                  <span className={"route-pin " + s.status}>{s.status === "done" ? "✓" : s.id}</span>
                  <span className="route-time">{s.time}</span>
                  <div className="route-info">
                    <div className="nm">{s.who} · ${s.pay}</div>
                    <div className="sv">{s.svc} · {s.where}</div>
                  </div>
                  <Pill kind={s.status === "done" ? "ok" : s.status === "now" ? "info" : "mute"}>
                    {s.status === "done" ? "Done" : s.status === "now" ? "Now" : (i === 3 ? "Next" : "Later")}
                  </Pill>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <div className="card-title">Currently working · Aisha M.</div>
          <div className="dp-head-actions">
            <button className="btn btn-outline btn-sm"><IconPhone size={14}/> Call</button>
            <button className="btn btn-outline btn-sm"><IconMessageSquare size={14}/> Message</button>
            <button className="btn btn-dark btn-sm"><IconCheck size={14}/> Mark complete</button>
          </div>
        </div>
        <div className="card-body">
          <div className="grid-3">
            <div>
              <div className="ps-eyebrow muted">Service</div>
              <div style={{ fontFamily: "Space Grotesk, sans-serif", fontSize: 18, fontWeight: 700, marginTop: 4 }}>
                Interior detail · 2021 Tesla Model Y
              </div>
              <div className="card-sub" style={{ marginTop: 6 }}>
                Add-ons: Pet hair removal
              </div>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 10 }}>
                <Pill kind="info">$119</Pill>
                <Pill kind="mute">90 min</Pill>
                <Pill kind="ok">Paid in app</Pill>
              </div>
            </div>
            <div>
              <div className="ps-eyebrow muted">Location</div>
              <div style={{ fontFamily: "Space Grotesk, sans-serif", fontSize: 18, fontWeight: 700, marginTop: 4 }}>
                412 Glenwood Ave
              </div>
              <div className="card-sub" style={{ marginTop: 6 }}>
                Park in driveway · access water from side spigot
              </div>
              <div style={{ marginTop: 10 }}>
                <button className="btn btn-outline btn-xs"><IconPin size={12}/> Navigate</button>
              </div>
            </div>
            <div>
              <div className="ps-eyebrow muted">Progress</div>
              <div style={{ fontFamily: "Space Grotesk, sans-serif", fontSize: 18, fontWeight: 700, marginTop: 4 }}>
                42% complete · ~35m left
              </div>
              <div className="ps-prog-bar" style={{ marginTop: 8 }}>
                <div className="ps-prog-fill" style={{ width: "42%" }}></div>
              </div>
              <div className="card-sub" style={{ marginTop: 6 }}>
                Started 1:12 PM
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

window.ViewJobs = ViewJobs;
window.ViewRoute = ViewRoute;
