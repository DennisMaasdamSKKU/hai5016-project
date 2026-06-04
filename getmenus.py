import os
from datetime import date
from pathlib import Path
from loguru import logger

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
LOG_DIR = PROJECT_ROOT / "logs"


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(LOG_DIR / "getmenus.log", rotation="1 MB", encoding="utf-8")
    logger.add(lambda message: print(message, end=""))


def get_today() -> str:
    return date.today().isoformat()


def get_connection_string() -> str:
    load_dotenv()
    conn_str = os.getenv("SUPABASE_CONNECTION_STRING")
    if not conn_str:
        raise EnvironmentError("SUPABASE_CONNECTION_STRING must be set")
    return conn_str


def get_menu(menu_date: str | None = None, limit: int = 20) -> list[dict]:
    """
    Return campus menu items from Supabase.

    Args:
        menu_date: Date in YYYY-MM-DD format. Defaults to today.
        limit: Maximum number of menu rows to return.
    """
    if menu_date is None:
        menu_date = date.today().isoformat()

    sql = """
    select
        menu_date,
        university,
        campus,
        restaurant_name,
        meal_type,
        meal_name,
        price_krw,
        serving_time,
        raw_text
    from public.campus_menu_items
    where menu_date = %s
      and is_valid_menu = true
    order by university, restaurant_name, meal_type, meal_name
    limit %s
    """

    conn_str = get_connection_string()

    with psycopg.connect(conn_str, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (menu_date, limit))
            return cur.fetchall()


if __name__ == "__main__":
    rows = get_menu()
    for row in rows:
        print(row)