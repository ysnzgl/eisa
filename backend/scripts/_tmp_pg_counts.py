import psycopg

c = psycopg.connect("host=localhost port=5432 dbname=eisa user=eisa password=eisa")
cur = c.cursor()
queries = [
    ("kategoriler.ad_en", "SELECT COUNT(1) FROM kategoriler WHERE ad_en IS NULL OR btrim(ad_en)=''") ,
    ("danisma_kategorileri.ad_en", "SELECT COUNT(1) FROM danisma_kategorileri WHERE ad_en IS NULL OR btrim(ad_en)=''") ,
    ("sorular.metin_en", "SELECT COUNT(1) FROM sorular WHERE metin_en IS NULL OR btrim(metin_en)=''") ,
    ("cevaplar.metin_en", "SELECT COUNT(1) FROM cevaplar WHERE metin_en IS NULL OR btrim(metin_en)=''") ,
    ("idle.baslik_en", "SELECT COUNT(1) FROM dooh_idle_screen_contents WHERE baslik_en IS NULL OR btrim(baslik_en)=''") ,
    ("idle.metin_en", "SELECT COUNT(1) FROM dooh_idle_screen_contents WHERE metin_en IS NULL OR btrim(metin_en)=''") ,
]
for name, sql in queries:
    cur.execute(sql)
    print(name, cur.fetchone()[0])
c.close()
