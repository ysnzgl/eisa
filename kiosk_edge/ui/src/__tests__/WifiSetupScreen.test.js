/**
 * WifiSetupScreen Wi-Fi reconciliation testleri.
 *
 * /wifi-connect'in OS düzeyinde bağlantı kurulmasına rağmen hata dönmesi
 * (yanlış-negatif) durumunu ele alan reconciliation mantığını doğrular.
 *
 * Gerçek Wi-Fi veya nmcli kullanılmaz; api.js fonksiyonları mock'lanır.
 */
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, waitFor, fireEvent } from '@testing-library/svelte';

vi.mock('../lib/api.js', () => ({
  fetchWifiNetworks: vi.fn(),
  connectToWifi: vi.fn(),
  fetchWifiStatus: vi.fn(),
}));

import { fetchWifiNetworks, connectToWifi, fetchWifiStatus } from '../lib/api.js';
import WifiSetupScreen from '../components/WifiSetupScreen.svelte';

const SSID = 'MedinceAP';
// Şifresiz ağ: testlerde şifre girişini simüle etmeye gerek kalmaz;
// reconciliation mantığı secured/open ağdan bağımsızdır.
const OPEN_NETWORK = { ssid: SSID, signal: 80, secured: false };

/** Bileşeni render eder, taramayı bekler ve test ağını seçer. */
async function renderAndSelect() {
  fetchWifiNetworks.mockResolvedValue([OPEN_NETWORK]);
  const result = render(WifiSetupScreen);
  await waitFor(() => result.getByText(SSID));
  fireEvent.click(result.getByText(SSID));
  await waitFor(() => result.getByRole('button', { name: /Ağa bağlan/i }));
  return result;
}

describe('WifiSetupScreen — Wi-Fi reconciliation', () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it('başarılı /wifi-connect → connected eventi bir kez gönderilir, /wifi-status sorgulanmaz', async () => {
    connectToWifi.mockResolvedValue({ success: true, message: 'Bağlantı başarılı.' });

    const { component, getByRole } = await renderAndSelect();
    const onConnected = vi.fn();
    component.$on('connected', onConnected);

    fireEvent.click(getByRole('button', { name: /Ağa bağlan/i }));

    await waitFor(() => expect(onConnected).toHaveBeenCalledTimes(1));
    expect(fetchWifiStatus).not.toHaveBeenCalled();
  });

  it('/wifi-connect hata + /wifi-status seçili SSID bağlı → hata yok, connected bir kez', async () => {
    connectToWifi.mockRejectedValue(
      Object.assign(new Error('nmcli timeout'), { userMessage: 'Zaman aşımı.' }),
    );
    fetchWifiStatus.mockResolvedValue({ connected: true, ssid: SSID });

    const { component, container, getByRole } = await renderAndSelect();
    const onConnected = vi.fn();
    component.$on('connected', onConnected);

    vi.useFakeTimers();
    fireEvent.click(getByRole('button', { name: /Ağa bağlan/i }));
    await vi.runAllTimersAsync();
    vi.useRealTimers();

    expect(onConnected).toHaveBeenCalledTimes(1);
    expect(container.querySelector('.connect-error')).toBeNull();
  });

  it('/wifi-connect hata + Wi-Fi bağlı değil → hata gösterilir, connected yok', async () => {
    connectToWifi.mockRejectedValue(new Error('wrong password'));
    fetchWifiStatus.mockResolvedValue({ connected: false, ssid: null });

    const { component, container, getByRole } = await renderAndSelect();
    const onConnected = vi.fn();
    component.$on('connected', onConnected);

    vi.useFakeTimers();
    fireEvent.click(getByRole('button', { name: /Ağa bağlan/i }));
    await vi.runAllTimersAsync();
    vi.useRealTimers();

    expect(onConnected).not.toHaveBeenCalled();
    await waitFor(() => expect(container.querySelector('.connect-error')).not.toBeNull());
  });

  it('başka SSID bağlıysa seçili ağ başarı sayılmaz → hata gösterilir', async () => {
    connectToWifi.mockRejectedValue(new Error('rejected'));
    fetchWifiStatus.mockResolvedValue({ connected: true, ssid: 'DigerAg' });

    const { component, container, getByRole } = await renderAndSelect();
    const onConnected = vi.fn();
    component.$on('connected', onConnected);

    vi.useFakeTimers();
    fireEvent.click(getByRole('button', { name: /Ağa bağlan/i }));
    await vi.runAllTimersAsync();
    vi.useRealTimers();

    expect(onConnected).not.toHaveBeenCalled();
    await waitFor(() => expect(container.querySelector('.connect-error')).not.toBeNull());
  });

  it('component unmount olduğunda bekleyen poll devam etmez', async () => {
    connectToWifi.mockRejectedValue(new Error('rejected'));
    let statusCallCount = 0;
    fetchWifiStatus.mockImplementation(async () => {
      statusCallCount++;
      return { connected: false, ssid: null };
    });

    const { component, getByRole, unmount } = await renderAndSelect();
    component.$on('connected', vi.fn());

    vi.useFakeTimers();
    fireEvent.click(getByRole('button', { name: /Ağa bağlan/i }));

    // İlk 2 saniyelik poll aralığını geç; ilk /wifi-status çağrısı tamamlanır.
    await vi.advanceTimersByTimeAsync(2500);
    const callsAfterFirst = statusCallCount;

    // İkinci poll bekliyorken unmount: onDestroy bekleyen timer'ı iptal eder.
    unmount();
    await vi.runAllTimersAsync();
    vi.useRealTimers();

    expect(statusCallCount).toBe(callsAfterFirst);
  });

  it('polling sınırlıdır; başarısız durumda en fazla 3 (RECONCILE_ATTEMPTS) kez sorgulanır', async () => {
    connectToWifi.mockRejectedValue(new Error('rejected'));
    fetchWifiStatus.mockResolvedValue({ connected: false, ssid: null });

    const { component, getByRole } = await renderAndSelect();
    const onConnected = vi.fn();
    component.$on('connected', onConnected);

    vi.useFakeTimers();
    fireEvent.click(getByRole('button', { name: /Ağa bağlan/i }));
    await vi.runAllTimersAsync();
    vi.useRealTimers();

    expect(fetchWifiStatus).toHaveBeenCalledTimes(3);
    expect(onConnected).not.toHaveBeenCalled();
  });
});
