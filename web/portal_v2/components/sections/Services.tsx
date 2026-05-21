import { Clock, Check, ArrowRight } from "lucide-react";

const services = [
  { name: "Exterior wash", price: 49, duration: "45–60 min", features: ["Hand wash & dry", "Wheels and tires", "Spray wax finish"] },
  { name: "Full detail", price: 149, duration: "3–4 hours", features: ["Everything in exterior + interior", "Clay-bar decontamination", "Tire dressing", "Showroom-grade finish"], featured: true },
  { name: "Interior detail", price: 89, duration: "1.5–2 hours", features: ["Full vacuum", "Steam-clean upholstery", "Dashboard & door panels", "Glass cleaning"] },
];

export default function Services() {
  return (
    <section id="services" className="section section-alt">
      <div className="container">
        <div className="section-head split">
          <div>
            <span className="section-kicker">Services</span>
            <h2 className="section-title">Pick the level of clean.</h2>
            <p className="section-sub">Three core packages, with add-ons for pet hair, headlight restoration, and ceramic spray sealant inside the app.</p>
          </div>
          <a href="#" className="link-arrow">See all add-ons <ArrowRight size={14} /></a>
        </div>
        <div className="svc-grid">
          {services.map(s => (
            <div key={s.name} className={`svc-card${s.featured ? " featured" : ""}`}>
              {s.featured && <span className="svc-badge">Most popular</span>}
              <h3 className="svc-name">{s.name}</h3>
              <div className="svc-price-row">
                <span className="svc-from">from</span>
                <span className="svc-price">${s.price}</span>
              </div>
              <div className="svc-duration"><Clock size={14} /> {s.duration}</div>
              <ul className="svc-features">
                {s.features.map(f => (
                  <li key={f}><Check size={14} /><span>{f}</span></li>
                ))}
              </ul>
              <a href="#" className={`btn btn-block${s.featured ? " btn-dark" : " btn-outline"}`}>Book this</a>
            </div>
          ))}
        </div>
        <p className="svc-footnote">Starting prices for sedan-class vehicles. Final quote is generated in-app based on size, condition, and add-ons.</p>
      </div>
    </section>
  );
}
