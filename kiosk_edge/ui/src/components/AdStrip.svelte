<script>
  import { onMount, onDestroy } from 'svelte';
  import {
    playlistItems, playlistVersion, playlistHour, playlistIsFallback,
    campaigns, activeCampaignIndex,
  } from '../stores/kiosk.js';
  import { fetchCurrentPlaylist, logAdImpression } from '../lib/api.js';

  // Playlist yokken ya da yüklenmeden önce kullanılacak varsayılan süre (ms)
  const FALLBACK_DURATION_MS = 8000;
  // Playlist güncelleme kontrolü: her dakika hangi saat olduğunu kontrol et
  const HOUR_CHECK_MS = 60_000;

  let asset        = null;   // o an ekranda gösterilen öğe
  let shownKey     = null;   // gösterilen öğenin kimliği (impression için)
  let shownAt      = new Date().toISOString();
  let visible      = true;
  let cycleTick    = null;
  let hourTick     = null;
  let loopSeconds  = 60;     // 60sn DOOH loop süresi
  let useSlots     = false;  // gerçek slot playlist mi, yoksa basit sıralı mı
  let currentIndex = 0;      // sıralı (fallback) modda indeks

  // Güncel oynatma listesi (playlist varsa oradan, yoksa eski campaigns store)
  $: items = $playlistItems.length > 0 ? $playlistItems : $campaigns;

  const off   = (it) => it?.estimated_start_offset_seconds ?? 0;
  const keyOf = (it) =>
    it ? `${it.asset_type ?? it.type ?? 'creative'}:${it.asset_id ?? it.id}` : null;

  // O an gösterilen reklam slotunun gerçek izlenme süresini backend'e logla.
  function logCurrentImpression() {
    if (!asset || !shownKey) return;
    const durationMs = Date.now() - new Date(shownAt).getTime();
    logAdImpression({
      assetId:   asset.asset_id ?? asset.id,
      assetType: asset.asset_type ?? asset.type ?? 'creative',
      shownAt,
      durationMs,
    });
  }

  // Yeni öğeye geçir (öğe değiştiyse önceki slotu logla + yumuşak geçiş yap).
  function show(item, msUntilNext) {
    const newKey = keyOf(item);
    if (newKey !== shownKey) {
      logCurrentImpression();
      visible = false;
      setTimeout(() => {
        asset = item;
        shownKey = newKey;
        shownAt = new Date().toISOString();
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

  // ── Slot modu: duvar saatine göre 60sn loop içindeki konuma karşılık gelen
  //    öğeyi göster. Bu, her kioskun aynı dakikada doğru slotu oynatmasını ve
  //    proof-of-play kayıtlarının slotlarla hizalanmasını sağlar. ──
  function slotTick() {
    if (!items.length) { scheduleNext(1000); return; }
    const sorted = [...items].sort((a, b) => off(a) - off(b));
    const pos = Math.floor(Date.now() / 1000) % loopSeconds;

    let idx = sorted.length - 1; // pos ilk offsetten önce ise son slota sar
    for (let i = 0; i < sorted.length; i++) {
      if (off(sorted[i]) <= pos) idx = i;
      else break;
    }
    const cur = sorted[idx];
    const nextOffset = (idx + 1 < sorted.length) ? off(sorted[idx + 1]) : loopSeconds;
    let secsToNext = nextOffset - pos;
    if (secsToNext <= 0) secsToNext = loopSeconds - pos; // wrap koruması

    activeCampaignIndex.set(idx);
    show(cur, Math.max(250, secsToNext * 1000));
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
    const nowHour = new Date().getUTCHours();
    try {
      const pl = await fetchCurrentPlaylist();
      playlistItems.set(pl.items ?? []);
      playlistVersion.set(pl.version);
      playlistHour.set(pl.target_hour ?? nowHour);
      playlistIsFallback.set(pl.is_fallback ?? true);
      loopSeconds = pl.loop_duration_seconds || 60;

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
      const nowHour = new Date().getUTCHours();
      if (nowHour !== $playlistHour) {
        await loadPlaylist();
      }
    }, HOUR_CHECK_MS);
  });

  onDestroy(() => {
    logCurrentImpression(); // ekran kapanırken son slotu kaybetme
    clearTimeout(cycleTick);
    clearInterval(hourTick);
  });
</script>

<div class="ad-strip">
  {#if asset?.media_url}
    <div class="ad-strip-media" style="opacity:{visible ? 1 : 0}">
      {#if /\.(mp4|webm|ogg)$/i.test(asset.media_url)}
        <!-- svelte-ignore a11y-media-has-caption -->
        <video src={asset.media_url} autoplay loop muted playsinline class="ad-strip-fill"></video>
      {:else}
        <img src={asset.media_url} alt={asset.name ?? 'Reklam'} class="ad-strip-fill" />
      {/if}
    </div>
  {:else}
    <div class="ad-strip-default">
      <i class="fa-solid fa-leaf"></i>
      <span>e-<strong>İSA</strong> — Sağlıklı Yaşam</span>
    </div>
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

  .ad-strip-fill {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .ad-strip-default {
    display: flex;
    align-items: center;
    gap: 12px;
    color: #6B7280;
    font-size: 16px;
    font-style: italic;
  }

  .ad-strip-default i {
    font-size: 1.5rem;
    color: #B1121B;
  }
</style>
