import { describe, expect, it, vi } from 'vitest';
import { schedulePowerAction } from '../src/systemPower.js';

describe('schedulePowerAction', () => {
  it('Windows yeniden baslatma komutunu shell kullanmadan olusturur', () => {
    vi.useFakeTimers();
    const child = { once: vi.fn(), unref: vi.fn() };
    const spawnImpl = vi.fn(() => child);
    schedulePowerAction('restart', { platform: 'win32', spawnImpl, delayMs: 10 });
    vi.advanceTimersByTime(10);
    expect(spawnImpl).toHaveBeenCalledWith(
      'shutdown.exe', ['/r', '/t', '0'], { detached: true, stdio: 'ignore' },
    );
    expect(child.unref).toHaveBeenCalled();
    vi.useRealTimers();
  });

  it('Linux kapatma icin systemctl poweroff kullanir', () => {
    vi.useFakeTimers();
    const spawnImpl = vi.fn(() => ({ once: vi.fn(), unref: vi.fn() }));
    schedulePowerAction('shutdown', { platform: 'linux', spawnImpl, delayMs: 10 });
    vi.advanceTimersByTime(10);
    expect(spawnImpl).toHaveBeenCalledWith(
      'systemctl', ['poweroff'], { detached: true, stdio: 'ignore' },
    );
    vi.useRealTimers();
  });

  it('izin verilmeyen islemi reddeder', () => {
    expect(() => schedulePowerAction('format')).toThrow('Desteklenmeyen guc islemi');
  });
});
