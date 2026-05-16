# MEMORY — sacred-texts-rag

Project-local notes. Decisions, gotchas, and context that aren't obvious from
the code. Keep entries short; link to PR / commit when relevant.

## Decisions

- **Output dir**: `/Volumes/Extreme Pro/sacred-texts-rag-data/` (external SSD,
  same drive as the source mirror). Derived data is large (~3 GB) and external
  to the repo. Override with `SACRED_OUT`.
- **HTML parser**: `lxml` via BeautifulSoup. The mirror is uniform HTML4 with
  uppercase tags and unclosed `<P>`; `html.parser` is too forgiving in
  inconsistent ways, `lxml` normalizes reliably.
- **Nav-stripping heuristic**: split body on `<hr>` markers and keep the
  middle. Works because every text page is fenced by HR tags; index/about
  pages that don't follow the pattern are skipped by path rules.

## Gotchas

- Some pages have `<P><HR>` (HR nested inside P) at the bottom. The
  string-split-on-HR approach handles this; a strict "previous sibling of last
  HR" walk would not.
- `&nbsp;` survives `get_text()` as ` `. We normalize all whitespace runs
  to single spaces before emitting.
- Source paths contain spaces (`/Volumes/Extreme Pro/...`). Quote in shell.
- Python 3.14 is in use locally; `pyproject.toml` requires 3.11+.

## TODO / followups

- Decide chunk size + overlap for `chunk.py`.
- Decide embedding model and vector store.
- Add a skip-detection unit test once we have a fixture for a journals/ page.
