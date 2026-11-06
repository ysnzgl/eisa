import { mount, flushPromises } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { getFaturaAdmin, previewFaturaRebuild, correctFatura } = vi.hoisted(() => ({
  getFaturaAdmin: vi.fn(), previewFaturaRebuild: vi.fn(), correctFatura: vi.fn(),
}));
vi.mock('../../services/abonelik', () => ({ getFaturaAdmin, previewFaturaRebuild, correctFatura }));
import FaturaIslemModal from '../shared/FaturaIslemModal.vue';

const invoice = { id: 7, eczane_ad: 'Test Eczanesi', donem: '2026-01', surum: 4, tutar: '100.00' };
const calculation = { surum: 4, eski_tutar: '100.00', yeni_tutar: '150.00', tahsilat: '0.00',
  onizleme_anahtari: 'hash', kalemler: [], engel: '' };
const mountModal = (action) => mount(FaturaIslemModal, {
  props: { fatura: invoice, action }, global: { stubs: { Teleport: true } },
});
const submit = (wrapper) => wrapper.get('.eisa-btn-danger');

beforeEach(() => {
  vi.clearAllMocks();
  getFaturaAdmin.mockResolvedValue({ data: invoice });
  previewFaturaRebuild.mockResolvedValue({ data: calculation });
  correctFatura.mockResolvedValue({ data: { ...invoice, durum: 'IPTAL' } });
});

describe('Fatura düzeltme modalı', () => {
  it('iptal için gerekçe ister ve güncel sürümle gönderir', async () => {
    const w = mountModal('iptal');
    await flushPromises();
    expect(w.text()).toContain('İptal nedeni');
    expect(w.text()).toContain('para iadesi yapmaz');
    expect(submit(w).attributes('disabled')).toBeDefined();
    await w.get('textarea').setValue('   ');
    expect(submit(w).attributes('disabled')).toBeDefined();
    await w.get('textarea').setValue(' Yanlış fatura ');
    await submit(w).trigger('click');
    await flushPromises();
    expect(correctFatura).toHaveBeenCalledWith(7, 'iptal', { neden: 'Yanlış fatura', surum: 4 });
    expect(w.emitted('saved')).toHaveLength(1);
    w.unmount();
  });

  it('yeniden oluşturmada eski/yeni tutarı gösterir ve önizlemeyi onaya bağlar', async () => {
    const w = mountModal('yeniden-olustur');
    await flushPromises();
    expect(previewFaturaRebuild).toHaveBeenCalledWith(7);
    expect(w.text()).toContain('Eski tutar');
    expect(w.text()).toContain('100,00');
    expect(w.text()).toContain('150,00');
    expect(correctFatura).not.toHaveBeenCalled();
    await w.get('textarea').setValue('Bedel düzeltildi');
    await submit(w).trigger('click');
    await flushPromises();
    expect(correctFatura).toHaveBeenCalledWith(7, 'yeniden-olustur', {
      neden: 'Bedel düzeltildi', surum: 4, onizleme_anahtari: 'hash',
    });
    w.unmount();
  });

  it('ödenmiş faturada tutar farkı varsa yeniden oluşturmayı engeller', async () => {
    previewFaturaRebuild.mockResolvedValue({ data: { ...calculation, engel: 'Önce tahsilatı geri alın.' } });
    const w = mountModal('yeniden-olustur');
    await flushPromises();
    await w.get('textarea').setValue('Düzeltme');
    expect(w.get('[role="alert"]').text()).toContain('Önce tahsilatı');
    expect(submit(w).attributes('disabled')).toBeDefined();
    expect(correctFatura).not.toHaveBeenCalled();
    w.unmount();
  });

  it('sunucu hata verince eski sürümle tekrar göndermez, yenileme ister', async () => {
    correctFatura.mockRejectedValue({ response: { data: { detail: 'Fatura değişmiş.' } } });
    const w = mountModal('odemeyi-geri-al');
    await flushPromises();
    await w.get('textarea').setValue('Hatalı tahsilat');
    await submit(w).trigger('click');
    await flushPromises();
    expect(w.text()).toContain('Fatura değişmiş.');
    expect(w.text()).toContain('Bilgileri Yenile');
    expect(submit(w).attributes('disabled')).toBeDefined();
    expect(w.emitted('saved')).toBeUndefined();
    w.unmount();
  });
});
