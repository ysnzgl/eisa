<script>
  import { createEventDispatcher, onMount } from 'svelte';
  import { fetchWifiNetworks, connectToWifi } from '../lib/api.js';

  const dispatch = createEventDispatcher();

  /** @type {Array<{ssid: string, signal: number, secured: boolean}>} */
  let networks     = [];
  let scanning     = true;
  let scanError    = '';

  let selectedSsid = null;
  let password     = '';
  let connecting   = false;
  let connectError = '';
  let showPassword = false;

  // ── sinyal çubuğu yardımcısı ──────────────────────────────────────────
  function signalBars(signal) {
    if (signal >= 75) return 4;
    if (signal >= 50) return 3;
    if (signal >= 25) return 2;
    return 1;
  }

  // ── ağları tara ───────────────────────────────────────────────────────
  async function scan() {
    scanning     = true;
    scanError    = '';
    selectedSsid = null;
    password     = '';
    connectError = '';
    try {
      networks = await fetchWifiNetworks();
      if (!networks.length) scanError = 'Çevrede WiFi ağı bulunamadı.';
    } catch (err) {
      scanError = err.userMessage ?? 'Ağ tarama başarısız.';
    } finally {
      scanning = false;
    }
  }

  // ── seç ───────────────────────────────────────────────────────────────
  function selectNetwork(net) {
    selectedSsid = net.ssid;
    password     = '';
    connectError = '';
  }

  // ── bağlan ────────────────────────────────────────────────────────────
  async function connect() {
    if (!selectedSsid) return;
    connecting   = true;
    connectError = '';
    try {
      await connectToWifi(selectedSsid, password || undefined);
      dispatch('connected');
    } catch (err) {
      connectError = err.userMessage ?? 'Bağlantı kurulamadı. Şifreyi kontrol edin.';
    } finally {
      connecting = false;
    }
  }

  onMount(scan);
</script>

<!-- ── WiFi Kurulum Ekranı ────────────────────────────────────────────── -->
<div class="wifi-screen">

  <!-- Başlık -->
  <div class="wifi-header">
    <div class="wifi-icon">
      <i class="fa-solid fa-wifi"></i>
    </div>
    <h1 class="wifi-title">WiFi Bağlantısı Gerekli</h1>
    <p class="wifi-subtitle">
      Kiosk internete bağlı değil. Lütfen bir WiFi ağı seçin.
    </p>
  </div>

  <!-- Ağ listesi -->
  <div class="wifi-list-container">
    {#if scanning}
      <div class="wifi-loading">
        <i class="fa-solid fa-circle-notch fa-spin"></i>
        <span>Ağlar taranıyor…</span>
      </div>
    {:else if scanError}
      <div class="wifi-empty">
        <i class="fa-solid fa-triangle-exclamation"></i>
        <span>{scanError}</span>
      </div>
    {:else}
      <ul class="wifi-list" role="listbox" aria-label="WiFi ağları">
        {#each networks as net (net.ssid)}
          <!-- svelte-ignore a11y-click-events-have-key-events -->
          <li
            class="wifi-item"
            class:wifi-item--selected={selectedSsid === net.ssid}
            role="option"
            aria-selected={selectedSsid === net.ssid}
            on:click={() => selectNetwork(net)}
          >
            <!-- Sinyal çubukları -->
            <div class="signal-bars" aria-label="Sinyal: {net.signal}%">
              {#each [1, 2, 3, 4] as bar}
                <span
                  class="bar"
                  class:bar--active={bar <= signalBars(net.signal)}
                ></span>
              {/each}
            </div>

            <span class="ssid-text">{net.ssid}</span>

            {#if net.secured}
              <i class="fa-solid fa-lock lock-icon" title="Şifreli"></i>
            {:else}
              <i class="fa-solid fa-lock-open lock-icon lock-icon--open" title="Açık ağ"></i>
            {/if}
          </li>
        {/each}
      </ul>
    {/if}
  </div>

  <!-- Şifre alanı (seçili ağ şifreliyse göster) -->
  {#if selectedSsid}
    {@const selectedNet = networks.find(n => n.ssid === selectedSsid)}
    <div class="wifi-password-area">
      <p class="selected-label">
        <i class="fa-solid fa-wifi"></i>
        <strong>{selectedSsid}</strong>
      </p>

      {#if selectedNet?.secured}
        <div class="password-field">
          <label for="wifi-password" class="visually-hidden">WiFi Şifresi</label>
          <input
            id="wifi-password"
            type={showPassword ? 'text' : 'password'}
            placeholder="WiFi şifresini girin"
            bind:value={password}
            class="password-input"
            autocomplete="off"
            spellcheck="false"
          />
          <button
            type="button"
            class="toggle-password"
            on:click={() => (showPassword = !showPassword)}
            aria-label={showPassword ? 'Şifreyi gizle' : 'Şifreyi göster'}
          >
            <i class="fa-solid {showPassword ? 'fa-eye-slash' : 'fa-eye'}"></i>
          </button>
        </div>
      {/if}

      {#if connectError}
        <p class="connect-error">
          <i class="fa-solid fa-circle-exclamation"></i>
          {connectError}
        </p>
      {/if}

      <button
        class="btn-connect"
        on:click={connect}
        disabled={connecting || (selectedNet?.secured && !password)}
      >
        {#if connecting}
          <i class="fa-solid fa-circle-notch fa-spin"></i>
          Bağlanıyor…
        {:else}
          <i class="fa-solid fa-plug-circle-bolt"></i>
          Bağlan
        {/if}
      </button>
    </div>
  {/if}

  <!-- Alt araçlar -->
  <div class="wifi-footer">
    <button class="btn-rescan" on:click={scan} disabled={scanning || connecting}>
      <i class="fa-solid fa-arrows-rotate" class:fa-spin={scanning}></i>
      Yeniden Tara
    </button>
  </div>

</div>

<style>
  /* ── Kap ─────────────────────────────────────────────────────────────── */
  .wifi-screen {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: #F9FAFB;
    padding: 32px 40px 24px;
    gap: 20px;
    overflow: hidden;
  }

  /* ── Başlık ────────────────────────────────────────────────────────── */
  .wifi-header {
    text-align: center;
  }

  .wifi-icon {
    font-size: 48px;
    color: #6366F1;
    margin-bottom: 12px;
  }

  .wifi-title {
    font-size: 22px;
    font-weight: 700;
    color: #111827;
    margin: 0 0 6px;
  }

  .wifi-subtitle {
    font-size: 14px;
    color: #6B7280;
    margin: 0;
  }

  /* ── Liste ──────────────────────────────────────────────────────────── */
  .wifi-list-container {
    flex: 1;
    overflow-y: auto;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    background: #fff;
  }

  .wifi-loading,
  .wifi-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
    padding: 40px 20px;
    color: #6B7280;
    font-size: 15px;
  }

  .wifi-loading i,
  .wifi-empty i {
    font-size: 28px;
    color: #9CA3AF;
  }

  .wifi-list {
    list-style: none;
    margin: 0;
    padding: 8px 0;
  }

  .wifi-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 20px;
    cursor: pointer;
    border-bottom: 1px solid #F3F4F6;
    transition: background 0.15s;
  }

  .wifi-item:last-child {
    border-bottom: none;
  }

  .wifi-item:hover {
    background: #F3F4F6;
  }

  .wifi-item--selected {
    background: #EEF2FF;
    border-left: 3px solid #6366F1;
  }

  /* Sinyal çubukları */
  .signal-bars {
    display: flex;
    align-items: flex-end;
    gap: 2px;
    width: 20px;
    height: 16px;
    flex-shrink: 0;
  }

  .bar {
    flex: 1;
    background: #D1D5DB;
    border-radius: 2px;
  }

  .bar:nth-child(1) { height: 25%; }
  .bar:nth-child(2) { height: 50%; }
  .bar:nth-child(3) { height: 75%; }
  .bar:nth-child(4) { height: 100%; }

  .bar--active {
    background: #6366F1;
  }

  .ssid-text {
    flex: 1;
    font-size: 15px;
    font-weight: 500;
    color: #111827;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .lock-icon {
    font-size: 13px;
    color: #6B7280;
  }

  .lock-icon--open {
    color: #10B981;
  }

  /* ── Şifre Alanı ────────────────────────────────────────────────────── */
  .wifi-password-area {
    background: #fff;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    padding: 16px 20px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .selected-label {
    margin: 0;
    font-size: 14px;
    color: #374151;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .selected-label i {
    color: #6366F1;
  }

  .password-field {
    display: flex;
    align-items: center;
    gap: 8px;
    border: 1px solid #D1D5DB;
    border-radius: 8px;
    overflow: hidden;
    background: #F9FAFB;
  }

  .password-input {
    flex: 1;
    border: none;
    background: transparent;
    padding: 10px 14px;
    font-size: 16px;
    color: #111827;
    outline: none;
  }

  .toggle-password {
    background: transparent;
    border: none;
    padding: 10px 14px;
    cursor: pointer;
    color: #6B7280;
    font-size: 15px;
    line-height: 1;
  }

  .toggle-password:hover {
    color: #374151;
  }

  .connect-error {
    margin: 0;
    font-size: 13px;
    color: #DC2626;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .btn-connect {
    background: #6366F1;
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 12px 20px;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    transition: background 0.2s, opacity 0.2s;
  }

  .btn-connect:hover:not(:disabled) {
    background: #4F46E5;
  }

  .btn-connect:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  /* ── Alt Araçlar ────────────────────────────────────────────────────── */
  .wifi-footer {
    display: flex;
    justify-content: center;
  }

  .btn-rescan {
    background: transparent;
    border: 1px solid #D1D5DB;
    border-radius: 8px;
    padding: 8px 20px;
    font-size: 13px;
    color: #6B7280;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 8px;
    transition: border-color 0.15s, color 0.15s;
  }

  .btn-rescan:hover:not(:disabled) {
    border-color: #6366F1;
    color: #6366F1;
  }

  .btn-rescan:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  /* ── Erişilebilirlik ────────────────────────────────────────────────── */
  .visually-hidden {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
  }
</style>
