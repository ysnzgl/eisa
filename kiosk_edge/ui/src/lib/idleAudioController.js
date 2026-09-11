/** Idle ses listesinin ekran/etkilesimden bagimsiz, test edilebilir durum makinesi. */
export function isIdleAudioAllowed(config, now = new Date()) {
  if (config?.idle_audio_schedule_mode !== 'BUSINESS_HOURS') return true;
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Europe/Istanbul', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', hourCycle: 'h23',
  }).formatToParts(now).reduce((out, part) => ({ ...out, [part.type]: part.value }), {});
  const date = `${parts.year}-${parts.month}-${parts.day}`;
  if (config?.idle_audio_play_on_duty && (config?.idle_audio_duty_dates || []).includes(date)) return true;
  return Number(parts.hour) >= 8 && Number(parts.hour) < 19;
}

export function createIdleAudioController({ play, stop, onPlayingChange = () => {} }) {
  let timer = null;
  let active = false;
  let blockedByInteraction = false;
  let playing = false;
  let nextIndex = 0;
  let config = null;
  let configKey = '';
  let cycleToken = 0;

  function files() {
    const configured = config?.idle_audio?.files;
    if (Array.isArray(configured) && configured.length) return configured.filter((item) => item?.media_url);
    return config?.idle_audio?.media_url
      ? [{ id: 'legacy', media_url: config.idle_audio.media_url }]
      : [];
  }

  function clearTimer() {
    if (timer) clearTimeout(timer);
    timer = null;
  }

  function stopPlayback() {
    clearTimer();
    cycleToken += 1;
    playing = false;
    stop();
    onPlayingChange(false);
  }

  function canPlay() {
    return active && !blockedByInteraction && config?.idle_audio?.enabled && files().length > 0;
  }

  function schedule(delaySeconds) {
    clearTimer();
    if (!canPlay() || playing) return;
    const token = cycleToken;
    timer = setTimeout(async () => {
      timer = null;
      const playlist = files();
      if (!canPlay() || !playlist.length || token !== cycleToken) return;
      if (!isIdleAudioAllowed(config)) {
        schedule(60);
        return;
      }
      const item = playlist[nextIndex % playlist.length];
      nextIndex = (nextIndex + 1) % playlist.length;
      try {
        await play(item);
        if (!canPlay() || token !== cycleToken) {
          stop();
          return;
        }
        playing = true;
        onPlayingChange(true);
      } catch {
        if (canPlay() && token === cycleToken) {
          schedule(config?.idle_audio_repeat_seconds || 300);
        }
      }
    }, Math.max(1, delaySeconds) * 1000);
  }

  function resetCycle({ block = false } = {}) {
    stopPlayback();
    nextIndex = 0;
    blockedByInteraction = block;
  }

  return {
    update(nextActive, nextConfig) {
      const nextFiles = Array.isArray(nextConfig?.idle_audio?.files) ? nextConfig.idle_audio.files : [];
      const nextKey = JSON.stringify({
        enabled: nextConfig?.idle_audio?.enabled,
        files: nextFiles.map((item) => [item?.id, item?.media_url]),
        legacyUrl: nextConfig?.idle_audio?.media_url,
        delay: nextConfig?.idle_audio_delay_seconds,
        repeat: nextConfig?.idle_audio_repeat_seconds,
        scheduleMode: nextConfig?.idle_audio_schedule_mode,
        playOnDuty: nextConfig?.idle_audio_play_on_duty,
        dutyDates: nextConfig?.idle_audio_duty_dates,
      });
      const activeChanged = active !== nextActive;
      const configChanged = configKey !== nextKey;
      active = nextActive;
      config = nextConfig;
      configKey = nextKey;
      if (!active) {
        resetCycle();
      } else if (activeChanged) {
        resetCycle();
        schedule(config?.idle_audio_delay_seconds || 1200);
      } else if (configChanged && !blockedByInteraction) {
        resetCycle();
        schedule(config?.idle_audio_delay_seconds || 1200);
      }
    },
    interact() {
      if (active) resetCycle({ block: true });
    },
    ended() {
      if (!playing) return;
      playing = false;
      onPlayingChange(false);
      schedule(config?.idle_audio_repeat_seconds || 300);
    },
    destroy: stopPlayback,
  };
}
