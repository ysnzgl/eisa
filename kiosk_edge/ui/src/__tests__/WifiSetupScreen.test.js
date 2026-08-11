/**
 * WifiSetupScreen Wi-Fi reconciliation testleri.
 *
 * /wifi-connect'in OS düzeyinde bağlantı kurulmasına rağmen hata dönmesi
 * (yanlış-negatif) durumunu ele alan reconciliation algoritmasını doğrular.
 *
 * Gerçek Wi-Fi veya nmcli kullanılmaz; API fonksiyonları vi.fn() ile mock'lanır.
 * Svelte bileşeni render edilmez: mantık logic.test.js stiliyle saf-JS olarak test edilir.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// ─── Reconciliation algoritması ────────────────────────────────────────────
//
// WifiSetupScreen.svelte connect() içindeki reconciliation mantığının
// saf-JS eşdeğeri. Bileşen davranışını sözleşme düzeyinde belgelemek ve
// doğrulamak için burada ayrı bir fonksiyon olarak tanımlanmıştır.
//
// Sözleşme:
//   - connectFn(ssid)   → /wifi-connect'i temsil eder
//   - statusFn()        → fetchWifiStatus()'ü temsil eder; { connected, ssid } döner
//   - onSuccess()       → dispatch('connected') karşılığı
//   - onError(msg)      → connectError = msg karşılığı
//   - RECONCILE_ATTEMPTS: 3 (sonsuz döngü yok)
//   - delay: testlerde 0 ms (gerçek kodda 2000 ms)

async function runReconcile({
  targetSsid,
  connectFn,
  statusFn,
  onSuccess,
  onError,
  attempts = 3,
  delayMs = 0,
}) {
  let connectFailed = false;
  let originalError = '';

  try {
    await connectFn(targetSsid);
  } catch (err) {
    connectFailed = true;
    originalError = err.userMessage ?? 'Bağlantı kurulamadı. Şifreyi kontrol edin.';
  }

  if (!connectFailed) {
    onSuccess();
    return;
  }

  // /wifi-connect başarısız; OS bağlandı mı kontrol et.
  let verified = false;
  for (let i = 0; i < attempts && !verified; i++) {
    if (delayMs > 0) await new Promise((r) => setTimeout(r, delayMs));
    try {
      const status = await statusFn();
      if (status.connected && status.ssid === targetSsid) verified = true;
    } catch {
      // status sorgusu başarısız; sonraki denemeye geç
    }
  }

  if (verified) {
    onSuccess();
  } else {
    onError(originalError);
  }
}

// ─── Yardımcı: abortable reconcile (unmount testi için) ───────────────────
//
// Gerçek bileşendeki _reconcileId + _pendingResolvers mekanizmasını temsil eder.

function makeAbortableReconcile() {
  let aborted = false;
  const abort = () => { aborted = true; };

  async function run({ targetSsid, connectFn, statusFn, onSuccess, onError, attempts = 3 }) {
    let connectFailed = false;
    let originalError = '';

    try {
      await connectFn(targetSsid);
    } catch (err) {
      connectFailed = true;
      originalError = err.userMessage ?? 'Bağlantı kurulamadı.';
    }

    if (aborted) return;
    if (!connectFailed) { onSuccess(); return; }

    let verified = false;
    for (let i = 0; i < attempts && !verified; i++) {
      if (aborted) return;
      try {
        const status = await statusFn();
        if (aborted) return;
        if (status.connected && status.ssid === targetSsid) verified = true;
      } catch { /* devam */ }
    }

    if (aborted) return;
    if (verified) { onSuccess(); } else { onError(originalError); }
  }

  return { run, abort };
}

// ─── Testler ───────────────────────────────────────────────────────────────

describe('WifiSetupScreen — Wi-Fi reconciliation algoritması', () => {
  const SSID = 'MedinceAP';

  let connectFn;
  let statusFn;
  let onSuccess;
  let onError;

  beforeEach(() => {
    connectFn = vi.fn();
    statusFn  = vi.fn();
    onSuccess = vi.fn();
    onError   = vi.fn();
  });

  it('başarılı /wifi-connect → onSuccess bir kez çağrılır, /wifi-status sorgulanmaz', async () => {
    connectFn.mockResolvedValue({ success: true });

    await runReconcile({ targetSsid: SSID, connectFn, statusFn, onSuccess, onError });

    expect(onSuccess).toHaveBeenCalledTimes(1);
    expect(onError).not.toHaveBeenCalled();
    expect(statusFn).not.toHaveBeenCalled();
  });

  it('/wifi-connect hata + /wifi-status seçili SSID bağlı → onSuccess bir kez, onError yok', async () => {
    connectFn.mockRejectedValue(
      Object.assign(new Error('nmcli timeout'), { userMessage: 'Zaman aşımı.' }),
    );
    statusFn.mockResolvedValue({ connected: true, ssid: SSID });

    await runReconcile({ targetSsid: SSID, connectFn, statusFn, onSuccess, onError });

    expect(onSuccess).toHaveBeenCalledTimes(1);
    expect(onError).not.toHaveBeenCalled();
  });

  it('/wifi-connect hata + Wi-Fi bağlı değil → onError gerçek mesajla çağrılır, onSuccess yok', async () => {
    const errMsg = 'Yanlış şifre.';
    connectFn.mockRejectedValue(Object.assign(new Error(), { userMessage: errMsg }));
    statusFn.mockResolvedValue({ connected: false, ssid: null });

    await runReconcile({ targetSsid: SSID, connectFn, statusFn, onSuccess, onError });

    expect(onSuccess).not.toHaveBeenCalled();
    expect(onError).toHaveBeenCalledWith(errMsg);
  });

  it('başka SSID bağlıysa seçili ağ başarı sayılmaz', async () => {
    connectFn.mockRejectedValue(new Error('rejected'));
    statusFn.mockResolvedValue({ connected: true, ssid: 'DigerAg' }); // farklı SSID

    await runReconcile({ targetSsid: SSID, connectFn, statusFn, onSuccess, onError });

    expect(onSuccess).not.toHaveBeenCalled();
    expect(onError).toHaveBeenCalledTimes(1);
  });

  it('başarılı yolda onSuccess tam olarak bir kez çağrılır (duplicate yok)', async () => {
    connectFn.mockResolvedValue({ success: true });

    await runReconcile({ targetSsid: SSID, connectFn, statusFn, onSuccess, onError });
    await runReconcile({ targetSsid: SSID, connectFn, statusFn, onSuccess, onError });

    // Her çağrı için bir kez: iki bağımsız denemede ikişer kez, çapraz değil.
    expect(onSuccess).toHaveBeenCalledTimes(2);
  });

  it('abort sonrası onSuccess/onError çağrılmaz (unmount/yeni deneme iptal senaryosu)', async () => {
    connectFn.mockRejectedValue(new Error('rejected'));
    let resolveStatus;
    statusFn.mockImplementation(
      () => new Promise((r) => { resolveStatus = r; }), // asla otomatik çözülmez
    );

    const { run, abort } = makeAbortableReconcile();
    const promise = run({ targetSsid: SSID, connectFn, statusFn, onSuccess, onError });

    // İlk status çağrısı beklenirken iptal et
    abort();
    if (resolveStatus) resolveStatus({ connected: true, ssid: SSID });
    await promise;

    expect(onSuccess).not.toHaveBeenCalled();
    expect(onError).not.toHaveBeenCalled();
  });

  it('polling sınırlıdır — başarısız durumda en fazla 3 kez (RECONCILE_ATTEMPTS) sorgulanır', async () => {
    connectFn.mockRejectedValue(new Error('rejected'));
    statusFn.mockResolvedValue({ connected: false, ssid: null });

    await runReconcile({ targetSsid: SSID, connectFn, statusFn, onSuccess, onError, attempts: 3 });

    expect(statusFn).toHaveBeenCalledTimes(3);
    expect(onSuccess).not.toHaveBeenCalled();
  });
});
