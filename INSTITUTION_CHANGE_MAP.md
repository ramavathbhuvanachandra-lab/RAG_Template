# Institution Adaptation Guide & Change Map

## Purpose

This guide outlines exactly which files to preserve (shared RAG intelligence) and which files to modify or supply when onboarding a new college or university.

The repository architecture isolates institutional behaviors into specific adapters and knowledge packages, avoiding full codebase rewrites.

---

## 1. Shared Platform Core (DO NOT MODIFY)

These modules represent the common RAG engine and runtime infrastructure. They are completely decoupled from any single institution's name, degree list, or vocabulary.

### Generic Reasoning Engine (`ai_platform/core/`)
- `ai_platform/core/graph/`: LangGraph orchestration nodes (`nodes.py`, `graph.py`, `state.py`).
- `ai_platform/core/query/`: Query understanding, canonical planning, and frame normalization (`understanding.py`, `planner.py`).
- `ai_platform/core/conversation/`: Multi-turn reference resolution and multi-intent decomposition (`conversation.py`, `multi_intent.py`).
- `ai_platform/core/retrieval/`: Multi-channel retrieval, Reciprocal Rank Fusion, candidate verification, ranking, and evidence boundaries (`rrf.py`, `verification.py`, `ranking.py`, `evidence_boundary.py`).
- `ai_platform/core/evidence/`: Sufficiency evaluation, coverage analysis, claim auditing, and context compression (`evidence.py`, `coverage.py`, `claims.py`, `packaging.py`, `grouping.py`, `scope.py`).
- `ai_platform/core/answering/`: Grounded generation, inversion protection, Devanagari detection, and fail-closed output guards (`generator.py`, `grounding.py`, `guard.py`).
- `ai_platform/core/institution/`: Abstract profile and adapter base classes (`profile.py`).

### Runtime Infrastructure (`ai_platform/runtime/`)
- `ai_platform/runtime/engine.py`: Canonical composition roots (`ask()`, `ask_with_diagnostics()`).
- `ai_platform/runtime/llm.py`: Local Ollama LLM provider.
- `ai_platform/runtime/embedding.py`: Dense embedding model integration.
- `ai_platform/runtime/vectorstore.py`: ChromaDB initialization with multi-institution cache keys.
- `ai_platform/runtime/retrieval.py`: BM25 and Chroma retriever factories with cached instances.
- `ai_platform/runtime/corpus.py`: Document loading and chunking helpers.
- `ai_platform/runtime/config.py`: Dynamic runtime environment configuration.

### Canonical Service Layer (`ai_platform/service/`)
- `ai_platform/service/assistant_service.py`: Service boundary handling chat turns, structured routing, and safety fallbacks.
- `ai_platform/service/retrieval_diagnostics.py`: Retrieval telemetry and timing metrics.
- `ai_platform/service/suggestions.py`: Context-aware follow-up suggestion generator.

### Knowledge Ingestion Engine V2 Adapter (`ai_platform/packages/`)
- `ai_platform/packages/package_adapter.py`: Validates KIE V2 releases, loads canonical documents and structured records, and chunks text with metadata sidecars.
- `ai_platform/packages/models.py`: Data models for releases, documents, sidecars, and manifests.
- `ai_platform/packages/registry.py`: Manages active and staging release configurations.

### Shared UI Shell (`frontend/`)
- `frontend/components/`: Chat layout, messages, sidebar, diagnostics viewer, cards.
- `frontend/core/`: Session manager, configuration loader, plugin registry.
- `frontend/clients/`: Presentation-layer service client.
- `frontend/styles.py`: Dynamic CSS tokens and theme injector.

---

## 2. Institution-Specific Components (CUSTOMIZE PER CAMPUS)

To adapt the platform for a new institution (e.g. `xyz`):

### A. Environment Configuration (`.env`)
```bash
INSTITUTION_ID=xyz
OLLAMA_BASE_URL=http://localhost:11434
QUERY_LLM_MODEL=qwen2.5:3b
ANSWER_LLM_MODEL=qwen2.5:3b
```

### B. Institution Profile & Lexical Rules (`ai_platform/institutions/xyz/`)
Create `ai_platform/institutions/xyz/` by duplicating `ai_platform/institutions/iitj/`:
1. **`profile.py`**:
   - `INSTITUTION_ID = "xyz"`
   - `DISPLAY_NAME = "XYZ University"`
   - `VECTORSTORE_COLLECTION = "xyz_v1"`
   - `INSTITUTION_DATA_ROOT = PROJECT_ROOT / "data" / "data_xyz"`
   - `fallback_message = "Sorry, I couldn't find reliable information about that in the available XYZ University documents."`
2. **`data/aliases.json`**: Degree and programme naming variations (e.g., "btech", "b.tech", "bachelor of technology").
3. **`data/acronyms.json`**: Campus departments, schools, and building acronyms.
4. **`data/phrases.json`**: Exact multi-word domain phrases.
5. **`data/semantic_terms.json`**: Topic tags, attribute keywords, and campus vocabulary.
6. **`data/source_policy.json`**: Topic-to-category priors for re-ranking.
7. **`data/scope_policy.json`**: Boundary definitions for programs, degrees, and student types.

### C. Optional Structured Handlers (`ai_platform/institutions/xyz/`)
If the new institution supports campus navigation or emergency contacts:
- `campus_navigation.py`: Map coordinates and location search handler.
- `emergency.py`: Emergency response contact directory handler.
- If not supported, simply return `None` or disable them in `profile.py`.

### D. Frontend UI Plugin (`frontend/plugins/xyz/`)
Create `frontend/plugins/xyz/plugin.py`:
- `display_name = "XYZ University"`
- `logo_icon = "🎓"`
- `primary_color`, `accent_color`, `hero_badge_bg`
- `suggested_questions`: Curated homepage starter questions relevant to XYZ.
- `has_campus_map`: Set to `False` if no map data is available.

### E. Factual Knowledge Package (`data/data_xyz/`)
Provide the new institution's KIE V2 package in `data/data_xyz/<package_name>/`:
- Manifests (`document_inventory.json`, `package_manifest.json`)
- Readable documents (`documents/*.docx`)
- Paired metadata sidecars (`metadata/*.json`)
- Structured fact records (`data/*.json`)

---

## 3. Operational Indexing & Cutover

After configuring the files above, use `scripts/knowledge_package.py` to index and launch:

```bash
# 1. Validate the new package
python scripts/knowledge_package.py validate --package-root data/data_xyz/<package_name>

# 2. Stage the release
python scripts/knowledge_package.py stage \
    --package-root data/data_xyz/<package_name> \
    --institution xyz \
    --release xyz_package_v1

# 3. Build the vector index and lexical cache
python scripts/knowledge_package.py build-index --institution xyz

# 4. Activate the release
python scripts/knowledge_package.py activate --institution xyz --force

# 5. Start Streamlit
INSTITUTION_ID=xyz streamlit run app.py
```
