import datetime
import os
import re
import time
from pathlib import Path
from dotenv import load_dotenv
import requests

load_dotenv()

api_key = os.getenv("FIRECRAWL_API_KEY")

# --- Step 01: Search + scrape with Firecrawl ---

api_url = "https://api.firecrawl.dev/v2/search"

headers = {
    "Authorization": f"Bearer {api_key}"
}

payload = {
    "query": "Chipotle Mexican Grill new menu items food innovation 2025",
    "limit": 5,
    "scrapeOptions": {"formats": ["markdown"]}
}

response = requests.post(api_url, headers=headers, json=payload)

data = response.json()
results = data["data"]["web"]
print(f"Firecrawl returned {len(results)} results")

# --- Step 02: Save results to knowledge/raw/ ---

Path("knowledge/raw").mkdir(parents=True, exist_ok=True)

for i, r in enumerate(results):
    print(f"  - {r['title']}")
    print(f"    {r['url']}")
    print(f"    markdown length: {len(r.get('markdown') or '')} chars")

    markdown = r.get("markdown") or ""
    if not markdown:
        print(f"    [skipped — no markdown]")
        continue

    slug = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", r["url"].lower())).strip("-")[:80]
    filename = f"{i + 1:02d}-{slug}.md"
    title = r.get("title") or r["url"]
    scraped_at = datetime.datetime.utcnow().isoformat(timespec="seconds")

    content = f"---\ntitle: {title}\nurl: {r['url']}\nscraped_at: {scraped_at}\n---\n\n{markdown}"
    (Path("knowledge/raw") / filename).write_text(content, encoding="utf-8")
    print(f"    saved → knowledge/raw/{filename}")
