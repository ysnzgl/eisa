/**
 * Dekoratif QR kodu (gerçek veri taşımaz). Deterministik desen → SSR/istemci aynı.
 */

const N = 25;

function hucreleriUret(): boolean[][] {
  let tohum = 20261107;
  const rastgele = () => {
    tohum = (tohum * 9301 + 49297) % 233280;
    return tohum / 233280;
  };
  const izgara = Array.from({ length: N }, () => Array.from({ length: N }, () => rastgele() > 0.5));
  // Konum desenleri (3 köşe): 7x7 dış çerçeve + 3x3 merkez, etrafında 1 hücre boşluk
  const desen = (sx: number, sy: number) => {
    for (let y = -1; y <= 7; y++) {
      for (let x = -1; x <= 7; x++) {
        const gx = sx + x;
        const gy = sy + y;
        if (gx < 0 || gy < 0 || gx >= N || gy >= N) continue;
        const kenar = x === 0 || x === 6 || y === 0 || y === 6;
        const merkez = x >= 2 && x <= 4 && y >= 2 && y <= 4;
        izgara[gy][gx] = x >= 0 && x <= 6 && y >= 0 && y <= 6 && (kenar || merkez);
      }
    }
  };
  desen(0, 0);
  desen(N - 7, 0);
  desen(0, N - 7);
  return izgara;
}

const YOL = hucreleriUret()
  .flatMap((satir, y) => satir.map((dolu, x) => (dolu ? `M${x} ${y}h1v1h-1z` : "")))
  .join("");

export function KioskQr({ className }: { className?: string }) {
  return (
    <svg viewBox={`-1 -1 ${N + 2} ${N + 2}`} className={className} shapeRendering="crispEdges" aria-hidden>
      <rect x={-1} y={-1} width={N + 2} height={N + 2} fill="#fff" />
      <path d={YOL} fill="#0b0f14" />
    </svg>
  );
}