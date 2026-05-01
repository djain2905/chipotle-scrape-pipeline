# GitHub Actions Scrape Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a GitHub Actions workflow that runs `scrape_pipeline.py` every Monday at 06:00 UTC and auto-commits any new `knowledge/raw/` files back to `main`.

**Architecture:** A single workflow file (`.github/workflows/scrape.yml`) with one job: checkout → setup Python → install deps → run pipeline → commit & push. The `FIRECRAWL_API_KEY` is injected from a GitHub Actions repository secret. The built-in `GITHUB_TOKEN` handles push permissions.

**Tech Stack:** GitHub Actions, `actions/checkout@v4`, `actions/setup-python@v5`, Python 3.13, pip, native git CLI.

---

### Task 1: Create the workflow file

**Files:**
- Create: `.github/workflows/scrape.yml`

- [ ] **Step 1: Create the `.github/workflows/` directory**

```bash
mkdir -p .github/workflows
```

- [ ] **Step 2: Write the workflow file**

Create `.github/workflows/scrape.yml` with the following content:

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

- [ ] **Step 3: Commit and push**

```bash
git add .github/workflows/scrape.yml
git commit -m "feat: add weekly GitHub Actions scrape workflow"
git push
```

Expected output: push succeeds, commit appears on `main`.

---

### Task 2: Add the Firecrawl API secret to GitHub

This is a manual one-time step in the GitHub UI — it cannot be scripted.

- [ ] **Step 1: Open the repository secret settings**

Navigate to:
```
https://github.com/<your-username>/chipotle-scrape-pipeline/settings/secrets/actions
```

- [ ] **Step 2: Create the secret**

Click **New repository secret** and fill in:

| Field | Value |
|-------|-------|
| Name  | `FIRECRAWL_API_KEY` |
| Secret | *(your Firecrawl API key from your local `.env` file)* |

Click **Add secret**.

---

### Task 3: Verify the workflow and trigger a manual test run

- [ ] **Step 1: Confirm the workflow appears in GitHub Actions**

Navigate to:
```
https://github.com/<your-username>/chipotle-scrape-pipeline/actions
```

You should see **"Weekly Chipotle Scrape"** listed under All workflows.

- [ ] **Step 2: Trigger a manual run**

Click **"Weekly Chipotle Scrape"** → **"Run workflow"** → **"Run workflow"** (green button).

- [ ] **Step 3: Watch the run complete**

Click into the running job. All five steps should go green:
1. Checkout
2. Set up Python
3. Install dependencies
4. Run scrape pipeline
5. Commit new knowledge files

If step 4 fails with `Error: FIRECRAWL_API_KEY not set` or a 401, confirm the secret name matches exactly (case-sensitive).

If step 5 shows "Nothing to commit", that is correct — it means the scrape returned results identical to existing files.

- [ ] **Step 4: Confirm files or no-op message in step 5 logs**

In the "Commit new knowledge files" step output you should see either:
- `Nothing to commit` — pipeline ran clean, no new content
- A git commit hash and `main -> main` push confirmation — new files were written
