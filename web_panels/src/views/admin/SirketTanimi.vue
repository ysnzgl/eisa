<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { toast } from 'vue-sonner';
import { useConfirm } from '../../composables/useConfirm.js';
import {
  createBankaHesabi,
  deleteBankaHesabi,
  getSirketProfili,
  updateBankaHesabi,
  updateSirketProfili,
} from '../../services/sirket';

const { confirm } = useConfirm();
const loading = ref(true);
const saving = ref(false);
const bankSaving = ref(false);
const bankModalOpen = ref(false);
const editingBankId = ref(null);
const fieldErrors = ref({});

const emptyCompany = () => ({
  ticari_unvan: '', marka_adi: 'e-İSA', vergi_dairesi: '', vergi_numarasi: '',
  mersis_numarasi: '', ticaret_sicil_numarasi: '', kep_adresi: '', eposta: '',
  telefon: '', web_sitesi: '', adres: '', ilce: '', il: '', posta_kodu: '',
  yetkili_ad_soyad: '', yetkili_unvan: '', banka_hesaplari: [],
});
const company = reactive(emptyCompany());

const emptyBank = () => ({
  banka_adi: '', hesap_sahibi: '', iban: '', sube_adi: '', sube_kodu: '',
  hesap_numarasi: '', para_birimi: 'TRY', aciklama: '', aktif: true,
  varsayilan: false, sira: 0,
});
const bankForm = reactive(emptyBank());

const completeness = computed(() => {
  const required = ['ticari_unvan', 'vergi_dairesi', 'vergi_numarasi', 'adres', 'eposta', 'telefon'];
  const filled = required.filter((key) => String(company[key] || '').trim()).length;
  return Math.round((filled / required.length) * 100);
});
const activeBanks = computed(() => company.banka_hesaplari.filter((item) => item.aktif).length);

function cleanPayload() {
  const payload = { ...company };
  ['id', 'banka_hesaplari', 'guncellenme_tarihi', 'surum'].forEach((key) => delete payload[key]);
  return payload;
}

function applyErrors(error) {
  const data = error?.response?.data;
  fieldErrors.value = data && typeof data === 'object' ? data : {};
}

async function load() {
  loading.value = true;
  try {
    Object.assign(company, emptyCompany(), await getSirketProfili());
  } finally {
    loading.value = false;
  }
}

async function saveCompany() {
  saving.value = true;
  fieldErrors.value = {};
  try {
    Object.assign(company, await updateSirketProfili(cleanPayload()));
    toast.success('Şirket bilgileri kaydedildi.');
  } catch (error) {
    applyErrors(error);
    toast.error('Şirket bilgileri kontrol edilerek yeniden denenmeli.');
  } finally {
    saving.value = false;
  }
}

function openNewBank() {
  editingBankId.value = null;
  Object.assign(bankForm, emptyBank(), { sira: company.banka_hesaplari.length });
  fieldErrors.value = {};
  bankModalOpen.value = true;
}

function openBank(bank) {
  editingBankId.value = bank.id;
  Object.assign(bankForm, emptyBank(), bank);
  bankForm.iban = formatIban(bank.iban);
  fieldErrors.value = {};
  bankModalOpen.value = true;
}

function closeBankModal() {
  if (bankSaving.value) return;
  bankModalOpen.value = false;
  editingBankId.value = null;
}

function formatIban(value) {
  return String(value || '').replace(/\s/g, '').toUpperCase().replace(/(.{4})/g, '$1 ').trim();
}

function onIbanInput(event) {
  bankForm.iban = formatIban(event.target.value).slice(0, 41);
}

async function saveBank() {
  bankSaving.value = true;
  fieldErrors.value = {};
  const payload = { ...bankForm, iban: bankForm.iban.replace(/\s/g, '') };
  ['id', 'olusturulma_tarihi', 'guncellenme_tarihi', 'surum'].forEach((key) => delete payload[key]);
  try {
    if (editingBankId.value) await updateBankaHesabi(editingBankId.value, payload);
    else await createBankaHesabi(payload);
    toast.success(editingBankId.value ? 'Banka hesabı güncellendi.' : 'Banka hesabı eklendi.');
    bankModalOpen.value = false;
    await load();
  } catch (error) {
    applyErrors(error);
    toast.error('Banka hesabı kaydedilemedi.');
  } finally {
    bankSaving.value = false;
  }
}

async function removeBank(bank) {
  const approved = await confirm({
    title: 'Banka Hesabını Sil',
    message: `${bank.banka_adi} hesabı kalıcı olarak silinecek.`,
    confirmLabel: 'Evet, Sil',
    variant: 'danger',
  });
  if (!approved) return;
  await deleteBankaHesabi(bank.id);
  toast.success('Banka hesabı silindi.');
  await load();
}

onMounted(load);
</script>

<template>
  <div class="eisa-page company-page">
    <header class="eisa-page-header">
      <div>
        <p class="eisa-eyebrow">YÖNETİCİ / KURUMSAL AYARLAR</p>
        <h1 class="eisa-page-title">Şirket Tanımı</h1>
        <p class="eisa-page-subtitle">Sözleşme, fatura ve havale süreçlerinde kullanılacak e‑İSA bilgilerini yönetin.</p>
      </div>
      <button class="eisa-btn eisa-btn-cta" :disabled="saving || loading" @click="saveCompany">
        <i :class="saving ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-floppy-disk'"></i>
        {{ saving ? 'Kaydediliyor…' : 'Değişiklikleri Kaydet' }}
      </button>
    </header>

    <div v-if="loading" class="page-loading"><i class="fa-solid fa-circle-notch fa-spin"></i><span>Şirket bilgileri yükleniyor…</span></div>

    <template v-else>
      <section class="summary-strip">
        <div class="identity-mark"><i class="fa-solid fa-building"></i></div>
        <div class="summary-main"><span>Kurumsal profil</span><strong>{{ company.ticari_unvan || 'Şirket unvanı bekleniyor' }}</strong><small>{{ company.marka_adi || 'e-İSA' }}</small></div>
        <div class="summary-stat"><span>Profil doluluğu</span><strong>%{{ completeness }}</strong><div class="progress"><i :style="{ width: completeness + '%' }"></i></div></div>
        <div class="summary-stat"><span>Aktif banka hesabı</span><strong>{{ activeBanks }}</strong><small>{{ company.banka_hesaplari.length }} toplam kayıt</small></div>
      </section>

      <form class="content-grid" @submit.prevent="saveCompany">
        <div class="form-column">
          <section class="eisa-panel form-card">
            <div class="section-title"><span class="section-icon"><i class="fa-solid fa-file-signature"></i></span><div><h2>Ticari ve Vergi Bilgileri</h2><p>Sözleşmelerde “İş Sağlayan” tarafı olarak kullanılır.</p></div></div>
            <div class="fields two-col">
              <label class="wide"><span class="eisa-field-label">Ticari unvan *</span><input v-model.trim="company.ticari_unvan" class="eisa-field" maxlength="255" required><small v-if="fieldErrors.ticari_unvan" class="field-error">{{ fieldErrors.ticari_unvan[0] }}</small></label>
              <label><span class="eisa-field-label">Marka adı</span><input v-model.trim="company.marka_adi" class="eisa-field" maxlength="120"></label>
              <label><span class="eisa-field-label">Vergi dairesi *</span><input v-model.trim="company.vergi_dairesi" class="eisa-field" maxlength="120" required></label>
              <label><span class="eisa-field-label">Vergi numarası *</span><input v-model.trim="company.vergi_numarasi" class="eisa-field mono" maxlength="10" inputmode="numeric" placeholder="10 haneli" required><small v-if="fieldErrors.vergi_numarasi" class="field-error">{{ fieldErrors.vergi_numarasi[0] }}</small></label>
              <label><span class="eisa-field-label">MERSİS numarası</span><input v-model.trim="company.mersis_numarasi" class="eisa-field mono" maxlength="16" inputmode="numeric" placeholder="16 haneli"><small v-if="fieldErrors.mersis_numarasi" class="field-error">{{ fieldErrors.mersis_numarasi[0] }}</small></label>
              <label><span class="eisa-field-label">Ticaret sicil numarası</span><input v-model.trim="company.ticaret_sicil_numarasi" class="eisa-field" maxlength="50"></label>
            </div>
          </section>

          <section class="eisa-panel form-card">
            <div class="section-title"><span class="section-icon teal"><i class="fa-solid fa-location-dot"></i></span><div><h2>Adres ve İletişim</h2><p>Resmî yazışma ve belge iletişim bilgileri.</p></div></div>
            <div class="fields two-col">
              <label class="wide"><span class="eisa-field-label">Açık adres *</span><textarea v-model.trim="company.adres" class="eisa-field" rows="3" required></textarea></label>
              <label><span class="eisa-field-label">İlçe</span><input v-model.trim="company.ilce" class="eisa-field" maxlength="100"></label>
              <label><span class="eisa-field-label">İl</span><input v-model.trim="company.il" class="eisa-field" maxlength="100"></label>
              <label><span class="eisa-field-label">Posta kodu</span><input v-model.trim="company.posta_kodu" class="eisa-field" maxlength="10" inputmode="numeric"></label>
              <label><span class="eisa-field-label">Telefon</span><input v-model.trim="company.telefon" class="eisa-field" maxlength="30" type="tel" placeholder="+90 352 …"></label>
              <label><span class="eisa-field-label">E-posta</span><input v-model.trim="company.eposta" class="eisa-field" type="email" placeholder="muhasebe@…"></label>
              <label><span class="eisa-field-label">KEP adresi</span><input v-model.trim="company.kep_adresi" class="eisa-field" type="email"></label>
              <label><span class="eisa-field-label">Web sitesi</span><input v-model.trim="company.web_sitesi" class="eisa-field" type="url" placeholder="https://"></label>
            </div>
          </section>

          <section class="eisa-panel form-card">
            <div class="section-title"><span class="section-icon amber"><i class="fa-solid fa-user-tie"></i></span><div><h2>Yetkili Bilgileri</h2><p>Sözleşme ve kurumsal iletişim için imza yetkilisi.</p></div></div>
            <div class="fields two-col">
              <label><span class="eisa-field-label">Ad soyad</span><input v-model.trim="company.yetkili_ad_soyad" class="eisa-field" maxlength="150"></label>
              <label><span class="eisa-field-label">Görevi / unvanı</span><input v-model.trim="company.yetkili_unvan" class="eisa-field" maxlength="120"></label>
            </div>
          </section>
        </div>

        <aside class="bank-column">
          <section class="eisa-panel bank-panel">
            <div class="bank-head"><div><p class="eisa-eyebrow">TAHSİLAT HESAPLARI</p><h2>Banka Hesapları</h2><p>EFT / havale ile ödeme için birden fazla hesap tanımlayın.</p></div><button type="button" class="add-bank" @click="openNewBank"><i class="fa-solid fa-plus"></i></button></div>
            <div v-if="!company.banka_hesaplari.length" class="bank-empty"><span><i class="fa-solid fa-building-columns"></i></span><strong>Henüz banka hesabı yok</strong><p>Ödeme bildirimlerinde kullanılacak ilk hesabı ekleyin.</p><button type="button" class="eisa-btn eisa-btn-cta" @click="openNewBank">Banka Hesabı Ekle</button></div>
            <div v-else class="bank-list">
              <article v-for="bank in company.banka_hesaplari" :key="bank.id" class="bank-card" :class="{ inactive: !bank.aktif }">
                <div class="bank-card-top"><span class="bank-logo"><i class="fa-solid fa-building-columns"></i></span><div><strong>{{ bank.banka_adi }}</strong><small>{{ bank.para_birimi }} hesabı</small></div><span v-if="bank.varsayilan" class="default-pill"><i class="fa-solid fa-star"></i> Varsayılan</span><span v-else-if="!bank.aktif" class="passive-pill">Pasif</span></div>
                <div class="iban-line"><span>{{ formatIban(bank.iban) }}</span><button type="button" title="IBAN'ı kopyala" @click="navigator.clipboard?.writeText(bank.iban); toast.success('IBAN kopyalandı.')"><i class="fa-regular fa-copy"></i></button></div>
                <div class="bank-meta"><span><b>Alıcı</b>{{ bank.hesap_sahibi }}</span><span v-if="bank.sube_adi"><b>Şube</b>{{ bank.sube_adi }}<template v-if="bank.sube_kodu"> / {{ bank.sube_kodu }}</template></span></div>
                <div class="bank-actions"><button type="button" @click="openBank(bank)"><i class="fa-solid fa-pen"></i> Düzenle</button><button type="button" class="danger" @click="removeBank(bank)"><i class="fa-regular fa-trash-can"></i></button></div>
              </article>
              <button type="button" class="new-bank-row" @click="openNewBank"><i class="fa-solid fa-plus"></i> Yeni banka hesabı ekle</button>
            </div>
          </section>

          <div class="usage-note"><i class="fa-solid fa-circle-info"></i><div><strong>Merkezi kullanım</strong><p>Şirket bilgileri yeni oluşturulan sözleşmelere otomatik aktarılır. Onaylanmış sözleşmelerin dondurulmuş metni değişmez.</p></div></div>
        </aside>
      </form>
    </template>

    <Teleport to="body">
      <div v-if="bankModalOpen" class="eisa-modal-backdrop" @click.self="closeBankModal">
        <div class="eisa-modal bank-modal" role="dialog" aria-modal="true">
          <div class="eisa-modal-header"><div><p class="eisa-eyebrow">EFT / HAVALE</p><h3 class="eisa-modal-title">{{ editingBankId ? 'Banka Hesabını Düzenle' : 'Yeni Banka Hesabı' }}</h3></div><button class="eisa-modal-close" @click="closeBankModal"><i class="fa-solid fa-xmark"></i></button></div>
          <form @submit.prevent="saveBank">
            <div class="eisa-modal-body bank-form">
              <div class="fields two-col">
                <label><span class="eisa-field-label">Banka adı *</span><input v-model.trim="bankForm.banka_adi" class="eisa-field" maxlength="120" required></label>
                <label><span class="eisa-field-label">Para birimi *</span><select v-model="bankForm.para_birimi" class="eisa-field"><option value="TRY">TRY — Türk Lirası</option><option value="USD">USD — Amerikan Doları</option><option value="EUR">EUR — Euro</option><option value="GBP">GBP — İngiliz Sterlini</option></select></label>
                <label class="wide"><span class="eisa-field-label">Hesap sahibi / alıcı unvanı *</span><input v-model.trim="bankForm.hesap_sahibi" class="eisa-field" maxlength="255" required></label>
                <label class="wide"><span class="eisa-field-label">IBAN *</span><input :value="bankForm.iban" class="eisa-field mono iban-input" maxlength="41" autocomplete="off" placeholder="TR00 0000 0000 0000 0000 0000 00" required @input="onIbanInput"><small v-if="fieldErrors.iban" class="field-error">{{ fieldErrors.iban[0] }}</small></label>
                <label><span class="eisa-field-label">Şube adı</span><input v-model.trim="bankForm.sube_adi" class="eisa-field" maxlength="120"></label>
                <label><span class="eisa-field-label">Şube kodu</span><input v-model.trim="bankForm.sube_kodu" class="eisa-field" maxlength="20"></label>
                <label><span class="eisa-field-label">Hesap numarası</span><input v-model.trim="bankForm.hesap_numarasi" class="eisa-field mono" maxlength="40"></label>
                <label><span class="eisa-field-label">Gösterim sırası</span><input v-model.number="bankForm.sira" class="eisa-field" min="0" max="999" type="number"></label>
                <label class="wide"><span class="eisa-field-label">Açıklama</span><input v-model.trim="bankForm.aciklama" class="eisa-field" maxlength="255" placeholder="Örn. Havale/EFT işlemlerinde açıklamaya fatura no yazınız."></label>
              </div>
              <div class="switch-row"><label><input v-model="bankForm.aktif" type="checkbox"><span><b>Aktif hesap</b><small>Ödeme ekranlarında kullanılabilir.</small></span></label><label><input v-model="bankForm.varsayilan" type="checkbox" :disabled="!bankForm.aktif"><span><b>Varsayılan hesap</b><small>Öncelikli ödeme hesabı olarak gösterilir.</small></span></label></div>
            </div>
            <div class="eisa-modal-footer"><button type="button" class="eisa-btn eisa-btn-ghost" :disabled="bankSaving" @click="closeBankModal">Vazgeç</button><button class="eisa-btn eisa-btn-cta" :disabled="bankSaving"><i :class="bankSaving ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-floppy-disk'"></i>{{ bankSaving ? 'Kaydediliyor…' : 'Hesabı Kaydet' }}</button></div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.company-page{max-width:1600px;margin:0 auto}.page-loading{min-height:55vh;display:flex;align-items:center;justify-content:center;gap:.75rem;color:#6b7280}.summary-strip{display:grid;grid-template-columns:auto minmax(240px,1fr) 180px 170px;gap:1.25rem;align-items:center;background:linear-gradient(118deg,#111827 0%,#26191d 55%,#7f1d1d 140%);color:#fff;border-radius:16px;padding:1.2rem 1.4rem;margin-bottom:1.25rem;box-shadow:0 10px 28px rgba(17,24,39,.13)}.identity-mark{width:48px;height:48px;border-radius:13px;display:grid;place-items:center;background:rgba(255,255,255,.1);color:#fca5a5;font-size:1.2rem}.summary-main,.summary-stat{display:flex;flex-direction:column}.summary-main span,.summary-stat span{font-size:.66rem;text-transform:uppercase;letter-spacing:.11em;color:#cbd5e1}.summary-main strong{font-size:1rem;margin:.15rem 0}.summary-main small,.summary-stat small{font-size:.72rem;color:#9ca3af}.summary-stat{padding-left:1.2rem;border-left:1px solid rgba(255,255,255,.14)}.summary-stat strong{font-family:'Syne',sans-serif;font-size:1.45rem;margin:.15rem 0}.progress{height:4px;background:rgba(255,255,255,.14);border-radius:99px;overflow:hidden}.progress i{display:block;height:100%;background:#ef4444;border-radius:99px}.content-grid{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(330px,.8fr);gap:1.25rem;align-items:start}.form-column{display:flex;flex-direction:column;gap:1rem}.form-card,.bank-panel{padding:1.25rem}.section-title{display:flex;gap:.8rem;align-items:center;padding-bottom:1rem;margin-bottom:1rem;border-bottom:1px solid #eef2f6}.section-icon{width:39px;height:39px;border-radius:10px;display:grid;place-items:center;color:#b1121b;background:#fef2f2}.section-icon.teal{color:#0f766e;background:#f0fdfa}.section-icon.amber{color:#b45309;background:#fffbeb}.section-title h2,.bank-head h2{font-size:.98rem;margin:0}.section-title p,.bank-head p{font-size:.74rem;color:#6b7280;margin:.18rem 0 0}.fields{display:grid;gap:.85rem}.two-col{grid-template-columns:repeat(2,minmax(0,1fr))}.fields label{display:flex;flex-direction:column;gap:.3rem;min-width:0}.fields .wide{grid-column:1/-1}.fields textarea{resize:vertical}.mono{font-family:'DM Mono',monospace;letter-spacing:.04em}.field-error{color:#b91c1c;font-size:.68rem}.bank-column{display:flex;flex-direction:column;gap:1rem;position:sticky;top:1rem}.bank-head{display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;padding-bottom:1rem;border-bottom:1px solid #eef2f6}.add-bank{width:38px;height:38px;border:0;border-radius:10px;color:#fff;background:#b1121b;cursor:pointer;box-shadow:0 4px 12px rgba(177,18,27,.22)}.bank-empty{text-align:center;padding:2.4rem 1rem}.bank-empty>span{width:52px;height:52px;border-radius:50%;display:grid;place-items:center;margin:0 auto .8rem;background:#f3f4f6;color:#9ca3af}.bank-empty strong{display:block;font-size:.88rem}.bank-empty p{font-size:.73rem;color:#6b7280;max-width:240px;margin:.35rem auto 1rem}.bank-list{display:flex;flex-direction:column;gap:.7rem;padding-top:1rem}.bank-card{border:1px solid #dfe4ea;border-radius:12px;padding:.9rem;transition:.18s}.bank-card:hover{border-color:#c9b4b7;box-shadow:0 5px 16px rgba(17,24,39,.06)}.bank-card.inactive{opacity:.62;background:#f8fafc}.bank-card-top{display:flex;align-items:center;gap:.6rem}.bank-logo{width:32px;height:32px;display:grid;place-items:center;border-radius:8px;background:#fef2f2;color:#b1121b}.bank-card-top>div{display:flex;flex:1;flex-direction:column}.bank-card-top strong{font-size:.8rem}.bank-card-top small{font-size:.66rem;color:#6b7280}.default-pill,.passive-pill{font-size:.6rem;font-weight:750;padding:.25rem .42rem;border-radius:99px}.default-pill{background:#ecfdf5;color:#047857}.passive-pill{background:#f3f4f6;color:#6b7280}.iban-line{display:flex;justify-content:space-between;align-items:center;background:#f8fafc;border-radius:8px;padding:.55rem .65rem;margin:.75rem 0;font-family:'DM Mono',monospace;font-size:.73rem;color:#1f2937}.iban-line button{border:0;background:none;color:#6b7280;cursor:pointer}.bank-meta{display:grid;grid-template-columns:1fr 1fr;gap:.6rem}.bank-meta span{font-size:.67rem;color:#4b5563;overflow-wrap:anywhere}.bank-meta b{display:block;text-transform:uppercase;color:#9ca3af;font-size:.57rem;letter-spacing:.06em;margin-bottom:.1rem}.bank-actions{display:flex;justify-content:flex-end;gap:.35rem;margin-top:.8rem;padding-top:.7rem;border-top:1px solid #f1f5f9}.bank-actions button{border:0;background:#f3f4f6;border-radius:7px;padding:.38rem .55rem;font-size:.67rem;cursor:pointer;color:#374151}.bank-actions .danger{color:#b91c1c}.new-bank-row{border:1px dashed #d1d5db;background:#fff;color:#6b7280;border-radius:10px;padding:.7rem;cursor:pointer;font-size:.74rem}.new-bank-row:hover{border-color:#b1121b;color:#b1121b}.usage-note{display:flex;gap:.7rem;padding:1rem;border:1px solid #c7d2fe;background:#eef2ff;border-radius:12px;color:#3730a3}.usage-note strong{font-size:.76rem}.usage-note p{font-size:.69rem;line-height:1.55;margin:.2rem 0 0}.bank-modal{width:min(700px,calc(100vw - 2rem));max-height:calc(100vh - 2rem);overflow:auto}.bank-form{display:flex;flex-direction:column;gap:1rem}.iban-input{font-size:.92rem}.switch-row{display:grid;grid-template-columns:1fr 1fr;gap:.7rem;padding-top:.25rem}.switch-row label{display:flex;gap:.55rem;align-items:flex-start;border:1px solid #e5e7eb;border-radius:10px;padding:.75rem;cursor:pointer}.switch-row input{margin-top:.2rem}.switch-row span{display:flex;flex-direction:column}.switch-row b{font-size:.75rem}.switch-row small{font-size:.65rem;color:#6b7280;margin-top:.12rem}@media(max-width:1050px){.content-grid{grid-template-columns:1fr}.bank-column{position:static}.summary-strip{grid-template-columns:auto 1fr 150px}.summary-stat:last-child{display:none}}@media(max-width:700px){.eisa-page-header{align-items:flex-start;flex-direction:column}.summary-strip{grid-template-columns:auto 1fr}.summary-stat{display:none}.two-col,.switch-row{grid-template-columns:1fr}.fields .wide{grid-column:auto}.bank-meta{grid-template-columns:1fr}}
</style>
