# Markdown Save Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `scrape_pipeline.py` so each Firecrawl search result with non-empty markdown is saved as a numbered, frontmatter-annotated `.md` file in `knowledge/raw/`.

**Architecture:** Inline changes to the existing loop in `scrape_pipeline.py` — no new files, no new functions. A test module patches `requests.post` to verify file output in a temp directory without hitting the network.

**Tech Stack:** Python 3 stdlib (`datetime`, `re`, `pathlib`), `pytest`, `python-dotenv`, `requests`.

---

## Files

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `scrape_pipeline.py` | Add `import datetime`, `mkdir`, and save block inside the loop |
| Create | `tests/test_save.py` | Verify slug logic, frontmatter, skip-on-empty, and overwrite behavior |

---

### Task 1: Write failing tests

**Files:**
- Create: `tests/test_save.py`

- [ ] **Step 1: Create the test file**

```python
# tests/test_save.py
import datetime
import importlib
import re
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


def _make_response(results):
    mock = MagicMock()
    mock.json.return_value = {"data": {"web": results}}
    return mock


def _run_pipeline(tmp_path, results, monkeypatch):
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    monkeypatch.chdir(tmp_path)
    with patch("requests.post", return_value=_make_response(results)):
        if "scrape_pipeline" in sys.modules:
            del sys.modules["scrape_pipeline"]
        sys.path.insert(0, str(Path(__file__).parent.parent))
        importlib.import_module("scrape_pipeline")


def test_file_created_with_frontmatter(tmp_path, monkeypatch):
    results = [
        {
            "title": "Chipotle News",
            "url": "https://ir.chipotle.com/news-releases",
            "markdown": "## Q4 Results\n\nRecord revenue.",
        }
    ]
    _run_pipeline(tmp_path, results, monkeypatch)
    files = list((tmp_path / "knowledge" / "raw").glob("*.md"))
    assert len(files) == 1
    content = files[0].read_text()
    assert "title: Chipotle News" in content
    assert "url: https://ir.chipotle.com/news-releases" in content
    assert "scraped_at:" in content
    assert "## Q4 Results" in content


def test_filename_zero_padded_slug(tmp_path, monkeypatch):
    results = [
        {
            "title": "News",
            "url": "https://ir.chipotle.com/news-releases",
            "markdown": "content",
        },
        {
            "title": "News",
            "url": "https://ir.chipotle.com/news-releases",
            "markdown": "content2",
        },
    ]
    _run_pipeline(tmp_path, results, monkeypatch)
    raw = tmp_path / "knowledge" / "raw"
    names = sorted(f.name for f in raw.glob("*.md"))
    assert names[0].startswith("01-")
    assert names[1].startswith("02-")
    assert names[0] != names[1]


def test_empty_markdown_skipped(tmp_path, monkeypatch):
    results = [
        {"title": "Empty", "url": "https://ir.chipotle.com/empty", "markdown": None},
        {"title": "Empty2", "url": "https://ir.chipotle.com/empty2", "markdown": ""},
    ]
    _run_pipeline(tmp_path, results, monkeypatch)
    files = list((tmp_path / "knowledge" / "raw").glob("*.md"))
    assert len(files) == 0


def test_overwrite_on_rerun(tmp_path, monkeypatch):
    result = [
        {
            "title": "Page",
            "url": "https://ir.chipotle.com/page",
            "markdown": "first run",
        }
    ]
    _run_pipeline(tmp_path, result, monkeypatch)
    result[0]["markdown"] = "second run"
    _run_pipeline(tmp_path, result, monkeypatch)
    files = list((tmp_path / "knowledge" / "raw").glob("*.md"))
    assert len(files) == 1
    assert "second run" in files[0].read_text()


def test_missing_title_falls_back_to_url(tmp_path, monkeypatch):
    results = [
        {
            "title": None,
            "url": "https://ir.chipotle.com/no-title",
            "markdown": "some content",
        }
    ]
    _run_pipeline(tmp_path, results, monkeypatch)
    files = list((tmp_path / "knowledge" / "raw").glob("*.md"))
    assert len(files) == 1
    assert "url: https://ir.chipotle.com/no-title" in files[0].read_text()
    assert "title: https://ir.chipotle.com/no-title" in files[0].read_text()
```

- [ ] **Step 2: Run tests to confirm they all fail**

```bash
venv/bin/pytest tests/test_save.py -v
```

Expected: all 5 tests FAIL (ImportError or AttributeError — `scrape_pipeline` has no save logic yet).

---

### Task 2: Implement the save logic in `scrape_pipeline.py`

**Files:**
- Modify: `scrape_pipeline.py`

- [ ] **Step 1: Add `import datetime` and update the loop**

Replace the entire file with:

```python
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
    "query": "Chipotle investor relations press releases",
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
```

- [ ] **Step 2: Run the tests**

```bash
venv/bin/pytest tests/test_save.py -v
```

Expected output:
```
tests/test_save.py::test_file_created_with_frontmatter PASSED
tests/test_save.py::test_filename_zero_padded_slug PASSED
tests/test_save.py::test_empty_markdown_skipped PASSED
tests/test_save.py::test_overwrite_on_rerun PASSED
tests/test_save.py::test_missing_title_falls_back_to_url PASSED

5 passed
```

If any test fails, read the error and fix before committing.

- [ ] **Step 3: Commit**

```bash
git add scrape_pipeline.py tests/test_save.py
git commit -m "feat: save Firecrawl results as markdown files in knowledge/raw/"
```

---

### Task 3: Smoke-test with the real API

**Files:**
- No changes — verification only.

- [ ] **Step 1: Run the pipeline**

```bash
venv/bin/python scrape_pipeline.py
```

Expected output (exact filenames will vary by URL):
```
Firecrawl returned 5 results
  - Chipotle Mexican Grill | Investor Relations
    https://ir.chipotle.com/
    markdown length: 4821 chars
    saved → knowledge/raw/01-ir-chipotle-com.md
  ...
```

- [ ] **Step 2: Inspect the files**

```bash
ls knowledge/raw/
head -8 knowledge/raw/01-*.md
```

Expected: frontmatter block with `title`, `url`, `scraped_at` fields, followed by a blank line and markdown content.

- [ ] **Step 3: Commit the generated files (optional)**

If you want `knowledge/raw/` tracked in git:

```bash
git add knowledge/raw/
git commit -m "chore: add initial knowledge/raw/ scrape results"
```

Skip this step if `knowledge/raw/` should stay gitignored.
