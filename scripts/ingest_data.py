from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path so `src` imports work when run as a script
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ingestion.build_corpus import main as build_corpus  # type: ignore  # noqa: E402
from src.ingestion.build_index import main as build_index  # type: ignore  # noqa: E402
from src.scraping.fetch_articles import fetch_all  # type: ignore  # noqa: E402


def main() -> None:
    fetch_all()
    build_corpus()
    build_index()


if __name__ == "__main__":
    main()

