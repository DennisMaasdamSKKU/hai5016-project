import json
import os
import urllib.request
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

from getmenus import get_menu
from halal_filter import group_by_halal_category
from known_halal_locations import get_known_halal_locations


PROJECT_ROOT = Path(__file__).resolve().parent
LOG_DIR = PROJECT_ROOT / "logs"
SMTP2GO_URL = "https://api.smtp2go.com/v3/email/send"


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(LOG_DIR / "send_daily_menu_email.log", rotation="1 MB", encoding="utf-8")
    logger.add(lambda message: print(message, end=""))


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise EnvironmentError(f"{name} must be set in .env")
    return value


def format_price(row: dict) -> str:
    price = row.get("price_krw")
    return f"{price} KRW" if price else "Price unknown"


def render_items(rows: list[dict], empty_message: str) -> str:
    if not rows:
        return f"<p style='color:#666; font-size:14px;'>{empty_message}</p>"

    cards = []

    for row in rows[:5]:
        cards.append(
            f"""
            <div style="border:1px solid #ddd; border-radius:12px; padding:14px; margin:10px 0; background:#ffffff;">
                <div style="font-size:14px; color:#666;">
                    {row.get("university", "")} · {row.get("restaurant_name", "")} · {row.get("meal_type", "")}
                </div>

                <div style="font-size:17px; font-weight:700; margin-top:6px; line-height:1.4;">
                    {row.get("meal_name", "")}
                </div>

                <div style="font-size:14px; margin-top:8px; line-height:1.5;">
                    <strong>Price:</strong> {format_price(row)}<br>
                    <strong>Time:</strong> {row.get("serving_time") or "Time unknown"}
                </div>

                <div style="font-size:13px; color:#555; margin-top:8px; line-height:1.5;">
                    <strong>Guidance:</strong> {row.get("halal_reason", "")}
                </div>
            </div>
            """
        )

    return "\n".join(cards)


def render_known_halal_locations() -> str:
    known_locations = get_known_halal_locations()

    if not known_locations:
        return "<p style='color:#666;'>No known halal campus locations stored yet.</p>"

    cards = []

    for item in known_locations:
        cards.append(
            f"""
            <div style="border:1px solid #ddd; border-radius:12px; padding:14px; margin:10px 0; background:#ffffff;">
                <div style="font-size:16px; font-weight:700;">
                    {item["university"]} — {item["location"]}
                </div>

                <div style="font-size:14px; margin-top:6px; line-height:1.5;">
                    {item["note"]}
                </div>

                <div style="font-size:12px; color:#777; margin-top:8px;">
                    Source: {item["source"]}
                </div>
            </div>
            """
        )

    return "\n".join(cards)


def build_halal_menu_html(rows: list[dict]) -> str:
    today = date.today().isoformat()
    grouped = group_by_halal_category(rows)
    known_locations_html = render_known_halal_locations()

    return f"""
    <div style="font-family:Arial, sans-serif; background:#f6f7f9; padding:24px;">
        <div style="max-width:780px; margin:0 auto; background:#ffffff; border-radius:18px; padding:26px;">

            <h1 style="margin-bottom:4px; font-size:26px;">
                Daily Halal-Aware Campus Menu Briefing
            </h1>

            <p style="color:#666; margin-top:0; font-size:14px;">
                Date: {today}
            </p>

            <div style="background:#fff4d6; border-left:5px solid #f0b429; padding:14px; margin:20px 0; border-radius:8px;">
                <strong>Important:</strong> These results are not halal certification.
                The system only uses visible menu text to help Muslim students screen options.
                Chicken or beef is not treated as halal unless explicitly labeled halal.
            </div>

            <div style="background:#eef6ff; border-left:5px solid #4a90e2; padding:14px; margin:20px 0; border-radius:8px;">
                <strong>How to use this briefing:</strong>
                First check for explicitly halal-labeled items. If none are found, use seafood or vegetarian fallback options.
                Meat dishes are shown separately so students can ask staff whether halal meat was used.
                Avoid items are flagged because the menu text contains visible pork, alcohol, processed-meat, or unclear meat-risk keywords.
            </div>

            <h2 style="margin-top:28px;">✅ Explicit halal-labeled items</h2>
            {render_items(grouped["halal_labeled"], "No explicitly halal-labeled items found in today’s menu data.")}

            <h2 style="margin-top:28px;">🐟 Seafood fallback options</h2>
            {render_items(grouped["seafood"], "No seafood fallback options found in today’s menu data.")}

            <h2 style="margin-top:28px;">🥬 Vegetarian fallback options</h2>
            {render_items(grouped["vegetarian"], "No vegetarian fallback options found in today’s menu data.")}

            <h2 style="margin-top:28px;">⚠️ Meat dishes — check halal status</h2>
            {render_items(grouped["unknown_meat"], "No meat items requiring confirmation found.")}

            <h2 style="margin-top:28px;">❓ Unknown — ask staff</h2>
            {render_items(grouped["unknown"], "No unknown items found.")}

            <h2 style="margin-top:28px;">🚫 Avoid — visible non-halal risk</h2>
            {render_items(grouped["avoid"], "No visible pork/alcohol/processed-meat risk items found.")}

            <h2 style="margin-top:32px;">📍 Known campus halal locations</h2>
            <p style="color:#666; font-size:14px; line-height:1.5;">
                These are known campus locations that may provide halal options.
                Students should still confirm current availability and certification with staff.
            </p>
            {known_locations_html}

            <p style="font-size:12px; color:#777; margin-top:32px; line-height:1.5;">
                Generated automatically by the HAI5016 halal-aware campus menu assistant.
                This is a screening tool, not a religious ruling or certification system.
            </p>
        </div>
    </div>
    """


def send_email(html_body: str) -> dict:
    api_key = get_required_env("SMTP2GO_API_KEY")
    sender = get_required_env("SMTP2GO_SENDER_EMAIL")
    recipient = get_required_env("SMTP2GO_RECIPIENT_EMAIL")

    payload = {
        "api_key": api_key,
        "sender": sender,
        "to": [recipient],
        "subject": f"Daily Halal-Aware Campus Menu Briefing - {date.today().isoformat()}",
        "html_body": html_body,
        "text_body": (
            "Your daily halal-aware campus menu briefing is available in the HTML version of this email. "
            "This is not halal certification; please confirm with staff when needed."
        ),
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        SMTP2GO_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        response_body = response.read().decode("utf-8")
        return json.loads(response_body)


def main() -> None:
    setup_logging()
    load_dotenv()

    logger.info("Loading menu rows from Supabase")
    rows = get_menu(limit=200)
    logger.info(f"Loaded {len(rows)} menu rows")

    html_body = build_halal_menu_html(rows)

    logger.info("Sending halal-aware daily menu email via SMTP2GO")
    result = send_email(html_body)

    logger.info(f"SMTP2GO response: {result}")
    print(result)


if __name__ == "__main__":
    main()