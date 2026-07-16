"""Smoke tests for the live-news layer (Bing News RSS + daily cache).

No network: _fetch is monkeypatched; parsing is tested against canned RSS.
"""

import time

import pytest

from app import data, live_news
from app.models import NewsItem

RAJHI = data.company("1120")

CANNED_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:News="https://www.bing.com:443/news/search?q=x&amp;format=rss">
<channel>
  <item>
    <title>مصرف الراجحي يعلن نتائج الربع الثاني</title>
    <link>http://www.bing.com/news/apiclick.aspx?ref=FexRss&amp;url=https%3A%2F%2Falarabiya.net%2Fa&amp;cc=sa</link>
    <pubDate>Tue, 14 Jul 2026 13:42:00 GMT</pubDate>
    <description>&lt;b&gt;أظهرت&lt;/b&gt; نتائج المصرف نمواً في صافي الدخل خلال الربع الثاني</description>
    <News:Source>العربية</News:Source>
  </item>
  <item>
    <title>مصرف الراجحي يعلن نتائج الربع الثاني</title>
    <link>http://www.bing.com/news/apiclick.aspx?ref=FexRss&amp;url=https%3A%2F%2Fdup.example%2Fx</link>
    <pubDate>Tue, 14 Jul 2026 13:42:00 GMT</pubDate>
    <description>نسخة مكررة</description>
    <News:Source>العربية</News:Source>
  </item>
  <item>
    <title>خبر أقدم عن المصرف</title>
    <link>http://www.bing.com/news/apiclick.aspx?ref=FexRss&amp;url=https%3A%2F%2Fmaaal.com%2Fb</link>
    <pubDate>Thu, 09 Jul 2026 12:48:45 GMT</pubDate>
    <description>نص الخبر الأقدم</description>
    <News:Source>مال</News:Source>
  </item>
  <item>
    <title>صفحة قديمة جداً عن الشركة</title>
    <link>http://www.bing.com/news/apiclick.aspx?ref=FexRss&amp;url=https%3A%2F%2Fold.example%2Fc</link>
    <pubDate>Thu, 17 Nov 2016 17:19:00 GMT</pubDate>
    <description>صفحة تعريفية قديمة</description>
    <News:Source>قديم</News:Source>
  </item>
</channel></rss>"""


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path, monkeypatch):
    """Each test gets an empty on-disk cache and live mode enabled."""
    monkeypatch.delenv("DELTA_OFFLINE", raising=False)
    monkeypatch.setattr(live_news, "CACHE_PATH", tmp_path / "news_cache.json")
    monkeypatch.setattr(live_news, "_cache", None)
    monkeypatch.setattr(live_news, "_backoff", {})


def test_parse_rss_maps_and_dedupes():
    items = live_news._parse_rss(CANNED_RSS)
    assert len(items) == 2  # duplicate headline + >1y-old page dropped
    first = items[0]
    assert first.headline == "مصرف الراجحي يعلن نتائج الربع الثاني"
    assert first.date == "2026-07-14"
    assert first.source == "العربية"
    assert first.url == "https://alarabiya.net/a"  # extracted from ?url=
    assert first.body == "أظهرت نتائج المصرف نمواً في صافي الدخل خلال الربع الثاني"  # HTML stripped
    assert items[0].date > items[1].date  # newest first


def test_company_news_caches_to_disk(monkeypatch):
    calls = []
    fake = [NewsItem(headline="h", date="2026-07-15", body="", source="s")]
    monkeypatch.setattr(live_news, "_fetch", lambda c: calls.append(1) or fake)

    assert live_news.company_news(RAJHI) == fake
    assert live_news.company_news(RAJHI) == fake  # second call: cache hit
    assert len(calls) == 1
    assert live_news.CACHE_PATH.exists()


def test_expired_cache_triggers_daily_refetch(monkeypatch):
    """The core daily-update guarantee: entries older than 24h are refetched."""
    day1 = [NewsItem(headline="yesterday", date="2026-07-15", body="", source="s")]
    day2 = [NewsItem(headline="today", date="2026-07-16", body="", source="s")]
    monkeypatch.setattr(live_news, "_fetch", lambda c: day1)
    assert live_news.company_news(RAJHI) == day1

    # simulate 25 hours passing, with fresher news now available upstream
    live_news._cache[RAJHI.ticker]["fetched_at"] = time.time() - 25 * 3600
    monkeypatch.setattr(live_news, "_fetch", lambda c: day2)
    assert live_news.company_news(RAJHI) == day2  # refetched, not stale-served
    # and the new snapshot is cached fresh again
    assert time.time() - live_news._cache[RAJHI.ticker]["fetched_at"] < 60


def test_stale_cache_served_when_fetch_fails(monkeypatch):
    fake = [NewsItem(headline="old", date="2026-06-01", body="", source="s")]
    monkeypatch.setattr(live_news, "_fetch", lambda c: fake)
    live_news.company_news(RAJHI)

    # expire the entry, then make the network fail
    live_news._cache[RAJHI.ticker]["fetched_at"] = time.time() - 2 * live_news.CACHE_TTL_S
    monkeypatch.setattr(live_news, "_fetch", lambda c: None)
    assert live_news.company_news(RAJHI) == fake  # stale beats nothing


def test_no_cache_and_fetch_fails_returns_none(monkeypatch):
    monkeypatch.setattr(live_news, "_fetch", lambda c: None)
    assert live_news.company_news(RAJHI) is None


def test_endpoint_falls_back_to_seed_news(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app

    monkeypatch.setattr(live_news, "_fetch", lambda c: None)
    r = TestClient(app).get("/companies/1120/news")
    assert r.status_code == 200
    assert len(r.json()) >= 4  # seed items served
    assert all("headline" in i for i in r.json())


def test_offline_env_skips_live(monkeypatch):
    monkeypatch.setenv("DELTA_OFFLINE", "1")
    monkeypatch.setattr(live_news, "_fetch",
                        lambda c: pytest.fail("must not fetch when DELTA_OFFLINE"))
    assert live_news.company_news(RAJHI) is None
