"use client";
import { useState } from "react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import FAQ from "@/components/sections/FAQ";
import { Apple, Smartphone, Shield, UserCheck, Check, Star, Clock, ArrowRight, MapPin } from "lucide-react";

const faqItems = [
  { q: "How quickly can I get a detailer?", a: "Most bookings are matched within minutes. Average ETA to your location is 22 minutes from confirmation." },
  { q: "Do I need to be home during the service?", a: "Not necessarily. You just need the car accessible. Most clients go about their day and get notified when the detailer arrives and completes." },
  { q: "What vehicles can you detail?", a: "Sedans, SUVs, trucks, vans, and motorcycles. Size affects pricing — the in-app quote adjusts automatically." },
  { q: "How do I pay?", a: "Card on file. We authorize at booking and capture only after the job is rated complete. Tips are optional, 100% go to the detailer." },
  { q: "What if my car has pet hair or heavy soiling?", a: "Add the pet hair or heavy contamination add-on at booking. Detailers come prepared. If it's more extensive, they'll update the quote before starting." },
  { q: "Can I request the same detailer again?", a: "Yes. Save any detailer as a favorite and request them directly on future bookings." },
  { q: "What is the satisfaction guarantee?", a: "If you're not happy with the result, open a dispute within 48 hours. We'll arrange a complimentary re-service or issue a refund." },
  { q: "Is this available outside Fort Wayne?", a: "We're currently serving Fort Wayne and surrounding suburbs. Sign up with your ZIP and we'll notify you when we expand to your area." },
];

const journeySteps = [
  {
    label: "Pick service", icon: "🎯",
    title: "Choose your clean, set your time.",
    desc: "Select a service package, add-ons, and your vehicle. Get a flat quote before you commit — no hidden fees, ever.",
    tags: ["Exterior $49", "Interior $89", "Full $149", "Add-ons"],
  },
  {
    label: "Choose time", icon: "📅",
    title: "Book in 90 seconds.",
    desc: "Pick a time window that works for you. We match you with a nearby vetted detailer and confirm instantly.",
    tags: ["Same-day slots", "Future scheduling", "2hr windows"],
  },
  {
    label: "Watch arrive", icon: "📍",
    title: "Track them live.",
    desc: "See your detailer's real-time location, ETA, and profile. Know exactly when they'll arrive.",
    tags: ["Live map", "22 min avg ETA", "Detailer profile"],
  },
  {
    label: "Pay & rate", icon: "⭐",
    title: "Pay after. Rate in two taps.",
    desc: "Card captures only when the job is marked complete. Before/after photos attached automatically.",
    tags: ["Secure payment", "Photo proof", "Rate & tip"],
  },
];

const trustPillars = [
  { ic: <UserCheck size={22} />, t: "Identity verified", b: "Government ID + selfie match on every detailer before their first job." },
  { ic: <Shield size={22} />, t: "Background checked", b: "Criminal and driving record review. Re-verified annually." },
  { ic: <Shield size={22} />, t: "Insured", b: "Commercial general liability covers your vehicle during every service." },
  { ic: <Check size={22} />, t: "Documented", b: "Before/after photos on every job create an audit trail for disputes." },
];

const reviews = [
  { stars: 5, text: "Booked at 9 a.m., the truck was in my driveway by 11. Insanely convenient.", name: "Maria G.", loc: "Fort Wayne, IN" },
  { stars: 5, text: "My detailer sent before/after photos through the app. Felt extremely legit.", name: "Derrick P.", loc: "Aboite, IN" },
  { stars: 5, text: "Full detail on my F-150 — looks better than the day I bought it.", name: "Jonas R.", loc: "New Haven, IN" },
  { stars: 5, text: "Pricing is transparent up front. No surprise upcharges.", name: "Anna L.", loc: "Fort Wayne, IN" },
  { stars: 5, text: "Pet hair add-on was worth every penny. The lab mix had done serious damage.", name: "Cynthia M.", loc: "Waynedale, IN" },
  { stars: 5, text: "The detailer was professional and efficient. Car smells brand new.", name: "Rick T.", loc: "Leo-Cedarville, IN" },
];

const addons = [
  { name: "Pet hair removal", price: 25 }, { name: "Headlight restoration", price: 40 },
  { name: "Ceramic spray sealant", price: 35 }, { name: "Odor elimination", price: 30 },
  { name: "Engine bay clean", price: 45 }, { name: "Tire shine", price: 15 },
];

export default function RidersPage() {
  const [activeStep, setActiveStep] = useState(0);

  return (
    <>
      <Navbar page="riders" />
      <main>
        {/* Hero */}
        <section className="riders-hero">
          <div className="hero-grid" aria-hidden />
          <div className="container riders-hero-inner">
            <div>
              <div className="hero-kicker">
                <span className="kicker-dot" />
                <span>For riders · Fort Wayne, IN</span>
              </div>
              <h1 className="hero-h1">Your car, cleaned.<br /><span className="hero-h1-accent">Without leaving home.</span></h1>
              <p className="hero-sub">Book a vetted detailer to your driveway in minutes. Flat-rate pricing, live tracking, and before/after photos — every time.</p>
              <div className="hero-ctas" style={{ marginBottom: "24px" }}>
                <a href={process.env.NEXT_PUBLIC_APPSTORE_URL || "#"} className="btn btn-dark btn-lg"><Apple size={18} /> App Store</a>
                <a href={process.env.NEXT_PUBLIC_PLAYSTORE_URL || "#"} className="btn btn-outline btn-lg"><Smartphone size={18} /> Google Play</a>
              </div>
              <div className="riders-stat-strip">
                <div className="rs-stat"><div className="rs-n">4.9★</div><div className="rs-l">1,240+ reviews</div></div>
                <div className="rs-stat"><div className="rs-n">22 min</div><div className="rs-l">avg detailer ETA</div></div>
                <div className="rs-stat"><div className="rs-n">2,400+</div><div className="rs-l">details delivered</div></div>
                <div className="rs-stat"><div className="rs-n">$0</div><div className="rs-l">surprise fees</div></div>
              </div>
            </div>
            <div style={{ display: "flex", justifyContent: "center" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", maxWidth: "340px" }}>
                {[
                  { bg: "linear-gradient(135deg,#1e3a8a,#2563eb)", label: "Booking flow" },
                  { bg: "linear-gradient(135deg,#065f46,#059669)", label: "Live tracking" },
                  { bg: "#f4f4f5", label: "Before photo", dark: true },
                  { bg: "linear-gradient(135deg,#1e3a8a,#3b82f6)", label: "After photo" },
                ].map(({ bg, label, dark }) => (
                  <div key={label} style={{ height: "140px", borderRadius: "14px", background: bg, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "11px", fontWeight: 600, color: dark ? "#a1a1aa" : "rgba(255,255,255,0.5)" }}>{label}</div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Booking Journey */}
        <section id="how" className="section booking-journey" style={{ background: "#fff" }}>
          <div className="container">
            <div className="section-head">
              <span className="section-kicker">How it works</span>
              <h2 className="section-title">Book in 90 seconds.</h2>
              <p className="section-sub">From tapping "book" to a spotless car — four steps, zero friction.</p>
            </div>
            <div className="bj-tabs">
              {journeySteps.map((s, i) => (
                <button key={s.label} className={`bj-tab${activeStep === i ? " on" : ""}`} onClick={() => setActiveStep(i)}>
                  {s.icon} {s.label}
                </button>
              ))}
            </div>
            <div className="bj-content">
              <div className="bj-text">
                <h3>{journeySteps[activeStep].title}</h3>
                <p>{journeySteps[activeStep].desc}</p>
                <div className="bj-tags">
                  {journeySteps[activeStep].tags.map(t => <span key={t} className="bj-tag">{t}</span>)}
                </div>
              </div>
              <div style={{ display: "flex", justifyContent: "center" }}>
                <div className="phone-mock">
                  <div className="phone-screen">
                    <div className="phone-notch" />
                    <div className="phone-content" style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "10px" }}>
                      <div style={{ fontSize: "12px", fontWeight: 700, color: "#09090b" }}>Step {activeStep + 1} — {journeySteps[activeStep].label}</div>
                      <div style={{ flex: 1, background: "linear-gradient(135deg,#eff6ff,#dbeafe)", borderRadius: "10px", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "28px" }}>
                        {journeySteps[activeStep].icon}
                      </div>
                      {journeySteps[activeStep].tags.map(t => (
                        <div key={t} style={{ padding: "7px 10px", borderRadius: "6px", background: "#fafafa", border: "1px solid #e4e4e7", fontSize: "12px" }}>{t}</div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Services Compare */}
        <section id="services" className="section section-alt">
          <div className="container">
            <div className="section-head">
              <span className="section-kicker">Services</span>
              <h2 className="section-title">Flat-rate packages. No surprises.</h2>
              <p className="section-sub">Three tiers plus à-la-carte add-ons. Starting prices for sedan-class vehicles.</p>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table className="svc-compare-table" style={{ marginBottom: "32px" }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: "left" }}>Feature</th>
                    <th>Exterior<br /><span style={{ fontSize: "18px", fontWeight: 800, color: "#2563eb" }}>$49</span></th>
                    <th style={{ background: "#eff6ff", borderTop: "2px solid #2563eb" }}>Full Detail<br /><span style={{ fontSize: "18px", fontWeight: 800, color: "#2563eb" }}>$149</span></th>
                    <th>Interior<br /><span style={{ fontSize: "18px", fontWeight: 800, color: "#2563eb" }}>$89</span></th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    ["Hand wash & dry", true, true, false],
                    ["Wheels & tires", true, true, false],
                    ["Spray wax", true, true, false],
                    ["Full vacuum", false, true, true],
                    ["Steam-clean upholstery", false, true, true],
                    ["Dashboard & panels", false, true, true],
                    ["Glass cleaning", false, true, true],
                    ["Clay-bar decon.", false, true, false],
                  ].map(([feature, ext, full, int_]) => (
                    <tr key={feature as string}>
                      <td>{feature as string}</td>
                      <td>{ext ? <span className="check">✓</span> : <span style={{ color: "#e4e4e7" }}>—</span>}</td>
                      <td style={{ background: "#fafafa" }}>{full ? <span className="check">✓</span> : <span style={{ color: "#e4e4e7" }}>—</span>}</td>
                      <td>{int_ ? <span className="check">✓</span> : <span style={{ color: "#e4e4e7" }}>—</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div>
              <div style={{ fontSize: "14px", fontWeight: 600, marginBottom: "16px" }}>Popular add-ons</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "12px" }}>
                {addons.map(a => (
                  <div key={a.name} style={{ padding: "14px 16px", background: "white", border: "1px solid #e4e4e7", borderRadius: "10px", display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "14px" }}>
                    <span style={{ fontWeight: 500 }}>{a.name}</span>
                    <span style={{ fontWeight: 700, color: "#2563eb" }}>+${a.price}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Trust & Safety */}
        <section id="safety" className="section">
          <div className="container">
            <div className="section-head">
              <span className="section-kicker">Trust & safety</span>
              <h2 className="section-title">Every detailer, triple-checked.</h2>
              <p className="section-sub">We built the trust system we wished existed when we hired our first pro.</p>
            </div>
            <div className="trust-safety-grid">
              {trustPillars.map(p => (
                <div key={p.t} className="ts-card">
                  <div className="ts-ic">{p.ic}</div>
                  <div className="ts-t">{p.t}</div>
                  <div className="ts-b">{p.b}</div>
                </div>
              ))}
            </div>
            <div className="dispute-card">
              <div style={{ width: "44px", height: "44px", borderRadius: "12px", background: "#d1fae5", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, fontSize: "20px" }}>✓</div>
              <div>
                <div style={{ fontSize: "15px", fontWeight: 700, marginBottom: "4px" }}>94% of disputes resolved in 24 hours</div>
                <div style={{ fontSize: "14px", color: "#71717a" }}>Open a claim in the app. Our team reviews before/after photos and job timeline — most are resolved same day.</div>
              </div>
            </div>
          </div>
        </section>

        {/* Reviews wall */}
        <section id="reviews" className="section section-alt">
          <div className="container">
            <div className="section-head split">
              <div>
                <span className="section-kicker">Reviews</span>
                <h2 className="section-title">What riders say.</h2>
              </div>
              <div className="rating-summary">
                <div className="rating-stars">★★★★★</div>
                <div className="rating-meta">4.9 · 1,240+ reviews</div>
              </div>
            </div>
            <div className="reviews-wall">
              {reviews.map(r => (
                <div key={r.name} className="review-card">
                  <div className="review-stars">{"★".repeat(r.stars)}</div>
                  <div className="review-text">&ldquo;{r.text}&rdquo;</div>
                  <div className="review-name">{r.name}</div>
                  <div className="review-meta">{r.loc}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <FAQ title="Questions from riders." items={faqItems} />

        {/* CTA */}
        <section className="section final-cta">
          <div className="container">
            <div className="cta-card">
              <div className="cta-left">
                <span className="section-kicker accent">Get the app</span>
                <h2 className="cta-title">Ready for a cleaner car?</h2>
                <p className="cta-sub">Download RayCarWash and book your first detail in under two minutes. Available for iOS and Android.</p>
                <div className="cta-actions">
                  <a href={process.env.NEXT_PUBLIC_APPSTORE_URL || "#"} className="btn btn-light btn-lg"><Apple size={18} /> App Store</a>
                  <a href={process.env.NEXT_PUBLIC_PLAYSTORE_URL || "#"} className="btn btn-light-outline btn-lg"><Smartphone size={18} /> Google Play</a>
                </div>
                <div className="cta-footnotes">
                  <span>✓ Free to download</span>
                  <span>✓ No subscription</span>
                  <span>✓ Pay only when booked</span>
                </div>
              </div>
              <div className="cta-right">
                <div className="cta-mosaic">
                  <div className="cta-photo cta-photo-main"><span className="photo-label">App screenshot</span></div>
                  <div className="cta-photo cta-photo-b"><span className="photo-label">Before</span></div>
                  <div className="cta-photo cta-photo-a"><span className="photo-label">After</span></div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
