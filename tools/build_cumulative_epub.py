"""Build deterministic reflowable EPUB 3 cumulative readers."""

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

import build_cumulative_reader as reader


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_MAP_PATH = ROOT / "evidence" / "CUMULATIVE_EPUB_REFERENCE_MAP.json"
EDITION_VERSION = "0.6.0"
EDITION_MODIFIED = "2026-09-20T00:00:00Z"
EPUB_NAME = "openlogic-ps-Arab-PK-cumulative-through-computability-v0.6.0.epub"
TITLE = "خلاص منطق"
SUBTITLE = "له بنسټونو تر محاسبويت او د ټيورينګ ماشينونو پېژندګلو"
LANGUAGE = "ps-Arab-PK"
CHAPTER_COUNT = 25
EXPECTED_SEGMENTS = 2683
EXPECTED_FIGURES = 20
THROUGH_UNIT = 255
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
    "rem": "يادونه",
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
\newcommand{\tuple}[1]{\langle #1\rangle}
\newcommand{\openTuple}{\langle}
\newcommand{\closeTuple}{\rangle}
\newcommand{\Setabs}[2]{\ensuremath{\{#1:#2\}}}
\newcommand{\equivrep}[2]{\ensuremath{[#1]_{#2}}}
\newcommand{\equivclass}[2]{\ensuremath{#1/_{\!#2}}}
\newcommand{\num}[1]{\ensuremath{\overline{#1}}}
\newcommand{\PVar}{\ensuremath{\mathrm{At}_0}}
\newcommand{\PAx}{\ensuremath{\mathrm{Ax}_0}}
\newcommand{\ident}{\equiv}
\newcommand{\Nat}{\mathbb{N}}
\newcommand{\Int}{\mathbb{Z}}
\newcommand{\Rat}{\mathbb{Q}}
\newcommand{\Real}{\mathbb{R}}
\newcommand{\PosInt}{\mathbb{Z}^{+}}
\newcommand{\Pow}[1]{\mathcal{P}(#1)}
\newcommand{\Bin}{\{0,1\}}
\newcommand{\len}[1]{|#1|}
\newcommand{\nicefrac}[2]{\frac{#1}{#2}}
\newcommand{\shoveright}[1]{#1}
\newcommand{\shoveleft}[1]{#1}
\newcommand{\Id}[1]{\mathrm{Id}_{#1}}
\newcommand{\emptyseq}{\langle\rangle}
\newcommand{\funrestrictionto}[2]{#1\upharpoonright #2}
\newcommand{\funimage}[2]{#1[#2]}
\newcommand{\ran}[1]{\operatorname{ran}(#1)}
\newcommand{\dom}[1]{\operatorname{dom}(#1)}
\newcommand{\lcm}{\operatorname{lcm}}
\newcommand{\pto}{\rightharpoonup}
\newcommand{\fdefined}{\mathord{\downarrow}}
\newcommand{\fundefined}{\mathord{\uparrow}}
\newcommand{\cardeq}[2]{#1\approx #2}
\newcommand{\cardneq}[2]{#1\not\approx #2}
\newcommand{\cardle}[2]{#1\preceq #2}
\newcommand{\cardless}[2]{#1\prec #2}
\newcommand{\small}{}
\newcommand{\Intequiv}{\sim}
\newcommand{\Ratequiv}{\backsim}
\newcommand{\Realequiv}{\simeq}
\newcommand{\defis}{=}
\newcommand{\closureofunder}[2]{\mathrm{clo}_{#1}(#2)}
\newcommand{\Closureofunder}[2]{\mathrm{Clo}_{#1}(#2)}
\newcommand{\Var}{\mathrm{Var}}
\newcommand{\VDash}{\Vdash}
\newcommand{\Part}[2]{\mathsf{P}(#1,#2)}
\newcommand{\substruct}{\subseteq}
\newcommand{\Theory}[1]{\mathrm{Th}(\mathfrak{#1})}
\newcommand{\QuantRank}[1]{\mathrm{qr}(#1)}
\newcommand{\Expan}[2]{(\mathfrak{#1},#2)}
\newcommand{\PIso}[1]{\mathcal{#1}}
\newcommand{\concat}{\frown}
\newcommand{\Th}[1]{\mathbf{#1}}
\newcommand{\gn}[1]{\ulcorner #1\urcorner}
\newcommand{\scode}[1]{\mathrm{c}_{#1}}
\newcommand{\Gn}[1]{{}^{\#}#1^{\#}}
\newcommand{\nszero}{\mathbf{z}}
\newcommand{\nssucc}{*}
\newcommand{\nsplus}{\oplus}
\newcommand{\nstimes}{\otimes}
\newcommand{\nsless}{<_{\mathrm{ns}}}
\newcommand{\fn}[1]{\mathrm{#1}}
\newcommand{\Proj}[2]{P^{#1}_{#2}}
\newcommand{\Zero}{\mathrm{zero}}
\newcommand{\Succ}{\mathrm{succ}}
\newcommand{\Add}{\mathrm{add}}
\newcommand{\Mult}{\mathrm{mult}}
\newcommand{\Exp}{\mathrm{exp}}
\newcommand{\Pred}{\mathrm{pred}}
\newcommand{\tsub}{\mathbin{\dot{-}}}
\newcommand{\Char}[1]{\chi_{#1}}
\newcommand{\defiff}{\Leftrightarrow}
\newcommand{\umin}[2]{\mu #1\;#2}
\newcommand{\bmin}[2]{(\mathrm{min}\;#1)\,#2}
\newcommand{\bexists}[2]{(\exists #1)\;#2}
\newcommand{\bforall}[2]{(\forall #1)\;#2}
\newcommand{\fact}[1]{#1!}
\newcommand{\raisebox}[2]{#2}
\newcommand{\Complement}[1]{\overline{#1}}
\newcommand{\red}{\longrightarrow}
\newcommand{\TMendtape}{\triangleright}
\newcommand{\TMblank}{0}
\newcommand{\TMstroke}{1}
\newcommand{\TMright}{R}
\newcommand{\TMleft}{L}
\newcommand{\TMstay}{N}
\newcommand{\TMtrans}[3]{#1,#2,#3}
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
    role: str


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
    figures: list[dict] = field(default_factory=list)


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

    def html(self, markup: str) -> str:
        token = self._token("HTML")
        self.replacements[token] = markup
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


def extract_context(text: str) -> tuple[str, str, str, str]:
    return reader.context(text)


def load_units() -> tuple[list[Unit], dict]:
    manifest_rows = [
        json.loads(line)
        for line in reader.MANIFEST.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    alignment_rows = [
        json.loads(line)
        for line in reader.ALIGNMENT.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    alignment_by_unit: dict[str, list[dict]] = {}
    for row in alignment_rows:
        alignment_by_unit.setdefault(row["unit_id"], []).append(row)
    selected = manifest_rows[: len(reader.EXPECTED_IDS)]
    if [row["unit_id"] for row in selected] != reader.EXPECTED_IDS:
        raise ValueError(f"manifest does not contain exact OLP-0001..OLP-{THROUGH_UNIT:04d} sequence")
    if any(row["source_commit"] != reader.UPSTREAM_REVISION for row in selected):
        raise ValueError("source revision mismatch")

    prepared: list[tuple[dict, str, str, list[Path]]] = []
    profile_stats: Counter = Counter()
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
        body, unit_profile, assets = reader.prepare_unit(
            target_text, alignment_by_unit.get(row["unit_id"], []), row
        )
        role = extract_context(body)[3]
        prepared.append((row, body, role, assets))
        profile_stats.update(unit_profile)
        input_files.append(
            {
                "unit_id": row["unit_id"],
                "source_path": f"upstream/{row['source_path']}",
                "source_sha256": sha256(upstream),
                "target_path": f"ps-Arab-PK/{row['source_path']}",
                "target_sha256": sha256(target),
                "role": role,
            }
        )

    selected_labels: set[str] = set()
    for _row, body, _role, _assets in prepared:
        overlap = selected_labels & reader.label_keys(body)
        if overlap:
            raise ValueError(f"duplicate selected labels: {sorted(overlap)[:8]}")
        selected_labels.update(reader.label_keys(body))
    upstream_labels = reader.upstream_label_index(manifest_rows)

    rendered: list[tuple[dict, str, str, list[Path]]] = []
    external_counts: Counter = Counter()
    for row, body, role, assets in prepared:
        body, label_stats = reader.resolve_label_conditionals(body, selected_labels)
        profile_stats.update(label_stats)
        body, counts = reader.render_external_references(
            body, selected_labels=selected_labels, upstream_labels=upstream_labels
        )
        external_counts.update(counts)
        rendered.append((row, body, role, assets))

    expected_external = Counter(
        {
            "his:set:limits:sec": 2,
            "his:set:mythology:sec": 1,
            "inc:req:min:lem:less-nsucc": 1,
            "inc:req:min:lem:less-zero": 1,
            "mth:ind:idf:sec": 1,
            "mth:ind:sti:sec": 1,
            "sth:::part": 1,
            "sth:ord-arithmetic::chap": 1,
        }
    )
    if THROUGH_UNIT >= 321:
        del expected_external["inc:req:min:lem:less-nsucc"]
        del expected_external["inc:req:min:lem:less-zero"]
    if external_counts != expected_external:
        raise ValueError(f"external reference count mismatch: {external_counts}")

    chapter_ordinals: list[int | None] = []
    chapter_number = 0
    for _row, _body, role, _assets in rendered:
        if role == "chapter":
            chapter_number += 1
        chapter_ordinals.append(chapter_number if role in {"chapter", "section"} else None)
    if chapter_number != CHAPTER_COUNT:
        raise ValueError(f"expected {CHAPTER_COUNT} chapters, found {chapter_number}")
    next_chapter = chapter_number
    for index in range(len(chapter_ordinals) - 1, -1, -1):
        if chapter_ordinals[index] is not None:
            next_chapter = chapter_ordinals[index] or next_chapter
        else:
            chapter_ordinals[index] = next_chapter

    units: list[Unit] = []
    asset_paths: set[Path] = set()
    for (row, body, role, assets), ordinal in zip(rendered, chapter_ordinals, strict=True):
        if ordinal is None or ordinal < 1:
            raise ValueError(f"cannot assign {row['unit_id']} to an EPUB chapter")
        part, chapter, section, _ = extract_context(body)
        units.append(
            Unit(
                row=row,
                text=body,
                unit_id=row["unit_id"],
                part=part,
                chapter=chapter,
                section=section,
                chapter_number=ordinal,
                document_name=f"chapter-{ordinal:02d}.xhtml",
                role=role,
            )
        )
        asset_paths.update(assets)

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
        "assets": [
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in sorted(asset_paths)
        ],
    }
    return units, provenance


def load_reference_map() -> tuple[dict, dict[str, dict]]:
    record = json.loads(REFERENCE_MAP_PATH.read_text(encoding="utf-8"))
    if record["schema"] != "openlogic-ps-Arab-PK-epub-reference-map/1":
        raise ValueError("unexpected EPUB reference map schema")
    references = record["references"]
    if record["scope"] != {
        "first_unit": "OLP-0001",
        "last_unit": f"OLP-{THROUGH_UNIT:04d}",
        "unit_count": THROUGH_UNIT,
    }:
        raise ValueError("reference map has the wrong cumulative scope")
    if record["reference_count"] != len(references) or not references:
        raise ValueError("reference map count is inconsistent")
    return record, references


def build_reference_targets(
    units: list[Unit], reference_map: dict[str, dict]
) -> dict[str, tuple[str, str]]:
    targets: dict[str, tuple[str, str]] = {}
    segment_start_pattern = re.compile(
        r"\\phantomsection\\label\{olpseg:([^}:]+-[^}:]+):start\}"
    )
    for unit in units:
        unit_text = strip_comments(unit.text)
        if unit.role == "part":
            part_key = f"{unit.part}:::part"
            targets[part_key] = (unit.document_name, anchor_slug(part_key))
        elif unit.role == "chapter":
            chapter_key = f"{unit.part}:{unit.chapter}::chap"
            targets[chapter_key] = (unit.document_name, anchor_slug(chapter_key))
        elif unit.role == "section" and re.search(
            r"\\olsection(?:\[[^\]]*\])?\{", unit_text
        ):
            section_key = f"{unit.part}:{unit.chapter}:{unit.section}:sec"
            targets[section_key] = (unit.document_name, anchor_slug(section_key))

        starts = [
            (match.start(), match.group(1))
            for match in segment_start_pattern.finditer(unit_text)
        ]
        if not starts:
            raise ValueError(f"{unit.unit_id} has no semantic segment anchors")
        positions = [position for position, _ in starts]
        for match in re.finditer(r"\\ollabel\{([^}]+)\}", unit_text):
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
        for match in re.finditer(r"\\label\{([^}]+)\}", unit_text):
            key = match.group(1)
            if key.startswith("olpseg:"):
                continue
            index = bisect.bisect_right(positions, match.start()) - 1
            if index < 0:
                raise ValueError(f"{unit.unit_id} label precedes first segment")
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
        unit_text = strip_comments(unit.text)
        for match in pattern.finditer(unit_text):
            env = match.group(1)
            counters[unit.chapter_number] += 1
            counts[env] += 1
            expected = f"{unit.chapter_number}.{counters[unit.chapter_number]}"
            end_start, _ = find_environment_end(unit_text, env, match.start())
            content = unit_text[match.end() : end_start]
            keys = [
                f"{unit.part}:{unit.chapter}:{unit.section}:{label}"
                for label in re.findall(r"\\ollabel\{([^}]+)\}", content)
            ]
            keys.extend(
                label
                for label in re.findall(r"\\label\{([^}]+)\}", content)
                if not label.startswith("olpseg:")
            )
            for key in keys:
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
        key = reader.base.reference_key(
            unit.part, unit.chapter, unit.section, options, label
        )
        return reference_link(state, key, unit.document_name), cursor

    return replace_command(text, "olref", handler)


def expand_crefs(text: str, unit: Unit, state: TransformState) -> str:
    """Render fully-qualified cleveref lists as separate internal links."""

    text = text.replace(r"\Cref", r"\cref")

    def handler(source: str, index: int) -> tuple[str, int]:
        argument, cursor = read_mandatory(source, index)
        keys = [item.strip() for item in argument.split(",") if item.strip()]
        if not keys:
            raise ValueError(f"empty cleveref list in {unit.unit_id}")
        links = [
            reference_link(state, key, unit.document_name) for key in keys
        ]
        state.stats["cref_occurrences"] += 1
        state.stats["cref_selected_links"] += len(links)
        if len(links) == 1:
            return links[0], cursor
        if len(links) == 2:
            return " او ".join(links), cursor
        return "، ".join(links[:-1]) + " او " + links[-1], cursor

    return replace_command(text, "cref", handler)


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

    def numbered_equation(body: str, _: int) -> str:
        labels = re.findall(r"\\ollabel\{([^}]+)\}", body)
        if not labels:
            return r"\begin{equation}" + body + r"\end{equation}"
        if len(labels) != 1:
            raise ValueError(f"unexpected equation labels in {unit.unit_id}: {labels}")
        key = f"{unit.part}:{unit.chapter}:{unit.section}:{labels[0]}"
        if key not in state.reference_map:
            raise ValueError(f"equation label lacks accepted PDF number: {key}")
        number = state.reference_map[key]["number"]
        state.stats["numbered_equations"] += 1
        marker = state.tokens.html(
            '<span class="equation-number" dir="ltr">('
            + html.escape(number)
            + ")</span>"
        )
        return r"\begin{equation}" + body + r"\end{equation}" + "\n" + marker + "\n"

    text = replace_environment(text, "equation", numbered_equation)
    text = re.sub(r"\\ollabel\{[^}]+\}", "", text)
    text = re.sub(r"\\label\{[^}]+\}", "", text)

    def file_id_handler(source: str, index: int) -> tuple[str, int]:
        cursor = index
        for _ in range(3):
            _, cursor = read_mandatory(source, cursor)
        return "", cursor

    text = replace_command(text, "olfileid", file_id_handler)

    def part_handler(source: str, index: int) -> tuple[str, int]:
        _, cursor = read_optional(source, index)
        part, cursor = read_mandatory(source, cursor)
        title, cursor = read_mandatory(source, cursor)
        key = f"{part}:::part"
        anchor = anchor_slug(key)
        number = state.reference_map[key]["number"]
        state.stats["part_headings"] += 1
        token = state.tokens.anchor(anchor, **{"class": "reference-anchor part-anchor"})
        return token + "\n" + rf"\section*{{برخه {number}: {title}}}", cursor

    text = replace_command(text, "olpart", part_handler)

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
    text = expand_crefs(text, unit, state)
    text = expand_olrefs(text, unit, state)
    if re.search(
        r"\\(?:olpart|olchapter|olsection|olfileid|ollabel|olref|"
        r"tagrefs|cref|Cref)\b",
        text,
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
        case_text = (
            case_text.replace(r"\indfrmp", formula)
            .replace(r"\indfrm", formula)
            .replace(r"\indcomplex", complex_formula)
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


def register_figure(
    unit: Unit,
    state: TransformState,
    tex_body: str,
    caption: str,
) -> str:
    figure_id = f"figure-{len(state.figures) + 1:03d}"
    asset_matches = re.findall(
        r"\\olasset(?:\[[^\]]*\])?\{([^{}]+)\}", tex_body
    )
    tikz_count = tex_body.count(r"\begin{tikzpicture}")
    if len(asset_matches) > 1 or (asset_matches and tikz_count):
        raise ValueError(f"ambiguous diagram source in {unit.unit_id}")
    if asset_matches:
        source_kind = "olasset"
        source_path = asset_matches[0]
        render_tex = rf"\input{{{source_path}}}"
    elif tikz_count >= 1:
        if tikz_count > 1 and (unit.unit_id != "OLP-0266" or tikz_count != 2):
            raise ValueError(f"unexpected grouped TikZ figure in {unit.unit_id}")
        source_kind = "inline_tikz"
        source_path = None
        start = tex_body.index(r"\begin{tikzpicture}")
        cursor = start
        for _ in range(tikz_count):
            begin = tex_body.index(r"\begin{tikzpicture}", cursor)
            _, end = find_environment_end(tex_body, "tikzpicture", begin)
            cursor = end
        render_tex = tex_body[start:end]
        if tikz_count > 1:
            render_tex = "\\begin{center}\n" + render_tex + "\n\\end{center}"
    else:
        raise ValueError(f"figure in {unit.unit_id} has no renderable diagram")
    render_tex = re.sub(r"EPUBANCHOR\d{8}TOKEN", "", render_tex)
    state.figures.append(
        {
            "id": figure_id,
            "unit_id": unit.unit_id,
            "source_kind": source_kind,
            "source_path": source_path,
            "tex_body": render_tex,
            "caption_tex": caption,
        }
    )
    alt = plain_title(caption) or "تخنيکي شکل"
    return state.tokens.html(
        '<img class="diagram" src="images/'
        + figure_id
        + '.svg" alt="'
        + html.escape(alt, quote=True)
        + '"/>'
    )


def transform_figures(text: str, unit: Unit, state: TransformState) -> str:
    """Convert captioned figures to image-bearing semantic blocks."""

    def handler(body: str, _: int) -> str:
        captions: list[str] = []

        def caption_handler(source: str, index: int) -> tuple[str, int]:
            _, cursor = read_optional(source, index)
            caption, cursor = read_mandatory(source, cursor)
            captions.append(caption)
            return "", cursor

        body = replace_command(body, "caption", caption_handler)
        if len(captions) != 1:
            raise ValueError(f"figure has {len(captions)} captions")
        anchors = re.findall(r"EPUBANCHOR\d{8}TOKEN", body)
        image = register_figure(unit, state, body, captions[0])
        marker = state.tokens.environment("semantic figure", "شکل")
        state.stats["environment_figure"] += 1
        return (
            "\n".join(anchors)
            + "\n\\begin{quote}\n"
            + rf"\textbf{{{marker} شکل}}\par"
            + "\n"
            + image
            + "\n"
            + captions[0]
            + "\n\\end{quote}"
        )

    return replace_environment(text, "figure", handler)


def transform_standalone_tikz(text: str, unit: Unit, state: TransformState) -> str:
    def handler(body: str, _: int) -> str:
        anchors = re.findall(r"EPUBANCHOR\d{8}TOKEN", body)
        tex_body = r"\begin{tikzpicture}" + body + r"\end{tikzpicture}"
        image = register_figure(unit, state, tex_body, "")
        marker = state.tokens.environment("semantic figure", "تخنيکي شکل")
        state.stats["environment_figure"] += 1
        return (
            "\n".join(anchors)
            + "\n\\begin{quote}\n"
            + rf"\textbf{{{marker} تخنيکي شکل}}\par"
            + "\n"
            + image
            + "\n\\end{quote}"
        )

    return replace_environment(text, "tikzpicture", handler)


def unwrap_diagram_math_wrappers(text: str) -> str:
    def for_environment(source: str, environment: str) -> str:
        def handler(body: str, _: int) -> str:
            if "EPUBHTML" not in body:
                return (
                    rf"\begin{{{environment}}}"
                    + body
                    + rf"\end{{{environment}}}"
                )
            body = re.sub(r"^\s*&\s*", "", body)
            body = re.sub(r"\\\\\s*$", "", body)
            return body.strip()

        return replace_environment(source, environment, handler)

    text = for_environment(text, "align")
    text = for_environment(text, "align*")

    def display_handler(match: re.Match[str]) -> str:
        body = match.group(1)
        if (
            "EPUBHTML" not in body
            and r"\begin{tabular}" not in body
        ):
            return match.group(0)
        return body.strip()

    return re.sub(
        r"\\\[(.*?)\\\]", display_handler, text, flags=re.DOTALL
    )


def transform_tables(text: str, state: TransformState) -> str:
    def handler(body: str, _: int) -> str:
        captions: list[str] = []

        def caption_handler(source: str, index: int) -> tuple[str, int]:
            _, cursor = read_optional(source, index)
            caption, cursor = read_mandatory(source, cursor)
            captions.append(caption)
            return "", cursor

        body = replace_command(body, "caption", caption_handler)
        body = re.sub(r"^\s*\[[^\]]*\]\s*", "", body)
        if len(captions) > 1:
            raise ValueError("table has more than one caption")
        marker = state.tokens.environment("semantic data-table", "جدول")
        state.stats["environment_table"] += 1
        caption = captions[0] if captions else ""
        return (
            "\\begin{quote}\n"
            + rf"\textbf{{{marker} جدول}}\par"
            + "\n"
            + body
            + ("\n" + caption if caption else "")
            + "\n\\end{quote}"
        )

    return replace_environment(text, "table", handler)


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

    def lambda_handler(source: str, index: int) -> tuple[str, int]:
        variable, cursor = read_optional(source, index)
        body, cursor = read_optional(source, cursor)
        result = r"\lambda"
        if variable is not None:
            result += " " + variable
        if body is not None:
            result += r".\," + body
        return result, cursor

    text = replace_command(text, "lambd", lambda_handler)

    def modal_sat_handler(source: str, index: int) -> tuple[str, int]:
        cursor = skip_space(source, index)
        negated = cursor < len(source) and source[cursor] == "/"
        if negated:
            cursor += 1
        model, cursor = read_mandatory(source, cursor)
        formula, cursor = read_mandatory(source, cursor)
        world, cursor = read_optional(source, cursor)
        left = rf"\mathfrak{{{model}}}"
        if world is not None:
            left += ", " + world
        relation = r"\nVdash" if negated else r"\Vdash"
        return left + " " + relation + " " + formula, cursor

    text = replace_command(text, "mSat", modal_sat_handler)

    def modal_model_handler(source: str, index: int) -> tuple[str, int]:
        model, cursor = read_mandatory(source, index)
        return rf"\mathfrak{{{model}}}", cursor

    text = replace_command(text, "mModel", modal_model_handler)

    def optional_operator(name: str, operator: str, font: str = "mathsf") -> None:
        nonlocal text

        def handler(source: str, index: int) -> tuple[str, int]:
            subscript, cursor = read_optional(source, index)
            result = rf"\{font}{{{operator}}}"
            if subscript is not None:
                result += rf"_{{{subscript}}}"
            return result, cursor

        text = replace_command(text, name, handler)

    optional_operator("OCon", "Con")
    optional_operator("Prf", "Prf", "mathrm")
    optional_operator("OPrf", "Prf")
    optional_operator("Refut", "Ref", "mathrm")
    optional_operator("ORefut", "Ref")
    optional_operator("Prov", "Prov", "mathrm")
    optional_operator("OProv", "Prov")
    optional_operator("RProv", "RProv", "mathrm")
    optional_operator("ORProv", "RProv")

    def cfind_handler(source: str, index: int) -> tuple[str, int]:
        function_index, cursor = read_mandatory(source, index)
        arity, cursor = read_optional(source, cursor)
        result = rf"\varphi_{{{function_index}}}"
        if arity is not None:
            result += rf"^{{{arity}}}"
        return result, cursor

    text = replace_command(text, "cfind", cfind_handler)

    def models_handler(source: str, index: int) -> tuple[str, int]:
        language, cursor = read_optional(source, index)
        cursor = skip_space(source, cursor)
        logic = None
        if cursor < len(source) and source[cursor] == "(":
            logic, cursor = read_group(source, cursor, "(", ")")
        theory, cursor = read_mandatory(source, cursor)
        result = r"\mathrm{Mod}"
        if logic is not None:
            result += rf"_{{{logic}}}"
        if language is not None:
            result += rf"^{{\mathcal{{{language}}}}}"
        result += f"({theory})"
        return result, cursor

    text = replace_command(text, "Mod", models_handler)

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
    text = replace_command(
        text, "iso", relation_handler(r"\simeq", r"\not\simeq")
    )
    text = replace_command(
        text, "elemequiv", relation_handler(r"\equiv", r"\not\equiv")
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
    text = text.replace(r"\centering", "")
    text = text.replace(
        r"\DeclareRobustCommand{\VDash}{\mathrel{||}\joinrel\Relbar}", ""
    )
    text = text.replace(r"\allowbreak", "")
    text = text.replace(r"\notag", r"\nonumber")
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


def normalize_nested_math_text(text: str) -> str:
    """Rewrite dollar-delimited formulas nested inside ``\text{...}``.

    XeLaTeX accepts the historical idiom, but Pandoc's texmath parser expects
    the mathematical spans outside the text command.
    """

    output: list[str] = []
    cursor = 0
    for match in re.finditer(r"\\text\{", text):
        if match.start() < cursor:
            continue
        argument, end = read_group(text, match.end() - 1)
        original_argument = argument

        def unwrap(source: str, index: int) -> tuple[str, int]:
            value, finish = read_mandatory(source, index)
            return value, finish

        def strip_href(source: str, index: int) -> tuple[str, int]:
            _, cursor = read_mandatory(source, index)
            label, cursor = read_mandatory(source, cursor)
            return label, cursor

        while re.search(r"\\(?:LR|RL|emph|textbf|textrm)\{", argument):
            previous = argument
            argument = replace_command(argument, "LR", unwrap)
            argument = replace_command(argument, "RL", unwrap)
            argument = replace_command(argument, "emph", unwrap)
            argument = replace_command(argument, "textbf", unwrap)
            argument = replace_command(argument, "textrm", unwrap)
            if argument == previous:
                break
        argument = replace_command(argument, "href", strip_href)
        if not re.search(r"(?<!\\)\$", argument):
            if argument == original_argument:
                continue
            output.append(text[cursor : match.start()])
            output.append(r"\text{" + argument + "}")
            cursor = end
            continue
        parts = re.split(r"(?<!\\)\$", argument)
        if len(parts) % 2 == 0:
            raise ValueError("unpaired dollar inside math text argument")
        replacement: list[str] = []
        for index, part in enumerate(parts):
            if not part:
                continue
            replacement.append(part if index % 2 else rf"\text{{{part}}}")
        output.append(text[cursor : match.start()])
        output.append("".join(replacement))
        cursor = end
    return "".join(output) + text[cursor:]


def normalize_math_emphasis(text: str) -> str:
    def replace_emphasis(body: str) -> str:
        def handler(source: str, index: int) -> tuple[str, int]:
            value, cursor = read_mandatory(source, index)
            return r"\text{" + value + "}", cursor

        return replace_command(body, "emph", handler)

    def for_environment(source: str, environment: str) -> str:
        return replace_environment(
            source,
            environment,
            lambda body, _: (
                rf"\begin{{{environment}}}"
                + replace_emphasis(body)
                + rf"\end{{{environment}}}"
            ),
        )

    for environment in (
        "align",
        "align*",
        "equation",
        "aligned",
        "array",
        "cases",
        "eqnarray*",
        "gather*",
        "multline*",
    ):
        text = for_environment(text, environment)
    text = re.sub(
        r"\\\[(.*?)\\\]",
        lambda match: r"\[" + replace_emphasis(match.group(1)) + r"\]",
        text,
        flags=re.DOTALL,
    )
    return text


def transform_unit(unit: Unit, state: TransformState) -> str:
    text = replace_source_structure(strip_comments(unit.text), unit, state)
    text = transform_figures(text, unit, state)
    text = transform_standalone_tikz(text, unit, state)
    text = unwrap_diagram_math_wrappers(text)
    text = transform_tables(text, state)
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
    text = transform_named_quote_environment(
        text, "history", state, "history", "تاريخي يادونه"
    )
    for env in ("explain", "intro", "digress", "center"):
        text = unwrap_environment(text, env, state)
    text = split_intertext_displays(text, state)
    text = expand_optional_notation(text)
    text = cleanup_latex(text)
    text = normalize_nested_math_text(text)
    text = normalize_math_emphasis(text)
    remaining_environments = Counter(
        re.findall(r"\\begin\{([^}]+)\}", text)
    )
    allowed = {
        "enumerate",
        "itemize",
        "quote",
        "align",
        "align*",
        "equation",
        "aligned",
        "eqnarray*",
        "gather*",
        "multline*",
        "cases",
        "array",
        "tabular",
        "verbatim",
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
            "په دې ټوليزه لوستيزه نسخه کښې د خلاص منطق د پروژې "
            "لومړنۍ مادې، ساده سټ نظريه، بياني او لومړۍ درجې "
            "منطق، د ثبوت نظامونه، موډل نظريه، محاسبويت، او د "
            "ټيورينګ ماشينونو لومړنۍ پېژندګلو شامل دي۔"
        ),
        (
            f"دا جزوي لوستونکی {THROUGH_UNIT} سرچينيز واحدونه (OLP-0001 تر "
            f"OLP-{THROUGH_UNIT:04d}) لري؛ د 722 واحدونو بشپړه ژباړه لا روانه "
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
        f"contains {THROUGH_UNIT} source units (OLP-0001 through OLP-{THROUGH_UNIT:04d}). "
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


def package_opf(
    chapter_count: int, identifier: str, figure_count: int
) -> bytes:
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
    for number in range(1, figure_count + 1):
        manifest_items.append(
            f'<item id="figure-{number:03d}" '
            f'href="images/figure-{number:03d}.svg" '
            'media-type="image/svg+xml"/>'
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


def install_figures(
    figures_dir: Path,
    tree: Path,
    figures: list[dict],
) -> dict:
    record_path = figures_dir / "figure-render.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    if (
        record.get("schema")
        != "openlogic-ps-Arab-PK-cumulative-epub-figure-render/1"
        or record.get("status") != "accepted"
        or record.get("figure_count") != EXPECTED_FIGURES
    ):
        raise ValueError("figure render record is not accepted")
    inventory_semantic_bytes = json.dumps(
        figures,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    inventory_semantic_sha256 = hashlib.sha256(
        inventory_semantic_bytes
    ).hexdigest()
    if (
        record.get("inventory", {}).get("semantic_sha256")
        != inventory_semantic_sha256
    ):
        raise ValueError(
            "rendered figures were prepared from a different transformed inventory"
        )
    expected_ids = [figure["id"] for figure in figures]
    if expected_ids != [
        f"figure-{number:03d}"
        for number in range(1, EXPECTED_FIGURES + 1)
    ]:
        raise ValueError("transformed figure inventory is incomplete")
    rendered = record.get("figures", [])
    if [item.get("id") for item in rendered] != expected_ids:
        raise ValueError("rendered figure inventory differs from content")
    image_dir = tree / "EPUB" / "images"
    image_dir.mkdir(parents=True)
    installed: list[dict] = []
    for figure, rendered_figure in zip(figures, rendered, strict=True):
        if (
            rendered_figure.get("unit_id") != figure["unit_id"]
            or rendered_figure.get("source_kind")
            != figure["source_kind"]
        ):
            raise ValueError(
                f"rendered figure provenance differs for {figure['id']}"
            )
        source = figures_dir / f"{figure['id']}.svg"
        if (
            not source.is_file()
            or sha256(source) != rendered_figure["svg"]["sha256"]
            or source.stat().st_size != rendered_figure["svg"]["bytes"]
        ):
            raise ValueError(f"rendered SVG differs for {figure['id']}")
        root = etree.parse(str(source)).getroot()
        root_qname = etree.QName(root)
        if (
            root_qname.namespace != "http://www.w3.org/2000/svg"
            or root_qname.localname != "svg"
        ):
            raise ValueError(f"invalid SVG root for {figure['id']}")
        if not root.get("viewBox"):
            raise ValueError(f"SVG lacks viewBox for {figure['id']}")
        destination = image_dir / source.name
        destination.write_bytes(source.read_bytes())
        installed.append(
            {
                "id": figure["id"],
                "unit_id": figure["unit_id"],
                "source_kind": figure["source_kind"],
                "caption": plain_title(figure["caption_tex"]),
                "path": f"EPUB/images/{source.name}",
                "bytes": destination.stat().st_size,
                "sha256": sha256(destination),
                "viewBox": root.get("viewBox"),
            }
        )
    return {
        "render_record": {
            "path": str(record_path),
            "sha256": sha256(record_path),
        },
        "figures": installed,
    }


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
.equation-number {
  display: block;
  text-align: left;
  margin-top: -0.7em;
}
table {
  border-collapse: collapse;
  margin: 1em auto;
  max-width: 100%;
}
th, td { border: 0.06em solid #888; padding: 0.3em 0.55em; }
img.diagram {
  display: block;
  width: auto;
  max-width: 100%;
  height: auto;
  margin: 0.8em auto;
}
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
    image_sources: list[tuple[str, str]] = []
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
        for element in root.xpath(
            "//x:img", namespaces={"x": XHTML_NS}
        ):
            source = element.get("src", "")
            alternative = element.get("alt", "").strip()
            if not alternative:
                raise ValueError(
                    f"image lacks alternative text in {path.name}"
                )
            image_sources.append((path.name, source))
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
                "//text()[not(ancestor::x:code) and "
                "not(ancestor::m:math)]",
                namespaces={"x": XHTML_NS, "m": MATHML_NS},
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

    expected_images = {
        f"images/figure-{number:03d}.svg"
        for number in range(1, EXPECTED_FIGURES + 1)
    }
    actual_images = [source for _, source in image_sources]
    if (
        len(actual_images) != EXPECTED_FIGURES
        or set(actual_images) != expected_images
    ):
        raise ValueError("XHTML image references are incomplete")
    for relative in sorted(expected_images):
        image_path = tree / "EPUB" / Path(relative)
        if not image_path.is_file():
            raise ValueError(f"missing EPUB image: {relative}")
        image_root = etree.parse(str(image_path), parser).getroot()
        image_qname = etree.QName(image_root)
        if (
            image_qname.namespace != "http://www.w3.org/2000/svg"
            or image_qname.localname != "svg"
            or not image_root.get("viewBox")
        ):
            raise ValueError(f"invalid EPUB SVG: {relative}")

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
        "figures": len(actual_images),
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
    if state.stats["segment_start_anchors"] != EXPECTED_SEGMENTS:
        raise ValueError(
            f"expected {EXPECTED_SEGMENTS} semantic segments, found "
            f"{state.stats['segment_start_anchors']}"
        )
    if len(state.figures) != EXPECTED_FIGURES:
        raise ValueError(
            f"expected {EXPECTED_FIGURES} figures, found "
            f"{len(state.figures)}"
        )
    for env, expected in expected_theorem_counts.items():
        actual = state.stats[f"environment_{env}"]
        if actual != expected:
            raise ValueError(
                f"{env} environment count mismatch: "
                f"{actual} vs {expected}"
            )

    figure_package = install_figures(
        args.figures_dir.resolve(), tree, state.figures
    )

    used_tokens: set[str] = set()
    used_environment_markers: set[str] = set()
    chapter_stats: dict[str, dict] = {}
    for chapter_number in range(1, CHAPTER_COUNT + 1):
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
    edition_scope = (
        "cumulative-through-church-rosser" if THROUGH_UNIT == 372 else
        "cumulative-through-incompleteness" if THROUGH_UNIT == 321 else
        "cumulative-through-computability"
    )
    identifier = "urn:uuid:" + str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            "https://github.com/KokunoYumeto/"
            "openlogic-ps-Arab-PK/"
            f"{edition_scope}/{EDITION_VERSION}",
        )
    )
    (tree / "EPUB" / "package.opf").write_bytes(
        package_opf(CHAPTER_COUNT, identifier, EXPECTED_FIGURES)
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
            "openlogic-ps-Arab-PK-cumulative-epub-build/1"
        ),
        "status": "built_and_locally_validated",
        "edition_version": EDITION_VERSION,
        "scope": {
            "first_unit": "OLP-0001",
            "last_unit": f"OLP-{THROUGH_UNIT:04d}",
            "unit_count": len(units),
            "chapter_count": CHAPTER_COUNT,
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
            "figure_renderer": {
                "path": "tools/render_cumulative_epub_figures.py",
                "sha256": sha256(
                    ROOT / "tools" / "render_cumulative_epub_figures.py"
                ),
            },
        },
        "figures": figure_package,
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
                "chapters": CHAPTER_COUNT,
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
    parser.add_argument("--through-unit", type=int, choices=(255, 321, 372), default=255)
    parser.add_argument("--reference-map", type=Path)
    parser.add_argument(
        "--build-dir", type=Path, required=True
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--figures-dir", type=Path, required=True
    )
    args = parser.parse_args()
    global REFERENCE_MAP_PATH, EDITION_VERSION, EDITION_MODIFIED
    global EPUB_NAME, SUBTITLE, CHAPTER_COUNT, EXPECTED_SEGMENTS
    global EXPECTED_FIGURES, THROUGH_UNIT
    THROUGH_UNIT = args.through_unit
    reader.EXPECTED_IDS = [f"OLP-{number:04d}" for number in range(1, THROUGH_UNIT + 1)]
    if THROUGH_UNIT == 321:
        EDITION_VERSION = "0.7.0"
        EDITION_MODIFIED = "2026-09-25T00:00:00Z"
        EPUB_NAME = "openlogic-ps-Arab-PK-cumulative-through-incompleteness-v0.7.0.epub"
        SUBTITLE = "له بنسټونو تر محاسبويت او د نيمګړتيا تر قضيو"
        CHAPTER_COUNT = 31
        EXPECTED_SEGMENTS = 3414
        EXPECTED_FIGURES = 31
        if args.reference_map is None:
            parser.error("--reference-map is required for OLP-0321")
    elif THROUGH_UNIT == 372:
        EDITION_VERSION = "0.8.0"
        EDITION_MODIFIED = "2026-09-26T00:00:00Z"
        EPUB_NAME = "openlogic-ps-Arab-PK-cumulative-through-church-rosser-v0.8.0.epub"
        SUBTITLE = "له بنسټونو تر چرچ--روسر خاصيته"
        CHAPTER_COUNT = 37
        EXPECTED_SEGMENTS = 3852
        EXPECTED_FIGURES = 31
        if args.reference_map is None:
            parser.error("--reference-map is required for OLP-0372")
    if args.reference_map is not None:
        REFERENCE_MAP_PATH = args.reference_map.resolve()
    build(args)


if __name__ == "__main__":
    main()
