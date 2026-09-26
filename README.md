# File Hunter Embedding Service

Standalone embedding service for [File Hunter](https://github.com/zen-logic/file-hunter). Provides image and document embeddings for similarity search and semantic content search, and converts documents to markdown.

## What it does

Two embedding pipelines and a document converter behind a simple HTTP API.

**Image embeddings** (MetaCLIP): post an image, get a 1024-dimension vector. Post text, get a vector in the same space. Image similarity search finds visually similar images or searches by description.

**Document embeddings** (Nomic): post a document (PDF, DOCX, PPTX, ODT, plain text, etc.), get it extracted, chunked by structure, and embedded as 768-dimension vectors. Semantic content search finds documents by what they contain, not just their filename.

**Document extraction** (Docling): post a document, get its full text back as markdown, with headings and tables. File Hunter uses this for "Extract to Markdown".

## Requirements

- Python 3.11+
- GPU strongly recommended. CPU works but is slow.
- LibreOffice, only for DOC, XLS and PPT documents (see [below](#libreoffice-for-doc-xls-and-ppt)).

The launch script auto-detects your GPU and installs the right PyTorch:

| GPU | Detection | PyTorch backend |
|-----|-----------|-----------------|
| NVIDIA | `nvidia-smi` | CUDA (version matched to your driver) |
| AMD | `rocm-smi` or `/opt/rocm` | ROCm 6.2 |
| Apple Silicon | macOS | MPS (included in default wheel) |
| None | fallback | CPU |

Models download from HuggingFace on first run. MetaCLIP is roughly 2.5 GB, Nomic roughly 0.5 GB.

## Installation

```bash
git clone https://github.com/zen-logic/file-hunter-embedding.git
cd file-hunter-embedding
./embedding
```

The launch script creates a virtual environment, installs PyTorch with the appropriate GPU support, installs remaining dependencies, and starts the service. First run takes longer while models download.

If you change GPU hardware, delete the `venv` directory and re-run `./embedding` to reinstall with the correct backend.

### Updating

Stop the service, then in the `file-hunter-embedding` folder:

```bash
git pull
./embedding
```

If the update changed the dependencies, the launch script installs them before starting. If you run it as a service (see [Running as a service](#running-as-a-service)), restart the service instead of running `./embedding`:

```bash
sudo systemctl restart filehunter-embedding                                          # Linux
sudo launchctl kickstart -k system/uk.zenlogic.filehunter-embedding                  # macOS
```

### LibreOffice (for DOC, XLS and PPT)

The legacy binary Office formats (DOC, XLS, PPT) are converted through LibreOffice before extraction. Without it those files fail to embed; everything else works. LibreOffice runs headless, no display needed.

Debian 12 / Ubuntu 22.04 and later (no GUI components):

```bash
sudo apt install libreoffice-writer-nogui libreoffice-calc-nogui libreoffice-impress-nogui
```

macOS:

```bash
brew install --cask libreoffice
```

Nothing to configure: the service finds LibreOffice automatically in both places these installs put it. To check it's installed, run LibreOffice's command-line program:

```bash
soffice --version                                              # Linux
/Applications/LibreOffice.app/Contents/MacOS/soffice --version  # macOS
```

## Configuration

Copy `config.json.example` to `config.json` and edit as needed. All fields are optional and fall back to defaults.

| Field | Default | Description |
|-------|---------|-------------|
| `host` | `0.0.0.0` | Bind address |
| `port` | `8002` | Port |
| `model` | `facebook/metaclip-h14-fullcc2.5b` | HuggingFace model ID for image embeddings |
| `doc_model` | `nomic-ai/nomic-embed-text-v1` | HuggingFace model ID for document embeddings |
| `offline` | `false` | Prevent HuggingFace network calls (set after models are downloaded) |

Command-line options override the config file:

| Option | Overrides |
|--------|-----------|
| `--host` | `host` |
| `--port` | `port` |
| `--model` | `model` |
| `--config` | Path to the config file (default: `config.json` in the `file-hunter-embedding` folder) |

For example: `./embedding --port 9000`

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

### Document extraction

**POST /api/extract/markdown**

```bash
curl -X POST http://localhost:8002/api/extract/markdown \
  -H "X-Filename: report.pdf" \
  --data-binary @report.pdf
```

Returns `{"markdown": "..."}`: the whole document converted to markdown by Docling, with headings and tables. Accepts the Docling formats listed below.

## Supported document formats

Extracted and chunked by document structure with Docling: PDF, DOCX, XLSX, PPTX, ODT, ODS. DOC, XLS and PPT also, when [LibreOffice](#libreoffice-for-doc-xls-and-ppt) is installed.

Chunked by paragraph as plain text: TXT, MD, CSV, JSON, XML, LOG, HTML. HTML is chunked as raw text, markup included.

## Running as a service

### systemd (Linux)

Create `/etc/systemd/system/filehunter-embedding.service`:

```ini
[Unit]
Description=File Hunter Embedding Service
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/path/to/file-hunter-embedding
ExecStart=/path/to/file-hunter-embedding/embedding
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Replace `YOUR_USER` and `/path/to/file-hunter-embedding` with your username and installation path, then enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable filehunter-embedding
sudo systemctl start filehunter-embedding
```

Check status with `systemctl status filehunter-embedding` and logs with `journalctl -u filehunter-embedding -f`.

### launchd (macOS)

This runs the service system-wide at boot, whether or not anyone is logged in. Create the plist file:

```bash
sudo nano /Library/LaunchDaemons/uk.zenlogic.filehunter-embedding.plist
```

Paste the following, replacing `YOUR_USER` with your macOS username (the one that owns the `file-hunter-embedding` folder) and the paths with your installation path:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>uk.zenlogic.filehunter-embedding</string>
    <key>UserName</key>
    <string>YOUR_USER</string>
    <key>WorkingDirectory</key>
    <string>/Users/YOUR_USER/file-hunter-embedding</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/YOUR_USER/file-hunter-embedding/embedding</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/YOUR_USER/file-hunter-embedding/embedding.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/YOUR_USER/file-hunter-embedding/embedding.log</string>
</dict>
</plist>
```

Then load it:

```bash
sudo launchctl load /Library/LaunchDaemons/uk.zenlogic.filehunter-embedding.plist
```

Useful commands:

```bash
sudo launchctl list | grep filehunter-embedding                                        # check status
sudo launchctl unload /Library/LaunchDaemons/uk.zenlogic.filehunter-embedding.plist   # stop
sudo launchctl load /Library/LaunchDaemons/uk.zenlogic.filehunter-embedding.plist     # start
tail -f ~/file-hunter-embedding/embedding.log                                          # follow logs
```

## Connecting to File Hunter

In File Hunter, open Settings, go to the Embedding Service section, tick "Enable embedding service" and enter the Embedding Service URL, e.g. `http://192.168.1.20:8002` (the address of the machine running this service, and its port). That turns on image similarity search, document content search and Extract to Markdown. File Hunter handles storage (ChromaDB) and search. This service stores nothing.

## Licence

MIT
