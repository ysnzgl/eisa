<script>
  import { onMount, onDestroy } from 'svelte';
  import { campaigns, activeCampaignIndex } from '../stores/kiosk.js';
  import { fetchActiveCampaigns, logAdImpression } from '../lib/api.js';

  const AD_INTERVAL = 8000;

  let shownAt = new Date().toISOString();
  let cycleTick;
  let visible = true;

  $: asset = $campaigns[$activeCampaignIndex] ?? null;

  function advance() {
    if (!$campaigns.length) return;
    const durationMs = Date.now() - new Date(shownAt).getTime();
    if (asset) {
      logAdImpression({ assetId: asset.id, assetType: asset.type, shownAt, durationMs });
    }
    visible = false;
    setTimeout(() => {
      activeCampaignIndex.update(i => (i + 1) % $campaigns.length);
      shownAt = new Date().toISOString();
      visible = true;
    }, 400);
  }

  onMount(async () => {
    shownAt = new Date().toISOString();
    try {
      if (!$campaigns.length) {
        const list = await fetchActiveCampaigns();
        campaigns.set(list);
      }
    } catch { /* offline */ }
    cycleTick = setInterval(advance, AD_INTERVAL);
  });

  onDestroy(() => clearInterval(cycleTick));
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
    background: #0f172a;
    border-top: 3px solid #22c55e;
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
    color: #64748b;
    font-size: 16px;
    font-style: italic;
  }

  .ad-strip-default i {
    font-size: 1.5rem;
    color: #22c55e;
  }
</style>
