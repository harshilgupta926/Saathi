"use client";

import Link from "next/link";
import { ArrowRight, CheckCircle2, CloudRain, Database, Mic2, ShieldCheck, Wheat, type LucideIcon } from "lucide-react";
import SaathiHero from "../components/SaathiHero";
import "../components/SaathiHero.css";

type Capability = { icon: LucideIcon; title: string; text: string };
type FlowStep = { number: string; title: string; text: string; icon: LucideIcon };

const capabilities: Capability[] = [
  { icon: Wheat, title: "Mandi prices", text: "Ask for a commodity and market. Saathi checks the available government market data before answering." },
  { icon: CloudRain, title: "Weather", text: "Get a local weather check alongside a farming question, with the source kept visible." },
  { icon: ShieldCheck, title: "Government schemes", text: "Understand schemes and next steps without pretending an eligibility decision has been verified." },
];

const flowSteps: FlowStep[] = [
  { number: "01", title: "You ask", text: "Speak or type naturally.", icon: Mic2 },
  { number: "02", title: "Saathi understands", text: "Language, intent and entities.", icon: CheckCircle2 },
  { number: "03", title: "Sources are checked", text: "Specialist tools return evidence.", icon: Database },
  { number: "04", title: "You get the answer", text: "Grounded response with provenance.", icon: ShieldCheck },
];

export default function Home() {
  return (
    <main className="product-home">
      <SaathiHero />

      <section className="product-proof" id="how-it-works">
        <div className="product-wrap">
          <div className="product-section-intro">
            <span className="product-kicker"><span /> HOW SAATHI WORKS</span>
            <h2>From a natural question to a useful answer.</h2>
            <p>Saathi separates understanding from factual verification. The assistant can interpret your request, but specialist tools supply the facts.</p>
          </div>

          <div className="product-flow">
            {flowSteps.map(({ number, title, text, icon: Icon }) => (
              <article className="product-flow-card" key={number}>
                <span className="flow-number">{number}</span>
                <Icon size={19} />
                <h3>{title}</h3>
                <p>{text}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="product-capabilities">
        <div className="product-wrap">
          <div className="product-section-heading">
            <div>
              <span className="product-kicker"><span /> USE SAATHI FOR</span>
              <h2>Useful help, not a generic chat box.</h2>
            </div>
            <Link href="/dashboard" className="product-inline-link">Open the app <ArrowRight size={14} /></Link>
          </div>

          <div className="capability-grid">
            {capabilities.map(({ icon: Icon, title, text }) => (
              <article className="capability-card" key={title}>
                <div className="capability-icon"><Icon size={18} /></div>
                <h3>{title}</h3>
                <p>{text}</p>
                <Link href="/dashboard">Try it <ArrowRight size={13} /></Link>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="product-trust">
        <div className="product-wrap trust-panel">
          <div>
            <span className="product-kicker"><span /> WHEN SAATHI CANNOT VERIFY</span>
            <h2>It tells you what is missing.</h2>
          </div>
          <p>Saathi does not fill missing market, location, or source information with a guess. It asks for clarification or explains that a verified answer is unavailable.</p>
        </div>
      </section>

      <footer className="product-footer">
        <div className="product-wrap">
          <Link href="/" className="product-brand">saathi<span>.</span></Link>
          <span>Hindi · Hinglish · verified assistance</span>
          <Link href="/dashboard">Open Saathi <ArrowRight size={13} /></Link>
        </div>
      </footer>
    </main>
  );
}
