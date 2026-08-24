# Privacy Analyst — 100% Local RAG System

A Retrieval-Augmented Generation (RAG) system for chatting with sensitive documents
(payslips, contracts, medical records) while guaranteeing that no data ever leaves
the computer. Every step of the pipeline — text extraction, embeddings, semantic
search, and answer generation — runs locally, with no external API calls.

## Motivation

RAG systems built on third-party APIs (OpenAI, Anthropic, etc.) aren't viable for
highly sensitive documents: the document content travels to external servers on
every query. This project solves that by running every component of the
pipeline — from the language model to the vector database — on the user's own
hardware.

## Project status

Feature-complete. All planned phases are done:

- [x] Phase 0 — Development environment
- [x] Phase 1 — Local LLM engine (Ollama)
- [x] Phase 2 — PDF ingestion and text extraction
- [x] Phase 3 — Document chunking
- [x] Phase 4 — Embeddings and vector database
- [x] Phase 5 — Full RAG pipeline
- [x] Phase 6 — Chat interface
- [x] Phase 7 — Polish, testing, and privacy verification

## Architecture

User -> Chat interface (Streamlit)
|
+---------------------------------------+
| Your computer (offline) |
| |
| Ingestion -> Vector store -> Local LLM |
| (PDF->chunks) (ChromaDB) (Ollama) |
+---------------------------------------+

No component requires an internet connection once the models are downloaded.

## Tech stack

| Component | Tool | Why |
|---|---|---|
| LLM engine | Ollama + Llama 3.1 8B (Q4_K_M) | Runs quantized models on CPU, no dedicated GPU required |
| Embeddings | bge-m3 (via Ollama) | Multilingual model, strong performance on non-English text (see Technical decisions) |
| Vector store | ChromaDB (cosine similarity) | Embedded, no external server, on-disk persistence |
| Reranking | cross-encoder/mmarco-mMiniLMv2-L12-H384-v1 | Second-pass relevance scoring to reduce embedding false positives |
| PDF extraction | pdfplumber + pytesseract (OCR) | Automatic detection of native text vs. scanned pages |
| Chunking | langchain-text-splitters | Recursive splitting with overlap |
| Interface | Streamlit | Web chat UI with no dedicated frontend build |

## Hardware requirements

Tested on:
- Consumer-grade CPU (no dedicated GPU)
- 16 GB RAM
- Observed throughput: ~67 tokens/s with Llama 3.1 8B (Q4_K_M) — see Benchmarks

## Installation

### Prerequisites

- Windows 10/11 with WSL2
- Windows 11 22H2+ recommended (required for WSL2 "mirrored" networking mode, see Troubleshooting)

### 1. Install WSL2

From an elevated PowerShell prompt:

```powershell
wsl --install
```

Restart the computer after installation.

### 2. Set up the environment inside WSL (Ubuntu)

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git build-essential
sudo apt install -y tesseract-ocr tesseract-ocr-spa poppler-utils

git clone https://github.com/yagobordell/privacy-analyst.git
cd privacy-analyst

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Install Ollama (native Windows)

Download from [ollama.com/download](https://ollama.com/download) and install
with default options. Ollama runs as a background service on
`http://localhost:11434`.

### 4. Download the required models

From PowerShell:

```powershell
ollama pull llama3.1:8b
ollama pull bge-m3
```

### 5. Verify the WSL <-> Ollama connection

From the Ubuntu (WSL) terminal:

```bash
curl http://localhost:11434
```

Should return `Ollama is running`. If it fails, see Troubleshooting below.

### 6. Disable Streamlit telemetry

By default, Streamlit sends usage statistics to external servers — incompatible
with this project's privacy goal. Disable it with:

```bash
mkdir -p ~/.streamlit
cat >> ~/.streamlit/config.toml << 'EOF'
[browser]
gatherUsageStats = false
EOF
```

## Usage

```bash
source venv/bin/activate
streamlit run src/ui/app.py
```

This opens the interface at `http://localhost:8501`. From there you can:
1. Upload a PDF from the sidebar and click "Process and index."
2. Ask questions in the chat about the indexed documents.
3. Expand "Sources" under each answer to see which document and page it came from.

You can also run each pipeline stage independently from the terminal:

```bash
python3 src/ingestion/parser.py      # extracts text from PDFs in data/
python3 src/ingestion/chunker.py     # splits extracted text into chunks
python3 src/vectorstore/indexer.py   # generates embeddings and indexes into ChromaDB
python3 src/rag/pipeline.py          # runs a fixed set of test questions end-to-end
```

## Project structure

privacy-analyst/
├── data/ # Sample PDFs (not versioned, see .gitignore)
│ ├── processed/ # JSON files with text extracted per page
│ ├── chunks/ # JSON files with chunked text
│ └── chroma_db/ # Persistent vector database (not versioned)
├── src/
│ ├── ingestion/ # PDF parsing, OCR, chunking, single-file pipeline
│ ├── vectorstore/ # Embedding generation and ChromaDB indexing
│ ├── rag/ # Retrieval + reranking + generation pipeline
│ └── ui/ # Streamlit interface
├── notebooks/ # Exploration and prototyping
├── tests/
└── README.md

## Technical decisions

### Embedding model: nomic-embed-text -> bge-m3

`nomic-embed-text` was tried first. When evaluating retrieval with questions
phrased without literal vocabulary overlap with the source documents (e.g.
"what part of my salary goes to the tax authority?" to retrieve chunks about
income tax withholding), the system consistently returned irrelevant fragments
(an employment contract) ahead of relevant ones (payslips with the tax
deduction data).

**Diagnosis**: distances across all indexed chunks were measured for a fixed
query. The range was very narrow (0.399-0.511 with cosine similarity) for a
corpus with clearly distinct content, indicating the model wasn't
discriminating meaning well in this language. Chunks literally containing the
word "IRPF" ranked worse than semantically unrelated fragments.

**Likely cause**: `nomic-embed-text` is trained mostly on English-language
corpora, with weak multilingual support.

**Fix**: switched to `bge-m3`, a multilingual embedding model (100+ languages)
from BAAI. After reindexing, the distance range widened (0.476-0.650) and
relevant payslip chunks moved to the top of the ranking, with the contract
correctly pushed to the bottom.

**Trade-off**: `bge-m3` produces higher-dimensional vectors (1024 vs. 768) and
is computationally heavier than `nomic-embed-text`. For this project's document
volume, the impact on performance is negligible compared to the retrieval
quality gained.

### Distance metric in ChromaDB: Euclidean -> cosine

ChromaDB defaults to Euclidean distance. With embeddings that aren't
normalized to unit length, this metric is affected by vector magnitude in
addition to semantic direction, degrading search quality. The collection was
explicitly configured with `metadata={"hnsw:space": "cosine"}`, which only
considers the angle between vectors (meaning), ignoring magnitude.

### Chunk size: increased from 600 to 1200 characters

Short documents (single-page payslips and contracts) were being split into 2
chunks each purely due to chunk size, with no natural reason to fragment them.
This caused a real failure case: a question about a specific payslip's tax
deduction returned a "not found" answer even though the correct data was
indexed, because the retrieved chunk happened to be the "wrong half" of the
document (the half without the tax figure), while a near-identical sibling
chunk from the same document diluted the model's confidence. Increasing chunk
size to 1200 characters lets most short documents fit in a single chunk,
removing this artificial fragmentation. Longer, multi-page documents still
split naturally.

### Document-name filtering with accent and language normalization

When a question names a specific document (e.g. "the standard payslip"), the
pipeline detects it and restricts retrieval to that document via ChromaDB
metadata filtering, bypassing semantic ambiguity between near-duplicate
documents entirely. Two robustness issues were found and fixed during
development:
- **Accents**: "estándar" (with accent) in a question didn't match "estandar"
  (extracted from a file name without accents). Fixed by normalizing both
  sides with Unicode NFD decomposition before comparing.
- **Cross-language generic words**: a fixed exclusion list of generic words
  (e.g. "payslip", "contract") stopped working once file names and questions
  were translated to English while some words remained mismatched. Replaced
  with a dynamic approach: a word is treated as generic (and ignored) if it
  appears in more than one document's file name; otherwise it's treated as a
  unique, usable identifier for that document.

### Reranking with a cross-encoder

A cross-encoder (`cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`, multilingual)
was added as a second-pass filter after the initial embedding-based retrieval,
to catch semantic false positives the bi-encoder alone might miss. In testing,
for one specific ambiguous question, the cross-encoder actually **agreed**
with the bi-encoder's false positive (both scored an irrelevant contract chunk
above the relevant payslip chunks) — see Limitations below. The reranker is
kept in the pipeline as it's expected to improve other, less extreme cases,
even though it didn't resolve this particular one.

## Troubleshooting

### WSL2 can't reach Ollama (`localhost:11434`)

By default, WSL2 may fail to resolve `localhost` to services running on native
Windows (like Ollama), even on the same machine.

**Symptom:**
curl http://localhost:11434
curl: (7) Failed to connect to localhost port 11434

**Fix applied**: enable WSL2's "mirrored" networking mode, which unifies WSL's
network stack with Windows' (requires Windows 11 22H2+).

1. Create/edit `C:\Users\<user>\.wslconfig`:
```ini
   [wsl2]
   networkingMode=mirrored
```
2. Restart WSL from PowerShell:
```powershell
   wsl --shutdown
```
3. Verify from the Ubuntu terminal:
```bash
   curl http://localhost:11434
   # Should return: "Ollama is running"
```

**Alternative** (if your Windows version doesn't support `mirrored`): use the
Windows host's IP instead of `localhost`, obtained via `cat /etc/resolv.conf`
from WSL.

### Garbled accented characters in PowerShell (`n?mina` instead of `nómina`)

PowerShell's console doesn't interpret UTF-8 by default. Run at the start of
each session:

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

## Benchmarks

| Model | Quantization | Tokens/s (CPU, no GPU) |
|---|---|---|
| Llama 3.1 8B | Q4_K_M | ~67 tok/s |

## Known limitations

- **Table extraction**: `pdfplumber` extracts table text (like payslip
  line-item tables) as flat, linear text rather than preserving row/column
  structure. Values stay associated with their labels, but questions
  requiring arithmetic across multiple table rows might need a more
  structured extraction approach (e.g. `extract_table()`).
- **Special character encoding**: in some PDFs, characters like `º` are
  extracted incorrectly, likely due to the embedded font table in the source
  PDF. Affects isolated cases, not overall text readability.
- **Ambiguous questions across similar documents**: when a question doesn't
  specify which document it refers to (e.g. "what part of my salary goes to
  the tax authority?" with several payslips indexed), retrieval can surface an
  unrelated document (an employment contract) ahead of the relevant payslips.
  Root-cause analysis: both the bi-encoder (embeddings) and the cross-encoder
  reranker independently score a contract chunk mentioning a salary figure as
  more relevant than payslip chunks with specific tax deduction data — this
  isn't a bug in a single model, but a genuine vocabulary overlap issue
  ("salary" vs. domain-specific tax terminology). A working mitigation exists
  for questions that name a specific document (metadata filtering, see
  Technical decisions); the general ambiguous case is unresolved. In manual
  testing, once the competing document is excluded, the model correctly lists
  each remaining source's value separately rather than picking one, though it
  can occasionally confuse a tax base amount with the actual tax withheld.
  Response consistency for this specific ambiguous case also showed some
  run-to-run variance at low (0.1) temperature. Possible future improvement:
  query rewriting before retrieval, or a larger LLM for the comparison step.
- **Test corpus size**: retrieval quality was validated with a small corpus
  (4 documents, ~10-12 chunks). Sufficient to catch clear discrimination
  failures, but not to measure retrieval quality with statistical confidence
  at larger scale.

## Privacy

This project is designed so that, after initial setup (model downloads), no
outbound network connection occurs during normal use. Streamlit's telemetry
has been explicitly disabled (`gatherUsageStats = false`), as it otherwise
sends usage statistics to servers in the United States by default.

Verified by monitoring active TCP connections for the Ollama and Streamlit
processes while using the app, confirming only loopback (`127.0.0.1`)
connections between WSL and Windows on the same machine — no external IPs.

## License

_(To be decided)_
