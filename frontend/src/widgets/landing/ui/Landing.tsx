import LandingNavbar from "./LandingNavbar";
import Hero from "./Hero";
import StatBand from "./StatBand";
import ResultCard from "./ResultCard";
import MethodCards from "./MethodCards";
import FeatureMockups from "./FeatureMockups";
import CloudCTA from "./CloudCTA";
import FAQ from "./FAQ";
import LandingFooter from "./LandingFooter";

export default function Landing() {
  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900">
      <LandingNavbar />
      <main>
        <Hero />
        <StatBand />
        <ResultCard />
        <MethodCards />
        <FeatureMockups />
        <CloudCTA />
        <FAQ />
      </main>
      <LandingFooter />
    </div>
  );
}
