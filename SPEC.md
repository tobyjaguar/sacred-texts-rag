# sacred-texts-rag — Pipeline Spec

This is the contract between pipeline stages. CLI flags and on-disk schemas
should match this document; if a stage diverges, update this file first, then
the code.

## 0. Paths

| Var          | Default                                       | Role                |
|--------------|-----------------------------------------------|---------------------|
| `SACRED_SRC` | `/Volumes/Extreme Pro/Sacred-Texts`           | Read-only HTML mirror |
| `SACRED_OUT` | `/Volumes/Extreme Pro/sacred-texts-rag-data`  | Derived data root   |

All stages accept `--src` / `--out` flags that override the env vars.

Output tree under `SACRED_OUT`:

```
sacred-texts-rag-data/
├── corpus.jsonl           # one line per converted document (convert.py)
├── chunks.jsonl           # produced by chunk.py
└── vectors/               # produced by embed.py / index.py
```

The corpus is packed into a single JSONL rather than a mirrored `.txt`
tree because `SACRED_OUT` typically lives on an exFAT-formatted external
drive (cross-platform with Linux). exFAT cluster sizes on large volumes
are commonly 1 MB, which is catastrophic for ~140k mostly-tiny files
(~135 GB allocated for ~1 GB of text). Downstream stages stream JSONL
anyway, so this is the natural shape.

## 1. Stage 1 — `src/convert.py`

### Input
Files under `SACRED_SRC` matching `*.htm` or `*.html`.

### Skip rules
A file is skipped (not converted, no manifest line) when any of:

- Filename is `index.htm` / `index.html` (navigation landing pages).
- Any parent path segment is `journals`, `img`, `imgs`, or `images`.
- File sits at the mirror root (no tradition folder above it, e.g. `about.htm`).
- File is unreadable or has empty body after nav stripping.

### HTML conventions (sacred-texts.com)
The mirror is uniform HTML4:

- Uppercase tags (`<HTML>`, `<BODY>`, `<HR>`, `<P>`, `<A HREF>`).
- Every text page has nav blocks at the top and bottom, fenced by `<HR>` tags.
- Body text sits between the **first** `<HR>` and the **last** `<HR>` in `<BODY>`.
- `<TITLE>` holds useful metadata (work + chapter), e.g. `King James Version: Genesis: Genesis Chapter 1`.
- Verse anchors look like `<A NAME="001">1</A>&nbsp;In the beginning...`. The visible verse number must survive the conversion.

### Conversion algorithm
1. Parse with BeautifulSoup + `lxml`.
2. Read `<TITLE>` into `title` (whitespace-collapsed).
3. Take `<BODY>` inner HTML. Normalize `<HR>` / `<hr/>` / `<hr>` to a single marker.
4. Split on that marker:
   - ≥3 segments → keep everything joined between the first and last marker.
   - 2 segments → keep the second.
   - 1 segment → keep the whole body (no HR fence; rare).
5. Re-parse the kept fragment. Walk block-level elements (`h1`-`h6`, `p`) in document order, extracting text with whitespace collapsed to single spaces. Drop empty blocks.
6. Join blocks with a blank line (`\n\n`).

### Output: `corpus.jsonl`
One JSON object per line, sorted by `source`:

```json
{
  "source": "bib/kjv/gen001.htm",
  "title":  "King James Version: Genesis: Genesis Chapter 1",
  "body":   "King James Version: Genesis Chapter 1\n\n1 In the beginning…",
  "bytes":  4321
}
```

`source` is a POSIX-style path relative to `SACRED_SRC`. `bytes` is the
UTF-8 length of `body`.

### CLI
```
python -m src.convert --src "$SACRED_SRC" --out "$SACRED_OUT" [--limit N] [--workers N]
```

- `--limit N` stops after N input files (smoke testing).
- `--workers N` overrides the worker count (defaults to `os.cpu_count()`).

## 2. Stage 2 — `src/chunk.py` (not yet implemented)

Streams `SACRED_OUT/corpus.jsonl`, emits `chunks.jsonl`. Each chunk
carries: chunk id, source path, title, tradition (top-level dir of
`source`), text, char offsets, token count (approximate).

Chunk size, overlap, and tokenizer are TBD; record decisions here once made.

## 3. Stage 3 — `src/embed.py` (not yet implemented)

Reads `chunks.jsonl`, batch-embeds, writes vectors to `SACRED_OUT/vectors/`.
Embedding model is TBD (sentence-transformers / OpenAI / Anthropic — picked
at implementation time, see `pyproject.toml` `[embed]` extras).

## 4. Stage 4 — `src/index.py` (not yet implemented)

Builds a local vector store from `vectors/` (FAISS / Chroma / LanceDB — TBD).
Exposes a query CLI: `python -m src.index --query "..." --k 5`.
