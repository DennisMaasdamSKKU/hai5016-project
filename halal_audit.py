import os
from collections import Counter, defaultdict

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

from halal_filter import classify_menu_items


def get_connection_string() -> str:
    load_dotenv()
    conn_str = os.getenv("SUPABASE_CONNECTION_STRING")
    if not conn_str:
        raise EnvironmentError("SUPABASE_CONNECTION_STRING must be set")
    return conn_str


def load_all_menu_items() -> list[dict]:
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
    where is_valid_menu = true
    order by menu_date desc, university, restaurant_name
    """

    with psycopg.connect(get_connection_string(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()


def main() -> None:
    rows = load_all_menu_items()
    classified = classify_menu_items(rows)

    overall = Counter(row["halal_category"] for row in classified)

    print("Overall halal-aware category counts")
    print("===================================")
    for category, count in overall.items():
        print(f"{category}: {count}")

    print("\nCounts by date")
    print("==============")
    by_date = defaultdict(Counter)
    for row in classified:
        by_date[str(row["menu_date"])][row["halal_category"]] += 1

    for menu_date in sorted(by_date.keys(), reverse=True):
        print(menu_date, dict(by_date[menu_date]))

    print("\nSample useful candidates")
    print("========================")

    for category in ["halal_labeled", "seafood", "vegetarian", "unknown_meat"]:
        print(f"\n--- {category} ---")
        examples = [row for row in classified if row["halal_category"] == category][:5]

        if not examples:
            print("No examples found.")
            continue

        for row in examples:
            print(
                f"- {row['menu_date']} | {row['university']} | "
                f"{row['restaurant_name']} | {row['meal_type']} | "
                f"{row['meal_name']}"
            )
            print(f"  Reason: {row['halal_reason']}")


if __name__ == "__main__":
    main()