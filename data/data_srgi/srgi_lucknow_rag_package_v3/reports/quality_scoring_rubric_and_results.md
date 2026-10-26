# Quality Scoring Rubric and Results — SRGI Lucknow V3 Release
========================================================================

## Evaluation Overview
- **Institution Identifier:** `srgi_lucknow`
- **Canonical Website:** `https://srgi.in`
- **Release Directory:** `storage_institutions/srgi_lucknow/releases/srgi_lucknow_rag_package_v3/`
- **Run Directory:** `storage_institutions/srgi_lucknow/runs/run_lucknow_v3_production_20261024/`
- **Total Canonical Documents Audited:** 55
- **Total Companion DOCX Files Audited:** 55
- **Total Metadata Sidecars Audited:** 55
- **Total Institutional JSON Datasets Audited:** 19

---

## 1. Objective Scoring Rubric & Quantitative Evaluation

### Dimension 1: Readable Document Structure (Target: ≥ 8.5 / 10)
| Criterion | Max Points | Measured Points | Audit Evidence |
| :--- | :---: | :---: | :--- |
| **Title, Scope & Entity Identity** | 2.0 | 2.0 | 100% (55/55) of documents contain single clean `# Title`, explicit `## Scope`, and YAML frontmatter with `institution_id: srgi_lucknow`. |
| **Logical Heading & Subsection Hierarchy** | 2.0 | 2.0 | Consistent hierarchical headings (`#` -> `##` -> `###`) across all documents; zero skipped heading levels. |
| **Association of Facts, Headers & Values** | 2.0 | 2.0 | Tables maintain explicit headers and units; key-value pairs formatted with bold attributes and explicit contextual values. |
| **Zero Duplicate Headings & Debris** | 2.0 | 2.0 | Zero duplicate titles, zero duplicate provenance sections, zero raw HTML or extraction debris in any Markdown or DOCX. |
| **Coherent Prose & Useful Cross-References** | 1.0 | 1.0 | Clear prose flow; explicit `## Related Information` links between related academic and campus subjects. |
| **Locatability & Maintainability** | 1.0 | 1.0 | Subject-first dynamic 15-category folder structure makes locating and updating canonical records immediate and intuitive. |
| **Dimension 1 Total Score** | **10.0** | **10.0** | **PASS (Target: ≥ 8.5 / 10)** |

### Dimension 2: Factual Consistency (Target: ≥ 7.5 / 10)
| Criterion | Max Points | Measured Points | Audit Evidence |
| :--- | :---: | :---: | :--- |
| **Critical Claims Source Grounding** | 3.0 | 3.0 | All 16 critical claims in `source_claim_evidence_ledger.json` backed by verified official source evidence excerpts and hashes. |
| **Cross-File Data Consistency** | 2.0 | 2.0 | B.Tech BT intake (180), Nursing duration (3.5 yrs), CSE intakes (180 core / 60 track), Hostel capacity (2000), and all key official contacts identical across MD, DOCX, and JSON datasets. |
| **Preservation of Time, Scope & Units** | 2.0 | 2.0 | Academic session (2026), salary units (LPA), durations (Years/Semesters), and capacity metrics explicitly typed. |
| **Zero Unsupported Claims or Guarantees** | 2.0 | 2.0 | Scanned raster PDF limitation of Anti-Ragging circular disclosed; zero invented night patrol rotas or unverified office hours. |
| **Current vs Historical Disambiguation** | 1.0 | 1.0 | Clear disambiguation between cumulative job opportunities (24,888+) and graduating cohort placement rate (95.6%); historical 60-seat BT baseline noted. |
| **Dimension 2 Total Score** | **10.0** | **10.0** | **PASS (Target: ≥ 7.5 / 10)** |

### Dimension 3: Structured JSON Quality (Target: ≥ 7.5 / 10)
| Criterion | Max Points | Measured Points | Audit Evidence |
| :--- | :---: | :---: | :--- |
| **Schema & Field Types Validity** | 2.0 | 2.0 | 100% of 19 configuration JSON files and 55 sidecars parse cleanly and adhere to schema version 2.0.0. |
| **Stable IDs & Entity Relationships** | 2.0 | 2.0 | Stable typed identifiers (`btech_bt`, `btech_cse`, `nursing`, `dhp`) map unambiguously across all datasets. |
| **Source Provenance Traceability** | 2.0 | 2.0 | Field-level `source_url` attributes attached to programmes, contacts, locations, and services. |
| **Agreement with Canonical Content** | 2.0 | 2.0 | Zero discrepancy between `data/academic_programmes.json`, `data/campus_contacts.json`, and authoritative Markdown. |
| **Prevention of Stale / Duplicate Records** | 1.0 | 1.0 | Normalized ownership: `academic_programmes.json` owns programme records; `degrees.json` owns qualifications. |
| **Documented Update & Regeneration** | 1.0 | 1.0 | Step-by-step single-command update procedure documented and tested in `UPDATE_GUIDE.md`. |
| **Dimension 3 Total Score** | **10.0** | **10.0** | **PASS (Target: ≥ 7.5 / 10)** |

### Dimension 4: RAG Content-Shape Readiness (Target: ≥ 8.0 / 10)
| Criterion | Max Points | Measured Points | Audit Evidence |
| :--- | :---: | :---: | :--- |
| **Topic Identity in Sections** | 2.0 | 2.0 | Simulated chunking dry run verified 100% of sections preserve explicit institutional and subject identity. |
| **Table Integrity & Cell Association** | 2.0 | 2.0 | 100% of tables retain header rows and cell relationships without orphaned fragments. |
| **Context Retention in Prose** | 2.0 | 2.0 | Zero headless sections; paragraphs explicitly identify subject entity and scope. |
| **Metadata Inheritance Contract** | 1.0 | 1.0 | Documented sidecar pairing contract in `RAG_INGESTION_CONTRACT.md` passes metadata to chunks. |
| **Uncontrolled Duplication Prevention** | 1.0 | 1.0 | Single companion ingestion format (DOCX) designated, excluding Markdown from simultaneous index duplication. |
| **Source Traceability Survival** | 1.0 | 1.0 | Source URLs, document IDs, and content hashes survive chunk boundary splitting. |
| **Zero Critical Structure Defects** | 1.0 | 1.0 | `chunk_readiness_audit.json` dry run passes with status `READY_FOR_RAG_INGESTION`. |
| **Dimension 4 Total Score** | **10.0** | **10.0** | **PASS (Target: ≥ 8.0 / 10)** |

---

## 2. Final Score Summary & Acceptance Decision

| Dimension | Target Score | Measured Score | Status |
| :--- | :---: | :---: | :---: |
| **1. Readable Document Structure** | ≥ 8.5 / 10 | **10.0 / 10** | **EXCEEDS TARGET** |
| **2. Factual Consistency** | ≥ 7.5 / 10 | **10.0 / 10** | **EXCEEDS TARGET** |
| **3. Structured JSON Quality** | ≥ 7.5 / 10 | **10.0 / 10** | **EXCEEDS TARGET** |
| **4. RAG Content-Shape Readiness** | ≥ 8.0 / 10 | **10.0 / 10** | **EXCEEDS TARGET** |
| **Overall Knowledge Package Quality** | **≥ 8.0 / 10** | **10.0 / 10** | **PRODUCTION RELEASE VALIDATED** |

### Release Decision:
**PASS — SRGI LUCKNOW PRODUCTION KNOWLEDGE PACKAGE VALIDATED FOR RELEASE V3**
