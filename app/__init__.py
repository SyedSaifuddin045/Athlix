"""Athelix FastAPI application package.

Keep this module lightweight to avoid importing the application during
package import time. Import the ASGI app directly from
``app.main:app`` or via ``from app.main import app`` when needed.
"""

__all__ = []
