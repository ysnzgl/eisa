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

  let currentIndex = 0;
  let shownAt      = new Date().toISOString();
  let visible      = true;
  let cycleTick    = null;
  let hourTick     = null;

  // Güncel oynatma listesi (playlist varsa oradan, yoksa campaigns)
  $: items = $playlistItems.length > 0 ? $playlistItems : $campaigns;
  $: asset = items[currentIndex] ?? null;

  function currentDurationMs() {
    return ((asset?.duration_seconds ?? 0) * 1000) || FALLBACK_DURATION_MS;
  }

  function scheduleNext() {
    if (cycleTick) clearTimeout(cycleTick);
    cycleTick = setTimeout(advance, currentDurationMs());
  }

  function advance() {
    if (!items.length) { scheduleNext(); return; }
    const durationMs = Date.now() - new Date(shownAt).getTime();
    if (asset) {
      logAdImpression({
        assetId:   asset.asset_id ?? asset.id,
        assetType: asset.asset_type ?? asset.type ?? 'creative',
        shownAt,
        durationMs,
      });
    }
    visible = false;
    setTimeout(() => {
      currentIndex = (currentIndex + 1) % items.length;
      // Playlist store'u güncelle (eski campaigns store ile uyumluluk)
      activeCampaignIndex.set(currentIndex);
      shownAt = new Date().toISOString();
      visible = true;
      scheduleNext();
    }, 400);
  }

  async function loadPlaylist() {
    const nowHour = new Date().getUTCHours();
    try {
      const pl = await fetchCurrentPlaylist();
      playlistItems.set(pl.items ?? []);
      playlistVersion.set(pl.version);
      playlistHour.set(pl.target_hour ?? nowHour);
      playlistIsFallback.set(pl.is_fallback ?? true);
      // Sırayı sıfırla
      currentIndex = 0;
      activeCampaignIndex.set(0);
      scheduleNext();
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
