"use client";
import { useState } from "react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import Hero from "@/components/sections/Hero";
import TrustStrip from "@/components/sections/TrustStrip";
import HowItWorks from "@/components/sections/HowItWorks";
import Services from "@/components/sections/Services";
import Coverage from "@/components/sections/Coverage";
import ForDetailers from "@/components/sections/ForDetailers";
import Testimonials from "@/components/sections/Testimonials";
import FAQ from "@/components/sections/FAQ";
import FinalCTA from "@/components/sections/FinalCTA";

export default function LandingPage() {
  const [audience, setAudience] = useState<"client" | "detailer">("client");

  return (
    <>
      <Navbar page="landing" audience={audience} onAudienceChange={setAudience} />
      <main>
        <Hero audience={audience} onAudienceChange={setAudience} />
        <TrustStrip />
        <HowItWorks audience={audience} />
        <Services />
        <Coverage />
        <ForDetailers />
        <Testimonials />
        <FAQ />
        <FinalCTA audience={audience} />
      </main>
      <Footer />
    </>
  );
}
