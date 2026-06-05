from getmenus import get_menu
from halal_filter import group_by_halal_category


def format_price(row: dict) -> str:
    price = row.get("price_krw")
    return f"{price} KRW" if price else "Price unknown"


def print_section(title: str, rows: list[dict], limit: int = 5) -> None:
    print(f"\n=== {title} ===")

    if not rows:
        print("No items found.")
        return

    for row in rows[:limit]:
        print(
            f"- {row.get('university', '')} | "
            f"{row.get('restaurant_name', '')} | "
            f"{row.get('meal_type', '')}"
        )
        print(f"  Menu: {row.get('meal_name', '')}")
        print(f"  Price: {format_price(row)}")
        print(f"  Time: {row.get('serving_time') or 'Time unknown'}")
        print(f"  Guidance: {row.get('halal_reason', '')}")


def main() -> None:
    rows = get_menu(limit=200)
    grouped = group_by_halal_category(rows)

    print("Daily Halal-Aware Campus Menu Briefing")
    print("=" * 45)
    print("Important: These results are NOT halal certification.")
    print("The system uses visible menu text to help Muslim students screen options.")
    print("Chicken or beef is not treated as halal unless explicitly labeled halal.")
    print("Meat dishes are shown separately so students can ask staff for confirmation.")

    print_section("✅ Explicit halal-labeled items", grouped["halal_labeled"])
    print_section("🐟 Seafood fallback options", grouped["seafood"])
    print_section("🥬 Vegetarian fallback options", grouped["vegetarian"])
    print_section("⚠️ Meat dishes — check halal status", grouped["unknown_meat"])
    print_section("❓ Unknown — needs manual confirmation", grouped["unknown"])
    print_section("🚫 Avoid — visible non-halal risk", grouped["avoid"])


if __name__ == "__main__":
    main()