"""Package init: load backend/.env into the environment before any module
reads ANTHROPIC_API_KEY. Real environment variables win over .env values;
tests set DELTA_NO_ENV_FILE=1 so the suite never picks up a live key."""

import os
from pathlib import Path


def _load_env_file() -> None:
    if os.environ.get("DELTA_NO_ENV_FILE"):
        return
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    # utf-8-sig: tolerate the BOM Windows Notepad adds
    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


_load_env_file()
