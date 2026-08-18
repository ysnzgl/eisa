/**
 * Termal yazıcı (ESC/POS).
 * EISA_THERMAL_PRINTER_HOST:
 *   default          → Windows varsayılan yazıcısı (Spooler API, PowerShell)
 *   POS-80           → Windows yazıcı adı (Spooler API, PowerShell)
 *   COM3 / USB001    → Windows cihaz portu (writeFileSync → \\.\COM3 / \\.\USB001)
 *   /dev/usb/lp0     → Linux cihaz dosyası
 *   192.168.1.x      → TCP/IP raw port 9100
 */
import net from 'node:net';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execSync } from 'node:child_process';
import zlib from 'node:zlib';

const ESC = 0x1b;
const GS = 0x1d;
const LF = 0x0a;

const INIT = Buffer.from([ESC, 0x40]); // ESC @
const ALIGN_CENTER = Buffer.from([ESC, 0x61, 0x01]);
const ALIGN_LEFT = Buffer.from([ESC, 0x61, 0x00]);
const BOLD_ON = Buffer.from([ESC, 0x45, 0x01]);
const BOLD_OFF = Buffer.from([ESC, 0x45, 0x00]);
const CUT = Buffer.from([GS, 0x56, 0x42, 0x00]); // partial cut

// ── PNG → ESC/POS raster dönüşümü (built-in node:zlib; yeni bağımlılık yok) ──

/**
 * PNG dosyasını ESC/POS GS v 0 raster komutuna dönüştürür.
 *
 * Desteklenen PNG: grayscale (color_type 0), RGB (color_type 2), 8-bit, interlace yok.
 * Beyaz arka plan + siyah/koyu piksel varsayımı: piksel değeri < 128 → siyah.
 *
 * @param {string} filePath - PNG dosya yolu
 * @returns {Buffer} - ESC/POS GS v 0 komutu
 * @throws Dosya okunamazsa veya PNG geçersizse
 */
export function pngToEscposRaster(filePath) {
  const data = fs.readFileSync(filePath);

  // PNG magic kontrolü
  if (data.slice(0, 8).toString('hex') !== '89504e470d0a1a0a') {
    throw new Error('Geçersiz PNG: magic byte kontrolü başarısız');
  }

  // IHDR: offset 8 (4 len + 4 type + 13 data)
  const ihdrLen = data.readUInt32BE(8);
  if (data.slice(12, 16).toString('ascii') !== 'IHDR' || ihdrLen !== 13) {
    throw new Error('Geçersiz PNG: IHDR chunk bulunamadı');
  }
  const width = data.readUInt32BE(16);
  const height = data.readUInt32BE(20);
  const bitDepth = data[24];
  const colorType = data[25];
  const interlace = data[28];

  if (bitDepth !== 8) throw new Error(`Desteklenmeyen bit derinliği: ${bitDepth} (yalnız 8 desteklenir)`);
  if (interlace !== 0) throw new Error('Interlaced PNG desteklenmiyor');
  // 0=grayscale, 2=RGB, 6=RGBA (backend opak RGBA kabul eder — alpha kanalı yoksayılır)
  if (colorType !== 0 && colorType !== 2 && colorType !== 6) {
    throw new Error(`Desteklenmeyen renk tipi: ${colorType} (grayscale=0, RGB=2, RGBA=6 desteklenir)`);
  }

  // Tüm IDAT chunk'larını birleştir
  const idatBuffers = [];
  let offset = 8;
  while (offset < data.length - 12) {
    const chunkLen = data.readUInt32BE(offset);
    const chunkType = data.slice(offset + 4, offset + 8).toString('ascii');
    if (chunkType === 'IEND') break;
    if (chunkType === 'IDAT') {
      idatBuffers.push(data.slice(offset + 8, offset + 8 + chunkLen));
    }
    offset += 12 + chunkLen;
  }
  if (!idatBuffers.length) throw new Error('IDAT chunk bulunamadı');

  const compressed = Buffer.concat(idatBuffers);
  const raw = zlib.inflateSync(compressed);

  // Kanal sayısı: RGBA (6) = 4, RGB (2) = 3, grayscale (0) = 1
  const channels = colorType === 6 ? 4 : colorType === 2 ? 3 : 1;
  const bytesPerRow = width * channels;
  const strideRaw = 1 + bytesPerRow; // 1 filter byte + pixel data

  // PNG filter uygula → piksel dizisi (flat, row-major, channels bayt/piksel)
  const pixels = Buffer.alloc(height * bytesPerRow);

  const paethPredictor = (a, b, c) => {
    const p = a + b - c;
    const pa = Math.abs(p - a);
    const pb = Math.abs(p - b);
    const pc = Math.abs(p - c);
    if (pa <= pb && pa <= pc) return a;
    if (pb <= pc) return b;
    return c;
  };

  for (let y = 0; y < height; y++) {
    const filterByte = raw[y * strideRaw];
    const rowStart = y * strideRaw + 1;
    const outStart = y * bytesPerRow;

    for (let x = 0; x < bytesPerRow; x++) {
      const raw_val = raw[rowStart + x];
      const a = x >= channels ? pixels[outStart + x - channels] : 0;
      const b = y > 0 ? pixels[(y - 1) * bytesPerRow + x] : 0;
      const c = y > 0 && x >= channels ? pixels[(y - 1) * bytesPerRow + x - channels] : 0;

      let val;
      switch (filterByte) {
        case 0: val = raw_val; break;                          // None
        case 1: val = (raw_val + a) & 0xff; break;             // Sub
        case 2: val = (raw_val + b) & 0xff; break;             // Up
        case 3: val = (raw_val + Math.floor((a + b) / 2)) & 0xff; break; // Average
        case 4: val = (raw_val + paethPredictor(a, b, c)) & 0xff; break; // Paeth
        default: val = raw_val;
      }
      pixels[outStart + x] = val;
    }
  }

  // Piksel dizisini 1-bit bitmap'e dönüştür (grayscale luminance < 128 → siyah)
  const bytesPerBitmapRow = Math.ceil(width / 8);
  const bitmap = Buffer.alloc(height * bytesPerBitmapRow, 0);

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      let lum;
      if (colorType === 0) {
        lum = pixels[y * bytesPerRow + x];
      } else if (colorType === 6) {
        // RGBA: alpha=255 olarak doğrulanmış (backend); RGB kanalları al
        const base = y * bytesPerRow + x * 4;
        lum = Math.round((pixels[base] * 299 + pixels[base + 1] * 587 + pixels[base + 2] * 114) / 1000);
      } else {
        // RGB
        const base = y * bytesPerRow + x * 3;
        lum = Math.round((pixels[base] * 299 + pixels[base + 1] * 587 + pixels[base + 2] * 114) / 1000);
      }
      if (lum < 128) {
        // Siyah piksel → bit 1 (MSB-first)
        const byteIdx = y * bytesPerBitmapRow + Math.floor(x / 8);
        const bitShift = 7 - (x % 8);
        bitmap[byteIdx] |= (1 << bitShift);
      }
    }
  }

  // GS v 0 m xL xH yL yH d[0..n]
  // m=0 (normal), xL=bytes per row, xH=0, yL=low(height), yH=high(height)
  const cmd = Buffer.from([
    GS, 0x76, 0x30, 0x00,
    bytesPerBitmapRow & 0xff, (bytesPerBitmapRow >> 8) & 0xff,
    height & 0xff, (height >> 8) & 0xff,
  ]);

  return Buffer.concat([cmd, bitmap]);
}

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
    Buffer.from([GS, 0x28, 0x6b, 0x03, 0x00, 0x31, 0x43, 0x10]), // size (16 = ~42mm at 203 DPI)
    Buffer.from([GS, 0x28, 0x6b, 0x03, 0x00, 0x31, 0x45, 0x31]), // EC = M
    Buffer.from([GS, 0x28, 0x6b, pL, pH, 0x31, 0x50, 0x30]), // store
    data,
    Buffer.from([GS, 0x28, 0x6b, 0x03, 0x00, 0x31, 0x51, 0x30]), // print
  ]);
}

/**
 * Tam fiş buffer'ını bellekte oluşturur.
 * Logo adaylarını sırayla dener; ilk başarılıyı kullanır.
 * Tüm adaylar başarısızsa e-ISA metin fallback kullanılır.
 *
 * @param {object[]} logoCandidates - {id, local_path} nesneleri, rotation sırası
 * @returns {{ buffer: Buffer, logoId: string|null }}
 */
export function buildReceiptBuffer({ qrPayload, logoCandidates = [], logger }) {
  const log = logger ?? null;

  for (const logo of logoCandidates) {
    try {
      const raster = pngToEscposRaster(logo.local_path);
      return {
        buffer: Buffer.concat([
          INIT, ALIGN_CENTER, raster,
          text('Sağlıklı günler diler.'), text(''),
          qrCommands(qrPayload),
          text(''), text(qrPayload),
          Buffer.from([LF, LF, LF]), CUT,
        ]),
        logoId: logo.id,
      };
    } catch (err) {
      log?.warn?.({ err: err?.message, logoId: logo.id }, 'Logo raster basarisiz; sonraki deneniyor');
    }
  }

  // Tüm adaylar başarısız veya liste boş: e-ISA fallback
  return {
    buffer: Buffer.concat([
      INIT, ALIGN_CENTER, BOLD_ON, text('e-isa'), BOLD_OFF,
      text('Sağlıklı günler diler.'), text(''),
      qrCommands(qrPayload),
      text(''), text(qrPayload),
      Buffer.from([LF, LF, LF]), CUT,
    ]),
    logoId: null,
  };
}

/**
 * Windows Print Spooler API üzerinden ham ESC/POS baytlarını gönderir.
 * printerName boşsa veya 'default' ise sistemin varsayılan yazıcısı kullanılır.
 * Geçici dosyalar otomatik temizlenir.
 */
function sendToWindowsSpooler(buffer, printerName, log) {
  const tmp = os.tmpdir();
  const dataFile   = path.join(tmp, `eisa_esc_${Date.now()}.bin`);
  const scriptFile = path.join(tmp, `eisa_print_${Date.now()}.ps1`);

  // Yazıcı adı boşsa varsayılanı al; 'default' anahtar kelimesini de destekle
  const resolvedName = (!printerName || printerName.toLowerCase() === 'default') ? '' : printerName;

  const ps1 = `
param([string]$DataFile, [string]$PrinterName)
if (-not $PrinterName) {
    $PrinterName = (Get-CimInstance Win32_Printer -Filter "Default='True'").Name
}
$bytes = [System.IO.File]::ReadAllBytes($DataFile)
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class RawPrint {
    [DllImport("winspool.drv", EntryPoint="OpenPrinterA")]
    public static extern bool OpenPrinter(string n, ref IntPtr h, IntPtr d);
    [DllImport("winspool.drv", EntryPoint="ClosePrinter")]
    public static extern bool ClosePrinter(IntPtr h);
    [DllImport("winspool.drv", EntryPoint="StartDocPrinterA")]
    public static extern int StartDocPrinter(IntPtr h, int l, ref DOCINFO d);
    [DllImport("winspool.drv", EntryPoint="EndDocPrinter")]
    public static extern bool EndDocPrinter(IntPtr h);
    [DllImport("winspool.drv", EntryPoint="StartPagePrinter")]
    public static extern bool StartPagePrinter(IntPtr h);
    [DllImport("winspool.drv", EntryPoint="EndPagePrinter")]
    public static extern bool EndPagePrinter(IntPtr h);
    [DllImport("winspool.drv", EntryPoint="WritePrinter")]
    public static extern bool WritePrinter(IntPtr h, byte[] b, int c, ref int w);
}
[System.Runtime.InteropServices.StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential, CharSet=System.Runtime.InteropServices.CharSet.Ansi)]
public struct DOCINFO {
    [System.Runtime.InteropServices.MarshalAs(System.Runtime.InteropServices.UnmanagedType.LPStr)] public string pDocName;
    [System.Runtime.InteropServices.MarshalAs(System.Runtime.InteropServices.UnmanagedType.LPStr)] public string pOutputFile;
    [System.Runtime.InteropServices.MarshalAs(System.Runtime.InteropServices.UnmanagedType.LPStr)] public string pDataType;
}
'@
$h = [IntPtr]::Zero
[RawPrint]::OpenPrinter($PrinterName, [ref]$h, [IntPtr]::Zero) | Out-Null
$di = New-Object DOCINFO; $di.pDocName = 'eISA-Fis'; $di.pDataType = 'RAW'
[RawPrint]::StartDocPrinter($h, 1, [ref]$di) | Out-Null
[RawPrint]::StartPagePrinter($h) | Out-Null
$w = 0; [RawPrint]::WritePrinter($h, $bytes, $bytes.Length, [ref]$w) | Out-Null
[RawPrint]::EndPagePrinter($h) | Out-Null
[RawPrint]::EndDocPrinter($h) | Out-Null
[RawPrint]::ClosePrinter($h) | Out-Null
`;

  try {
    fs.writeFileSync(dataFile, buffer);
    fs.writeFileSync(scriptFile, ps1, 'utf8');
    execSync(
      `powershell -NoProfile -ExecutionPolicy Bypass -File "${scriptFile}" -DataFile "${dataFile}" -PrinterName "${resolvedName}"`,
      { timeout: 15000 },
    );
    log?.info?.({ printer: resolvedName || '(default)' }, 'Windows Spooler gonderimi tamamlandi');
  } finally {
    try { fs.unlinkSync(dataFile); } catch { /* temizlik */ }
    try { fs.unlinkSync(scriptFile); } catch { /* temizlik */ }
  }
}

/**
 * Cihaz dosyası için: writeFileSync (senkron) — hata throw eder.
 * TCP için: async — hata yalnız log'lanır, throw etmez.
 *
 * "Transport başarısı" tanımı: bu fonksiyon throw etmedi.
 * ESC/POS yazıcı fiziksel baskıyı teyit edemez; bu kısıt kodda kabul edilir.
 */
export function sendToTransport({ buffer, host, port = 9100, logger }) {
  const log = logger ?? null;
  if (!host) return;
  // Linux device path (/dev/usb/lp0 vb.) veya Windows port (C:\, COM3, USB001, LPT1 vb.)
  const isFilePath = host.startsWith('/') || /^[A-Za-z]:[/\\]/.test(host)
    || host.startsWith('\\\\') || /^(COM|USB|LPT)\d+$/i.test(host);
  if (isFilePath) {
    // COM3 / USB001 / LPT1 → \\.\COM3 / \\.\USB001 / \\.\LPT1
    const target = /^(COM|USB|LPT)\d+$/i.test(host) ? `\\\\.\\${host}` : host;
    fs.writeFileSync(target, buffer); // sync: throw olursa caller yakalar
    return;
  }
  // Windows yazıcı adı: 'default', 'POS-80', 'EPSON TM-T20' vb.
  // TCP IP adresi veya hostname değilse Windows Spooler üzerinden gönder
  const looksLikeTcp = /^\d{1,3}(\.\d{1,3}){3}$/.test(host) || /^[a-z0-9][a-z0-9.-]*\.[a-z]{2,}$/i.test(host);
  if (!looksLikeTcp && process.platform === 'win32') {
    sendToWindowsSpooler(buffer, host, log); // sync, throw olursa caller yakalar
    return;
  }
  // TCP / IP
  const socket = new net.Socket();
  socket.setTimeout(4000);
  socket.once('error', (err) => log?.warn?.({ err: err.message }, 'Termal yazici TCP hatasi'));
  socket.once('timeout', () => { log?.warn?.('Termal yazici zaman asimi'); socket.destroy(); });
  socket.connect(port, host, () => { socket.write(buffer, () => socket.end()); });
}

/**
 * Geriye dönük uyumluluk wrapper'ı (eski testler ve idempotency re-delivery).
 * Yeni kod buildReceiptBuffer + sendToTransport kullanmalı.
 */
export function printReceipt({ qrCode, qrPayload, barkodLogoPath, host, port = 9100, logger }) {
  const log = logger ?? console;
  if (!host) {
    log.info?.({ qrCode }, 'Termal yazici yapilandirilmamis — fis atlandi.');
    return { logoBasildi: false };
  }
  const candidates = barkodLogoPath ? [{ id: '__legacy__', local_path: barkodLogoPath }] : [];
  const { buffer, logoId } = buildReceiptBuffer({ qrPayload, logoCandidates: candidates, logger: log });
  const logoBasildi = (logoId !== null);
  try {
    sendToTransport({ buffer, host, port, logger: log });
  } catch (err) {
    log.warn?.({ err: err?.message }, 'Termal yazici gonderilemedi');
    return { logoBasildi: false };
  }
  return { logoBasildi };
}
