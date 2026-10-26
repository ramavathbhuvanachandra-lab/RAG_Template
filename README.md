# S. R. Group of Institutions (SRGI), Lucknow — AI Assistant

> Production-ready, institution-grounded Retrieval-Augmented Generation (RAG) assistant for **S. R. Group of Institutions (SRGI), Lucknow** (`INSTITUTION_ID=srgi`).

---

## 1. Overview & Institutional Identity

This repository deploys the official, fully evidence-grounded conversational AI assistant for **S. R. Group of Institutions (SRGI), Lucknow**, encompassing:
- Faculty of Engineering & Technology (SRIMT)
- Faculty of Management Studies
- Faculty of Skill & Vocational Studies
- Faculty of Medical & Allied Health Sciences (SRM Ayush Institute, Pharmacy, Nursing, Homeopathy)

### Key Capabilities
- **High-Precision Evidence Grounding**: Answers are synthesized exclusively from verified institutional evidence extracted from authoritative documents (`srgi_lucknow_rag_package_v3`).
- **Sub-Second Embedding Latency**: Pre-warmed `nomic-embed-text` with persistent process caching and `keep_alive` ensures dense retrieval runs in < 0.20s.
- **Strict Evidence Boundary & Isolation**: Undergraduate vs. postgraduate eligibility, fees, branch structures, and statutory regulations are strictly isolated without cross-discipline pollution.
- **Deterministic Refusal & Impersonation Defense**: Safeguards prevent authority roleplay (e.g. Chairman/Registrar impersonation), prompt exfiltration, and out-of-scope fraud.
- **Interactive Campus Map & Location Directory**: Full geospatial visualization of SRGI campus blocks, hostels, and administrative facilities.
- **Turn-Accurate Developer Diagnostics**: Trace inspector displays real-time retrieval candidates, verified units, token estimates, and panel timings for each exact turn.

---

## 2. Single Authoritative Launch Command

To launch the SRGI application deterministically on port 8501:

```bash
cd /Users/bhuvanachandra/Desktop/RAG_SRGI
python run_srgi.py
```

Or directly via Streamlit:
```bash
streamlit run app.py --server.port 8501
```

Once started, open your browser at:
`http://localhost:8501`

### Running on an Alternative Port (e.g. 8502)
If port 8501 is occupied by another application:
```bash
STREAMLIT_PORT=8502 python run_srgi.py
```

---

## 3. Technology Stack & Runtime Configuration

| Layer | Component | Specification |
|---|---|---|
| **Python Runtime** | Core Engine | Python 3.11+ |
| **User Interface** | Web Application | Streamlit (>= 1.60.0) |
| **Active Institution** | Tenant ID | `srgi` (`S. R. Group of Institutions, Lucknow`) |
| **Active Staging Release** | Knowledge Package | `srgi_lucknow_rag_package_v3` |
| **Vector Collection** | ChromaDB Collection | `srgi_srgi_lucknow_rag_package_v3_staging` (768 dimensions) |
| **Dense Embeddings** | Ollama Model | `nomic-embed-text:latest` (Ollama keep_alive=3600) |
| **Language Model** | Reasoning & Answering | `qwen2.5:3b` via [Ollama](http://localhost:11434) |
| **Lexical Search** | Keyword Matching | `rank-bm25` (BM25Retriever) |
| **Fusion Algorithm** | Hybrid Reranking | Weighted Reciprocal Rank Fusion (RRF, k=60) |

---

## 4. Quickstart & Verification

### Step 1: Verify Ollama Models
Ensure Ollama is running and models are pulled:
```bash
ollama list
# Required: qwen2.5:3b, nomic-embed-text:latest
```

### Step 2: Environment Settings (.env)
```bash
INSTITUTION_ID=srgi
RAG_USE_STAGING=1
OLLAMA_BASE_URL=http://localhost:11434
QUERY_LLM_MODEL=qwen2.5:3b
ANSWER_LLM_MODEL=qwen2.5:3b
LLM_TEMPERATURE=0
```

### Step 3: Run Blind Evaluation Suite
```bash
python scripts/run_srgi_blind_evaluation.py
```

### Step 4: Run Regression Test Suite
```bash
python scripts/run_srgi_evaluation_suite.py
```

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
