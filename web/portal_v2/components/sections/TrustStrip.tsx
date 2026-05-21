import { UserCheck, Shield, Star, ArrowRight } from "lucide-react";

const items = [
  { ic: <UserCheck size={20} />, t: "Verified detailers", b: "Identity + background check before any job." },
  { ic: <Shield size={20} />, t: "Insured service", b: "Your vehicle is protected during every visit." },
  { ic: <Star size={20} />, t: "Satisfaction guarantee", b: "Not happy? We'll re-do it or refund." },
];

export default function TrustStrip() {
  return (
    <section className="trust">
      <div className="container">
        <div className="trust-grid">
          {items.map(it => (
            <div key={it.t} className="trust-card">
              <span className="trust-ic">{it.ic}</span>
              <div>
                <div className="trust-title">{it.t}</div>
                <div className="trust-body">{it.b}</div>
              </div>
              <span className="trust-arrow"><ArrowRight size={14} /></span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
