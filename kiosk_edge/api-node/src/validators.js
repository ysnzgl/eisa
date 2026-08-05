// Pydantic eslenigi — zod semalari. Tum alan adlari Turkce ASCII.
import { z } from 'zod';

// SEC-010: Bit-pack codec her zaman 8-12 karakterlik uppercase Base36 uretir.
export const QR_RE = /^[0-9A-Z]{8,12}$/;

const YAS_ARALIGI_RE = /^(?:\d{1,2}-\d{1,2}|65\+)$/;
const CINSIYET_SET = ['M', 'F', 'O'];

export const oturumGonderSchema = z.object({
  // UI'dan gelen kararlı idempotency anahtarı (sessionId). Yoksa server üretir.
  idempotency_anahtari: z.string().uuid('Gecersiz idempotency_anahtari formati').optional(),
  yas_araligi_kod: z.string().trim().regex(YAS_ARALIGI_RE, 'Gecersiz yas araligi'),
  cinsiyet_kod: z.enum(CINSIYET_SET, {
    errorMap: () => ({ message: 'Gecersiz cinsiyet kodu' }),
  }),
  oturum_tipi: z.enum(['SIKAYET', 'OZEL_DANISMANLIK']).default('SIKAYET'),
  kategori_slug: z.string().min(1).max(64).nullable().optional(),
  danisma_kategorisi_slug: z.string().min(1).max(64).nullable().optional(),
  hassas_akis: z.boolean().default(false),
  qr_kodu: z.string().max(256).regex(QR_RE, 'Gecersiz QR kodu formati').nullable().optional(),
  cevaplar: z.record(z.any()).default({}),
  onerilen_etken_maddeler: z.array(z.string()).max(50, 'Cok fazla bilesen').default([]),
  // false = 10sn etkilesimsizlik ile terk edilmis (sahte/abandoned) oturum.
  tamamlandi: z.boolean().default(true),
});

export const reklamGosterimSchema = z.object({
  asset_id: z.string().uuid(),
  asset_type: z.enum(['creative', 'house_ad']),
  played_at: z.string().max(64),
  duration_played: z.number().int().min(0).max(24 * 60 * 60).default(0),
  // Faz 3: oynatma durumu + idempotency (eski kiosk sürümleri göndermez — opsiyonel)
  play_event_id: z.string().uuid().optional().nullable(),
  status: z.enum(['STARTED', 'COMPLETED', 'FAILED', 'INTERRUPTED']).default('COMPLETED').optional(),
  expected_duration: z.number().int().min(0).max(600).optional().nullable(),
  error_code: z.string().max(64).optional().default(''),
  error_summary: z.string().max(255).optional().default(''),
  occurred_at: z.string().max(64).optional().nullable(),
});

// Faz 4: kiosk teknik olay (hata, restart, bağlantı vb.)
const KIOSK_EVENT_TYPES = [
  'CONNECTION_LOST', 'CONNECTION_RESTORED', 'SYNC_FAILED',
  'PLAYBACK_ERROR', 'APP_RESTART', 'OUTBOX_PRESSURE', 'GENERAL_ERROR',
];
const KIOSK_EVENT_SEVERITIES = ['INFO', 'WARNING', 'ERROR', 'CRITICAL'];

export const kioskEventItemSchema = z.object({
  event_id: z.string().uuid(),
  event_type: z.enum(KIOSK_EVENT_TYPES).default('GENERAL_ERROR'),
  severity: z.enum(KIOSK_EVENT_SEVERITIES).default('WARNING'),
  message: z.string().max(512).default(''),
  occurred_at: z.string().max(64).optional().nullable(),
});

export const kioskEventBatchSchema = z.object({
  items: z.array(kioskEventItemSchema).min(1).max(200),
});

// Svelte UI'den gelen client (frontend) hata bildirimi.
// Sadece izin verilen kucuk bir alan seti kabul edilir; kullanici verisi loglanmaz.
const CLIENT_LEVELS = ['WARNING', 'ERROR', 'CRITICAL'];
export const clientLogSchema = z.object({
  level: z.enum(CLIENT_LEVELS).default('ERROR'),
  event: z.string().trim().min(1).max(128),
  message: z.string().max(4096).default(''),
  stack: z.string().max(8192).optional(),
  route: z.string().max(256).optional(),
  component: z.string().max(128).optional(),
  correlation_id: z.string().max(64).optional(),
  occurred_at: z.string().max(64).optional(),
  context: z.record(z.any()).optional(),
});

