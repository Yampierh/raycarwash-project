"use client";
import { MapPin } from "lucide-react";

const neighborhoods = [
  { name: "Fort Wayne", cx: 50, cy: 50, r: 12, primary: true },
  { name: "Aboite", cx: 30, cy: 58, r: 6 },
  { name: "Huntertown", cx: 48, cy: 28, r: 5 },
  { name: "Leo-Cedarville", cx: 68, cy: 30, r: 5 },
  { name: "New Haven", cx: 70, cy: 56, r: 6 },
  { name: "Waynedale", cx: 40, cy: 70, r: 4 },
];

export default function Coverage() {
  return (
    <section id="coverage" className="section">
      <div className="container coverage-grid">
        <div className="coverage-text">
          <span className="section-kicker">Coverage</span>
          <h2 className="section-title">Live in Fort Wayne. Expanding fast.</h2>
          <p className="section-sub">We're operating across Fort Wayne and surrounding suburbs today. New neighborhoods every quarter — request yours below.</p>
          <ul className="coverage-list">
            {neighborhoods.map(n => (
              <li key={n.name}>
                <MapPin size={14} /> {n.name}
                {n.primary && <span className="hub-pill">HQ</span>}
              </li>
            ))}
          </ul>
          <div className="coverage-cta">
            <input className="coverage-input" placeholder="Your ZIP code" />
            <button className="btn btn-dark">Check coverage</button>
          </div>
        </div>
        <div className="coverage-map">
          <svg viewBox="0 0 100 100" className="map-svg" preserveAspectRatio="xMidYMid meet">
            <defs>
              <radialGradient id="hubGrad" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#2563eb" stopOpacity="0.35" />
                <stop offset="60%" stopColor="#2563eb" stopOpacity="0.10" />
                <stop offset="100%" stopColor="#2563eb" stopOpacity="0" />
              </radialGradient>
              <pattern id="mapDots" x="0" y="0" width="4" height="4" patternUnits="userSpaceOnUse">
                <circle cx="0.7" cy="0.7" r="0.4" fill="#cbd5e1" />
              </pattern>
            </defs>
            <rect width="100" height="100" fill="url(#mapDots)" />
            <path d="M0 60 Q20 50 35 55 T70 50 T100 55" stroke="#bfdbfe" strokeWidth="2" fill="none" opacity="0.7" />
            <circle cx="50" cy="50" r="35" fill="url(#hubGrad)" />
            <circle cx="50" cy="50" r="35" fill="none" stroke="#2563eb" strokeWidth="0.4" strokeDasharray="1 1.2" opacity="0.55" />
            {neighborhoods.map(n => (
              <g key={n.name}>
                <circle cx={n.cx} cy={n.cy} r={n.r / 3 + 2} fill="white" opacity="0.95" />
                <circle cx={n.cx} cy={n.cy} r={n.r / 3} fill={n.primary ? "#2563eb" : "#0f172a"} />
                {n.primary && (
                  <circle cx={n.cx} cy={n.cy} r="4" fill="none" stroke="#2563eb" strokeWidth="0.5">
                    <animate attributeName="r" from="3" to="9" dur="2.4s" repeatCount="indefinite" />
                    <animate attributeName="opacity" from="0.7" to="0" dur="2.4s" repeatCount="indefinite" />
                  </circle>
                )}
                <text x={n.cx} y={n.cy - 4} textAnchor="middle" fontSize="2.6" fontFamily="ui-monospace,monospace" fill="#0f172a" fontWeight="600">{n.name.toUpperCase()}</text>
              </g>
            ))}
          </svg>
          <div className="map-legend">
            <div><span className="leg-dot brand" />HQ</div>
            <div><span className="leg-dot" />Service area</div>
            <div><span className="leg-dot ring" />20 mi radius</div>
          </div>
        </div>
      </div>
    </section>
  );
}
