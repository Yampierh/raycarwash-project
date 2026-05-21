import { Phone, Car, Droplets, Star } from "lucide-react";

interface Props { audience: "client" | "detailer"; }

const clientSteps = [
  { t: "Book in seconds", b: "Pick a service, add your vehicle, choose a time. Get an instant flat quote." },
  { t: "We come to you", b: "A nearby vetted detailer is dispatched. Track them live in the app." },
  { t: "Work happens", b: "They bring water, power, and pro products. You don't lift a finger." },
  { t: "Pay & review", b: "Pay securely after the job. Rate your detailer in two taps." },
];
const detailerSteps = [
  { t: "Apply", b: "Tell us about your experience and the services you offer." },
  { t: "Verify", b: "Identity, background check, and portfolio review — all in-app." },
  { t: "Accept jobs", b: "Set your area. Get matched. Decline anything that doesn't fit." },
  { t: "Get paid same day", b: "Funds hit your bank the day you mark the job complete." },
];
const icons = [Phone, Car, Droplets, Star];

export default function HowItWorks({ audience }: Props) {
  const isClient = audience === "client";
  const steps = isClient ? clientSteps : detailerSteps;

  return (
    <section id="how" className="section">
      <div className="container">
        <div className="section-head">
          <span className="section-kicker">How it works</span>
          <h2 className="section-title">{isClient ? "Simple. Fast. Done right." : "Onboard in a week. Earn the next."}</h2>
          <p className="section-sub">
            {isClient
              ? "From booking to a clean car, everything is built around your time."
              : "We handle the admin so you spend your hours on the work."}
          </p>
        </div>
        <ol className="how-grid">
          {steps.map((s, i) => {
            const Icon = icons[i];
            return (
              <li key={s.t} className="how-card">
                <div className="how-card-top">
                  <span className="how-ic"><Icon size={20} /></span>
                  <span className="how-num">{String(i + 1).padStart(2, "0")}</span>
                </div>
                <h3 className="how-title">{s.t}</h3>
                <p className="how-body">{s.b}</p>
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}
