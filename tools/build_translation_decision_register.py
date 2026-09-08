"""Project the Pashto review ledger into the canonical OpenLogic contract.

The projection is reversible: accepted translations and the historical review
ledger remain unchanged.  It pairs every decision occurrence with an exact
aligned source/target semantic segment, byte span, line span, and file hash.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


REPO = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = REPO / "evidence"
SCHEMA_VERSION = "openlogic-translation-decisions/1.0.0"
SOURCE_REVISION = "9620cc73f9c8e0ad003c514a5d3748f29611c4c0"

EDITION = {
    "edition_id": "openlogic-ps-Arab-PK",
    "language_tag": "ps-Arab-PK",
    "language_name": "Pashto",
    "script": "Arab",
    "territory": "PK",
    "locale": "ps-Arab-PK",
    "register_or_variant": (
        "Pakistani Pashto scholarly register; Afghan Pashto is cited only as a labelled regional comparator"
    ),
    "notation_profile": "RTL Pashto prose with LTR OpenLogic mathematics and proof diagrams",
    "layer_type": "semantic_translation",
    "parent_semantic_edition_id": None,
}

PART_AND_CHAPTER = {
    "sets": ("سټونه، تابعې او اړيکې", "سټونه"),
    "relations": ("سټونه، تابعې او اړيکې", "اړيکې"),
    "functions": ("سټونه، تابعې او اړيکې", "تابعې"),
    "size-of-sets": ("سټونه، تابعې او اړيکې", "د سټونو کچه"),
    "arithmetization": ("سټونه، تابعې او اړيکې", "د شمېر نظامونو سټ‌تيوري جوړښت"),
    "infinite": ("سټونه، تابعې او اړيکې", "لامتناهي سټونه"),
    "syntax-and-semantics": ("بياني منطق", "بياني نحو او معناپوهنه"),
    "proof-systems": ("د لومړۍ درجې منطق", "د اشتقاق نظامونه"),
    "sequent-calculus": ("د لومړۍ درجې منطق", "د سېکوېنټ حساب"),
    "natural-deduction": ("د لومړۍ درجې منطق", "فطري استنتاج"),
    "tableaux": ("د لومړۍ درجې منطق", "تابلوګانې"),
    "axiomatic-deduction": ("د لومړۍ درجې منطق", "بديهي اشتقاق"),
    "models-theories": ("د لومړۍ درجې منطق", "مدلونه او تيورۍ"),
    "beyond": ("د لومړۍ درجې منطق", "د لومړۍ درجې له منطق څخه وړاندې"),
}

OUTPUT_NAMES = [
    "START_HERE.md",
    "TRANSLATION_DECISIONS_FULL.md",
    "PRIORITY_REVIEW.md",
    "DECISION_OCCURRENCES.csv",
    "DECISIONS.json",
    "translation-decision.schema.json",
    "TRANSLATION_DECISION_QA.json",
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def artifact(path: Path, shown_path: str | None = None) -> dict:
    return {
        "path_or_uri": shown_path or path.as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def compact(text: str, limit: int = 520) -> str:
    value = re.sub(r"\s+", " ", text).strip()
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def balanced_macro_arg(text: str, names: tuple[str, ...]) -> str | None:
    for name in names:
        needle = "\\" + name + "{"
        start = text.find(needle)
        if start < 0:
            continue
        pos = start + len(needle)
        depth = 1
        end = pos
        while end < len(text) and depth:
            if text[end] == "{" and (end == 0 or text[end - 1] != "\\"):
                depth += 1
            elif text[end] == "}" and (end == 0 or text[end - 1] != "\\"):
                depth -= 1
            end += 1
        if depth == 0:
            return compact(text[pos : end - 1], 180)
    return None


def titles_for_path(source_path: str, target_file: Path) -> tuple[str | None, str | None, str]:
    parts = Path(source_path).parts
    key = None
    if "sets-functions-relations" in parts:
        index = parts.index("sets-functions-relations")
        if len(parts) > index + 1:
            key = parts[index + 1]
    elif "propositional-logic" in parts:
        key = "syntax-and-semantics"
    elif "first-order-logic" in parts:
        index = parts.index("first-order-logic")
        if len(parts) > index + 1:
            key = parts[index + 1]
    part_title, chapter_title = PART_AND_CHAPTER.get(key, (None, None))
    text = target_file.read_text(encoding="utf-8")
    section_title = balanced_macro_arg(text, ("olsection", "olchapter", "chapter")) or Path(source_path).stem
    return part_title, chapter_title, section_title


def record_kind(entry_type: str) -> str:
    return {
        "terminology": "terminology",
        "source-correction": "source_correction",
        "source display omission": "source_correction",
        "notation ambiguity": "notation",
        "context-dependent notation": "notation",
        "cross-source notation conflict": "notation",
        "alternative chapter integration": "syntax",
    }[entry_type]


def recording_mode(entry: dict) -> str:
    timing = entry.get("entry_timing", "").casefold()
    return "contemporaneous" if timing.startswith("contemporaneous") else "retrospective"


def confidence(entry: dict) -> str:
    if entry["entry_type"] == "source-correction":
        return "high"
    uncertainty = entry.get("uncertainty", "").casefold()
    if any(word in uncertainty for word in ("unattested", "no exact", "sparse", "genuinely inconsistent")):
        return "low"
    if entry.get("provisional") or entry.get("review_priority") == "high":
        return "medium"
    return "high"


def review_priority(entry: dict) -> str:
    return {"high": "high", "medium": "normal", "standard": "low"}[entry["review_priority"]]


def alternatives(entry: dict) -> list[dict]:
    return [
        {
            "rendering": str(value),
            "disposition": "viable_alternative",
            "reason": (
                "Recorded for expert comparison; the current evidence and rationale favored the chosen rendering or treatment."
            ),
        }
        for value in entry.get("alternatives_for_expert_review", [])
        if str(value).strip()
    ]


def find_block_spans(alignments: list[dict]) -> dict[str, dict[str, dict]]:
    spans: dict[str, dict[str, dict]] = {}
    cursors: dict[tuple[str, str], int] = defaultdict(int)
    raw_cache: dict[tuple[str, str], bytes] = {}
    for row in alignments:
        spans[row["segment_id"]] = {}
        for side, prefix in (("source", "upstream"), ("target", "ps-Arab-PK")):
            key = (row["source_path"], side)
            path = REPO / prefix / row["source_path"]
            raw = raw_cache.setdefault(key, path.read_bytes())
            needle = row[side].encode("utf-8")
            start = raw.find(needle, cursors[key])
            if start < 0:
                raise ValueError(f"cannot locate {row['segment_id']} {side} bytes")
            end = start + len(needle)
            cursors[key] = end
            start_line = raw.count(b"\n", 0, start) + 1
            end_line = start_line + needle.count(b"\n")
            spans[row["segment_id"]][side] = {
                "start": start,
                "end_exclusive": end,
                "line_start": start_line,
                "line_end": end_line,
                "raw_sha256": sha256_bytes(raw),
                "path": path,
            }
    return spans


def locate_segment_for_line(
    unit_id: str,
    side: str,
    line: int,
    by_unit: dict[str, list[dict]],
    spans: dict[str, dict[str, dict]],
) -> dict:
    candidates = [
        row
        for row in by_unit[unit_id]
        if spans[row["segment_id"]][side]["line_start"]
        <= line
        <= spans[row["segment_id"]][side]["line_end"]
    ]
    if len(candidates) != 1:
        raise ValueError(f"line {unit_id} {side}:{line} maps to {len(candidates)} segments")
    return candidates[0]


def line_from_location(location: dict, side: str) -> int | None:
    keys = (
        ("source_line_1based", "source_literal_line_1based")
        if side == "source"
        else ("target_line_1based", "target_literal_or_token_line_1based")
    )
    for key in keys:
        value = location.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, list) and value:
            return int(value[0])
    return None


def reader_locator(segment_id: str, reader_pages: dict[str, dict]) -> dict:
    if segment_id not in reader_pages:
        return {
            "status": "pending",
            "reason": "No stable verified line-to-page mapping currently contains this semantic segment; no page was guessed.",
        }
    page = reader_pages[segment_id]
    required = {"artifact_filename", "artifact_sha256", "profile", "provenance"}
    if not required <= set(page):
        raise ValueError(f"incomplete reader page record for {segment_id}")
    return {
        "status": "available",
        "artifact_filename": page["artifact_filename"],
        "artifact_sha256": page["artifact_sha256"],
        "profile": page["profile"],
        "printed_page": page.get("printed_page"),
        "assembled_pdf_page": page.get("assembled_pdf_page"),
        "provenance": page["provenance"],
    }


def make_text_locator(
    alignment: dict,
    side: str,
    span: dict,
    source_term: str,
    intended_sense: str,
    context: str,
) -> dict:
    prefix = "upstream" if side == "source" else "ps-Arab-PK"
    return {
        "path": f"{prefix}/{alignment['source_path']}",
        "file_id": f"{alignment['unit_id']}-{side}",
        "file_sha256": span["raw_sha256"],
        "line_span": {"status": "available", "start": span["line_start"], "end": span["line_end"]},
        "byte_span": {"status": "available", "start": span["start"], "end_exclusive": span["end_exclusive"]},
        "printed_page": None,
        "excerpt": compact(alignment[side]),
        "term": source_term if side == "source" else None,
        "intended_sense": intended_sense,
        "context": context,
    }


def make_occurrence(
    occurrence_id: str,
    entry: dict,
    alignment: dict,
    spans: dict[str, dict[str, dict]],
    reader_pages: dict[str, dict],
    evidence_ref: dict,
    context: str,
) -> dict:
    segment_id = alignment["segment_id"]
    target_file = REPO / "ps-Arab-PK" / alignment["source_path"]
    part_title, chapter_title, section_title = titles_for_path(alignment["source_path"], target_file)
    source_term = entry.get("english_sense") or entry.get("source_term_or_sense") or entry["entry_id"]
    intended = entry.get("english_sense") or entry.get("rationale") or entry["entry_type"]
    chosen = entry.get("chosen_rendering_or_treatment") or entry.get("chosen_pashto")
    source_locator = make_text_locator(
        alignment, "source", spans[segment_id]["source"], source_term, intended, context
    )
    target_locator = make_text_locator(
        alignment, "target", spans[segment_id]["target"], chosen, intended, context
    )
    target_locator["term"] = chosen
    return {
        "occurrence_id": occurrence_id,
        "unit_id": alignment["unit_id"],
        "semantic_unit_id": segment_id,
        "part_title": part_title,
        "chapter_title": chapter_title,
        "section_title": section_title,
        "source": source_locator,
        "target": target_locator,
        "reader_locator": reader_locator(segment_id, reader_pages),
        "evidence_refs": [evidence_ref],
    }


def authority_status(note: str) -> str:
    lower = note.casefold()
    adverse = ("conflict" in lower or "differs" in lower) and "not" not in lower
    if adverse:
        return "checked_adverse"
    supports = any(word in lower for word in ("attest", "defines", "supports", "uses ", "records "))
    context_only = any(
        phrase in lower
        for phrase in (
            "not mathematical",
            "not technical",
            "not set-theoretic",
            "not a claim",
            "prose",
            "grammar",
            "orthography",
            "context only",
        )
    )
    return "checked_supports" if supports and not context_only else "checked_context_only"


def build_authorities(
    entry: dict,
    first_occurrence: dict,
    canon_sources: dict[str, dict],
    canon_passages: dict[str, dict],
    alignments: dict[str, dict],
) -> list[dict]:
    output: list[dict] = []
    for index, raw in enumerate(entry.get("actual_authorities_checked", []), 1):
        if isinstance(raw, dict) and (raw.get("passage_id") or raw.get("source_id")):
            passage_id = raw.get("passage_id")
            passage = canon_passages.get(passage_id, {})
            source_id = raw.get("source_id") or passage.get("source_id")
            source = canon_sources.get(source_id, {})
            note = raw.get("finding") or passage.get("evidence_note") or "Checked as recorded in the review ledger."
            locator = "; ".join(
                item
                for item in (
                    f"PDF page {raw.get('pdf_page_1based') or passage.get('pdf_page_1based')}"
                    if raw.get("pdf_page_1based") or passage.get("pdf_page_1based")
                    else None,
                    f"printed page {raw.get('printed_page') or passage.get('printed_page')}"
                    if raw.get("printed_page") or passage.get("printed_page")
                    else None,
                    raw.get("inspection") or passage.get("inspection"),
                )
                if item
            )
            citation = ". ".join(
                item
                for item in (
                    source.get("authors"),
                    raw.get("source_title") or source.get("title"),
                    raw.get("region") or source.get("region"),
                    source.get("url"),
                )
                if item
            )
            passage_hash = passage.get("anchor_sha256") or passage.get("page_image_sha256")
            if not passage_id or not passage_hash or not locator or not citation:
                raise ValueError(f"authority evidence incomplete for {entry['entry_id']}")
            output.append(
                {
                    "authority_id": passage_id,
                    "citation": citation,
                    "passage_id": passage_id,
                    "locator": locator,
                    "source_sha256": source.get("sha256") or passage.get("source_sha256"),
                    "passage_sha256": passage_hash,
                    "status": authority_status(note),
                    "note": note,
                }
            )
        else:
            segment_id = first_occurrence["semantic_unit_id"]
            alignment = alignments[segment_id]
            source = first_occurrence["source"]
            if isinstance(raw, dict):
                authority_id = raw.get("audit_id") or f"OPENLOGIC-{entry['entry_id']}-{index}"
                note = "; ".join(
                    str(value)
                    for value in (raw.get("classification"), raw.get("review"), entry.get("rationale"))
                    if value
                )
            else:
                authority_id = f"OPENLOGIC-{entry['entry_id']}-{index}"
                note = str(raw) + " " + entry.get("rationale", "")
            output.append(
                {
                    "authority_id": authority_id,
                    "citation": f"Open Logic Project source revision {SOURCE_REVISION}",
                    "passage_id": segment_id,
                    "locator": (
                        f"{source['path']} lines {source['line_span']['start']}-{source['line_span']['end']}"
                    ),
                    "source_sha256": source["file_sha256"],
                    "passage_sha256": alignment["source_sha256"],
                    "status": "checked_supports",
                    "note": note,
                }
            )
    if not output:
        segment_id = first_occurrence["semantic_unit_id"]
        alignment = alignments[segment_id]
        source = first_occurrence["source"]
        output.append(
            {
                "authority_id": f"OPENLOGIC-{entry['entry_id']}",
                "citation": f"Open Logic Project source revision {SOURCE_REVISION}",
                "passage_id": segment_id,
                "locator": f"{source['path']} lines {source['line_span']['start']}-{source['line_span']['end']}",
                "source_sha256": source["file_sha256"],
                "passage_sha256": alignment["source_sha256"],
                "status": "checked_context_only",
                "note": entry.get("rationale", "The frozen source passage was checked."),
            }
        )
    return output


def markdown_for(decisions: list[dict], title: str, introduction: str) -> str:
    lines = [f"# {title}", "", introduction, ""]
    for decision in decisions:
        lines.extend(
            [
                f"## {decision['decision_id']}",
                "",
                f"- Kind: `{decision['record_kind']}`; priority: `{decision['review_priority']}`; confidence: `{decision['confidence']}`; provisional: `{str(decision['provisional']).lower()}`",
                f"- Source term or construction: {decision['source_term_or_construction']}",
                f"- Intended sense: {decision['intended_sense']}",
                f"- Chosen Pashto: {decision['chosen_rendering']}",
                f"- Rationale: {decision['rationale']}",
                f"- Confidence reason: {decision['confidence_reason']}",
                f"- Expert question: {decision['please_double_check_question']}",
                "- Authorities:",
            ]
        )
        for authority in decision["authorities_checked"]:
            lines.append(
                f"  - `{authority['authority_id']}` ({authority['status']}): {authority['citation']} — {authority['note']}"
            )
        lines.append("- Alternatives:")
        if decision["alternatives"]:
            for alternative in decision["alternatives"]:
                lines.append(
                    f"  - {alternative['rendering']} ({alternative['disposition']}): {alternative['reason']}"
                )
        else:
            lines.append("  - None recorded.")
        lines.extend(
            [
                f"- Exact paired occurrences: {len(decision['occurrences'])}",
                "",
                "| Occurrence | Unit / semantic unit | Section | Source locus | Target locus | Reader page |",
                "|---|---|---|---|---|---|",
            ]
        )
        for occurrence in decision["occurrences"]:
            source = occurrence["source"]
            target = occurrence["target"]
            reader = occurrence["reader_locator"]
            if reader["status"] == "available":
                page = reader.get("printed_page") or str(reader.get("assembled_pdf_page") or "available")
                reader_text = f"{reader['artifact_filename']} p. {page}"
            else:
                reader_text = "pending; no page guessed"
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"`{occurrence['occurrence_id']}`",
                        f"`{occurrence['unit_id']}` / `{occurrence['semantic_unit_id']}`",
                        str(occurrence.get("section_title") or "—").replace("|", "\\|"),
                        f"`{source['path']}:{source['line_span']['start']}-{source['line_span']['end']}`",
                        f"`{target['path']}:{target['line_span']['start']}-{target['line_span']['end']}`",
                        reader_text,
                    ]
                )
                + " |"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--release-tag", default=None)
    parser.add_argument("--reader-units", type=int, default=None)
    args = parser.parse_args()
    source_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    input_names = {
        "review": "EXPERT_REVIEW_LOG.jsonl",
        "alignment": "ALIGNMENT.jsonl",
        "canon_use": "SEGMENT_CANON_USE.jsonl",
        "manifest": "SOURCE_MANIFEST.jsonl",
        "canon_sources": "CANON_SOURCES.jsonl",
        "canon_passages": "CANON_PASSAGES.jsonl",
        "corrections": "SOURCE_CORRECTIONS.json",
        "terms": "TERM_DECISIONS.jsonl",
        "schema": "translation-decision.schema.json",
        "qa": "QA.json",
    }
    for name in input_names.values():
        if not (source_dir / name).is_file():
            raise FileNotFoundError(source_dir / name)

    schema_source = source_dir / input_names["schema"]
    schema_target = output_dir / "translation-decision.schema.json"
    if schema_source.resolve() != schema_target.resolve():
        schema_target.write_bytes(schema_source.read_bytes())
    if sha256(schema_target) != "50e7fa407b62c711f92f8b93be591d3b4a6e1c4adb1386c398bb5f76844d9f90":
        raise ValueError("canonical schema hash mismatch")

    raw_entries = read_jsonl(source_dir / input_names["review"])
    alignments_list = read_jsonl(source_dir / input_names["alignment"])
    alignments = {row["segment_id"]: row for row in alignments_list}
    canon_use = read_jsonl(source_dir / input_names["canon_use"])
    manifest_rows = read_jsonl(source_dir / input_names["manifest"])
    manifest = {row["unit_id"]: row for row in manifest_rows}
    canon_sources = {row["source_id"]: row for row in read_jsonl(source_dir / input_names["canon_sources"])}
    canon_passages = {row["passage_id"]: row for row in read_jsonl(source_dir / input_names["canon_passages"])}
    qa_source = json.loads((source_dir / input_names["qa"]).read_text(encoding="utf-8"))
    spans = find_block_spans(alignments_list)
    by_unit: dict[str, list[dict]] = defaultdict(list)
    for row in alignments_list:
        by_unit[row["unit_id"]].append(row)

    reader_pages_path = source_dir / "READER_OCCURRENCE_PAGES.json"
    reader_pages_document = (
        json.loads(reader_pages_path.read_text(encoding="utf-8"))
        if reader_pages_path.exists()
        else {"segments": {}}
    )
    reader_pages = reader_pages_document.get("segments", {})

    uses_by_term: dict[str, list[dict]] = defaultdict(list)
    for use in canon_use:
        if use["segment_id"] not in alignments:
            raise ValueError(f"canon-use segment missing from alignment: {use['segment_id']}")
        alignment = alignments[use["segment_id"]]
        if use["source_sha256"] != alignment["source_sha256"] or use["target_sha256"] != alignment["target_sha256"]:
            raise ValueError(f"canon-use hash mismatch: {use['segment_id']}")
        for term_id in use.get("terms", []):
            uses_by_term[term_id].append(use)

    evidence_refs = {
        "terminology": artifact(
            source_dir / input_names["canon_use"], "evidence/SEGMENT_CANON_USE.jsonl"
        ),
        "source_correction": artifact(
            source_dir / input_names["corrections"], "evidence/SOURCE_CORRECTIONS.json"
        ),
        "other": artifact(
            source_dir / input_names["review"], "evidence/EXPERT_REVIEW_LOG.jsonl"
        ),
    }

    decisions: list[dict] = []
    occurrence_number = 0
    represented_term_pairs: set[tuple[str, str]] = set()
    for entry in raw_entries:
        if not {
            "entry_id",
            "entry_type",
            "source_term_or_sense",
            "chosen_rendering_or_treatment",
            "rationale",
            "review_priority",
            "uncertainty",
            "review_question",
        } <= set(entry):
            raise ValueError(f"review entry is not enriched: {entry.get('entry_id')}")

        occurrence_specs: list[tuple[dict, str, dict]] = []
        if entry["entry_type"] == "terminology":
            uses = uses_by_term.get(entry["entry_id"], [])
            if not uses:
                raise ValueError(f"terminology decision has no canon-use segment: {entry['entry_id']}")
            for use in uses:
                segment_id = use["segment_id"]
                represented_term_pairs.add((entry["entry_id"], segment_id))
                occurrence_specs.append(
                    (
                        alignments[segment_id],
                        f"Accepted aligned semantic segment; canon consultation scope: {use['consultation_scope']}",
                        evidence_refs["terminology"],
                    )
                )
        else:
            for location in entry.get("source_target_locations", []):
                unit_id = location.get("unit_id")
                target_line = line_from_location(location, "target")
                source_line = line_from_location(location, "source")
                if target_line is not None:
                    alignment = locate_segment_for_line(unit_id, "target", target_line, by_unit, spans)
                elif source_line is not None:
                    alignment = locate_segment_for_line(unit_id, "source", source_line, by_unit, spans)
                else:
                    raise ValueError(f"decision location has no exact line: {entry['entry_id']}")
                context = location.get("source_locator") or (
                    f"Recorded decision location: target line {target_line}"
                    if target_line is not None
                    else f"Recorded decision location: source line {source_line}"
                )
                ref = (
                    evidence_refs["source_correction"]
                    if record_kind(entry["entry_type"]) == "source_correction"
                    else evidence_refs["other"]
                )
                occurrence_specs.append((alignment, context, ref))

        seen_segments: set[str] = set()
        occurrences: list[dict] = []
        for alignment, context, evidence_ref in occurrence_specs:
            if alignment["segment_id"] in seen_segments:
                continue
            seen_segments.add(alignment["segment_id"])
            occurrence_number += 1
            occurrence_id = f"ps-Arab-PK-OCC-{occurrence_number:06d}"
            occurrences.append(
                make_occurrence(
                    occurrence_id,
                    entry,
                    alignment,
                    spans,
                    reader_pages,
                    evidence_ref,
                    context,
                )
            )

        first_location = entry.get("source_target_locations", [{}])[0]
        source_term_or_construction = entry.get("english_sense") or entry.get("source_term_or_sense")
        if entry["entry_type"] != "terminology":
            source_term_or_construction = (
                f"{entry['entry_id']}: {first_location.get('source_locator') or source_term_or_construction}"
            )
        question = entry.get("review_question") or entry.get("please_double_check", "")
        decision = {
            "decision_id": entry["entry_id"],
            "supersedes": [],
            "record_kind": record_kind(entry["entry_type"]),
            "recording_mode": recording_mode(entry),
            "edition": dict(EDITION),
            "source_term_or_construction": source_term_or_construction,
            "intended_sense": entry.get("english_sense") or entry.get("rationale") or entry["entry_type"],
            "chosen_rendering": entry["chosen_rendering_or_treatment"],
            "rationale": entry["rationale"],
            "authorities_checked": [],
            "alternatives": alternatives(entry),
            "confidence": confidence(entry),
            "confidence_reason": f"{entry.get('confidence', '')}. {entry.get('uncertainty', '')}".strip(". "),
            "provisional": bool(entry.get("provisional") or entry.get("open_to_correction")),
            "review_priority": review_priority(entry),
            "expert_review_useful": True,
            "expert_review_reason": entry.get("uncertainty"),
            "please_double_check_question": question,
            "occurrences": occurrences,
        }
        decision["authorities_checked"] = build_authorities(
            entry, occurrences[0], canon_sources, canon_passages, alignments
        )
        decisions.append(decision)

    draft_units = int(qa_source["translation_coverage"]["draft_units"])
    reader_units = args.reader_units
    if reader_units is None:
        reader_units = int(qa_source["translation_coverage"].get("published", 0))
    document = {
        "schema_version": SCHEMA_VERSION,
        "edition_release": {
            "edition": dict(EDITION),
            "release_tag": args.release_tag,
            "repository": "https://github.com/KokunoYumeto/openlogic-ps-Arab-PK",
            "doi": "10.5281/zenodo.22307197",
            "source_revision": SOURCE_REVISION,
            "coverage_state": "partial",
            "source_units": draft_units,
            "reader_units": reader_units,
        },
        "generator": artifact(Path(__file__), "tools/build_translation_decision_register.py"),
        "decisions": decisions,
    }

    schema = json.loads(schema_target.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(document), key=lambda error: list(error.path))
    if errors:
        first = errors[0]
        raise ValueError(f"canonical schema validation failed at {list(first.path)}: {first.message}")

    decisions_path = output_dir / "DECISIONS.json"
    decisions_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\r\n",
    )

    csv_fields = [
        "decision_id",
        "occurrence_id",
        "record_kind",
        "review_priority",
        "confidence",
        "provisional",
        "unit_id",
        "semantic_unit_id",
        "part_title",
        "chapter_title",
        "section_title",
        "source_term_or_construction",
        "intended_sense",
        "chosen_rendering",
        "source_path",
        "source_file_sha256",
        "source_line_start",
        "source_line_end",
        "source_byte_start",
        "source_byte_end_exclusive",
        "source_excerpt",
        "target_path",
        "target_file_sha256",
        "target_line_start",
        "target_line_end",
        "target_byte_start",
        "target_byte_end_exclusive",
        "target_excerpt",
        "reader_status",
        "reader_artifact",
        "reader_artifact_sha256",
        "reader_printed_page",
        "reader_pdf_page",
        "reader_provenance_or_reason",
        "evidence_path",
        "evidence_sha256",
        "please_double_check_question",
    ]
    csv_rows: list[dict] = []
    for decision in decisions:
        for occurrence in decision["occurrences"]:
            source = occurrence["source"]
            target = occurrence["target"]
            reader = occurrence["reader_locator"]
            evidence = occurrence["evidence_refs"][0]
            csv_rows.append(
                {
                    "decision_id": decision["decision_id"],
                    "occurrence_id": occurrence["occurrence_id"],
                    "record_kind": decision["record_kind"],
                    "review_priority": decision["review_priority"],
                    "confidence": decision["confidence"],
                    "provisional": str(decision["provisional"]).lower(),
                    "unit_id": occurrence["unit_id"],
                    "semantic_unit_id": occurrence["semantic_unit_id"],
                    "part_title": occurrence.get("part_title") or "",
                    "chapter_title": occurrence.get("chapter_title") or "",
                    "section_title": occurrence.get("section_title") or "",
                    "source_term_or_construction": decision["source_term_or_construction"],
                    "intended_sense": decision["intended_sense"],
                    "chosen_rendering": decision["chosen_rendering"],
                    "source_path": source["path"],
                    "source_file_sha256": source["file_sha256"],
                    "source_line_start": source["line_span"]["start"],
                    "source_line_end": source["line_span"]["end"],
                    "source_byte_start": source["byte_span"]["start"],
                    "source_byte_end_exclusive": source["byte_span"]["end_exclusive"],
                    "source_excerpt": source["excerpt"],
                    "target_path": target["path"],
                    "target_file_sha256": target["file_sha256"],
                    "target_line_start": target["line_span"]["start"],
                    "target_line_end": target["line_span"]["end"],
                    "target_byte_start": target["byte_span"]["start"],
                    "target_byte_end_exclusive": target["byte_span"]["end_exclusive"],
                    "target_excerpt": target["excerpt"],
                    "reader_status": reader["status"],
                    "reader_artifact": reader.get("artifact_filename", ""),
                    "reader_artifact_sha256": reader.get("artifact_sha256", ""),
                    "reader_printed_page": reader.get("printed_page") or "",
                    "reader_pdf_page": reader.get("assembled_pdf_page") or "",
                    "reader_provenance_or_reason": reader.get("provenance") or reader.get("reason", ""),
                    "evidence_path": evidence["path_or_uri"],
                    "evidence_sha256": evidence["sha256"],
                    "please_double_check_question": decision["please_double_check_question"] or "",
                }
            )
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=csv_fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(csv_rows)
    csv_path = output_dir / "DECISION_OCCURRENCES.csv"
    csv_path.write_text(buffer.getvalue(), encoding="utf-8-sig", newline="")

    full_path = output_dir / "TRANSLATION_DECISIONS_FULL.md"
    full_path.write_text(
        markdown_for(
            decisions,
            "Pashto (Pakistan) translation decisions — full expert-review index",
            (
                f"This index contains {len(decisions)} decisions and {len(csv_rows)} exact paired source/target occurrences. "
                "Pakistani Pashto is primary; Afghan evidence is explicitly regional. Pending reader pages are stated rather than guessed."
            ),
        ),
        encoding="utf-8",
        newline="\r\n",
    )
    priority_decisions = [decision for decision in decisions if decision["review_priority"] in {"urgent", "high"}]
    priority_path = output_dir / "PRIORITY_REVIEW.md"
    priority_path.write_text(
        markdown_for(
            priority_decisions,
            "Pashto (Pakistan) translation decisions — priority expert review",
            (
                f"This focused view contains {len(priority_decisions)} high-priority decisions. "
                "It preserves every exact paired occurrence for those decisions."
            ),
        ),
        encoding="utf-8",
        newline="\r\n",
    )

    decision_ids = [decision["decision_id"] for decision in decisions]
    occurrence_ids = [row["occurrence_id"] for decision in decisions for row in decision["occurrences"]]
    if len(decision_ids) != len(set(decision_ids)):
        raise ValueError("duplicate decision_id")
    if len(occurrence_ids) != len(set(occurrence_ids)):
        raise ValueError("duplicate occurrence_id")
    expected_term_pairs = {
        (term_id, use["segment_id"])
        for term_id, uses in uses_by_term.items()
        for use in uses
        if term_id in {entry["entry_id"] for entry in raw_entries if entry["entry_type"] == "terminology"}
    }
    if represented_term_pairs != expected_term_pairs:
        raise ValueError("not every canon-use term/segment pair is represented")

    raw_cache: dict[str, bytes] = {}
    for decision in decisions:
        for occurrence in decision["occurrences"]:
            alignment = alignments[occurrence["semantic_unit_id"]]
            for side in ("source", "target"):
                locator = occurrence[side]
                file_path = REPO / locator["path"]
                raw = raw_cache.setdefault(locator["path"], file_path.read_bytes())
                if sha256_bytes(raw) != locator["file_sha256"]:
                    raise ValueError(f"file hash mismatch: {locator['path']}")
                span = locator["byte_span"]
                actual = raw[span["start"] : span["end_exclusive"]]
                expected = alignment[side].encode("utf-8")
                if actual != expected:
                    raise ValueError(f"byte span mismatch: {occurrence['occurrence_id']} {side}")
            evidence = occurrence["evidence_refs"][0]
            evidence_path = REPO / evidence["path_or_uri"]
            if not evidence_path.is_file() or sha256(evidence_path) != evidence["sha256"]:
                raise ValueError(f"evidence hash mismatch: {evidence['path_or_uri']}")

    csv_check = list(csv.DictReader(io.StringIO(csv_path.read_text(encoding="utf-8-sig"))))
    if [row["occurrence_id"] for row in csv_check] != occurrence_ids:
        raise ValueError("CSV occurrence projection mismatch")
    full_text = full_path.read_text(encoding="utf-8")
    if any(full_text.count(f"## {decision_id}\n") != 1 for decision_id in decision_ids):
        raise ValueError("full Markdown decision projection mismatch")
    priority_text = priority_path.read_text(encoding="utf-8")
    if any(priority_text.count(f"## {decision['decision_id']}\n") != 1 for decision in priority_decisions):
        raise ValueError("priority Markdown decision projection mismatch")

    pending_pages = sum(
        occurrence["reader_locator"]["status"] == "pending"
        for decision in decisions
        for occurrence in decision["occurrences"]
    )
    qa = {
        "schema": "openlogic-translation-decision-qa/1.0.0",
        "status": "PASS",
        "normative_schema": artifact(schema_target, "evidence/translation-decision.schema.json"),
        "canonical_register": artifact(decisions_path, "evidence/DECISIONS.json"),
        "counts": {
            "decisions": len(decisions),
            "occurrences": len(occurrence_ids),
            "terminology_decisions": sum(decision["record_kind"] == "terminology" for decision in decisions),
            "source_correction_decisions": sum(decision["record_kind"] == "source_correction" for decision in decisions),
            "priority_decisions": len(priority_decisions),
            "reader_pages_available": len(occurrence_ids) - pending_pages,
            "reader_pages_pending": pending_pages,
        },
        "validation": {
            "json_schema_draft_2020_12": "PASS",
            "unique_decision_ids": "PASS",
            "unique_occurrence_ids": "PASS",
            "one_paired_occurrence_per_decision_semantic_unit": "PASS",
            "canon_use_term_segment_coverage": "PASS",
            "source_target_file_hashes": "PASS",
            "source_target_line_and_byte_spans": "PASS",
            "alignment_segment_bytes": "PASS",
            "evidence_reference_hashes": "PASS",
            "markdown_csv_json_agreement": "PASS",
            "pending_pages_are_explicit_and_never_guessed": "PASS",
        },
        "projection_artifacts": {
            "START_HERE.md": None,
            "TRANSLATION_DECISIONS_FULL.md": artifact(full_path, "evidence/TRANSLATION_DECISIONS_FULL.md"),
            "PRIORITY_REVIEW.md": artifact(priority_path, "evidence/PRIORITY_REVIEW.md"),
            "DECISION_OCCURRENCES.csv": artifact(csv_path, "evidence/DECISION_OCCURRENCES.csv"),
        },
        "input_artifacts": {
            key: artifact(source_dir / name, f"evidence/{name}")
            for key, name in input_names.items()
            if key != "schema"
        },
    }

    start_here_path = output_dir / "START_HERE.md"
    start_here = f"""# Translation decision review — start here

This package records every currently identified judgment-dependent Pashto (Pakistan) translation choice in the canonical OpenLogic schema. It contains **{len(decisions)} decisions** and **{len(occurrence_ids)} exact paired source/target occurrences** across **{draft_units} of 722 translated source units**.

- [Full expert-review index](TRANSLATION_DECISIONS_FULL.md)
- [High-priority review](PRIORITY_REVIEW.md)
- [One paired occurrence per CSV row](DECISION_OCCURRENCES.csv)
- [Canonical machine register](DECISIONS.json)
- [Normative JSON Schema](translation-decision.schema.json)
- [Validation receipt](TRANSLATION_DECISION_QA.json)

Pakistani Pashto usage and orthography are primary. Afghan Pashto sources are labelled regional comparators. The release uses Arabic-derived Pashto script, international mathematical notation, RTL prose, and LTR formulas and proof diagrams. A separate Afghan edition would need its own canon, terminology decisions, semantic QA, rendering QA, and publication receipts; character conversion alone would not produce one.

Missing dictionary attestation never leaves a needed term blank. The register records the best evidence-based provisional rendering, alternatives, confidence, and a concrete expert question. Reader pages remain `pending` until a stable artifact and verified segment-to-page map exist; no page is inferred from a unit range.
"""
    start_here_path.write_text(start_here, encoding="utf-8", newline="\r\n")
    qa["projection_artifacts"]["START_HERE.md"] = artifact(start_here_path, "evidence/START_HERE.md")
    qa_path = output_dir / "TRANSLATION_DECISION_QA.json"
    qa_path.write_text(
        json.dumps(qa, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\r\n",
    )

    print(
        json.dumps(
            {
                "status": "PASS",
                "decisions": len(decisions),
                "occurrences": len(occurrence_ids),
                "priority_decisions": len(priority_decisions),
                "pending_reader_pages": pending_pages,
                "artifacts": {
                    name: {"bytes": (output_dir / name).stat().st_size, "sha256": sha256(output_dir / name)}
                    for name in OUTPUT_NAMES
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
