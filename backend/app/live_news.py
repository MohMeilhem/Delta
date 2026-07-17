"""Live news layer: real Arabic articles via Bing News RSS, refreshed daily.

Follows the same philosophy as live.py (quotes): a best-effort enrichment on
top of the offline seed dataset. Each company's news is fetched from Bing News
(ar-SA market) by searching its Arabic name, cached to /data/news_cache.json
with a 24-hour TTL, and served from that cache between refreshes.

Bing was chosen over Google News RSS because its feed carries what the UI
needs directly: the article's opening text in <description> (the item body),
the real publisher URL inside the link's url= param (Google's links are
JS-only redirects that can't be resolved server-side), and the outlet name
in <News:Source>. Failure modes degrade gracefully:

  fresh cache -> serve it
  stale cache + fetch OK -> refresh and serve
  stale cache + fetch fails -> serve stale (better old real news than none)
  no cache + fetch fails -> return None, caller falls back to seed news.json
"""

from __future__ import annotations

import html
import json
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qs, unquote, urlparse
from xml.etree import ElementTree

import httpx

from .data import WRITABLE_DIR
from .models import Company, NewsItem

RSS_URL = "https://www.bing.com/news/search"
TIMEOUT_S = 8.0
CACHE_TTL_S = 24 * 60 * 60  # "every day it looks for the latest update"
MAX_ITEMS = 8
MAX_AGE_DAYS = 365  # Bing occasionally surfaces ancient evergreen pages
BODY_MAX_CHARS = 600
CACHE_PATH = WRITABLE_DIR / "news_cache.json"

_lock = threading.Lock()
_cache: dict[str, dict] | None = None  # {ticker: {fetched_at, items}}
# tickers whose last fetch failed recently; avoid hammering while offline
_backoff: dict[str, float] = {}
BACKOFF_S = 600


def _load_cache() -> dict[str, dict]:
    global _cache
    if _cache is None:
        try:
            _cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _cache = {}
    return _cache


def _save_cache() -> None:
    try:
        CACHE_PATH.write_text(
            json.dumps(_cache, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass  # read-only fs etc. — in-process cache still works


def _clean_text(raw: str) -> str:
    """Strip HTML tags/entities and collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _direct_url(link: str) -> str | None:
    """Bing links are apiclick.aspx redirects; the publisher URL is in ?url=."""
    if not link:
        return None
    target = parse_qs(urlparse(link).query).get("url", [None])[0]
    return unquote(target) if target else link


def _parse_rss(xml_text: str) -> list[NewsItem]:
    """Map Bing News RSS <item>s onto the NewsItem schema."""
    root = ElementTree.fromstring(xml_text)
    oldest = (datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)).date()
    items: list[NewsItem] = []
    seen: set[str] = set()
    for el in root.iter("item"):
        title = _clean_text(el.findtext("title") or "")
        if not title or title in seen:
            continue
        seen.add(title)
        try:
            dt = parsedate_to_datetime(el.findtext("pubDate") or "")
            date = dt.date()
        except (TypeError, ValueError):
            date = datetime.now(timezone.utc).date()
        if date < oldest:
            continue  # evergreen page, not news
        # <News:Source> is namespaced; match by suffix to stay prefix-agnostic
        source = next(
            (c.text.strip() for c in el if c.tag.endswith("Source") and c.text),
            "Bing News",
        )
        body = _clean_text(el.findtext("description") or "")[:BODY_MAX_CHARS]
        items.append(NewsItem(
            headline=title,
            date=date.isoformat(),
            body=body,
            source=source,
            url=_direct_url((el.findtext("link") or "").strip()),
        ))
    items.sort(key=lambda i: i.date, reverse=True)
    return items[:MAX_ITEMS]


def _normalize_ar(s: str) -> str:
    """Fold hamza variants so 'الإنماء' and 'الانماء' compare equal."""
    return re.sub("[أإآ]", "ا", s)


def _relevant(company: Company, items: list[NewsItem]) -> list[NewsItem]:
    """Bing's quoted-phrase matching is loose in the RSS endpoint — e.g.
    'مصرف الإنماء' surfaces Lebanon's 'مجلس الإنماء والإعمار'. Require the
    company's full Arabic name to actually appear in the item text."""
    n = _normalize_ar(company.name_ar)
    return [i for i in items if n in _normalize_ar(f"{i.headline} {i.body}")]


def _fetch(company: Company) -> list[NewsItem] | None:
    # Query ladder: exact-phrase name first (most on-topic); if everything it
    # finds is stale (>1y, filtered by _parse_rss) or off-entity (filtered by
    # _relevant), retry with stock-market phrasings that surface recent
    # coverage for less-newsworthy tickers.
    n = company.name_ar
    queries = [f'"{n}"', f'"سهم {n}"', f'"{n}" أرباح']
    try:
        with httpx.Client(timeout=TIMEOUT_S,
                          headers={"User-Agent": "Mozilla/5.0"},
                          follow_redirects=True) as client:
            for i, query in enumerate(queries):
                if i:  # pace ladder retries; bursts trip Bing's rate limiting
                    time.sleep(1.0)
                r = client.get(RSS_URL, params={
                    "q": query, "format": "rss", "setmkt": "ar-SA"})
                r.raise_for_status()
                items = _relevant(company, _parse_rss(r.text))
                if items:
                    return items
        return None
    except (httpx.HTTPError, ElementTree.ParseError):
        return None


def company_news(company: Company) -> list[NewsItem] | None:
    """Live news for one company, or None when nothing real is available."""
    if os.environ.get("DELTA_OFFLINE"):  # forced-offline mode: seed news only
        return None
    now = time.time()
    with _lock:
        cache = _load_cache()
        entry = cache.get(company.ticker)
        if entry and now - entry["fetched_at"] < CACHE_TTL_S:
            return [NewsItem(**i) for i in entry["items"]]
        if _backoff.get(company.ticker, 0) > now:
            entry = cache.get(company.ticker)
            return [NewsItem(**i) for i in entry["items"]] if entry else None

    items = _fetch(company)  # network call outside the lock

    with _lock:
        cache = _load_cache()
        if items:
            _backoff.pop(company.ticker, None)
            cache[company.ticker] = {
                "fetched_at": now,
                "items": [i.model_dump() for i in items],
            }
            _save_cache()
            return items
        _backoff[company.ticker] = now + BACKOFF_S
        entry = cache.get(company.ticker)  # serve stale over nothing
        return [NewsItem(**i) for i in entry["items"]] if entry else None


def cache_status() -> dict:
    """Freshness snapshot for /health: proves the daily refresh is working."""
    with _lock:
        cache = _load_cache()
        if not cache:
            return {"tickers_live": 0, "oldest_fetch": None, "newest_fetch": None}
        stamps = [e["fetched_at"] for e in cache.values()]
        iso = lambda ts: datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds")
        return {
            "tickers_live": len(cache),
            "oldest_fetch": iso(min(stamps)),
            "newest_fetch": iso(max(stamps)),
        }


def refresh_all(companies: list[Company], spacing_s: float = 3.0) -> int:
    """Warm the cache for every company (used by the daily background task).

    Returns how many tickers ended up with live news. Politely spaced so we
    don't burst 33 requests at Google in one instant.
    """
    ok = 0
    for c in companies:
        if company_news(c):
            ok += 1
        time.sleep(spacing_s)
    return ok
