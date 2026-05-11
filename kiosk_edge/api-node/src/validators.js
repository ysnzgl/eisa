// Pydantic eslenigi — zod semalari. Tum alan adlari Turkce ASCII.
import { z } from 'zod';

// Backend lookup'lariyla bire bir eslesir.
// Cinsiyet kodlari: M (Erkek), F (Kadin), O (Diger).
export const ALLOWED_YAS_ARALIKLARI = ['0-17', '18-25', '26-35', '36-50', '51-65', '65+'];
export const ALLOWED_CINSIYETLER = ['M', 'F', 'O'];

// SEC-010: Bit-pack codec her zaman 8-12 karakterlik uppercase Base36 uretir.
export const QR_RE = /^[0-9A-Z]{8,12}$/;

export const oturumGonderSchema = z.object({
  yas_araligi_kod: z.enum(ALLOWED_YAS_ARALIKLARI, {
    errorMap: () => ({ message: 'Gecersiz yas araligi' }),
  }),
  cinsiyet_kod: z.enum(ALLOWED_CINSIYETLER, {
    errorMap: () => ({ message: 'Gecersiz cinsiyet kodu' }),
  }),
  kategori_slug: z.string().min(1).max(64),
  hassas_akis: z.boolean().default(false),
  qr_kodu: z.string().max(256).regex(QR_RE, 'Gecersiz QR kodu formati').nullable().optional(),
  cevaplar: z.record(z.any()).default({}),
  onerilen_etken_maddeler: z.array(z.string()).max(50, 'Cok fazla bilesen').default([]),
});

export const reklamGosterimSchema = z.object({
  asset_id: z.string().uuid(),
  asset_type: z.enum(['creative', 'house_ad']),
  played_at: z.string().max(64),
  duration_played: z.number().int().min(0).max(24 * 60 * 60).default(0),
});
