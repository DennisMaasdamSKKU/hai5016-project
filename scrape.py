import os
import json
import httpx
import pandas as pd
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv
from pathlib import Path
import asyncio
import concurrent.futures

# Load environment variables
load_dotenv()
API_KEY = os.getenv('AZURE_FOUNDRY_API_KEY')
AZURE_ENDPOINT = os.getenv('AZURE_FOUNDRY_ENDPOINT')
MODEL_NAME = os.getenv('AZURE_FOUNDRY_MODEL')

# Logging setup
Path('logs').mkdir(exist_ok=True)
logger.add('logs/scrape_{time:YYYY-MM-DD}.log', rotation='1 day')

# Output file
scrape_date = datetime.now().strftime('%Y-%m-%d')
output_path = f'results/menus-{scrape_date}.jsonl'
Path('results').mkdir(exist_ok=True)


# Read Excel with headers on row 2 (0-indexed) and correct column name 'Url'
excel_path = 'campus_restaurant_websites.xlsx'
df = pd.read_excel(excel_path, header=2, usecols=['University', 'Url'])

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36'

async def fetch_text(url):
    try:
        async with httpx.AsyncClient(timeout=5.0, headers={'User-Agent': USER_AGENT}) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return None

def extract_readable_text(html):
    # Simple fallback: strip tags, or use BeautifulSoup if available
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        return soup.get_text(separator=' ', strip=True)
    except ImportError:
        import re
        return re.sub('<[^<]+?>', '', html)

async def call_ai_model(text, university, url):
    prompt = f"""
    Extract the menu information from the following university restaurant web page text. Return ONLY a JSON array of menu items, with no markdown, no code block, and no explanation. Each item must include:
- scrape_date (YYYY-MM-DD)
- url
- menu_date (if available, else null)
- meal_type (breakfast, lunch, dinner, or unknown)
- meal_name
- price_krw (if available, else null)
- university
- restaurant_name (if available, else null)
Skip invalid or empty meals.

Web page text:
{text}
"""
    endpoint = AZURE_ENDPOINT.rstrip('/') + "/chat/completions"
    headers = {
        'api-key': API_KEY,
        'Content-Type': 'application/json',
    }
    data = {
            'model': MODEL_NAME,
            'messages': [
                {"role": "system", "content": "You are a helpful assistant that extracts structured menu data from university restaurant web pages."},
                {"role": "user", "content": prompt}
            ],
            'max_completion_tokens': 4096,
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(endpoint, headers=headers, json=data)
            resp.raise_for_status()
            result = resp.json()
            if isinstance(result, dict) and 'choices' in result:
                choice = result['choices'][0]
                content = choice.get('message', {}).get('content', '').strip()
                finish_reason = choice.get('finish_reason', None)
                usage = result.get('usage', None)
                if not content:
                    logger.error(f"AI response for {url} has empty content. Full response: {result}")
                    return None
                try:
                    return json.loads(content)
                except Exception:
                    logger.error(f"AI response not valid JSON for {url}. Raw response: {content}. Finish reason: {finish_reason}, Usage: {usage}, Full response: {result}")
                    return None
            else:
                logger.error(f"Unexpected AI response for {url}: {result}")
                return None
    except Exception as e:
        logger.error(f"AI model call failed for {url}: {e}")
        return None

def is_valid_menu_item(item):
    required = ['scrape_date', 'url', 'meal_type', 'meal_name', 'university']
    if not all(item.get(k) for k in required):
        return False
    if item['meal_type'] not in ['breakfast', 'lunch', 'dinner', 'unknown']:
        return False
    if not item['meal_name'].strip():
        return False
    return True

async def process_row(row):
    university = row['University']
    url = row['Url']
    html = await fetch_text(url)
    if not html:
        return []
    text = extract_readable_text(html)
    ai_result = await call_ai_model(text, university, url)
    if not ai_result:
        return []
    valid_items = [item for item in ai_result if is_valid_menu_item(item)]
    return valid_items

async def main():
    tasks = []
    for _, row in df.iterrows():
        tasks.append(process_row(row))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        for res in results:
            if isinstance(res, Exception):
                logger.error(f"Task failed: {res}")
                continue
            for item in res:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
    logger.info(f"Scraping complete. Results saved to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
