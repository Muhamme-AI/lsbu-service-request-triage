"""Rebuild the guidance index and report what is in it: ``python -m triage.rag``."""

from __future__ import annotations

import sys

from .pipeline import build_index, index_stats, source_files, writable_db_path


def main() -> int:
    path = writable_db_path()
    count = build_index(path, source_files())
    stats = index_stats(path)
    print(f"Indexed {count} chunks from {len(source_files())} files into {path}")
    for source, chunks in stats["sources"].items():
        print(f"  {source}: {chunks} chunk{'s' if chunks != 1 else ''}")
    print(f"Vocabulary: {stats['vocabulary']} terms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
