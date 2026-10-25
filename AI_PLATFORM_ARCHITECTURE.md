# Institutional AI Platform Architecture

> Architectural specification and system topology for the reusable institutional Retrieval-Augmented Generation (RAG) platform.

---

## 1. System Philosophy & Reusability Goal

The Institutional AI Platform is architected to support multiple higher-education institutions with **~2 days of configuration and data onboarding** rather than weeks of custom rewrites per campus.

To achieve this, the system enforces a strict separation of concerns across clean boundaries:
1. **Generic RAG Intelligence Core** (`ai_platform/core/`): Query understanding, multi-intent planning, hybrid retrieval, reciprocal rank fusion (RRF), deterministic candidate verification, multi-signal ranking, evidence boundary enforcement, claim auditing, grounded answer generation, and safety guards. No college names or institution-specific hardcoded values exist in the core.
2. **Institutional Adapters & Metadata** (`ai_platform/institutions/<id>/`): Curated vocabulary, acronyms, program aliases, degree codes, local policies, and campus data.
3. **Runtime Infrastructure** (`ai_platform/runtime/`): Local LLM integration (Ollama), embeddings (`nomic-embed-text`), vector store (ChromaDB), BM25 retriever, and graph composition roots.
4. **Service Boundary** (`ai_platform/service/`): Decoupled assistant service bridging user frontends with reasoning graphs, structured actions, and contextual suggestions.
5. **Knowledge Package Ingestion** (`ai_platform/packages/`): Standardized KIE V2 package adapter supporting schema validation, metadata chunking, release staging, and atomic promotion.
6. **Presentation Layer** (`frontend/`): Decoupled Streamlit user interface featuring dynamic branding, continuous conversation history, quick action cards, and diagnostic telemetry.

---

## 2. High-Level Architectural Topology

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                       INSTITUTIONAL RAG PLATFORM                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   frontend/                                                                 │
│   ├── app.py             Modular Streamlit entry point                      │
│   ├── components/        Chat, messages, quick actions, sidebar, maps       │
│   ├── clients/           Assistant service presentation client adapter      │
│   ├── core/              UI config loader, session manager, plugin registry │
│   └── plugins/           Tenant UI branding & quick questions (<id>/)       │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ai_platform/service/                                                      │
│   └── assistant_service.py   Canonical service orchestrator & turn handler  │
│   └── retrieval_diagnostics.py Retrieval telemetry and timing metrics      │
│   └── suggestions.py         Contextual follow-up question generator        │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ai_platform/core/                                                         │
│   ├── graph/             LangGraph deterministic node orchestration         │
│   ├── query/             Query understanding, normalization, planning       │
│   ├── conversation/      Multi-turn state resolution and multi-intent plan   │
│   ├── retrieval/         Hybrid retrieval, RRF fusion, candidate check      │
│   ├── evidence/          Evidence boundary, sufficiency, claim audit        │
│   └── answering/         Grounded answer generator, grounding check, guard  │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ai_platform/institutions/                                                 │
│   ├── loader.py          Dynamic institution profile & capability loader    │
│   └── iitj/              Reference institution: vocabulary, policies, data  │
│   └── <future_id>/       Onboarding directory per new institution           │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ai_platform/runtime/                                                      │
│   ├── engine.py          Composition root: ask() & ask_with_diagnostics()   │
│   ├── llm.py             Local LLM provider (Ollama: qwen2.5:3b)            │
│   ├── embedding.py       Dense embedding provider (nomic-embed-text)        │
│   ├── retrieval.py       BM25 + Chroma retriever factories with cache      │
│   └── vectorstore.py     ChromaDB client initialization                     │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ai_platform/packages/                                                     │
│   ├── models.py          KIE V2 schema, manifest, and contract models       │
│   ├── package_adapter.py Package validation, sidecar loading, chunking      │
│   └── registry.py        Release registry, staging isolation, rollback      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Canonical Graph Execution Flow

The canonical reasoning engine (`ai_platform/core/graph/graph.py`) compiles a deterministic LangGraph workflow:

```text
                             User Question
                                   │
                                   ▼
                       [resolve_conversation_node]
                                   │
                                   ▼
                     [understand_and_plan_query_node]
                                   │
             ┌─────────────────────┴─────────────────────┐
             ▼                                           ▼
  [retrieve_and_qualify_node]                 [process_multi_intent_node]
      (Single-Intent Path)                       (Multi-Intent Path)
             │                                           │
             └─────────────────────┬─────────────────────┘
                                   │
                                   ▼
                     [build_evidence_package_node]
                                   │
                                   ▼
                         [generate_answer_node]
                                   │
                                   ▼
                          [guard_answer_node]
                                   │
                                   ▼
                             Final Answer
```

### Typed State Contract (`RAGState`)

The graph operates on an immutable, typed state contract:

| State Field | Type | Description |
|---|---|---|
| `question` | `str` | Raw input query from user |
| `resolved_question` | `str` | Conversational resolution incorporating history |
| `query_frame` | `QueryFrame` | Extracted intents, targets, attributes, constraints |
| `query_plan` | `QueryPlan` | Execution strategy (single vs. multi-intent, search queries) |
| `retrieval_results` | `tuple` | Multi-channel raw candidate lists (Dense, BM25, Lexical) |
| `fused_candidates` | `tuple` | Reciprocal Rank Fusion (RRF) output |
| `verified_candidates`| `tuple` | Safety-gated candidates passing deterministic criteria |
| `ranked_candidates` | `tuple` | Verified candidates scored by multi-signal ranker |
| `evidence_package` | `EvidencePackage` | Final compressed context, claim audits, and status |
| `answer` | `str` | Generated user-facing answer |
| `answer_grounding` | `GroundingResult` | Polarity, numeric, currency, and causality checks |
| `answer_guard` | `GuardResult` | Sanitized output or fail-closed fallback |

---

## 4. Pipeline Stages & Verification Guarantees

### Stage 1: Query Understanding & Intent Planning
- **Modules**: `ai_platform/core/conversation/conversation.py`, `understanding.py`, `planner.py`
- Resolves conversational pronouns and context.
- Deconstructs compound multi-intent questions into independent intent units with specialized retrieval queries.
- Determines query scope (`in_scope`, `out_of_scope`, `security_violation`).

### Stage 2: Multi-Channel Hybrid Retrieval
- **Modules**: `ai_platform/runtime/retrieval.py`, `ai_platform/core/retrieval/`
- **Dense Channel**: Cosine vector similarity against `nomic-embed-text` embeddings in ChromaDB.
- **BM25 Channel**: Lexical keyword matching over tokenized corpus chunks.
- **Lexical Rescue Channel**: Acronym and exact-phrase recovery for campus-specific codes.

### Stage 3: Reciprocal Rank Fusion (RRF)
- **Module**: `ai_platform/core/retrieval/rrf.py`
- Combines multi-channel rank lists deterministically:
  RRF(d) = sum(w_c / (k + rank_c(d))) where k = 60.

### Stage 4: Pre-LLM Candidate Verification Boundary
- **Module**: `ai_platform/core/retrieval/verification.py`
- Deterministic safety and relevance filter prior to ranking.
- Rejects explicit scope mismatches, contradictory degree levels, and off-target passages.

### Stage 5: Multi-Signal Ranking
- **Module**: `ai_platform/core/retrieval/ranking.py`
- Deterministically scores verified candidates using target overlap, attribute alignment, lexical density, and source policy priors.

### Stage 6: Evidence Boundary, Sufficiency Calibration & Abstention
- **Module**: `ai_platform/core/evidence/`
- Assembles verified and ranked chunks into an `EvidencePackage`.
- Enforces a 4-state semantic decision (`SUFFICIENT`, `PARTIAL`, `INSUFFICIENT`, `CONFLICTING`).
- When evidence is missing or cannot substantiate the claim, marks `ready_for_generation=False` and abstains with standard institutional fallback.

### Stage 7: Grounded Answer Generation
- **Module**: `ai_platform/core/answering/generator.py`
- Synthesizes answers strictly from verified evidence.
- Defends against user-asserted premises and prompt injection.

### Stage 8: Grounding Verification & Extractive Repair
- **Module**: `ai_platform/core/answering/grounding.py`
- Validates generated answer against evidence without additional LLM calls: checks numeric consistency, date formats, scope boundaries, and polarity inversion.

### Stage 9: Fail-Closed Output Guarding & Citations
- **Module**: `ai_platform/core/answering/guard.py`
- Sanitizes internal metadata, attaches verified source citations, and suppresses citations during refusals.

---

## 5. Knowledge Ingestion Engine V2 Lifecycle

Institutional data onboarding is handled through `scripts/knowledge_package.py`:
- `validate`: Cryptographically validates package manifests, documents, and sidecar metadata.
- `stage`: Registers a package version in staging isolation.
- `build-index`: Creates the staging Chroma vector index and lexical search cache.
- `evaluate`: Evaluates retrieval and answering quality across validation probes.
- `compare`: Compares active baseline vs staging results.
- `activate`: Performs zero-downtime cutover of active release pointers.
- `status`: Displays current active and staged configurations.
- `rollback`: Instantly reverts to the previous release.
