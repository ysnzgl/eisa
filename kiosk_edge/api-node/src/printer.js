/**
 * Termal yazıcı (ESC/POS) — opsiyonel TCP/IP bağlantısı.
 *
 * `EISA_THERMAL_PRINTER_HOST` env tanımlıysa, ESC/POS komutları 9100 (raw)
 * portuna gönderilir. Tanımsızsa fonksiyon log'lar ve sessiz döner.
 *
 * Bu sayede kiosk yazıcısız da çalışır, yazıcı eklendiğinde yeniden derleme
 * gerekmez. Çoğu termal yazıcı (Epson, Star, Bixolon, vs.) raw port destekler.
 */
import net from 'node:net';

const ESC = 0x1b;
const GS = 0x1d;
const LF = 0x0a;

const INIT = Buffer.from([ESC, 0x40]); // ESC @
const ALIGN_CENTER = Buffer.from([ESC, 0x61, 0x01]);
const ALIGN_LEFT = Buffer.from([ESC, 0x61, 0x00]);
const BOLD_ON = Buffer.from([ESC, 0x45, 0x01]);
const BOLD_OFF = Buffer.from([ESC, 0x45, 0x00]);
const CUT = Buffer.from([GS, 0x56, 0x42, 0x00]); // partial cut

function text(s) {
  // Türkçe karakterleri yazıcıya uygun ASCII'ye düşür (CP-857 yok varsayımı).
  const ascii = String(s)
    .replace(/[ğĞ]/g, (c) => (c === 'ğ' ? 'g' : 'G'))
    .replace(/[şŞ]/g, (c) => (c === 'ş' ? 's' : 'S'))
    .replace(/[ıİ]/g, (c) => (c === 'ı' ? 'i' : 'I'))
    .replace(/[üÜ]/g, (c) => (c === 'ü' ? 'u' : 'U'))
    .replace(/[öÖ]/g, (c) => (c === 'ö' ? 'o' : 'O'))
    .replace(/[çÇ]/g, (c) => (c === 'ç' ? 'c' : 'C'));
  return Buffer.from(ascii + '\n', 'ascii');
}

/** ESC/POS QR komutu — model 2, modül 6, EC seviyesi M */
function qrCommands(payload) {
  const data = Buffer.from(payload, 'utf8');
  const len = data.length + 3;
  const pL = len & 0xff;
  const pH = (len >> 8) & 0xff;
  return Buffer.concat([
    Buffer.from([GS, 0x28, 0x6b, 0x04, 0x00, 0x31, 0x41, 0x32, 0x00]), // model
    Buffer.from([GS, 0x28, 0x6b, 0x03, 0x00, 0x31, 0x43, 0x06]), // size
    Buffer.from([GS, 0x28, 0x6b, 0x03, 0x00, 0x31, 0x45, 0x31]), // EC = M
    Buffer.from([GS, 0x28, 0x6b, pL, pH, 0x31, 0x50, 0x30]), // store
    data,
    Buffer.from([GS, 0x28, 0x6b, 0x03, 0x00, 0x31, 0x51, 0x30]), // print
  ]);
}

/**
 * Eczacı için termal fiş bas.
 * Çağıran asla beklemez (fire-and-forget); hatalar log'lanır.
 */
export function printReceipt({ qrCode, qrPayload, categoryName, ingredients, isSensitive, host, port = 9100, logger }) {
  const log = logger ?? console;
  if (!host) {
    log.info?.({ qrCode }, 'Termal yazıcı yapılandırılmamış — fiş atlandı.');
    return;
  }

  const lines = [
    INIT,
    ALIGN_CENTER,
    BOLD_ON,
    text('e-ISA'),
    BOLD_OFF,
    text('Eczaci Danisma Fisi'),
    text('--------------------------------'),
    ALIGN_LEFT,
    text(`Kategori : ${categoryName ?? '-'}`),
    text(`Kod      : ${qrCode}`),
    text(isSensitive ? 'NOT: HASSAS DANISMA' : ''),
    text(''),
    text('Onerilen Etken Maddeler:'),
  ];
  for (const ing of (ingredients ?? []).slice(0, 8)) {
    lines.push(text(`  - ${ing}`));
  }
  if (!ingredients?.length) lines.push(text('  (yok)'));
  lines.push(text(''));
  lines.push(ALIGN_CENTER);
  lines.push(qrCommands(qrPayload));
  lines.push(text(''));
  lines.push(text('Bu QR\'i eczacinizdan okutunuz.'));
  lines.push(Buffer.from([LF, LF, LF]));
  lines.push(CUT);

  const buffer = Buffer.concat(lines);
  const socket = new net.Socket();
  socket.setTimeout(4000);
  socket.once('error', (err) => log.warn?.({ err: err.message }, 'Termal yazıcı hatası'));
  socket.once('timeout', () => {
    log.warn?.('Termal yazıcı zaman aşımı');
    socket.destroy();
  });
  socket.connect(port, host, () => {
    socket.write(buffer, () => socket.end());
  });
}
