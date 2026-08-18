<script>
  // Kalici (persistent) DOOH medya oynaticisi.
  //
  // Tek <video> DOM instance'i idle (fullscreen) ve oturum (strip) duzenleri
  // arasinda KORUNUR; ekran duzeni degisince yalniz CSS/mode degisir, video
  // remount/reload olmaz, currentTime sifirlanmaz. Video yalniz GERCEK slot
  // degistiginde ({#key slotKey}) yeniden olusur.
  //
  // Slot zamanlamasi playlistSlot resolver'i ile aynidir: item yalniz
  // [offset, offset+duration) araliginda aktiftir; disinda AdPromo gosterilir.
  import { onMount, onDestroy } from 'svelte';
  import { get } from 'svelte/store';
  import { playlistItems, playlistVersion, playlistHour, playlistIsFallback, activeCampaignIndex } from '../stores/kiosk.js';
  import { fetchCurrentPlaylist, logAdImpression } from '../lib/api.js';
  import { resolveActiveItem, currentHourPosition, secondsUntilBoundary } from '../lib/playlistSlot.js';
  import { startIdleContent, stopIdleContent } from '../lib/idleContentStore.js';
  import AdPromo from './AdPromo.svelte';
  import MediaView from './MediaView.svelte';

  /** Sunum modu: 'fullscreen' (idle) | 'strip' (oturum). Yalniz layout etkiler. */
  export let mode = 'fullscreen';

  const HOUR_CHECK_MS = 60_000;

  let asset    = null;   // o an aktif PlaylistItem veya null (bosluk)
  let slotKey  = null;   // `${version}:${item.id}` — {#key} ile video kimligi
  let tickTimer = null;
  let hourTick  = null;
  let _unsub    = null;
  // Impression yasam dongusu (mode/layout degisiminden BAGIMSIZ).
  let playEventId = null;
  let shownAt     = null;

  // Duvar saatini Europe/Istanbul'a gore hesapla (cihaz TZ'sinden bagimsiz).
  const _hourFmt = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Europe/Istanbul', hour: '2-digit', hour12: false,
  });
  const istanbulHour = () => {
    const h = parseInt(_hourFmt.format(new Date()), 10);
    return h === 24 ? 0 : h;
  };

  async function loadPlaylist() {
    try {
      const pl = await fetchCurrentPlaylist();
      playlistItems.set(pl.items ?? []);
      playlistVersion.set(pl.version);
      playlistHour.set(pl.target_hour ?? istanbulHour());
      playlistIsFallback.set(pl.is_fallback ?? true);
    } catch {
      // Offline — mevcut playlist state'i korunur.
    }
  }

  function _openImpression(item) {
    playEventId = (typeof crypto !== 'undefined' && crypto.randomUUID)
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    shownAt = new Date().toISOString();
  }

  function _closeImpression(statusOverride) {
    if (!asset || !playEventId) return;
    const durationMs = Date.now() - new Date(shownAt).getTime();
    const expectedDuration = asset.duration_seconds ?? null;
    const durationSec = Math.round(durationMs / 1000);
    let finalStatus = statusOverride || 'COMPLETED';
    if (!statusOverride && expectedDuration && durationSec < expectedDuration * 0.5) {
      finalStatus = 'INTERRUPTED';
    }
    logAdImpression({
      assetId:          asset.asset_id ?? asset.id,
      assetType:        asset.asset_type ?? asset.type ?? 'creative',
      shownAt,
      durationMs,
      playEventId,
      status:           finalStatus,
      expectedDuration,
    });
    playEventId = null;
  }

  // Aktif slotu cozumle. Store'lar get() ile OKUNUR (reactive zamanlama/bayat
  // closure sorunlarindan bagimsiz). Slot GERCEKTEN degistiyse eski impression'i
  // kapat, yeni item icin yeni impression ac ve slotKey'i degistir (video
  // remount). Layout/mode degisimi bu fonksiyonu tetiklemez → video korunur.
  function evaluate() {
    clearTimeout(tickTimer);
    const items = get(playlistItems) ?? [];
    const pos = currentHourPosition();
    const active = resolveActiveItem(items, pos);
    const newKey = active ? `${get(playlistVersion)}:${active.id}` : null;
    if (newKey !== slotKey) {
      _closeImpression();          // onceki slot kaydini kapat
      asset = active;              // null => AdPromo
      slotKey = newKey;
      activeCampaignIndex.set(active ? items.indexOf(active) : -1);
      if (active) _openImpression(active);
    }
    tickTimer = setTimeout(evaluate, secondsUntilBoundary(items, pos) * 1000);
  }

  onMount(async () => {
    startIdleContent();
    await loadPlaylist();
    // Playlist degisince (yeni version/yukleme) hemen yeniden cozumle; subscribe
    // abone olunca mevcut degerle de bir kez calisir.
    _unsub = playlistItems.subscribe(() => evaluate());
    // Saat degisiminde yeni saatin playlist'ini yukle (mevcut sozlesme).
    hourTick = setInterval(async () => {
      if (istanbulHour() !== get(playlistHour)) await loadPlaylist();
    }, HOUR_CHECK_MS);
  });
  onDestroy(() => {
    _unsub?.();
    clearTimeout(tickTimer);
    clearInterval(hourTick);
    stopIdleContent();
    _closeImpression('INTERRUPTED');
  });

  function handleMediaError() {
    if (!asset || !playEventId) return;
    const pid = playEventId;
    playEventId = null;
    logAdImpression({
      assetId:          asset.asset_id ?? asset.id,
      assetType:        asset.asset_type ?? asset.type ?? 'creative',
      shownAt,
      durationMs:       Date.now() - new Date(shownAt).getTime(),
      playEventId:      pid,
      status:           'FAILED',
      expectedDuration: asset.duration_seconds ?? null,
      errorCode:        'MEDIA_LOAD_ERROR',
    });
  }
</script>

<div class="player player--{mode}">
  {#if asset}
    <!-- Her iki video da slot boyunca DAIMA oynar (playing={true}); mode yalniz
         CSS opacity/z-index degistirir. Boylece fullscreen ve mini video slotun
         baslangicindan itibaren AYNI currentTime'da ilerler: geciste seek/reset
         gerekmez, yalniz gorunurluk degisir. {#key} yalniz gercek slot
         degisiminde (slotKey farklilasinca) her iki video'yu birlikte remount
         eder ve ikisi de t=0'dan baslar. -->
    {#key slotKey}
      <MediaView
        src={asset.media_url}
        type={asset.media_type}
        alt={asset.name ?? 'Reklam'}
        playing={true}
        class={mode === 'fullscreen' ? 'player-media' : 'player-media player-media--behind'}
        on:error={handleMediaError}
      />
    {/key}
    {#if asset.active_media_url}
      {#key slotKey}
        <MediaView
          src={asset.active_media_url}
          type={asset.media_type}
          alt={asset.name ?? 'Reklam'}
          playing={true}
          class={mode === 'strip' ? 'player-media player-media--strip' : 'player-media player-media--strip player-media--behind'}
        />
      {/key}
    {/if}
  {:else}
    <AdPromo large={mode === 'fullscreen'} />
  {/if}
</div>

<style>
  .player {
    position: absolute;
    inset: 0;
    overflow: hidden;
    background: #111827;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .player--strip {
    border-top: 3px solid #B1121B;
  }
  :global(.player-media) {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  /* Fullscreen video strip modunda gizli ama oynamaya devam eder (sureklilik). */
  :global(.player-media--behind) {
    opacity: 0;
    pointer-events: none;
  }
  /* Strip'e ozel 7:5 gorsel ustte gorunur. */
  :global(.player-media--strip) {
    z-index: 1;
  }
</style>
