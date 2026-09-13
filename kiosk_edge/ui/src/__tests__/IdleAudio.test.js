import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { createIdleAudioController, formatIdleAudioDebugText, isIdleAudioAllowed } from '../lib/idleAudioController.js';


describe('IdleAudio durum makinesi', () => {
  let play;
  let stop;
  let states;
  let controller;
  const config = {
    idle_audio_delay_seconds: 1200,
    idle_audio_repeat_seconds: 300,
    idle_audio: {
      enabled: true,
      files: [
        { id: 'one', media_url: '/api/device-audio/one' },
        { id: 'two', media_url: '/api/device-audio/two' },
      ],
    },
  };

  beforeEach(() => {
    vi.useFakeTimers();
    play = vi.fn().mockResolvedValue();
    stop = vi.fn();
    states = [];
    controller = createIdleAudioController({
      play,
      stop,
      onPlayingChange: (value) => states.push(value),
    });
  });

  afterEach(() => {
    controller.destroy();
    vi.useRealTimers();
  });

  it('ilk sesi kesintisiz 20 dakika sonra başlatır', async () => {
    controller.update(true, config);
    await vi.advanceTimersByTimeAsync(1_199_999);
    expect(play).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1);
    expect(play).toHaveBeenCalledWith(config.idle_audio.files[0]);
    expect(states.at(-1)).toBe(true);
  });

  it('ses bittikten 5 dakika sonra sıradaki dosyayı çalar', async () => {
    controller.update(true, config);
    await vi.advanceTimersByTimeAsync(1_200_000);
    controller.ended();
    await vi.advanceTimersByTimeAsync(299_999);
    expect(play).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1);
    expect(play).toHaveBeenNthCalledWith(2, config.idle_audio.files[1]);
  });

  it('listenin sonundan sonra tekrar ilk dosyaya döner', async () => {
    controller.update(true, config);
    await vi.advanceTimersByTimeAsync(1_200_000);
    controller.ended();
    await vi.advanceTimersByTimeAsync(300_000);
    controller.ended();
    await vi.advanceTimersByTimeAsync(300_000);
    expect(play).toHaveBeenNthCalledWith(3, config.idle_audio.files[0]);
  });

  it('QR zamanı yoksa idle ekrandaki dokunuş sesi keser ve devam süresinde sıradaki sesi çalar', async () => {
    controller.update(true, config);
    await vi.advanceTimersByTimeAsync(1_200_000);
    controller.interact();
    expect(stop).toHaveBeenCalled();
    expect(play).toHaveBeenCalledTimes(1);
    expect(states.at(-1)).toBe(false);
    await vi.advanceTimersByTimeAsync(300_000);
    expect(play).toHaveBeenNthCalledWith(2, config.idle_audio.files[1]);
  });

  it('idle ekranından çıkıp dönünce ilk gecikme kurulur', async () => {
    controller.update(true, config);
    await vi.advanceTimersByTimeAsync(600_000);
    controller.update(false, config);
    controller.update(true, config);
    await vi.advanceTimersByTimeAsync(1_199_999);
    expect(play).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1);
    expect(play).toHaveBeenCalledWith(config.idle_audio.files[0]);
  });

  it('idle ekranından çıkıp dönünce ses sırasını başa sarmaz', async () => {
    controller.update(true, config);
    await vi.advanceTimersByTimeAsync(1_200_000);
    controller.update(false, config);
    controller.update(true, config);
    await vi.advanceTimersByTimeAsync(1_200_000);
    expect(play).toHaveBeenNthCalledWith(1, config.idle_audio.files[0]);
    expect(play).toHaveBeenNthCalledWith(2, config.idle_audio.files[1]);
  });

  it('idle olmayan ekranda sesi başlatmaz', async () => {
    controller.update(false, config);
    await vi.advanceTimersByTimeAsync(2_000_000);
    expect(play).not.toHaveBeenCalled();
  });

  it('16 dosyanın tamamını tanımlı sırayla çalar', async () => {
    const files = Array.from({ length: 16 }, (_, index) => ({
      id: String(index + 1), media_url: `/api/device-audio/${index + 1}`,
    }));
    controller.update(true, { ...config, idle_audio: { enabled: true, files } });
    await vi.advanceTimersByTimeAsync(1_200_000);
    for (let index = 1; index < files.length; index += 1) {
      controller.ended();
      await vi.advanceTimersByTimeAsync(300_000);
    }
    expect(play).toHaveBeenCalledTimes(16);
    expect(play.mock.calls.map(([file]) => file.id)).toEqual(files.map((file) => file.id));
  });

  it('bir dosya oynatılamazsa devam süresi sonunda sıradaki dosyayı dener', async () => {
    play.mockRejectedValueOnce(new Error('bozuk dosya')).mockResolvedValue();
    controller.update(true, config);
    await vi.advanceTimersByTimeAsync(1_200_000);
    await vi.advanceTimersByTimeAsync(300_000);
    expect(play).toHaveBeenNthCalledWith(1, config.idle_audio.files[0]);
    expect(play).toHaveBeenNthCalledWith(2, config.idle_audio.files[1]);
  });

  it('debug sayaç için sese kalan süreyi bildirir', async () => {
    controller.update(true, config);
    expect(controller.getDebugState().remainingSeconds).toBe(1200);
    await vi.advanceTimersByTimeAsync(1_000);
    expect(controller.getDebugState().remainingSeconds).toBe(1199);
    await vi.advanceTimersByTimeAsync(1_199_000);
    expect(controller.getDebugState().playing).toBe(true);
    expect(controller.getDebugState().remainingSeconds).toBeNull();
    controller.ended();
    expect(controller.getDebugState().remainingSeconds).toBe(300);
  });

  it('ilk beklemeyi ekran değişiminden değil son QR kayıt zamanından hesaplar', async () => {
    vi.setSystemTime(new Date('2026-09-13T10:20:00.000Z'));
    controller.update(true, {
      ...config,
      idle_audio_last_qr_created_at: '2026-09-13T10:18:00.000Z',
    });
    expect(controller.getDebugState().remainingSeconds).toBe(1080);

    await vi.advanceTimersByTimeAsync(1_079_000);
    expect(play).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1_000);
    expect(play).toHaveBeenCalledWith(config.idle_audio.files[0]);
  });

  it('son QR üzerinden ilk süre aşılmışsa devam süresini kurar', async () => {
    vi.setSystemTime(new Date('2026-09-13T10:30:00.000Z'));
    controller.update(true, {
      ...config,
      idle_audio_last_qr_created_at: '2026-09-13T10:05:00.000Z',
    });
    expect(controller.getDebugState().remainingSeconds).toBe(300);

    await vi.advanceTimersByTimeAsync(299_999);
    expect(play).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1);
    expect(play).toHaveBeenCalledWith(config.idle_audio.files[0]);
  });

  it('yeni QR zamanı geldiğinde sayacı ilk süreye göre yeniden kurar', () => {
    vi.setSystemTime(new Date('2026-09-13T10:30:00.000Z'));
    controller.update(true, {
      ...config,
      idle_audio_last_qr_created_at: '2026-09-13T10:05:00.000Z',
    });
    expect(controller.getDebugState().remainingSeconds).toBe(300);

    controller.update(true, {
      ...config,
      idle_audio_last_qr_created_at: '2026-09-13T10:30:00.000Z',
    });
    expect(controller.getDebugState().remainingSeconds).toBe(1200);
  });

  it('idle ekrandaki dokunuş son QR bazlı beklemeyi başa sarmaz', async () => {
    vi.setSystemTime(new Date('2026-09-13T10:20:00.000Z'));
    controller.update(true, {
      ...config,
      idle_audio_last_qr_created_at: '2026-09-13T10:02:00.000Z',
    });
    expect(controller.getDebugState().remainingSeconds).toBe(120);

    await vi.advanceTimersByTimeAsync(60_000);
    controller.interact();
    expect(controller.getDebugState().remainingSeconds).toBe(60);
  });

  it('ilk süre aşıldıktan sonra idle dokunuşu devam sayacını sıfırlamaz', async () => {
    vi.setSystemTime(new Date('2026-09-13T10:30:00.000Z'));
    controller.update(true, {
      ...config,
      idle_audio_last_qr_created_at: '2026-09-13T10:05:00.000Z',
    });
    await vi.advanceTimersByTimeAsync(60_000);
    controller.interact();
    expect(controller.getDebugState().remainingSeconds).toBe(240);
  });

  it('debug sayaç metnini toplam saniye olarak üretir', () => {
    expect(formatIdleAudioDebugText({
      enabled: true,
      fileCount: 1,
      allowedNow: true,
      playing: false,
      remainingSeconds: 120,
    })).toBe('120 sn');
    expect(formatIdleAudioDebugText({
      enabled: true,
      fileCount: 1,
      allowedNow: true,
      playing: false,
      remainingSeconds: 119,
    })).toBe('119 sn');
  });
});

describe('Idle ses zaman kuralı', () => {
  const weekdayMorning = new Date('2026-09-14T07:30:00.000Z'); // Istanbul 10:30
  const weekdayAfterHours = new Date('2026-09-14T16:00:00.000Z'); // Istanbul 19:00

  it('24 saat kuralında günün her saatinde izin verir', () => {
    expect(isIdleAudioAllowed({ idle_audio_schedule_mode: 'ALL_DAY' }, weekdayAfterHours)).toBe(true);
  });

  it('mesai içi kuralını Istanbul 08:00–19:00 ile sınırlar', () => {
    expect(isIdleAudioAllowed({ idle_audio_schedule_mode: 'BUSINESS_HOURS' }, weekdayMorning)).toBe(true);
    expect(isIdleAudioAllowed({ idle_audio_schedule_mode: 'BUSINESS_HOURS' }, weekdayAfterHours)).toBe(false);
  });

  it('nöbet günü seçiliyse mesai dışındaki saatte de izin verir', () => {
    expect(isIdleAudioAllowed({
      idle_audio_schedule_mode: 'BUSINESS_HOURS', idle_audio_play_on_duty: true,
      idle_audio_duty_dates: ['2026-09-14'],
    }, weekdayAfterHours)).toBe(true);
  });
});
