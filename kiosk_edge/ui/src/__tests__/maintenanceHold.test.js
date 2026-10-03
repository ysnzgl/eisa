import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createMaintenanceHold } from '../lib/maintenanceHold.js';

describe('Idle logo bakim menusu uzun basma', () => {
  let onShortPress;
  let onLongPress;
  let states;
  let progress;
  let hold;

  beforeEach(() => {
    vi.useFakeTimers();
    onShortPress = vi.fn();
    onLongPress = vi.fn();
    states = [];
    progress = [];
    hold = createMaintenanceHold({
      durationMs: 10_000,
      onHoldingChange: (value) => states.push(value),
      onProgress: (percent, seconds) => progress.push([percent, seconds]),
      onShortPress,
      onLongPress,
    });
  });

  afterEach(() => {
    hold.destroy();
    vi.useRealTimers();
  });

  it('kisa dokunusta normal kiosk akisini baslatir', () => {
    hold.begin();
    vi.advanceTimersByTime(9999);
    hold.end();
    expect(onShortPress).toHaveBeenCalledOnce();
    expect(onLongPress).not.toHaveBeenCalled();
  });

  it('10 saniye sonunda yalniz bakim menusunu acar', () => {
    hold.begin();
    vi.advanceTimersByTime(10_000);
    hold.end();
    expect(onLongPress).toHaveBeenCalledOnce();
    expect(onShortPress).not.toHaveBeenCalled();
    expect(states).toEqual([true, false, false]);
    expect(progress).toContainEqual([100, 0]);
  });

  it('basili tutarken kalan saniyeyi ve ilerlemeyi bildirir', () => {
    hold.begin();
    vi.advanceTimersByTime(4100);
    expect(progress.at(-1)).toEqual([41, 6]);
  });

  it('iptal edilen basma hicbir islem calistirmaz', () => {
    hold.begin();
    vi.advanceTimersByTime(5000);
    hold.cancel();
    vi.advanceTimersByTime(5000);
    expect(onLongPress).not.toHaveBeenCalled();
    expect(onShortPress).not.toHaveBeenCalled();
  });
});
