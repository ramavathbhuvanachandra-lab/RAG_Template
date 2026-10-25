# Institutional RAG Chatbot Source Template

> A clean, production-ready, institution-grounded Retrieval-Augmented Generation (RAG) source template designed for rapid cloning and multi-institution deployment. Reference institution: **Indian Institute of Technology Jodhpur (IIT Jodhpur)**.

---

## 1. Overview & Reusability Goal

`RAG_Source_Template` is a clean source-code distribution extracted from the validated institutional RAG platform. It contains only production application code, runtime dependencies, institution configuration, knowledge-package adapters, operational deployment files, and documentation.

This repository is designed to be **cloned once per educational institution** (e.g. for IIT Jodhpur, IIT Mandi, SRGI Lucknow, etc.) and customized through configuration and data packages rather than code rewrites.

### Key Capabilities
- **High-Precision Evidence Grounding**: Answers are synthesized exclusively from verified institutional evidence extracted from authoritative documents.
- **Compound Query Understanding**: Automatically decomposes multi-policy queries into focused sub-queries and aggregates answers.
- **Hybrid Retrieval & RRF**: Fuses dense semantic vector retrieval (`nomic-embed-text` in ChromaDB) with lexical keyword search (`rank-bm25`) using weighted Reciprocal Rank Fusion.
- **Strict Evidence Boundary & Qualification**: Deterministically rejects off-target passages and prevents hallucinated cross-degree assertions.
- **Safe Abstention**: Refuses speculation gracefully when evidence is insufficient or conflicting.
- **Attribution & Provenance**: Provides authoritative source citations in the UI with zero hallucinated citations on abstention.
- **Decoupled Modern Frontend**: Modular Streamlit interface (`frontend/`) supporting institutional themes, continuous chat history, quick action cards, and diagnostic inspectors.

---

## 2. Directory Structure

```text
RAG_Source_Template/
├── app.py                     # Primary Streamlit application launcher
├── requirements.txt           # Verified Python runtime dependencies
├── Dockerfile                 # Container image specification
├── docker-compose.yml         # Local container orchestration
├── .env.example               # Environment configuration template
├── .gitignore                 # Clean ignore rules (excludes caches, local DBs)
├── .dockerignore              # Container build ignore rules
├── README.md                  # Template documentation & onboarding guide
├── AI_PLATFORM_ARCHITECTURE.md# Comprehensive architectural specification
├── flow.md                    # Detailed runtime execution flow & state schema
├── INSTITUTION_CHANGE_MAP.md  # Detailed institution adaptation map
├── frontend/                  # Modular Streamlit user interface
│   ├── app.py                 # Frontend composition root
│   ├── styles.py              # Dynamic theme & styling token injector
│   ├── clients/               # Presentation-to-service client adapter
│   ├── components/            # Chat view, messages, sidebar, cards
│   ├── core/                  # Session manager, config loader, plugin registry
│   └── plugins/               # Institution UI plugins (iitj, template)
├── ai_platform/               # Reusable AI Platform core & runtime
│   ├── core/                  # Core RAG engine (graph, retrieval, answering)
│   ├── runtime/               # Execution roots, LLM, embeddings, vectorstore
│   ├── service/               # Canonical assistant service boundary
│   ├── packages/              # KIE V2 package adapter & release registry
│   └── institutions/          # Institution profiles & adapters
│       ├── loader.py          # Dynamic institution profile resolver
│       └── iitj/              # Reference institution configuration & data
├── data/                      # Reference data & knowledge packages
│   ├── campus_locations.json  # Reference campus coordinates & map data
│   ├── emergency_contacts.json# Reference emergency contact list
│   ├── staging_release_iitj.json # Staging release metadata
│   └── data_iitj/             # Reference institution knowledge root
│       └── iit_jodhpur_rag_package_v2/ # Validated KIE V2 package
└── scripts/
    └── knowledge_package.py   # Operational package validation & indexing CLI
```

---

## 3. Technology Stack & Prerequisites

| Layer | Component | Specification |
|---|---|---|
| **Python Runtime** | Core Engine | Python 3.11+ |
| **User Interface** | Web Application | Streamlit (>= 1.60.0) |
| **Reasoning Engine** | Graph Orchestration | LangGraph (>= 1.2.9) |
| **Local LLM** | Answer & Query Generation | `qwen2.5:3b` via [Ollama](http://localhost:11434) |
| **Embeddings** | Dense Semantic Search | `nomic-embed-text:latest` via [Ollama](http://localhost:11434) |
| **Vector Database** | Local Vector Persistence | ChromaDB (>= 1.5.9) |
| **Lexical Search** | Keyword Matching | `rank-bm25` (BM25Retriever) |
| **Package Adapter** | Data Ingestion V2 | `scripts/knowledge_package.py` |

### System Requirements
1. **Ollama**: Installed and running locally (`ollama serve`).
2. **Models pulled**:
   ```bash
   ollama pull qwen2.5:3b
   ollama pull nomic-embed-text
   ```

---

## 4. Quickstart: Running IIT Jodhpur Reference Deployment

### Step 1: Environment Setup
Create and activate a virtual environment:
```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Configure Environment
```bash
cp .env.example .env
```
Default `.env` settings point to `INSTITUTION_ID=iitj` and `OLLAMA_BASE_URL=http://localhost:11434`.

### Step 3: Validate the Reference Knowledge Package
Validate the included IIT Jodhpur KIE V2 package:
```bash
python scripts/knowledge_package.py validate --package-root data/data_iitj/iit_jodhpur_rag_package_v2
```

### Step 4: Build the Vector & Lexical Index
The repository does not commit binary Chroma databases or disposable lexical caches. Build them locally from the validated package:
```bash
# 1. Stage the package
python scripts/knowledge_package.py stage \
    --package-root data/data_iitj/iit_jodhpur_rag_package_v2 \
    --institution iitj \
    --release iit_jodhpur_rag_package_v2

# 2. Build the vector collection and lexical cache
python scripts/knowledge_package.py build-index --institution iitj

# 3. (Optional) Run evaluation probes to verify indexing
python scripts/knowledge_package.py evaluate --institution iitj

# 4. Activate the release
python scripts/knowledge_package.py activate --institution iitj --force
```

### Step 5: Launch the Streamlit Web Application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 5. How to Adapt this Template for a New Institution

To deploy this template for a new institution (e.g. `xyz` university):

### 1. Create Institution Configuration Directory
Create `ai_platform/institutions/xyz/` by copying the structure from `ai_platform/institutions/iitj/`:
```bash
cp -r ai_platform/institutions/iitj ai_platform/institutions/xyz
```
Update `profile.py`:
- `INSTITUTION_ID = "xyz"`
- `DISPLAY_NAME = "XYZ University"`
- `VECTORSTORE_COLLECTION = "xyz_v1"`
- `INSTITUTION_DATA_ROOT = PROJECT_ROOT / "data" / "data_xyz"`
- Update `fallback_message`, `answer_tone`, etc.

Update lexical rules and domain policies in `data/`:
- `aliases.json`: Local program synonyms and degree abbreviations.
- `acronyms.json`: Department and facility acronyms.
- `semantic_terms.json`: Domain entity bindings.
- `source_policy.json`: Document priority weights.

### 2. Supply the Knowledge Ingestion V2 Package
Place the institution's validated KIE V2 package under `data/data_xyz/<package_name>/`.
Ensure the package contains:
- `manifests/document_inventory.json`
- `documents/` (canonical `.docx` files)
- `metadata/` (paired sidecar JSON files)

### 3. Configure Frontend UI Plugin
Create a frontend plugin under `frontend/plugins/xyz/` (or copy `frontend/plugins/template/`):
```bash
cp -r frontend/plugins/template frontend/plugins/xyz
```
Configure:
- College display name, logo icon, primary brand colors.
- Quick suggested questions reflecting XYZ's academic programs.
- Optional campus map coordinates or emergency contact directories.

### 4. Build Index and Activate
```bash
export INSTITUTION_ID=xyz

# Validate
python scripts/knowledge_package.py validate --package-root data/data_xyz/<package_name>

# Stage & Build
python scripts/knowledge_package.py stage --package-root data/data_xyz/<package_name> --institution xyz
python scripts/knowledge_package.py build-index --institution xyz

# Activate
python scripts/knowledge_package.py activate --institution xyz --force
```

### 5. Launch
```bash
INSTITUTION_ID=xyz streamlit run app.py
```

---

## 6. Running with Docker

Build and run using Docker Compose:
```bash
docker-compose up --build
```
Ensure Ollama is accessible from within the container (via `http://host.docker.internal:11434` or an external network host).

---

## 7. License & Compliance
This software is intended for institutional deployment. Document corpora and institutional knowledge packages are proprietary to their respective institutions.
