<script>
  import { createEventDispatcher, onMount } from 'svelte';
  import { campaigns, activeCampaignIndex, showCampaignOverlay } from '../stores/kiosk.js';
  import { logAdImpression } from '../lib/api.js';

  const dispatch = createEventDispatcher();

  let shownAt = null;

  $: campaign = $campaigns[$activeCampaignIndex] ?? null;

  onMount(() => {
    shownAt = new Date().toISOString();
  });

  function dismiss() {
    const durationMs = shownAt ? Date.now() - new Date(shownAt).getTime() : 0;
    if (campaign) {
      logAdImpression({ assetId: campaign.id, assetType: campaign.type, shownAt, durationMs });
    }
    // Sıradaki kampanyaya geç
    activeCampaignIndex.update(i => ($campaigns.length > 0 ? (i + 1) % $campaigns.length : 0));
    showCampaignOverlay.set(false);
    dispatch('start');
  }
</script>

<div class="campaign-overlay" role="dialog" aria-modal="true">
  <div class="campaign-media-wrap">
    {#if campaign?.media_url}
      {#if /\.(mp4|webm|ogg)$/i.test(campaign.media_url)}
        <!-- svelte-ignore a11y-media-has-caption -->
        <video
          src={campaign.media_url}
          autoplay
          loop
          muted
          playsinline
          class="campaign-media"
        ></video>
      {:else}
        <img src={campaign.media_url} alt={campaign.name ?? 'Kampanya'} class="campaign-media" />
      {/if}
    {:else}
      <div class="campaign-placeholder">
        <i class="fa-solid fa-photo-film"></i>
        <p>{campaign?.name ?? 'Kampanya'}</p>
      </div>
    {/if}
  </div>

  <div class="campaign-bottom">
    <button class="campaign-cta" on:click={dismiss}>
      <i class="fa-solid fa-hand-pointer"></i>
      Tıklayınız
    </button>
  </div>
</div>

<style>
  .campaign-overlay {
    position: absolute;
    inset: 0;
    z-index: 100;
    background: #000;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: space-between;
    border-radius: 20px;
    overflow: hidden;
  }

  .campaign-media-wrap {
    flex: 1;
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }

  .campaign-media {
    width: 100%;
    height: 100%;
    object-fit: contain;
  }

  .campaign-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    color: #6b7280;
    font-size: 1.2rem;
  }

  .campaign-placeholder i {
    font-size: 4rem;
  }

  .campaign-bottom {
    width: 100%;
    padding: 24px 40px;
    background: rgba(0, 0, 0, 0.75);
    display: flex;
    justify-content: center;
  }

  .campaign-cta {
    background: #16a34a;
    color: #fff;
    border: none;
    border-radius: 14px;
    padding: 18px 60px;
    font-size: 1.5rem;
    font-weight: 700;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 14px;
    transition: background 0.2s;
  }

  .campaign-cta:hover {
    background: #15803d;
  }
</style>
