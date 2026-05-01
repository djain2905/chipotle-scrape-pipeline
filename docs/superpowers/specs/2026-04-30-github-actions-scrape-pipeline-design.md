# GitHub Actions Scrape Pipeline — Design Spec

**Date:** 2026-04-30
**Status:** Approved

---

## Overview

Schedule `scrape_pipeline.py` to run automatically on GitHub Actions every Monday, commit the resulting `knowledge/raw/` markdown files back to `main`, and surface failures as a red Actions run.

---

## Trigger

- **Cron:** `0 6 * * 1` — every Monday at 06:00 UTC
- **Manual:** `workflow_dispatch` for on-demand runs and workflow testing

---

## Job: `scrape`

Single job on `ubuntu-latest`.

### Permissions

`contents: write` — required to push the auto-commit back to the repo. Uses the built-in `GITHUB_TOKEN`; no extra secret needed.

### Steps

| Step | Action / Command |
|------|-----------------|
| Checkout | `actions/checkout@v4` with `GITHUB_TOKEN` |
| Python setup | `actions/setup-python@v5`, version `3.13`, pip cache keyed on `requirements.txt` |
| Install deps | `pip install -r requirements.txt` |
| Run pipeline | `python scrape_pipeline.py` with `FIRECRAWL_API_KEY` injected from repo secret |
| Commit & push | Native git commands (see below) |

### Commit step

```bash
git config user.name  "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"
git add knowledge/raw/
git diff --cached --quiet && echo "Nothing to commit" || \
  git commit -m "chore: weekly Firecrawl scrape $(date -u +%Y-%m-%d)"
git push
```

- Skips the commit cleanly if no files changed (idempotent).
- Commit message includes UTC date for traceability.
- Bot identity keeps automated commits visually distinct in git log.

---

## Secrets

| Secret | Where set | How used |
|--------|-----------|----------|
| `FIRECRAWL_API_KEY` | GitHub → Settings → Secrets and variables → Actions | Injected as env var into the run pipeline step |

`GITHUB_TOKEN` is provided automatically by Actions — no manual setup.

---

## Failure handling

No special notification. A failed run surfaces as a red check on the repository. GitHub's default behavior emails the repo owner on workflow failure.

---

## Files created / changed

| Path | Change |
|------|--------|
| `.github/workflows/scrape.yml` | New — the workflow definition |

No changes to `scrape_pipeline.py`, `requirements.txt`, or tests.

---

## Full workflow YAML

```yaml
name: Weekly Chipotle Scrape

on:
  schedule:
    - cron: '0 6 * * 1'
  workflow_dispatch:

jobs:
  scrape:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
          cache: 'pip'
          cache-dependency-path: requirements.txt

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run scrape pipeline
        env:
          FIRECRAWL_API_KEY: ${{ secrets.FIRECRAWL_API_KEY }}
        run: python scrape_pipeline.py

      - name: Commit new knowledge files
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add knowledge/raw/
          git diff --cached --quiet && echo "Nothing to commit" || \
            git commit -m "chore: weekly Firecrawl scrape $(date -u +%Y-%m-%d)"
          git push
```
