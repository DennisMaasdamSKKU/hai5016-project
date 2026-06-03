import os
from datetime import datetime, timezone

import requests
import psycopg
from dotenv import load_dotenv


load_dotenv()


API_KEY = os.getenv("EXCHANGE_RATE_API_KEY")
SUPABASE_CONNECTION_STRING = os.getenv("SUPABASE_CONNECTION_STRING")


def fetch_rates(base_currency="USD"):
    if not API_KEY:
        raise ValueError("Missing EXCHANGE_RATE_API_KEY in environment")

    url = f"https://v6.exchangerate-api.com/v6/{API_KEY}/latest/{base_currency}"
    response = requests.get(url, timeout=20)
    response.raise_for_status()

    data = response.json()

    if data.get("result") != "success":
        raise RuntimeError(f"Exchange rate API error: {data}")

    return data["base_code"], data["conversion_rates"]


def save_rates(base_currency, rates):
    if not SUPABASE_CONNECTION_STRING:
        raise ValueError("Missing SUPABASE_CONNECTION_STRING in environment")

    fetched_at = datetime.now(timezone.utc)

    with psycopg.connect(SUPABASE_CONNECTION_STRING) as conn:
        with conn.cursor() as cur:
            for target_currency, rate in rates.items():
                cur.execute(
                    """
                    INSERT INTO fx_rates_cache
                        (base_currency, target_currency, rate, fetched_at, source)
                    VALUES
                        (%s, %s, %s, %s, %s)
                    """,
                    (
                        base_currency,
                        target_currency,
                        rate,
                        fetched_at,
                        "exchangerate-api",
                    ),
                )
        conn.commit()


def main():
    base_currency, rates = fetch_rates("USD")
    save_rates(base_currency, rates)
    print(f"Saved {len(rates)} exchange rates for base currency {base_currency}")


if __name__ == "__main__":
    main()