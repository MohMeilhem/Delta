"""Seed-data access layer. Loads /data JSON once at import time."""

from __future__ import annotations

import json
import os
import threading
from functools import lru_cache
from pathlib import Path

from .models import Company, NewsItem, QuarterFinancials, Sector

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
# Seed data (DATA_DIR) is read-only in production. Runtime writes (subscribers,
# caches) go to a writable dir: /tmp on Vercel, where the bundle FS is read-only
# except /tmp; the seed dir locally otherwise.
WRITABLE_DIR = Path("/tmp") if os.environ.get("VERCEL") else DATA_DIR
SUBSCRIBERS_PATH = WRITABLE_DIR / "subscribers.json"


@lru_cache(maxsize=1)
def _companies_raw() -> dict:
    return json.loads((DATA_DIR / "companies.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _financials_raw() -> dict:
    return json.loads((DATA_DIR / "financials.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _news_raw() -> dict:
    return json.loads((DATA_DIR / "news.json").read_text(encoding="utf-8"))


def sectors() -> list[Sector]:
    return [Sector(**s) for s in _companies_raw()["sectors"]]


def companies() -> list[Company]:
    return [Company(**c) for c in _companies_raw()["companies"]]


def companies_by_sector(sector_id: str) -> list[Company]:
    return [c for c in companies() if c.sector == sector_id]


def company(ticker: str) -> Company | None:
    return next((c for c in companies() if c.ticker == ticker), None)


def financials(ticker: str) -> list[QuarterFinancials] | None:
    rows = _financials_raw().get(ticker)
    if rows is None:
        return None
    return [QuarterFinancials(**r) for r in rows]


def news(ticker: str) -> list[NewsItem] | None:
    items = _news_raw().get(ticker)
    if items is None:
        return None
    return [NewsItem(**i) for i in items]


@lru_cache(maxsize=1)
def _macro_raw() -> dict:
    return json.loads((DATA_DIR / "macro.json").read_text(encoding="utf-8"))


def macro() -> dict:
    """Saudi macro series (Brent, SAMA repo) aligned to the seed quarters."""
    raw = _macro_raw()
    return {"series": raw["series"], "context_en": raw.get("context_en", [])}


# /subscribe runs on FastAPI's threadpool: serialize read-append-write and
# write atomically (temp file + replace) so concurrent submits can't lose an
# entry or leave a half-written file behind for the next read to choke on.
_subscribers_lock = threading.Lock()


def subscribers() -> list[dict]:
    with _subscribers_lock:
        return _read_subscribers()


def _read_subscribers() -> list[dict]:
    if not SUBSCRIBERS_PATH.exists():
        return []
    return json.loads(SUBSCRIBERS_PATH.read_text(encoding="utf-8"))


def append_subscriber(entry: dict) -> None:
    with _subscribers_lock:
        rows = _read_subscribers()
        rows.append(entry)
        try:
            tmp = SUBSCRIBERS_PATH.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, SUBSCRIBERS_PATH)
        except OSError:
            pass  # read-only fs: never 500 the signup form over a persistence miss
