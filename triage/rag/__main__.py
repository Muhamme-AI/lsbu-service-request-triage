"""Rebuild the guidance index: ``python -m triage.rag``."""

from __future__ import annotations

import sys

from .pipeline import build_index, ensure_index, source_files


def main() -> int:
    path = ensure_index()
    count = build_index(path, source_files())
    print(f"Indexed {count} chunks from {len(source_files())} files into {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
