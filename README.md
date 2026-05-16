# sacred-texts-rag

Convert a local mirror of the [sacred-texts.com](https://sacred-texts.com) archive (~140k HTML files, ~1.8 GB) into a clean text corpus, chunk it, embed it, and build a vector index for retrieval-augmented generation (RAG).

**Status:** corpus extracted, paused before chunking — see [docs/PROGRESS.md](docs/PROGRESS.md).

## Pipeline

```
HTML mirror  ──convert──▶  clean .txt  ──chunk──▶  chunks.jsonl  ──embed──▶  vectors  ──index──▶  query
```

1. **`src/convert.py`** — template-aware HTML → plain text. Strips sacred-texts.com nav blocks (between top and bottom `<HR>`), preserves paragraph breaks, mirrors the source directory tree.
2. **`src/chunk.py`** — splits cleaned text into RAG-sized chunks with metadata (tradition, work, chapter, source path).
3. **`src/embed.py`** — batch embedding (model is configurable).
4. **`src/index.py`** — builds a local vector store (FAISS / Chroma / LanceDB — TBD).

## Layout

```
sacred-texts-rag/
├── src/                  # pipeline stages
├── tests/fixtures/       # a handful of sample .htm files (committed)
├── scripts/              # one-shot helpers
└── data/                 # gitignored — see DATA_DIR below
```

## Paths

The source mirror and the output corpus are **not** in the repo. Configure via env vars or CLI flags:

| Var | Default | Purpose |
|---|---|---|
| `SACRED_SRC` | `/Volumes/Extreme Pro/Sacred-Texts` | Read-only HTML mirror |
| `SACRED_OUT` | `/Volumes/Extreme Pro/sacred-texts-rag-data` | Where `.txt`, chunks, and vectors are written |

Output layout under `SACRED_OUT`:

```
sacred-texts-rag-data/
├── corpus.jsonl          # one line per document: source, title, body, bytes
├── chunks.jsonl          # chunked records ready for embedding
└── vectors/              # vector store files
```

The corpus is a single JSONL because `SACRED_OUT` lives on an
exFAT-formatted external drive (1 MB cluster size); a mirrored `.txt`
tree of ~140k tiny files allocates ~135 GB for ~1 GB of text.

## Setup

```bash
cd ~/dev/sacred-texts-rag
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Usage (planned)

```bash
# Convert HTML → corpus.jsonl
python -m src.convert --src "$SACRED_SRC" --out "$SACRED_OUT"

# Chunk
python -m src.chunk --in "$SACRED_OUT/corpus.jsonl" --out "$SACRED_OUT/chunks.jsonl"

# Embed + index
python -m src.embed --in "$SACRED_OUT/chunks.jsonl" --out "$SACRED_OUT/vectors"
python -m src.index --vectors "$SACRED_OUT/vectors"
```

## Size estimates

- Source: 1.80 GB across 140,480 `.htm` files
- Clean text: ~650–850 MB
- Chunks (JSONL with metadata): ~+300 MB
- Vectors (180M tokens, ~225k chunks @ 1536-dim float32): ~1.3 GB
- **Total derived data: ~2.5–3.5 GB**

## License

MIT — see [LICENSE](LICENSE).

Note: the *converted corpus* is not redistributed from this repo. Sacred-texts.com content is mostly public-domain source works; the site's own compilation work has its own terms. Consult [sacred-texts.com](https://sacred-texts.com) before redistributing derived text.
