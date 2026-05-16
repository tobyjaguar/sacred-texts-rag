"""HTML → plain text for the sacred-texts.com mirror.

Walks SACRED_SRC, converts each tradition page into a plain `.txt` file under
SACRED_OUT/txt/ mirroring the source tree, and appends one record per file to
SACRED_OUT/manifest.jsonl. See SPEC.md for the contract.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from bs4 import BeautifulSoup

DEFAULT_SRC = Path(os.environ.get("SACRED_SRC", "/Volumes/Extreme Pro/Sacred-Texts"))
DEFAULT_OUT = Path(
    os.environ.get("SACRED_OUT", "/Volumes/Extreme Pro/sacred-texts-rag-data")
) / "txt"

SKIP_NAMES = {"index.htm", "index.html"}
SKIP_DIR_PARTS = {"journals", "img", "imgs", "images"}

_HR_RE = re.compile(r"<hr\b[^>]*/?>", re.IGNORECASE)
_BLOCK_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6", "p")
_WS_RE = re.compile(r"\s+")


@dataclass
class Converted:
    title: str
    body: str


def convert_html(html: str) -> Converted:
    """Convert one sacred-texts HTML page into title + plain-text body.

    Strips the nav blocks fenced by `<HR>` tags at the top and bottom of the
    body, then joins block-level text with blank lines.
    """
    soup = BeautifulSoup(html, "lxml")
    title_tag = soup.find("title")
    title = _collapse_ws(title_tag.get_text(" ", strip=True)) if title_tag else ""

    body = soup.body
    if body is None:
        return Converted(title=title, body="")

    inner_html = body.decode_contents()
    parts = _HR_RE.split(inner_html)
    if len(parts) >= 3:
        kept_html = "<hr/>".join(parts[1:-1])
    elif len(parts) == 2:
        kept_html = parts[1]
    else:
        kept_html = parts[0]

    inner = BeautifulSoup(kept_html, "lxml")
    blocks: list[str] = []
    for el in inner.find_all(_BLOCK_TAGS):
        text = _collapse_ws(el.get_text(" ", strip=True))
        if text:
            blocks.append(text)

    if not blocks:
        fallback = _collapse_ws(inner.get_text(" ", strip=True))
        if fallback:
            blocks.append(fallback)

    return Converted(title=title, body="\n\n".join(blocks))


def _collapse_ws(s: str) -> str:
    return _WS_RE.sub(" ", s.replace("\xa0", " ")).strip()


def should_skip(path: Path, src_root: Path) -> bool:
    if path.name.lower() in SKIP_NAMES:
        return True
    rel = path.relative_to(src_root)
    parent_parts = rel.parts[:-1]
    if not parent_parts:
        return True
    if any(part.lower() in SKIP_DIR_PARTS for part in parent_parts):
        return True
    return False


def iter_html(src_root: Path) -> Iterator[Path]:
    for pattern in ("*.htm", "*.html"):
        for path in src_root.rglob(pattern):
            if path.is_file() and not should_skip(path, src_root):
                yield path


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--src", type=Path, default=DEFAULT_SRC, help="HTML mirror root")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output .txt root")
    p.add_argument("--limit", type=int, default=None, help="Stop after N files (smoke test)")
    args = p.parse_args()

    if not args.src.exists():
        raise SystemExit(f"Source not found: {args.src}")

    args.out.mkdir(parents=True, exist_ok=True)
    manifest_path = args.out.parent / "manifest.jsonl"

    n = 0
    with manifest_path.open("w", encoding="utf-8") as manifest:
        for src_path in iter_html(args.src):
            if args.limit is not None and n >= args.limit:
                break

            try:
                raw = src_path.read_bytes()
            except OSError as e:
                print(f"skip {src_path}: {e}", file=sys.stderr)
                continue
            html = raw.decode("utf-8", errors="replace")

            converted = convert_html(html)
            if not converted.body:
                continue

            rel = src_path.relative_to(args.src)
            out_path = args.out / rel.with_suffix(".txt")
            out_path.parent.mkdir(parents=True, exist_ok=True)

            header = f"# {converted.title}\n\n" if converted.title else ""
            out_path.write_text(f"{header}{converted.body}\n", encoding="utf-8")

            manifest.write(
                json.dumps(
                    {
                        "source": rel.as_posix(),
                        "output": out_path.relative_to(args.out.parent).as_posix(),
                        "title": converted.title,
                        "bytes": out_path.stat().st_size,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            n += 1

    print(f"converted {n} files → {args.out}")


if __name__ == "__main__":
    main()
