from __future__ import annotations

import csv
import time
from pathlib import Path
from urllib.parse import quote

import psycopg
import requests

INPUT_TSV = Path("scripts/pg_missing_i18n.tsv")
OUT_SQL = Path("scripts/backfill_i18n_en_pg.sql")
CONN_STR = "host=localhost port=5432 dbname=eisa user=eisa password=eisa"


def esc(text: str) -> str:
    return text.replace("'", "''")


def translate_tr_to_en(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    if text == "-":
        return "-"

    url = (
        "https://api.mymemory.translated.net/get"
        f"?q={quote(text)}&langpair=tr|en"
    )

    for attempt in range(6):
        try:
            res = requests.get(url, timeout=12)
            res.raise_for_status()
            payload = res.json()
            translated = (payload.get("responseData") or {}).get("translatedText", "").strip()
            if translated:
                return translated
        except Exception:
            time.sleep(0.6 + attempt * 0.4)
    return text


def main() -> None:
    rows: list[tuple[str, int, str, str]] = []
    with INPUT_TSV.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for rec in reader:
            rows.append((rec["table"], int(rec["id"]), rec["field"], rec["tr_text"]))

    sql_lines: list[str] = ["BEGIN;"]

    total = len(rows)
    print(f"rows_to_translate={total}")
    for i, (table, _id, field, tr_text) in enumerate(rows, start=1):
        print(f"translating {i}/{total}: {table}.{field} id={_id}")
        en = translate_tr_to_en(tr_text)
        sql_lines.append(
            f"UPDATE {table} SET {field} = '{esc(en)}' WHERE id = {_id} AND ({field} IS NULL OR btrim({field})='');"
        )
        time.sleep(0.12)

    sql_lines.append("COMMIT;")
    OUT_SQL.write_text("\n".join(sql_lines) + "\n", encoding="utf-8")

    conn = psycopg.connect(CONN_STR)
    with conn.cursor() as cur:
        cur.execute("\n".join(sql_lines))
    conn.commit()
    conn.close()

    print(f"SQL_WRITTEN {OUT_SQL}")


if __name__ == "__main__":
    main()
