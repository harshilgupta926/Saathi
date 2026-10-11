"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { ArrowRight, CheckCircle2, CloudRain, Database, Mic2, ShieldCheck, Wheat } from "lucide-react";

const cards = [
  { label: "VOICE", title: "Ask naturally", text: "Hindi, Hinglish, or a mix. Saathi starts from what you actually say.", icon: Mic2, tone: "dark" },
  { label: "MANDI", title: "Verified market data", text: "Get a market observation with its source instead of an invented number.", icon: Wheat, tone: "light" },
  { label: "WEATHER", title: "Local conditions", text: "Pair a farming question with a weather check for the same place.", icon: CloudRain, tone: "gold" },
  { label: "TRUST", title: "Evidence stays visible", text: "Every tool-backed answer carries provenance and retrieval context.", icon: ShieldCheck, tone: "light" },
];

export default function SaathiHero() {
  const ref = useRef(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const move = (event) => {
      const rect = el.getBoundingClientRect();
      el.style.setProperty("--mx", ((event.clientX - rect.left) / rect.width * 100).toFixed(2) + "%");
      el.style.setProperty("--my", ((event.clientY - rect.top) / rect.height * 100).toFixed(2) + "%");
    };
    const leave = () => {
      el.style.setProperty("--mx", "50%");
      el.style.setProperty("--my", "50%");
    };
    el.addEventListener("pointermove", move);
    el.addEventListener("pointerleave", leave);
    return () => {
      el.removeEventListener("pointermove", move);
      el.removeEventListener("pointerleave", leave);
    };
  }, []);

  return (
    <section className="product-hero" ref={ref}>
      <div className="hero-glow" aria-hidden="true" />
      <div className="product-hero-inner">
        <div className="product-hero-copy">
          <div className="product-kicker"><span /> SAATHI</div>
          <h1>Ask in your own words.<br /><em>Get a grounded answer.</em></h1>
          <p>Saathi is a Hindi and Hinglish voice assistant that turns everyday questions into verified assistance from specialist sources.</p>
          <div className="product-hero-actions">
            <Link className="primary-action" href="/dashboard">Try Saathi <ArrowRight size={16} /></Link>
            <a className="secondary-action" href="#how-it-works">See how it works</a>
          </div>
          <div className="hero-trust"><CheckCircle2 size={15} /> Answers are grounded in available source data</div>
        </div>

        <div className="bento-grid" aria-label="Saathi product capabilities">
          {cards.map(({ label, title, text, icon: Icon, tone }, index) => (
            <article className={`bento-card bento-${tone} bento-${index + 1}`} key={label}>
              <div className="bento-top"><span>{label}</span><Icon size={17} /></div>
              <div>
                <h2>{title}</h2>
                <p>{text}</p>
              </div>
              {index === 0 && <div className="bento-wave" aria-hidden="true"><span /><span /><span /><span /><span /></div>}
              {index === 1 && <div className="data-preview"><Database size={14} /><span>AGMARKNET</span><b>source attached</b></div>}
              {index === 2 && <div className="weather-preview"><span>24h</span><strong>Weather check</strong><i /></div>}
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
