import Link from "next/link";

export default function NotFound() {
  return (
    <main className="state-page">
      <section className="state-card" aria-labelledby="not-found-title">
        <span className="state-kicker">404 · PAGE NOT FOUND</span>
        <h1 id="not-found-title">This page isn&apos;t here.</h1>
        <p>The address may be outdated or the page may have moved. This error does not submit or change any information.</p>
        <div className="state-actions">
          <Link className="site-nav-cta" href="/">Back to Saathi</Link>
          <Link className="state-link" href="/dashboard">Open the demo</Link>
        </div>
      </section>
    </main>
  );
}