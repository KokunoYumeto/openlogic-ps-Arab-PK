#!/usr/bin/env python3
"""Independently validate the cumulative computability EPUB archive."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import posixpath
import re
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET


XHTML_NS = "http://www.w3.org/1999/xhtml"
MATHML_NS = "http://www.w3.org/1998/Math/MathML"
OPF_NS = "http://www.idpf.org/2007/opf"
DC_NS = "http://purl.org/dc/elements/1.1/"
XML_NS = "http://www.w3.org/XML/1998/namespace"
EPUB_NS = "http://www.idpf.org/2007/ops"

X = f"{{{XHTML_NS}}}"
M = f"{{{MATHML_NS}}}"
O = f"{{{OPF_NS}}}"
D = f"{{{DC_NS}}}"

CHAPTERS = [f"chapter-{number:02d}.xhtml" for number in range(1, 26)]
XHTML_DOCUMENTS = ["title.xhtml", "nav.xhtml", *CHAPTERS]
FIGURES = [f"figure-{number:03d}.svg" for number in range(1, 21)]
REQUIRED_MEMBERS = {
    "mimetype",
    "META-INF/container.xml",
    "EPUB/package.opf",
    "EPUB/styles.css",
    *(f"EPUB/{name}" for name in XHTML_DOCUMENTS),
    *(f"EPUB/images/{name}" for name in FIGURES),
}

CLASS_COUNT_MAP = {
    "proof-tree": "proof-tree_environments",
    "proof-rules": "proof-rules_environments",
    "tableau": "tableau_environments",
    "cor": "environment_cor",
    "defn": "environment_defn",
    "editorial": "environment_editorial",
    "history": "environment_history",
    "figure": "environment_figure",
    "data-table": "environment_table",
    "ex": "environment_ex",
    "lem": "environment_lem",
    "prob": "environment_prob",
    "proof": "environment_proof",
    "prop": "environment_prop",
    "rem": "environment_rem",
    "thm": "environment_thm",
}

RAW_TEX = re.compile(r"\\(?:[A-Za-z@]+|[\[\]()])")
UNIT_ID = re.compile(r"OLP-\d{4}")
SEGMENT_ID = re.compile(r"OLP-\d{4}-B\d{3}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epub", type=Path, required=True)
    parser.add_argument("--build-record", type=Path, required=True)
    parser.add_argument("--alignment", type=Path, required=True)
    parser.add_argument("--reference-map", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def classes(element: ET.Element) -> set[str]:
    return set(element.attrib.get("class", "").split())


def visible_text(element: ET.Element) -> str:
    if element.tag == f"{X}code":
        return ""
    parts: list[str] = []
    if element.text:
        parts.append(element.text)
    for child in element:
        if not child.tag.startswith(f"{{{MATHML_NS}}}"):
            parts.append(visible_text(child))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)


def descendant_count(element: ET.Element, tag: str) -> int:
    return sum(1 for item in element.iter(f"{X}{tag}") if item is not element)


def main() -> None:
    args = parse_args()
    build_record = json.loads(args.build_record.read_text(encoding="utf-8"))
    global CHAPTERS, XHTML_DOCUMENTS, FIGURES, REQUIRED_MEMBERS
    chapter_count = build_record["scope"]["chapter_count"]
    figure_count = build_record["validation"]["figures"]
    unit_count = build_record["scope"]["unit_count"]
    require((unit_count, chapter_count, figure_count) in {(255, 25, 20), (321, 31, 31)}, "Unsupported cumulative EPUB scope")
    CHAPTERS = [f"chapter-{number:02d}.xhtml" for number in range(1, chapter_count + 1)]
    XHTML_DOCUMENTS = ["title.xhtml", "nav.xhtml", *CHAPTERS]
    FIGURES = [f"figure-{number:03d}.svg" for number in range(1, figure_count + 1)]
    REQUIRED_MEMBERS = {
        "mimetype", "META-INF/container.xml", "EPUB/package.opf", "EPUB/styles.css",
        *(f"EPUB/{name}" for name in XHTML_DOCUMENTS),
        *(f"EPUB/images/{name}" for name in FIGURES),
    }
    reference_map = json.loads(args.reference_map.read_text(encoding="utf-8"))
    epub_sha256 = sha256_file(args.epub)
    epub_bytes = args.epub.stat().st_size

    require(epub_sha256 == build_record["epub"]["sha256"], "EPUB hash differs from build record")
    require(epub_bytes == build_record["epub"]["bytes"], "EPUB size differs from build record")
    require(
        sha256_file(args.reference_map) == build_record["reference_map"]["sha256"],
        "Reference-map hash differs from build record",
    )
    require(reference_map["status"] == "accepted_pdf_numbering_replayed", "Reference map is not accepted")
    require(
        reference_map["accepted_pdf"]["sha256"]
        == build_record["reference_map"]["accepted_pdf_sha256"],
        "Reference map and build record name different accepted PDFs",
    )

    with zipfile.ZipFile(args.epub) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        require(len(names) == len(set(names)), "Duplicate ZIP member name")
        require(set(names) == REQUIRED_MEMBERS, "Unexpected or missing EPUB member")
        require(names[0] == "mimetype", "mimetype is not the first ZIP member")
        require(infos[0].compress_type == zipfile.ZIP_STORED, "mimetype is compressed")
        require(archive.read("mimetype") == b"application/epub+zip", "Invalid mimetype payload")
        require(names[1:] == sorted(names[1:]), "Non-mimetype members are not deterministic/sorted")
        require(all(not (info.flag_bits & 0x1) for info in infos), "Encrypted ZIP member")
        member_timestamps = sorted({info.date_time for info in infos})
        require(len(member_timestamps) == 1, "ZIP member timestamps are not normalized")

        container = ET.fromstring(archive.read("META-INF/container.xml"))
        rootfiles = [
            element.attrib.get("full-path")
            for element in container.iter()
            if element.tag.endswith("rootfile")
        ]
        require(rootfiles == ["EPUB/package.opf"], "Container rootfile is not package.opf")

        opf = ET.fromstring(archive.read("EPUB/package.opf"))
        require(opf.attrib.get("version") == "3.0", "Package is not EPUB 3")
        require(opf.attrib.get("unique-identifier") == "pub-id", "Unexpected unique-identifier")
        language = opf.findtext(f".//{D}language")
        title = opf.findtext(f".//{D}title")
        require(language == "ps-Arab-PK", "Package language is not ps-Arab-PK")
        require(bool(title and title.strip()), "Package title is empty")

        manifest = {
            item.attrib["id"]: item.attrib
            for item in opf.findall(f".//{O}manifest/{O}item")
        }
        spine = opf.find(f".//{O}spine")
        require(spine is not None, "Package has no spine")
        require(spine.attrib.get("page-progression-direction") == "rtl", "Spine is not RTL")
        spine_ids = [item.attrib["idref"] for item in spine.findall(f"{O}itemref")]
        require(
            spine_ids == ["title", *(f"chapter-{number:02d}" for number in range(1, chapter_count + 1))],
            "Unexpected spine order",
        )
        require(
            manifest.get("nav", {}).get("properties") == "nav",
            "Navigation document is not identified in the manifest",
        )
        for number in range(1, chapter_count + 1):
            properties = manifest[f"chapter-{number:02d}"].get("properties", "").split()
            require("mathml" in properties, f"Chapter {number} lacks manifest MathML property")
        for number in range(1, figure_count + 1):
            item = manifest.get(f"figure-{number:03d}", {})
            require(
                item.get("href") == f"images/figure-{number:03d}.svg"
                and item.get("media-type") == "image/svg+xml",
                f"Figure {number} is absent from the manifest",
            )

        roots: dict[str, ET.Element] = {}
        document_ids: dict[str, set[str]] = {}
        class_counts: collections.Counter[str] = collections.Counter()
        unit_anchors: collections.Counter[str] = collections.Counter()
        segment_boundaries: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
        math_count = 0
        tex_annotation_count = 0
        raw_tex_hits: list[dict[str, str]] = []
        formal_direction_failures: list[dict[str, str]] = []
        table_direction_failures: list[str] = []
        proof_nodes = 0
        tableau_nodes = 0
        image_sources: list[tuple[str, str]] = []

        for document in XHTML_DOCUMENTS:
            member = f"EPUB/{document}"
            root = ET.fromstring(archive.read(member))
            roots[document] = root
            require(root.tag == f"{X}html", f"{document} is not XHTML")
            require(root.attrib.get("lang") == "ps-Arab-PK", f"{document} has wrong lang")
            require(root.attrib.get(f"{{{XML_NS}}}lang") == "ps-Arab-PK", f"{document} has wrong xml:lang")
            require(root.attrib.get("dir") == "rtl", f"{document} is not RTL")

            ids = [element.attrib["id"] for element in root.iter() if "id" in element.attrib]
            require(len(ids) == len(set(ids)), f"Duplicate id in {document}")
            document_ids[document] = set(ids)

            text_without_math = visible_text(root)
            for match in RAW_TEX.finditer(text_without_math):
                raw_tex_hits.append(
                    {"document": document, "token": match.group(0), "offset": str(match.start())}
                )

            for element in root.iter():
                token_set = classes(element)
                class_counts.update(token_set)
                if "source-unit" in token_set:
                    unit = element.attrib.get("data-source-unit", "")
                    require(bool(UNIT_ID.fullmatch(unit)), f"Malformed source unit in {document}")
                    unit_anchors[unit] += 1
                if "source-segment" in token_set:
                    segment = element.attrib.get("data-source-segment", "")
                    boundary = element.attrib.get("data-boundary", "")
                    require(bool(SEGMENT_ID.fullmatch(segment)), f"Malformed segment in {document}")
                    require(boundary in {"start", "end"}, f"Malformed segment boundary in {document}")
                    segment_boundaries[segment][boundary] += 1
                if token_set & {"proof-tree", "proof-rules", "tableau"}:
                    if element.attrib.get("dir") != "rtl":
                        formal_direction_failures.append(
                            {"document": document, "classes": " ".join(sorted(token_set))}
                        )
                if "derivation" in token_set and element.attrib.get("dir") not in {"ltr", "rtl"}:
                    formal_direction_failures.append(
                        {"document": document, "classes": " ".join(sorted(token_set))}
                    )
                if "equation-number" in token_set and element.attrib.get("dir") != "ltr":
                    formal_direction_failures.append(
                        {"document": document, "classes": " ".join(sorted(token_set))}
                    )
                if element.tag == f"{X}table" and element.attrib.get("dir") not in {"ltr", "rtl"}:
                    table_direction_failures.append(document)
                if element.tag == f"{X}img":
                    source = element.attrib.get("src", "")
                    alternative = element.attrib.get("alt", "").strip()
                    require(bool(alternative), f"Image lacks alt text in {document}")
                    image_sources.append((document, source))
                if token_set & {"proof-tree", "proof-rules"}:
                    proof_nodes += descendant_count(element, "li")
                if "tableau" in token_set:
                    tableau_nodes += descendant_count(element, "li")

            for math in root.iter(f"{M}math"):
                math_count += 1
                require(math.attrib.get("dir") == "ltr", f"MathML without LTR direction in {document}")
                annotations = [
                    node
                    for node in math.iter(f"{M}annotation")
                    if node.attrib.get("encoding") == "application/x-tex"
                ]
                require(len(annotations) == 1, f"MathML lacks one TeX annotation in {document}")
                require(bool((annotations[0].text or "").strip()), f"Empty TeX annotation in {document}")
                tex_annotation_count += 1

        require(not raw_tex_hits, "Visible raw TeX remains outside MathML annotations")
        require(
            not formal_direction_failures,
            f"Formal panels lack explicit/expected direction: {formal_direction_failures[:10]}",
        )
        require(not table_direction_failures, "Tables lack explicit direction")

        expected_image_sources = {f"images/{name}" for name in FIGURES}
        require(
            len(image_sources) == len(FIGURES)
            and {source for _, source in image_sources} == expected_image_sources,
            "XHTML image references are incomplete or duplicated",
        )
        svg_viewboxes: dict[str, str] = {}
        for figure in FIGURES:
            root = ET.fromstring(archive.read(f"EPUB/images/{figure}"))
            require(
                root.tag == f"{{http://www.w3.org/2000/svg}}svg",
                f"{figure} is not SVG",
            )
            viewbox = root.attrib.get("viewBox", "")
            require(bool(viewbox), f"{figure} lacks a viewBox")
            svg_viewboxes[figure] = viewbox
            for element in root.iter():
                for name, value in element.attrib.items():
                    if name.endswith("href"):
                        require(
                            not urlsplit(value).scheme and not value.startswith("/"),
                            f"{figure} contains an external resource reference",
                        )

        expected_units = [f"OLP-{number:04d}" for number in range(1, unit_count + 1)]
        require(sorted(unit_anchors) == expected_units, "Source-unit anchors do not cover the declared scope")
        require(all(count == 1 for count in unit_anchors.values()), "Source-unit anchor is duplicated")
        require(
            all(boundaries == {"start": 1, "end": 1} for boundaries in segment_boundaries.values()),
            "Source segment does not have exactly one start and one end boundary",
        )

        internal_links = 0
        external_links = 0
        broken_links: list[dict[str, str]] = []
        for document, root in roots.items():
            for anchor in root.iter(f"{X}a"):
                href = anchor.attrib.get("href")
                if not href:
                    continue
                parsed = urlsplit(href)
                if parsed.scheme:
                    external_links += 1
                    continue
                internal_links += 1
                target_document = unquote(parsed.path) if parsed.path else document
                target_document = posixpath.normpath(
                    posixpath.join(posixpath.dirname(document), target_document)
                )
                if target_document not in roots:
                    broken_links.append({"document": document, "href": href, "reason": "missing document"})
                    continue
                if parsed.fragment and unquote(parsed.fragment) not in document_ids[target_document]:
                    broken_links.append({"document": document, "href": href, "reason": "missing fragment"})
        require(not broken_links, "Broken internal XHTML link")

        nav = roots["nav.xhtml"]
        nav_nodes = list(nav.iter(f"{X}nav"))
        require(
            len(nav_nodes) == 1 and nav_nodes[0].attrib.get(f"{{{EPUB_NS}}}type") == "toc",
            "Navigation document lacks one EPUB TOC",
        )
        nav_entries = descendant_count(nav_nodes[0], "a")

        styles = archive.read("EPUB/styles.css").decode("utf-8")
        require(not re.search(r"(?i)\b(?:direction|unicode-bidi)\s*:", styles), "Forbidden bidi CSS declaration")

        member_records = [
            {
                "path": info.filename,
                "bytes": info.file_size,
                "compressed_bytes": info.compress_size,
                "compression": info.compress_type,
                "timestamp": list(info.date_time),
                "sha256": sha256_bytes(archive.read(info.filename)),
            }
            for info in infos
        ]

    expected_structure = build_record["structure_counts"]
    require(math_count == build_record["validation"]["mathml_elements"], "MathML count mismatch")
    require(tex_annotation_count == math_count, "TeX annotation count mismatch")
    require(internal_links == build_record["validation"]["internal_links"], "Internal-link count mismatch")
    require(external_links == build_record["validation"]["external_links"], "External-link count mismatch")
    require(
        len(image_sources) == build_record["validation"]["figures"] == figure_count,
        "Figure count mismatch",
    )
    require(len(segment_boundaries) == build_record["scope"]["semantic_segment_count"], "Segment count mismatch")
    require(
        proof_nodes == expected_structure["proof_nodes"],
        f"Proof-node count mismatch: {proof_nodes} != {expected_structure['proof_nodes']}",
    )
    require(
        tableau_nodes == expected_structure["tableau_nodes"],
        f"Tableau-node count mismatch: {tableau_nodes} != {expected_structure['tableau_nodes']}",
    )
    for class_name, build_key in CLASS_COUNT_MAP.items():
        require(class_counts[class_name] == expected_structure[build_key], f"{class_name} count mismatch")

    alignment_units: set[str] = set()
    alignment_segments: set[str] = set()
    with args.alignment.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            unit = row.get("unit_id", "")
            if unit in unit_anchors:
                alignment_units.add(unit)
                alignment_segments.add(row["segment_id"])
    require(alignment_units == set(unit_anchors), "Alignment lacks a released unit")
    require(set(segment_boundaries) <= alignment_segments, "EPUB has a segment absent from alignment")

    checks = {
        "archive_members_exact": True,
        "archive_member_order_deterministic": True,
        "archive_timestamps_normalized": True,
        "mimetype_first_and_uncompressed": True,
        "container_and_package_valid": True,
        "spine_order_and_rtl_valid": True,
        "xhtml_well_formed": True,
        "language_and_direction_valid": True,
        "mathml_native_ltr_and_annotated": True,
        "unit_coverage_exact": True,
        "segment_boundaries_paired": True,
        "segments_trace_to_alignment": True,
        "internal_links_resolve": True,
        "visible_raw_tex_absent": True,
        "formal_direction_explicit": True,
        "forbidden_bidi_css_absent": True,
        "svg_figures_complete_and_self_contained": True,
        "semantic_counts_match_build": True,
    }
    segment_ids = sorted(segment_boundaries)
    excluded_alignment_segments = sorted(alignment_segments - set(segment_ids))
    receipt = {
        "schema": "openlogic-ps-Arab-PK-cumulative-computability-epub-independent-validation/1",
        "status": "accepted",
        "inputs": {
            "epub": {"path": str(args.epub), "bytes": epub_bytes, "sha256": epub_sha256},
            "build_record": {"path": str(args.build_record), "sha256": sha256_file(args.build_record)},
            "alignment": {"path": str(args.alignment), "sha256": sha256_file(args.alignment)},
            "reference_map": {"path": str(args.reference_map), "sha256": sha256_file(args.reference_map)},
        },
        "package": {
            "title": title,
            "language": language,
            "page_progression_direction": "rtl",
            "spine": spine_ids,
            "member_count": len(member_records),
            "member_timestamp": list(member_timestamps[0]),
            "members": member_records,
        },
        "coverage": {
            "source_units": len(unit_anchors),
            "first_unit": min(unit_anchors),
            "last_unit": max(unit_anchors),
            "semantic_segments": len(segment_ids),
            "segment_id_set_sha256": sha256_bytes(("\n".join(segment_ids) + "\n").encode("utf-8")),
            "alignment_segments_in_scope": len(alignment_segments),
            "profile_excluded_alignment_segments": excluded_alignment_segments,
        },
        "semantics": {
            "mathml_elements": math_count,
            "mathml_tex_annotations": tex_annotation_count,
            "proof_tree_environments": class_counts["proof-tree"],
            "proof_nodes": proof_nodes,
            "tableau_environments": class_counts["tableau"],
            "tableau_nodes": tableau_nodes,
            "problems": class_counts["prob"],
            "definitions": class_counts["defn"],
            "propositions": class_counts["prop"],
            "theorems": class_counts["thm"],
            "corollaries": class_counts["cor"],
            "lemmas": class_counts["lem"],
            "examples": class_counts["ex"],
            "proofs": class_counts["proof"],
            "editorial_notes": class_counts["editorial"],
            "historical_notes": class_counts["history"],
            "remarks": class_counts["rem"],
            "figures": class_counts["figure"],
            "data_tables": class_counts["data-table"],
            "svg_viewboxes": svg_viewboxes,
        },
        "links": {
            "internal": internal_links,
            "external": external_links,
            "broken": 0,
            "navigation_entries": nav_entries,
        },
        "checks": checks,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "accepted", "epub_sha256": epub_sha256, "output": str(args.output)}))


if __name__ == "__main__":
    main()
