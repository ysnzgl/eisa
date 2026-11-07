/**
 * Hafif sağlık ucu (K8s readiness/liveness — deploy/eisa-site-production.yaml).
 *
 *   GET /api/health → 200 { "durum": "ok" }
 *
 * Bilinçli olarak API'ye DOKUNMAZ: backend geçici olarak kapalıyken pod'lar
 * yeniden başlatılmasın; site ISR önbelleğinden sunmaya devam eder.
 */

export const dynamic = "force-dynamic";

export function GET() {
  return Response.json({ durum: "ok" }, { headers: { "Cache-Control": "no-store" } });
}
