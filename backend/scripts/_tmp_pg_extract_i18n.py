import psycopg

conn = psycopg.connect("host=localhost port=5432 dbname=eisa user=eisa password=eisa")
cur = conn.cursor()

cur.execute("SELECT id, slug, ad FROM kategoriler WHERE ad_en IS NULL OR btrim(ad_en)='' ORDER BY id")
print("KATEGORILER", cur.fetchall())

cur.execute("SELECT id, slug, ad FROM danisma_kategorileri WHERE ad_en IS NULL OR btrim(ad_en)='' ORDER BY id")
print("DANISMA", cur.fetchall())

cur.execute("SELECT id, metin FROM sorular WHERE metin_en IS NULL OR btrim(metin_en)='' ORDER BY id")
print("SORULAR", cur.fetchall())

cur.execute("SELECT id, metin FROM cevaplar WHERE metin_en IS NULL OR btrim(metin_en)='' ORDER BY id")
print("CEVAPLAR", cur.fetchall())

cur.execute(
    "SELECT id, baslik, metin FROM dooh_idle_screen_contents "
    "WHERE baslik_en IS NULL OR btrim(baslik_en)='' OR metin_en IS NULL OR btrim(metin_en)='' "
    "ORDER BY id"
)
print("IDLE", cur.fetchall())

conn.close()
