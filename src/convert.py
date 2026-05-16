"""HTML → plain text for the sacred-texts.com mirror.

Walks SACRED_SRC, converts each tradition page into a plain `.txt` file under
SACRED_OUT/txt/ mirroring the source tree, and appends one record per file to
SACRED_OUT/manifest.jsonl. See SPEC.md for the contract.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from bs4 import BeautifulSoup
from tqdm import tqdm

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


def _process_file(job: tuple[str, str, str]) -> dict | None:
    """Worker: read one HTML file, write its .txt, return its manifest record.

    Returns None for empty / unreadable files. Returns {"error": ..., "source": ...}
    when conversion raises, so the parent can log without crashing the pool.
    """
    src_str, src_root_str, out_root_str = job
    src_path = Path(src_str)
    src_root = Path(src_root_str)
    out_root = Path(out_root_str)
    rel = src_path.relative_to(src_root)

    try:
        html = src_path.read_bytes().decode("utf-8", errors="replace")
        converted = convert_html(html)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "source": rel.as_posix()}

    if not converted.body:
        return None

    out_path = out_root / rel.with_suffix(".txt")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    header = f"# {converted.title}\n\n" if converted.title else ""
    out_path.write_text(f"{header}{converted.body}\n", encoding="utf-8")

    return {
        "source": rel.as_posix(),
        "output": out_path.relative_to(out_root.parent).as_posix(),
        "title": converted.title,
        "bytes": out_path.stat().st_size,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--src", type=Path, default=DEFAULT_SRC, help="HTML mirror root")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output .txt root")
    p.add_argument("--limit", type=int, default=None, help="Stop after N files (smoke test)")
    p.add_argument(
        "--workers",
        type=int,
        default=os.cpu_count() or 4,
        help="Worker processes (default: CPU count)",
    )
    args = p.parse_args()

    if not args.src.exists():
        raise SystemExit(f"Source not found: {args.src}")

    args.out.mkdir(parents=True, exist_ok=True)
    manifest_path = args.out.parent / "manifest.jsonl"

    print(f"walking {args.src} …", file=sys.stderr)
    src_paths = list(iter_html(args.src))
    if args.limit is not None:
        src_paths = src_paths[: args.limit]
    total = len(src_paths)
    print(f"found {total} files; converting with {args.workers} workers", file=sys.stderr)

    jobs = [(str(p), str(args.src), str(args.out)) for p in src_paths]

    written = 0
    skipped = 0
    errors = 0
    with manifest_path.open("w", encoding="utf-8") as manifest, mp.Pool(args.workers) as pool:
        for record in tqdm(
            pool.imap_unordered(_process_file, jobs, chunksize=32),
            total=total,
            unit="file",
            smoothing=0.1,
        ):
            if record is None:
                skipped += 1
                continue
            if "error" in record:
                errors += 1
                print(f"error {record['source']}: {record['error']}", file=sys.stderr)
                continue
            manifest.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1

    print(
        f"converted {written} files → {args.out} "
        f"(skipped {skipped} empty, {errors} errors)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
