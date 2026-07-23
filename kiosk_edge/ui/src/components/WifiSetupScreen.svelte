<script>
  import { createEventDispatcher, onMount } from 'svelte';
  import ScreenHeader from './ScreenHeader.svelte';
  import { fetchWifiNetworks, connectToWifi } from '../lib/api.js';

  const dispatch = createEventDispatcher();
  const MAX_PASSWORD_LENGTH = 128;

  /** @type {Array<{ssid: string, signal: number, secured: boolean}>} */
  let networks = [];
  let scanning = true;
  let scanError = '';
  let selectedSsid = null;
  let password = '';
  let connecting = false;
  let connectError = '';
  let showPassword = false;
  let keyboardMode = 'letters';
  let uppercase = false;

  const letterRows = [
    ['q', 'w', 'e', 'r', 't', 'y', 'u', 'ı', 'o', 'p', 'ğ', 'ü'],
    ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'ş', 'i'],
    ['z', 'x', 'c', 'v', 'b', 'n', 'm', 'ö', 'ç'],
  ];

  const symbolRows = [
    ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
    ['@', '#', '$', '%', '&', '*', '-', '_', '+', '='],
    ['!', '?', '.', ',', ':', ';', '/', '\\', '(', ')'],
    ['[', ']', '{', '}', '<', '>', '^', '~', "'", '"'],
  ];

  $: selectedNet = networks.find((network) => network.ssid === selectedSsid);
  $: canConnect = Boolean(
    selectedNet && !connecting && (!selectedNet.secured || password.length > 0),
  );

  function signalBars(signal) {
    if (signal >= 75) return 4;
    if (signal >= 50) return 3;
    if (signal >= 25) return 2;
    return 1;
  }

  async function scan() {
    scanning = true;
    scanError = '';
    selectedSsid = null;
    password = '';
    connectError = '';
    try {
      networks = await fetchWifiNetworks();
      if (!networks.length) scanError = 'Çevrede Wi-Fi ağı bulunamadı.';
    } catch (err) {
      scanError = err.userMessage ?? 'Ağ taraması başarısız oldu.';
    } finally {
      scanning = false;
    }
  }

  function selectNetwork(network) {
    if (connecting) return;
    selectedSsid = network.ssid;
    password = '';
    connectError = '';
    showPassword = false;
    keyboardMode = 'letters';
    uppercase = false;
  }

  function addKey(key) {
    if (!selectedNet?.secured || connecting || password.length >= MAX_PASSWORD_LENGTH) return;
    const value = uppercase ? key.toLocaleUpperCase('tr-TR') : key;
    password += value;
    connectError = '';
  }

  function backspace() {
    password = Array.from(password).slice(0, -1).join('');
    connectError = '';
  }

  function clearPassword() {
    password = '';
    connectError = '';
  }

  function handlePhysicalKeyboard(event) {
    if (!selectedNet?.secured || connecting) return;

    if (event.key === 'Backspace') {
      event.preventDefault();
      backspace();
      return;
    }

    if (event.key === 'Delete' || event.key === 'Escape') {
      event.preventDefault();
      clearPassword();
      return;
    }

    if (event.key === 'Enter') {
      event.preventDefault();
      if (canConnect) connect();
      return;
    }

    if (!event.ctrlKey && !event.altKey && !event.metaKey && event.key.length === 1) {
      event.preventDefault();
      if (password.length < MAX_PASSWORD_LENGTH) password += event.key;
    }
  }

  async function connect() {
    if (!canConnect || !selectedNet) return;
    connecting = true;
    connectError = '';
    try {
      await connectToWifi(selectedNet.ssid, password || undefined);
      dispatch('connected');
    } catch (err) {
      connectError = err.userMessage ?? 'Bağlantı kurulamadı. Şifreyi kontrol edin.';
    } finally {
      connecting = false;
    }
  }

  onMount(() => {
    scan();
    window.addEventListener('keydown', handlePhysicalKeyboard);
    return () => window.removeEventListener('keydown', handlePhysicalKeyboard);
  });
</script>

<div class="wifi-screen">
  <div class="wifi-topbar">
    <div class="connection-badge">
      <i class="fa-solid fa-wifi"></i>
      Bağlantı kurulumu
    </div>
    <ScreenHeader
      height="50px"
      subtitle="Devam etmek için kullanmak istediğiniz Wi-Fi ağını seçin."
    />
  </div>

  <section class="network-card" class:network-card--compact={Boolean(selectedNet)} aria-labelledby="network-title">
    <div class="section-heading">
      <div>
        <h1 id="network-title">Kullanılabilir ağlar</h1>
        <p>{scanning ? 'Yakındaki ağlar aranıyor…' : `${networks.length} ağ bulundu`}</p>
      </div>
      <button
        type="button"
        class="icon-button"
        on:click={scan}
        disabled={scanning || connecting}
        aria-label="Ağları yeniden tara"
      >
        <i class="fa-solid fa-arrows-rotate" class:fa-spin={scanning}></i>
      </button>
    </div>

    <div class="wifi-list-container">
      {#if scanning}
        <div class="status-state">
          <i class="fa-solid fa-circle-notch fa-spin"></i>
          <strong>Ağlar taranıyor</strong>
          <span>Lütfen kısa bir süre bekleyin.</span>
        </div>
      {:else if scanError}
        <div class="status-state status-state--error">
          <i class="fa-solid fa-triangle-exclamation"></i>
          <strong>{scanError}</strong>
          <button type="button" class="retry-button" on:click={scan}>Tekrar dene</button>
        </div>
      {:else}
        <ul class="wifi-list" aria-label="Wi-Fi ağları">
          {#each networks as network (network.ssid)}
            <li>
              <button
                type="button"
                class="wifi-item"
                class:wifi-item--selected={selectedSsid === network.ssid}
                aria-pressed={selectedSsid === network.ssid}
                on:click={() => selectNetwork(network)}
              >
                <span class="network-icon" aria-hidden="true">
                  <span class="signal-bars">
                    {#each [1, 2, 3, 4] as bar}
                      <span class="bar" class:bar--active={bar <= signalBars(network.signal)}></span>
                    {/each}
                  </span>
                </span>
                <span class="network-copy">
                  <strong>{network.ssid}</strong>
                  <small>Sinyal %{network.signal}</small>
                </span>
                <span class="security-icon" aria-label={network.secured ? 'Şifreli ağ' : 'Açık ağ'}>
                  <i class="fa-solid {network.secured ? 'fa-lock' : 'fa-lock-open'}"></i>
                </span>
                {#if selectedSsid === network.ssid}
                  <span class="selected-check" aria-label="Seçildi">
                    <i class="fa-solid fa-check"></i>
                  </span>
                {/if}
              </button>
            </li>
          {/each}
        </ul>
      {/if}
    </div>
  </section>

  {#if selectedNet}
    <section class="connect-card" aria-labelledby="selected-network-title">
      <div class="selected-network">
        <div class="selected-network-icon"><i class="fa-solid fa-wifi"></i></div>
        <div>
          <small>Seçili ağ</small>
          <strong id="selected-network-title">{selectedNet.ssid}</strong>
        </div>
        <span class="security-label">
          <i class="fa-solid {selectedNet.secured ? 'fa-lock' : 'fa-lock-open'}"></i>
          {selectedNet.secured ? 'Şifreli' : 'Açık ağ'}
        </span>
      </div>

      {#if selectedNet.secured}
        <div class="password-field" class:password-field--error={Boolean(connectError)}>
          <i class="fa-solid fa-key field-icon"></i>
          <label for="wifi-password" class="visually-hidden">Wi-Fi şifresi</label>
          <input
            id="wifi-password"
            type={showPassword ? 'text' : 'password'}
            value={password}
            placeholder="Wi-Fi şifresini girin"
            class="password-input"
            autocomplete="off"
            autocapitalize="off"
            spellcheck="false"
            inputmode="none"
            readonly
          />
          <span class="character-count">{password.length}/{MAX_PASSWORD_LENGTH}</span>
          <button
            type="button"
            class="toggle-password"
            on:click={() => (showPassword = !showPassword)}
            aria-label={showPassword ? 'Şifreyi gizle' : 'Şifreyi göster'}
          >
            <i class="fa-solid {showPassword ? 'fa-eye-slash' : 'fa-eye'}"></i>
          </button>
        </div>

        {#if connectError}
          <div class="connect-error" role="alert">
            <i class="fa-solid fa-circle-exclamation"></i>
            <span>{connectError}</span>
          </div>
        {/if}

        <div class="virtual-keyboard" aria-label="Türkçe sanal klavye">
          <div class="keyboard-toolbar">
            <button
              type="button"
              class:active={keyboardMode === 'letters'}
              on:click={() => (keyboardMode = 'letters')}
            >ABC</button>
            <button
              type="button"
              class:active={keyboardMode === 'symbols'}
              on:click={() => (keyboardMode = 'symbols')}
            >123 / #+=</button>
            <span>Türkçe Q klavye</span>
            <button type="button" class="clear-key" on:click={clearPassword} disabled={!password}>
              Temizle
            </button>
          </div>

          {#if keyboardMode === 'letters'}
            {#each letterRows as row}
              <div class="keyboard-row">
                {#each row as key}
                  <button type="button" class="key" on:click={() => addKey(key)}>
                    {uppercase ? key.toLocaleUpperCase('tr-TR') : key}
                  </button>
                {/each}
              </div>
            {/each}
            <div class="keyboard-row keyboard-row--actions">
              <button
                type="button"
                class="key key--wide"
                class:key--active={uppercase}
                on:click={() => (uppercase = !uppercase)}
                aria-pressed={uppercase}
              >
                <i class="fa-solid fa-arrow-up"></i>
                {uppercase ? 'Küçük' : 'Büyük'}
              </button>
              <button type="button" class="key key--space" on:click={() => addKey(' ')}>Boşluk</button>
              <button type="button" class="key key--wide" on:click={backspace} disabled={!password}>
                <i class="fa-solid fa-delete-left"></i>
                Sil
              </button>
            </div>
          {:else}
            {#each symbolRows as row}
              <div class="keyboard-row">
                {#each row as key}
                  <button type="button" class="key" on:click={() => addKey(key)}>{key}</button>
                {/each}
              </div>
            {/each}
            <div class="keyboard-row keyboard-row--actions">
              <button type="button" class="key key--wide" on:click={() => (keyboardMode = 'letters')}>ABC</button>
              <button type="button" class="key key--space" on:click={() => addKey(' ')}>Boşluk</button>
              <button type="button" class="key key--wide" on:click={backspace} disabled={!password}>
                <i class="fa-solid fa-delete-left"></i>
                Sil
              </button>
            </div>
          {/if}
        </div>
      {:else}
        <div class="open-network-note">
          <i class="fa-solid fa-circle-info"></i>
          Bu ağ parola istemiyor. Bağlanarak devam edebilirsiniz.
        </div>
      {/if}

      <button type="button" class="connect-button" on:click={connect} disabled={!canConnect}>
        {#if connecting}
          <i class="fa-solid fa-circle-notch fa-spin"></i>
          Bağlantı kuruluyor…
        {:else}
          <i class="fa-solid fa-wifi"></i>
          Ağa bağlan
        {/if}
      </button>
    </section>
  {/if}

  <p class="wifi-footer-note">
    <i class="fa-solid fa-shield-halved"></i>
    Ağ parolanız yalnızca bağlantı kurulurken kullanılır.
  </p>
</div>

<style>
  .wifi-screen {
    --brand: #b1121b;
    --brand-dark: #7f1d1d;
    --brand-soft: #fef2f2;
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    padding: 24px 32px 18px;
    gap: 14px;
    overflow: hidden;
    background:
      radial-gradient(circle at 100% 0%, rgba(177, 18, 27, 0.09), transparent 34%),
      linear-gradient(180deg, #ffffff 0%, #f9fafb 58%, #f3f4f6 100%);
  }

  .wifi-topbar {
    position: relative;
    flex: 0 0 auto;
  }

  .wifi-topbar :global(.kiosk-header) {
    margin-bottom: 0;
  }

  .wifi-topbar :global(.kiosk-subtitle) {
    margin-top: 7px;
    font-size: 16px;
  }

  .connection-badge {
    width: max-content;
    margin: 0 auto 8px;
    padding: 6px 13px;
    border-radius: 999px;
    color: var(--brand-dark);
    background: var(--brand-soft);
    border: 1px solid #fecaca;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 0.2px;
  }

  .connection-badge i { margin-right: 6px; }

  .network-card,
  .connect-card {
    background: rgba(255, 255, 255, 0.96);
    border: 1px solid #e5e7eb;
    border-radius: 20px;
    box-shadow: 0 8px 28px rgba(17, 24, 39, 0.08);
  }

  .network-card {
    display: flex;
    flex-direction: column;
    min-height: 0;
    flex: 1 1 auto;
    overflow: hidden;
  }

  .network-card--compact {
    flex: 0 0 250px;
  }

  .section-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 15px 18px 12px;
    border-bottom: 1px solid #f3f4f6;
  }

  .section-heading h1 {
    margin: 0;
    color: #111827;
    font-size: 19px;
    font-weight: 800;
  }

  .section-heading p {
    margin: 3px 0 0;
    color: #6b7280;
    font-size: 13px;
  }

  .icon-button,
  .retry-button {
    border: 0;
    cursor: pointer;
    font-weight: 800;
  }

  .icon-button {
    width: 48px;
    height: 48px;
    border-radius: 14px;
    color: var(--brand);
    background: var(--brand-soft);
    font-size: 18px;
  }

  .icon-button:disabled { opacity: 0.45; cursor: not-allowed; }

  .wifi-list-container {
    min-height: 0;
    flex: 1;
    overflow-y: auto;
    overscroll-behavior: contain;
  }

  .status-state {
    min-height: 150px;
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    color: #6b7280;
  }

  .status-state > i { color: var(--brand); font-size: 30px; }
  .status-state strong { color: #374151; font-size: 16px; }
  .status-state span { font-size: 13px; }
  .status-state--error > i { color: #dc2626; }

  .retry-button {
    margin-top: 5px;
    padding: 10px 18px;
    border-radius: 10px;
    color: #fff;
    background: var(--brand);
  }

  .wifi-list { list-style: none; margin: 0; padding: 7px; }
  .wifi-list li + li { margin-top: 5px; }

  .wifi-item {
    position: relative;
    width: 100%;
    min-height: 68px;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 14px;
    border: 2px solid transparent;
    border-radius: 15px;
    background: #fff;
    color: #111827;
    cursor: pointer;
    text-align: left;
    transition: transform 0.1s, border-color 0.15s, background 0.15s;
  }

  .wifi-item:active { transform: scale(0.985); }
  .wifi-item:hover { background: #f9fafb; }

  .wifi-item--selected {
    border-color: var(--brand);
    background: var(--brand-soft);
  }

  .network-icon {
    width: 44px;
    height: 44px;
    flex: 0 0 44px;
    display: grid;
    place-items: center;
    border-radius: 13px;
    color: var(--brand);
    background: #f3f4f6;
  }

  .wifi-item--selected .network-icon { background: #fee2e2; }

  .signal-bars {
    display: flex;
    align-items: flex-end;
    gap: 2px;
    width: 23px;
    height: 20px;
  }

  .bar { flex: 1; border-radius: 2px; background: #d1d5db; }
  .bar:nth-child(1) { height: 25%; }
  .bar:nth-child(2) { height: 50%; }
  .bar:nth-child(3) { height: 75%; }
  .bar:nth-child(4) { height: 100%; }
  .bar--active { background: var(--brand); }

  .network-copy {
    min-width: 0;
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .network-copy strong {
    overflow: hidden;
    color: #111827;
    font-size: 16px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .network-copy small { color: #6b7280; font-size: 12px; }
  .security-icon { width: 22px; color: #6b7280; text-align: center; }

  .selected-check {
    width: 27px;
    height: 27px;
    display: grid;
    place-items: center;
    border-radius: 50%;
    color: #fff;
    background: var(--brand);
    font-size: 13px;
  }

  .connect-card {
    flex: 0 0 auto;
    padding: 15px;
  }

  .selected-network {
    display: flex;
    align-items: center;
    gap: 11px;
    margin-bottom: 12px;
  }

  .selected-network-icon {
    width: 42px;
    height: 42px;
    display: grid;
    place-items: center;
    flex: 0 0 42px;
    border-radius: 13px;
    color: #fff;
    background: linear-gradient(135deg, var(--brand), #991b1b);
  }

  .selected-network > div:nth-child(2) { min-width: 0; flex: 1; }
  .selected-network small { display: block; margin-bottom: 2px; color: #6b7280; font-size: 12px; }
  .selected-network strong { display: block; overflow: hidden; font-size: 16px; text-overflow: ellipsis; white-space: nowrap; }

  .security-label {
    padding: 7px 10px;
    border-radius: 999px;
    color: #4b5563;
    background: #f3f4f6;
    font-size: 12px;
    font-weight: 700;
  }

  .security-label i { margin-right: 4px; }

  .password-field {
    min-height: 56px;
    display: flex;
    align-items: center;
    overflow: hidden;
    border: 2px solid #d1d5db;
    border-radius: 14px;
    background: #f9fafb;
  }

  .password-field:focus-within { border-color: var(--brand); box-shadow: 0 0 0 4px rgba(177, 18, 27, 0.1); }
  .password-field--error { border-color: #dc2626; }
  .field-icon { margin-left: 16px; color: var(--brand); }

  .password-input {
    min-width: 0;
    flex: 1;
    padding: 14px 12px;
    border: 0;
    outline: 0;
    color: #111827;
    background: transparent;
    font-size: 18px;
    user-select: text;
  }

  .character-count { color: #9ca3af; font-size: 11px; white-space: nowrap; }

  .toggle-password {
    width: 52px;
    height: 52px;
    flex: 0 0 52px;
    border: 0;
    color: #4b5563;
    background: transparent;
    cursor: pointer;
    font-size: 17px;
  }

  .connect-error {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 9px 2px 0;
    padding: 9px 12px;
    border-radius: 10px;
    color: #991b1b;
    background: #fef2f2;
    font-size: 13px;
    font-weight: 700;
  }

  .virtual-keyboard {
    margin-top: 11px;
    padding: 9px;
    border: 1px solid #d1d5db;
    border-radius: 16px;
    background: #e5e7eb;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
  }

  .keyboard-toolbar {
    display: flex;
    align-items: center;
    gap: 7px;
    margin-bottom: 7px;
  }

  .keyboard-toolbar button {
    min-height: 34px;
    padding: 0 12px;
    border: 1px solid #d1d5db;
    border-radius: 9px;
    color: #4b5563;
    background: #fff;
    cursor: pointer;
    font-weight: 800;
  }

  .keyboard-toolbar button.active { border-color: var(--brand); color: #fff; background: var(--brand); }
  .keyboard-toolbar span { flex: 1; color: #6b7280; font-size: 12px; text-align: center; }
  .keyboard-toolbar .clear-key { color: #991b1b; }
  .keyboard-toolbar button:disabled { opacity: 0.45; cursor: not-allowed; }

  .keyboard-row { display: flex; justify-content: center; gap: 5px; }
  .keyboard-row + .keyboard-row { margin-top: 5px; }

  .key {
    min-width: 0;
    height: 43px;
    flex: 1 1 0;
    padding: 0 4px;
    border: 0;
    border-bottom: 3px solid #c7cbd1;
    border-radius: 9px;
    color: #111827;
    background: #fff;
    cursor: pointer;
    font-size: 17px;
    font-weight: 700;
    text-transform: none;
    touch-action: manipulation;
  }

  .key:active { transform: translateY(2px); border-bottom-width: 1px; }
  .key:disabled { opacity: 0.45; cursor: not-allowed; }
  .key--wide { flex: 0 0 128px; font-size: 13px; }
  .key--space { flex: 1; font-size: 13px; }
  .key--active { color: #fff; background: var(--brand); border-color: var(--brand-dark); }
  .keyboard-row--actions i { margin-right: 5px; }

  .open-network-note {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 14px;
    border-radius: 12px;
    color: #065f46;
    background: #ecfdf5;
    font-size: 14px;
    font-weight: 700;
  }

  .connect-button {
    width: 100%;
    min-height: 58px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    margin-top: 12px;
    border: 0;
    border-radius: 15px;
    color: #fff;
    background: linear-gradient(135deg, var(--brand), #991b1b);
    box-shadow: 0 7px 20px rgba(177, 18, 27, 0.28);
    cursor: pointer;
    font-size: 17px;
    font-weight: 800;
  }

  .connect-button:active:not(:disabled) { transform: scale(0.99); }
  .connect-button:disabled { opacity: 0.45; box-shadow: none; cursor: not-allowed; }

  .wifi-footer-note {
    flex: 0 0 auto;
    margin: 0;
    color: #6b7280;
    font-size: 12px;
    text-align: center;
  }

  .wifi-footer-note i { margin-right: 5px; color: var(--brand); }

  .visually-hidden {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
    border: 0;
  }
</style>
