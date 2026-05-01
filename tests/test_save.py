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
        monkeypatch.syspath_prepend(str(Path(__file__).parent.parent))
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
    assert re.search(r"scraped_at:\s*\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", content)
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
