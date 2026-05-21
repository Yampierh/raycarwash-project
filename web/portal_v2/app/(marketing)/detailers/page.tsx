"use client";
import { useState } from "react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import FAQ from "@/components/sections/FAQ";
import { ArrowRight, Check, Calendar, Wallet, Shield, Wrench } from "lucide-react";

const faqItems = [
  { q: "How much does it really cost to join?", a: "Nothing up front. We deduct a 15% platform fee from each completed job — that covers payment processing, insurance coverage during service, dispatch, support, and marketing. You keep the rest, including 100% of tips." },
  { q: "Do I need to be a full-time detailer?", a: "No. About 30% of our detailers work part-time or weekends only. Set your hours and we'll route jobs to fit." },
  { q: "Can I bring my existing clients?", a: "Yes. We have a referral code system — anyone you refer who books through the app gets $20 off and you get a $40 bonus on top of your usual cut." },
  { q: "What about insurance?", a: "We carry commercial general liability that covers damage caused by you during a service. Your personal auto policy still covers transit. We strongly recommend you also carry your own business liability." },
  { q: "How fast do I actually get paid?", a: "Funds initiate transfer the same day a job is marked complete. Most banks post within 1–2 business days; instant payouts (eligible debit cards) hit in minutes." },
  { q: "Can I decline jobs?", a: "Always. Decline rate doesn't affect your standing as long as you don't ghost. The app shows you the full job details before you accept." },
  { q: "What happens if a customer disputes the work?", a: "We use the before/after photos you captured, the timeline of the job, and the customer's complaint. Most disputes are resolved with a re-service rather than a refund." },
];

const days = [
  { d: "Mon", date: "Jun 3", jobs: [{ t: "9:00", svc: "Exterior wash · M3", pay: 49 }, { t: "11:30", svc: "Full detail · Civic", pay: 149 }, { t: "3:00", svc: "Interior · F-150", pay: 89 }] },
  { d: "Tue", date: "Jun 4", jobs: [{ t: "10:00", svc: "Full detail · CX-5", pay: 149 }, { t: "2:00", svc: "Exterior · Camry", pay: 49 }] },
  { d: "Wed", date: "Jun 5", jobs: [{ t: "9:00", svc: "Interior · Pilot", pay: 89 }, { t: "1:00", svc: "Full detail · Wrangler", pay: 189 }, { t: "4:30", svc: "Ext + interior · Sienna", pay: 169 }] },
  { d: "Thu", date: "Jun 6", off: true },
  { d: "Fri", date: "Jun 7", jobs: [{ t: "8:30", svc: "Full detail · Model Y", pay: 159 }, { t: "12:00", svc: "Full detail · Tacoma", pay: 189 }, { t: "4:00", svc: "Interior · Outback", pay: 89 }] },
  { d: "Sat", date: "Jun 8", jobs: [{ t: "9:00", svc: "Full detail · CR-V", pay: 149 }, { t: "1:00", svc: "Full detail · Q5", pay: 179 }] },
  { d: "Sun", date: "Jun 9", off: true },
];

const reqs = [
  "Own vehicle with cargo space for equipment",
  "Pro-grade detailing tools and products",
  "Smartphone with data plan (iOS 16+ or Android 10+)",
  "Valid driver's license & auto insurance",
  "Pass background check + identity verification",
  "Stripe-eligible bank account for payouts",
];

const howSteps = [
  { t: "Apply", b: "Tell us about your experience, your gear, and the services you offer." },
  { t: "Verify", b: "Identity verification via Stripe + background check. Usually under 48 hours." },
  { t: "Setup", b: "Set your service area, hours, and per-service prices. We provide starting templates." },
  { t: "Earn", b: "Jobs route to you automatically. Get paid the day you complete each one." },
];

const testimonials = [
  { quote: "I left my dealership job in March. By July I was making more, and I'm home for dinner every night.", name: "Marcus T.", meta: "Detailer · 312 jobs · ★ 4.9" },
  { quote: "The app routes me to jobs I would have spent days finding on Facebook. I just show up and work.", name: "Trey W.", meta: "Detailer · 198 jobs · ★ 4.8" },
  { quote: "Same-day payouts changed everything. I don't have to wait two weeks for an invoice to clear.", name: "Jamal R.", meta: "Detailer · 421 jobs · ★ 5.0" },
];

const tools = [
  { title: "Smart job dispatcher", body: "Get matched only to jobs in your service area and price range. Auto-decline filters keep junk off your screen." },
  { title: "Route + day planner", body: "See every job for the day on one map. We optimize the order so you spend less time driving and more time billing." },
  { title: "Before/after capture", body: "Snap photos as you work. We attach them to the receipt and the dispute audit trail — no he-said-she-said." },
];

export default function DetailersPage() {
  const [jobs, setJobs] = useState(12);
  const [avg, setAvg] = useState(140);
  const [workDays, setWorkDays] = useState(5);

  const gross = jobs * avg;
  const net = gross * 0.85;
  const monthly = Math.round(net * 4.33);
  const yearly = Math.round(net * 52);
  const perDay = Math.round(net / workDays);
  const fmt = (n: number) => "$" + Math.round(n).toLocaleString();

  const weekTotal = days.reduce((s, d) => s + ((d as any).jobs?.reduce((a: number, j: any) => a + j.pay, 0) || 0), 0);
  const jobsCount = days.reduce((s, d) => s + ((d as any).jobs?.length || 0), 0);

  return (
    <>
      <Navbar page="detailers" />
      <main>
        {/* Hero */}
        <section id="top" className="det-hero">
          <div className="hero-grid" aria-hidden />
          <div className="container det-hero-inner">
            <div className="det-hero-text">
              <div className="hero-kicker">
                <span className="kicker-dot" />
                <span>Detail with RayCarWash · Fort Wayne, IN</span>
              </div>
              <h1 className="det-hero-h1">Your hands.<br /><span className="hero-h1-accent">Our pipeline.</span></h1>
              <p className="det-hero-sub">Stop spending Sundays running ads. Plug into a steady flow of vetted clients, set your own schedule, and get paid the day you finish the job.</p>
              <div className="hero-ctas">
                <Link href="/signup" className="btn btn-accent btn-lg">Start application <ArrowRight size={16} /></Link>
                <a href="#earnings" className="btn btn-outline btn-lg">See earnings</a>
              </div>
              <div className="det-trust-strip">
                <div><strong>4 min</strong><span>average application</span></div>
                <div><strong>48 hrs</strong><span>decision turnaround</span></div>
                <div><strong>Same day</strong><span>payouts to bank</span></div>
              </div>
            </div>
            <div className="det-hero-card">
              <div className="payout-sticker">
                <div className="ps-eyebrow muted">Last 7 days · Marcus T.</div>
                <div className="payout-amt"><span className="dollar">$</span>2,148<span className="cents">.50</span></div>
                <div className="payout-meta"><span className="payout-up">▲ +18%</span><span>vs prior week</span></div>
                <div className="payout-row"><span>Jobs completed</span><span className="b">14</span></div>
                <div className="payout-row"><span>Avg per job</span><span className="b">$153.46</span></div>
                <div className="payout-row"><span>Tips earned</span><span className="b">$248</span></div>
                <div className="payout-row total"><span>Cash out now</span><span className="b accent">$412.00 →</span></div>
                <div className="payout-mini-bars">
                  {[40, 65, 30, 80, 55, 90, 70].map((h, i) => (
                    <div key={i} className="pmb" style={{ height: `${h}%` }} />
                  ))}
                </div>
                <div className="payout-mini-labels">
                  {["M","T","W","T","F","S","S"].map((d, i) => <span key={i}>{d}</span>)}
                </div>
              </div>
              <div className="det-hero-orbit">
                <div className="orbit-chip">★ 4.9 rating</div>
                <div className="orbit-chip">312 jobs</div>
                <div className="orbit-chip">98% on-time</div>
              </div>
            </div>
          </div>
        </section>

        {/* Earnings Calculator */}
        <section id="earnings" className="section section-alt">
          <div className="container">
            <div className="section-head split">
              <div>
                <span className="section-kicker">Earnings calculator</span>
                <h2 className="section-title">See what your week looks like.</h2>
                <p className="section-sub">Drag the sliders. We do the math — including our 15% platform fee, so the take-home is already net.</p>
              </div>
            </div>
            <div className="calc-grid">
              <div className="calc-controls">
                {[
                  { label: "Jobs per week", value: jobs, min: 3, max: 25, step: 1, fmt: (v: number) => String(v), set: setJobs },
                  { label: "Average ticket", value: avg, min: 49, max: 299, step: 1, fmt: (v: number) => `$${v}`, set: setAvg },
                  { label: "Days worked", value: workDays, min: 1, max: 7, step: 1, fmt: (v: number) => `${v} / week`, set: setWorkDays },
                ].map(({ label, value, min, max, step, fmt: f, set }) => (
                  <div key={label} className="calc-control">
                    <div className="calc-label">
                      <span>{label}</span>
                      <span className="calc-val">{f(value)}</span>
                    </div>
                    <input
                      type="range" min={min} max={max} step={step} value={value}
                      onChange={e => set(+e.target.value)}
                      className="range"
                      style={{ width: "100%", accentColor: "var(--brand)" }}
                    />
                    <div className="range-track"><span>{f(min)}</span><span>{f(max)}</span></div>
                  </div>
                ))}
                <div className="calc-fineprint"><strong>Platform fee:</strong> 15% covers payment processing, insurance, dispatch, customer support, and marketing.</div>
              </div>
              <div className="calc-output">
                <div className="calc-big">
                  <div className="calc-big-lbl">Net per week</div>
                  <div className="calc-big-val">{fmt(net)}</div>
                  <div className="calc-big-sub">Take-home · after 15% platform fee</div>
                </div>
                <div className="calc-meta">
                  <div><div className="calc-meta-l">Gross weekly</div><div className="calc-meta-v">{fmt(gross)}</div></div>
                  <div><div className="calc-meta-l">Per day</div><div className="calc-meta-v">{fmt(perDay)}</div></div>
                  <div><div className="calc-meta-l">Monthly</div><div className="calc-meta-v">{fmt(monthly)}</div></div>
                  <div><div className="calc-meta-l">Yearly</div><div className="calc-meta-v">{fmt(yearly)}</div></div>
                </div>
                <div className="calc-bench">
                  <div className="calc-bench-row"><span>Median Fort Wayne detailer</span><span>$1,840 / wk</span></div>
                  <div className="calc-bench-row"><span>Top quartile</span><span>$2,720 / wk</span></div>
                  <div className="calc-bench-row hi"><span>Top 10%</span><span>$3,400+ / wk</span></div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Week in life */}
        <section id="week" className="section">
          <div className="container">
            <div className="section-head split">
              <div>
                <span className="section-kicker">A real week</span>
                <h2 className="section-title">Marcus&apos;s week in June.</h2>
                <p className="section-sub">Sample schedule from one of our top 20% detailers. Two days off. Thirteen jobs. No cold calls.</p>
              </div>
              <div className="week-total">
                <div className="week-total-lbl">Week total</div>
                <div className="week-total-amt">${weekTotal.toLocaleString()}</div>
                <div className="week-total-sub">{jobsCount} jobs · 5 days worked</div>
              </div>
            </div>
            <div className="week-grid">
              {days.map(d => (
                <div key={d.d} className={`week-day${(d as any).off ? " off" : ""}`}>
                  <div className="week-day-head">
                    <span className="week-d">{d.d}</span>
                    <span className="week-date">{d.date}</span>
                  </div>
                  {(d as any).off ? (
                    <div className="week-off"><span className="off-tag">Off</span><span className="off-meta">Family · errands</span></div>
                  ) : (
                    <>
                      <div className="week-jobs">
                        {(d as any).jobs.map((j: any, i: number) => (
                          <div key={i} className="week-job">
                            <span className="wj-t">{j.t}</span>
                            <span className="wj-svc">{j.svc}</span>
                            <span className="wj-pay">${j.pay}</span>
                          </div>
                        ))}
                      </div>
                      <div className="week-day-foot">
                        <span>${(d as any).jobs.reduce((a: number, j: any) => a + j.pay, 0)}</span>
                        <span className="wf-sub">{(d as any).jobs.length} jobs</span>
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Tools */}
        <section id="tools" className="section dark-section">
          <div className="container">
            <div className="section-head">
              <span className="section-kicker accent">Tools you get</span>
              <h2 className="section-title light">Built by people who&apos;ve held a clay bar.</h2>
              <p className="section-sub light">The detailer app isn&apos;t a re-skin of the rider app. It&apos;s a separate workflow built for the work.</p>
            </div>
            <div className="tools-grid">
              {tools.map(t => (
                <div key={t.title} className="tool-card">
                  <div className="tool-phone-wrap">
                    <div className="tool-phone">
                      <div className="tool-phone-notch" />
                      <div className="tool-phone-screen">
                        <div className="tp-head">
                          <span className="tp-eb">{t.title.split(" ").slice(0, 2).join(" ")}</span>
                          <span className="tp-pill">Live</span>
                        </div>
                        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "6px" }}>
                          {[1, 2, 3].map(i => (
                            <div key={i} style={{ height: "32px", borderRadius: "6px", background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.08)" }} />
                          ))}
                        </div>
                        <div className="tp-foot">{t.title}</div>
                      </div>
                    </div>
                  </div>
                  <div className="tool-body">
                    <h3 className="tool-title">{t.title}</h3>
                    <p className="tool-text">{t.body}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Requirements */}
        <section id="requirements" className="section">
          <div className="container">
            <div className="req-grid">
              <div className="req-left">
                <span className="section-kicker">Requirements</span>
                <h2 className="section-title">What you&apos;ll need to get started.</h2>
                <p className="section-sub">We maintain high standards so every client experience is consistent. Here&apos;s the minimum bar.</p>
                <ul className="req-list">
                  {reqs.map(r => (
                    <li key={r}><span className="req-ic"><Check size={14} /></span><span>{r}</span></li>
                  ))}
                </ul>
              </div>
              <div className="req-right">
                <span className="section-kicker">How to start</span>
                <h3 className="req-h3">Four steps to your first paycheck.</h3>
                <ol className="req-steps">
                  {howSteps.map((s, i) => (
                    <li key={s.t}>
                      <span className="req-step-num">{String(i + 1).padStart(2, "0")}</span>
                      <div><div className="req-step-t">{s.t}</div><div className="req-step-b">{s.b}</div></div>
                    </li>
                  ))}
                </ol>
              </div>
            </div>
          </div>
        </section>

        {/* Testimonials */}
        <section className="section section-alt">
          <div className="container">
            <div className="section-head">
              <span className="section-kicker">From detailers</span>
              <h2 className="section-title">People who&apos;d never go back.</h2>
            </div>
            <div className="dt-grid">
              {testimonials.map(t => (
                <figure key={t.name} className="dt-card">
                  <div className="dt-quote">&ldquo;{t.quote}&rdquo;</div>
                  <figcaption>
                    <div className="dt-avatar" />
                    <div><div className="dt-name">{t.name}</div><div className="dt-meta">{t.meta}</div></div>
                  </figcaption>
                </figure>
              ))}
            </div>
          </div>
        </section>

        <FAQ title="Detailer questions, answered." items={faqItems} />

        {/* Apply CTA */}
        <section id="apply" className="section final-cta">
          <div className="container">
            <div className="cta-card">
              <div className="cta-left">
                <span className="section-kicker accent">Become a detailer</span>
                <h2 className="cta-title">Ready to apply?</h2>
                <p className="cta-sub">It takes about 4 minutes. We&apos;ll get back to you within 48 hours with a decision.</p>
                <div className="cta-actions">
                  <Link href="/signup" className="btn btn-light btn-lg">Start application <ArrowRight size={16} /></Link>
                  <Link href="/" className="btn btn-light-outline btn-lg">Back to home</Link>
                </div>
                <div className="cta-footnotes">
                  <span>✓ No upfront cost</span>
                  <span>✓ Cancel anytime</span>
                  <span>✓ 15% platform fee · keep 100% of tips</span>
                </div>
              </div>
              <div className="cta-right">
                <div className="apply-preview">
                  <div className="ap-step done">1 · Personal info</div>
                  <div className="ap-step done">2 · Identity verification</div>
                  <div className="ap-step active">3 · Services & pricing</div>
                  <div className="ap-step">4 · Service area</div>
                  <div className="ap-progress"><div className="ap-progress-fill" style={{ width: "62%" }} /></div>
                  <div className="ap-progress-meta">62% complete · ~2 min remaining</div>
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
