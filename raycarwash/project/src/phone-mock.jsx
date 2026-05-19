// Phone mock — varies content based on `audience` ("client" or "detailer") and `step` (0..3).
function PhoneFrame({ children, glow = false }) {
  return (
    <div className="phone-wrap">
      <div className={"phone-glow " + (glow ? "on" : "")}></div>
      <div className="phone">
        <div className="phone-notch"></div>
        <div className="phone-screen">{children}</div>
      </div>
    </div>
  );
}

function StripedPlaceholder({ label, ratio = "1/1", className = "" }) {
  return (
    <div
      className={"striped-ph " + className}
      style={{ aspectRatio: ratio }}
      aria-label={label}
    >
      <span>{label}</span>
    </div>
  );
}

function ClientPhone({ step = 0 }) {
  // step: 0 book, 1 matched, 2 in-progress, 3 done
  return (
    <PhoneFrame glow>
      <div className="ps-header">
        <div className="ps-status">9:41</div>
        <div className="ps-status-icons">
          <span className="ps-dot"></span>
          <span className="ps-dot"></span>
          <span className="ps-dot"></span>
        </div>
      </div>
      <div className="ps-body">
        {step === 0 && (
          <>
            <div className="ps-eyebrow">Book a detail</div>
            <div className="ps-title">Pick the level of clean</div>
            <div className="ps-card-stack">
              <div className="ps-svc-card">
                <div className="ps-svc-row">
                  <div className="ps-svc-name">Exterior wash</div>
                  <div className="ps-svc-price">$49</div>
                </div>
                <div className="ps-svc-meta">45–60 min · Hand wash + spray wax</div>
              </div>
              <div className="ps-svc-card sel">
                <div className="ps-svc-row">
                  <div className="ps-svc-name">Full detail</div>
                  <div className="ps-svc-price">$149</div>
                </div>
                <div className="ps-svc-meta">3–4 hr · Interior + exterior + clay bar</div>
                <div className="ps-svc-badge">Most popular</div>
              </div>
              <div className="ps-svc-card">
                <div className="ps-svc-row">
                  <div className="ps-svc-name">Interior detail</div>
                  <div className="ps-svc-price">$89</div>
                </div>
                <div className="ps-svc-meta">1.5–2 hr · Steam + vacuum + glass</div>
              </div>
            </div>
            <div className="ps-cta">Continue</div>
          </>
        )}
        {step === 1 && (
          <>
            <div className="ps-eyebrow">Detailer assigned</div>
            <div className="ps-title">Marcus is en route</div>
            <div className="ps-eta-card">
              <div className="ps-eta-time">22 min</div>
              <div className="ps-eta-sub">Arriving by 2:30 PM</div>
              <div className="ps-eta-map">
                <svg viewBox="0 0 200 80" preserveAspectRatio="none">
                  <path d="M0 70 Q40 30 80 50 T160 30 L200 20" stroke="#3b82f6" strokeWidth="2.5" fill="none" strokeDasharray="4 4"/>
                  <circle cx="200" cy="20" r="4" fill="#3b82f6"/>
                  <circle cx="0" cy="70" r="3" fill="#0f172a"/>
                </svg>
              </div>
              <div className="ps-eta-pro">
                <div className="ps-eta-avatar"></div>
                <div className="ps-eta-pro-text">
                  <div className="ps-eta-pro-name">Marcus T.</div>
                  <div className="ps-eta-pro-meta">★ 4.9 · 312 jobs</div>
                </div>
                <div className="ps-pill ps-pill-green">En route</div>
              </div>
            </div>
            <div className="ps-cta">Message detailer</div>
          </>
        )}
        {step === 2 && (
          <>
            <div className="ps-eyebrow">In progress</div>
            <div className="ps-title">Full detail · Civic</div>
            <div className="ps-prog-card">
              <div className="ps-prog-bar"><div className="ps-prog-fill" style={{ width: "62%" }}></div></div>
              <div className="ps-prog-meta">
                <span>62% · ~1h 14m left</span>
                <span className="ps-pill ps-pill-amber">Working</span>
              </div>
              <div className="ps-prog-steps">
                <div className="ps-step done">Pre-wash inspection</div>
                <div className="ps-step done">Exterior wash</div>
                <div className="ps-step active">Interior steam clean</div>
                <div className="ps-step">Clay bar + wax</div>
              </div>
            </div>
          </>
        )}
        {step === 3 && (
          <>
            <div className="ps-eyebrow">Service complete</div>
            <div className="ps-title">Rate Marcus</div>
            <div className="ps-grid3">
              <StripedPlaceholder label="BEFORE" ratio="1/1" className="dark" />
              <StripedPlaceholder label="AFTER" ratio="1/1" />
              <StripedPlaceholder label="DETAIL" ratio="1/1" />
            </div>
            <div className="ps-rate">
              <span>★</span><span>★</span><span>★</span><span>★</span><span>★</span>
            </div>
            <div className="ps-receipt">
              <div className="ps-receipt-row"><span>Full detail</span><span>$149.00</span></div>
              <div className="ps-receipt-row"><span>Tip</span><span>$20.00</span></div>
              <div className="ps-receipt-total"><span>Total</span><span>$169.00</span></div>
            </div>
          </>
        )}
      </div>
    </PhoneFrame>
  );
}

function DetailerPhone({ step = 0 }) {
  return (
    <PhoneFrame glow>
      <div className="ps-header dark">
        <div className="ps-status">9:41</div>
        <div className="ps-status-icons">
          <span className="ps-dot light"></span>
          <span className="ps-dot light"></span>
          <span className="ps-dot light"></span>
        </div>
      </div>
      <div className="ps-body dark">
        {step === 0 && (
          <>
            <div className="ps-eyebrow muted">Incoming job</div>
            <div className="ps-title light">2 miles away</div>
            <div className="ps-job-card">
              <div className="ps-job-row">
                <div className="ps-job-svc">Full detail · Civic</div>
                <div className="ps-job-pay">$149</div>
              </div>
              <div className="ps-job-meta">Today · 2:30 PM · 3.4 mi · Aboite, IN</div>
              <div className="ps-job-row mt">
                <div className="ps-job-svc">Net to you</div>
                <div className="ps-job-pay green">$126.65</div>
              </div>
              <div className="ps-job-actions">
                <div className="ps-cta ghost">Decline</div>
                <div className="ps-cta accent">Accept</div>
              </div>
            </div>
            <div className="ps-job-footer">Auto-decline in 0:42</div>
          </>
        )}
        {step === 1 && (
          <>
            <div className="ps-eyebrow muted">Today · Mon Jun 3</div>
            <div className="ps-title light">3 jobs · $387</div>
            <div className="ps-sched">
              <div className="ps-sched-row done">
                <div className="ps-sched-time">9:00</div>
                <div className="ps-sched-info">
                  <div>Exterior wash · Tesla M3</div>
                  <div className="muted">Completed · $49</div>
                </div>
              </div>
              <div className="ps-sched-row active">
                <div className="ps-sched-time">11:30</div>
                <div className="ps-sched-info">
                  <div>Full detail · Civic</div>
                  <div className="muted">In progress · $149</div>
                </div>
              </div>
              <div className="ps-sched-row">
                <div className="ps-sched-time">3:00</div>
                <div className="ps-sched-info">
                  <div>Interior detail · F-150</div>
                  <div className="muted">Upcoming · $189</div>
                </div>
              </div>
            </div>
          </>
        )}
        {step === 2 && (
          <>
            <div className="ps-eyebrow muted">This week</div>
            <div className="ps-title light">Earnings</div>
            <div className="ps-earn">
              <div className="ps-earn-big">$2,148<span className="ps-earn-sub">.50</span></div>
              <div className="ps-earn-trend">+18% vs last week</div>
              <div className="ps-bars">
                {[40, 65, 30, 80, 55, 90, 70].map((h, i) => (
                  <div key={i} className="ps-bar" style={{ height: h + "%" }}></div>
                ))}
              </div>
              <div className="ps-bars-labels">
                <span>M</span><span>T</span><span>W</span><span>T</span><span>F</span><span>S</span><span>S</span>
              </div>
            </div>
            <div className="ps-cashout">
              <div>
                <div className="ps-cashout-label">Available now</div>
                <div className="ps-cashout-amt">$412.00</div>
              </div>
              <div className="ps-cta sm accent">Cash out</div>
            </div>
          </>
        )}
        {step === 3 && (
          <>
            <div className="ps-eyebrow muted">Profile</div>
            <div className="ps-title light">Marcus T.</div>
            <div className="ps-prof-stats">
              <div className="ps-prof-stat"><div className="big">4.9</div><div className="muted">Rating</div></div>
              <div className="ps-prof-stat"><div className="big">312</div><div className="muted">Jobs</div></div>
              <div className="ps-prof-stat"><div className="big">98%</div><div className="muted">On-time</div></div>
            </div>
            <div className="ps-badges-list">
              <div className="ps-badge-chip">✓ Identity verified</div>
              <div className="ps-badge-chip">✓ Background check</div>
              <div className="ps-badge-chip">✓ Insured</div>
            </div>
          </>
        )}
      </div>
    </PhoneFrame>
  );
}

window.PhoneFrame = PhoneFrame;
window.ClientPhone = ClientPhone;
window.DetailerPhone = DetailerPhone;
window.StripedPlaceholder = StripedPlaceholder;
