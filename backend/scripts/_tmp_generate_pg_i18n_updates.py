from __future__ import annotations

import time
from pathlib import Path

import psycopg
from deep_translator import MyMemoryTranslator

CONN_STR = "host=localhost port=5432 dbname=eisa user=eisa password=eisa"
OUT_SQL = Path("scripts/backfill_i18n_en_pg.sql")

translator = MyMemoryTranslator(source="tr-TR", target="en-GB")


def tr_to_en(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    for attempt in range(8):
        try:
            val = translator.translate(text)
            if val:
                time.sleep(0.10)
                return val.strip()
        except Exception:
            time.sleep(min(3.0, 0.4 + attempt * 0.3))
    return text


def batch_tr_to_en(texts: list[str]) -> list[str]:
    if not texts:
        return []
    out: list[str] = []
    chunk_size = 20
    for i in range(0, len(texts), chunk_size):
        chunk = texts[i:i + chunk_size]
        translated: list[str] | None = None
        for attempt in range(6):
            try:
                translated = translator.translate_batch(chunk)
                break
            except Exception:
                time.sleep(min(3.5, 0.6 + attempt * 0.4))
        if not translated or len(translated) != len(chunk):
            translated = [tr_to_en(x) for x in chunk]
        out.extend([(t or "").strip() for t in translated])
        print(f"batch translated: {min(i + chunk_size, len(texts))}/{len(texts)}")
    return out


def esc(val: str) -> str:
    return val.replace("'", "''")


# Curated overrides for consistent medical terminology.
CATEGORY_OVERRIDES = {
    1: "Energy and Fatigue",
    2: "Sleep Support",
    3: "Eye Health",
    4: "Hair and Nail Problems",
    5: "Joint and Muscle Problems",
    6: "Sports and Active Lifestyle Support",
    7: "Stress and Anxiety Management",
    8: "Focus and Concentration",
    9: "Weight Management",
    10: "Digestive Problems",
    11: "Child Development and Related Problems",
    12: "Women's Health Support",
    13: "Men's Health Support",
    14: "Skin Problems",
    15: "Cardiovascular Support",
    16: "Liver and Detox Support",
    17: "Allergy Management",
    18: "General Health and Prevention",
    19: "Immune Support",
}

DANISMA_OVERRIDES = {
    1: "Sexual Health",
    2: "Severe Diarrhea and Nausea",
    3: "Hemorrhoids",
    4: "Excessive Sweating and Body Odor",
    5: "Intense Hair Loss",
    6: "Fungal and Eczema Complaints",
}


def main() -> None:
    conn = psycopg.connect(CONN_STR)
    cur = conn.cursor()

    sql_lines: list[str] = []
    sql_lines.append("BEGIN;")

    empty_tables: list[str] = []
    update_counts = {
        "kategoriler": 0,
        "danisma_kategorileri": 0,
        "sorular": 0,
        "cevaplar": 0,
        "dooh_idle_screen_contents": 0,
    }

    # kategoriler.ad_en
    cur.execute("SELECT id, ad FROM kategoriler WHERE ad_en IS NULL OR btrim(ad_en)='' ORDER BY id")
    rows = cur.fetchall()
    if not rows:
        empty_tables.append("kategoriler.ad_en")
    auto_ids = [r[0] for r in rows if r[0] not in CATEGORY_OVERRIDES]
    auto_tr = [r[1] for r in rows if r[0] not in CATEGORY_OVERRIDES]
    auto_en = batch_tr_to_en(auto_tr)
    auto_map = dict(zip(auto_ids, auto_en))
    for idx, (_id, ad) in enumerate(rows, start=1):
        en = CATEGORY_OVERRIDES.get(_id) or auto_map.get(_id) or tr_to_en(ad)
        sql_lines.append(
            f"UPDATE kategoriler SET ad_en = '{esc(en)}' WHERE id = {_id} AND (ad_en IS NULL OR btrim(ad_en)='');"
        )
        update_counts["kategoriler"] += 1
        if idx % 10 == 0:
            print(f"kategoriler progress: {idx}/{len(rows)}")

    # danisma_kategorileri.ad_en
    cur.execute("SELECT id, ad FROM danisma_kategorileri WHERE ad_en IS NULL OR btrim(ad_en)='' ORDER BY id")
    rows = cur.fetchall()
    if not rows:
        empty_tables.append("danisma_kategorileri.ad_en")
    auto_ids = [r[0] for r in rows if r[0] not in DANISMA_OVERRIDES]
    auto_tr = [r[1] for r in rows if r[0] not in DANISMA_OVERRIDES]
    auto_en = batch_tr_to_en(auto_tr)
    auto_map = dict(zip(auto_ids, auto_en))
    for idx, (_id, ad) in enumerate(rows, start=1):
        en = DANISMA_OVERRIDES.get(_id) or auto_map.get(_id) or tr_to_en(ad)
        sql_lines.append(
            f"UPDATE danisma_kategorileri SET ad_en = '{esc(en)}' WHERE id = {_id} AND (ad_en IS NULL OR btrim(ad_en)='');"
        )
        update_counts["danisma_kategorileri"] += 1
        if idx % 10 == 0:
            print(f"danisma progress: {idx}/{len(rows)}")

    # sorular.metin_en
    cur.execute("SELECT id, metin FROM sorular WHERE metin_en IS NULL OR btrim(metin_en)='' ORDER BY id")
    rows = cur.fetchall()
    if not rows:
        empty_tables.append("sorular.metin_en")
    soru_ids = [r[0] for r in rows]
    soru_tr = [r[1] for r in rows]
    soru_en = batch_tr_to_en(soru_tr)
    for idx, (_id, _metin) in enumerate(rows, start=1):
        en = soru_en[idx - 1] if idx - 1 < len(soru_en) else tr_to_en(_metin)
        sql_lines.append(
            f"UPDATE sorular SET metin_en = '{esc(en)}' WHERE id = {_id} AND (metin_en IS NULL OR btrim(metin_en)='');"
        )
        update_counts["sorular"] += 1
        if idx % 10 == 0:
            print(f"sorular progress: {idx}/{len(rows)}")

    # cevaplar.metin_en
    cur.execute("SELECT id, metin FROM cevaplar WHERE metin_en IS NULL OR btrim(metin_en)='' ORDER BY id")
    rows = cur.fetchall()
    if not rows:
        empty_tables.append("cevaplar.metin_en")
    cevap_tr = [r[1] for r in rows]
    cevap_en = batch_tr_to_en(cevap_tr)
    for idx, (_id, _metin) in enumerate(rows, start=1):
        en = cevap_en[idx - 1] if idx - 1 < len(cevap_en) else tr_to_en(_metin)
        sql_lines.append(
            f"UPDATE cevaplar SET metin_en = '{esc(en)}' WHERE id = {_id} AND (metin_en IS NULL OR btrim(metin_en)='');"
        )
        update_counts["cevaplar"] += 1
        if idx % 10 == 0:
            print(f"cevaplar progress: {idx}/{len(rows)}")

    # dooh_idle_screen_contents.baslik_en + metin_en
    cur.execute(
        "SELECT id, baslik, metin FROM dooh_idle_screen_contents "
        "WHERE baslik_en IS NULL OR btrim(baslik_en)='' OR metin_en IS NULL OR btrim(metin_en)='' "
        "ORDER BY id"
    )
    rows = cur.fetchall()
    if not rows:
        empty_tables.append("dooh_idle_screen_contents.baslik_en/metin_en")

    idle_baslik_src = []
    idle_metin_src = []
    for _id, baslik, metin in rows:
        idle_baslik_src.append("-" if (not baslik or baslik.strip() == "-") else baslik)
        idle_metin_src.append(metin)
    idle_baslik_en = batch_tr_to_en(idle_baslik_src)
    idle_metin_en = batch_tr_to_en(idle_metin_src)

    for idx, (_id, baslik, metin) in enumerate(rows, start=1):
        baslik_en = idle_baslik_en[idx - 1] if idx - 1 < len(idle_baslik_en) else ("-" if (not baslik or baslik.strip() == "-") else tr_to_en(baslik))
        metin_en = idle_metin_en[idx - 1] if idx - 1 < len(idle_metin_en) else tr_to_en(metin)

        sql_lines.append(
            f"UPDATE dooh_idle_screen_contents SET baslik_en = '{esc(baslik_en)}' "
            f"WHERE id = {_id} AND (baslik_en IS NULL OR btrim(baslik_en)='');"
        )
        sql_lines.append(
            f"UPDATE dooh_idle_screen_contents SET metin_en = '{esc(metin_en)}' "
            f"WHERE id = {_id} AND (metin_en IS NULL OR btrim(metin_en)='');"
        )
        update_counts["dooh_idle_screen_contents"] += 2
        if idx % 10 == 0:
            print(f"idle progress: {idx}/{len(rows)}")

    sql_lines.append("COMMIT;")

    OUT_SQL.write_text("\n".join(sql_lines) + "\n", encoding="utf-8")

    # execute generated SQL
    with conn.cursor() as run_cur:
        run_cur.execute("\n".join(sql_lines))
    conn.commit()
    conn.close()

    print("SQL_FILE", str(OUT_SQL))
    print("UPDATE_COUNTS", update_counts)
    print("NO_MISSING_FIELDS", empty_tables)


if __name__ == "__main__":
    main()
