"use client";
import { useState } from "react";
import { Plus } from "lucide-react";

interface FAQItem { q: string; a: string; }

const defaultItems: FAQItem[] = [
  { q: "What area do you serve?", a: "Fort Wayne, IN and surrounding suburbs (Aboite, New Haven, Huntertown, Leo-Cedarville). We're expanding — drop us a line if you want us in your neighborhood." },
  { q: "Do detailers bring their own water and power?", a: "Yes. Every detailer arrives self-contained: water tanks, generators, and pro-grade products. You don't need to lift a finger." },
  { q: "How are detailers vetted?", a: "Identity verification, background check, and portfolio review before they take any job. We re-verify annually." },
  { q: "Is my vehicle insured during service?", a: "Yes. We carry commercial coverage for damage caused by the detailer during a service." },
  { q: "How does payment work?", a: "You get a flat quote up front. We authorize the card when you book and only charge once the job is complete." },
  { q: "What if I'm not satisfied?", a: "Open a dispute in the app within 48 hours. If the work doesn't meet the standard, we'll re-do it or refund you." },
  { q: "Can I tip my detailer?", a: "Absolutely — 100% of every tip goes to the detailer." },
  { q: "Do you offer recurring service?", a: "Yes. Save your vehicle and detailer to schedule weekly, bi-weekly, or monthly cleans with one tap." },
];

interface Props {
  title?: string;
  items?: FAQItem[];
}

export default function FAQ({ title = "Questions, answered.", items = defaultItems }: Props) {
  const [open, setOpen] = useState<number>(0);

  return (
    <section id="faq" className="section section-alt">
      <div className="container faq-container">
        <div className="section-head centered">
          <span className="section-kicker">FAQ</span>
          <h2 className="section-title">{title}</h2>
        </div>
        <div className="faq-list">
          {items.map((it, i) => (
            <details
              key={it.q}
              open={open === i}
              onClick={e => { e.preventDefault(); setOpen(open === i ? -1 : i); }}
              className={`faq-item${open === i ? " open" : ""}`}
            >
              <summary>
                <span>{it.q}</span>
                <span className="faq-ic"><Plus size={16} /></span>
              </summary>
              <div className="faq-a">{it.a}</div>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
