import { Star } from "lucide-react";

const items = [
  { quote: "Booked at 9 a.m., the truck was in my driveway by 11. Insanely convenient.", name: "Maria G.", city: "Fort Wayne, IN", rating: 5 },
  { quote: "My detailer sent before/after photos through the app. Felt extremely legit.", name: "Derrick P.", city: "Aboite, IN", rating: 5 },
  { quote: "Full detail on my F-150 — looks better than the day I bought it.", name: "Jonas R.", city: "New Haven, IN", rating: 5 },
  { quote: "Pricing is transparent up front. No surprise upcharges, no haggling.", name: "Anna L.", city: "Fort Wayne, IN", rating: 5 },
];

export default function Testimonials() {
  return (
    <section className="section">
      <div className="container">
        <div className="section-head split">
          <div>
            <span className="section-kicker">What people say</span>
            <h2 className="section-title">Loved by people who&apos;d rather not drive to a car wash.</h2>
          </div>
          <div className="rating-summary">
            <div className="rating-stars">★★★★★</div>
            <div className="rating-meta">4.9 from 1,240+ reviews</div>
          </div>
        </div>
        <div className="testi-grid">
          {items.map(t => (
            <figure key={t.name} className="testi-card">
              <div className="testi-stars">{Array.from({ length: t.rating }).map((_, i) => <Star key={i} size={14} fill="currentColor" />)}</div>
              <blockquote>&ldquo;{t.quote}&rdquo;</blockquote>
              <figcaption>
                <div className="testi-name">{t.name}</div>
                <div className="testi-city">{t.city}</div>
              </figcaption>
            </figure>
          ))}
        </div>
      </div>
    </section>
  );
}
