import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';

// Gerçek Word şablonları ve backend üreticisiyle oluşturulmuş tam metinler.
const contractDocuments = JSON.parse(readFileSync(new URL('./fixtures/contracts.json', import.meta.url), 'utf8'));

// Yalnız izole test tarayıcısı ve sentetik API verileri. Gerçek hesaba veya tahsilata yazılmaz.
const pharmacy = { id: 1, ad: 'Merkez Eczanesi', sahip_adi: 'Ecz. Test', il: 38, ilce: 1, il_adi: 'Kayseri', ilce_adi: 'Melikgazi', kiosk_sayisi: 1, aktif: true };
const physical = { id: 1, seri_no: 'EISA-SN-2026-001', marka: 'e-isa', model: 'K21', ekran_boyutu: '21,5 inç FHD', garanti_ay: 24, donanim_degeri: '42000.00', eczane: 1, eczane_ad: 'Merkez Eczanesi', kiosk: null, kiosk_ad: '', aktif: true };
const region = { id: 1, ad: 'Kayseri Merkez', aktif: true, kapsamlar: [{ il: 38, il_adi: 'Kayseri', ilce: 1, ilce_adi: 'Melikgazi' }, { il: 38, il_adi: 'Kayseri', ilce: 2, ilce_adi: 'Kocasinan' }] };
const tariff = { id: 1, ad: 'Bölge Sponsorluğu — 6 ila 15 Cihaz', tur: 'BOLGE', min_cihaz: 6, max_cihaz: 15, brut_bedel: '36000.00', kdv_orani: 20, gecerlilik_baslangic: '2026-01-01', gecerlilik_bitis: '2026-12-31', aktif: true };
const provision = { id: '00000000-0000-0000-0000-000000000001', mac_adresi: 'AA:BB:CC:DD:EE:01', hostname: 'eisa-kiosk-01', status: 'PENDING', first_seen_at: '2026-11-08T08:00:00+03:00', last_seen_at: '2026-11-08T09:00:00+03:00', request_count: 3 };
const contract = { id: 1, eczane: 1, eczane_ad: 'Merkez Eczanesi', tur: 'STANDART', sozlesme_tipi_ay: 24, tip_display: '24 Ay', baslangic_tarihi: '2026-11-08', bitis_tarihi: '2028-11-08', aylik_kullanim_bedeli: '3900.00', kdv_orani: 20, durum: 'AKTIF', etkin_durum: 'AKTIF', kalan_gun: 730, imza_tipi: 'ISLAK', sozlesme_surumu: '2026-EK1', oteleme_ay: 0, cihaz_planlari: [{ id: 1, tip: 'TAHSIS', adet: 1, cihaz_bilgisi: 'e-isa K21', cihazlar: [1], taksit_sayisi: 1, durum: 'AKTIF' }] };

async function fixtures(page) {
  await page.addInitScript(() => { localStorage.setItem('eisa_role', 'superadmin'); localStorage.setItem('eisa_user_id', '1'); });
  await page.route('**/api/**', async route => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    let data = [];
    if (path === '/api/campaigns/v2/bolgeler/') data = [region];
    else if (path === '/api/campaigns/v2/tarifeler/') data = [tariff];
    else if (path === '/api/pharmacies/cihazlar/') data = [physical];
    else if (path === '/api/pharmacies/') data = [pharmacy];
    else if (path === '/api/pharmacies/kiosks/provisioning/') data = [provision];
    else if (path === '/api/lookups/iller/') data = [{ id: 38, ad: 'Kayseri' }];
    else if (path === '/api/lookups/ilceler/') data = [{ id: 1, ad: 'Melikgazi' }, { id: 2, ad: 'Kocasinan' }];
    else if (path === '/api/abonelik/sozlesmeler/') data = [contract];
    else if (path.includes('/fiyatlar/aktif/')) data = { abonelik_bedeli: '3900.00', abonelik_kdv_orani: 20 };
    else if (path.endsWith('/metin/')) {
      const kind = url.searchParams.get('belge_turu') || 'EK1';
      data = contractDocuments[kind];
    } else if (path.endsWith('/belge-olustur/')) {
      await route.fulfill({ status: 200, contentType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', body: Buffer.from('PK-test-docx') }); return;
    } else if (path.includes('sayisi') || path.endsWith('/ozet/')) data = { sayi: 0, yeni: 0 };
    if (request.method() !== 'GET') data = { id: 2, ...request.postDataJSON() };
    await route.fulfill({ status: request.method() === 'POST' ? 201 : 200, contentType: 'application/json', body: JSON.stringify(data) });
  });
}

test.beforeEach(async ({ page }) => { await fixtures(page); });
async function capture(page, testInfo, name) {
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: testInfo.outputPath(name), fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy();
  await expect(page.getByText('İstenen kaynak bulunamadı.', { exact: true })).toHaveCount(0);
}

test('bölge ayrı sayfa, kod alanı yok, tüm ilçelerle kayıt', async ({ page }, info) => {
  await page.goto('/admin/regions');
  await expect(page.getByRole('heading', { name: 'Bölge Tanımları', exact: true })).toBeVisible();
  await expect(page.getByText('Kayseri Merkez', { exact: true })).toBeVisible();
  await capture(page, info, 'regions-desktop.png');
  await page.getByRole('button', { name: 'Yeni Bölge', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByText('Kod', { exact: true })).toHaveCount(0);
  await dialog.getByLabel('Bölge adı').fill('Kayseri İli');
  await dialog.getByLabel('İl', { exact: true }).selectOption('38');
  await dialog.getByRole('button', { name: 'Ekle', exact: true }).click();
  await expect(dialog.getByText('Kayseri / Tüm ilçeler', { exact: true })).toBeVisible();
  await capture(page, info, 'region-form-desktop.png');
  const saved = page.waitForRequest(req => req.url().endsWith('/api/campaigns/v2/bolgeler/') && req.method() === 'POST');
  await dialog.getByRole('button', { name: 'Kaydet', exact: true }).click();
  expect((await saved).postDataJSON()).toEqual({ ad: 'Kayseri İli', aktif: true, kapsamlar: [{ il: 38, ilce: null }] });
});

test('tarife ayrı sayfa ve ortak modal tasarımı', async ({ page }, info) => {
  await page.goto('/admin/sponsorship-tariffs');
  await expect(page.getByText(tariff.ad, { exact: true })).toBeVisible();
  await capture(page, info, 'tariffs-desktop.png');
  await page.getByRole('button', { name: 'Yeni Tarife', exact: true }).click();
  await expect(page.getByRole('dialog').getByText('Kod', { exact: true })).toHaveCount(0);
  await capture(page, info, 'tariff-form-desktop.png');
});

test('fiziksel cihaz kayıt ekranı ve seri alanları', async ({ page }, info) => {
  await page.goto('/admin/device-inventory');
  await expect(page.getByText(physical.seri_no, { exact: true })).toBeVisible();
  await capture(page, info, 'inventory-desktop.png');
  await page.getByRole('button', { name: 'Yeni Cihaz', exact: true }).click();
  await expect(page.getByRole('dialog').getByLabel('Üretici seri numarası')).toBeVisible();
  await capture(page, info, 'inventory-form-desktop.png');
});

test('provizyon onayında kayıtlı seri ile eşleştirme', async ({ page }, info) => {
  await page.goto('/admin/devices/pending');
  await page.getByRole('button', { name: 'Eşleştir ve Onayla', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByText('Eczane seçin…', { exact: true }).click();
  await page.getByText(pharmacy.ad, { exact: true }).last().click();
  await dialog.getByLabel('Kayıtlı fiziksel cihaz / seri numarası').selectOption('1');
  await capture(page, info, 'provision-match-desktop.png');
  const saved = page.waitForRequest(req => req.url().endsWith('/approve/') && req.method() === 'POST');
  await dialog.getByRole('button', { name: 'Eşleştir ve Onayla' }).click();
  expect((await saved).postDataJSON()).toMatchObject({ eczane_id: 1, fiziksel_cihaz_id: 1 });
});

test('sözleşme cihaz planında seri seçimi kayda taşınır', async ({ page }, info) => {
  await page.goto('/admin/abonelik');
  await page.getByRole('button', { name: 'Düzenle', exact: true }).click();
  const dialog = page.getByRole('dialog');
  const selector = dialog.locator('.eisa-multi-lookup');
  await expect(selector.locator('.eisa-multi-lookup__chip')).toContainText(physical.seri_no);
  await selector.locator('.eisa-multi-lookup__chip').click();
  await selector.getByPlaceholder('Kayıtlı seri numarasını seçin…').click();
  await selector.getByRole('button').filter({ hasText: physical.seri_no }).click();
  await expect(dialog.getByLabel('Cihaz Bilgisi', { exact: true })).toHaveValue('e-isa K21');
  await dialog.getByLabel('Cihaz Bilgisi', { exact: true }).click();
  await capture(page, info, 'contract-device-selection-desktop.png');
  const saved = page.waitForRequest(req => req.url().endsWith('/api/abonelik/sozlesmeler/1/') && req.method() === 'PATCH');
  await dialog.getByRole('button', { name: 'Kaydet', exact: true }).click();
  expect((await saved).postDataJSON().cihaz_planlari[0]).toMatchObject({ cihazlar: [1], adet: 1 });
});

test('sözleşmede dolu önizleme, Ek-2 sekmesi ve indirme', async ({ page }, info) => {
  await page.goto('/admin/abonelik');
  await page.getByRole('button', { name: 'Sözleşmeyi Görüntüle', exact: true }).click();
  await expect(page.locator('.matbu-body')).toContainText('EISA-SN-2026-001');
  await capture(page, info, 'contract-ek1-desktop.png');
  await page.locator('.matbu-body').getByText(physical.seri_no, { exact: false }).first().scrollIntoViewIfNeeded();
  await capture(page, info, 'contract-ek1-filled-fields-desktop.png');
  await page.getByRole('button', { name: 'Ek-2 Teslim Tutanağı', exact: true }).click();
  await expect(page.locator('.matbu-body')).toContainText('CİHAZ TESLİM & KURULUM TUTANAĞI');
  await capture(page, info, 'contract-ek2-desktop.png');
  await page.locator('.matbu-body').getByText(physical.seri_no, { exact: true }).scrollIntoViewIfNeeded();
  await capture(page, info, 'contract-ek2-filled-fields-desktop.png');
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Word İndir', exact: true }).click();
  expect((await download).suggestedFilename()).toBe('sozlesme-1-ek2.docx');
});

test('mobilde bölge ve cihaz formları taşmıyor', async ({ page }, info) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/admin/regions');
  await page.getByRole('button', { name: 'Yeni Bölge', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await capture(page, info, 'region-form-mobile.png');
  await page.getByRole('button', { name: 'Vazgeç', exact: true }).click();
  await page.goto('/admin/device-inventory');
  await page.getByRole('button', { name: 'Yeni Cihaz', exact: true }).click();
  await expect(page.getByRole('dialog').getByRole('button', { name: 'Kaydet', exact: true })).toBeInViewport();
  await page.getByRole('dialog').getByLabel('Notlar').scrollIntoViewIfNeeded();
  await expect(page.getByRole('dialog').getByLabel('Notlar')).toBeInViewport();
  await capture(page, info, 'inventory-form-mobile.png');
});
