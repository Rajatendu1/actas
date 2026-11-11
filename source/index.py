"""Vercel entrypoint: zero-config FastAPI detection looks for `app` here.

Without ACTAS_DATA_DIR the server runs in memory (state resets with the
function instance), which is what the stateless public lab needs.
"""
from actas.app import app  # noqa: F401
