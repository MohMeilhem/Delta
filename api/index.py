"""Vercel serverless entrypoint.

Wraps the Delta FastAPI app and mounts it under /api, because Vercel invokes
the function with the original request path (/api/...) while the backend
declares its routes without that prefix (the Vite dev proxy strips it).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from fastapi import FastAPI

from app.main import app as delta_app

app = FastAPI()
app.mount("/api", delta_app)
