# File Hunter Embedding Service

Standalone embedding service for [File Hunter](https://github.com/zen-logic/file-hunter). Provides image and document embeddings for similarity search and semantic content search.

## What it does

Two embedding pipelines behind a simple HTTP API.

**Image embeddings** (MetaCLIP): post an image, get a 1024-dimension vector. Post text, get a vector in the same space. Image similarity search finds visually similar images or searches by description.

**Document embeddings** (Nomic): post a document (PDF, DOCX, PPTX, ODT, plain text, etc.), get it extracted, chunked by structure, and embedded as 768-dimension vectors. Semantic content search finds documents by what they contain, not just their filename.

## Requirements

- Python 3.11+
- GPU (CUDA or Apple MPS) strongly recommended. CPU works but is slow.

Models download from HuggingFace on first run. MetaCLIP is roughly 2.5 GB, Nomic roughly 0.5 GB.

## Installation

```bash
git clone https://github.com/zen-logic/file-hunter-embedding.git
cd file-hunter-embedding
./embedding
```

The launch script creates a virtual environment, installs dependencies, and starts the service. First run takes longer while models download.

## Configuration

Copy `config.json.example` to `config.json` and edit as needed. All fields are optional and fall back to defaults.

| Field | Default | Description |
|-------|---------|-------------|
| `host` | `0.0.0.0` | Bind address |
| `port` | `8002` | Port |
| `model` | `facebook/metaclip-h14-fullcc2.5b` | HuggingFace model ID for image embeddings |
| `doc_model` | `nomic-ai/nomic-embed-text-v1` | HuggingFace model ID for document embeddings |
| `offline` | `false` | Prevent HuggingFace network calls (set after models are downloaded) |

CLI arguments override config: `./embedding --host 0.0.0.0 --port 9000 --model google/siglip2-so400m-patch16-512`

## API

### Image embeddings

**POST /api/embed/image**

```bash
curl -X POST http://localhost:8002/api/embed/image \
  -H "Content-Type: image/jpeg" \
  --data-binary @photo.jpg
```

Returns `{"embedding": [...]}` (1024 floats, normalised).

**POST /api/embed/text**

```bash
curl -X POST http://localhost:8002/api/embed/text \
  -H "Content-Type: application/json" \
  -d '{"text": "red socks"}'
```

Returns `{"embedding": [...]}` in the same vector space as image embeddings.

### Document embeddings

**POST /api/embed/document**

```bash
curl -X POST http://localhost:8002/api/embed/document \
  -H "X-Filename: report.pdf" \
  --data-binary @report.pdf
```

Returns `{"chunks": [{"text": "...", "meta": "...", "embedding": [...]}, ...]}`.

Documents are extracted with Docling and chunked by document structure. Plain text files are chunked by paragraph. Each chunk is embedded independently. The document model loads on first use, not at startup.

**POST /api/embed/search**

```bash
curl -X POST http://localhost:8002/api/embed/search \
  -H "Content-Type: application/json" \
  -d '{"query": "local authority legal action"}'
```

Returns `{"embedding": [...]}` (768 floats, normalised).

## Supported document formats

PDF, DOCX, PPTX, XLSX, ODT, ODS, HTML, EPUB, plain text (TXT, MD, CSV, JSON, XML, YAML, LOG, INI, RST, EML).

## Connecting to File Hunter

In File Hunter settings, enable "Similarity Search" and enter the embedding service URL. File Hunter handles storage (ChromaDB) and search. This service is stateless.

## Licence

MIT
