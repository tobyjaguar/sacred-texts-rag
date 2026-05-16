# CLAUDE.md — sacred-texts-rag

@SPEC.md
@MEMORY.md

## Project
Convert a local mirror of sacred-texts.com (~140k HTML files on an external SSD) into a clean text corpus, chunk it, embed it, and build a local vector index for RAG.

## Where things live

| What | Path | Notes |
|---|---|---|
| Code | `~/dev/sacred-texts-rag/` (this repo) | Versioned, public on GitHub |
| Source HTML mirror | `/Volumes/Extreme Pro/Sacred-Texts/` | **Read-only.** Never write here. |
| Derived corpus + vectors | `/Volumes/Extreme Pro/sacred-texts-rag-data/` | Output target. Not in repo. |
| Test fixtures | `tests/fixtures/` | A few committed .htm samples for offline testing |

Override via env vars `SACRED_SRC` and `SACRED_OUT` or CLI flags `--src` / `--out`.

## Pipeline stages

1. `src/convert.py` — HTML → plain `.txt`, mirrors directory tree, emits `manifest.jsonl`
2. `src/chunk.py` — chunks `.txt` with metadata
3. `src/embed.py` — batch embedding
4. `src/index.py` — vector store build / query

## Conventions

- Python 3.11+ (developing on 3.14).
- **Always use the project venv**: `.venv/bin/python`, `.venv/bin/pytest`, `.venv/bin/pip`. Don't fall back to system `python3`.
- Single-package layout under `src/`. Run modules with `.venv/bin/python -m src.convert`.
- Type-annotate public functions; keep internals untyped if it adds noise.
- Tests live under `tests/`, use pytest. Fixtures are real `.htm` samples from the mirror.
- One CLI per stage. Use `argparse`. No global config singleton.
- Do not commit anything from `data/` or any file > ~1 MB. The `.gitignore` enforces this.

## Sacred-texts HTML shape (important for `convert.py`)

The mirror is uniform HTML4:
- Uppercase tags (`<HTML>`, `<BODY>`, `<HR>`, `<P>`, `<A HREF>`).
- Every page has nav blocks wrapped between `<HR>` tags at the top and bottom.
- Body text sits between the *first* `<HR>` and the *last* `<HR>`.
- `<TITLE>` holds useful metadata (work + chapter).
- Verse anchors are `<A NAME="001">` style; preserve verse numbers when present.
- Skip: `index.htm`, image directories, `journals/`, anything not under a tradition folder.

## Don't

- Don't redistribute the converted corpus from this repo (gitignored).
- Don't mock filesystem in conversion tests — use the real fixtures.
- Don't add a database, queue, or service layer. This is a batch ETL + local index.
- Don't introduce abstractions until there are two concrete callers.
