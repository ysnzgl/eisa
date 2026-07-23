/**
 * useKioskRolloutStatus — Faz 5 kiosk desired/applied/horizon durum hesabı.
 *
 * Tek merkezi kaynak. ControlCenter ve diğer ekranlar bu composable'ı kullanır;
 * durum hesabı farklı yerlerde kopyalanmaz.
 *
 * Semantik (implementation-plan-dooh-scheduler.md Faz 5):
 *   - desired version = backend'in yayınlamak istediği sürüm (last_playlist_version)
 *   - applied version = kiosk SQLite'a atomik uygulayıp ACK gönderdiği sürüm
 *   - applied null    = eski kiosk / ACK vermemiş (hata sayılmaz)
 *   - applied < desired → Geride
 *   - applied == desired fakat horizon eksik → Horizon Eksik (yine güncel sayılmaz)
 *   - Gerçekten güncel: applied == desired AND horizon coverage yeterli
 *   - Europe/Istanbul bugünü kullanılır; browser timezone'una güvenilmez
 *   - serverHorizonEnd backend response'undan (ping.horizon_end) alınır
 */

import { computed } from 'vue';

/**
 * Kiosk durumunu hesapla (pure function — Vue bağımlılığı yok).
 *
 * @param {object} kiosk
 * @param {string|null} serverHorizonEnd — backend'in döndürdüğü horizon_end (YYYY-MM-DD)
 * @returns {{ status: string, label: string, accent: string }}
 */
export function calcKioskRolloutStatus(kiosk, serverHorizonEnd = null) {
  if (!kiosk) return { status: 'unknown', label: 'Bilinmiyor', accent: 'default' };

  const desired = kiosk.last_playlist_version ?? null;
  const applied = kiosk.applied_playlist_version ?? null;

  // Çevrimdışı / hiç ping yok
  if (!kiosk.is_online || !kiosk.son_goruldu) {
    return { status: 'offline', label: 'Çevrimdışı', accent: 'red' };
  }

  // Desired hiç set edilmemiş (henüz V2 yayın yapılmamış)
  if (desired == null || desired === 0) {
    return { status: 'no_publish', label: 'Yayın Yok', accent: 'default' };
  }

  // applied null = ACK bekleniyor (eski kiosk veya ilk kez) — hata değil
  if (applied == null) {
    return { status: 'ack_pending', label: 'ACK Bekleniyor', accent: 'amber' };
  }

  // applied < desired = geride
  if (applied < desired) {
    return { status: 'behind', label: 'Geride', accent: 'red' };
  }

  // applied == desired ama horizon coverage kontrolü
  if (serverHorizonEnd) {
    const appliedEnd = kiosk.applied_horizon_end;
    if (!appliedEnd || appliedEnd < serverHorizonEnd) {
      return { status: 'horizon_stale', label: 'Horizon Eksik', accent: 'amber' };
    }
  }

  // Tüm kontroller geçti → güncel
  return { status: 'up_to_date', label: 'Güncel', accent: 'green' };
}

/**
 * Vue composable — kiosk listesi için toplu durum hesabı.
 * @param {import('vue').Ref<object[]>} kiosksRef — reaktif kiosk listesi
 * @param {import('vue').Ref<string|null>} serverHorizonEndRef — ping.horizon_end
 */
export function useKioskRolloutStatus(kiosksRef, serverHorizonEndRef) {
  const statusOf = (kiosk) =>
    calcKioskRolloutStatus(kiosk, serverHorizonEndRef?.value ?? null);

  const withStatus = computed(() =>
    (kiosksRef?.value ?? []).map((k) => ({
      ...k,
      rollout: statusOf(k),
    }))
  );

  const counts = computed(() => {
    const list = withStatus.value;
    return {
      upToDate:    list.filter((k) => k.rollout.status === 'up_to_date').length,
      behind:      list.filter((k) => k.rollout.status === 'behind').length,
      ackPending:  list.filter((k) => k.rollout.status === 'ack_pending').length,
      horizonStale:list.filter((k) => k.rollout.status === 'horizon_stale').length,
      offline:     list.filter((k) => k.rollout.status === 'offline').length,
      noPublish:   list.filter((k) => k.rollout.status === 'no_publish').length,
    };
  });

  return { statusOf, withStatus, counts };
}

