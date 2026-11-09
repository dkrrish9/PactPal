"use client";
import Navbar from "@/components/Navbar";
import HeroSection from "@/components/HeroSection";
import TrustedByStrip from "@/components/TrustedByStrip";
import BenefitCards from "@/components/BenefitCards";
import HowItWorks from "@/components/HowItWorks";
import AIRefereeShowcase from "@/components/AIRefereeShowcase";
import GanttShowcase from "@/components/GanttShowcase";
import BentoGrid from "@/components/BentoGrid";
import CategoryCloud from "@/components/CategoryCloud";
import SocialProof from "@/components/SocialProof";
import DualCTAFinale from "@/components/DualCTAFinale";
import Footer from "@/components/Footer";

export default function HomePage() {
  return (
    <main className="min-h-screen" style={{ background: "var(--color-bg)" }}>
      <Navbar />
      <HeroSection />
      <TrustedByStrip />
      <BenefitCards />
      <HowItWorks />
      <AIRefereeShowcase />
      <GanttShowcase />
      <BentoGrid />
      <CategoryCloud />
      <SocialProof />
      <DualCTAFinale />
      <Footer />
    </main>
  );
}
