"use client";

import Link from "next/link";

export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, minHeight: "100vh", background: "#f7f5ed", color: "#1d2823", fontFamily: "Arial, sans-serif", display: "grid", placeItems: "center", padding: "24px" }}>
        <main style={{ width: "min(100%, 620px)", padding: "32px", border: "1px solid #e7e8de", borderRadius: "16px", background: "#fffefa" }}>
          <p style={{ fontSize: "11px", fontWeight: 700, letterSpacing: "1.5px", color: "#244f40" }}>SAATHI · TEMPORARY ERROR</p>
          <h1 style={{ fontSize: "clamp(30px, 6vw, 46px)", lineHeight: 1.1, color: "#183d32" }}>The page could not load.</h1>
          <p role="alert" style={{ lineHeight: 1.7, color: "#68736c" }}>Something went wrong. Internal error details are hidden to protect your information.</p>
          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginTop: "22px" }}>
            <button type="button" onClick={reset} style={{ minHeight: "44px", padding: "10px 14px", border: 0, borderRadius: "8px", background: "#183d32", color: "white", fontWeight: 700, cursor: "pointer" }}>Try again</button>
            <Link href="/" style={{ minHeight: "44px", display: "inline-flex", alignItems: "center", padding: "10px 14px", border: "1px solid #e7e8de", borderRadius: "8px", color: "#183d32", textDecoration: "none", fontWeight: 700 }}>Back to Saathi</Link>
          </div>
        </main>
      </body>
    </html>
  );
}