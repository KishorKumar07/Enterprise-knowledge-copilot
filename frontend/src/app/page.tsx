import { MarketingNav } from "@/components/layout/marketing-nav";
import { HeroSection } from "@/components/layout/hero-section";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col">
      <MarketingNav />
      <main className="flex-1">
        <HeroSection />
      </main>
    </div>
  );
}
