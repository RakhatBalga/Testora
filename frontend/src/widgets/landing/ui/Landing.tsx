import LandingNavbar from "./LandingNavbar";
import Hero from "./Hero";
import Features from "./Features";
import Showcase from "./Showcase";
import Statistics from "./Statistics";
import FAQ from "./FAQ";
import CTA from "./CTA";
import LandingFooter from "./LandingFooter";

export default function Landing() {
  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900">
      <LandingNavbar />
      <main>
        <Hero />
        <Features />
        <Showcase />
        <Statistics />
        <FAQ />
        <CTA />
      </main>
      <LandingFooter />
    </div>
  );
}
