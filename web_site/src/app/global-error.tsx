"use client";

/**
 * Kök layout dahil her şey çöktüğünde son çare (kendi <html>/<body>'sini render eder).
 * Normalde getSite() hata fırlatmadığı için tetiklenmemesi beklenir.
 */

export default function GlobalError({ retry }: { error: unknown; retry: () => void }) {
  return (
    <html lang="tr">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
          background: "#0b0f14",
          color: "#fff",
          fontFamily: "system-ui, -apple-system, 'Segoe UI', sans-serif",
          textAlign: "center",
          padding: "2rem",
        }}
      >
        <main>
          <p style={{ fontSize: "3rem", fontWeight: 700, color: "#ed1c24", margin: 0 }}>e-isa</p>
          <h1 style={{ fontSize: "1.5rem", margin: "1rem 0 0.5rem" }}>Beklenmeyen bir hata oluştu</h1>
          <p style={{ opacity: 0.7, margin: "0 0 1.5rem" }}>Lütfen sayfayı yenileyin veya biraz sonra tekrar deneyin.</p>
          <button
            type="button"
            onClick={() => retry()}
            style={{
              background: "#e3141c",
              color: "#fff",
              border: 0,
              borderRadius: 999,
              padding: "0.75rem 1.5rem",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Tekrar dene
          </button>
        </main>
      </body>
    </html>
  );
}
