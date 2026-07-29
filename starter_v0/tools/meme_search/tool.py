from __future__ import annotations

import os
from typing import Any

import requests

from tools._shared import TIMEOUT, err


def meme_search(query: str = "", limit: int = 3, rating: str = "g") -> dict[str, Any]:
    try:
        key = os.getenv("GIPHY_API_KEY")
        if not key:
            raise RuntimeError("Missing GIPHY_API_KEY env var")
        rating = rating if rating in {"g", "pg", "pg-13"} else "g"
        limit = max(1, min(int(limit or 3), 10))
        response = requests.get(
            "https://api.giphy.com/v1/gifs/search",
            params={"api_key": key, "q": query, "limit": limit, "rating": rating},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        items = [{
            "title": item.get("title"),
            "url": item.get("url"),
            "gif_url": (item.get("images", {}).get("original", {}) or {}).get("url"),
            "preview_url": (item.get("images", {}).get("fixed_height", {}) or {}).get("url"),
            "source": "giphy.com",
        } for item in data.get("data", [])]
        return {"tool": "meme_search", "query": query, "rating": rating, "items": items}
    except Exception as exc:
        return err("meme_search", exc)
