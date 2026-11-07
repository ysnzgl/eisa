import { ImageResponse } from "next/og";
import { readFile } from "node:fs/promises";
import { join } from "node:path";

/**
 * Varsayılan markalı Open Graph görseli (1200×630). Build sırasında statik üretilir.
 * Türkçe karakterler (ç, ğ, ı, İ, ö, ş, ü) için latin-ext içeren TTF fontlar
 * src/assets/fonts altından okunur (next/og varsayılan fontu latin-ext içermez).
 * Sayfa/blog SEO'sunda og_gorsel tanımlıysa o görsel bunun yerine kullanılır.
 */

export const alt = "e-isa — Eczanenizdeki reçete bekleme süresini sağlık okuryazarlığına dönüştürün";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const E_HARFI =
  "M155.3,86.7h-78.1v1.5c0,10.6,3,19.1,9.1,25.6,6,6.5,13.9,9.8,23.6,9.8s12.6-1.8,17.9-5.3c5.3-3.6,10-8.9,14.1-16.1l12.8,8.6c-5,8.9-11.3,15.6-19,20.2-7.7,4.5-16.6,6.8-26.7,6.8-15,0-27.2-5-36.4-14.9-9.3-9.9-13.9-22.9-13.9-39s4.6-28.1,13.8-37.9c9.2-9.8,21-14.8,35.5-14.8s26.1,4.7,34.6,14c8.5,9.3,12.8,22.1,12.8,38.3v3.3ZM137.2,73.1c-.6-8.7-3.5-15.4-8.7-20.1-5.2-4.7-12.3-7.1-21.4-7.1s-15,2.5-20.5,7.4c-5.5,4.9-8.6,11.5-9.5,19.8h60Z";

export default async function OpengraphImage() {
  const fontKlasoru = join(process.cwd(), "src", "assets", "fonts");
  const [baslikFontu, govdeFontu] = await Promise.all([
    readFile(join(fontKlasoru, "SpaceGrotesk-Bold.ttf")),
    readFile(join(fontKlasoru, "Inter-Medium.ttf")),
  ]);

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "72px 80px",
          backgroundColor: "#0b0f14",
          backgroundImage:
            "radial-gradient(circle at 85% 10%, rgba(237,28,36,0.45) 0%, rgba(237,28,36,0) 45%), radial-gradient(circle at 0% 100%, rgba(43,108,176,0.25) 0%, rgba(43,108,176,0) 50%)",
          color: "#ffffff",
          fontFamily: "Inter",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 22 }}>
          <svg width="76" height="76" viewBox="42.2 19.7 129.5 129.5">
            <rect x="42.2" y="19.7" width="129.5" height="129.5" rx="33.3" ry="33.3" fill="#ed1c24" />
            <path d={E_HARFI} fill="#ffffff" />
          </svg>
          <div style={{ display: "flex", fontFamily: "Space Grotesk", fontSize: 52, letterSpacing: -1 }}>e-isa</div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 26 }}>
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              fontFamily: "Space Grotesk",
              fontSize: 64,
              lineHeight: 1.08,
              letterSpacing: -1.5,
              maxWidth: 1000,
            }}
          >
            Reçete bekleme süresini sağlık okuryazarlığına dönüştürün
          </div>
          <div style={{ display: "flex", fontSize: 28, color: "rgba(255,255,255,0.72)" }}>
            Eczacının ön hazırlık asistanı · Marka değil, ihtiyaç kategorisi · Son değerlendirme eczacıda
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: 24 }}>
          <div style={{ display: "flex", color: "rgba(255,255,255,0.6)" }}>Eisa Bilişim Teknolojileri A.Ş.</div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ width: 12, height: 12, borderRadius: 999, backgroundColor: "#ed1c24" }} />
            <div style={{ display: "flex", color: "#ffffff" }}>eisa.com.tr</div>
          </div>
        </div>
      </div>
    ),
    {
      ...size,
      fonts: [
        { name: "Space Grotesk", data: baslikFontu, weight: 700, style: "normal" },
        { name: "Inter", data: govdeFontu, weight: 500, style: "normal" },
      ],
    },
  );
}
