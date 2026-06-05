"""
halal_filter.py
---------------
Classifies campus menu items into halal-aware categories.

Important:
This does NOT certify food as halal.
It only uses visible menu text to help Muslim students screen menu items.

Design choice:
The filter is intentionally conservative.

It only labels an item as "halal_labeled" if the menu text explicitly contains
"halal" or "할랄".

Chicken, beef, and other non-pork land meat are NOT treated as halal by default,
because the menu does not confirm halal slaughter or certification.

Seafood is only used as a fallback if no land-meat keyword is visible.
"""

from __future__ import annotations


HALAL_KEYWORDS = [
    "halal",
    "할랄",
]


AVOID_KEYWORDS = [
    # English pork / processed meat / alcohol risk
    "pork",
    "ham",
    "bacon",
    "spam",
    "sausage",
    "gelatin",
    "alcohol",
    "wine",
    "pork cutlet",
    "meatball",
    "hot dog",
    "hamburger",
    "dumpling",
    "tonkotsu",

    # Korean pork / explicit non-halal risk
    "돼지",
    "돼지고기",
    "돈육",
    "제육",
    "삼겹살",
    "돈가스",
    "돈까스",
    "카츠",
    "가츠",
    "탕수육",
    "햄",
    "베이컨",
    "스팸",
    "소시지",
    "소세지",
    "족발",
    "순대",
    "돈코츠",

    # Korean unclear processed meat / mixed meat risk
    "감자탕",
    "비엔나",
    "떡갈비",
    "너비아니",
    "미트볼",
    "핫도그",
    "햄버거",
    "만두",
    "군만두",
    "물만두",
    "왕교자",
    "교자",

    # Alcohol-related
    "막걸리",
    "와인",
    "술",
]


VEGETARIAN_KEYWORDS = [
    # English
    "vegetable",
    "vegetarian",
    "tofu",
    "salad",
    "egg",
    "cheese",
    "mushroom",

    # Korean
    "야채",
    "채소",
    "두부",
    "샐러드",
    "계란",
    "달걀",
    "치즈",
    "버섯",
    "비빔밥",
]


SEAFOOD_KEYWORDS = [
    # English
    "fish",
    "shrimp",
    "tuna",
    "seafood",
    "squid",
    "mackerel",
    "salmon",
    "anchovy",

    # Korean
    "생선",
    "새우",
    "참치",
    "해물",
    "오징어",
    "고등어",
    "연어",
    "멸치",
    "꼬막",
    "낙지",
    "조개",
]


LAND_MEAT_KEYWORDS = [
    # English
    "chicken",
    "beef",
    "meat",
    "duck",

    # Korean
    "닭",
    "치킨",
    "찜닭",
    "소고기",
    "쇠고기",
    "불고기",
    "고기",
    "오리",
]


ANIMAL_KEYWORDS = LAND_MEAT_KEYWORDS + SEAFOOD_KEYWORDS


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return value.lower().strip()


def contains_any(text: str, keywords: list[str]) -> list[str]:
    return [keyword for keyword in keywords if keyword.lower() in text]


def classify_menu_item(row: dict) -> dict:
    combined_text = " ".join(
        [
            str(row.get("meal_name", "")),
            str(row.get("raw_text", "")),
            str(row.get("restaurant_name", "")),
        ]
    )

    text = normalize_text(combined_text)

    halal_matches = contains_any(text, HALAL_KEYWORDS)
    avoid_matches = contains_any(text, AVOID_KEYWORDS)
    vegetarian_matches = contains_any(text, VEGETARIAN_KEYWORDS)
    seafood_matches = contains_any(text, SEAFOOD_KEYWORDS)
    land_meat_matches = contains_any(text, LAND_MEAT_KEYWORDS)
    animal_matches = contains_any(text, ANIMAL_KEYWORDS)

    result = dict(row)

    if halal_matches:
        result["halal_category"] = "halal_labeled"
        result["halal_reason"] = (
            "Explicit halal keyword found in visible menu text: "
            + ", ".join(halal_matches)
        )

    elif avoid_matches:
        result["halal_category"] = "avoid"
        result["halal_reason"] = (
            "Contains visible pork, alcohol, processed-meat, or unclear meat risk keyword(s): "
            + ", ".join(avoid_matches)
        )

    elif seafood_matches and not land_meat_matches:
        result["halal_category"] = "seafood"
        result["halal_reason"] = (
            "Seafood fallback candidate; no visible pork/alcohol/land-meat risk keyword found. Keyword(s): "
            + ", ".join(seafood_matches)
        )

    elif vegetarian_matches and not animal_matches:
        result["halal_category"] = "vegetarian"
        result["halal_reason"] = (
            "Vegetarian fallback candidate based on visible keyword(s): "
            + ", ".join(vegetarian_matches)
        )

    elif land_meat_matches:
        result["halal_category"] = "unknown_meat"
        result["halal_reason"] = (
            "Land-meat keyword found, but no explicit halal label. Needs confirmation: "
            + ", ".join(land_meat_matches)
        )

    elif seafood_matches:
        result["halal_category"] = "unknown"
        result["halal_reason"] = (
            "Seafood keyword found, but mixed context needs confirmation: "
            + ", ".join(seafood_matches)
        )

    else:
        result["halal_category"] = "unknown"
        result["halal_reason"] = (
            "No clear halal, vegetarian, seafood, avoid, or meat keyword found. "
            "Needs manual confirmation."
        )

    return result


def classify_menu_items(rows: list[dict]) -> list[dict]:
    return [classify_menu_item(row) for row in rows]


def group_by_halal_category(rows: list[dict]) -> dict[str, list[dict]]:
    grouped = {
        "halal_labeled": [],
        "seafood": [],
        "vegetarian": [],
        "unknown_meat": [],
        "unknown": [],
        "avoid": [],
    }

    for row in classify_menu_items(rows):
        grouped[row["halal_category"]].append(row)

    return grouped