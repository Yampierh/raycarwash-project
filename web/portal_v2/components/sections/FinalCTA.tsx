import Link from "next/link";
import { Apple, Smartphone, ArrowRight } from "lucide-react";

interface Props { audience: "client" | "detailer"; }

export default function FinalCTA({ audience }: Props) {
  const isClient = audience === "client";
  return (
    <section className="section final-cta">
      <div className="container">
        <div className="cta-card">
          <div className="cta-left">
            <span className="section-kicker accent">{isClient ? "Get the app" : "Become a detailer"}</span>
            <h2 className="cta-title">{isClient ? "Ready for a cleaner car?" : "Ready to start earning?"}</h2>
            <p className="cta-sub">
              {isClient
                ? "Download RayCarWash and book your first detail in under two minutes."
                : "Apply in 4 minutes. Get a decision in 48 hours. Start earning the next."}
            </p>
            <div className="cta-actions">
              {isClient ? (
                <>
                  <a href={process.env.NEXT_PUBLIC_APPSTORE_URL || "#"} className="btn btn-light btn-lg"><Apple size={18} /> App Store</a>
                  <a href={process.env.NEXT_PUBLIC_PLAYSTORE_URL || "#"} className="btn btn-light-outline btn-lg"><Smartphone size={18} /> Google Play</a>
                </>
              ) : (
                <Link href="/signup" className="btn btn-light btn-lg">Apply now <ArrowRight size={16} /></Link>
              )}
            </div>
          </div>
          <div className="cta-right">
            <div className="cta-mosaic">
              <div className="cta-photo cta-photo-main"><span className="photo-label">Hero photo</span></div>
              <div className="cta-photo cta-photo-b"><span className="photo-label">Before</span></div>
              <div className="cta-photo cta-photo-a"><span className="photo-label">After</span></div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
