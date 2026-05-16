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
├── txt/                   # mirrored .txt tree (one per converted .htm)
├── manifest.jsonl         # one line per converted source file
├── chunks.jsonl           # produced by chunk.py
└── vectors/               # produced by embed.py / index.py
```

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

### Output `.txt` file
```
# {title}

{block 1}

{block 2}

…
```
Path mirrors the source: `bib/kjv/gen001.htm` → `txt/bib/kjv/gen001.txt`.

### `manifest.jsonl` schema
One JSON object per line:

```json
{
  "source": "bib/kjv/gen001.htm",
  "output": "txt/bib/kjv/gen001.txt",
  "title":  "King James Version: Genesis: Genesis Chapter 1",
  "bytes":  4321
}
```

`source` and `output` are POSIX-style paths relative to `SACRED_SRC` and
`SACRED_OUT`, respectively.

### CLI
```
python -m src.convert --src "$SACRED_SRC" --out "$SACRED_OUT/txt" [--limit N]
```

`--limit N` stops after N successful conversions (smoke testing).

## 2. Stage 2 — `src/chunk.py` (not yet implemented)

Reads `SACRED_OUT/txt/**/*.txt` plus `manifest.jsonl`, emits `chunks.jsonl`.
Each chunk carries: chunk id, source path, title, tradition (top-level dir),
text, char offsets, token count (approximate).

Chunk size, overlap, and tokenizer are TBD; record decisions here once made.

## 3. Stage 3 — `src/embed.py` (not yet implemented)

Reads `chunks.jsonl`, batch-embeds, writes vectors to `SACRED_OUT/vectors/`.
Embedding model is TBD (sentence-transformers / OpenAI / Anthropic — picked
at implementation time, see `pyproject.toml` `[embed]` extras).

## 4. Stage 4 — `src/index.py` (not yet implemented)

Builds a local vector store from `vectors/` (FAISS / Chroma / LanceDB — TBD).
Exposes a query CLI: `python -m src.index --query "..." --k 5`.
