# Design: Save Firecrawl Results as Markdown Files

**Date:** 2026-04-30  
**Status:** Approved  
**Scope:** Extend `scrape_pipeline.py` to persist each Firecrawl search result as a markdown file in `knowledge/raw/`.

---

## Goal

After each pipeline run, `knowledge/raw/` contains up to five markdown files — one per Firecrawl result — with enough metadata to cite the source when reading the files later.

---

## File Naming

Pattern: `{index:02d}-{slug}.md`

- **Index** is 1-based, zero-padded (01, 02, … 05). Ensures uniqueness even when multiple results share the same title or URL domain, and keeps files sorted in result order.
- **Slug** is derived from the result URL: lowercase, non-alphanumeric characters replaced with hyphens, consecutive hyphens collapsed, leading/trailing hyphens stripped, capped at 80 characters.

Example:
```
https://ir.chipotle.com/news-releases  →  01-ir-chipotle-com-news-releases.md
```

---

## File Contents

Each file contains a YAML frontmatter block followed by the scraped markdown body:

```markdown
---
title: Chipotle Investor Relations – News Releases
url: https://ir.chipotle.com/news-releases
scraped_at: 2026-04-30T14:23:01
---

<markdown body>
```

| Field | Source | Notes |
|---|---|---|
| `title` | `r['title']` | Falls back to URL if missing |
| `url` | `r['url']` | Canonical source; used for citation |
| `scraped_at` | `datetime.utcnow()` | UTC, ISO-8601, second precision |
| Body | `r.get('markdown')` | Scraped page content |

---

## Empty Result Handling

If `r.get('markdown')` is falsy (None or empty string), the file is **skipped** and a warning is printed. Empty files are worse than missing files for downstream consumers.

---

## Overwrite Behavior

Re-running the pipeline overwrites existing files in `knowledge/raw/` silently. No versioning.

---

## Implementation Approach

Inline in the existing loop — no new functions, no new modules.

Changes to `scrape_pipeline.py`:
1. Add `import datetime` at the top (`re` and `Path` already imported).
2. Call `Path("knowledge/raw").mkdir(parents=True, exist_ok=True)` once before the loop.
3. Inside the loop, after the existing prints: check for empty markdown (skip+warn), derive slug, build frontmatter string, write file, print confirmation.

No new dependencies beyond stdlib.

---

## Success Criteria

- After a successful run, `knowledge/raw/` contains one `.md` file per non-empty result.
- Each file has valid YAML frontmatter with `title`, `url`, and `scraped_at`.
- Files sort in result order (01-, 02-, …).
- Results with no markdown produce a printed warning and no file.
- Re-running overwrites files cleanly.
