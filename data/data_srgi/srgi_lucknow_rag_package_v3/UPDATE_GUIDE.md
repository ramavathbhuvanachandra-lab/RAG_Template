# Update Workflow Guide — SRGI Lucknow Knowledge Package
=========================================================

## 1. Principle of Canonical Ownership
Each institutional fact has a single authoritative source:
- **Academic Programmes & Intakes:** Canonical specification in `scripts/srgi_lucknow_corpus_data_v3.py` and `data/academic_programmes.json`.
- **Administrative Officials & Contacts:** Canonical specification in `02_governance_and_leadership/srgi_lucknow_administrative_heads.md` and `data/campus_contacts.json`.
- **Placement Statistics:** Canonical specification in `10_placements_and_careers/srgi_lucknow_top_placements_and_recruiters.md`.
- **Hostel & Residential Facilities:** Canonical specification in `09_campus_facilities_and_services/srgi_lucknow_hostel_and_residential_facilities.md` and `data/hostel_facilities.json`.

## 2. Updating a Document
To update an existing document or fact:
1. Locate the document markdown specification in `scripts/srgi_lucknow_corpus_data_v3.py`.
2. Update the text, table, or Scope.
3. Update the corresponding structured JSON dataset in `data/` if the edit affects institutional entities (e.g. `campus_contacts.json` or `academic_programmes.json`).
4. Run the package builder:
   ```bash
   python scripts/build_srgi_lucknow_rag_package_v3.py
   ```
5. Run the automated test suite to ensure zero regressions:
   ```bash
   pytest tests/test_srgi_lucknow_v3_package.py -v
   ```
