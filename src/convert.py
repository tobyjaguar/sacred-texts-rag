"""HTML → plain text for the sacred-texts.com mirror.

Stub. The next Claude Code session will fill this in.

Plan:
  - Walk SACRED_SRC recursively, find every .htm/.html file.
  - Skip index.htm, image dirs, journals/, anything matching SKIP_PATTERNS.
  - For each file:
      * Parse with BeautifulSoup (lxml).
      * Strip the nav blocks: everything before the first <HR> and after the last <HR>.
      * Pull <TITLE> for the header line.
      * Preserve <P> breaks as blank lines; keep verse anchors as plain numbers.
      * Write to SACRED_OUT/txt/<mirrored path>.txt.
  - Append one record per file to SACRED_OUT/manifest.jsonl.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

DEFAULT_SRC = Path(os.environ.get("SACRED_SRC", "/Volumes/Extreme Pro/Sacred-Texts"))
DEFAULT_OUT = Path(
    os.environ.get("SACRED_OUT", "/Volumes/Extreme Pro/sacred-texts-rag-data")
) / "txt"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--src", type=Path, default=DEFAULT_SRC, help="HTML mirror root")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output .txt root")
    p.add_argument("--limit", type=int, default=None, help="Stop after N files (smoke test)")
    args = p.parse_args()

    if not args.src.exists():
        raise SystemExit(f"Source not found: {args.src}")

    raise NotImplementedError("convert.py: implement in the next session")


if __name__ == "__main__":
    main()
