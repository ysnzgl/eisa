<script>
  import { createEventDispatcher } from 'svelte';
  import ScreenHeader from './ScreenHeader.svelte';
  import { t } from '../lib/i18n.js';

  const dispatch = createEventDispatcher();
</script>

<div class="screen">
  <ScreenHeader />

  <div class="flex-grow-1 d-flex flex-column justify-content-center">
    <h2 class="screen-title text-center">{$t('welcome.title')}</h2>
    <div class="d-flex flex-column gap-3">
      <button class="btn-touch btn-secondary-touch btn-main-touch" on:click={() => dispatch('flowA')}>
        <i class="fa-solid fa-hand-pointer"></i>
        {$t('welcome.flowA')}
        <span class="btn-sub">{$t('welcome.flowASub')}</span>
      </button>

      <div class="or-divider">{$t('welcome.or')}</div>

      <button class="btn-touch btn-primary-touch btn-main-touch" on:click={() => dispatch('flowConsult')}>
        <i class="fa-solid fa-comments"></i>
        {$t('welcome.flowConsult')}
        <span class="btn-sub">{$t('welcome.flowConsultSub')}</span>
      </button>
    </div>
  </div>

  <div class="footer-note">
    <i class="fa-solid fa-shield-halved"></i>
    {$t('welcome.footer')}
  </div>
</div>
