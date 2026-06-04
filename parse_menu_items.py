import os
import re
from datetime import date
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from loguru import logger


PROJECT_ROOT = Path(__file__).resolve().parent
LOG_DIR = PROJECT_ROOT / "logs"


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(LOG_DIR / "parse_menu_items.log", rotation="1 MB", encoding="utf-8")
    logger.add(lambda message: print(message, end=""))


def get_connection_string() -> str:
    load_dotenv()
    conn_str = os.getenv("SUPABASE_CONNECTION_STRING")
    if not conn_str:
        raise EnvironmentError("SUPABASE_CONNECTION_STRING must be set in .env")
    return conn_str


def load_today_snapshots(conn_str: str) -> list[dict]:
    sql = """
    select
        s.id as snapshot_id,
        s.source_id,
        s.scrape_date,
        s.html_raw,
        cms.university_name,
        cms.campus
    from public.scraped_html_snapshots s
    join public.campus_menu_sources cms
      on cms.id = s.source_id
    where s.scrape_date = %s
    order by s.created_at desc
    """
    with psycopg.connect(conn_str, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (date.today().isoformat(),))
            return cur.fetchall()


def already_parsed(conn_str: str, snapshot_id: str) -> bool:
    sql = """
    select 1
    from public.campus_menu_items
    where snapshot_id = %s
    limit 1
    """
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (snapshot_id,))
            return cur.fetchone() is not None


def html_to_lines(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n")
    lines = []

    for line in text.splitlines():
        clean = re.sub(r"\s+", " ", line).strip()
        if len(clean) < 2:
            continue
        if clean in {"Home", "Search", "Login", "Menu"}:
            continue
        lines.append(clean)

    return lines


def looks_like_menu_item(line: str) -> bool:
    if len(line) < 3 or len(line) > 120:
        return False

    ignore_keywords = [
        "copyright",
        "privacy",
        "login",
        "sungkyunkwan",
        "성균관대학교",
        "javascript",
        "조회",
        "검색",
    ]
    lower = line.lower()
    if any(word in lower for word in ignore_keywords):
        return False

    food_signals = [
        "rice", "soup", "kimchi", "noodle", "pork", "chicken", "beef",
        "fish", "salad", "egg", "curry", "밥", "국", "김치", "라면",
        "돈까스", "제육", "치킨", "카레", "덮밥", "찌개", "볶음",
    ]

    return any(signal in lower for signal in food_signals)


def save_items(conn_str: str, snapshot: dict, lines: list[str]) -> int:
    menu_lines = [line for line in lines if looks_like_menu_item(line)]

    if not menu_lines:
        menu_lines = lines[:20]

    sql = """
    insert into public.campus_menu_items (
        snapshot_id,
        source_id,
        menu_date,
        university_name,
        campus,
        item_name,
        raw_text
    ) values (
        %(snapshot_id)s,
        %(source_id)s,
        %(menu_date)s,
        %(university_name)s,
        %(campus)s,
        %(item_name)s,
        %(raw_text)s
    )
    """

    rows = []
    for line in menu_lines[:50]:
        rows.append({
            "snapshot_id": snapshot["snapshot_id"],
            "source_id": snapshot["source_id"],
            "menu_date": snapshot["scrape_date"],
            "university_name": snapshot["university_name"],
            "campus": snapshot["campus"],
            "item_name": line[:250],
            "raw_text": line,
        })

    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, rows)
        conn.commit()

    return len(rows)


def main() -> None:
    setup_logging()
    conn_str = get_connection_string()

    snapshots = load_today_snapshots(conn_str)
    logger.info(f"Loaded {len(snapshots)} snapshots for today")

    total_inserted = 0

    for snapshot in snapshots:
        snapshot_id = snapshot["snapshot_id"]

        if already_parsed(conn_str, snapshot_id):
            logger.info(f"Skipping snapshot {snapshot_id} — already parsed")
            continue

        lines = html_to_lines(snapshot["html_raw"])
        inserted = save_items(conn_str, snapshot, lines)

        logger.info(f"Parsed snapshot {snapshot_id}: inserted {inserted} menu rows")
        total_inserted += inserted

    logger.info(f"Parser finished. Total inserted rows: {total_inserted}")


if __name__ == "__main__":
    main()