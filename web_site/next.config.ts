import type { NextConfig } from "next";

/**
 * e-isa kurumsal site — Next.js yapılandırması.
 *
 * Notlar:
 * - `output: "standalone"`: Docker imajı için minimal sunucu çıktısı.
 * - `distDir`: paralel geliştirme için `NEXT_DIST_DIR` ile değiştirilebilir
 *   (ör. iki ajan aynı anda `next dev` çalıştırırken `.next-ajan1`).
 * - Cache Components (`cacheComponents`) KAPALI: veri katmanı klasik
 *   `fetch(..., { next: { tags, revalidate } })` + ISR modelini kullanır
 *   (bkz. src/lib/api.ts, CONTRACT §6).
 */

const medyaTabani = process.env.MEDIA_BASE_URL || "http://localhost:8000";
const siteUrl = process.env.SITE_URL || "http://localhost:3000";

/** Medya sunucusu localhost ise next/image optimizer'ın yerel IP engelini kaldır (yalnızca geliştirme). */
const yerelMedya = /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?/i.test(medyaTabani);

type UzakDesen = NonNullable<NonNullable<NextConfig["images"]>["remotePatterns"]>[number];

const uzakDesenler: UzakDesen[] = [
  { protocol: "http", hostname: "localhost", port: "8000", pathname: "/api/media/**" },
  { protocol: "http", hostname: "127.0.0.1", port: "8000", pathname: "/api/media/**" },
  { protocol: "https", hostname: "api.eisa.com.tr", pathname: "/api/media/**" },
];

// MEDIA_BASE_URL yukarıdakilerden farklı bir host ise onu da ekle.
try {
  const u = new URL(medyaTabani);
  const protokol = u.protocol.replace(":", "") as "http" | "https";
  const varMi = uzakDesenler.some(
    (d) => d.hostname === u.hostname && (d.port ?? "") === u.port && d.protocol === protokol,
  );
  if (!varMi) {
    uzakDesenler.push({ protocol: protokol, hostname: u.hostname, port: u.port, pathname: "/api/media/**" });
  }
} catch {
  // Geçersiz MEDIA_BASE_URL: varsayılan desenlerle devam.
}

const guvenlikBasliklari = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Content-Security-Policy", value: "frame-ancestors 'none'; base-uri 'self'; form-action 'self'" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=(), payment=(), usb=(), browsing-topics=()",
  },
  ...(siteUrl.startsWith("https://")
    ? [{ key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" }]
    : []),
];

const nextConfig: NextConfig = {
  output: "standalone",
  distDir: process.env.NEXT_DIST_DIR || ".next",
  // Monorepo kökünde ayrı bir package-lock.json var; proje kökü bu dizindir
  // (standalone çıktısı .next/standalone/server.js olur).
  outputFileTracingRoot: __dirname,
  poweredByHeader: false,
  reactStrictMode: true,
  images: {
    remotePatterns: uzakDesenler,
    dangerouslyAllowLocalIP: yerelMedya,
    formats: ["image/avif", "image/webp"],
  },
  async headers() {
    return [{ source: "/:path*", headers: guvenlikBasliklari }];
  },
  turbopack: {
    root: __dirname,
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
