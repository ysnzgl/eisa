// Korelasyon ID yardimcilari (Fastify + backend cagrilari).
// Bir HTTP istegi veya scheduler dongusu boyunca ayni ID takip edilir; dis
// cagrilarda `X-Correlation-ID` basligi olarak iletilir.
import { AsyncLocalStorage } from 'node:async_hooks';
import crypto from 'node:crypto';

export const CORRELATION_HEADER = 'x-correlation-id';
export const CORRELATION_HEADER_PRETTY = 'X-Correlation-ID';

const _als = new AsyncLocalStorage();

const _SAFE_RE = /^[A-Za-z0-9._-]{1,64}$/;

export function newCorrelationId() {
  return crypto.randomUUID().replace(/-/g, '');
}

/**
 * Istekten gelen degeri normalize eder; guvenli degilse null doner.
 */
export function sanitizeIncoming(value) {
  if (!value || typeof value !== 'string') return null;
  const v = value.trim();
  return _SAFE_RE.test(v) ? v : null;
}

export function getCorrelationId() {
  return _als.getStore()?.correlationId ?? null;
}

/**
 * Bir isi bir korelasyon ID'si altinda calistirir. Nested cagrilar da ayni ID'yi gorur.
 */
export function runWithCorrelation(id, fn) {
  return _als.run({ correlationId: id }, fn);
}

/**
 * Ana ID'ye baglanmis fakat bagimsiz yeni scheduler dongusu icin kisa unique bir ID uret.
 */
export function derivedId(prefix) {
  const suffix = crypto.randomBytes(6).toString('hex');
  return prefix ? `${prefix}-${suffix}` : suffix;
}
