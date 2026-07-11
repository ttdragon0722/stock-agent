"""Vercel serverless entry point for the dashboard API.

Vercel's Python runtime serves any ASGI `app` exported from api/*.py;
vercel.json rewrites every request here so FastAPI keeps its own routing.
The whole repo is bundled into the function, so the skill's data layer
(invest-advisor/data/) is available read-only as of the last git push.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "dashboard" / "backend"))

from main import app  # noqa: E402,F401
