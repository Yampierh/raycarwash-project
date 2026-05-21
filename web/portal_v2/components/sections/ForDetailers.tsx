import Link from "next/link";
import { Calendar, Wallet, Shield, Wrench, ArrowRight } from "lucide-react";

const benefits = [
  { ic: <Calendar size={20} />, t: "Own your schedule", b: "Accept or decline any job. Set your service area and your hours." },
  { ic: <Wallet size={20} />, t: "Instant payouts", b: "Funds hit your bank the same day a job is marked complete." },
  { ic: <Shield size={20} />, t: "Verified clients", b: "Every customer is identity-checked. No-shows are tracked." },
  { ic: <Wrench size={20} />, t: "Built-in tools", b: "Routing, before/after capture, and payout ledger in one app." },
];

export default function ForDetailers() {
  return (
    <section id="detailers" className="section dark-section">
      <div className="container detailers-grid">
        <div className="detailers-left">
          <span className="section-kicker accent">For detailers</span>
          <h2 className="section-title light">Run your own detailing business — without the marketing.</h2>
          <p className="section-sub light">Bring your skills. We bring the clients, the schedule, and same-day payouts.</p>

          <div className="earn-card">
            <div className="earn-row"><span className="earn-lbl">Median weekly earnings</span><span className="earn-val">$1,840</span></div>
            <div className="earn-row"><span className="earn-lbl">Top-quartile weekly</span><span className="earn-val">$2,720</span></div>
            <div className="earn-row"><span className="earn-lbl">Average per job</span><span className="earn-val">$112</span></div>
            <div className="earn-bar">
              <div className="earn-bar-fill" />
              <span className="earn-bar-tag">Top 10% earn $3,400+/wk</span>
            </div>
          </div>

          <Link href="/detailers" className="btn btn-light btn-lg">Apply to detail <ArrowRight size={16} /></Link>
          <p className="apply-note">Average application takes 4 minutes · Decision in 48 hours</p>
        </div>

        <div className="detailers-right">
          <ul className="benefits-grid">
            {benefits.map(b => (
              <li key={b.t} className="benefit-card">
                <span className="benefit-ic">{b.ic}</span>
                <div className="benefit-t">{b.t}</div>
                <div className="benefit-b">{b.b}</div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
