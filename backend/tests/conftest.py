"""Test-suite defaults: force offline mode so no test ever hits the network.

Individual tests that exercise the live layers monkeypatch the fetchers
directly (and remove DELTA_OFFLINE) instead of making real requests.
"""

import os

import pytest

os.environ.setdefault("DELTA_OFFLINE", "1")


@pytest.fixture(autouse=True)
def _isolated_summary_cache(tmp_path, monkeypatch):
    """Point the LLM summary cache at a temp file so tests never read or
    write the real data/summary_cache.json."""
    from app import llm

    monkeypatch.setattr(llm, "SUMMARY_CACHE_PATH", tmp_path / "summary_cache.json")
    monkeypatch.setattr(llm, "_summary_cache", None)
# Never load backend/.env in tests — a real ANTHROPIC_API_KEY there would
# make LLM tests hit the live API (and bill the account).
os.environ.setdefault("DELTA_NO_ENV_FILE", "1")
