"use client";

import Link from "next/link";

export default function ErrorBoundary({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main className="state-page">
      <section className="state-card" aria-labelledby="error-title">
        <span className="state-kicker">TEMPORARY ERROR</span>
        <h1 id="error-title">Saathi couldn&apos;t finish that request.</h1>
        <p role="alert" className="state-error">Something went wrong. Internal error details are hidden to protect your information.</p>
        <div className="state-actions">
          <button className="state-retry" type="button" onClick={reset}>Try again</button>
          <Link className="state-link" href="/">Back to Saathi</Link>
        </div>
      </section>
    </main>
  );
}