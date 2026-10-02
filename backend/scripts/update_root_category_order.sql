-- Root kategorileri (bagli_kategori_id IS NULL) kiosk 3-kolon görünümüne göre sırala.
-- Not: Alt kategorilerin sırası değiştirilmez.
-- Hedef veritabanı: PostgreSQL

BEGIN;

-- 1) İstenen kategorilerin tamamı root seviyede var mı kontrol et.
DO $$
DECLARE
  missing_list text;
BEGIN
  WITH desired(ad, sira) AS (
    VALUES
      ('Enerji & Halsizlik', 1),
      ('Uyku Desteği', 2),
      ('Kilo Yönetimi', 3),
      ('Eklem & Kas Problemleri', 4),
      ('Bağışıklık Güçlendirme', 5),
      ('Sindirim Problemleri', 6),
      ('Stres ve Kaygı Yönetimi', 7),
      ('Çocuk Gelişimi & Problemleri', 8),
      ('Cilt Problemleri', 9),
      ('Kalp ve Damar Desteği', 10),
      ('Odak & Konsantrasyon', 11),
      ('Saç & Tırnak Problemleri', 12),
      ('Spor & Aktif Yaşam Desteği', 13),
      ('Alerji Yönetimi', 14),
      ('Karaciğer & Detoks', 15),
      ('Kadın Desteği', 16),
      ('Göz Sağlığı', 17),
      ('Erkek Desteği', 18),
      ('Genel Sağlık & Korunma', 19)
  ),
  missing AS (
    SELECT d.ad
    FROM desired d
    LEFT JOIN kategoriler k
      ON k.ad = d.ad
     AND k.bagli_kategori_id IS NULL
    WHERE k.id IS NULL
  )
  SELECT string_agg(ad, ', ' ORDER BY ad)
    INTO missing_list
  FROM missing;

  IF missing_list IS NOT NULL THEN
    RAISE EXCEPTION 'Root kategorilerde eksik kayıt(lar) var: %', missing_list;
  END IF;
END
$$;

-- 2) Unique constraint çakışmasını önlemek için root sıralarını geçici olarak kaydır.
UPDATE kategoriler
SET sira = sira + 100
WHERE bagli_kategori_id IS NULL;

-- 3) Hedef sırayı uygula.
WITH desired(ad, sira) AS (
  VALUES
    ('Enerji & Halsizlik', 1),
    ('Uyku Desteği', 2),
    ('Kilo Yönetimi', 3),
    ('Eklem & Kas Problemleri', 4),
    ('Bağışıklık Güçlendirme', 5),
    ('Sindirim Problemleri', 6),
    ('Stres ve Kaygı Yönetimi', 7),
    ('Çocuk Gelişimi & Problemleri', 8),
    ('Cilt Problemleri', 9),
    ('Kalp ve Damar Desteği', 10),
    ('Odak & Konsantrasyon', 11),
    ('Saç & Tırnak Problemleri', 12),
    ('Spor & Aktif Yaşam Desteği', 13),
    ('Alerji Yönetimi', 14),
    ('Karaciğer & Detoks', 15),
    ('Kadın Desteği', 16),
    ('Göz Sağlığı', 17),
    ('Erkek Desteği', 18),
    ('Genel Sağlık & Korunma', 19)
)
UPDATE kategoriler k
SET sira = d.sira
FROM desired d
WHERE k.ad = d.ad
  AND k.bagli_kategori_id IS NULL;

COMMIT;

-- Kontrol sorgusu (opsiyonel)
-- SELECT sira, ad
-- FROM kategoriler
-- WHERE bagli_kategori_id IS NULL
-- ORDER BY sira, ad;
