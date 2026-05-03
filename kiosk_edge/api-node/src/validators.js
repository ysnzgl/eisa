// Pydantic eşleniği — zod şemaları.
import { z } from 'zod';

export const ALLOWED_AGE_RANGES = ['0-17', '18-25', '26-35', '36-50', '51-65', '65+'];
export const ALLOWED_GENDERS = ['M', 'F', 'male', 'female', 'other', 'unspecified'];

export const QR_RE = /^[A-Za-z0-9][\w:\-]{5,255}$/;

export const sessionSubmitSchema = z.object({
  age_range: z.enum(ALLOWED_AGE_RANGES, {
    errorMap: () => ({ message: 'Geçersiz yaş aralığı' }),
  }),
  gender: z.enum(ALLOWED_GENDERS, {
    errorMap: () => ({ message: 'Geçersiz cinsiyet değeri' }),
  }),
  category_slug: z.string().min(1).max(64),
  is_sensitive_flow: z.boolean().default(false),
  qr_code: z
    .string()
    .max(256)
    .regex(QR_RE, 'Geçersiz QR kodu formatı')
    .nullable()
    .optional(),
  answers_payload: z.record(z.any()).default({}),
  suggested_ingredients: z.array(z.string()).max(50, 'Çok fazla bileşen').default([]),
});

export const adImpressionSchema = z.object({
  campaign_id: z.number().int().min(1),
  shown_at: z.string().max(64),
  duration_ms: z.number().int().min(0).max(24 * 60 * 60 * 1000).default(0),
});
