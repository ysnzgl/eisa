import csv
import psycopg

conn = psycopg.connect("host=localhost port=5432 dbname=eisa user=eisa password=eisa")
cur = conn.cursor()

out_path = "scripts/pg_missing_i18n.tsv"
with open(out_path, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter="\t")
    w.writerow(["table", "id", "field", "tr_text"])

    cur.execute("SELECT id, ad FROM kategoriler WHERE ad_en IS NULL OR btrim(ad_en)='' ORDER BY id")
    for _id, ad in cur.fetchall():
        w.writerow(["kategoriler", _id, "ad_en", ad])

    cur.execute("SELECT id, ad FROM danisma_kategorileri WHERE ad_en IS NULL OR btrim(ad_en)='' ORDER BY id")
    for _id, ad in cur.fetchall():
        w.writerow(["danisma_kategorileri", _id, "ad_en", ad])

    cur.execute("SELECT id, metin FROM sorular WHERE metin_en IS NULL OR btrim(metin_en)='' ORDER BY id")
    for _id, metin in cur.fetchall():
        w.writerow(["sorular", _id, "metin_en", metin])

    cur.execute("SELECT id, metin FROM cevaplar WHERE metin_en IS NULL OR btrim(metin_en)='' ORDER BY id")
    for _id, metin in cur.fetchall():
        w.writerow(["cevaplar", _id, "metin_en", metin])

    cur.execute("SELECT id, baslik FROM dooh_idle_screen_contents WHERE baslik_en IS NULL OR btrim(baslik_en)='' ORDER BY id")
    for _id, baslik in cur.fetchall():
        w.writerow(["dooh_idle_screen_contents", _id, "baslik_en", baslik])

    cur.execute("SELECT id, metin FROM dooh_idle_screen_contents WHERE metin_en IS NULL OR btrim(metin_en)='' ORDER BY id")
    for _id, metin in cur.fetchall():
        w.writerow(["dooh_idle_screen_contents", _id, "metin_en", metin])

conn.close()
print(out_path)
