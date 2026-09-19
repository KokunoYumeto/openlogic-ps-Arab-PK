"""Build a deterministic, reflowable EPUB 3 reader for OLP-0056..OLP-0137."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import unicodedata
import uuid
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from lxml import etree

import build_completeness_reader as reader


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_MAP_PATH = ROOT / "evidence" / "EPUB_REFERENCE_MAP.json"
EDITION_VERSION = "0.5.1"
EDITION_MODIFIED = "2026-09-13T00:00:00Z"
EPUB_NAME = "openlogic-ps-Arab-PK-proof-systems-completeness-v0.5.1.epub"
TITLE = "خلاص منطق"
SUBTITLE = "د ثبوت نظامونه او بشپړتيا"
LANGUAGE = "ps-Arab-PK"
XHTML_NS = "http://www.w3.org/1999/xhtml"
EPUB_NS = "http://www.idpf.org/2007/ops"
MATHML_NS = "http://www.w3.org/1998/Math/MathML"
XML_NS = "http://www.w3.org/XML/1998/namespace"

THEOREM_NAMES = {
    "thm": "قضيه",
    "lem": "لم",
    "prop": "قضيه",
    "cor": "نتيجه",
    "defn": "تعريف",
    "ex": "بېلګه",
    "prob": "تمرين",
}
THEOREM_ENVS = frozenset(THEOREM_NAMES)
FORMULA_GREEK = {
    "A": r"\varphi",
    "B": r"\psi",
    "C": r"\chi",
    "D": r"\theta",
    "E": r"\alpha",
    "F": r"\beta",
    "G": r"\gamma",
    "H": r"\delta",
    "K": r"\xi",
    "L": r"\zeta",
    "O": r"\omega",
    "R": r"\rho",
    "S": r"\sigma",
    "T": r"\tau",
}

# Pandoc expands these mandatory-argument macros before texmath emits MathML.
# Macros with optional, slash, or delimited arguments are expanded below.
PANDOC_MACROS = r"""
\newcommand{\LR}[1]{#1}
\newcommand{\RL}[1]{#1}
\newcommand{\True}{\ensuremath{\mathbb{T}}}
\newcommand{\False}{\ensuremath{\mathbb{F}}}
\newcommand{\lfalse}{\ensuremath{\bot}}
\newcommand{\ltrue}{\ensuremath{\top}}
\newcommand{\lif}{\ensuremath{\rightarrow}}
\newcommand{\liff}{\ensuremath{\leftrightarrow}}
\newcommand{\Sequent}{\ensuremath{\Rightarrow}}
\newcommand{\fCenter}{\ensuremath{\,\Rightarrow\,}}
\newcommand{\LeftR}[1]{\ensuremath{{#1}\mathrm{L}}}
\newcommand{\RightR}[1]{\ensuremath{{#1}\mathrm{R}}}
\newcommand{\Weakening}{\ensuremath{\mathrm{W}}}
\newcommand{\Contraction}{\ensuremath{\mathrm{C}}}
\newcommand{\Exchange}{\ensuremath{\mathrm{X}}}
\newcommand{\Cut}{\ensuremath{\mathrm{Cut}}}
\newcommand{\FalseInt}{\ensuremath{\bot_{\mathrm I}}}
\newcommand{\FalseCl}{\ensuremath{\bot_{\mathrm C}}}
\newcommand{\Discharge}[2]{\ensuremath{[#1]^{#2}}}
\newcommand{\MP}{\ensuremath{\mathrm{MP}}}
\newcommand{\QR}{\ensuremath{\mathrm{QR}}}
\newcommand{\Hyp}{\ensuremath{\mathrm{Hyp}}}
\newcommand{\TAss}{\ensuremath{\mathrm{Assumption}}}
\newcommand{\Subst}[3]{\ensuremath{#1[#2/#3]}}
\newcommand{\subst}[2]{\ensuremath{#1/#2}}
\newcommand{\SSubst}[2]{\ensuremath{#1[#2]}}
\newcommand{\Struct}[1]{\ensuremath{\mathfrak{#1}}}
\newcommand{\Lang}[1]{\ensuremath{\mathcal{#1}}}
\newcommand{\Obj}[1]{\ensuremath{\mathsf{#1}}}
\newcommand{\Atom}[2]{\ensuremath{\mathord{#1}(#2)}}
\newcommand{\Domain}[1]{\ensuremath{\left|\mathfrak{#1}\right|}}
\newcommand{\Assign}[2]{\ensuremath{#1^{\mathfrak{#2}}}}
\newcommand{\tuple}[1]{\ensuremath{\langle #1\rangle}}
\newcommand{\Setabs}[2]{\ensuremath{\{#1:#2\}}}
\newcommand{\equivrep}[2]{\ensuremath{[#1]_{#2}}}
\newcommand{\equivclass}[2]{\ensuremath{#1/_{\!#2}}}
\newcommand{\num}[1]{\ensuremath{\overline{#1}}}
\newcommand{\PVar}{\ensuremath{\mathrm{At}_0}}
\newcommand{\PAx}{\ensuremath{\mathrm{Ax}_0}}
\newcommand{\ident}{\ensuremath{\equiv}}
\newcommand{\Nat}{\ensuremath{\mathbb{N}}}
\newcommand{\Rat}{\ensuremath{\mathbb{Q}}}
\newcommand{\Real}{\ensuremath{\mathbb{R}}}
\newcommand{\PosInt}{\ensuremath{\mathbb{Z}^{+}}}
"""


@dataclass
class Unit:
    row: dict
    text: str
    unit_id: str
    part: str
    chapter: str
    section: str
    chapter_number: int
    document_name: str


@dataclass
class Heading:
    level: int
    number: str
    title_tex: str
    title_text: str
    document_name: str
    anchor_id: str


@dataclass
class ProofNode:
    conclusion: str
    children: list["ProofNode"] = field(default_factory=list)
    right_label: str = ""
    left_label: str = ""
    line_style: str = "single"
    relation: str = "inference"


@dataclass
class TableauNode:
    formula: str
    justification: str
    closed: bool
    checked: bool
    children: list["TableauNode"] = field(default_factory=list)


@dataclass
class TransformState:
    tokens: "TokenRegistry"
    reference_map: dict[str, dict]
    reference_targets: dict[str, tuple[str, str]]
    headings: list[Heading] = field(default_factory=list)
    stats: Counter = field(default_factory=Counter)
    internal_links: list[dict] = field(default_factory=list)
    theorem_counter_by_chapter: Counter = field(default_factory=Counter)


class TokenRegistry:
    def __init__(self) -> None:
        self._counter = 0
        self.replacements: dict[str, str] = {}
        self.environment_markers: dict[str, dict] = {}

    def _token(self, prefix: str) -> str:
        self._counter += 1
        return f"EPUB{prefix}{self._counter:08d}TOKEN"

    def anchor(self, anchor_id: str, **attributes: str) -> str:
        token = self._token("ANCHOR")
        attrs = {"id": anchor_id, **attributes}
        rendered = " ".join(
            f'{html.escape(key, quote=True)}="{html.escape(value, quote=True)}"'
            for key, value in attrs.items()
        )
        self.replacements[token] = f"<span {rendered}></span>"
        return token

    def environment(self, kind: str, aria_label: str, **metadata: object) -> str:
        token = self._token("ENV")
        self.environment_markers[token] = {
            "kind": kind,
            "aria_label": aria_label,
            **metadata,
        }
        return token


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def skip_space(text: str, index: int) -> int:
    while index < len(text) and text[index].isspace():
        index += 1
    return index


def read_group(
    text: str, index: int, opener: str = "{", closer: str = "}"
) -> tuple[str, int]:
    if index >= len(text) or text[index] != opener:
        raise ValueError(f"expected {opener!r} at offset {index}: {text[index:index + 40]!r}")
    depth = 1
    cursor = index + 1
    while cursor < len(text):
        char = text[cursor]
        if char == "\\":
            cursor += 2
            continue
        if char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return text[index + 1 : cursor], cursor + 1
        cursor += 1
    raise ValueError(f"unclosed {opener!r} group at offset {index}")


def read_mandatory(text: str, index: int) -> tuple[str, int]:
    index = skip_space(text, index)
    if index >= len(text):
        raise ValueError("missing mandatory TeX argument")
    if text[index] == "{":
        return read_group(text, index)
    if text[index] == "\\":
        match = re.match(r"\\[A-Za-z@]+|\\.", text[index:])
        if not match:
            raise ValueError(f"bad control sequence at offset {index}")
        return match.group(0), index + len(match.group(0))
    return text[index], index + 1


def read_optional(text: str, index: int) -> tuple[str | None, int]:
    probe = skip_space(text, index)
    if probe < len(text) and text[probe] == "[":
        value, end = read_group(text, probe, "[", "]")
        return value, end
    return None, index


def replace_command(
    text: str,
    name: str,
    handler: Callable[[str, int], tuple[str, int]],
) -> str:
    pattern = re.compile(rf"\\{re.escape(name)}(?![A-Za-z@])")
    current = text
    for _ in range(64):
        output: list[str] = []
        cursor = 0
        while True:
            match = pattern.search(current, cursor)
            if not match:
                output.append(current[cursor:])
                break
            output.append(current[cursor : match.start()])
            replacement, end = handler(current, match.end())
            if end <= match.start():
                raise ValueError(f"{name} handler did not advance")
            output.append(replacement)
            cursor = end
        rendered = "".join(output)
        if not pattern.search(rendered):
            return rendered
        if rendered == current:
            raise ValueError(f"{name} handler left an unchanged recursive call")
        current = rendered
    raise ValueError(f"{name} expansion exceeded 64 recursive passes")


def split_top_level(text: str, delimiter: str = ",") -> list[str]:
    parts: list[str] = []
    start = 0
    braces = brackets = parentheses = 0
    cursor = 0
    while cursor < len(text):
        char = text[cursor]
        if char == "\\":
            cursor += 2
            continue
        if char == "{":
            braces += 1
        elif char == "}":
            braces -= 1
        elif char == "[":
            brackets += 1
        elif char == "]":
            brackets -= 1
        elif char == "(":
            parentheses += 1
        elif char == ")":
            parentheses -= 1
        elif char == delimiter and braces == brackets == parentheses == 0:
            parts.append(text[start:cursor])
            start = cursor + 1
        cursor += 1
    parts.append(text[start:])
    return parts


def find_environment_end(text: str, name: str, begin_start: int) -> tuple[int, int]:
    token_pattern = re.compile(rf"\\(begin|end)\{{{re.escape(name)}\}}")
    depth = 0
    for match in token_pattern.finditer(text, begin_start):
        depth += 1 if match.group(1) == "begin" else -1
        if depth == 0:
            return match.start(), match.end()
    raise ValueError(f"unclosed environment {name}")


def replace_environment(
    text: str,
    name: str,
    handler: Callable[[str, int], str],
) -> str:
    pattern = re.compile(rf"\\begin\{{{re.escape(name)}\}}")
    output: list[str] = []
    cursor = 0
    occurrence = 0
    while True:
        match = pattern.search(text, cursor)
        if not match:
            output.append(text[cursor:])
            break
        occurrence += 1
        end_start, end_end = find_environment_end(text, name, match.start())
        output.append(text[cursor : match.start()])
        output.append(handler(text[match.end() : end_start], occurrence))
        cursor = end_end
    return "".join(output)


def anchor_slug(key: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "-", key).strip("-").lower()
    return f"ref-{value}"


def segment_anchor(segment_id: str, boundary: str) -> str:
    return f"seg-{segment_id.lower()}-{boundary}"


def strip_comments(text: str) -> str:
    return re.sub(r"(?<!\\)%[^\r\n]*", "", text)


def extract_context(text: str, driver: bool) -> tuple[str, str, str]:
    file_ids = re.findall(
        r"\\olfileid(?:\[[^\]]*\])?\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}",
        text,
    )
    chapter = re.search(
        r"\\olchapter(?:\[[^\]]*\])?\{([^}]+)\}\{([^}]+)\}\{",
        text,
    )
    if driver:
        if not chapter:
            raise ValueError("chapter driver lacks olchapter")
        return chapter.group(1), chapter.group(2), ""
    if len(file_ids) != 1:
        raise ValueError(f"expected one selected olfileid, found {len(file_ids)}")
    return file_ids[0]


def load_units() -> tuple[list[Unit], dict]:
    manifest_rows = [
        json.loads(line)
        for line in reader.MANIFEST.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    alignment_rows = [
        json.loads(line)
        for line in reader.ALIGNMENT.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    alignment_by_unit: dict[str, list[dict]] = {}
    for row in alignment_rows:
        alignment_by_unit.setdefault(row["unit_id"], []).append(row)
    selected = [row for row in manifest_rows if row["unit_id"] in reader.EXPECTED_IDS]
    if [row["unit_id"] for row in selected] != reader.EXPECTED_IDS:
        raise ValueError("manifest does not contain exact OLP-0056..OLP-0137 sequence")

    units: list[Unit] = []
    chapter_number = 0
    profile_stats: Counter = Counter()
    external_counts: Counter = Counter()
    input_files: list[dict] = []
    for row in selected:
        upstream = ROOT / "upstream" / row["source_path"]
        target = ROOT / "ps-Arab-PK" / row["source_path"]
        if not upstream.is_file() or not target.is_file():
            raise FileNotFoundError(row["unit_id"])
        if sha256(upstream) != row["source_sha256"]:
            raise ValueError(f"source hash mismatch for {row['unit_id']}")
        target_text = target.read_text(encoding="utf-8")
        if unicodedata.normalize("NFC", target_text) != target_text:
            raise ValueError(f"target is not NFC: {row['unit_id']}")
        is_driver = row["unit_id"] in reader.DRIVER_IDS
        prepared, unit_profile, unit_external = reader.prepare_unit(
            target_text,
            driver=is_driver,
            alignment_rows=alignment_by_unit.get(row["unit_id"], []),
        )
        if is_driver:
            chapter_number += 1
        if chapter_number == 0:
            raise ValueError("content precedes first chapter driver")
        part, chapter, section = extract_context(prepared, is_driver)
        units.append(
            Unit(
                row=row,
                text=prepared,
                unit_id=row["unit_id"],
                part=part,
                chapter=chapter,
                section=section,
                chapter_number=chapter_number,
                document_name=f"chapter-{chapter_number:02d}.xhtml",
            )
        )
        profile_stats.update(unit_profile)
        external_counts.update(unit_external)
        input_files.append(
            {
                "unit_id": row["unit_id"],
                "source_path": f"upstream/{row['source_path']}",
                "source_sha256": sha256(upstream),
                "target_path": f"ps-Arab-PK/{row['source_path']}",
                "target_sha256": sha256(target),
                "role": "chapter_driver" if is_driver else "reader_unit",
            }
        )
    if chapter_number != 7:
        raise ValueError(f"expected seven chapters, found {chapter_number}")
    expected_external = Counter(
        {key: value["occurrences"] for key, value in reader.EXTERNAL_REFERENCES.items()}
    )
    if external_counts != expected_external:
        raise ValueError(f"external reference count mismatch: {external_counts}")
    translated_bundle_units = sum(
        1
        for row in manifest_rows
        if (ROOT / "ps-Arab-PK" / row["source_path"]).is_file()
    )
    provenance = {
        "profile_resolution": {
            "active_tags": sorted(reader.ACTIVE_TAGS),
            "inactive_tags": sorted(reader.INACTIVE_TAGS),
            "resolved_construct_counts": dict(sorted(profile_stats.items())),
        },
        "external_reference_occurrences": sum(external_counts.values()),
        "translated_bundle_units": translated_bundle_units,
        "input_files": input_files,
    }
    return units, provenance


def load_reference_map() -> tuple[dict, dict[str, dict]]:
    record = json.loads(REFERENCE_MAP_PATH.read_text(encoding="utf-8"))
    if record["schema"] != "openlogic-ps-Arab-PK-epub-reference-map/1":
        raise ValueError("unexpected EPUB reference map schema")
    references = record["references"]
    if record["reference_count"] != 246 or len(references) != 246:
        raise ValueError("reference map does not contain 246 accepted labels")
    return record, references


def build_reference_targets(
    units: list[Unit], reference_map: dict[str, dict]
) -> dict[str, tuple[str, str]]:
    targets: dict[str, tuple[str, str]] = {}
    segment_start_pattern = re.compile(
        r"\\phantomsection\\label\{olpseg:([^}:]+-[^}:]+):start\}"
    )
    for unit in units:
        chapter_key = f"{unit.part}:{unit.chapter}::chap"
        if not unit.section:
            targets[chapter_key] = (unit.document_name, anchor_slug(chapter_key))
        else:
            section_key = f"{unit.part}:{unit.chapter}:{unit.section}:sec"
            targets[section_key] = (unit.document_name, anchor_slug(section_key))

        starts = [
            (match.start(), match.group(1))
            for match in segment_start_pattern.finditer(unit.text)
        ]
        if not starts:
            raise ValueError(f"{unit.unit_id} has no semantic segment anchors")
        positions = [position for position, _ in starts]
        for match in re.finditer(r"\\ollabel\{([^}]+)\}", unit.text):
            index = bisect.bisect_right(positions, match.start()) - 1
            if index < 0:
                raise ValueError(f"{unit.unit_id} label precedes first segment")
            key = f"{unit.part}:{unit.chapter}:{unit.section}:{match.group(1)}"
            if key in targets:
                raise ValueError(f"duplicate accepted label {key}")
            segment_id = starts[index][1]
            targets[key] = (
                unit.document_name,
                segment_anchor(segment_id, "start"),
            )
    if set(targets) != set(reference_map):
        missing = sorted(set(reference_map) - set(targets))
        extra = sorted(set(targets) - set(reference_map))
        raise ValueError(
            f"reference target mismatch; missing={missing[:8]}, extra={extra[:8]}"
        )
    return targets


def verify_theorem_numbering(
    units: list[Unit], reference_map: dict[str, dict]
) -> Counter:
    counters: Counter = Counter()
    counts: Counter = Counter()
    pattern = re.compile(r"\\begin\{(" + "|".join(sorted(THEOREM_ENVS)) + r")\}")
    for unit in units:
        for match in pattern.finditer(unit.text):
            env = match.group(1)
            counters[unit.chapter_number] += 1
            counts[env] += 1
            expected = f"{unit.chapter_number}.{counters[unit.chapter_number]}"
            end_start, _ = find_environment_end(unit.text, env, match.start())
            content = unit.text[match.end() : end_start]
            for label in re.findall(r"\\ollabel\{([^}]+)\}", content):
                key = f"{unit.part}:{unit.chapter}:{unit.section}:{label}"
                accepted = reference_map[key]
                if (
                    accepted["target"].startswith("thm.")
                    and accepted["number"] != expected
                ):
                    raise ValueError(
                        f"theorem numbering mismatch for {key}: "
                        f"{expected} vs {accepted['number']}"
                    )
    return counts


def plain_title(text: str) -> str:
    replacements = {
        r"\lnot": "¬",
        r"\land": "∧",
        r"\lor": "∨",
        r"\lif": "→",
        r"\liff": "↔",
        r"\lexists": "∃",
        r"\lforall": "∀",
        r"\lfalse": "⊥",
        r"\ltrue": "⊤",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = re.sub(r"\\(?:LR|RL|emph|textbf|textrm)\{([^{}]*)\}", r"\1", text)
    text = text.replace("$", "").replace("~", " ").replace("--", "–")
    text = re.sub(r"\\[A-Za-z@]+", "", text)
    text = text.replace("{", "").replace("}", "")
    return " ".join(text.split())


def reference_link(state: TransformState, key: str, current_document: str) -> str:
    if key not in state.reference_map or key not in state.reference_targets:
        raise ValueError(f"unresolved internal reference: {key}")
    target_document, anchor = state.reference_targets[key]
    href = (
        f"#{anchor}"
        if target_document == current_document
        else f"{target_document}#{anchor}"
    )
    tex_href = href.replace("#", r"\#")
    number = state.reference_map[key]["number"]
    state.stats["internal_reference_occurrences"] += 1
    state.internal_links.append(
        {"key": key, "from": current_document, "href": href, "text": number}
    )
    return rf"\href{{{tex_href}}}{{\LR{{{number}}}}}"


def expand_tagrefs(text: str, unit: Unit, state: TransformState) -> str:
    def handler(source: str, index: int) -> tuple[str, int]:
        argument, end = read_mandatory(source, index)
        rendered: list[str] = []
        for item in split_top_level(argument):
            match = re.fullmatch(
                r"\s*([A-Za-z0-9]+)\s*/\s*\{([^{}]+)\}\s*", item, re.S
            )
            if not match:
                raise ValueError(f"bad tagrefs item: {item!r}")
            tag, key = match.groups()
            if tag in reader.ACTIVE_TAGS:
                rendered.append(reference_link(state, key, unit.document_name))
        if not rendered:
            raise ValueError("tagrefs selected no active references")
        state.stats["tagrefs_occurrences"] += 1
        state.stats["tagrefs_selected_links"] += len(rendered)
        return "، ".join(rendered), end

    return replace_command(text, "tagrefs", handler)


def expand_olrefs(text: str, unit: Unit, state: TransformState) -> str:
    text = text.replace(r"\Olref", r"\olref")

    def handler(source: str, index: int) -> tuple[str, int]:
        options: list[str] = []
        cursor = index
        for _ in range(3):
            value, end = read_optional(source, cursor)
            if value is None:
                break
            options.append(value)
            cursor = end
        label, cursor = read_mandatory(source, cursor)
        key = reader.reference_key(
            unit.part, unit.chapter, unit.section, options, label
        )
        return reference_link(state, key, unit.document_name), cursor

    return replace_command(text, "olref", handler)


def replace_source_structure(text: str, unit: Unit, state: TransformState) -> str:
    text = (
        state.tokens.anchor(
            f"unit-{unit.unit_id.lower()}",
            **{"class": "source-unit", "data-source-unit": unit.unit_id},
        )
        + "\n"
        + text
    )

    def start_anchor(match: re.Match[str]) -> str:
        segment_id = match.group(1)
        state.stats["segment_start_anchors"] += 1
        return state.tokens.anchor(
            segment_anchor(segment_id, "start"),
            **{
                "class": "source-segment",
                "data-source-segment": segment_id,
                "data-boundary": "start",
            },
        )

    def end_anchor(match: re.Match[str]) -> str:
        segment_id = match.group(1)
        state.stats["segment_end_anchors"] += 1
        return state.tokens.anchor(
            segment_anchor(segment_id, "end"),
            **{
                "class": "source-segment",
                "data-source-segment": segment_id,
                "data-boundary": "end",
            },
        )

    text = re.sub(
        r"\\phantomsection\\label\{olpseg:([^}:]+-[^}:]+):start\}",
        start_anchor,
        text,
    )
    text = re.sub(
        r"\\label\{olpseg:([^}:]+-[^}:]+):end\}", end_anchor, text
    )
    text = re.sub(r"\\ollabel\{[^}]+\}", "", text)

    def file_id_handler(source: str, index: int) -> tuple[str, int]:
        cursor = index
        for _ in range(3):
            _, cursor = read_mandatory(source, cursor)
        return "", cursor

    text = replace_command(text, "olfileid", file_id_handler)

    def chapter_handler(source: str, index: int) -> tuple[str, int]:
        _, cursor = read_optional(source, index)
        part, cursor = read_mandatory(source, cursor)
        chapter, cursor = read_mandatory(source, cursor)
        title, cursor = read_mandatory(source, cursor)
        key = f"{part}:{chapter}::chap"
        anchor = anchor_slug(key)
        accepted_number = state.reference_map[key]["number"]
        state.headings.append(
            Heading(
                level=1,
                number=accepted_number,
                title_tex=title,
                title_text=plain_title(title),
                document_name=unit.document_name,
                anchor_id=anchor,
            )
        )
        token = state.tokens.anchor(anchor, **{"class": "reference-anchor"})
        return token + "\n" + rf"\section{{{title}}}", cursor

    text = replace_command(text, "olchapter", chapter_handler)

    def section_handler(source: str, index: int) -> tuple[str, int]:
        _, cursor = read_optional(source, index)
        title, cursor = read_mandatory(source, cursor)
        key = f"{unit.part}:{unit.chapter}:{unit.section}:sec"
        anchor = anchor_slug(key)
        accepted_number = state.reference_map[key]["number"]
        state.headings.append(
            Heading(
                level=2,
                number=accepted_number,
                title_tex=title,
                title_text=plain_title(title),
                document_name=unit.document_name,
                anchor_id=anchor,
            )
        )
        token = state.tokens.anchor(anchor, **{"class": "reference-anchor"})
        return token + "\n" + rf"\subsection{{{title}}}", cursor

    text = replace_command(text, "olsection", section_handler)
    subsection_number = 0

    def subsection_handler(source: str, index: int) -> tuple[str, int]:
        nonlocal subsection_number
        title, cursor = read_mandatory(source, index)
        subsection_number += 1
        section_key = f"{unit.part}:{unit.chapter}:{unit.section}:sec"
        number = f"{state.reference_map[section_key]['number']}.{subsection_number}"
        anchor = f"sub-{unit.unit_id.lower()}-{subsection_number:02d}"
        state.headings.append(
            Heading(
                level=3,
                number=number,
                title_tex=title,
                title_text=plain_title(title),
                document_name=unit.document_name,
                anchor_id=anchor,
            )
        )
        token = state.tokens.anchor(anchor, **{"class": "subsection-anchor"})
        return token + "\n" + rf"\subsubsection{{{title}}}", cursor

    text = replace_command(text, "subsection", subsection_handler)
    text = expand_tagrefs(text, unit, state)
    text = expand_olrefs(text, unit, state)
    if re.search(
        r"\\(?:olchapter|olsection|olfileid|ollabel|olref|tagrefs)\b", text
    ):
        raise ValueError(f"OpenLogic structural macro remains in {unit.unit_id}")
    return text


def expand_indcase(text: str) -> str:
    def handler(source: str, index: int) -> tuple[str, int]:
        cursor = skip_space(source, index)
        starred = cursor < len(source) and source[cursor] == "*"
        if starred:
            cursor += 1
        unique = cursor < len(source) and source[cursor] == "!"
        if unique:
            cursor += 1
        formula, cursor = read_mandatory(source, cursor)
        complex_formula, cursor = read_mandatory(source, cursor)
        case_text, cursor = read_mandatory(source, cursor)
        case_text = case_text.replace(r"\indfrm", formula).replace(
            r"\indcomplex", complex_formula
        )
        if starred:
            lead = r"\LR{$" + formula + "$}: "
        else:
            lead = (
                r"\LR{$"
                + formula
                + r" \ident "
                + complex_formula
                + "$}: "
            )
        if unique:
            lead = (
                r"\LR{$"
                + formula
                + r" \ident "
                + complex_formula
                + "$}: "
            )
        return lead + case_text, cursor

    return replace_command(text, "indcase", handler)


def strip_math_wrapper(value: str) -> str:
    value = value.strip()
    while value.startswith(r"\LR"):
        match = re.match(r"\\LR(?![A-Za-z@])", value)
        if not match:
            break
        argument, end = read_mandatory(value, match.end())
        if value[end:].strip():
            break
        value = argument.strip()
    if len(value) >= 2 and value[0] == "$" and value[-1] == "$":
        value = value[1:-1].strip()
    # Centered bussproofs arguments occasionally mix several inline-math
    # spans (for example ``[$A$]$^n$``). The EPUB renderer wraps the whole
    # conclusion in one math span, so nested dollar delimiters must be removed.
    value = re.sub(r"(?<!\\)\$", "", value).strip()
    return value


def proof_argument(text: str, index: int, centered: bool) -> tuple[str, int]:
    cursor = skip_space(text, index)
    if centered:
        value, cursor = read_mandatory(text, cursor)
        return strip_math_wrapper(value), cursor
    if cursor >= len(text) or text[cursor] != "$":
        raise ValueError(
            f"expected dollar-delimited proof conclusion: "
            f"{text[cursor:cursor + 80]!r}"
        )
    end = cursor + 1
    while end < len(text):
        if text[end] == "$" and text[end - 1] != "\\":
            return text[cursor + 1 : end].strip(), end + 1
        end += 1
    raise ValueError("unterminated proof conclusion")


def parse_proof_body(body: str) -> tuple[list[ProofNode], Counter, list[str]]:
    body = strip_comments(body)
    anchor_tokens = re.findall(r"EPUBANCHOR\d{8}TOKEN", body)
    body = re.sub(r"EPUBANCHOR\d{8}TOKEN", "", body)
    stack: list[ProofNode] = []
    roots: list[ProofNode] = []
    pending_right = ""
    pending_left = ""
    pending_line = "single"
    stats: Counter = Counter()
    cursor = 0

    def flush() -> None:
        nonlocal stack
        if not stack:
            return
        if len(stack) != 1:
            raise ValueError(f"proof display has {len(stack)} uncombined roots")
        roots.append(stack[0])
        stack = []

    while cursor < len(body):
        cursor = skip_space(body, cursor)
        if cursor >= len(body):
            break
        if body.startswith(r"\\", cursor):
            cursor += 2
            _, cursor = read_optional(body, cursor)
            continue
        if body.startswith((r"\[", r"\]", r"\(", r"\)"), cursor):
            cursor += 2
            continue
        if body[cursor] != "\\":
            if body[cursor] in "{}[]&":
                cursor += 1
                continue
            snippet = body[cursor : cursor + 100].strip()
            if not snippet:
                break
            raise ValueError(f"unexpected proof-layout text: {snippet!r}")
        command_match = re.match(r"\\([A-Za-z@]+)", body[cursor:])
        if not command_match:
            raise ValueError(
                f"bad proof control sequence at {cursor}: "
                f"{body[cursor:cursor + 120]!r}"
            )
        command = command_match.group(1)
        cursor += len(command_match.group(0))

        if command in {"begin", "end"}:
            environment, cursor = read_mandatory(body, cursor)
            if environment != "tabular":
                raise ValueError(
                    f"unexpected proof layout environment {environment}"
                )
            if command == "begin":
                _, cursor = read_mandatory(body, cursor)
            continue
        if command in {
            "bottomAlignProof",
            "hfill",
            "noindent",
            "qquad",
            "quad",
        }:
            continue
        if command == "insertBetweenHyps":
            _, cursor = read_mandatory(body, cursor)
            stats["layout_insert_between_hypotheses"] += 1
            continue
        if command == "noLine":
            pending_line = "none"
            continue
        if command == "doubleLine":
            pending_line = "double"
            continue
        if command == "RightLabel":
            pending_right, cursor = read_mandatory(body, cursor)
            continue
        if command == "LeftLabel":
            pending_left, cursor = read_mandatory(body, cursor)
            continue
        if command == "DischargeRule":
            pending_right, cursor = read_mandatory(body, cursor)
            pending_left, cursor = read_mandatory(body, cursor)
            stats["discharge_rules"] += 1
            continue
        if command == "DisplayProof":
            flush()
            stats["explicit_displays"] += 1
            continue

        match = re.fullmatch(
            r"(Axiom|Deduce|UnaryInf|BinaryInf|TrinaryInf|QuaternaryInf)(C?)",
            command,
        )
        if not match:
            raise ValueError(f"unexpected proof command {command}")
        base, centered_suffix = match.groups()
        conclusion, cursor = proof_argument(body, cursor, bool(centered_suffix))
        if base == "Axiom":
            stack.append(ProofNode(conclusion=conclusion, relation="assumption"))
            stats["assumptions"] += 1
            continue
        arity = {
            "Deduce": 1,
            "UnaryInf": 1,
            "BinaryInf": 2,
            "TrinaryInf": 3,
            "QuaternaryInf": 4,
        }[base]
        if len(stack) < arity:
            if base == "Deduce" and not stack:
                children: list[ProofNode] = []
            else:
                raise ValueError(
                    f"{base} needs {arity} premises, stack has {len(stack)}"
                )
        else:
            children = stack[-arity:]
            del stack[-arity:]
        stack.append(
            ProofNode(
                conclusion=conclusion,
                children=children,
                right_label=pending_right,
                left_label=pending_left,
                line_style=pending_line,
                relation="deduction" if base == "Deduce" else "inference",
            )
        )
        pending_right = pending_left = ""
        pending_line = "single"
        stats["inferences"] += 1
    flush()
    if pending_right or pending_left or pending_line != "single":
        raise ValueError("unconsumed proof layout modifier")
    stats["roots"] = len(roots)
    stats["anchor_tokens"] = len(anchor_tokens)
    stats["nodes"] = stats["assumptions"] + stats["inferences"]
    return roots, stats, anchor_tokens


def render_proof_node(node: ProofNode) -> str:
    if node.conclusion:
        line = r"\item \LR{$" + node.conclusion + "$}"
    else:
        line = r"\item \emph{تش ځاے}"
    labels = [label for label in (node.right_label, node.left_label) if label]
    if labels:
        joined = r"\; ".join(labels)
        line += r" \quad \emph{قاعده:} \LR{$" + joined + "$}"
    if node.line_style == "double":
        line += r" \emph{(دوه کرښې)}"
    elif node.line_style == "none":
        line += r" \emph{(بې کرښې پړاو)}"
    if node.children:
        line += "\n\\begin{itemize}\n"
        line += "\n".join(render_proof_node(child) for child in node.children)
        line += "\n\\end{itemize}"
    return line


def render_proof_block(
    body: str,
    state: TransformState,
    kind: str,
    heading: str,
) -> str:
    roots, stats, anchors = parse_proof_body(body)
    state.stats.update({f"proof_{key}": value for key, value in stats.items()})
    state.stats[f"{kind}_environments"] += 1
    marker = state.tokens.environment(
        kind,
        heading,
        expected_list_items=stats["assumptions"] + stats["inferences"],
        content_preview=roots[0].conclusion[:160] if roots else "",
    )
    rendered = "\n".join(anchors)
    rendered += "\n\\begin{quote}\n"
    rendered += rf"\textbf{{{marker} {heading}}}\par" + "\n"
    rendered += "\\begin{itemize}\n"
    rendered += "\n".join(render_proof_node(root) for root in roots)
    rendered += "\n\\end{itemize}\n\\end{quote}\n"
    return rendered


def is_tableau_child(text: str, index: int) -> bool:
    if index >= len(text) or text[index] != "[":
        return False
    probe = skip_space(text, index + 1)
    return text.startswith(r"\sFmla", probe)


def parse_tableau_node(text: str, index: int) -> tuple[TableauNode, int]:
    if not is_tableau_child(text, index):
        raise ValueError(f"expected tableau node at {index}")
    cursor = index + 1
    header: list[str] = []
    children: list[TableauNode] = []
    while cursor < len(text):
        char = text[cursor]
        if char == "{":
            group, end = read_group(text, cursor)
            header.append("{" + group + "}")
            cursor = end
            continue
        if char == "[":
            if is_tableau_child(text, cursor):
                child, cursor = parse_tableau_node(text, cursor)
                children.append(child)
            else:
                group, end = read_group(text, cursor, "[", "]")
                header.append("[" + group + "]")
                cursor = end
            continue
        if char == "]":
            cursor += 1
            break
        header.append(char)
        cursor += 1
    else:
        raise ValueError("unterminated tableau node")
    header_text = "".join(header).strip()
    formula_match = re.search(r"\\sFmla(?![A-Za-z@])", header_text)
    if not formula_match:
        raise ValueError(f"tableau node lacks sFmla: {header_text!r}")
    sign, formula_end = read_mandatory(header_text, formula_match.end())
    formula, formula_end = read_mandatory(header_text, formula_end)
    optional, formula_end = read_optional(header_text, formula_end)
    formula_tex = rf"\sFmla{{{sign}}}{{{formula}}}"
    if optional is not None:
        formula_tex += f"[{optional}]"
    attributes_text = (
        header_text[: formula_match.start()] + header_text[formula_end:]
    )
    justification = ""
    closed = checked = False
    for part in split_top_level(attributes_text):
        part = part.strip()
        if not part:
            continue
        if part.startswith("just"):
            match = re.match(r"just\s*=\s*", part)
            if not match:
                raise ValueError(f"bad tableau justification: {part!r}")
            raw_value = part[match.end() :].strip()
            if raw_value.startswith("{"):
                value, end = read_group(raw_value, 0)
                if raw_value[end:].strip():
                    raise ValueError(
                        f"trailing tableau justification material: {part!r}"
                    )
                justification = value
            else:
                justification = raw_value
        elif part == "close":
            closed = True
        elif part == "checked":
            checked = True
        elif re.fullmatch(r"move\s+by\s*=\s*[-+]?\d+", part):
            # Forest-only horizontal positioning; the EPUB branch list reflows.
            pass
        else:
            raise ValueError(f"unknown tableau attribute: {part!r}")
    return (
        TableauNode(
            formula=formula_tex,
            justification=justification,
            closed=closed,
            checked=checked,
            children=children,
        ),
        cursor,
    )


def render_tableau_node(node: TableauNode) -> str:
    rendered = r"\item \LR{$" + node.formula + "$}"
    if node.justification:
        rendered += (
            r" \quad \emph{قاعده:} \LR{$"
            + node.justification
            + "$}"
        )
    if node.checked:
        rendered += r" \emph{(کتل شوے)}"
    if node.closed:
        rendered += r" \textbf{(تړلې څانګه)}"
    if node.children:
        rendered += "\n\\begin{itemize}\n"
        rendered += "\n".join(
            render_tableau_node(child) for child in node.children
        )
        rendered += "\n\\end{itemize}"
    return rendered


def render_tableau_block(body: str, state: TransformState) -> str:
    body = strip_comments(body)
    anchor_tokens = re.findall(r"EPUBANCHOR\d{8}TOKEN", body)
    body = re.sub(r"EPUBANCHOR\d{8}TOKEN", "", body).strip()
    if body.startswith("{"):
        _, option_end = read_group(body, 0)
        body = body[option_end:].lstrip()
    roots: list[TableauNode] = []
    cursor = 0
    while cursor < len(body):
        cursor = skip_space(body, cursor)
        if cursor >= len(body):
            break
        if not is_tableau_child(body, cursor):
            raise ValueError(
                f"unexpected tableau material: {body[cursor:cursor + 100]!r}"
            )
        root, cursor = parse_tableau_node(body, cursor)
        roots.append(root)
    if len(roots) != 1:
        raise ValueError(f"tableau environment has {len(roots)} roots")

    def walk(node: TableauNode) -> tuple[int, int, int]:
        nodes = 1
        closed = int(node.closed)
        branches = int(len(node.children) > 1)
        for child in node.children:
            child_nodes, child_closed, child_branches = walk(child)
            nodes += child_nodes
            closed += child_closed
            branches += child_branches
        return nodes, closed, branches

    nodes, closed, branches = walk(roots[0])
    state.stats["tableau_environments"] += 1
    state.stats["tableau_nodes"] += nodes
    state.stats["tableau_closed_branches"] += closed
    state.stats["tableau_branch_points"] += branches
    marker = state.tokens.environment(
        "tableau",
        "تابلو",
        expected_list_items=nodes,
        content_preview=roots[0].formula[:160],
    )
    rendered = "\n".join(anchor_tokens)
    rendered += "\n\\begin{quote}\n"
    rendered += rf"\textbf{{{marker} تابلو}}\par" + "\n"
    rendered += "\\begin{itemize}\n" + render_tableau_node(roots[0])
    rendered += "\n\\end{itemize}\n\\end{quote}\n"
    return rendered


def split_derivation_rows(body: str) -> list[str]:
    rows: list[str] = []
    start = 0
    braces = 0
    cursor = 0
    while cursor < len(body) - 1:
        char = body[cursor]
        if char == "{":
            braces += 1
        elif char == "}":
            braces -= 1
        elif char == "\\" and body[cursor + 1] == "\\" and braces == 0:
            rows.append(body[start:cursor])
            cursor += 2
            _, cursor = read_optional(body, cursor)
            start = cursor
            continue
        cursor += 1
    tail = body[start:].strip()
    if tail:
        rows.append(tail)
    return rows


def render_derivation(body: str, state: TransformState) -> str:
    rows = []
    for raw in split_derivation_rows(strip_comments(body)):
        if "&" not in raw:
            raise ValueError(f"bad derivation row: {raw!r}")
        _, content = raw.split("&", 1)
        rows.append(content.strip().replace("&", r"\quad"))
    state.stats["derivation_environments"] += 1
    state.stats["derivation_rows"] += len(rows)
    marker = state.tokens.environment(
        "derivation",
        "اشتقاق",
        expected_list_items=len(rows),
        content_preview=rows[0][:160] if rows else "",
    )
    return (
        "\\begin{quote}\n"
        + rf"\textbf{{{marker} اشتقاق}}\par"
        + "\n\\begin{enumerate}\n"
        + "\n".join(rf"\item {row}" for row in rows)
        + "\n\\end{enumerate}\n\\end{quote}"
    )


def transform_formal_environments(
    text: str, state: TransformState
) -> str:
    # Rule panels contain bussproofs commands directly in fixed-width tables.
    # Parse their proof stack and retain the formal tree, discarding only layout.
    text = replace_environment(
        text,
        "defish",
        lambda body, _: render_proof_block(
            body, state, "proof-rules", "ثبوتي قاعدې"
        ),
    )
    text = replace_environment(
        text,
        "prooftree",
        lambda body, _: render_proof_block(
            body, state, "proof-tree", "ثبوتي ونه"
        ),
    )
    text = replace_environment(
        text,
        "oltableau",
        lambda body, _: render_tableau_block(body, state),
    )
    text = replace_environment(
        text,
        "tableau",
        lambda body, _: render_tableau_block(body, state),
    )
    text = replace_environment(
        text,
        "derivation",
        lambda body, _: render_derivation(body, state),
    )
    return text


def transform_semantic_environments(
    text: str, chapter_number: int, state: TransformState
) -> str:
    pattern = re.compile(
        r"\\begin\{(" + "|".join(sorted(THEOREM_ENVS)) + r")\}"
    )
    output: list[str] = []
    cursor = 0
    while True:
        match = pattern.search(text, cursor)
        if not match:
            output.append(text[cursor:])
            break
        env = match.group(1)
        end_start, end_end = find_environment_end(text, env, match.start())
        content = text[match.end() : end_start]
        probe = skip_space(content, 0)
        optional_title = None
        if probe < len(content) and content[probe] == "[":
            optional_title, content_start = read_group(
                content, probe, "[", "]"
            )
            content = content[content_start:]
        state.theorem_counter_by_chapter[chapter_number] += 1
        number = (
            f"{chapter_number}."
            f"{state.theorem_counter_by_chapter[chapter_number]}"
        )
        name = THEOREM_NAMES[env]
        heading = f"{name} {number}"
        if optional_title:
            heading += f": {optional_title}"
        marker = state.tokens.environment(
            f"semantic {env}", f"{name} {number}"
        )
        replacement = (
            "\\begin{quote}\n"
            + rf"\textbf{{{marker} {heading}}}\par"
            + "\n"
            + content
            + "\n\\end{quote}"
        )
        output.append(text[cursor : match.start()])
        output.append(replacement)
        cursor = end_end
        state.stats[f"environment_{env}"] += 1
    return "".join(output)


def transform_named_quote_environment(
    text: str,
    env: str,
    state: TransformState,
    kind: str,
    heading: str,
) -> str:
    def handler(body: str, _: int) -> str:
        marker = state.tokens.environment(kind, heading)
        state.stats[f"environment_{env}"] += 1
        return (
            "\\begin{quote}\n"
            + rf"\textbf{{{marker} {heading}}}\par"
            + "\n"
            + body
            + "\n\\end{quote}"
        )

    return replace_environment(text, env, handler)


def unwrap_environment(
    text: str, env: str, state: TransformState
) -> str:
    def handler(body: str, _: int) -> str:
        state.stats[f"environment_{env}"] += 1
        return body

    return replace_environment(text, env, handler)


def split_intertext_displays(
    text: str, state: TransformState
) -> str:
    def for_environment(
        source: str, environment: str
    ) -> str:
        def handler(body: str, _: int) -> str:
            if r"\intertext" not in body:
                return (
                    rf"\begin{{{environment}}}"
                    + body
                    + rf"\end{{{environment}}}"
                )
            output: list[str] = []
            cursor = 0
            while True:
                match = re.search(
                    r"\\intertext(?![A-Za-z@])", body[cursor:]
                )
                if not match:
                    tail = body[cursor:]
                    tail = re.sub(r"\\\\\s*\Z", "", tail).strip()
                    if tail:
                        output.append(
                            rf"\begin{{{environment}}}"
                            + "\n"
                            + tail
                            + "\n"
                            + rf"\end{{{environment}}}"
                        )
                    break
                start = cursor + match.start()
                command_end = cursor + match.end()
                before = body[cursor:start]
                before = re.sub(
                    r"\\\\\s*\Z", "", before
                ).strip()
                if before:
                    output.append(
                        rf"\begin{{{environment}}}"
                        + "\n"
                        + before
                        + "\n"
                        + rf"\end{{{environment}}}"
                    )
                prose, cursor = read_mandatory(
                    body, command_end
                )
                output.append(prose.strip())
                state.stats["intertext_rows"] += 1
            return "\n\n".join(output)

        return replace_environment(
            source, environment, handler
        )

    text = for_environment(text, "align")
    text = for_environment(text, "align*")
    return text


def expand_optional_notation(text: str) -> str:
    # Preserve TeX's literal-command idiom before expanding the named command.
    # For example, \texttt{\string\sFmla} must become visible code rather than
    # an empty signed-formula call that consumes the following Pashto word.
    text = re.sub(
        r"\\string\\([A-Za-z@]+)",
        lambda match: rf"\textbackslash{{}}{match.group(1)}",
        text,
    )
    text = expand_indcase(text)

    def intro_elim(name: str, suffix: str) -> None:
        nonlocal text

        def handler(source: str, index: int) -> tuple[str, int]:
            operator, cursor = read_mandatory(source, index)
            subscript, cursor = read_optional(source, cursor)
            result = rf"\ensuremath{{{{{operator}}}\mathrm{{{suffix}}}"
            if subscript is not None:
                result += rf"_{{{subscript}}}"
            result += "}"
            return result, cursor

        text = replace_command(text, name, handler)

    intro_elim("Intro", "I")
    intro_elim("Elim", "E")

    def trule_handler(source: str, index: int) -> tuple[str, int]:
        sign, cursor = read_mandatory(source, index)
        operator, cursor = read_mandatory(source, cursor)
        line, cursor = read_optional(source, cursor)
        result = rf"\ensuremath{{{{{operator}}}{{{sign}}}"
        if line is not None:
            result += rf"\,{line}"
        result += "}"
        return result, cursor

    text = replace_command(text, "TRule", trule_handler)

    def sfmla_handler(source: str, index: int) -> tuple[str, int]:
        sign, cursor = read_mandatory(source, index)
        formula, cursor = read_mandatory(source, cursor)
        prefix, cursor = read_optional(source, cursor)
        content = (
            (rf"{prefix}\," if prefix is not None else "")
            + rf"{sign}\;{formula}"
        )
        return rf"\ensuremath{{{content}}}", cursor

    text = replace_command(text, "sFmla", sfmla_handler)

    def quantifier_handler(
        symbol: str, unique: bool = False
    ) -> Callable[[str, int], tuple[str, int]]:
        def handler(source: str, index: int) -> tuple[str, int]:
            cursor = skip_space(source, index)
            bang = (
                unique
                and cursor < len(source)
                and source[cursor] == "!"
            )
            if bang:
                cursor += 1
            variable, cursor = read_optional(source, cursor)
            matrix, cursor = read_optional(source, cursor)
            result = symbol + ("!" if bang else "")
            if variable is not None:
                result += f" {variable}"
            if matrix is not None:
                result += rf"\,{matrix}"
            return result, cursor

        return handler

    text = replace_command(
        text, "lexists", quantifier_handler(r"\exists", True)
    )
    text = replace_command(
        text, "lforall", quantifier_handler(r"\forall")
    )

    def eq_handler(source: str, index: int) -> tuple[str, int]:
        cursor = skip_space(source, index)
        negated = cursor < len(source) and source[cursor] == "/"
        if negated:
            cursor += 1
        left, cursor2 = read_optional(source, cursor)
        right, cursor3 = read_optional(source, cursor2)
        symbol = r"\neq" if negated else "="
        if left is None:
            return symbol, cursor
        if right is None:
            raise ValueError("eq has only one optional operand")
        return f"{left} {symbol} {right}", cursor3

    text = replace_command(text, "eq", eq_handler)

    def relation_handler(
        symbol: str, negative: str
    ) -> Callable[[str, int], tuple[str, int]]:
        def handler(source: str, index: int) -> tuple[str, int]:
            cursor = skip_space(source, index)
            negated = cursor < len(source) and source[cursor] == "/"
            if negated:
                cursor += 1
            subscript, cursor = read_optional(source, cursor)
            result = negative if negated else symbol
            if subscript is not None:
                result += rf"_{{{subscript}}}"
            return result + "{}", cursor

        return handler

    text = replace_command(
        text, "Proves", relation_handler(r"\vdash", r"\nvdash")
    )
    text = replace_command(
        text, "Entails", relation_handler(r"\vDash", r"\nvDash")
    )

    def sat_handler(source: str, index: int) -> tuple[str, int]:
        cursor = skip_space(source, index)
        negated = cursor < len(source) and source[cursor] == "/"
        if negated:
            cursor += 1
        structure, cursor = read_mandatory(source, cursor)
        formula, cursor = read_mandatory(source, cursor)
        assignment, cursor = read_optional(source, cursor)
        left = rf"\Struct{{{structure}}}"
        if assignment is not None:
            left += f", {assignment}"
        relation = r"\nvDash" if negated else r"\vDash"
        return (
            rf"\ensuremath{{{left} {relation} {formula}}}",
            cursor,
        )

    text = replace_command(text, "Sat", sat_handler)

    def psat_handler(source: str, index: int) -> tuple[str, int]:
        cursor = skip_space(source, index)
        negated = cursor < len(source) and source[cursor] == "/"
        if negated:
            cursor += 1
        valuation, cursor = read_mandatory(source, cursor)
        formula, cursor = read_mandatory(source, cursor)
        logic, cursor = read_optional(source, cursor)
        relation = r"\nvDash" if negated else r"\vDash"
        if logic is not None:
            relation += rf"_{{{logic}}}"
        return (
            rf"\ensuremath{{\mathfrak{{{valuation}}} "
            rf"{relation} {formula}}}",
            cursor,
        )

    text = replace_command(text, "pSat", psat_handler)

    def pvalue_handler(source: str, index: int) -> tuple[str, int]:
        valuation, cursor = read_mandatory(source, index)
        cursor = skip_space(source, cursor)
        formula = None
        if cursor < len(source) and source[cursor] == "(":
            formula, cursor = read_group(source, cursor, "(", ")")
        logic, cursor = read_optional(source, cursor)
        result = rf"\overline{{\mathfrak{{{valuation}}}}}"
        if logic is not None:
            result += rf"_{{{logic}}}"
        if formula is not None:
            result += f"({formula})"
        return rf"\ensuremath{{{result}}}", cursor

    text = replace_command(text, "pValue", pvalue_handler)

    def value_handler(source: str, index: int) -> tuple[str, int]:
        term, cursor = read_mandatory(source, index)
        structure, cursor = read_mandatory(source, cursor)
        assignment, cursor = read_optional(source, cursor)
        result = rf"\operatorname{{Val}}^{{\Struct{{{structure}}}}}"
        if assignment is not None:
            result += rf"_{{{assignment}}}"
        result += f"({term})"
        return rf"\ensuremath{{{result}}}", cursor

    text = replace_command(text, "Value", value_handler)

    def passign_handler(source: str, index: int) -> tuple[str, int]:
        value, cursor = read_mandatory(source, index)
        return rf"\ensuremath{{\mathfrak{{{value}}}}}", cursor

    text = replace_command(text, "pAssign", passign_handler)

    def varassign_handler(source: str, index: int) -> tuple[str, int]:
        variant, cursor = read_mandatory(source, index)
        base, cursor = read_mandatory(source, cursor)
        variable, cursor = read_mandatory(source, cursor)
        value, cursor = read_optional(source, cursor)
        if value is None:
            result = rf"{variant}\sim_{{{variable}}}{base}"
        else:
            result = rf"{variant}={base}[{value}/{variable}]"
        return rf"\ensuremath{{{result}}}", cursor

    text = replace_command(text, "varAssign", varassign_handler)

    def log_handler(source: str, index: int) -> tuple[str, int]:
        logic, cursor = read_mandatory(source, index)
        subscript, cursor = read_optional(source, cursor)
        result = rf"\mathbf{{{logic}}}"
        if subscript is not None:
            result += rf"_{{{subscript}}}"
        return rf"\ensuremath{{{result}}}", cursor

    text = replace_command(text, "Log", log_handler)

    def expression_set_handler(
        name: str,
    ) -> Callable[[str, int], tuple[str, int]]:
        def handler(source: str, index: int) -> tuple[str, int]:
            language, cursor = read_optional(source, index)
            result = rf"\mathrm{{{name}}}"
            if language is not None:
                result += rf"(\Lang{{{language}}})"
            return rf"\ensuremath{{{result}}}", cursor

        return handler

    text = replace_command(text, "Trm", expression_set_handler("Trm"))
    text = replace_command(text, "Frm", expression_set_handler("Frm"))

    def formula_handler(source: str, index: int) -> tuple[str, int]:
        value, cursor = read_mandatory(source, index)
        value = value.strip()
        return FORMULA_GREEK.get(value, value), cursor

    text = replace_command(text, "formula", formula_handler)
    text = re.sub(
        r"(?<![\\!])!([ABCDEFGHKLORST])",
        lambda match: FORMULA_GREEK[match.group(1)],
        text,
    )
    return text


def cleanup_latex(text: str) -> str:
    text = text.replace(r"\latinfont", "")
    text = text.replace(r"\scriptsize", "")
    text = text.replace(r"\startycommalist", "")
    text = text.replace(r"\ycomma", "، ")
    text = text.replace(r"\setRTL", "")
    text = text.replace(r"\noindent", "")
    text = text.replace(r"\allowbreak", "")
    text = re.sub(r"\\hfill(?![A-Za-z@])", r"\\quad", text)
    text = re.sub(r"\\newline(?![A-Za-z@])", r"\\\\", text)
    text = text.replace("!{}", "!")
    # Pandoc discards free text between an enumerate opener and its first item.
    # Move source anchors into the following item without changing list content.
    text = re.sub(
        r"((?:EPUBANCHOR\d{8}TOKEN\s*)+)(\\item\b)",
        lambda match: match.group(2) + " " + match.group(1),
        text,
    )
    return text


def transform_unit(unit: Unit, state: TransformState) -> str:
    text = replace_source_structure(unit.text, unit, state)
    text = transform_formal_environments(text, state)
    text = transform_semantic_environments(
        text, unit.chapter_number, state
    )
    text = transform_named_quote_environment(
        text, "proof", state, "semantic proof", "ثبوت"
    )
    text = transform_named_quote_environment(
        text, "editorial", state, "editorial", "ادارتي يادونه"
    )
    for env in ("explain", "intro", "digress", "center"):
        text = unwrap_environment(text, env, state)
    text = split_intertext_displays(text, state)
    text = expand_optional_notation(text)
    text = cleanup_latex(text)
    remaining_environments = Counter(
        re.findall(r"\\begin\{([^}]+)\}", text)
    )
    allowed = {
        "enumerate",
        "itemize",
        "quote",
        "align",
        "align*",
        "gather*",
        "multline*",
        "cases",
        "tabular",
    }
    unexpected = sorted(set(remaining_environments) - allowed)
    if unexpected:
        raise ValueError(
            f"{unit.unit_id} retains unsupported environments: {unexpected}"
        )
    forbidden_commands = re.findall(
        r"\\(?:Axiom|Deduce|UnaryInf|BinaryInf|TrinaryInf|"
        r"QuaternaryInf|DisplayProof|RightLabel|DischargeRule|"
        r"sFmla|TRule|Sat|pSat|pValue|Value|varAssign|Proves|"
        r"Entails|lexists|lforall|eq|formula|indcase)"
        r"(?![A-Za-z@])",
        text,
    )
    if forbidden_commands:
        first = text.find(forbidden_commands[0])
        context = text[max(0, first - 120):first + 240] if first >= 0 else ""
        raise ValueError(
            f"{unit.unit_id} retains custom commands: "
            f"{sorted(set(forbidden_commands))}; context={context!r}"
        )
    if unicodedata.normalize("NFC", text) != text:
        raise ValueError(
            f"transformed unit is not NFC: {unit.unit_id}"
        )
    return text


def run_pandoc(source: str, build_dir: Path, stem: str) -> str:
    pandoc = shutil.which("pandoc")
    if not pandoc:
        raise FileNotFoundError("pandoc is required")
    source_path = build_dir / f"{stem}.pandoc.tex"
    output_path = build_dir / f"{stem}.fragment.html"
    source_path.write_text(
        PANDOC_MACROS + "\n" + source, encoding="utf-8"
    )
    command = [
        pandoc,
        str(source_path),
        "--from=latex",
        "--to=html5",
        "--mathml",
        "--wrap=none",
        "--eol=lf",
        "--fail-if-warnings",
        f"--output={output_path}",
    ]
    result = subprocess.run(
        command,
        cwd=ROOT,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
    )
    (build_dir / f"{stem}.pandoc.stderr.txt").write_text(
        result.stderr, encoding="utf-8"
    )
    if result.returncode:
        raise RuntimeError(
            f"pandoc failed for {stem} ({result.returncode}):\n"
            f"{result.stderr[:8000]}"
        )
    if result.stderr.strip():
        raise RuntimeError(
            f"pandoc emitted diagnostics for {stem}:\n"
            f"{result.stderr[:8000]}"
        )
    return output_path.read_text(encoding="utf-8")


def apply_tokens(
    fragment: str,
    registry: TokenRegistry,
    used: set[str],
) -> str:
    for token, replacement in registry.replacements.items():
        occurrences = fragment.count(token)
        if occurrences > 1:
            raise ValueError(
                f"anchor token {token} occurs {occurrences} times"
            )
        if occurrences == 1:
            fragment = fragment.replace(token, replacement)
            used.add(token)
    return fragment


def postprocess_fragment(
    fragment: str,
    registry: TokenRegistry,
    stats: Counter,
    used_environment_markers: set[str],
) -> etree._Element:
    wrapped = f'<div xmlns="{XHTML_NS}">{fragment}</div>'
    parser = etree.XMLParser(
        resolve_entities=False, no_network=True, recover=False
    )
    root = etree.fromstring(wrapped.encode("utf-8"), parser)
    for marker, metadata in registry.environment_markers.items():
        matches: list[etree._Element] = []
        seen: set[int] = set()
        for element in root.iter():
            if not (
                (element.text and marker in element.text)
                or (element.tail and marker in element.tail)
            ):
                continue
            owner = element
            while (
                owner is not None
                and owner.tag != etree.QName(XHTML_NS, "blockquote")
            ):
                owner = owner.getparent()
            if owner is not None and id(owner) not in seen:
                seen.add(id(owner))
                matches.append(owner)
        if len(matches) > 1:
            raise ValueError(
                f"environment marker {marker} matched "
                f"{len(matches)} blockquotes"
            )
        if not matches:
            continue
        used_environment_markers.add(marker)
        quote = matches[0]
        existing = quote.get("class", "")
        quote.set(
            "class", (existing + " " + metadata["kind"]).strip()
        )
        quote.set("aria-label", metadata["aria_label"])
        if metadata["kind"] in {
            "proof-tree",
            "proof-rules",
            "tableau",
            "derivation",
        }:
            quote.set("dir", "rtl")
        if "expected_list_items" in metadata:
            actual_list_items = len(
                quote.xpath(".//x:li", namespaces={"x": XHTML_NS})
            )
            if actual_list_items != metadata["expected_list_items"]:
                raise ValueError(
                    "formal environment lost list items: "
                    f"kind={metadata['kind']!r}; "
                    f"expected={metadata['expected_list_items']}; "
                    f"actual={actual_list_items}; "
                    f"preview={metadata.get('content_preview', '')!r}"
                )
        for element in quote.iter():
            if element.text and marker in element.text:
                element.text = element.text.replace(
                    marker, ""
                ).lstrip()
            if element.tail and marker in element.tail:
                element.tail = element.tail.replace(
                    marker, ""
                ).lstrip()

    math_nodes = root.xpath(
        ".//m:math", namespaces={"m": MATHML_NS}
    )
    for math_node in math_nodes:
        math_node.set("dir", "ltr")
    for table in root.xpath(".//x:table", namespaces={"x": XHTML_NS}):
        table.set("dir", "ltr")
    annotations = root.xpath(
        ".//m:math/m:semantics/"
        "m:annotation[@encoding='application/x-tex']",
        namespaces={"m": MATHML_NS},
    )
    if len(annotations) != len(math_nodes):
        raise ValueError(
            f"MathML annotation mismatch: {len(math_nodes)} math, "
            f"{len(annotations)} annotations"
        )
    stats["mathml_elements"] += len(math_nodes)
    stats["mathml_tex_annotations"] += len(annotations)
    stats["html_tables"] += len(
        root.xpath(".//x:table", namespaces={"x": XHTML_NS})
    )
    stats["html_ordered_lists"] += len(
        root.xpath(".//x:ol", namespaces={"x": XHTML_NS})
    )
    stats["html_unordered_lists"] += len(
        root.xpath(".//x:ul", namespaces={"x": XHTML_NS})
    )
    return root


def xhtml_document(
    title: str,
    fragment_root: etree._Element,
    body_type: str = "bodymatter",
) -> bytes:
    nsmap = {None: XHTML_NS, "epub": EPUB_NS}
    root = etree.Element(
        etree.QName(XHTML_NS, "html"), nsmap=nsmap
    )
    root.set("lang", LANGUAGE)
    root.set(etree.QName(XML_NS, "lang"), LANGUAGE)
    root.set("dir", "rtl")
    head = etree.SubElement(
        root, etree.QName(XHTML_NS, "head")
    )
    etree.SubElement(
        head, etree.QName(XHTML_NS, "meta"), charset="utf-8"
    )
    title_element = etree.SubElement(
        head, etree.QName(XHTML_NS, "title")
    )
    title_element.text = title
    etree.SubElement(
        head,
        etree.QName(XHTML_NS, "link"),
        rel="stylesheet",
        href="styles.css",
        type="text/css",
    )
    body = etree.SubElement(
        root, etree.QName(XHTML_NS, "body")
    )
    body.set(etree.QName(EPUB_NS, "type"), body_type)
    main = etree.SubElement(
        body, etree.QName(XHTML_NS, "main")
    )
    for child in list(fragment_root):
        fragment_root.remove(child)
        main.append(child)
    return etree.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
        pretty_print=True,
        doctype="<!DOCTYPE html>",
    )


def title_page(translated_bundle_units: int) -> bytes:
    fragment = etree.Element(
        etree.QName(XHTML_NS, "div"), nsmap={None: XHTML_NS}
    )
    section = etree.SubElement(
        fragment, etree.QName(XHTML_NS, "section")
    )
    section.set("class", "title-page")
    heading = etree.SubElement(
        section, etree.QName(XHTML_NS, "h1")
    )
    heading.text = TITLE
    locale = etree.SubElement(
        section, etree.QName(XHTML_NS, "p")
    )
    locale.set("class", "locale")
    locale.text = "پښتو — پاکستان"
    subtitle = etree.SubElement(
        section, etree.QName(XHTML_NS, "h2")
    )
    subtitle.text = SUBTITLE
    edition = etree.SubElement(
        section, etree.QName(XHTML_NS, "p")
    )
    edition.set("class", "edition")
    edition.text = (
        "د ماشيني ژباړې د روان کار برېښنايي لوستيزه نسخه"
    )
    paragraphs = [
        (
            "په دې لوستيزه نسخه کښې د بياني منطق د نحو او "
            "معناپوهنې بشپړ باب، د ثبوتي نظامونو ټولکتنه، د "
            "لومړۍ درجې منطق د سېکوېنټ حساب، فطري استنتاج، "
            "تابلو او بديهي اشتقاق بشپړ بابونه، او د لومړۍ درجې "
            "منطق د بشپړتيا باب شامل دي۔ وروستی باب د نحوي "
            "وسيلو، لينډنباوم جوړونې، ترمي موډلونو، بشپړتيا، "
            "فشردګۍ او ښکته لوېنهايم–سکولم قضيه را اخلي۔"
        ),
        (
            "دا جزوي لوستونکی 82 سرچينيز واحدونه (OLP-0056 تر "
            "OLP-0137) لري؛ د 722 واحدونو بشپړه ژباړه لا روانه "
            f"ده او تر اوسه {translated_bundle_units} واحدونه په "
            "ژباړل شوي بنډل کښې شته۔"
        ),
        (
            "په متن کښې کږلي عنوانونه او ورپسې آبي [OLP] نښه "
            "د بشپړ OpenLogic هغو لومړۍ درجې منطق نحوي او معنايي "
            "برخو ته تړنې دي چې په دې جزوي لوستيزه نسخه کښې نۀ "
            "دي شاملې۔ هره نښه اړوند تعريف، قضيه يا نتيجه په "
            "ثابته سرچينه کښې پرانيزي۔"
        ),
    ]
    for value in paragraphs:
        paragraph = etree.SubElement(
            section, etree.QName(XHTML_NS, "p")
        )
        paragraph.text = value
    provenance = etree.SubElement(
        section, etree.QName(XHTML_NS, "section")
    )
    provenance.set("class", "provenance")
    provenance.set("dir", "ltr")
    provenance.set("lang", "en")
    provenance.set(etree.QName(XML_NS, "lang"), "en")
    p1 = etree.SubElement(
        provenance, etree.QName(XHTML_NS, "p")
    )
    p1.text = (
        "Independent Pashto (Pakistan) translation of Open Logic "
        f"Project revision {reader.UPSTREAM_REVISION}. This reader "
        "contains 82 source units (OLP-0056 through OLP-0137). "
        "Pakistani usage is primary; Afghan Pashto sources are "
        "labelled regional comparators. Specialist terminology "
        "remains openly reviewable where exact native technical "
        "attestation is sparse. No native-reader review or upstream "
        "endorsement is claimed."
    )
    p2 = etree.SubElement(
        provenance, etree.QName(XHTML_NS, "p")
    )
    p2.text = (
        "Original text and adaptation: Creative Commons Attribution "
        "4.0 International, subject to the component notices "
        "preserved with the source snapshot. "
    )
    links = [
        ("Open Logic Project", "https://openlogicproject.org/"),
        (
            "Translation catalogue",
            "https://github.com/KokunoYumeto/OpenLogic-translations",
        ),
        (
            "Edition lineage",
            "https://doi.org/10.5281/zenodo.22307197",
        ),
    ]
    for index, (label, href) in enumerate(links):
        link = etree.SubElement(
            p2, etree.QName(XHTML_NS, "a"), href=href
        )
        link.text = label
        link.tail = (
            ". " if index == len(links) - 1 else "; "
        )
    return xhtml_document(TITLE, fragment, "frontmatter")


def build_nav(headings: list[Heading]) -> bytes:
    nsmap = {None: XHTML_NS, "epub": EPUB_NS}
    root = etree.Element(
        etree.QName(XHTML_NS, "html"), nsmap=nsmap
    )
    root.set("lang", LANGUAGE)
    root.set(etree.QName(XML_NS, "lang"), LANGUAGE)
    root.set("dir", "rtl")
    head = etree.SubElement(
        root, etree.QName(XHTML_NS, "head")
    )
    etree.SubElement(
        head, etree.QName(XHTML_NS, "meta"), charset="utf-8"
    )
    title = etree.SubElement(
        head, etree.QName(XHTML_NS, "title")
    )
    title.text = "فهرست"
    etree.SubElement(
        head,
        etree.QName(XHTML_NS, "link"),
        rel="stylesheet",
        href="styles.css",
        type="text/css",
    )
    body = etree.SubElement(
        root, etree.QName(XHTML_NS, "body")
    )
    nav = etree.SubElement(
        body, etree.QName(XHTML_NS, "nav")
    )
    nav.set(etree.QName(EPUB_NS, "type"), "toc")
    nav.set("id", "toc")
    h1 = etree.SubElement(
        nav, etree.QName(XHTML_NS, "h1")
    )
    h1.text = "فهرست"
    top = etree.SubElement(
        nav, etree.QName(XHTML_NS, "ol")
    )
    title_item = etree.SubElement(
        top, etree.QName(XHTML_NS, "li")
    )
    title_link = etree.SubElement(
        title_item,
        etree.QName(XHTML_NS, "a"),
        href="title.xhtml",
    )
    title_link.text = "د نسخې پېژندنه"
    section_list = None
    section_item = None
    subsection_list = None
    for heading in headings:
        label = f"{heading.number} {heading.title_text}"
        href = f"{heading.document_name}#{heading.anchor_id}"
        if heading.level == 1:
            chapter_item = etree.SubElement(
                top, etree.QName(XHTML_NS, "li")
            )
            link = etree.SubElement(
                chapter_item,
                etree.QName(XHTML_NS, "a"),
                href=href,
            )
            link.text = label
            section_list = etree.SubElement(
                chapter_item, etree.QName(XHTML_NS, "ol")
            )
            section_item = None
            subsection_list = None
        elif heading.level == 2:
            if section_list is None:
                raise ValueError(
                    "section precedes chapter in navigation"
                )
            section_item = etree.SubElement(
                section_list, etree.QName(XHTML_NS, "li")
            )
            link = etree.SubElement(
                section_item,
                etree.QName(XHTML_NS, "a"),
                href=href,
            )
            link.text = label
            subsection_list = None
        elif heading.level == 3:
            if section_item is None:
                raise ValueError(
                    "subsection precedes section in navigation"
                )
            if subsection_list is None:
                subsection_list = etree.SubElement(
                    section_item, etree.QName(XHTML_NS, "ol")
                )
            subitem = etree.SubElement(
                subsection_list, etree.QName(XHTML_NS, "li")
            )
            link = etree.SubElement(
                subitem,
                etree.QName(XHTML_NS, "a"),
                href=href,
            )
            link.text = label
        else:
            raise ValueError(
                f"unsupported heading level {heading.level}"
            )
    return etree.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
        pretty_print=True,
        doctype="<!DOCTYPE html>",
    )


def package_opf(chapter_count: int, identifier: str) -> bytes:
    manifest_items = [
        (
            '<item id="nav" href="nav.xhtml" '
            'media-type="application/xhtml+xml" properties="nav"/>'
        ),
        (
            '<item id="title" href="title.xhtml" '
            'media-type="application/xhtml+xml"/>'
        ),
        (
            '<item id="css" href="styles.css" '
            'media-type="text/css"/>'
        ),
    ]
    spine_items = ['<itemref idref="title"/>']
    for number in range(1, chapter_count + 1):
        manifest_items.append(
            f'<item id="chapter-{number:02d}" '
            f'href="chapter-{number:02d}.xhtml" '
            'media-type="application/xhtml+xml" '
            'properties="mathml"/>'
        )
        spine_items.append(
            f'<itemref idref="chapter-{number:02d}"/>'
        )
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0"
  unique-identifier="pub-id"
  prefix="schema: http://schema.org/">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="pub-id">{identifier}</dc:identifier>
    <dc:title>{TITLE}: {SUBTITLE}</dc:title>
    <dc:language>{LANGUAGE}</dc:language>
    <dc:creator id="creator">Open Logic Project</dc:creator>
    <dc:contributor>Independent Pashto (Pakistan) translation</dc:contributor>
    <dc:rights>Creative Commons Attribution 4.0 International, subject to component notices.</dc:rights>
    <meta property="dcterms:modified">{EDITION_MODIFIED}</meta>
    <meta property="schema:accessMode">textual</meta>
    <meta property="schema:accessMode">visual</meta>
    <meta property="schema:accessModeSufficient">textual,visual</meta>
    <meta property="schema:accessibilityFeature">MathML</meta>
    <meta property="schema:accessibilityFeature">structuralNavigation</meta>
    <meta property="schema:accessibilityFeature">tableOfContents</meta>
    <meta property="schema:accessibilityFeature">readingOrder</meta>
    <meta property="schema:accessibilityHazard">none</meta>
    <meta property="schema:accessibilitySummary">Reflowable RTL Pashto text with native MathML, structured headings, exercises, proof derivations, tableaux, and linked navigation.</meta>
    <meta property="rendition:layout">reflowable</meta>
  </metadata>
  <manifest>
    {''.join(manifest_items)}
  </manifest>
  <spine page-progression-direction="rtl">
    {''.join(spine_items)}
  </spine>
</package>
"""
    return xml.encode("utf-8")


STYLESHEET = """@charset "utf-8";
:root {
  font-family: "Noto Naskh Arabic", "Noto Sans Arabic", "Amiri", serif;
  line-height: 1.75;
}
body {
  margin: 5%;
  text-align: start;
  overflow-wrap: anywhere;
  word-wrap: break-word;
}
main { max-width: 54rem; margin: 0 auto; }
h1, h2, h3 { line-height: 1.35; page-break-after: avoid; }
h1 { border-bottom: 0.08em solid #555; padding-bottom: 0.25em; }
a { color: #1859a9; text-decoration: underline; }
.source-anchor, .source-unit, .source-segment,
.reference-anchor, .subsection-anchor { display: inline; }
blockquote {
  margin: 1.2em 0;
  padding: 0.8em 1em;
  border-right: 0.22em solid #73849a;
}
blockquote.semantic.defn, blockquote.semantic.prob,
blockquote.semantic.ex { border-right-color: #8a5c18; }
blockquote.editorial { border-right-color: #a23838; }
blockquote.proof-tree, blockquote.proof-rules,
blockquote.tableau {
  overflow-x: auto;
  overflow-y: visible;
}
blockquote.proof-tree ul, blockquote.proof-rules ul,
blockquote.tableau ul {
  list-style: none;
  margin: 0.35em 0;
  padding-right: 1.3em;
  border-right: 0.08em solid #9aa4b1;
}
blockquote.proof-tree li, blockquote.proof-rules li,
blockquote.tableau li { margin: 0.45em 0; }
math {
  max-width: none;
}
table {
  border-collapse: collapse;
  margin: 1em auto;
  max-width: 100%;
}
th, td { border: 0.06em solid #888; padding: 0.3em 0.55em; }
.title-page { text-align: center; }
.title-page > p:not(.locale):not(.edition) { text-align: start; }
.locale, .edition { font-size: 1.15em; }
.provenance {
  margin-top: 2em;
  text-align: left;
  font-family: serif;
  line-height: 1.45;
}
nav ol { padding-right: 1.4em; }
"""


def container_xml() -> bytes:
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container"
  version="1.0">
  <rootfiles>
    <rootfile full-path="EPUB/package.opf"
      media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""


def write_epub(tree: Path, output: Path) -> None:
    members = [
        path.relative_to(tree).as_posix()
        for path in tree.rglob("*")
        if path.is_file() and path.name != "mimetype"
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w") as archive:
        mime_info = zipfile.ZipInfo(
            "mimetype", date_time=(1980, 1, 1, 0, 0, 0)
        )
        mime_info.compress_type = zipfile.ZIP_STORED
        mime_info.create_system = 0
        mime_info.external_attr = 0o644 << 16
        archive.writestr(mime_info, b"application/epub+zip")
        for member in sorted(members):
            info = zipfile.ZipInfo(
                member, date_time=(1980, 1, 1, 0, 0, 0)
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 0
            info.external_attr = 0o644 << 16
            info.flag_bits |= 0x800
            archive.writestr(
                info,
                (tree / Path(member)).read_bytes(),
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )


def validate_tree(tree: Path, stats: Counter) -> dict:
    parser = etree.XMLParser(
        resolve_entities=False, no_network=True, recover=False
    )
    xhtml_files = sorted((tree / "EPUB").glob("*.xhtml"))
    ids_by_file: dict[str, set[str]] = {}
    hrefs: list[tuple[str, str]] = []
    math_count = annotation_count = 0
    raw_tex_hits: list[str] = []
    for path in xhtml_files:
        document = etree.parse(str(path), parser)
        root = document.getroot()
        if (
            root.get("lang") != LANGUAGE
            or root.get(etree.QName(XML_NS, "lang")) != LANGUAGE
        ):
            raise ValueError(
                f"language metadata missing in {path.name}"
            )
        if root.get("dir") != "rtl":
            raise ValueError(
                f"RTL root direction missing in {path.name}"
            )
        ids = root.xpath("//@id")
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate IDs in {path.name}")
        ids_by_file[path.name] = set(ids)
        for element in root.xpath(
            "//x:a[@href]", namespaces={"x": XHTML_NS}
        ):
            hrefs.append((path.name, element.get("href")))
        maths = root.xpath(
            "//m:math", namespaces={"m": MATHML_NS}
        )
        annotations = root.xpath(
            "//m:math/m:semantics/"
            "m:annotation[@encoding='application/x-tex']",
            namespaces={"m": MATHML_NS},
        )
        math_count += len(maths)
        annotation_count += len(annotations)
        for annotation in annotations:
            if not (annotation.text or "").strip():
                raise ValueError(
                    f"empty MathML TeX annotation in {path.name}"
                )
            annotation.getparent().remove(annotation)
        visible = "".join(
            root.xpath(
                "//text()[not(ancestor::x:code)]",
                namespaces={"x": XHTML_NS},
            )
        )
        if re.search(
            r"\\(?:begin|end|[A-Za-z@]{2,})|\$", visible
        ):
            raw_tex_hits.append(path.name)
    if raw_tex_hits:
        raise ValueError(f"visible raw TeX in {raw_tex_hits}")
    if math_count == 0 or annotation_count != math_count:
        raise ValueError(
            "native MathML/annotation coverage failed"
        )

    internal_count = external_count = 0
    broken: list[dict] = []
    for source, href in hrefs:
        if re.match(r"https?://", href):
            external_count += 1
            continue
        if href.startswith("mailto:"):
            continue
        internal_count += 1
        if "#" in href:
            file_part, fragment = href.split("#", 1)
            target_file = file_part or source
            if (
                target_file not in ids_by_file
                or fragment not in ids_by_file[target_file]
            ):
                broken.append({"source": source, "href": href})
        elif href not in ids_by_file:
            broken.append({"source": source, "href": href})
    if broken:
        raise ValueError(f"broken internal links: {broken[:10]}")
    stats["validated_mathml_elements"] = math_count
    stats["validated_internal_links"] = internal_count
    stats["validated_external_links"] = external_count
    return {
        "xhtml_documents": len(xhtml_files),
        "mathml_elements": math_count,
        "tex_annotations": annotation_count,
        "internal_links": internal_count,
        "external_links": external_count,
        "broken_links": 0,
        "visible_raw_tex_hits": 0,
    }


def build(args: argparse.Namespace) -> None:
    build_dir = args.build_dir.resolve()
    build_dir.mkdir(parents=True, exist_ok=True)
    tree = build_dir / "epub-tree"
    if tree.exists():
        shutil.rmtree(tree)
    (tree / "META-INF").mkdir(parents=True)
    (tree / "EPUB").mkdir(parents=True)

    units, provenance = load_units()
    reference_record, reference_map = load_reference_map()
    reference_targets = build_reference_targets(
        units, reference_map
    )
    expected_theorem_counts = verify_theorem_numbering(
        units, reference_map
    )
    tokens = TokenRegistry()
    state = TransformState(
        tokens=tokens,
        reference_map=reference_map,
        reference_targets=reference_targets,
    )

    transformed_by_chapter: dict[int, list[str]] = {}
    for unit in units:
        transformed_by_chapter.setdefault(
            unit.chapter_number, []
        ).append(transform_unit(unit, state))
    if (
        state.stats["segment_start_anchors"]
        != state.stats["segment_end_anchors"]
    ):
        raise ValueError(
            "semantic segment start/end count mismatch"
        )
    if state.stats["segment_start_anchors"] != 907:
        raise ValueError(
            "expected 907 semantic segments, found "
            f"{state.stats['segment_start_anchors']}"
        )
    for env, expected in expected_theorem_counts.items():
        actual = state.stats[f"environment_{env}"]
        if actual != expected:
            raise ValueError(
                f"{env} environment count mismatch: "
                f"{actual} vs {expected}"
            )

    used_tokens: set[str] = set()
    used_environment_markers: set[str] = set()
    chapter_stats: dict[str, dict] = {}
    for chapter_number in range(1, 8):
        stem = f"chapter-{chapter_number:02d}"
        source = "\n\n".join(
            transformed_by_chapter[chapter_number]
        )
        fragment = run_pandoc(
            source, build_dir, stem
        )
        fragment = apply_tokens(
            fragment, tokens, used_tokens
        )
        fragment_root = postprocess_fragment(
            fragment,
            tokens,
            state.stats,
            used_environment_markers,
        )
        chapter_heading = next(
            heading
            for heading in state.headings
            if heading.level == 1
            and heading.document_name == f"{stem}.xhtml"
        )
        data = xhtml_document(
            chapter_heading.title_text, fragment_root
        )
        destination = tree / "EPUB" / f"{stem}.xhtml"
        destination.write_bytes(data)
        chapter_stats[f"{stem}.xhtml"] = {
            "bytes": destination.stat().st_size,
            "sha256": sha256(destination),
            "source_units": [
                unit.unit_id
                for unit in units
                if unit.chapter_number == chapter_number
            ],
        }
    if used_tokens != set(tokens.replacements):
        missing = sorted(set(tokens.replacements) - used_tokens)
        raise ValueError(
            f"{len(missing)} anchor tokens were not rendered: "
            f"{missing[:8]}"
        )
    if used_environment_markers != set(
        tokens.environment_markers
    ):
        missing = sorted(
            set(tokens.environment_markers)
            - used_environment_markers
        )
        raise ValueError(
            f"{len(missing)} environment markers were not rendered: "
            f"{missing[:8]}"
        )

    title_path = tree / "EPUB" / "title.xhtml"
    title_path.write_bytes(
        title_page(provenance["translated_bundle_units"])
    )
    nav_path = tree / "EPUB" / "nav.xhtml"
    nav_path.write_bytes(build_nav(state.headings))
    (tree / "EPUB" / "styles.css").write_text(
        STYLESHEET, encoding="utf-8", newline="\n"
    )
    identifier = "urn:uuid:" + str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            "https://github.com/KokunoYumeto/"
            "openlogic-ps-Arab-PK/"
            f"proof-systems-completeness/{EDITION_VERSION}",
        )
    )
    (tree / "EPUB" / "package.opf").write_bytes(
        package_opf(7, identifier)
    )
    (tree / "META-INF" / "container.xml").write_bytes(
        container_xml()
    )
    (tree / "mimetype").write_bytes(
        b"application/epub+zip"
    )

    validation = validate_tree(tree, state.stats)
    output = (
        args.output or (build_dir / EPUB_NAME)
    ).resolve()
    write_epub(tree, output)
    first_hash = sha256(output)
    replay = build_dir / (output.stem + ".replay.epub")
    write_epub(tree, replay)
    replay_hash = sha256(replay)
    if (
        first_hash != replay_hash
        or output.read_bytes() != replay.read_bytes()
    ):
        raise ValueError(
            "deterministic EPUB replay differs byte-for-byte"
        )

    with zipfile.ZipFile(output) as archive:
        members = archive.infolist()
        if not members or members[0].filename != "mimetype":
            raise ValueError(
                "mimetype is not the first EPUB member"
            )
        if members[0].compress_type != zipfile.ZIP_STORED:
            raise ValueError("mimetype is compressed")
        member_inventory = [
            {
                "path": info.filename,
                "bytes": info.file_size,
                "compressed_bytes": info.compress_size,
                "compression": info.compress_type,
                "sha256": hashlib.sha256(
                    archive.read(info.filename)
                ).hexdigest(),
            }
            for info in members
        ]

    record = {
        "schema": (
            "openlogic-ps-Arab-PK-proof-systems-"
            "completeness-epub-build/1"
        ),
        "status": "built_and_locally_validated",
        "edition_version": EDITION_VERSION,
        "scope": {
            "first_unit": "OLP-0056",
            "last_unit": "OLP-0137",
            "unit_count": len(units),
            "chapter_count": 7,
            "semantic_segment_count": (
                state.stats["segment_start_anchors"]
            ),
            "partial_edition": True,
            "full_project_unit_count": 722,
            "translated_bundle_units": (
                provenance["translated_bundle_units"]
            ),
        },
        "language": {
            "tag": LANGUAGE,
            "script": "Arab",
            "region": "PK",
            "page_progression": "rtl",
        },
        "source_revision": reader.UPSTREAM_REVISION,
        "profile_resolution": (
            provenance["profile_resolution"]
        ),
        "input_files": provenance["input_files"],
        "reference_map": {
            "path": (
                REFERENCE_MAP_PATH.relative_to(ROOT).as_posix()
            ),
            "sha256": sha256(REFERENCE_MAP_PATH),
            "reference_count": len(reference_map),
            "accepted_pdf_sha256": (
                reference_record["accepted_pdf"]["sha256"]
            ),
        },
        "conversion": {
            "builder": {
                "path": (
                    Path(__file__).relative_to(ROOT).as_posix()
                ),
                "sha256": sha256(Path(__file__)),
            },
            "pandoc": subprocess.run(
                [
                    shutil.which("pandoc") or "pandoc",
                    "--version",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
            ).stdout.splitlines()[0],
            "native_mathml": True,
            "proof_tree_representation": (
                "nested semantic HTML lists with native MathML"
            ),
            "tableau_representation": (
                "nested semantic HTML branch lists with native MathML"
            ),
        },
        "structure_counts": dict(sorted(state.stats.items())),
        "validation": validation,
        "deterministic_replay": {
            "byte_identical": True,
            "sha256_identical": True,
            "replay_sha256": replay_hash,
        },
        "chapters": chapter_stats,
        "epub": {
            "path": str(output),
            "bytes": output.stat().st_size,
            "sha256": first_hash,
            "member_count": len(member_inventory),
            "members": member_inventory,
        },
    }
    record_path = build_dir / "build-epub.json"
    record_path.write_text(
        json.dumps(
            record, ensure_ascii=False, indent=2
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "epub": str(output),
                "bytes": output.stat().st_size,
                "sha256": first_hash,
                "reader_units": len(units),
                "chapters": 7,
                "segments": (
                    state.stats["segment_start_anchors"]
                ),
                "mathml": validation["mathml_elements"],
                "internal_links": (
                    validation["internal_links"]
                ),
                "external_links": (
                    validation["external_links"]
                ),
                "build_record": str(record_path),
            },
            ensure_ascii=False,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--build-dir", type=Path, required=True
    )
    parser.add_argument("--output", type=Path)
    build(parser.parse_args())


if __name__ == "__main__":
    main()
