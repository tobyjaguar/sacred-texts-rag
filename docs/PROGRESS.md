# Progress

Quick status of where the project is and what's next. Update as stages move.

## Status: corpus ready, paused before chunking

The HTML mirror has been fully converted into a clean, deduplicated text
corpus on the external SSD. The pipeline is paused here intentionally —
chunking choices are coupled to the embedding model, so the next stage
waits until the research machine and model are picked.

```
HTML mirror  ──convert──▶  corpus.jsonl  ──chunk──▶  chunks.jsonl  ──embed──▶  vectors  ──index──▶  query
   140k .htm     [DONE]      138,215 docs    [TODO]                  [TODO]                [TODO]
   1.8 GB                    1.18 GB                                 (needs GPU /
                                                                      API budget)
```

## Done

### Stage 1 — `convert.py` (HTML → corpus.jsonl)
- Walks `$SACRED_SRC` (`/Volumes/Extreme Pro/Sacred-Texts`).
- Strips sacred-texts.com nav blocks (the `<HR>`-fenced top/bottom of each
  page); extracts `<TITLE>`; preserves verse numbers and paragraph breaks.
- Skips `index.htm`, image dirs, `journals/`, and root-level non-tradition
  files.
- Parallelized across CPU cores with a tqdm progress bar.
- Emits a single `$SACRED_OUT/corpus.jsonl` (one record per document:
  `{source, title, body, bytes}`, sorted by source).

**Run output (last full run):**
| | |
|---|---|
| Source files found | 138,817 |
| Successfully converted | 138,215 |
| Empty after stripping | 602 |
| Errors | 0 |
| Body text written | 1.18 GB |
| Walltime | 2:35 (12 workers) |

### Infrastructure
- Repo on GitHub: `git@github.com:tobyjaguar/sacred-texts-rag.git`
- `.venv/` set up at repo root (Python 3.14, bs4 + lxml + tqdm + pytest)
- 3 fixture-driven tests in `tests/test_convert.py`, all green
- `SPEC.md` documents the pipeline contract
- `MEMORY.md` and `CLAUDE.md` capture decisions and Claude session bootstrap

## Key decisions

- **Output format: single JSONL, not a mirrored `.txt` tree.** The SSD is
  exFAT (cross-OS portable) with 1 MB cluster size; 138k tiny files would
  allocate ~135 GB for ~1 GB of text. JSONL is also the natural input shape
  for `chunk.py`. See [MEMORY.md](../MEMORY.md).
- **No re-chunking now.** Chunk size and tokenization depend on the
  embedding model. Premature to commit to numbers without the target model.

## Next steps (when research machine is ready)

### 1. Pick the embedding model
This decision drives everything downstream:

| Model family | Pros | Cons |
|---|---|---|
| `sentence-transformers` (local, e.g. `all-MiniLM-L6-v2`, `bge-large`) | Free, runs on GPU, no API budget | Need GPU; quality below frontier |
| OpenAI `text-embedding-3-large` (1536 or 3072 dim) | Strong quality, simple | API cost (~$0.13/M tokens → ~$40 for full corpus); offline-incompatible |
| Voyage AI / Cohere / others | Various tradeoffs | Each has its own SDK / pricing |

The choice fixes: tokenizer (for chunk sizing), vector dimension (for the
index), and per-chunk embedding cost.

### 2. Implement `chunk.py`
Stream `corpus.jsonl`, split each `body` into overlapping chunks. Suggested
starting params (tune after the model is picked):

- Target ~500–1000 tokens per chunk
- ~10–20% overlap
- Tokenize with the chosen model's tokenizer (so chunk boundaries are
  predictable for the embedder)

Output: `$SACRED_OUT/chunks.jsonl`, one record per chunk with
`{chunk_id, source, title, tradition, text, char_start, char_end, token_count}`.
Tradition = top-level dir of `source` (e.g. `bib`, `bud`, `hin`).

### 3. Implement `embed.py`
Batch-embed every chunk. Resumable (track processed `chunk_id`s) so a
crash doesn't waste compute. Output: `$SACRED_OUT/vectors/` (format
depends on the index — FAISS `.faiss`, Chroma `parquet`, LanceDB
`.lance`).

### 4. Implement `index.py`
Build the vector store, expose a query CLI:
```bash
python -m src.index --query "what does Genesis say about light?" --k 5
```

### 5. Cost / size estimate (rough, model-dependent)
For ~180M source tokens at 1536-dim float32:
- Embedding cost (OpenAI 3-large): ~$23 for 180M tokens
- Vector storage: ~1.3 GB (raw) or ~600 MB (quantized)

## Tasks not blocking the next stage

These are quality-of-life items that can be done any time:

- [ ] Tiny normalization pass: trailing-space-before-period artifacts left
  by cross-reference links (e.g. `"the deep ."`).
- [ ] Add `extract.py` helper: pull a single document out of `corpus.jsonl`
  by source path (5 lines of code, only matters once you actually need it).
- [ ] Decide whether to back up `corpus.jsonl` to S3 / iCloud — single
  1.18 GB file uploads fine; reproducible from source in ~3 min if lost.

## How to resume

```bash
cd ~/dev/sacred-texts-rag
source .venv/bin/activate     # or: .venv/bin/python …
# corpus is at $SACRED_OUT/corpus.jsonl already; no need to re-run convert.py.

# When ready:
# 1. Pin embedding model
# 2. Add it to pyproject.toml [embed] extra
# 3. Implement chunk.py against corpus.jsonl
```
