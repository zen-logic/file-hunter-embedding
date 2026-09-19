# File Hunter Embedding Service

Standalone embedding service for [File Hunter](https://github.com/zen-logic/file-hunter). Provides image and document embeddings for similarity search and semantic content search.

## What it does

Two embedding pipelines behind a simple HTTP API:

**Image embeddings** (MetaCLIP) -- post an image, get a 1024-dimension vector. Post text, get a vector in the same space. Used for image similarity search: find visually similar images or search by description.

**Document embeddings** (Nomic) -- post a document (PDF, DOCX, PPTX, ODT, plain text, etc.), get it extracted, chunked by structure, and embedded as 768-dimension vectors. Used for semantic content search: find documents by what they say, not just their filename.

## Requirements

- Python 3.11+
- A machine with a GPU (CUDA or Apple MPS) is strongly recommended. CPU works but is slow.

Models are downloaded from HuggingFace on first run. MetaCLIP is approximately 2.5 GB, Nomic is approximately 0.5 GB.

## Installation

```bash
git clone https://github.com/zen-logic/file-hunter-embedding.git
cd file-hunter-embedding
./embedding
```

The launch script creates a virtual environment, installs dependencies, and starts the service. First run takes longer while models download.

## Configuration

Create a `config.json` in the project root (optional, defaults shown):

```json
{
    "host": "0.0.0.0",
    "port": 8002,
    "model": "facebook/metaclip-h14-fullcc2.5b",
    "doc_model": "nomic-ai/nomic-embed-text-v1",
    "offline": false
}
```

- `host` / `port` -- bind address and port
- `model` -- HuggingFace model ID for image embeddings
- `doc_model` -- HuggingFace model ID for document embeddings
- `offline` -- set to `true` after models are downloaded to prevent HuggingFace network calls

CLI arguments override config: `./embedding --host 0.0.0.0 --port 9000 --model google/siglip2-so400m-patch16-512`

## API

### Image embeddings

**POST /api/embed/image** -- embed an image

```bash
curl -X POST http://localhost:8002/api/embed/image \
  -H "Content-Type: image/jpeg" \
  --data-binary @photo.jpg
```

Returns `{"embedding": [...]}`  (1024 floats, normalised).

**POST /api/embed/text** -- embed text for image search

```bash
curl -X POST http://localhost:8002/api/embed/text \
  -H "Content-Type: application/json" \
  -d '{"text": "red socks"}'
```

Returns `{"embedding": [...]}` in the same vector space as image embeddings.

### Document embeddings

**POST /api/embed/document** -- extract, chunk, and embed a document

```bash
curl -X POST http://localhost:8002/api/embed/document \
  -H "X-Filename: report.pdf" \
  --data-binary @report.pdf
```

Returns `{"chunks": [{"text": "...", "meta": "...", "embedding": [...]}, ...]}`.

Documents are extracted with Docling (PDF, DOCX, PPTX, XLSX, ODT, HTML) and chunked by document structure. Plain text files (TXT, MD, CSV, JSON) are chunked by paragraph. Each chunk is embedded independently.

The document model loads on first use, not at startup.

**POST /api/embed/search** -- embed a query for document search

```bash
curl -X POST http://localhost:8002/api/embed/search \
  -H "Content-Type: application/json" \
  -d '{"query": "local authority legal action"}'
```

Returns `{"embedding": [...]}` (768 floats, normalised). Uses the `search_query:` prefix required by the Nomic model.

## Supported document formats

PDF, DOCX, PPTX, XLSX, ODT, ODS, HTML, EPUB, plain text (TXT, MD, CSV, JSON, XML, YAML, LOG, INI, RST, EML).

## Connecting to File Hunter

In File Hunter settings, enable "Similarity Search" and enter the embedding service URL (e.g. `http://hostname:8002`). File Hunter handles storage (ChromaDB) and search. The embedding service is stateless.

## Licence

MIT
