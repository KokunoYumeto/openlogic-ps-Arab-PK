"""Build the isolated OLP-0056..OLP-0125 Pashto proof-systems reader.

This script only prepares deterministic TeX input.  TeX itself must be run via
tools/guard_tex.ps1, which owns the global mutex and captured Windows job.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evidence" / "SOURCE_MANIFEST.jsonl"
ALIGNMENT = ROOT / "evidence" / "ALIGNMENT.jsonl"
UPSTREAM_REVISION = "9620cc73f9c8e0ad003c514a5d3748f29611c4c0"
EXPECTED_IDS = [f"OLP-{number:04d}" for number in range(56, 126)]
DRIVER_IDS = {
    "OLP-0056",
    "OLP-0063",
    "OLP-0069",
    "OLP-0084",
    "OLP-0098",
    "OLP-0112",
}

# This reader deliberately fixes one reproducible upstream selection profile.
# Resolve that profile before TeX sees the flattened units: the upstream
# ``tagblock`` implementation delegates inactive blocks to the ``comment``
# environment, whose end marker cannot be found after the source files have
# been assembled into a different top-level document.
ACTIVE_TAGS = frozenset(
    {
        "FOL",
        "limitClause",
        "prfAX",
        "prfND",
        "prfSC",
        "prfTab",
        "prvAll",
        "prvAnd",
        "prvEx",
        "prvFalse",
        "prvIf",
        "prvIff",
        "prvNot",
        "prvOr",
        "prvTrue",
        "tagTrue",
    }
)
INACTIVE_TAGS = frozenset(
    {
        "defAll",
        "defAnd",
        "defEx",
        "defFalse",
        "defIf",
        "defIff",
        "defNot",
        "defOr",
        "defTrue",
        "probAll",
        "probAnd",
        "probEx",
        "probIf",
        "probIff",
        "probNot",
        "probOr",
    }
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# Four values are nominative singular, nominative plural, oblique singular,
# and oblique plural.  The upstream `a` and capitalization switches do not add
# articles or case distinctions in Pashto; suffix s/x selects the plural form.
TOKENS: dict[str, tuple[str, str, str, str]] = {
    "biconditional": ("دوه اړخيز شرطي",) * 4,
    "conditional": ("شرطي",) * 4,
    "constant": ("ثابت سمبول", "ثابت سمبولونه", "ثابت سمبول", "ثابت سمبولونو"),
    "denumerable": ("شمېرېدونکے لامتناهي",) * 4,
    "derivability": ("د اشتقاق وړتيا",) * 4,
    "derivable": ("د اشتقاق وړ",) * 4,
    "derivation": ("اشتقاق", "اشتقاقونه", "اشتقاق", "اشتقاقونو"),
    "derive": ("اشتقاق",) * 4,
    "discharge": ("ايستل",) * 4,
    "discharged": ("ايستل",) * 4,
    "element": ("غړے", "غړي", "غړي", "غړو"),
    "falsity": ("دروغوالی",) * 4,
    "formula": ("فارمول", "فارمولونه", "فارمول", "فارمولونو"),
    "free for": ("ازاد",) * 4,
    "identity": ("عينيت",) * 4,
    "main operator": ("اصلي عملګر", "اصلي عملګرونه", "اصلي عملګر", "اصلي عملګرونو"),
    "nonderivability": ("د اشتقاق نۀ وړتيا",) * 4,
    "operator": ("منطقي عملګر", "منطقي عملګرونه", "منطقي عملګر", "منطقي عملګرونو"),
    "propositional variable": ("بياني متغير", "بياني متغيرونه", "بياني متغير", "بياني متغيرونو"),
    "sentence": ("تړلے فارمول", "تړلي فارمولونه", "تړلي فارمول", "تړلو فارمولونو"),
    "signed formula": ("نښه لرونکے فارمول", "نښه لرونکي فارمولونه", "نښه لرونکي فارمول", "نښه لرونکو فارمولونو"),
    "structure": ("جوړښت", "جوړښتونه", "جوړښت", "جوړښتونو"),
    "tableau": ("تابلو", "تابلوګانې", "تابلو", "تابلوګانو"),
    "truth": ("رښتياوالی",) * 4,
    "undischarged": ("نۀ ايستل شوې",) * 4,
    "valuation": ("ارزښت ټاکنه", "ارزښت ټاکنې", "ارزښت ټاکنې", "ارزښت ټاکنو"),
    "variable": ("متغير", "متغيرونه", "متغير", "متغيرونو"),
}


def escaped_at(text: str, pos: int) -> bool:
    backslashes = 0
    pos -= 1
    while pos >= 0 and text[pos] == "\\":
        backslashes += 1
        pos -= 1
    return backslashes % 2 == 1


def balanced_argument(text: str, opening: int) -> tuple[str, int]:
    """Return the contents and exclusive end for a braced TeX argument."""
    if opening >= len(text) or text[opening] != "{":
        raise ValueError("expected opening brace")
    depth = 1
    pos = opening + 1
    while depth:
        if pos >= len(text):
            raise ValueError("unbalanced TeX argument")
        if text[pos] == "{" and not escaped_at(text, pos):
            depth += 1
        elif text[pos] == "}" and not escaped_at(text, pos):
            depth -= 1
        pos += 1
    return text[opening + 1 : pos - 1], pos


def skip_tex_space(text: str, pos: int) -> int:
    """Skip inter-argument whitespace and TeX comments."""
    while pos < len(text):
        if text[pos].isspace():
            pos += 1
            continue
        if text[pos] == "%" and (pos == 0 or text[pos - 1] != "\\"):
            newline = text.find("\n", pos)
            return len(text) if newline == -1 else skip_tex_space(text, newline + 1)
        break
    return pos


def macro_arguments(text: str, start: int, name: str, count: int) -> tuple[list[str], int]:
    pos = start + len(name) + 1  # leading backslash plus command name
    arguments: list[str] = []
    for _ in range(count):
        pos = skip_tex_space(text, pos)
        argument, pos = balanced_argument(text, pos)
        arguments.append(argument)
    return arguments, pos


def tag_value(tag: str) -> bool:
    tag = tag.strip()
    if tag in ACTIVE_TAGS:
        return True
    if tag in INACTIVE_TAGS:
        return False
    if tag.startswith("not"):
        positive = tag[3:]
        if positive in ACTIVE_TAGS:
            return False
        if positive in INACTIVE_TAGS:
            return True
    raise ValueError(f"reader selection profile does not define tag {tag!r}")


def selected(tags: str) -> bool:
    r"""Match upstream \iftag semantics: a comma list is inclusive OR."""
    values = [tag_value(tag) for tag in tags.split(",") if tag.strip()]
    if not values:
        raise ValueError("empty reader selection tag list")
    return any(values)


def replace_tag_macros(
    text: str,
    *,
    command: str,
    item_prefix: bool,
    stats: Counter,
) -> str:
    pattern = re.compile(rf"(?<!\\)\\{command}\b")
    while True:
        matches = list(pattern.finditer(text))
        if not matches:
            return text
        # TeX expands the outer macro before any macros in its arguments.  The
        # source relies on that laziness in discarded branches, so resolve the
        # first lexical occurrence and then recurse into the retained text.
        match = matches[0]
        arguments, end = macro_arguments(text, match.start(), command, 3)
        tags, yes, no = arguments
        active = selected(tags)
        replacement = yes if active else no
        if command == "tagitem" and replacement.strip() and item_prefix:
            replacement = "\\item " + replacement
        stats[f"{command}_{'selected' if active else 'rejected'}"] += 1
        text = text[: match.start()] + replacement + text[end:]


def replace_tag_environment(text: str, environment: str, stats: Counter) -> str:
    begin_pattern = re.compile(rf"(?<!\\)\\begin\{{{environment}\}}")
    end_marker = rf"\end{{{environment}}}"
    while True:
        matches = list(begin_pattern.finditer(text))
        if not matches:
            return text
        match = matches[-1]
        pos = skip_tex_space(text, match.end())
        tags, body_start = balanced_argument(text, pos)
        close = text.find(end_marker, body_start)
        if close == -1:
            raise ValueError(f"unclosed {environment} environment")
        body = text[body_start:close]
        close_end = close + len(end_marker)
        active_count = sum(tag_value(tag) for tag in tags.split(",") if tag.strip())
        if environment == "tagblock":
            replacement = body if active_count else ""
        elif active_count > 1:
            replacement = "\\begin{enumerate}" + body + "\\end{enumerate}"
        else:
            replacement = replace_tag_macros(
                body,
                command="tagitem",
                item_prefix=False,
                stats=stats,
            )
            replacement = re.sub(r"\\item(?:\[[^\]]*\])?", "", replacement)
        stats[f"{environment}_{'selected' if active_count else 'rejected'}"] += 1
        text = text[: match.start()] + replacement + text[close_end:]


def replace_tagprobs(text: str, stats: Counter) -> str:
    pattern = re.compile(r"(?<!\\)\\tagprob\b")
    while True:
        matches = list(pattern.finditer(text))
        if not matches:
            return text
        match = matches[-1]
        pos = skip_tex_space(text, match.end())
        outer_tag = "tagTrue"
        if pos < len(text) and text[pos] == "[":
            bracket_end = text.find("]", pos + 1)
            if bracket_end == -1:
                raise ValueError("unclosed optional tagprob argument")
            outer_tag = text[pos + 1 : bracket_end]
            pos = skip_tex_space(text, bracket_end + 1)
        tags, pos = balanced_argument(text, pos)
        pos = skip_tex_space(text, pos)
        begin_marker = r"\begin{prob}"
        end_marker = r"\end{prob}"
        if not text.startswith(begin_marker, pos):
            raise ValueError("tagprob is not followed by a prob environment")
        body_start = pos + len(begin_marker)
        close = text.find(end_marker, body_start)
        if close == -1:
            raise ValueError("tagprob has no closing prob environment")
        close_end = close + len(end_marker)
        tail = skip_tex_space(text, close_end)
        if not text.startswith(r"\tagendprob", tail):
            raise ValueError("tagprob has no tagendprob terminator")
        end = tail + len(r"\tagendprob")
        active = selected(outer_tag) and selected(tags)
        replacement = text[pos:close_end] if active else ""
        stats[f"tagprob_{'selected' if active else 'rejected'}"] += 1
        text = text[: match.start()] + replacement + text[end:]


def prune_segment_anchors(text: str, stats: Counter) -> str:
    empty_pattern = re.compile(
        r"\\phantomsection\\label\{olpseg:([^{}]+):start\}"
        r"\s*\\label\{olpseg:\1:end\}"
    )
    text, empty_count = empty_pattern.subn("", text)
    stats["empty_segment_anchor_pairs_pruned"] += empty_count

    starts = re.findall(r"\\label\{olpseg:([^{}]+):start\}", text)
    ends = re.findall(r"\\label\{olpseg:([^{}]+):end\}", text)
    unmatched = (set(starts) - set(ends)) | (set(ends) - set(starts))
    for segment_id in sorted(unmatched):
        escaped = re.escape(segment_id)
        text = re.sub(
            rf"\\phantomsection\\label\{{olpseg:{escaped}:start\}}\s*",
            "",
            text,
        )
        text = re.sub(rf"\\label\{{olpseg:{escaped}:end\}}\s*", "", text)
    stats["unpaired_segment_anchors_pruned"] += len(unmatched)

    starts = re.findall(r"\\label\{olpseg:([^{}]+):start\}", text)
    ends = re.findall(r"\\label\{olpseg:([^{}]+):end\}", text)
    if starts != ends:
        raise ValueError("profile resolution left crossed semantic-segment anchors")
    return text


def resolve_profile_conditionals(text: str) -> tuple[str, Counter]:
    """Resolve every selective-typesetting construct used by this tranche."""
    stats: Counter = Counter()
    text = replace_tag_macros(text, command="iftag", item_prefix=False, stats=stats)
    text = replace_tag_environment(text, "tagblock", stats)
    text = replace_tag_environment(text, "tagenumerate", stats)
    text = replace_tag_macros(text, command="tagitem", item_prefix=True, stats=stats)
    text = replace_tagprobs(text, stats)
    residual = re.search(
        r"\\(?:iftag|tagitem|tagprob|tagendprob)\b|"
        r"\\(?:begin|end)\{(?:tagblock|tagenumerate)\}",
        text,
    )
    if residual:
        raise ValueError(f"unresolved reader selection construct: {residual.group(0)}")
    text = prune_segment_anchors(text, stats)
    return text, stats


def strip_subfile(text: str) -> str:
    if "\\begin{document}" not in text or "\\end{document}" not in text:
        raise ValueError("translated unit lacks a document wrapper")
    return text.split("\\begin{document}", 1)[1].rsplit("\\end{document}", 1)[0]


def remove_imports(text: str) -> str:
    pattern = re.compile(
        r"(?m)^[ \t]*\\olimport\*?(?:\[[^\]]*\])?\{[^{}]+\}(?:\[[^\]]*\])?[ \t]*%?.*$"
    )
    text = pattern.sub("", text)
    text = re.sub(r"(?m)^[ \t]*\\OLEndChapterHook[ \t]*$", "", text)
    return text


def normalize_token_key(key: str) -> str:
    return " ".join(key.split())


def expand_tokens(text: str) -> str:
    # Pashto supplies no indefinite article before this already complete noun
    # phrase.  The retained upstream macro is therefore intentionally empty.
    text = re.sub(r"\\(?:Article|article)\{[^{}]+\}", "", text)

    # Two inflection-sensitive phrases need a masculine plural participle.
    text = text.replace("ټول فرضونه !!{discharged} وي", "ټول فرضونه ايستل شوي وي")
    text = text.replace("!!{undischarged} فرضونه", "نۀ ايستل شوي فرضونه")

    token_pattern = re.compile(r"!!(?P<cap>\^)?(?P<article>a)?\{(?P<key>[^{}]+)\}(?P<suffix>[sdx]?)")

    def replace_token(match: re.Match[str]) -> str:
        key = normalize_token_key(match.group("key"))
        if key not in TOKENS:
            raise KeyError(f"unmapped source token: {key!r}")
        suffix = match.group("suffix")
        plural = suffix in {"s", "x"}
        # The reader does not need an oblique switch: OLP-0056..0125 contains
        # no psOblique calls.  Preserve a four-form table for future extension.
        return TOKENS[key][1 if plural else 0]

    text = token_pattern.sub(replace_token, text)

    def replace_usetoken(match: re.Match[str]) -> str:
        switch, raw_key = match.groups()
        key = normalize_token_key(raw_key)
        if key not in TOKENS:
            raise KeyError(f"unmapped usetoken key: {key!r}")
        index = {"s": 0, "S": 0, "p": 1, "P": 1}.get(switch)
        if index is None:
            raise KeyError(f"unsupported usetoken switch: {switch!r}")
        return TOKENS[key][index]

    text = re.sub(r"\\usetoken\{([^{}]+)\}\{([^{}]+)\}", replace_usetoken, text)
    return text


def wrap_rtl_math_text(text: str) -> str:
    # bussproofs-extra parses these displays with literal dollar delimiters
    # (for example ``\Axiom$left \fCenter right$``).  Replacing those dollars
    # by an LR wrapper would change the macro call itself, so protect the whole
    # delimited command.  The surrounding prooftree environment is already LTR.
    proof_math: list[str] = []
    proof_pattern = re.compile(
        r"\\(?:Axiom|Deduce|UnaryInf|BinaryInf|TrinaryInf|QuaternaryInf)\$.*?\$",
        re.DOTALL,
    )

    def protect_proof_math(match: re.Match[str]) -> str:
        marker = f"@@OLP_PROOF_MATH_{len(proof_math):05d}@@"
        proof_math.append(match.group(0))
        return marker

    text = proof_pattern.sub(protect_proof_math, text)

    # Text embedded in mathematical material must explicitly return to RTL.
    output: list[str] = []
    cursor = 0
    for match in re.finditer(r"\\(?:text|intertext)\{", text):
        if match.start() < cursor:
            continue
        argument, end = balanced_argument(text, match.end() - 1)
        output.append(text[cursor : match.end()])
        output.append("\\RL{")
        output.append(argument)
        output.append("}}")
        cursor = end
    text = "".join(output) + text[cursor:]

    # Inline mathematical runs retain their source bytes and are displayed LTR.
    text = re.sub(r"(?<!\\)\$([^$]+?)(?<!\\)\$", lambda m: "\\LR{$" + m.group(1) + "$}", text)
    for index, original in enumerate(proof_math):
        marker = f"@@OLP_PROOF_MATH_{index:05d}@@"
        if text.count(marker) != 1:
            raise ValueError("proof-math protection marker was altered")
        text = text.replace(marker, original)
    return text


def apply_layout_overrides(text: str) -> tuple[str, dict[str, int]]:
    """Insert one deterministic break where a long external ID crowds math."""
    old = (
        r"د \olref[syn][ext]{prop:extensionality} له مخې"
        "\n  "
        r"\LR{$\Sat/{M'}{!A(x)}[s]$}۔"
    )
    new = (
        r"د \olref[syn][ext]{prop:extensionality} له مخې\linebreak"
        "\n  "
        r"\LR{$\Sat/{M'}{!A(x)}[s]$}۔"
    )
    count = text.count(old)
    if count != 1:
        raise ValueError(f"expected one OLP-0109 external-reference layout site, found {count}")
    return text.replace(old, new), {"OLP-0109-B018-forced-break": count}


def prepare_unit(text: str, *, driver: bool, alignment_rows: list[dict]) -> tuple[str, Counter]:
    source_blocks = re.split(r"\n\s*\n", strip_subfile(text).strip())

    def alignment_body(row: dict) -> str:
        candidate = row["target"]
        if "\\begin{document}" in candidate:
            candidate = candidate.split("\\begin{document}", 1)[1]
        if "\\end{document}" in candidate:
            candidate = candidate.rsplit("\\end{document}", 1)[0]
        return candidate.strip("\r\n")

    body_alignment_rows: list[tuple[str, str]] = []
    inside_document = False
    for row in alignment_rows:
        raw_block = row["target"]
        if "\\begin{document}" in raw_block:
            inside_document = True
        if not inside_document:
            continue
        candidate = alignment_body(row)
        if candidate:
            body_alignment_rows.append((candidate, row["segment_id"]))
        if "\\end{document}" in raw_block:
            inside_document = False
            break
    if len(source_blocks) != len(body_alignment_rows):
        raise ValueError(
            f"reader body has {len(source_blocks)} blocks but alignment has {len(body_alignment_rows)} body blocks"
        )
    paired_blocks: list[tuple[str, str]] = []
    for index, (source_block, (aligned_block, segment_id)) in enumerate(
        zip(source_blocks, body_alignment_rows), 1
    ):
        if source_block != aligned_block:
            raise ValueError(
                f"reader/alignment body block {index} differs: " + repr(source_block[:180])
            )
        paired_blocks.append((source_block, segment_id))
    prepared_blocks: list[str] = []
    for source_block, segment_id in paired_blocks:
        block = remove_imports(source_block) if driver else source_block
        if not driver and "\\olimport" in block:
            raise ValueError("non-driver unit unexpectedly imports another source unit")
        block = wrap_rtl_math_text(expand_tokens(block)).strip()
        if block:
            prepared_blocks.append(
                f"\\phantomsection\\label{{olpseg:{segment_id}:start}}\n"
                f"{block}\n"
                f"\\label{{olpseg:{segment_id}:end}}"
            )
    body = "\n\n".join(prepared_blocks)
    body, profile_stats = resolve_profile_conditionals(body)
    if re.search(r"!!|\\usetoken|\\Article|\\article|\\olimport", body):
        raise ValueError("reader preparation left a source-only token or import")
    if "\\psOblique" in body:
        raise ValueError("unexpected psOblique call in proof-systems tranche")
    return body.strip(), profile_stats


def reference_inventory(texts: list[tuple[dict, str]]) -> dict:
    labels: dict[str, str] = {}
    reference_keys: list[str] = []
    for row, source_text in texts:
        ids = re.findall(
            r"\\olfileid(?:\[[^\]]*\])?\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}",
            source_text,
        )
        chapter = re.search(
            r"\\olchapter(?:\[[^\]]*\])?\{([^}]+)\}\{([^}]+)\}\{",
            source_text,
        )
        if ids:
            part, chapter_id, section = ids[0]  # first branch is the FOL branch
        elif chapter:
            part, chapter_id, section = chapter.group(1), chapter.group(2), ""
        else:
            raise ValueError(f"unit {row['unit_id']} has no OpenLogic file ID")
        if chapter:
            labels[f"{chapter.group(1)}:{chapter.group(2)}::chap"] = row["unit_id"]
        for label in re.findall(r"\\ollabel\{([^}]+)\}", source_text):
            labels[f"{part}:{chapter_id}:{section}:{label}"] = row["unit_id"]
        for match in re.finditer(r"\\olref((?:\[[^\]]*\]){0,3})\{([^}]+)\}", source_text):
            options = re.findall(r"\[([^\]]*)\]", match.group(1))
            label = match.group(2)
            if not options:
                key = f"{part}:{chapter_id}:{section}:{label}"
            elif len(options) == 1:
                key = f"{part}:{chapter_id}:{options[0]}:{label}"
            elif len(options) == 2:
                key = f"{part}:{options[0]}:{options[1]}:{label}"
            else:
                key = f"{options[0]}:{options[1]}:{options[2]}:{label}"
            reference_keys.append(key)
    counts = Counter(reference_keys)
    return {
        "defined_label_count": len(labels),
        "reference_occurrences": len(reference_keys),
        "unique_reference_count": len(counts),
        "internal_candidate_occurrences": sum(count for key, count in counts.items() if key in labels),
        "external_candidate_occurrences": sum(count for key, count in counts.items() if key not in labels),
        "external_candidate_ids": [
            {"key": key, "occurrences": counts[key]}
            for key in sorted(counts)
            if key not in labels
        ],
        "note": (
            "Candidate counts include references in inactive notFOL branches. The TeX profile selects FOL; "
            "the reader macro prints exact OpenLogic IDs only for selected references outside this volume."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", type=Path, required=True)
    args = parser.parse_args()
    build_dir = args.build_dir.resolve()
    build_dir.mkdir(parents=True, exist_ok=True)

    rows = [json.loads(line) for line in MANIFEST.read_text(encoding="utf-8").splitlines() if line.strip()]
    alignment_rows = [
        json.loads(line)
        for line in ALIGNMENT.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    alignment_by_unit: dict[str, list[dict]] = {}
    for alignment in alignment_rows:
        alignment_by_unit.setdefault(alignment["unit_id"], []).append(alignment)
    selected = [row for row in rows if row["unit_id"] in EXPECTED_IDS]
    if [row["unit_id"] for row in selected] != EXPECTED_IDS:
        raise ValueError("manifest does not contain the exact OLP-0056..OLP-0125 sequence")
    if any(row["source_commit"] != UPSTREAM_REVISION for row in selected):
        raise ValueError("source revision mismatch")

    prepared: list[str] = []
    profile_stats: Counter = Counter()
    inventory_texts: list[tuple[dict, str]] = []
    input_files: list[dict] = []
    for row in selected:
        upstream = ROOT / "upstream" / row["source_path"]
        target = ROOT / "ps-Arab-PK" / row["source_path"]
        if not upstream.is_file() or not target.is_file():
            raise FileNotFoundError(f"missing source/target pair for {row['unit_id']}")
        if sha256(upstream) != row["source_sha256"]:
            raise ValueError(f"manifest hash mismatch for {row['unit_id']}")
        target_text = target.read_text(encoding="utf-8")
        if unicodedata.normalize("NFC", target_text) != target_text:
            raise ValueError(f"target is not NFC: {row['unit_id']}")
        prepared_unit, unit_profile_stats = prepare_unit(
            target_text,
            driver=row["unit_id"] in DRIVER_IDS,
            alignment_rows=alignment_by_unit.get(row["unit_id"], []),
        )
        prepared.append(prepared_unit)
        profile_stats.update(unit_profile_stats)
        inventory_texts.append((row, target_text))
        input_files.append(
            {
                "unit_id": row["unit_id"],
                "source_path": f"upstream/{row['source_path']}",
                "source_sha256": sha256(upstream),
                "target_path": f"ps-Arab-PK/{row['source_path']}",
                "target_sha256": sha256(target),
                "role": "chapter_driver" if row["unit_id"] in DRIVER_IDS else "reader_unit",
            }
        )

    translated_bundle_units = sum(
        1
        for row in rows
        if (ROOT / "ps-Arab-PK" / row["source_path"]).is_file()
    )
    preamble = ROOT / "tools" / "proof-systems-reader-preamble.tex"
    preamble_text = preamble.read_text(encoding="utf-8")
    generated = (
        preamble_text.replace("OLP_UPSTREAM_PATH", ROOT.joinpath("upstream").as_posix())
        .replace("OLP_READER_UNITS", str(len(selected)))
        .replace("OLP_DRAFT_UNITS", str(translated_bundle_units))
        + "\n\n"
        + "\n\n".join(prepared)
        + "\n\n\\end{document}\n"
    )
    generated, layout_overrides = apply_layout_overrides(generated)
    if unicodedata.normalize("NFC", generated) != generated:
        raise ValueError("generated TeX is not NFC")
    reader_tex = build_dir / "reader.tex"
    reader_tex.write_bytes(generated.encode("utf-8"))

    record = {
        "schema": "openlogic-ps-Arab-PK-proof-systems-reader-inputs/1",
        "status": "prepared",
        "profile": "FOL; all primitive connectives and quantifiers; all four proof systems",
        "profile_resolution": {
            "active_tags": sorted(ACTIVE_TAGS),
            "inactive_tags": sorted(INACTIVE_TAGS),
            "resolved_construct_counts": dict(sorted(profile_stats.items())),
        },
        "source_revision": UPSTREAM_REVISION,
        "unit_range": {"first": "OLP-0056", "last": "OLP-0125", "count": len(selected)},
        "chapter_driver_ids": sorted(DRIVER_IDS),
        "translated_bundle_units": translated_bundle_units,
        "input_files": input_files,
        "token_renderings": {
            key: {"singular": value[0], "plural": value[1], "oblique_singular": value[2], "oblique_plural": value[3]}
            for key, value in sorted(TOKENS.items())
        },
        "reference_inventory": reference_inventory(inventory_texts),
        "preamble": {"path": preamble.relative_to(ROOT).as_posix(), "sha256": sha256(preamble)},
        "builder": {"path": Path(__file__).relative_to(ROOT).as_posix(), "sha256": sha256(Path(__file__))},
        "manifest": {"path": MANIFEST.relative_to(ROOT).as_posix(), "sha256": sha256(MANIFEST)},
        "alignment": {"path": ALIGNMENT.relative_to(ROOT).as_posix(), "sha256": sha256(ALIGNMENT)},
        "page_anchor_policy": (
            "Zero-width start/end labels surround each retained aligned semantic block. "
            "The accepted auxiliary file supplies verified page ranges after pagination stabilizes."
        ),
        "layout_overrides": layout_overrides,
        "generated_tex": {"path": "reader.tex", "bytes": reader_tex.stat().st_size, "sha256": sha256(reader_tex)},
        "tex_execution_policy": "Run only through tools/guard_tex.ps1 with Global\\InterlanguageTeXSlotV1.",
    }
    (build_dir / "build-inputs.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "reader_units": len(selected),
                "translated_bundle_units": translated_bundle_units,
                "reader_tex_bytes": reader_tex.stat().st_size,
                "reader_tex_sha256": sha256(reader_tex),
            }
        )
    )


if __name__ == "__main__":
    main()
