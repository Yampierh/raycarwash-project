"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { Apple, Smartphone, ArrowRight, Shield, Wallet, MapPin, Calendar, UserCheck } from "lucide-react";

interface HeroProps {
  audience: "client" | "detailer";
  onAudienceChange: (a: "client" | "detailer") => void;
}

function ClientPhoneMock({ step }: { step: number }) {
  const screens = [
    { label: "Book", content: (
      <div style={{ padding: "12px", display: "flex", flexDirection: "column", gap: "10px" }}>
        <div style={{ fontSize: "11px", fontWeight: 700, color: "#09090b", marginBottom: "4px" }}>Book a detail</div>
        {["Exterior wash · $49", "Full detail · $149", "Interior · $89"].map((s, i) => (
          <div key={i} style={{ padding: "10px 12px", borderRadius: "8px", background: i === 1 ? "#eff6ff" : "#fafafa", border: `1px solid ${i === 1 ? "#2563eb" : "#e4e4e7"}`, fontSize: "12px", fontWeight: i === 1 ? 600 : 400 }}>{s}</div>
        ))}
      </div>
    )},
    { label: "En route", content: (
      <div style={{ padding: "12px", display: "flex", flexDirection: "column", gap: "10px" }}>
        <div style={{ background: "#1e3a8a", borderRadius: "8px", height: "100px", display: "flex", alignItems: "center", justifyContent: "center", color: "rgba(255,255,255,0.5)", fontSize: "11px" }}>Map view</div>
        <div style={{ padding: "10px 12px", borderRadius: "8px", background: "#eff6ff", border: "1px solid #dbeafe", fontSize: "12px", fontWeight: 600, color: "#1e3a8a" }}>Marcus T. · ETA 18 min ★ 4.9</div>
      </div>
    )},
    { label: "In progress", content: (
      <div style={{ padding: "12px", display: "flex", flexDirection: "column", gap: "8px" }}>
        <div style={{ fontSize: "11px", fontWeight: 700, color: "#10b981" }}>● In progress</div>
        <div style={{ fontSize: "12px", color: "#52525b" }}>Full detail · 2018 Honda Civic</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px" }}>
          {["Before", "Wheels", "Interior", "After"].map((l, i) => (
            <div key={l} style={{ aspectRatio: "4/3", borderRadius: "6px", background: i % 2 === 0 ? "#e4e4e7" : "#dbeafe", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "10px", color: "#a1a1aa" }}>{l}</div>
          ))}
        </div>
      </div>
    )},
    { label: "Complete", content: (
      <div style={{ padding: "12px", display: "flex", flexDirection: "column", gap: "10px", alignItems: "center", textAlign: "center" }}>
        <div style={{ width: "40px", height: "40px", borderRadius: "50%", background: "#d1fae5", display: "flex", alignItems: "center", justifyContent: "center", color: "#10b981", fontSize: "20px" }}>✓</div>
        <div style={{ fontSize: "13px", fontWeight: 700 }}>Detail complete!</div>
        <div style={{ fontSize: "11px", color: "#71717a" }}>Full detail · $149 · 2:41 hrs</div>
        <div style={{ display: "flex", gap: "4px", color: "#f59e0b", fontSize: "16px" }}>★★★★★</div>
      </div>
    )},
  ];
  const s = screens[step];
  return (
    <div className="phone-mock">
      <div className="phone-screen">
        <div className="phone-notch" />
        <div className="phone-content">{s.content}</div>
      </div>
    </div>
  );
}

function DetailerPhoneMock({ step }: { step: number }) {
  const screens = [
    { label: "Job offered", content: (
      <div style={{ padding: "12px", display: "flex", flexDirection: "column", gap: "8px" }}>
        <div style={{ fontSize: "11px", fontWeight: 700, color: "#09090b" }}>New job offer</div>
        <div style={{ padding: "12px", borderRadius: "8px", background: "#eff6ff", border: "1px solid #2563eb" }}>
          <div style={{ fontSize: "13px", fontWeight: 700, marginBottom: "4px" }}>Full detail · Civic</div>
          <div style={{ fontSize: "11px", color: "#52525b" }}>2.1 mi · Today 2:30 PM · $149</div>
          <div style={{ fontSize: "11px", color: "#10b981", marginTop: "4px" }}>Great fit</div>
        </div>
        <div style={{ display: "flex", gap: "6px" }}>
          <div style={{ flex: 1, padding: "8px", borderRadius: "6px", background: "#09090b", color: "white", textAlign: "center", fontSize: "12px", fontWeight: 600 }}>Accept</div>
          <div style={{ flex: 1, padding: "8px", borderRadius: "6px", background: "#f4f4f5", textAlign: "center", fontSize: "12px", fontWeight: 600 }}>Decline</div>
        </div>
      </div>
    )},
    { label: "Schedule", content: (
      <div style={{ padding: "12px", display: "flex", flexDirection: "column", gap: "8px" }}>
        <div style={{ fontSize: "11px", fontWeight: 700 }}>Today · 4 jobs</div>
        {[{ t: "9:00", s: "M3 Exterior", p: "$49" }, { t: "11:30", s: "Civic Full", p: "$149" }, { t: "2:00", s: "F-150 Int.", p: "$89" }, { t: "4:30", s: "Sienna Full", p: "$169" }].map((j, i) => (
          <div key={i} style={{ display: "flex", gap: "8px", alignItems: "center", padding: "6px 8px", borderRadius: "6px", background: i === 0 ? "#d1fae5" : "#fafafa", border: "1px solid #e4e4e7", fontSize: "11px" }}>
            <span style={{ color: "#a1a1aa", minWidth: "30px" }}>{j.t}</span>
            <span style={{ flex: 1, fontWeight: 500 }}>{j.s}</span>
            <span style={{ color: "#2563eb", fontWeight: 700 }}>{j.p}</span>
          </div>
        ))}
      </div>
    )},
    { label: "Earnings", content: (
      <div style={{ padding: "12px", display: "flex", flexDirection: "column", gap: "8px", alignItems: "center", textAlign: "center" }}>
        <div style={{ fontSize: "11px", color: "#a1a1aa" }}>This week</div>
        <div style={{ fontSize: "32px", fontWeight: 800, letterSpacing: "-0.04em", color: "#09090b" }}>$1,143</div>
        <div style={{ fontSize: "11px", color: "#10b981", fontWeight: 600 }}>▲ +22% vs last week</div>
        <div style={{ display: "flex", gap: "4px", alignItems: "flex-end", height: "40px", width: "100%", justifyContent: "center" }}>
          {[40, 65, 30, 80, 55, 90, 70].map((h, i) => (
            <div key={i} style={{ width: "24px", height: `${h}%`, background: i === 5 ? "#2563eb" : "#dbeafe", borderRadius: "2px" }} />
          ))}
        </div>
      </div>
    )},
    { label: "Profile", content: (
      <div style={{ padding: "12px", display: "flex", flexDirection: "column", gap: "8px", alignItems: "center" }}>
        <div style={{ width: "48px", height: "48px", borderRadius: "50%", background: "#eff6ff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "18px", fontWeight: 700, color: "#2563eb" }}>MT</div>
        <div style={{ fontSize: "13px", fontWeight: 700 }}>Marcus T.</div>
        <div style={{ display: "flex", gap: "12px", fontSize: "11px", textAlign: "center" }}>
          {[["4.9★", "Rating"], ["312", "Jobs"], ["98%", "On-time"]].map(([n, l]) => (
            <div key={l}><div style={{ fontWeight: 700 }}>{n}</div><div style={{ color: "#a1a1aa" }}>{l}</div></div>
          ))}
        </div>
      </div>
    )},
  ];
  const s = screens[step];
  return (
    <div className="phone-mock">
      <div className="phone-screen">
        <div className="phone-notch" />
        <div className="phone-content">{s.content}</div>
      </div>
    </div>
  );
}

export default function Hero({ audience, onAudienceChange }: HeroProps) {
  const [step, setStep] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setStep(s => (s + 1) % 4), 3200);
    return () => clearInterval(id);
  }, []);

  const isClient = audience === "client";
  const stepLabels = isClient
    ? ["Book", "Detailer en route", "In progress", "Complete"]
    : ["Job offered", "Today's schedule", "Earnings", "Profile"];

  return (
    <section id="top" className="hero">
      <div className="hero-grid" aria-hidden />
      <div className="hero-inner">
        <div className="hero-left">
          <div className="hero-kicker">
            <span className="kicker-dot" />
            <span>Mobile detailing · Fort Wayne, IN</span>
          </div>

          {isClient ? (
            <h1 className="hero-h1">A spotless car,<br /><span className="hero-h1-accent">at your door.</span></h1>
          ) : (
            <h1 className="hero-h1">Detail cars.<br /><span className="hero-h1-accent">Skip the office.</span></h1>
          )}

          <p className="hero-sub">
            {isClient
              ? "Book a vetted detailer to your driveway in minutes. They bring water, power, and pro-grade products — you keep your day."
              : "Bring the skills. We bring the clients, the schedule, and same-day payouts straight to your bank."}
          </p>

          <div className="hero-ctas">
            {isClient ? (
              <>
                <a href={process.env.NEXT_PUBLIC_APPSTORE_URL || "#"} className="btn btn-dark">
                  <Apple size={18} /><span>Download the app</span>
                </a>
                <a href={process.env.NEXT_PUBLIC_PLAYSTORE_URL || "#"} className="btn btn-outline">
                  <Smartphone size={18} /><span>Get on Google Play</span>
                </a>
              </>
            ) : (
              <>
                <Link href="/signup" className="btn btn-accent">Apply to detail<ArrowRight size={16} /></Link>
                <a href="#earnings" className="btn btn-outline">See earnings</a>
              </>
            )}
          </div>

          <ul className="hero-bullets">
            {isClient ? (
              <>
                <li><span className="bul-ic"><Shield size={14} /></span>Vetted & insured pros</li>
                <li><span className="bul-ic"><Wallet size={14} /></span>Flat-rate pricing, no surprises</li>
                <li><span className="bul-ic"><MapPin size={14} /></span>Live ETA + before/after photos</li>
              </>
            ) : (
              <>
                <li><span className="bul-ic"><Calendar size={14} /></span>Set your own hours & service area</li>
                <li><span className="bul-ic"><Wallet size={14} /></span>Same-day payouts to your bank</li>
                <li><span className="bul-ic"><UserCheck size={14} /></span>Verified clients, tracked no-shows</li>
              </>
            )}
          </ul>

          <div className="hero-stats">
            <div><div className="hs-n">{isClient ? "2,400+" : "85"}</div><div className="hs-l">{isClient ? "details delivered" : "active detailers"}</div></div>
            <div><div className="hs-n">{isClient ? "22 min" : "$42/hr"}</div><div className="hs-l">{isClient ? "avg detailer ETA" : "median earnings"}</div></div>
            <div><div className="hs-n">{isClient ? "4.9★" : "Same day"}</div><div className="hs-l">{isClient ? "average rating" : "payouts"}</div></div>
          </div>
        </div>

        <div className="hero-right">
          <div className="hero-phone-stack">
            {isClient ? <ClientPhoneMock step={step} /> : <DetailerPhoneMock step={step} />}
            <div className="hero-step-track">
              {stepLabels.map((l, i) => (
                <button key={i} className={`hero-step-dot${i === step ? " on" : ""}`} onClick={() => setStep(i)} aria-label={l}>
                  <span className="hero-step-num">{i + 1}</span>
                  <span className="hero-step-lbl">{l}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
