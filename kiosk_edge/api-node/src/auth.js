// Lokal yetkilendirme — eczacı uçbiriminden /api/session/{qr} sorgusu için.
import crypto from 'node:crypto';

function timingSafeEqualStr(a, b) {
  const ab = Buffer.from(a, 'utf8');
  const bb = Buffer.from(b, 'utf8');
  if (ab.length !== bb.length) return false;
  return crypto.timingSafeEqual(ab, bb);
}

export function requireLocalSecret(expected) {
  return async function preHandler(req, reply) {
    if (!expected) {
      return reply
        .code(503)
        .send({ detail: 'Lokal API sırrı yapılandırılmamış.' });
    }
    const auth = req.headers['authorization'];
    if (!auth || !auth.startsWith('Bearer ')) {
      return reply.code(401).send({ detail: 'Yetkilendirme başlığı eksik.' });
    }
    const token = auth.slice(7).trim();
    if (!timingSafeEqualStr(token, expected)) {
      return reply.code(401).send({ detail: 'Geçersiz lokal sır.' });
    }
  };
}
