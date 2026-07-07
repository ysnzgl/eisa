import Database from 'better-sqlite3';
const db = new Database('eisa.db', { readonly: true });

console.log('=== KIOSK SQLite VERİTABANI KONTROLÜ ===\n');

// Toplam sayılar
const soruCount = db.prepare('SELECT COUNT(*) as count FROM sorular').get().count;
const semCount = db.prepare('SELECT COUNT(*) as count FROM soru_etken_maddeler').get().count;

console.log(`Toplam Soru: ${soruCount}`);
console.log(`Toplam SoruEtkenMadde Bağlantı: ${semCount}\n`);

// Örnek sorular
const sorular = db.prepare(`
  SELECT s.id, s.metin, s.eslesme_kurallari, 
         COUNT(sem.id) as etken_madde_count
  FROM sorular s
  LEFT JOIN soru_etken_maddeler sem ON s.id = sem.soru_id
  GROUP BY s.id
  LIMIT 10
`).all();

console.log('=== İLK 10 SORU ===\n');
sorular.forEach(s => {
  console.log(`Soru ${s.id}: ${s.metin.substring(0,60)}...`);
  console.log(`  Etken Madde Bağlantı: ${s.etken_madde_count}`);
  console.log(`  eslesme_kurallari: ${s.eslesme_kurallari || 'NULL'}`);
  console.log('');
});

// Ana role sahip etken maddeler
const anaRolSayisi = db.prepare(`
  SELECT COUNT(*) as count 
  FROM soru_etken_maddeler 
  WHERE rol = 'ana'
`).get().count;

console.log(`\nANA rol ile bağlı etken madde sayısı: ${anaRolSayisi}`);

// Hangi sorularda ana rol var?
const anaRolleSorular = db.prepare(`
  SELECT s.id, s.metin, sem.rol, em.ad as etken_madde_ad
  FROM sorular s
  INNER JOIN soru_etken_maddeler sem ON s.id = sem.soru_id
  INNER JOIN etken_maddeler em ON sem.etken_madde_id = em.id
  WHERE sem.rol = 'ana'
  LIMIT 5
`).all();

console.log('\n=== ANA ROL İLE ETKİLEŞEN SORULAR ===\n');
anaRolleSorular.forEach(s => {
  console.log(`Soru ${s.id}: ${s.metin.substring(0,60)}...`);
  console.log(`  Etken Madde: ${s.etken_madde_ad} (${s.rol})\n`);
});

db.close();
