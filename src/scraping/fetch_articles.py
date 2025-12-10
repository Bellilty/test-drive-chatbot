from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Iterable

import requests
from bs4 import BeautifulSoup

# Ensure project root on path when run as a script
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import RAW_DIR  # noqa: E402
from src.urls import ARTICLE_URLS  # noqa: E402


def sanitize_filename(url: str) -> str:
    slug = url.rstrip("/").split("/")[-1]
    slug = re.sub(r"[^a-zA-Z0-9_-]", "-", slug)
    return slug or "article"


def fetch_html(url: str, timeout: int = 20) -> str:
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding
    return resp.text


def extract_content(html: str) -> tuple[str, list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    # Remove non-content elements
    for tag in soup(["script", "style", "header", "footer", "nav", "aside"]):
        tag.decompose()

    title_el = soup.find("h1") or soup.find("title")
    title = title_el.get_text(strip=True) if title_el else "ללא כותרת"

    paragraphs: list[str] = []
    for p in soup.find_all("p"):
        text = p.get_text(separator=" ", strip=True)
        if text:
            paragraphs.append(text)

    return title, paragraphs


def save_raw(slug: str, url: str, html: str, title: str, paragraphs: Iterable[str]) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / f"{slug}.html").write_text(html, encoding="utf-8")
    payload = {"url": url, "title": title, "paragraphs": list(paragraphs)}
    (RAW_DIR / f"{slug}.txt").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_all(urls: list[str] | None = None) -> None:
    urls = urls or ARTICLE_URLS
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for idx, url in enumerate(urls, start=1):
        slug = sanitize_filename(url)
        print(f"[{idx}/{len(urls)}] Fetching {url}")
        try:
            html = fetch_html(url)
            title, paragraphs = extract_content(html)
            save_raw(slug, url, html, title, paragraphs)
            print(f"Saved {slug} ({len(paragraphs)} paragraphs)")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            print(f"Failed {url}: {exc}")


if __name__ == "__main__":
    fetch_all()

