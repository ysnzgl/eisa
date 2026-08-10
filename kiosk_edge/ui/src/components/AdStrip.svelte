<script>
  import { onMount, onDestroy } from 'svelte';
  import {
    playlistItems, playlistVersion, playlistHour, playlistIsFallback,
    campaigns, activeCampaignIndex,
  } from '../stores/kiosk.js';
  import { fetchCurrentPlaylist, logAdImpression } from '../lib/api.js';
  import { resolveActiveItem, currentHourPosition, secondsUntilBoundary } from '../lib/playlistSlot.js';
  import AdPromo from './AdPromo.svelte';
  import MediaView from './MediaView.svelte';

  // Playlist yokken ya da yüklenmeden önce kullanılacak varsayılan süre (ms)
  const FALLBACK_DURATION_MS = 8000;
  // Playlist güncelleme kontrolü: her dakika hangi saat olduğunu kontrol et
  const HOUR_CHECK_MS = 60_000;
  // Backend playlist'leri bir SAATLİK döngü üretir: estimated_start_offset_seconds
  // 0..3599 (loop_index*60 + slot offset). Slot hizalaması bu nedenle saatin
  // tamamı (3600sn) üzerinden yapılmalıdır; aksi halde yalnızca ilk dakikanın
  // (loop 0) öğeleri oynar, PER_HOUR/PER_DAY reklamlar hiç gösterilmez.
  const HOUR_SECONDS = 3600;

  // Duvar saatini Europe/Istanbul'a göre hesapla (cihaz TZ'sinden bağımsız).
  // Backend target_hour'u Istanbul yerel saatine göre üretir.
  const _hourFmt = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Europe/Istanbul', hour: '2-digit', hour12: false,
  });
  const istanbulHour = () => {
    const h = parseInt(_hourFmt.format(new Date()), 10);
    return h === 24 ? 0 : h;
  };

  let asset        = null;   // o an ekranda gösterilen öğe
  let shownKey     = null;   // gösterilen öğenin kimliği (impression için)
  let shownAt      = new Date().toISOString();
  let visible      = true;
  let cycleTick    = null;
  let hourTick     = null;
  let useSlots     = false;  // gerçek slot playlist mi, yoksa basit sıralı mı
  let currentIndex = 0;      // sıralı (fallback) modda indeks
  let currentPlayEventId = null;  // Faz 3: mevcut slot için idempotency UUID

  // Güncel oynatma listesi (playlist varsa oradan, yoksa eski campaigns store)
  // house_ad öğeleri işlem ekranında gösterilmez; yalnız paid creative'lar oynatılır.
  $: items = ($playlistItems.length > 0 ? $playlistItems : $campaigns)
    .filter(i => (i.asset_type ?? i.type) === 'creative');

  const off   = (it) => it?.estimated_start_offset_seconds ?? 0;
  // Slot kimligi: ayni asset farkli slotlarda ayri gosterim/impression sayilir.
  const keyOf = (it) =>
    it ? String(it.id ?? `${it.asset_id ?? it.asset_type ?? 'creative'}:${off(it)}`) : null;

  // O an gösterilen reklam slotunun gerçek izlenme süresini backend'e logla.
  // Faz 3: play_event_id ile idempotent; beklenen süre ile karşılaştırarak
  // COMPLETED (tam oynatıldı) veya INTERRUPTED (erken kesildi) durumunu belirle.
  function logCurrentImpression(statusOverride) {
    if (!asset || !shownKey || !currentPlayEventId) return;
    const durationMs = Date.now() - new Date(shownAt).getTime();
    const expectedDuration = asset.duration_seconds ?? null;
    const durationSec = Math.round(durationMs / 1000);
    let finalStatus = statusOverride || 'COMPLETED';
    if (!statusOverride && expectedDuration && durationSec < expectedDuration * 0.5) {
      finalStatus = 'INTERRUPTED';  // Beklenen sürenin yarısından az oynatıldı
    }
    logAdImpression({
      assetId:         asset.asset_id ?? asset.id,
      assetType:       asset.asset_type ?? asset.type ?? 'creative',
      shownAt,
      durationMs,
      playEventId:     currentPlayEventId,
      status:          finalStatus,
      expectedDuration,
    });
    currentPlayEventId = null;  // Bir kez gönder
  }

  // Yeni ogeye gecir (oge degistiyse onceki slotu logla + yumusak gecis yap).
  // item null ise bosluk demektir: AdPromo gosterilir, impression ACILMAZ.
  function show(item, msUntilNext) {
    const newKey = keyOf(item);
    if (newKey !== shownKey) {
      logCurrentImpression();   // onceki slot kaydi (COMPLETED/INTERRUPTED)
      visible = false;
      setTimeout(() => {
        asset = item;
        shownKey = newKey;
        shownAt = new Date().toISOString();
        // Impression yalniz gercek planli item icin acilir; bosluk/AdPromo icin yok.
        currentPlayEventId = item
          ? (typeof crypto !== 'undefined' && crypto.randomUUID
              ? crypto.randomUUID()
              : `${Date.now()}-${Math.random().toString(36).slice(2)}`)
          : null;
        visible = true;
      }, 400);
    }
    scheduleNext(msUntilNext);
  }

  function scheduleNext(ms) {
    if (cycleTick) clearTimeout(cycleTick);
    cycleTick = setTimeout(tick, ms);
  }

  function tick() {
    if (useSlots) slotTick();
    else seqTick();
  }

  // ── Slot modu: her item YALNIZ kendi [offset, offset+duration) araliginda
  //    aktiftir. Aralik disinda aktif item yoksa (bosluk) AdPromo gosterilir;
  //    item bir sonraki offset'e kadar UZATILMAZ. Zamanlayici bir sonraki
  //    sinira (item basi/sonu) gore planlanir. ──
  function slotTick() {
    const pos = currentHourPosition();
    const active = resolveActiveItem(items, pos); // bosluk => null
    const ms = secondsUntilBoundary(items, pos) * 1000;
    activeCampaignIndex.set(active ? items.indexOf(active) : -1);
    show(active, Math.max(250, ms));
  }

  // ── Sıralı (fallback) modu: öğeleri kendi sürelerine göre döngüsel oynat. ──
  function seqTick() {
    if (!items.length) { scheduleNext(FALLBACK_DURATION_MS); return; }
    const item  = items[currentIndex % items.length];
    const durMs = ((item?.duration_seconds ?? 0) * 1000) || FALLBACK_DURATION_MS;
    activeCampaignIndex.set(currentIndex % items.length);
    show(item, durMs);
    currentIndex = (currentIndex + 1) % items.length;
  }

  async function loadPlaylist() {
    const nowHour = istanbulHour();
    try {
      const pl = await fetchCurrentPlaylist();
      playlistItems.set(pl.items ?? []);
      playlistVersion.set(pl.version);
      playlistHour.set(pl.target_hour ?? nowHour);
      playlistIsFallback.set(pl.is_fallback ?? true);

      const list    = pl.items ?? [];
      const offsets = list.map(off);
      // Gerçek slot zamanlaması yalnızca backend offset üretmişse kullanılır.
      useSlots = !(pl.is_fallback ?? true) && list.length > 1 && new Set(offsets).size > 1;

      currentIndex = 0;
      activeCampaignIndex.set(0);
      scheduleNext(0); // reaktif `items` güncellensin diye bir sonraki mikro-adımda başlat
    } catch {
      // Offline — mevcut state korunur
    }
  }

  onMount(async () => {
    shownAt = new Date().toISOString();
    await loadPlaylist();

    // Her dakika saat değişti mi kontrol et → playlist güncelle
    hourTick = setInterval(async () => {
      const nowHour = istanbulHour();
      if (nowHour !== $playlistHour) {
        await loadPlaylist();
      }
    }, HOUR_CHECK_MS);
  });

  onDestroy(() => {
    logCurrentImpression('INTERRUPTED'); // ekran kapanırken son slotu INTERRUPTED kaydet
    clearTimeout(cycleTick);
    clearInterval(hourTick);
  });

  // Faz 3: medya yükleme hatası → FAILED kaydı
  function handleMediaError() {
    if (!asset || !currentPlayEventId) return;
    const pid = currentPlayEventId;
    currentPlayEventId = null; // INTERRUPTED'ın da tetiklenmesini önle
    logAdImpression({
      assetId:         asset.asset_id ?? asset.id,
      assetType:       asset.asset_type ?? asset.type ?? 'creative',
      shownAt,
      durationMs:      Date.now() - new Date(shownAt).getTime(),
      playEventId:     pid,
      status:          'FAILED',
      expectedDuration: asset.duration_seconds ?? null,
      errorCode:       'MEDIA_LOAD_ERROR',
    });
  }
</script>

<div class="ad-strip">
  {#if asset?.active_media_url}
    <!-- İşlem ekranı için doğru oranda yüklü medya (yaklaşık 7:5) -->
    <div class="ad-strip-media" style="opacity:{visible ? 1 : 0}">
      <MediaView src={asset.active_media_url} type={asset.media_type} alt={asset.name ?? 'İçerik'} class="ad-strip-fill" on:error={handleMediaError} />
    </div>
  {:else if asset?.media_url}
    <!-- Fallback: bekleme ekranı görseli — object-fit:contain ile letterbox -->
    <div class="ad-strip-media" style="opacity:{visible ? 1 : 0}">
      <MediaView src={asset.media_url} type={asset.media_type} alt={asset.name ?? 'İçerik'} class="ad-strip-fill ad-strip-fill--contain" on:error={handleMediaError} />
    </div>
  {:else}
    <AdPromo />
  {/if}
</div>

<style>
  .ad-strip {
    flex: 1;
    height: 100%;
    min-height: 0;
    background: #111827;
    border-top: 3px solid #B1121B;
    position: relative;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .ad-strip-media {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: opacity 0.4s ease;
  }
</style>
