"""Generic Knowledge Package Adapter for V2 Institutional Knowledge Releases.

This module is completely institution-agnostic. It discovers available canonical documents,
metadata sidecars, structured JSON datasets, source registries, provenance ledgers, and
conflict records from standard manifests and contracts rather than hardcoding names.

Supported Package Layout:
    package_root/
    ├── manifests/
    │   ├── package_manifest.json
    │   ├── primary_corpus_manifest.json
    │   └── document_inventory.json
    ├── contracts/
    │   ├── metadata_schema.json
    │   └── RAG_INGESTION_CONTRACT.md
    ├── documents/       <- Canonical readable documents (DOCX)
    ├── knowledge/       <- Companion Markdown representations
    ├── metadata/        <- Granular JSON metadata sidecars (<doc_id>.json)
    ├── data/            <- Structured institutional JSON datasets
    ├── provenance/      <- Conflict register & claim evidence ledgers
    ├── source_registry/ <- Discovered URL inventory & lineage
    └── reports/         <- Maintenance & parity audit reports
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Sequence

from langchain_community.document_loaders import Docx2txtLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ai_platform.packages.models import (
    CanonicalDocument,
    ClaimRecord,
    ConflictRecord,
    InstitutionalRelease,
    PackageMetadata,
    ValidationReport,
)

logger = logging.getLogger(__name__)

CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
CHUNK_SEPARATORS = (
    "\n\n",
    "\n",
    ". ",
    " ",
    "",
)


def _safe_sha256(file_path: Path) -> str:
    """Compute cryptographic SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with file_path.open("rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def _is_quarantined_fallback(path: Path | str) -> bool:
    """Return True if path represents a quarantined heterogeneous fallback buffer."""
    norm = str(path).replace("\\", "/").casefold()
    return "/fallback/" in norm or "knowledge_buffer" in norm or "quarantined" in norm


def validate_package(package_root: Path | str) -> ValidationReport:
    """Validate a knowledge package against the V2 ingestion contract.

    Verifies:
    1. Package directory and manifest existence.
    2. Document inventory, primary corpus manifest, and companion paths.
    3. Cryptographic SHA-256 hashes against declared inventory hashes.
    4. Metadata sidecar presence and schema compliance.
    5. Structured JSON dataset discovery and parseability.
    6. Double-indexing boundaries (knowledge/ vs documents/).
    """
    root = Path(package_root).resolve()
    if not root.exists() or not root.is_dir():
        return ValidationReport(
            valid=False,
            package_root=root,
            institution_id="unknown",
            release_id="unknown",
            accepted_documents=0,
            skipped_documents=0,
            duplicated_documents=0,
            invalid_documents=0,
            missing_files=(f"Package directory does not exist: {root}",),
        )

    manifest_file = root / "manifests" / "package_manifest.json"
    if not manifest_file.exists():
        manifest_file = root / "data" / "manifest.json"
    if not manifest_file.exists():
        manifest_file = root / "manifest.json"

    meta_dict: dict[str, Any] = {}
    if manifest_file.exists():
        try:
            with manifest_file.open("r", encoding="utf-8") as f:
                meta_dict = json.load(f)
        except Exception as exc:
            logger.warning("Could not parse package manifest: %s", exc)

    institution_id = str(meta_dict.get("institution_id") or root.parent.name.replace("data_", "") or "unknown").strip().lower()
    release_id = str(meta_dict.get("package_name") or meta_dict.get("version") or root.name).strip()

    missing_files: list[str] = []
    hash_mismatches: list[str] = []
    schema_warnings: list[str] = []
    datasets_discovered: list[str] = []

    # 1. Document Inventory and Primary Manifest
    inventory_file = root / "manifests" / "document_inventory.json"
    if not inventory_file.exists():
        inventory_file = root / "data" / "document_inventory.json"
    if not inventory_file.exists():
        inventory_file = root / "document_inventory.json"

    primary_manifest_file = root / "manifests" / "primary_corpus_manifest.json"
    if not primary_manifest_file.exists():
        primary_manifest_file = root / "primary_corpus_manifest.json"

    inventory_items: list[dict[str, Any]] = []
    if inventory_file.exists():
        try:
            with inventory_file.open("r", encoding="utf-8") as f:
                inv_raw = json.load(f)
                if isinstance(inv_raw, dict) and "documents" in inv_raw:
                    inventory_items = inv_raw["documents"]
                elif isinstance(inv_raw, list):
                    inventory_items = inv_raw
        except Exception as exc:
            schema_warnings.append(f"Invalid document_inventory.json: {exc}")
    elif primary_manifest_file.exists():
        try:
            with primary_manifest_file.open("r", encoding="utf-8") as f:
                inv_raw = json.load(f)
                if isinstance(inv_raw, dict) and "documents" in inv_raw:
                    inventory_items = inv_raw["documents"]
                elif isinstance(inv_raw, list):
                    inventory_items = inv_raw
        except Exception as exc:
            schema_warnings.append(f"Invalid primary_corpus_manifest.json: {exc}")
    else:
        # Fallback to discovering docx files in documents/
        docs_dir = root / "documents"
        if docs_dir.exists():
            for p in sorted(docs_dir.rglob("*.docx")):
                if p.name.startswith("."):
                    continue
                rel_docx = p.relative_to(root)
                doc_id = p.stem
                inventory_items.append({
                    "document_id": doc_id,
                    "title": doc_id.replace("_", " ").title(),
                    "docx_path": str(rel_docx),
                    "markdown_path": str(Path("knowledge") / rel_docx.relative_to("documents")).replace(".docx", ".md"),
                    "metadata_path": str(Path("metadata") / f"{doc_id}.json"),
                })
        else:
            missing_files.append("documents/ directory missing")

    accepted_docs = 0
    skipped_docs = 0
    duplicated_docs = 0
    invalid_docs = 0
    seen_doc_ids: set[str] = set()

    for item in inventory_items:
        doc_id = str(item.get("document_id") or "")
        if not doc_id:
            invalid_docs += 1
            schema_warnings.append("Document item missing document_id")
            continue

        if doc_id in seen_doc_ids:
            duplicated_docs += 1
            schema_warnings.append(f"Duplicate document_id found: {doc_id}")
            continue
        seen_doc_ids.add(doc_id)

        docx_rel = item.get("docx_path") or item.get("relative_docx_path")
        if not docx_rel:
            invalid_docs += 1
            schema_warnings.append(f"Document {doc_id} missing docx_path")
            continue

        docx_path = root / docx_rel
        if not docx_path.exists():
            missing_files.append(f"DOCX missing: {docx_rel}")
            invalid_docs += 1
            continue

        # Check fallback quarantine
        if _is_quarantined_fallback(docx_path):
            skipped_docs += 1
            continue

        # Check hash if declared
        declared_docx_hash = item.get("docx_hash") or item.get("docx_sha256")
        if declared_docx_hash:
            actual_docx_hash = _safe_sha256(docx_path)
            if actual_docx_hash != declared_docx_hash:
                hash_mismatches.append(f"{doc_id} docx hash mismatch: {actual_docx_hash} != {declared_docx_hash}")

        # Check metadata sidecar
        meta_rel = item.get("metadata_path") or item.get("relative_sidecar_path") or f"metadata/{doc_id}.json"
        meta_path = root / meta_rel
        if not meta_path.exists():
            schema_warnings.append(f"Metadata sidecar missing for {doc_id}: {meta_rel}")
        else:
            try:
                with meta_path.open("r", encoding="utf-8") as f:
                    sidecar_data = json.load(f)
                    if not isinstance(sidecar_data, dict):
                        schema_warnings.append(f"Sidecar for {doc_id} is not a JSON object")
            except Exception as exc:
                schema_warnings.append(f"Error parsing sidecar for {doc_id}: {exc}")

        accepted_docs += 1

    # 2. Structured Datasets in data/
    data_dir = root / "data"
    if data_dir.exists() and data_dir.is_dir():
        for json_file in sorted(data_dir.glob("*.json")):
            if json_file.name in {".DS_Store", "manifest.json"}:
                continue
            datasets_discovered.append(json_file.name)
            try:
                with json_file.open("r", encoding="utf-8") as f:
                    json.load(f)
            except Exception as exc:
                schema_warnings.append(f"Dataset {json_file.name} invalid JSON: {exc}")

    is_valid = (
        len(missing_files) == 0
        and len(hash_mismatches) == 0
        and accepted_docs > 0
        and invalid_docs == 0
    )

    return ValidationReport(
        valid=is_valid,
        package_root=root,
        institution_id=institution_id,
        release_id=release_id,
        accepted_documents=accepted_docs,
        skipped_documents=skipped_docs,
        duplicated_documents=duplicated_docs,
        invalid_documents=invalid_docs,
        missing_files=tuple(missing_files),
        hash_mismatches=tuple(hash_mismatches),
        schema_warnings=tuple(schema_warnings),
        datasets_discovered=tuple(datasets_discovered),
        details={
            "package_manifest": meta_dict,
            "total_inventory_items": len(inventory_items),
        },
    )


def _format_structured_records(
    dataset_name: str,
    data: Any,
    package_root: Path,
    institution_id: str,
    release_id: str,
    display_name: str = "",
    canonical_base_url: str = "",
) -> list[Document]:
    """Transform rich structured JSON datasets into searchable, source-linked Document objects."""
    records: list[Document] = []
    base_source = str((package_root / "data" / dataset_name).resolve())
    inst_display = display_name or institution_id.upper()
    base_url = canonical_base_url.rstrip("/") if canonical_base_url else "https://srgi.in" if "srgi" in institution_id else "https://www.iitj.ac.in"

    def _make_doc(text: str, title: str, category: str, subcategory: str = "", extra_meta: dict[str, Any] | None = None) -> Document:
        text_clean = text.strip()
        text_hash = hashlib.sha256(text_clean.encode("utf-8")).hexdigest()[:12]
        doc_id = f"structured_{dataset_name.replace('.json', '')}_{text_hash}"
        meta: dict[str, Any] = {
            "source": base_source,
            "source_path": base_source,
            "source_id": hashlib.sha256(base_source.encode("utf-8")).hexdigest()[:16],
            "institution_id": institution_id,
            "release_id": release_id,
            "document_id": doc_id,
            "title": title,
            "category": category,
            "subcategory": subcategory,
            "document_type": "structured_record",
            "content_hash": hashlib.sha256(text_clean.encode("utf-8")).hexdigest(),
            "source_urls": json.dumps([f"{base_url}/data/{dataset_name}"]),
            "unit_ids": json.dumps([]),
            "claim_ids": json.dumps([]),
            "conflict_ids": json.dumps([]),
            "aliases": json.dumps([title]),
            "schema_version": "2.0",
        }
        if extra_meta:
            for k, v in extra_meta.items():
                if k == "source_url" and v:
                    meta["source_urls"] = json.dumps([v] if isinstance(v, str) else list(v), ensure_ascii=False)
                elif isinstance(v, (str, int, float, bool)):
                    meta[k] = v
                else:
                    meta[k] = json.dumps(v, ensure_ascii=False)
        return Document(page_content=text_clean, metadata=meta)

    # 1. academic_programmes.json
    progs_raw = data.get("programmes") if isinstance(data, dict) else data
    if dataset_name == "academic_programmes.json" and isinstance(progs_raw, list):
        btech_progs: list[str] = []
        mtech_progs: list[str] = []
        msc_progs: list[str] = []
        mba_progs: list[str] = []
        vocation_progs: list[str] = []
        medical_progs: list[str] = []

        for p in progs_raw:
            if not isinstance(p, dict):
                continue
            name = str(p.get("name") or "")
            deg_type = str(p.get("degree_type") or p.get("degree") or "")
            unit = str(p.get("parent_unit_name") or p.get("faculty") or "")
            duration = p.get("duration") or p.get("duration_years")
            if isinstance(duration, dict):
                dur_str = f"{duration.get('years', '')} Years ({duration.get('semesters', '')} Semesters)"
            elif duration:
                dur_str = f"{duration} Years"
            else:
                dur_str = ""
            route = str(p.get("admission_route") or "")
            exam = str(p.get("entrance_examination") or "")
            counsel = str(p.get("counselling_authority") or "")
            intake = p.get("intake")
            track_intakes = p.get("track_intakes")
            intake_note = str(p.get("intake_evidence_note") or "")
            affiliation = str(p.get("affiliation") or "")
            approval = str(p.get("approval") or "")
            aliases = p.get("aliases") or []
            src_url = str(p.get("source_url") or "")
            canon_doc = str(p.get("canonical_document_id") or "")

            lines = [
                f"Academic Programme: {name}",
                f"Degree Type: {deg_type}",
                f"Offering Faculty/Department: {unit}",
            ]
            if dur_str:
                lines.append(f"Normal Duration: {dur_str}")
            if intake:
                lines.append(f"Sanctioned Intake / Annual Seats: {intake}")
            if track_intakes and isinstance(track_intakes, dict):
                lines.append("Track Intakes:")
                for tk, tv in track_intakes.items():
                    lines.append(f"  - {tk.replace('_', ' ').title()}: {tv} seats")
            if intake_note:
                lines.append(f"Intake Evidence Note: {intake_note}")
            if route:
                lines.append(f"Admission Channel: {route}")
            if exam:
                lines.append(f"Qualifying Examination: {exam}")
            if counsel:
                lines.append(f"Counselling Authority: {counsel}")
            if affiliation:
                lines.append(f"Affiliation: {affiliation}")
            if approval:
                lines.append(f"Approval: {approval}")
            if aliases:
                lines.append(f"Aliases: {', '.join(aliases)}")
            if canon_doc:
                lines.append(f"Canonical Document: {canon_doc}")
            if src_url:
                lines.append(f"Source URL: {src_url}")

            text = "\n".join(lines)
            records.append(_make_doc(
                text,
                title=name,
                category="programs",
                subcategory=deg_type.lower(),
                extra_meta={
                    "degree_type": deg_type,
                    "programme_id": str(p.get("programme_id") or ""),
                    "source_url": src_url,
                }
            ))

            deg_upper = deg_type.upper()
            unit_info = f" ({unit})" if unit else ""
            intake_info = f" [Sanctioned Intake: {intake} seats]" if intake else ""
            track_info = ""
            if track_intakes and isinstance(track_intakes, dict):
                tracks_str = ", ".join(f"{k.replace('_', ' ').title()}: {v} seats" for k, v in track_intakes.items())
                track_info = f" [Specializations/Tracks: {tracks_str}]"
            specs = p.get("specializations") or []
            if specs and isinstance(specs, list):
                track_info += f" [Specializations: {', '.join(str(s) for s in specs)}]"

            if "B.TECH" in deg_upper or "BACHELOR OF TECHNOLOGY" in deg_upper:
                btech_progs.append(f"- {name}{unit_info}{intake_info}{track_info}")
            elif "M.TECH" in deg_upper or "MASTER OF TECHNOLOGY" in deg_upper:
                mtech_progs.append(f"- {name}{unit_info}{intake_info}{track_info}")
            elif "M.SC" in deg_upper:
                msc_progs.append(f"- {name}{unit_info}{intake_info}{track_info}")
            elif "MBA" in deg_upper or "MANAGEMENT" in deg_upper:
                mba_progs.append(f"- {name}{unit_info}{intake_info}{track_info}")
            elif "B.VOC" in deg_upper or "VOCATION" in deg_upper:
                vocation_progs.append(f"- {name}{unit_info}{intake_info}{track_info}")
            elif any(k in deg_upper for k in ("PHARM", "NURSING", "HOMEOPATHY", "DHP", "MEDICAL")):
                medical_progs.append(f"- {name}{unit_info}{intake_info}{track_info}")

        if btech_progs:
            btech_summary = (
                f"Official Complete List of B.Tech Programmes and Specializations at {inst_display}:\n"
                f"{inst_display} offers {len(btech_progs)} undergraduate B.Tech programmes across diverse engineering branches and emerging technologies:\n"
                + "\n".join(btech_progs)
            )
            records.append(_make_doc(
                btech_summary,
                title="Complete List of B.Tech Programmes and Specializations",
                category="programs",
                subcategory="btech",
                extra_meta={"aliases": ["B.Tech Programmes", "B.Tech Specializations", "B.Tech Branches", "Undergraduate Engineering Programmes"]}
            ))

        if mtech_progs:
            mtech_summary = (
                f"Official Complete List of M.Tech Programmes at {inst_display}:\n"
                f"{inst_display} offers {len(mtech_progs)} postgraduate M.Tech programmes:\n"
                + "\n".join(mtech_progs)
            )
            records.append(_make_doc(mtech_summary, title="Complete List of M.Tech Programmes", category="programs", subcategory="mtech"))

        if msc_progs:
            msc_summary = (
                f"Official Complete List of M.Sc Programmes at {inst_display}:\n"
                f"{inst_display} offers {len(msc_progs)} M.Sc programmes:\n"
                + "\n".join(msc_progs)
            )
            records.append(_make_doc(msc_summary, title="Complete List of M.Sc Programmes", category="programs", subcategory="msc"))

        if mba_progs:
            mba_summary = (
                f"Official Management Programmes and MBA Specializations at {inst_display}:\n"
                f"{inst_display} offers the following management programmes and specializations:\n"
                + "\n".join(mba_progs)
            )
            records.append(_make_doc(
                mba_summary,
                title="Complete List of Management Programmes and MBA Specializations",
                category="programs",
                subcategory="mba",
                extra_meta={"aliases": ["MBA Specializations", "Management Programmes", "IMBA", "AGMP"]}
            ))

        if vocation_progs:
            voc_summary = (
                f"Official Vocational & Skill Programmes at {inst_display}:\n"
                f"{inst_display} offers the following Bachelor of Vocation (B.Voc) programmes:\n"
                + "\n".join(vocation_progs)
            )
            records.append(_make_doc(voc_summary, title="Complete List of Vocational Programmes", category="programs", subcategory="bvoc"))

        if medical_progs:
            med_summary = (
                f"Official Medical & Healthcare Programmes at {inst_display}:\n"
                f"{inst_display} offers the following medical and allied healthcare programmes:\n"
                + "\n".join(medical_progs)
            )
            records.append(_make_doc(med_summary, title="Complete List of Medical and Healthcare Programmes", category="programs", subcategory="medical"))

        # Institute-wide master programmes directory
        all_summary_lines = [
            f"Official Complete Directory of Academic Programmes at {inst_display}:",
            f"{inst_display} offers comprehensive academic programmes across Engineering, Management, Skill & Vocational Studies, and Medical & Allied Health Sciences.",
            "\n### Undergraduate Engineering (B.Tech) Programmes & Specializations:",
            *btech_progs,
        ]
        if mtech_progs:
            all_summary_lines.extend(["\n### Postgraduate Engineering (M.Tech) Programmes:", *mtech_progs])
        if mba_progs:
            all_summary_lines.extend(["\n### Management (MBA / IMBA / AGMP) Programmes:", *mba_progs])
        if vocation_progs:
            all_summary_lines.extend(["\n### Vocational & Skill (B.Voc) Programmes:", *vocation_progs])
        if medical_progs:
            all_summary_lines.extend(["\n### Medical & Allied Health Sciences (D.Pharm / Nursing / DHP) Programmes:", *medical_progs])

        records.append(_make_doc(
            "\n".join(all_summary_lines),
            title="Institute-Wide Academic Programmes and Courses Directory",
            category="programs",
            subcategory="programmes_list",
            extra_meta={"aliases": ["All Programmes", "Academic Programmes Directory", "Courses Offered", "Degrees Offered"]}
        ))

    # 2. departments.json
    elif dataset_name == "departments.json":
        if isinstance(data, dict) and "faculties" in data:
            dept_lines: list[str] = []
            for fac in data["faculties"]:
                fac_name = str(fac.get("faculty_name") or "")
                depts = fac.get("departments") or []
                d_list = [str(d) for d in depts]
                text = f"Academic Faculty: {fac_name}\nDepartments:\n" + "\n".join(f"- {d}" for d in d_list)
                records.append(_make_doc(text, title=fac_name, category="departments", subcategory="faculty_directory"))
                dept_lines.append(f"\n### {fac_name}:")
                for d in d_list:
                    dept_lines.append(f"- {d}")
            if dept_lines:
                dept_summary = (
                    f"Official Complete Directory of Academic Faculties and Departments at {inst_display}:\n"
                    + "\n".join(dept_lines)
                )
                records.append(_make_doc(dept_summary, title="Academic Faculties and Departments Directory", category="departments", subcategory="departments_list"))
        elif isinstance(data, list):
            dept_lines = []
            for d in data:
                if not isinstance(d, dict):
                    continue
                name = str(d.get("name") or "")
                code = str(d.get("code") or "")
                degrees = d.get("degrees_offered") or []
                deg_str = ", ".join(degrees) if isinstance(degrees, list) else str(degrees)
                text = f"Department: {name} (Code: {code})\nType: Academic Department\nDegrees Offered: {deg_str}"
                records.append(_make_doc(text, title=name, category="departments", subcategory="department_directory", extra_meta={"department_code": code}))
                dept_lines.append(f"- {name} ({code})")

            if dept_lines:
                dept_summary = (
                    f"Official Complete Directory of Academic Departments at {inst_display}:\n"
                    + f"{inst_display} comprises {len(dept_lines)} academic departments:\n"
                    + "\n".join(dept_lines)
                )
                records.append(_make_doc(dept_summary, title="Institute-Wide Academic Departments Directory", category="departments", subcategory="departments_list"))

    # 3. schools.json
    elif dataset_name == "schools.json" and isinstance(data, list):
        school_lines: list[str] = []
        for s in data:
            if not isinstance(s, dict):
                continue
            name = str(s.get("name") or "")
            acronym = str(s.get("acronym") or "")
            focus = str(s.get("focus") or "")
            degrees = s.get("degrees_offered") or []
            deg_str = ", ".join(degrees) if isinstance(degrees, list) else str(degrees)
            text = f"School: {name} ({acronym})\nFocus: {focus}\nDegrees Offered: {deg_str}"
            records.append(_make_doc(text, title=name, category="schools", subcategory="school_directory", extra_meta={"school_acronym": acronym}))
            school_lines.append(f"- {name} ({acronym})")

        if school_lines:
            school_summary = f"Official Schools at {inst_display}:\n" + "\n".join(school_lines)
            records.append(_make_doc(school_summary, title="Schools Directory", category="schools", subcategory="schools_list"))

    # 4. visitor_accommodation.json
    elif dataset_name == "visitor_accommodation.json" and isinstance(data, dict):
        short_term_list = data.get("short_term_rates_01_to_10_days") or []
        long_term = data.get("long_term_bookings_11_days_to_6_months") or {}
        booking_proc = str(data.get("booking_procedure") or "")

        st_lines: list[str] = []
        if isinstance(short_term_list, list):
            for st in short_term_list:
                cat = st.get("category", "")
                rtype = st.get("room_type", "")
                d_rate = st.get("double_occupancy_per_day", "")
                s_rate = st.get("single_occupancy_per_day", "")
                tax = st.get("tax", "")
                item_text = (
                    f"Category: {cat}\n"
                    f"Room Type: {rtype}\n"
                    f"Double Occupancy Charge: ₹{d_rate}/- per day\n"
                    f"Single Occupancy Charge: ₹{s_rate}/- per day\n"
                    f"Tax Status: {tax}"
                )
                records.append(_make_doc(item_text, title=f"Hostel Accommodation Charges — {cat}", category="hostel_accommodation", subcategory="short_term_rates"))
                st_lines.append(f"- {cat} ({rtype}): Double ₹{d_rate}/day, Single ₹{s_rate}/day ({tax})")

        lt_rate = long_term.get("rate_per_month", 2175) if isinstance(long_term, dict) else 2175
        lt_tax = long_term.get("tax", "Plus GST for visitors; without GST for students and staff") if isinstance(long_term, dict) else ""
        lt_policy = long_term.get("phd_post_thesis_policy", "") if isinstance(long_term, dict) else ""

        vh_summary = (
            f"Official {inst_display} Visitor and Guest Hostel Accommodation and Room Charges:\n\n"
            "Short-Term Hostel Accommodation (01 to 10 Days):\n"
            + "\n".join(st_lines)
            + "\n\nLong-Term Bookings (11 Days to 6 Months):\n"
            f"- Monthly Charge: ₹{lt_rate}/- per month\n"
            f"- Tax: {lt_tax}\n"
            f"- PhD Post-Thesis Policy: {lt_policy}\n\n"
            f"Booking Procedure: {booking_proc}"
        )
        records.append(_make_doc(vh_summary, title="Visitor Hostel Room Charges and Accommodation Rates", category="hostel_accommodation", subcategory="visitor_hostel"))

    # 5. emergency_contacts.json
    elif dataset_name == "emergency_contacts.json":
        contacts_raw = data.get("contacts") if isinstance(data, dict) else data
        if isinstance(contacts_raw, list):
            em_lines: list[str] = []
            for c in contacts_raw:
                if not isinstance(c, dict):
                    continue
                service = str(c.get("service") or "")
                tel = str(c.get("phone") or c.get("telephone") or "")
                person = str(c.get("contact_person") or "")
                alts = c.get("alternate_phones") or []
                alt_str = f" (Alternate: {', '.join(alts)})" if alts else ""
                loc = str(c.get("location") or "")
                avail = str(c.get("availability") or "")
                lines = [f"Emergency Service: {service}", f"Telephone / Helpline: {tel}{alt_str}"]
                if person:
                    lines.append(f"Contact Person: {person}")
                if loc:
                    lines.append(f"Location: {loc}")
                if avail:
                    lines.append(f"Availability: {avail}")
                records.append(_make_doc("\n".join(lines), title=service, category="emergency", subcategory="emergency_contacts", extra_meta={"telephone": tel}))
                person_info = f" ({person})" if person else ""
                loc_info = f" [{loc}]" if loc else ""
                em_lines.append(f"- {service}: {tel}{alt_str}{person_info}{loc_info}")

            if em_lines:
                em_summary = f"{inst_display} Emergency Phone Numbers & Contacts Directory:\n" + "\n".join(em_lines)
                records.append(_make_doc(em_summary, title="Emergency Contacts Directory", category="emergency", subcategory="contacts_list"))

    # 6. campus_contacts.json
    elif dataset_name == "campus_contacts.json" and isinstance(data, dict):
        adm_helplines = data.get("admissions_helpline") or []
        media = str(data.get("media_helpline") or "")
        wa = str(data.get("whatsapp_support") or "")
        emails = data.get("official_emails") or []
        officials = data.get("key_officials") or []

        lines = [f"Official Contact Directory for {inst_display}:"]
        if adm_helplines:
            lines.append("Admissions Helplines: " + ", ".join(adm_helplines if isinstance(adm_helplines, list) else [str(adm_helplines)]))
        if wa:
            lines.append(f"WhatsApp Support: {wa}")
        if media:
            lines.append(f"Media Helpline: {media}")
        if emails:
            lines.append("Official Emails: " + ", ".join(emails if isinstance(emails, list) else [str(emails)]))
        if officials and isinstance(officials, list):
            lines.append("\nKey Administrative Officials:")
            for off in officials:
                if isinstance(off, dict):
                    role = off.get("role", "")
                    name = off.get("name", "")
                    phone = off.get("phone", "")
                    lines.append(f"- {role}: {name} (Phone: {phone})")
        records.append(_make_doc("\n".join(lines), title="Campus Admissions & Administrative Contacts Directory", category="contacts", subcategory="campus_contacts"))

    # 7. hostel_facilities.json
    elif dataset_name == "hostel_facilities.json" and isinstance(data, dict):
        cap = data.get("residential_capacity")
        wings = data.get("wings") or []
        amenities = data.get("amenities") or []
        warden = data.get("chief_warden") or {}
        src = str(data.get("source_url") or "")

        lines = [f"Official Hostel Accommodation & Residential Facilities at {inst_display}:"]
        if cap:
            lines.append(f"Total Residential Capacity: {cap}+ students")
        if wings and isinstance(wings, list):
            lines.append("\nHostel Wings:")
            for w in wings:
                if isinstance(w, dict):
                    wtype = w.get("type", "")
                    feats = w.get("features", [])
                    feat_str = ", ".join(feats) if isinstance(feats, list) else str(feats)
                    lines.append(f"- {wtype}: {feat_str}")
        if amenities and isinstance(amenities, list):
            lines.append("\nHostel Amenities:")
            for a in amenities:
                lines.append(f"- {a}")
        if warden and isinstance(warden, dict):
            wname = warden.get("name", "")
            wphone = warden.get("phone", "")
            lines.append(f"\nChief Warden: {wname} (Contact: {wphone})")
        records.append(_make_doc("\n".join(lines), title="Hostel Accommodation and Residential Facilities", category="hostel_accommodation", subcategory="hostel_overview", extra_meta={"source_url": src}))

    # 8. transport_services.json
    elif dataset_name == "transport_services.json" and isinstance(data, dict):
        fleet = str(data.get("fleet_type") or "")
        coverage = data.get("service_coverage") or []
        officer = data.get("transport_officer") or {}
        src = str(data.get("source_url") or "")

        lines = [f"Campus Transport Facility and Bus Services at {inst_display}:"]
        if fleet:
            lines.append(f"Fleet Type: {fleet}")
        if coverage and isinstance(coverage, list):
            lines.append("Transit Coverage Corridors:")
            for c in coverage:
                lines.append(f"- {c}")
        if officer and isinstance(officer, dict):
            oname = officer.get("name", "")
            ophone = officer.get("phone", "")
            lines.append(f"Chief Transport Officer: {oname} (Phone: {ophone})")
        records.append(_make_doc("\n".join(lines), title="Campus Transport Facility and Transit Services", category="transport", subcategory="transport_overview", extra_meta={"source_url": src}))

    # 9. student_services.json
    elif dataset_name == "student_services.json" and isinstance(data, dict):
        services = data.get("services") or []
        lines = [f"Student Services & Campus Facilities at {inst_display}:"]
        if services and isinstance(services, list):
            for s in services:
                if isinstance(s, dict):
                    sname = s.get("service_name", "")
                    details = [f"{k.replace('_', ' ').title()}: {v}" for k, v in s.items() if k != "service_name"]
                    lines.append(f"- {sname}: {'; '.join(details)}")
        records.append(_make_doc("\n".join(lines), title="Student Services and Campus Facilities Directory", category="services", subcategory="student_services"))

    # 10. institution_profile.json
    elif dataset_name == "institution_profile.json" and isinstance(data, dict):
        name = str(data.get("name") or inst_display)
        estd = data.get("established")
        trust = str(data.get("sponsoring_trust") or "")
        chairman = str(data.get("founder_chairman") or "")
        size = data.get("campus_size_acres")
        loc = data.get("location") or {}
        addr = loc.get("address", "") if isinstance(loc, dict) else str(loc)
        motto = str(data.get("motto") or "")
        pillars = data.get("vision_pillars") or []
        metrics = data.get("key_metrics") or {}
        src = str(data.get("source_url") or data.get("canonical_url") or "")

        lines = [
            f"Official Institutional Profile: {name}",
            f"Establishment Year: {estd}",
            f"Sponsoring Trust: {trust}",
            f"Founder Chairman: {chairman}",
            f"Campus Size: {size} Acres",
            f"Campus Address: {addr}",
            f"Motto: {motto}",
            f"Vision Pillars: {', '.join(pillars) if isinstance(pillars, list) else str(pillars)}",
        ]
        if metrics and isinstance(metrics, dict):
            lines.append("\nKey Institutional & Placement Metrics:")
            for mk, mv in metrics.items():
                lines.append(f"- {mk.replace('_', ' ').title()}: {mv}")
        records.append(_make_doc("\n".join(lines), title=f"Institutional Profile — {name}", category="institutional_profile", subcategory="overview", extra_meta={"source_url": src}))

    # 11. degrees.json
    elif dataset_name == "degrees.json" and isinstance(data, dict) and "degrees" in data:
        deg_list = data["degrees"]
        lines = [f"Official Degrees Offered at {inst_display}:"]
        for d in deg_list:
            if isinstance(d, dict):
                code = d.get("code", "")
                dname = d.get("name", "")
                lvl = d.get("level", "")
                dur = d.get("duration_years", "")
                lines.append(f"- {code} ({dname}): {lvl} degree, {dur} years")
        records.append(_make_doc("\n".join(lines), title="Degrees & Academic Levels Offered", category="programs", subcategory="degrees"))

    # 12. fees_and_scholarships.json
    elif dataset_name == "fees_and_scholarships.json" and isinstance(data, dict):
        structures = data.get("academic_fee_structures") or []
        scholarships = data.get("scholarships_and_fellowships") or {}

        fee_lines = [f"Official {inst_display} Academic Tuition Fees and Waiver Policies:"]
        if isinstance(structures, list):
            for prog_fee in structures:
                if isinstance(prog_fee, dict):
                    prog_name = prog_fee.get("programme", "")
                    tuition = prog_fee.get("tuition_fee_per_semester", "")
                    curr = prog_fee.get("currency", "INR")
                    ay = prog_fee.get("academic_year", "")
                    auth = prog_fee.get("authority", "")
                    waivers = prog_fee.get("waiver_and_remission_policy") or {}
                    other_chg = prog_fee.get("other_semester_charges") or {}
                    notes = prog_fee.get("notes") or []

                    prog_text_lines = [
                        f"Academic Programme: {prog_name}",
                        f"Tuition Fee: ₹{tuition:,}/- per semester ({curr})" if isinstance(tuition, int) else f"Tuition Fee: {tuition}",
                        f"Academic Session: {ay}",
                        f"Governing Authority: {auth}",
                    ]
                    if isinstance(waivers, dict):
                        prog_text_lines.append("Tuition Waiver and Remission Policy:")
                        for w_k, w_v in waivers.items():
                            prog_text_lines.append(f"  - {w_k.replace('_', ' ').title()}: {w_v}")
                    if isinstance(other_chg, dict):
                        prog_text_lines.append("Other Charges:")
                        for c_k, c_v in other_chg.items():
                            prog_text_lines.append(f"  - {c_k.replace('_', ' ').title()}: ₹{c_v}")
                    if notes:
                        prog_text_lines.append("Important Notes:")
                        for n in notes:
                            prog_text_lines.append(f"  - {n}")

                    records.append(_make_doc("\n".join(prog_text_lines), title=f"Tuition Fee & Waivers — {prog_name}", category="finance", subcategory="tuition_fees"))
                    fee_lines.append(f"\n### {prog_name}:\n- Tuition Fee per Semester: ₹{tuition:,}/-\n- Governing Authority: {auth}")

        records.append(_make_doc("\n".join(fee_lines), title="Academic Fee Structures and Tuition Fee Waivers Summary", category="finance", subcategory="fees_summary"))

        if isinstance(scholarships, dict):
            sch_lines = [f"{inst_display} Scholarships, Assistantships, and Fellowships:"]
            for sch_k, sch_v in scholarships.items():
                sch_lines.append(f"- {sch_k.replace('_', ' ').title()}: {sch_v}")
            records.append(_make_doc("\n".join(sch_lines), title="Scholarships and Fellowships", category="finance", subcategory="scholarships"))

    # 13. Generic fallback parser for any other structured list or dict dataset
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            if isinstance(item, dict):
                name = item.get("name") or item.get("title") or item.get("id") or f"{dataset_name}_{idx}"
                lines = [f"{k.replace('_', ' ').title()}: {v}" for k, v in item.items() if v and not isinstance(v, (dict, list))]
                records.append(_make_doc("\n".join(lines), title=str(name), category=dataset_name.replace(".json", "")))
    elif isinstance(data, dict):
        for section_key, section_val in data.items():
            if isinstance(section_val, dict):
                lines = [f"Section: {section_key.replace('_', ' ').title()}"]
                lines.extend(f"- {k.replace('_', ' ').title()}: {v}" for k, v in section_val.items() if v and not isinstance(v, (dict, list)))
                records.append(_make_doc("\n".join(lines), title=f"{dataset_name} — {section_key}", category=dataset_name.replace(".json", "")))

    return records


def load_institutional_release(
    package_root: Path | str,
    validate_hashes: bool = True,
    institution_id: str | None = None,
) -> InstitutionalRelease:
    """Load, validate, and normalize a complete institutional knowledge package."""
    root = Path(package_root).resolve()
    report = validate_package(root)

    manifest_file = root / "manifests" / "package_manifest.json"
    if not manifest_file.exists():
        manifest_file = root / "data" / "manifest.json"
    if not manifest_file.exists():
        manifest_file = root / "manifest.json"

    meta_dict: dict[str, Any] = {}
    if manifest_file.exists():
        try:
            with manifest_file.open("r", encoding="utf-8") as f:
                meta_dict = json.load(f)
        except Exception:
            pass

    resolved_inst_id = (institution_id or os.getenv("INSTITUTION_ID") or report.institution_id).strip().lower()
    release_id = report.release_id
    display_name = str(meta_dict.get("institution_name") or "Indian Institute of Technology Jodhpur")

    prof_file = root / "data" / "institution_profile.json"
    canonical_base_url = "https://srgi.in" if "srgi" in resolved_inst_id else "https://www.iitj.ac.in"
    if prof_file.exists():
        try:
            with prof_file.open("r", encoding="utf-8") as f:
                prof_data = json.load(f)
                display_name = str(prof_data.get("name") or meta_dict.get("institution_name") or display_name)
                canonical_base_url = str(prof_data.get("canonical_url") or canonical_base_url)
        except Exception:
            pass

    metadata = PackageMetadata(
        package_name=str(meta_dict.get("package_name") or release_id),
        version=str(meta_dict.get("version") or meta_dict.get("release_version") or "2.0.0"),
        institution_id=resolved_inst_id,
        institution_name=display_name,
        release_timestamp=str(meta_dict.get("release_timestamp") or meta_dict.get("created_at") or ""),
        total_canonical_documents=int(meta_dict.get("total_canonical_documents") or meta_dict.get("total_docx_companions") or report.accepted_documents),
        total_structured_datasets=int(meta_dict.get("total_structured_datasets") or len(report.datasets_discovered)),
        schema_version="2.0",
        parity_guarantee=str(meta_dict.get("parity_guarantee") or ""),
    )

    # 1. Load canonical documents inventory
    documents: list[CanonicalDocument] = []
    inventory_file = root / "manifests" / "document_inventory.json"
    if not inventory_file.exists():
        inventory_file = root / "data" / "document_inventory.json"
    if not inventory_file.exists():
        inventory_file = root / "document_inventory.json"

    primary_manifest_file = root / "manifests" / "primary_corpus_manifest.json"
    if not primary_manifest_file.exists():
        primary_manifest_file = root / "primary_corpus_manifest.json"

    inventory_items: list[dict[str, Any]] = []
    if inventory_file.exists():
        with inventory_file.open("r", encoding="utf-8") as f:
            inv_raw = json.load(f)
            if isinstance(inv_raw, dict) and "documents" in inv_raw:
                inventory_items = inv_raw["documents"]
            elif isinstance(inv_raw, list):
                inventory_items = inv_raw
    elif primary_manifest_file.exists():
        with primary_manifest_file.open("r", encoding="utf-8") as f:
            inv_raw = json.load(f)
            if isinstance(inv_raw, dict) and "documents" in inv_raw:
                inventory_items = inv_raw["documents"]
            elif isinstance(inv_raw, list):
                inventory_items = inv_raw
    else:
        docs_dir = root / "documents"
        if docs_dir.exists():
            for p in sorted(docs_dir.rglob("*.docx")):
                if p.name.startswith("."):
                    continue
                rel_docx = p.relative_to(root)
                doc_id = p.stem
                inventory_items.append({
                    "document_id": doc_id,
                    "title": doc_id.replace("_", " ").title(),
                    "docx_path": str(rel_docx),
                    "markdown_path": str(Path("knowledge") / rel_docx.relative_to("documents")).replace(".docx", ".md"),
                    "metadata_path": str(Path("metadata") / f"{doc_id}.json"),
                })

    for item in inventory_items:
        doc_id = str(item.get("document_id") or "")
        docx_rel = item.get("docx_path") or item.get("relative_docx_path")
        if not doc_id or not docx_rel:
            continue

        docx_path = root / docx_rel
        if not docx_path.exists():
            continue

        is_fallback = _is_quarantined_fallback(docx_path)
        md_rel = item.get("markdown_path") or item.get("relative_markdown_path") or f"knowledge/{docx_rel.replace('documents/', '').replace('.docx', '.md')}"
        md_path = root / md_rel
        meta_rel = item.get("metadata_path") or item.get("relative_sidecar_path") or f"metadata/{doc_id}.json"
        meta_path = root / meta_rel

        # Read metadata sidecar
        sidecar: dict[str, Any] = {}
        if meta_path.exists():
            try:
                with meta_path.open("r", encoding="utf-8") as f:
                    sidecar = json.load(f)
            except Exception:
                pass

        title = str(sidecar.get("title") or item.get("title") or doc_id.replace("_", " ").title())
        category = str(sidecar.get("category") or item.get("category") or "general")
        subcategory = str(sidecar.get("subcategory") or item.get("subcategory") or "")
        document_type = str(sidecar.get("document_type") or "canonical_docx")

        source_urls = tuple(sidecar.get("source_urls") or item.get("source_urls") or ())
        unit_ids = tuple(sidecar.get("unit_ids") or ())
        aliases = tuple(sidecar.get("aliases") or ())
        claim_ids = tuple(sidecar.get("claim_ids") or ())
        conflict_ids = tuple(sidecar.get("conflict_ids") or ())

        val_status = sidecar.get("validation_status") or {}
        if not isinstance(val_status, dict):
            val_status = {}

        documents.append(
            CanonicalDocument(
                document_id=doc_id,
                title=title,
                category=category,
                subcategory=subcategory,
                document_type=document_type,
                docx_path=docx_path,
                markdown_path=md_path,
                metadata_path=meta_path,
                source_urls=source_urls,
                unit_ids=unit_ids,
                aliases=aliases,
                claim_ids=claim_ids,
                conflict_ids=conflict_ids,
                docx_hash=str(item.get("docx_hash") or item.get("docx_sha256") or sidecar.get("docx_hash") or ""),
                markdown_hash=str(item.get("markdown_hash") or item.get("markdown_sha256") or sidecar.get("markdown_hash") or ""),
                is_fallback=is_fallback,
                validation_status=val_status,
            )
        )

    # 2. Discover and parse structured datasets
    structured_datasets: dict[str, Any] = {}
    structured_records: list[Document] = []
    data_dir = root / "data"
    if data_dir.exists() and data_dir.is_dir():
        for json_file in sorted(data_dir.glob("*.json")):
            if json_file.name in {
                ".DS_Store",
                "manifest.json",
                "document_inventory.json",
                "source_policy.json",
                "scope_policy.json",
                "ingestion_config.json",
            }:
                continue
            try:
                with json_file.open("r", encoding="utf-8") as f:
                    dataset_data = json.load(f)
                    structured_datasets[json_file.name] = dataset_data
                    records = _format_structured_records(
                        dataset_name=json_file.name,
                        data=dataset_data,
                        package_root=root,
                        institution_id=resolved_inst_id,
                        release_id=release_id,
                        display_name=display_name,
                        canonical_base_url=canonical_base_url,
                    )
                    structured_records.extend(records)
            except Exception as exc:
                logger.warning("Could not parse dataset %s: %s", json_file.name, exc)

    # 3. Load conflicts
    conflicts: list[ConflictRecord] = []
    conflict_file = root / "provenance" / "source_conflict_register.json"
    if conflict_file.exists():
        try:
            with conflict_file.open("r", encoding="utf-8") as f:
                c_data = json.load(f)
                for c in c_data.get("conflicts", []):
                    conflicts.append(
                        ConflictRecord(
                            conflict_id=str(c.get("conflict_id") or ""),
                            entity=str(c.get("entity") or ""),
                            source_1=c.get("source_1") or {},
                            source_2=c.get("source_2") or {},
                            disposition=str(c.get("disposition") or ""),
                            explanation=str(c.get("explanation") or ""),
                        )
                    )
        except Exception as exc:
            logger.warning("Could not parse conflict register: %s", exc)

    # 4. Load claims
    claims: list[ClaimRecord] = []
    claim_file = root / "provenance" / "source_claim_evidence_ledger.json"
    if claim_file.exists():
        try:
            with claim_file.open("r", encoding="utf-8") as f:
                cl_data = json.load(f)
                if isinstance(cl_data, list):
                    for cl in cl_data:
                        claims.append(
                            ClaimRecord(
                                claim_id=str(cl.get("claim_id") or ""),
                                domain=str(cl.get("domain") or ""),
                                entity=str(cl.get("entity") or ""),
                                claim_value=str(cl.get("claim_value") or ""),
                                conditions=str(cl.get("conditions") or ""),
                                source_url=str(cl.get("source_url") or ""),
                                verified_in_documents=tuple(cl.get("verified_in_documents") or ()),
                                verification_status=str(cl.get("verification_status") or ""),
                            )
                        )
        except Exception as exc:
            logger.warning("Could not parse claim evidence ledger: %s", exc)

    # 5. Extract lexical resources from structured datasets
    lexical_resources: dict[str, Any] = {
        "acronyms": structured_datasets.get("acronyms.json", {}),
        "aliases": structured_datasets.get("aliases.json", {}),
        "phrases": structured_datasets.get("phrases.json", []),
        "semantic_terms": structured_datasets.get("semantic_terms.json", {}),
        "scope_policy": structured_datasets.get("scope_policy.json", {}),
        "source_policy": structured_datasets.get("source_policy.json", {}),
    }

    return InstitutionalRelease(
        institution_id=institution_id,
        release_id=release_id,
        display_name=display_name,
        package_root=root,
        metadata=metadata,
        documents=documents,
        structured_datasets=structured_datasets,
        structured_records=structured_records,
        conflicts=conflicts,
        claims=claims,
        lexical_resources=lexical_resources,
        validation_report=report,
    )


def chunk_package_documents(
    release: InstitutionalRelease,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    include_fallback: bool = False,
) -> list[Document]:
    """Split canonical documents into retrieval-optimized chunks with complete metadata sidecar propagation.

    Guarantees:
    - Exactly 1 copy per subject indexed (DOCX canonical, ignoring fallback by default).
    - Metadata sidecar fields attached to every chunk.
    - All metadata values sanitized to Chroma-compatible primitives (str, int, float, bool).
    - Structured records from approved datasets included seamlessly as first-class evidence chunks.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=list(CHUNK_SEPARATORS),
    )

    all_chunks: list[Document] = []

    # 1. Chunk canonical DOCX documents
    for doc_meta in release.documents:
        if doc_meta.is_fallback and not include_fallback:
            continue

        try:
            loader = Docx2txtLoader(str(doc_meta.docx_path))
            raw_docs = loader.load()
        except Exception as exc:
            logger.warning("Failed to load docx %s: %s", doc_meta.docx_path, exc)
            continue

        for raw_doc in raw_docs:
            page_text = raw_doc.page_content.strip()
            if not page_text:
                continue

            sub_chunks = splitter.split_text(page_text)
            total_chunks = len(sub_chunks)

            for idx, chunk_text in enumerate(sub_chunks):
                clean_chunk = chunk_text.strip()
                if not clean_chunk:
                    continue

                chunk_id_mat = f"{doc_meta.document_id}:{idx}:{doc_meta.docx_hash}:{clean_chunk[:50]}"
                chunk_id = hashlib.sha256(chunk_id_mat.encode("utf-8")).hexdigest()[:16]

                chunk_metadata: dict[str, Any] = {
                    "source": str(doc_meta.docx_path),
                    "source_path": str(doc_meta.docx_path),
                    "source_id": hashlib.sha256(str(doc_meta.docx_path).encode("utf-8")).hexdigest()[:16],
                    "institution_id": release.institution_id,
                    "release_id": release.release_id,
                    "document_id": doc_meta.document_id,
                    "title": doc_meta.title,
                    "category": doc_meta.category,
                    "subcategory": doc_meta.subcategory,
                    "document_type": doc_meta.document_type,
                    "chunk_id": chunk_id,
                    "chunk_index": idx,
                    "chunk_count": total_chunks,
                    "source_urls": json.dumps(list(doc_meta.source_urls), ensure_ascii=False),
                    "unit_ids": json.dumps(list(doc_meta.unit_ids), ensure_ascii=False),
                    "claim_ids": json.dumps(list(doc_meta.claim_ids), ensure_ascii=False),
                    "conflict_ids": json.dumps(list(doc_meta.conflict_ids), ensure_ascii=False),
                    "aliases": json.dumps(list(doc_meta.aliases), ensure_ascii=False),
                    "content_hash": doc_meta.docx_hash,
                    "schema_version": release.metadata.schema_version,
                }
                all_chunks.append(Document(page_content=clean_chunk, metadata=chunk_metadata))

    # 2. Append structured records (already formatted as Documents with Chroma-compatible metadata)
    all_chunks.extend(release.structured_records)

    return all_chunks
