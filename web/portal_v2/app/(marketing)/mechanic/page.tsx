"use client";
import { useState } from "react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import FAQ from "@/components/sections/FAQ";
import { ArrowRight, Check, Clock } from "lucide-react";

const faqItems = [
  { q: "When will mechanic services actually launch?", a: "Beta in Q4 2026 with our first cohort of founding mechanics. Public launch in Q1 2027, starting in Fort Wayne and surrounding suburbs." },
  { q: "Will mechanic prices be different from the detailing side?", a: "Each service has a flat parts-plus-labor price. You'll see the full quote before booking — no hourly meter, no surprise diagnostic fees." },
  { q: "What if my car needs work I can't get done in a driveway?", a: "Some jobs (transmission, body work, alignment) need a shop. We'll diagnose and refer you out — and your diagnostic fee is credited toward that shop work." },
  { q: "Do you carry the parts on the van?", a: "Common parts for your make/model are pulled before the appointment. If we need something obscure, we'll come back the next day with no second trip fee." },
  { q: "Is your work guaranteed?", a: "Yes. 12-month or 12,000-mile warranty on parts and labor — whichever comes first. If something we fixed fails, we come back free." },
  { q: "Can I get on the founding-customer list separately?", a: "Yes — that's what the waitlist above is. Founding customers get 20% off their first three appointments and priority booking during beta." },
];

const services = [
  { name: "Oil change", price: 65, dur: "30 min", body: "Full-synthetic. Fresh filter. Disposal included." },
  { name: "Brake pads + rotors", price: 280, dur: "90 min", body: "Front or rear axle. OEM-equivalent parts." },
  { name: "Battery replacement", price: 180, dur: "20 min", body: "AGM or standard lead-acid. Includes core return." },
  { name: "Diagnostics scan", price: 75, dur: "30 min", body: "Full OBD-II read. Detailed report in the app." },
  { name: "Tire rotation", price: 35, dur: "25 min", body: "All four. Torque-spec'd. Pressure adjusted." },
  { name: "Wiper blades", price: 35, dur: "10 min", body: "Pair, installed. Right-fit guaranteed." },
  { name: "Air + cabin filters", price: 55, dur: "20 min", body: "Both replaced. Recommended every 15k miles." },
  { name: "Spark plug replacement", price: 220, dur: "60 min", body: "Full set. Iridium or platinum, your choice." },
];

const howSteps = [
  { t: "Book in the app", b: "Pick a service. Tell us your car's year/make/model. Get a flat quote — including parts." },
  { t: "Pick a window", b: "2-hour service windows. Mechanic confirms within an hour. Same-day for emergencies." },
  { t: "We show up loaded", b: "Service van arrives with parts pre-pulled, tools racked, and a portable lift if needed." },
  { t: "Watch or walk away", b: "Live mechanic profile, certifications, photo updates. Pay only when the work passes inspection." },
];

const rollout = [
  { q: "Q2 2026", l: "Hire founding mechanic team", done: true },
  { q: "Q3 2026", l: "Service van fleet · gear procurement", done: true },
  { q: "Q4 2026", l: "Closed beta · waitlist invites", active: true },
  { q: "Q1 2027", l: "Public launch in Fort Wayne" },
  { q: "Q3 2027", l: "Expand to 5 cities" },
];

export default function MechanicPage() {
  const [count, setCount] = useState(347);
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setCount(c => c + 1);
    setSubmitted(true);
    setEmail("");
  };

  return (
    <>
      <Navbar page="mechanic" />
      <main>
        {/* Hero */}
        <section className="mech-hero">
          <div className="hero-grid" aria-hidden />
          <div className="container mech-hero-inner">
            <div className="mech-hero-text">
              <div className="mech-badge">
                <span className="mb-dot" />
                Q4 2026 · Beta launching in Fort Wayne
              </div>
              <h1 className="mech-h1">Mobile mechanic.<br /><span className="hero-h1-accent">In your driveway.</span></h1>
              <p className="mech-sub">
                Oil changes, brake jobs, diagnostics, battery swaps — done where your car actually lives.
                No towing. No waiting rooms. No &ldquo;we&apos;ll call you when it&apos;s ready.&rdquo;
              </p>
              {submitted ? (
                <div style={{ padding: "16px 20px", borderRadius: "10px", background: "#d1fae5", color: "#065f46", fontWeight: 600, fontSize: "15px", marginBottom: "12px" }}>
                  ✓ You&apos;re on the list! We&apos;ll email you when your ZIP goes live.
                </div>
              ) : (
                <form className="waitlist-form" onSubmit={handleSubmit}>
                  <input type="email" required placeholder="you@example.com" className="waitlist-input" value={email} onChange={e => setEmail(e.target.value)} />
                  <button type="submit" className="btn btn-dark btn-lg">Join waitlist <ArrowRight size={16} /></button>
                </form>
              )}
              <div className="waitlist-meta"><strong>{count}</strong> people in line · Fort Wayne first, expanding from there.</div>
              <div className="mech-bullets">
                <div><span className="mb-check"><Check size={12} /></span>No upfront commitment</div>
                <div><span className="mb-check"><Check size={12} /></span>Early-access pricing</div>
                <div><span className="mb-check"><Check size={12} /></span>Help shape the service</div>
              </div>
            </div>
            <div className="mech-hero-art">
              <div className="toolbox-art">
                <div className="ta-glow" />
                <div className="ta-grid">
                  {[
                    { label: "Service van", svg: <svg viewBox="0 0 60 60" className="ta-svg"><rect x="6" y="20" width="48" height="28" rx="3" fill="currentColor"/><rect x="10" y="8" width="44" height="14" rx="2" fill="currentColor" opacity="0.6"/><rect x="14" y="24" width="14" height="8" rx="1" fill="white"/><rect x="32" y="24" width="14" height="8" rx="1" fill="white"/><circle cx="18" cy="50" r="5" fill="white"/><circle cx="42" cy="50" r="5" fill="white"/><circle cx="18" cy="50" r="2" fill="currentColor"/><circle cx="42" cy="50" r="2" fill="currentColor"/></svg>, big: true },
                    { label: "Tools", svg: <svg viewBox="0 0 60 60" className="ta-svg"><path d="M20 14 a8 8 0 0 1 12 12 l16 16 -8 8 -16-16 a8 8 0 0 1 -12-12 z" fill="currentColor"/></svg> },
                    { label: "~30 min", svg: <svg viewBox="0 0 60 60" className="ta-svg"><circle cx="30" cy="30" r="20" fill="none" stroke="currentColor" strokeWidth="4"/><line x1="30" y1="14" x2="30" y2="30" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/><line x1="30" y1="30" x2="42" y2="36" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/></svg> },
                    { label: "Insured", svg: <svg viewBox="0 0 60 60" className="ta-svg"><path d="M30 8 c8 0 12 6 12 12 v6 h4 v22 h-32 v-22 h4 v-6 c0-6 4-12 12-12z" fill="none" stroke="currentColor" strokeWidth="3.5"/><circle cx="30" cy="38" r="3" fill="currentColor"/></svg> },
                    { label: "Diagnostics", svg: <svg viewBox="0 0 60 60" className="ta-svg"><path d="M14 38 l8-12 8 6 8-14 8 10" fill="none" stroke="currentColor" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"/><path d="M14 46 l32 0" stroke="currentColor" strokeWidth="3" strokeLinecap="round" opacity="0.4"/></svg> },
                    { label: "Battery", svg: <svg viewBox="0 0 60 60" className="ta-svg"><rect x="18" y="22" width="24" height="20" rx="2" fill="currentColor"/><rect x="22" y="18" width="6" height="6" fill="currentColor"/><rect x="32" y="18" width="6" height="6" fill="currentColor"/><text x="30" y="36" textAnchor="middle" fontSize="10" fontWeight="700" fill="white">12V</text></svg> },
                  ].map(({ label, svg, big }) => (
                    <div key={label} className={`ta-tile${big ? " big" : ""}`}>
                      {svg}
                      <div className="ta-lbl">{label}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Services */}
        <section id="services" className="section section-alt">
          <div className="container">
            <div className="section-head">
              <span className="section-kicker">Services at launch</span>
              <h2 className="section-title">Eight things we&apos;ll do in your driveway.</h2>
              <p className="section-sub">Starting with the most-requested. We&apos;ll add categories based on what waitlist members ask for first.</p>
            </div>
            <div className="mech-svc-grid">
              {services.map(s => (
                <div key={s.name} className="mech-svc">
                  <div className="mech-svc-head">
                    <span className="mech-svc-name">{s.name}</span>
                    <span className="mech-svc-price">${s.price}</span>
                  </div>
                  <div className="mech-svc-meta"><Clock size={12} /> {s.dur}</div>
                  <div className="mech-svc-body">{s.body}</div>
                </div>
              ))}
            </div>
            <div className="mech-svc-foot">
              <span>Don&apos;t see what you need?</span>
              <a href="#waitlist" className="link-arrow">Tell us in the waitlist form <ArrowRight size={14} /></a>
            </div>
          </div>
        </section>

        {/* How it'll work */}
        <section id="how" className="section">
          <div className="container">
            <div className="section-head">
              <span className="section-kicker">How it&apos;ll work</span>
              <h2 className="section-title">Same as detailing. Different toolkit.</h2>
              <p className="section-sub">If you&apos;ve used RayCarWash for a detail, mechanic bookings will feel identical — same app, same trust system, just deeper diagnostics.</p>
            </div>
            <ol className="mech-steps">
              {howSteps.map((s, i) => (
                <li key={s.t}>
                  <div className="ms-num">{String(i + 1).padStart(2, "0")}</div>
                  <div className="ms-body">
                    <div className="ms-t">{s.t}</div>
                    <div className="ms-b">{s.b}</div>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* For mechanics */}
        <section className="section dark-section">
          <div className="container mech-prov-grid">
            <div>
              <span className="section-kicker accent">For mechanics</span>
              <h2 className="section-title light">Are you the mechanic?</h2>
              <p className="section-sub light">We&apos;re recruiting our first 20 mobile mechanics in Fort Wayne. ASE-certified, your own van, ready to operate. Founding-member pricing on platform fees for the first six months.</p>
              <ul className="mech-req">
                {["ASE certification (any specialty)", "Own service van + portable lift", "2+ years mobile or shop experience", "Commercial liability insurance"].map(r => (
                  <li key={r}><span className="req-ic"><Check size={14} /></span>{r}</li>
                ))}
              </ul>
              <a href="#waitlist" className="btn btn-light btn-lg" style={{ marginTop: "32px" }}>Apply as founding mechanic <ArrowRight size={16} /></a>
            </div>
            <div className="founders-card">
              <div className="founders-tag">Founding mechanic perks</div>
              {[
                { l: "Platform fee · first 6 mo", v: <><s>15%</s><strong>0%</strong></> },
                { l: "Onboarding cost", v: <strong>Free</strong> },
                { l: "Equipment financing", v: <strong>Available</strong> },
                { l: "Guaranteed minimum", v: <strong>$1,200/wk</strong> },
                { l: "Spots remaining", v: <strong className="accent">12 / 20</strong>, total: true },
              ].map(({ l, v, total }) => (
                <div key={l} className={`founders-row${total ? " total" : ""}`}>
                  <span className="fr-l">{l}</span>
                  <span className="fr-v">{v}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        <FAQ title="Questions about the mechanic vertical." items={faqItems} />

        {/* Waitlist CTA */}
        <section id="waitlist" className="section final-cta">
          <div className="container">
            <div className="cta-card" style={{ gridTemplateColumns: "1fr" }}>
              <div className="cta-left" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "48px" }}>
                <div>
                  <span className="section-kicker accent">Get in line</span>
                  <h2 className="cta-title">First 500 people in, first 500 served.</h2>
                  <p className="cta-sub">Beta access in Q4. 20% off your first three appointments. We&apos;ll email you the moment your ZIP code goes live.</p>
                  {submitted ? (
                    <div style={{ padding: "16px 20px", borderRadius: "10px", background: "rgba(16,185,129,0.15)", color: "#6ee7b7", fontWeight: 600, fontSize: "15px", marginBottom: "12px" }}>
                      ✓ You&apos;re on the list!
                    </div>
                  ) : (
                    <form className="waitlist-form light" onSubmit={handleSubmit} style={{ marginBottom: "12px" }}>
                      <input type="email" required placeholder="you@example.com" className="waitlist-input light" value={email} onChange={e => setEmail(e.target.value)} />
                      <button type="submit" className="btn btn-light btn-lg">Join the waitlist <ArrowRight size={16} /></button>
                    </form>
                  )}
                  <div className="cta-footnotes">
                    <span>{count} people ahead of you</span>
                    <span>·</span>
                    <span>Avg wait: 4 weeks</span>
                  </div>
                </div>
                <div className="rollout">
                  <div className="rollout-t">Rollout plan</div>
                  {rollout.map(r => (
                    <div key={r.q} className={`rollout-row${r.done ? " done" : ""}${r.active ? " active" : ""}`}>
                      <span className="rr-q">{r.q}</span>
                      <span className="rr-l">{r.l}</span>
                    </div>
                  ))}
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
