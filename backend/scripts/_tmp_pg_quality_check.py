import psycopg

c = psycopg.connect("host=localhost port=5432 dbname=eisa user=eisa password=eisa")
cur = c.cursor()

checks = [
    ("kategoriler", "ad", "ad_en"),
    ("danisma_kategorileri", "ad", "ad_en"),
    ("sorular", "metin", "metin_en"),
    ("cevaplar", "metin", "metin_en"),
    ("dooh_idle_screen_contents", "baslik", "baslik_en"),
    ("dooh_idle_screen_contents", "metin", "metin_en"),
]

for t, tr_col, en_col in checks:
    cur.execute(
        f"SELECT COUNT(1) FROM {t} WHERE {en_col} IS NOT NULL AND btrim({en_col})<>'' AND {tr_col}={en_col}"
    )
    print(f"{t}.{en_col}_same_as_tr", cur.fetchone()[0])

c.close()
