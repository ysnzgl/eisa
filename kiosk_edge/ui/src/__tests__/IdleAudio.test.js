import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { createIdleAudioController, isIdleAudioAllowed } from '../lib/idleAudioController.js';


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

  it('kullanıcı etkileşiminde sesi keser ve aynı idle çevriminde yeniden başlatmaz', async () => {
    controller.update(true, config);
    await vi.advanceTimersByTimeAsync(1_200_000);
    controller.interact();
    await vi.advanceTimersByTimeAsync(2_000_000);
    expect(stop).toHaveBeenCalled();
    expect(play).toHaveBeenCalledTimes(1);
    expect(states.at(-1)).toBe(false);
  });

  it('idle ekranından çıkıp dönünce ilk gecikme ve sıra sıfırlanır', async () => {
    controller.update(true, config);
    await vi.advanceTimersByTimeAsync(600_000);
    controller.update(false, config);
    controller.update(true, config);
    await vi.advanceTimersByTimeAsync(1_199_999);
    expect(play).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1);
    expect(play).toHaveBeenCalledWith(config.idle_audio.files[0]);
  });

  it('idle olmayan ekranda sesi başlatmaz', async () => {
    controller.update(false, config);
    await vi.advanceTimersByTimeAsync(2_000_000);
    expect(play).not.toHaveBeenCalled();
  });
});

describe('Idle ses zaman kuralı', () => {
  const weekdayMorning = new Date('2026-09-14T07:30:00.000Z'); // Istanbul 10:30
  const weekdayNight = new Date('2026-09-14T18:30:00.000Z'); // Istanbul 21:30

  it('24 saat kuralında günün her saatinde izin verir', () => {
    expect(isIdleAudioAllowed({ idle_audio_schedule_mode: 'ALL_DAY' }, weekdayNight)).toBe(true);
  });

  it('mesai içi kuralını Istanbul 08:00–19:00 ile sınırlar', () => {
    expect(isIdleAudioAllowed({ idle_audio_schedule_mode: 'BUSINESS_HOURS' }, weekdayMorning)).toBe(true);
    expect(isIdleAudioAllowed({ idle_audio_schedule_mode: 'BUSINESS_HOURS' }, weekdayNight)).toBe(false);
  });

  it('nöbet günü seçiliyse mesai dışındaki saatte de izin verir', () => {
    expect(isIdleAudioAllowed({
      idle_audio_schedule_mode: 'BUSINESS_HOURS', idle_audio_play_on_duty: true,
      idle_audio_duty_dates: ['2026-09-14'],
    }, weekdayNight)).toBe(true);
  });
});
