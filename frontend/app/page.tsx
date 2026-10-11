"use client";

import Link from "next/link";
import { useRef } from "react";
import "./home.css";
import AcidSquares from "../components/AcidSquares";
import Stepper, { Step } from "../components/Stepper";
import { motion } from "motion/react";
import { ArrowRight, ArrowUpRight, AudioLines, Check, CheckCircle2, CloudRain, Database, Languages, Mic2, PhoneCall, ShieldCheck, Wheat } from "lucide-react";

const capabilities = [
  { title: "Mandi prices", prompt: "“Sonipat mein गेहूं ka mandi bhav?”", detail: "Government market observations, matched to the requested place and crop.", icon: Wheat },
  { title: "Weather", prompt: "“Kal baarish hogi?”", detail: "Forecast data with the location and retrieval time shown alongside the answer.", icon: CloudRain },
  { title: "Government schemes", prompt: "“Kisan yojana kaise milegi?”", detail: "Plain-language guidance without pretending an eligibility decision was verified.", icon: ShieldCheck },
  { title: "Human help", prompt: "“Mujhe kisi insaan se baat karni hai.”", detail: "The assistant stops automating and moves toward human support.", icon: PhoneCall },
] as const;

const proof = [
  [Languages, "Hindi / Hinglish", "Speak naturally instead of translating your question first."],
  [Database, "Source-backed", "Specialist data stays outside the language model."],
  [ShieldCheck, "Honest by default", "Missing or ambiguous information becomes a clarification, not a guess."],
] as const;

export default function Home() {
  const heroRef = useRef<HTMLDivElement | null>(null);
  const moveGlow = (event: React.PointerEvent<HTMLDivElement>) => {
    const node = heroRef.current;
    if (!node) return;
    const rect = node.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 100;
    const y = ((event.clientY - rect.top) / rect.height) * 100;
    node.style.setProperty("--mx", String(x) + "%");
    node.style.setProperty("--my", String(y) + "%");
  };

  return (
    <main>
      <div className="acid-background" aria-hidden="true"><AcidSquares color1="#183d32" color2="#d9a64b" color3="#fff8e8" detail="low" speed={0.22} waveDepth={0.45} zoom={1.15} density={9} glow={0.75} exposure={3300} spread={0.32} opacity={0.11} mouseInteraction mouseStrength={0.04} mouseRadius={0.28} grain={false} /></div>
      <section className="product-hero wrap" ref={heroRef} onPointerMove={moveGlow}>
        <div className="hero-glow" aria-hidden="true" />
        <div className="hero-intro">
          <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55 }}>
            <div className="eyebrow"><span className="eyebrow-line" /> VOICE-FIRST · HINDI / HINGLISH</div>
            <h1>Ask naturally.<br /><em>Saathi checks.</em></h1>
            <p className="hero-text">A practical voice assistant for everyday questions. Speak in Hindi or Hinglish, let Saathi find the right specialist source, and see what the answer is based on.</p>
            <div className="hero-actions"><Link className="button button-dark" href="/dashboard">Try Saathi <ArrowRight size={17} /></Link><a className="text-link" href="#capabilities">Explore what it can do <ArrowUpRight size={15} /></a></div>
            <div className="hero-meta"><span><Check size={14} /> Voice input</span><span><Check size={14} /> Source evidence</span><span><Check size={14} /> Human fallback</span></div>
          </motion.div>
        </div>
        <div className="hero-bento" aria-label="Saathi product preview">
          <motion.article className="bento-card bento-main" initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.08 }}>
            <div className="bento-topline"><span className="bento-kicker"><Mic2 size={13} /> YOU SAY</span><span className="bento-status"><i /> Ready</span></div>
            <p className="bento-question">“Sonipat mein गेहूं ka mandi bhav kya hai? Kal baarish ka chance bhi batao.”</p>
            <div className="bento-chain"><span>Understand</span><ArrowRight size={13} /><span>Check sources</span><ArrowRight size={13} /><span>Answer</span></div>
            <div className="bento-answer"><CheckCircle2 size={18} /><div><strong>Verified before speaking</strong><span>Market data + weather forecast are attached to the response.</span></div></div>
          </motion.article>
          <motion.article className="bento-card bento-source" initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.16 }}>
            <span className="bento-kicker"><Database size={13} /> EVIDENCE</span><strong>Government market data</strong><small>AGMARKNET / OGD</small><div className="source-meter"><span /><span /><span /></div><p>Retrieved with provenance, not model memory.</p>
          </motion.article>
          <motion.article className="bento-card bento-weather" initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.22 }}>
            <CloudRain size={19} /><div><strong>Weather</strong><small>Open-Meteo forecast</small></div><span className="bento-arrow"><ArrowUpRight size={14} /></span>
          </motion.article>
          <motion.article className="bento-card bento-human" initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.28 }}>
            <PhoneCall size={18} /><div><strong>Need a person?</strong><small>Saathi can stop and escalate.</small></div>
          </motion.article>
        </div>
      </section>
      <section className="proof-strip" aria-label="Product principles"><div className="wrap proof-grid">{proof.map(([Icon, label, text]) => <article className="proof-card" key={label}><div className="proof-icon"><Icon size={18} /></div><div><strong>{label}</strong><p>{text}</p></div></article>)}</div></section>
      <section className="difference wrap" id="capabilities">
        <div className="section-heading"><div className="eyebrow"><span className="eyebrow-line" /> WHAT YOU CAN ASK</div><h2>Useful answers,<br /><em>with a source.</em></h2><p>Saathi is deliberately narrow in the prototype: a few real workflows that can show their evidence clearly are better than a chatbot that claims everything.</p></div>
        <div className="scenario-grid product-capability-grid">{capabilities.map(({ icon: Icon, title, prompt, detail }, index) => <motion.article className="scenario-card" key={title} initial={{ opacity: 0, y: 14 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-40px" }} transition={{ delay: index * 0.06 }}><div className="scenario-icon"><Icon size={19} /></div><span className="scenario-label">{title}</span><h3>{prompt}</h3><p>{detail}</p></motion.article>)}</div>
      </section>
      <section className="how-section wrap" aria-labelledby="how-title">
        <div className="section-heading"><div className="eyebrow"><span className="eyebrow-line" /> HOW IT WORKS</div><h2 id="how-title">From speech to<br /><em>verified response.</em></h2><p>One visible path keeps the prototype understandable: listen, understand, verify, then respond.</p></div>
        <Stepper
          initialStep={1}
          onStepChange={() => undefined}
          backButtonText="Back"
          nextButtonText="Next"
          renderStepIndicator={({ step, currentStep, onStepClick }: { step: number; currentStep: number; onStepClick: (step: number) => void }) => (
            <button
              type="button"
              className={`step-indicator ${currentStep === step ? "active" : currentStep > step ? "complete" : "inactive"}`}
              aria-current={currentStep === step ? "step" : undefined}
              aria-label={`Go to step ${step}`}
              onClick={() => onStepClick(step)}
            >
              {step}
            </button>
          )}
        >
          <Step><h3>Listen</h3><p>Browser microphone input is converted to speech text through the configured speech provider.</p></Step>
          <Step><h3>Understand</h3><p>Saathi identifies the user’s intent and extracts the entities a specialist workflow needs.</p></Step>
          <Step><h3>Verify</h3><p>Only declared tools can supply factual values such as mandi observations or weather forecasts.</p></Step>
          <Step><h3>Respond safely</h3><p>The answer carries provenance. If the system cannot verify the request, it says so.</p></Step>
        </Stepper>
      </section>
      <section className="architecture" aria-labelledby="architecture-title"><div className="wrap architecture-inner">
        <div className="architecture-copy"><div className="eyebrow"><span className="eyebrow-line" /> THE PRODUCT RULE</div><h2 id="architecture-title">The model can reason.<br /><em>It cannot make up the facts.</em></h2><p>Saathi keeps reasoning and verification separate. Intent can choose a capability; the capability returns the evidence; the response is generated from that evidence.</p><Link className="button button-light" href="/dashboard">Open the working prototype <ArrowUpRight size={16} /></Link></div>
        <div className="architecture-flow" aria-label="Saathi processing flow">{([[Mic2, "Speech", "Input"], [Languages, "Intent", "Understand"], [Database, "Tools", "Verify"], [ShieldCheck, "Evidence", "Provenance"], [AudioLines, "Voice", "Respond"]] as const).map(([Icon, title, sub], index) => <div className="arch-node" key={title}><div className="arch-icon"><Icon size={18} /></div><strong>{title}</strong><small>{sub}</small>{index < 4 && <ArrowRight className="arch-arrow" size={15} />}</div>)}</div>
      </div></section>
      <section className="final-cta wrap"><div><span className="eyebrow"><span className="eyebrow-line" /> READY TO TRY IT?</span><h2>Ask Saathi the question<br /><em>you would actually ask.</em></h2></div><Link className="button button-dark" href="/dashboard">Try the prototype <ArrowUpRight size={17} /></Link></section>
      <footer className="footer wrap"><Link className="brand" href="/" aria-label="Saathi home"><span className="brand-mark"><AudioLines size={17} /></span>saathi<span className="brand-dot">.</span></Link><span>Voice-first · source-backed · consent-led</span><span>© 2026 Saathi</span></footer>
    </main>
  );
}
