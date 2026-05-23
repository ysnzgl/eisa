// E-ISA Kiosk — WiFi yönetimi (nmcli aracılığıyla NetworkManager)
//
// Güvenlik notu: Tüm komutlar spawn() ile çalıştırılır; hiçbir argüman
// shell üzerinden geçmez — command injection riski yoktur.
//
// Gereksinim: eisa kullanıcısı "netdev" grubunda olmalı
//   veya /etc/polkit-1/rules.d/ altında uygun bir kural tanımlı olmalı.
//   Örnek (60-eisa-wifi.rules):
//     polkit.addRule(function(action, subject) {
//       if (action.id.indexOf("org.freedesktop.NetworkManager") === 0 &&
//           subject.user === "eisa") { return polkit.Result.YES; }
//     });

import { spawn }       from 'node:child_process';
import { fetch as undiciFetch } from 'undici';

const EXEC_TIMEOUT_MS    = 20_000;
const CONNECT_TIMEOUT_MS = 40_000;

// ── temel spawn yardımcısı ─────────────────────────────────────────────────

/**
 * Belirtilen komutu spawn ile çalıştırır ve stdout'u döndürür.
 * Shell geçişi yoktur; argümanlar dizisi olarak aktarılır (injection-safe).
 * @param {string}   cmd
 * @param {string[]} args
 * @param {number}   [timeoutMs]
 * @returns {Promise<string>} stdout
 */
function runProcess(cmd, args, timeoutMs = EXEC_TIMEOUT_MS) {
  return new Promise((resolve, reject) => {
    const proc = spawn(cmd, args, { stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '';
    let stderr = '';

    const timer = setTimeout(() => {
      proc.kill('SIGTERM');
      reject(new Error(`Komut zaman aşımına uğradı: ${cmd} ${args.join(' ')}`));
    }, timeoutMs);

    proc.stdout.on('data', (d) => { stdout += d.toString(); });
    proc.stderr.on('data', (d) => { stderr += d.toString(); });

    proc.on('close', (code) => {
      clearTimeout(timer);
      if (code === 0) resolve(stdout);
      else reject(new Error(stderr.trim() || `Çıkış kodu: ${code}`));
    });

    proc.on('error', (err) => {
      clearTimeout(timer);
      reject(err);
    });
  });
}

// ── internet kontrolü ─────────────────────────────────────────────────────

/**
 * İnternet bağlantısını kontrol eder.
 * Önce Cloudflare DNS'e HEAD isteği dener; başarısız olursa
 * nmcli networking connectivity sonucuna bakar.
 * @returns {Promise<boolean>}
 */
export async function checkInternet() {
  try {
    const res = await undiciFetch('https://1.1.1.1', {
      method: 'HEAD',
      signal: AbortSignal.timeout(5_000),
    });
    return res.ok || res.status < 500;
  } catch {
    /* ağ yoksa nmcli'ye düş */
  }

  try {
    const out = await runProcess('nmcli', ['-t', 'networking', 'connectivity'], 8_000);
    return out.trim().toLowerCase() === 'full';
  } catch {
    return false;
  }
}

// ── mevcut bağlantı durumu ────────────────────────────────────────────────

/**
 * Mevcut WiFi durumunu döndürür.
 * @returns {Promise<{connected: boolean, ssid: string|null}>}
 */
export async function getWifiStatus() {
  const [connResult, ssidResult] = await Promise.allSettled([
    checkInternet(),
    runProcess('nmcli', ['-t', '-f', 'ACTIVE,SSID', 'dev', 'wifi']),
  ]);

  const connected = connResult.status === 'fulfilled' ? connResult.value : false;

  let ssid = null;
  if (ssidResult.status === 'fulfilled') {
    // nmcli -t çıktısı: "yes:AgAdi\n" veya "no:DigerAg\n"
    // Kolon içeren SSID'lerde nmcli \: ile escape eder; burada basit split yeterli.
    const activeLine = ssidResult.value
      .split('\n')
      .find((l) => l.toLowerCase().startsWith('yes:'));
    if (activeLine) {
      ssid = activeLine.slice(4).trim() || null; // "yes:" kısmını at
    }
  }

  return { connected, ssid };
}

// ── ağ tarama ─────────────────────────────────────────────────────────────

/**
 * Çevredeki WiFi ağlarını tarar.
 * @returns {Promise<Array<{ssid: string, signal: number, secured: boolean}>>}
 */
export async function scanWifi() {
  // Taramayı tetikle (başarısız olabilir, önemseme)
  await runProcess('nmcli', ['dev', 'wifi', 'rescan']).catch(() => {});

  const stdout = await runProcess('nmcli', [
    '-m', 'multiline',
    '-f', 'SSID,SIGNAL,SECURITY',
    'dev', 'wifi', 'list',
  ]);

  const networks = [];
  const seen     = new Set();
  let   current  = null;

  for (const rawLine of stdout.split('\n')) {
    const line = rawLine.trim();
    if (!line) continue;

    // nmcli multiline çıktısı: "FIELD:  değer" biçiminde
    const colonIdx = line.indexOf(':');
    if (colonIdx === -1) continue;

    const field = line.slice(0, colonIdx).trim().toUpperCase();
    const value = line.slice(colonIdx + 1).trim();

    if (field === 'SSID') {
      if (current && current.ssid && !seen.has(current.ssid)) {
        seen.add(current.ssid);
        networks.push(current);
      }
      const ssidVal = value === '--' ? '' : value;
      current = { ssid: ssidVal, signal: 0, secured: false };
    } else if (field === 'SIGNAL' && current) {
      current.signal = parseInt(value, 10) || 0;
    } else if (field === 'SECURITY' && current) {
      current.secured = value !== '' && value !== '--';
    }
  }

  // Son kaydı ekle
  if (current && current.ssid && !seen.has(current.ssid)) {
    networks.push(current);
  }

  return networks
    .filter((n) => n.ssid.length > 0)       // gizli ağları filtrele
    .sort((a, b) => b.signal - a.signal);    // sinyal gücüne göre sırala
}

// ── bağlanma ──────────────────────────────────────────────────────────────

/**
 * Belirtilen WiFi ağına bağlanır.
 * @param {string}  ssid
 * @param {string|null} [password]
 * @returns {Promise<{success: boolean, message: string}>}
 */
export async function connectWifi(ssid, password) {
  try {
    const args = ['dev', 'wifi', 'connect', ssid];
    if (password) {
      args.push('password', password);
    }
    const stdout = await runProcess('nmcli', args, CONNECT_TIMEOUT_MS);
    const success = stdout.toLowerCase().includes('successfully activated');
    return {
      success,
      message: success ? 'Bağlantı başarılı.' : stdout.trim(),
    };
  } catch (err) {
    return { success: false, message: err.message };
  }
}
