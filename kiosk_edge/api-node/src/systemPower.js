import { spawn } from 'node:child_process';

const COMMANDS = Object.freeze({
  win32: {
    restart: ['shutdown.exe', ['/r', '/t', '0']],
    shutdown: ['shutdown.exe', ['/s', '/t', '0']],
  },
  linux: {
    restart: ['systemctl', ['reboot']],
    shutdown: ['systemctl', ['poweroff']],
  },
});

/**
 * HTTP yanitinin UI'a ulasabilmesi icin guc komutunu kisa bir gecikmeyle baslatir.
 * Komut shell kullanmadan calistirilir; kullanici girdisi komuta aktarilmaz.
 */
export function schedulePowerAction(action, {
  platform = process.platform,
  spawnImpl = spawn,
  delayMs = 1200,
  logger = console,
} = {}) {
  if (action !== 'restart' && action !== 'shutdown') {
    throw new Error(`Desteklenmeyen guc islemi: ${action}`);
  }
  const command = COMMANDS[platform]?.[action];
  if (!command) throw new Error(`Guc islemi bu platformda desteklenmiyor: ${platform}`);

  const timer = setTimeout(() => {
    try {
      const child = spawnImpl(command[0], command[1], { detached: true, stdio: 'ignore' });
      child.once?.('error', (err) => logger?.error?.({ err: err?.message, action }, 'Cihaz guc komutu basarisiz'));
      child.unref?.();
    } catch (err) {
      logger?.error?.({ err: err?.message, action }, 'Cihaz guc komutu baslatilamadi');
    }
  }, delayMs);
  timer.unref?.();
  return timer;
}
