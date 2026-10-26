# RAG Ingestion Contract — SRGI Lucknow Release V3
==================================================

## 1. Designated Ingestion Representation
- **Companion Format for Vector / Graph Ingestion:** **DOCX** files located in `documents/`.
- **Authoritative Human-Editable Format:** **Markdown** (`.md`) files in `documents/`.
- **Metadata Pairing Mechanism:** Each `.docx` file MUST be paired with its matching metadata JSON sidecar from `metadata/<doc_id>.json`.
- **Duplicate Indexing Prohibition:** Downstream chunking pipelines MUST NOT ingest both `.docx` and `.md` versions of the same document simultaneously.

## 2. Inherited Metadata Attributes
Each chunk extracted from a document MUST inherit:
- `institution_id: srgi_lucknow`
- `document_id`
- `category`
- `subcategory`
- `source_urls`
- `canonical_source_urls`
- `markdown_hash`
- `docx_hash`
- `section_heading`
- `content_quality_status`
- `conflict_status`

## 3. Excluded Administrative Datasets
The following directories contain administrative and validation files and MUST NOT be ingested as factual student knowledge:
- `reports/` (Audit reports, test logs, parity manifests)
- `data/document_inventory.json`
- `data/manifest.json`
- `data/source_policy.json`
- `data/scope_policy.json`
