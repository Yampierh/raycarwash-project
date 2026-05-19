// Reviews view
function ViewReviews() {
  const [replyOpen, setReplyOpen] = useS(null);
  const [draft, setDraft] = useS("");

  const dist = [
    { s: 5, n: 312 },
    { s: 4, n: 28 },
    { s: 3, n: 6 },
    { s: 2, n: 1 },
    { s: 1, n: 1 },
  ];
  const total = dist.reduce((a, d) => a + d.n, 0);

  return (
    <div className="dp">
      <div className="dp-head">
        <div>
          <h1 className="dp-h1">Reviews</h1>
          <div className="dp-sub">348 reviews · respond within 24h to boost ranking</div>
        </div>
        <div className="dp-head-actions">
          <button className="btn btn-outline btn-sm"><IconShare size={14}/> Share profile link</button>
          <button className="btn btn-outline btn-sm"><IconDownload size={14}/> Export</button>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-body">
            <div className="rv-summary">
              <div>
                <div className="rv-big">4.92</div>
                <div className="rv-stars">★★★★★</div>
                <div className="rv-count">{total} reviews · all time</div>
                <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 6 }}>
                  <Pill kind="ok">↑ 0.04 vs last month</Pill>
                  <Pill kind="info">Top 8% in Fort Wayne</Pill>
                </div>
              </div>
              <div className="rv-dist">
                {dist.map(d => (
                  <div className="rv-dist-row" key={d.s}>
                    <span>{d.s}★</span>
                    <div className="rv-bar"><div style={{ width: `${d.n/total*100}%` }}></div></div>
                    <span style={{ textAlign: "right", color: "var(--ink-500)" }}>{d.n}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-head">
            <div className="card-title">Highlights</div>
            <span className="pill mute">Auto-tagged</span>
          </div>
          <div className="card-body">
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {[
                ["On time", 142, "ok"],
                ["Professional", 98, "ok"],
                ["Worth the price", 76, "ok"],
                ["Great communication", 64, "ok"],
                ["Thorough", 52, "ok"],
                ["Streaks (minor)", 4, "warn"],
                ["Late arrival", 2, "warn"],
              ].map(([t, n, k]) => (
                <span key={t} className={"pill " + k} style={{ padding: "5px 10px", fontSize: 12 }}>
                  {t} · {n}
                </span>
              ))}
            </div>
            <div style={{ marginTop: 16, paddingTop: 14, borderTop: "1px solid var(--ink-100)", fontSize: 13, color: "var(--ink-600)", lineHeight: 1.55 }}>
              <strong style={{ color: "var(--ink-900)" }}>AI summary:</strong> Customers consistently
              praise punctuality, attention to detail, and clear communication. A small
              number have mentioned occasional streaks on rear windows — consider an
              extra pass with the streak-free glass towel.
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <div className="card-title">All reviews</div>
          <div className="dp-head-actions">
            <div className="seg">
              <button className="on">All</button>
              <button>Needs reply</button>
              <button>5★</button>
              <button>≤3★</button>
            </div>
          </div>
        </div>
        <div className="card-body flush">
          {dashData.reviews.map((r) => (
            <div className="rv-item" key={r.id}>
              <div className="rv-item-head">
                <span className="rv-item-stars">{"★".repeat(r.stars)}{"☆".repeat(5-r.stars)}</span>
                <span className="rv-item-name">{r.name}</span>
                {!r.reply && <Pill kind="warn">Needs reply</Pill>}
                <span className="rv-item-meta">{r.svc} · {r.when}</span>
              </div>
              <div className="rv-item-body">{r.body}</div>
              {r.reply && (
                <div className="rv-reply">
                  <span className="b">Your reply</span>
                  {r.reply}
                </div>
              )}
              {replyOpen === r.id ? (
                <div style={{ marginTop: 10, padding: 12, border: "1px solid var(--ink-200)", borderRadius: 8, background: "white" }}>
                  <textarea
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    placeholder="Write a thoughtful reply…"
                    style={{
                      width: "100%",
                      minHeight: 70,
                      padding: 8,
                      border: "1px solid var(--ink-150)",
                      borderRadius: 6,
                      font: "inherit",
                      fontSize: 13,
                      resize: "vertical",
                    }}
                  />
                  <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8, alignItems: "center" }}>
                    <button className="btn-ghost"><IconSparkles size={14}/> Suggest with AI</button>
                    <div style={{ display: "flex", gap: 6 }}>
                      <button className="btn btn-outline btn-xs" onClick={() => setReplyOpen(null)}>Cancel</button>
                      <button className="btn btn-dark btn-xs" onClick={() => setReplyOpen(null)}>Post reply</button>
                    </div>
                  </div>
                </div>
              ) : (
                !r.reply && (
                  <div className="rv-actions">
                    <button className="btn btn-outline btn-xs" onClick={() => { setReplyOpen(r.id); setDraft(""); }}>Reply</button>
                    <button className="btn-ghost"><IconLink size={14}/> Share</button>
                    <button className="btn-ghost danger"><IconAlertTriangle size={14}/> Report</button>
                  </div>
                )
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

window.ViewReviews = ViewReviews;
