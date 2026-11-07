/**
 * useKaydedilmemisDegisiklik — kaydedilmemiş değişiklik koruması.
 *
 *  - Sekme kapatma / yenileme: `beforeunload` (tarayıcının kendi uyarısı)
 *  - Rota değişimi: onBeforeRouteLeave + useConfirm diyaloğu
 *
 * const { onayla } = useKaydedilmemisDegisiklik(kirli)
 *   onayla() → kirli değilse true; kirliyse kullanıcıya sorar.
 */
import { onBeforeUnmount, onMounted, unref } from 'vue';
import { onBeforeRouteLeave } from 'vue-router';
import { useConfirm } from './useConfirm.js';

export function useKaydedilmemisDegisiklik(kirli, {
  mesaj = 'Kaydedilmemiş değişiklikleriniz var. Sayfadan ayrılırsanız bu değişiklikler kaybolacak.',
} = {}) {
  const { confirm } = useConfirm();

  async function onayla(ozelMesaj) {
    if (!unref(kirli)) return true;
    return confirm({
      title: 'Kaydedilmemiş Değişiklikler',
      message: ozelMesaj || mesaj,
      confirmLabel: 'Değişiklikleri At',
      variant: 'warning',
    });
  }

  function beforeUnload(e) {
    if (!unref(kirli)) return undefined;
    e.preventDefault();
    e.returnValue = '';
    return '';
  }

  onMounted(() => window.addEventListener('beforeunload', beforeUnload));
  onBeforeUnmount(() => window.removeEventListener('beforeunload', beforeUnload));
  onBeforeRouteLeave(() => onayla());

  return { onayla };
}
