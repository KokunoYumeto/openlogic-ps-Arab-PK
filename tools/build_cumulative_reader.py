"""Build the cumulative OLP-0001..OLP-0255 Pashto reader.

The script prepares deterministic XeLaTeX input only.  TeX must be run via
``tools/guard_tex.ps1`` so the global Interlanguage TeX mutex and captured
Windows job remain authoritative.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

import build_completeness_reader as base


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evidence" / "SOURCE_MANIFEST.jsonl"
ALIGNMENT = ROOT / "evidence" / "ALIGNMENT.jsonl"
UPSTREAM_REVISION = "9620cc73f9c8e0ad003c514a5d3748f29611c4c0"
EXPECTED_IDS = [f"OLP-{number:04d}" for number in range(1, 256)]

# Match the default profile declared by the frozen upstream configuration.
ACTIVE_TAGS = base.ACTIVE_TAGS | frozenset(
    {"TMs", "lambda", "novice", "math", "compsci", "phil", "cmplCCS", "cmplMCS"}
)
INACTIVE_TAGS = base.INACTIVE_TAGS
base.ACTIVE_TAGS = ACTIVE_TAGS
base.INACTIVE_TAGS = INACTIVE_TAGS

TOKENS = dict(base.TOKENS)
TOKENS.update(
    {
        "injective": ("يو پر يو",) * 4,
        "surjective": (
            "پر هدف سټ بشپړه",
            "پر هدف سټ بشپړې",
            "پر هدف سټ بشپړې",
            "پر هدف سټ بشپړو",
        ),
        "bijective": (
            "دوه اړخيزه يو پر يو",
            "دوه اړخيزې يو پر يو",
            "دوه اړخيزې يو پر يو",
            "دوه اړخيزو يو پر يو",
        ),
        "injection": (
            "يو پر يو تابع",
            "يو پر يو تابعې",
            "يو پر يو تابعې",
            "يو پر يو تابعو",
        ),
        "surjection": (
            "پر هدف سټ بشپړه تابع",
            "پر هدف سټ بشپړې تابعې",
            "پر هدف سټ بشپړې تابعې",
            "پر هدف سټ بشپړو تابعو",
        ),
        "bijection": (
            "دوه اړخيزه يو پر يو تابع",
            "دوه اړخيزې يو پر يو تابعې",
            "دوه اړخيزې يو پر يو تابعې",
            "دوه اړخيزو يو پر يو تابعو",
        ),
        "subformula": (
            "فرعي فارمول",
            "فرعي فارمولونه",
            "فرعي فارمول",
            "فرعي فارمولونو",
        ),
        "computably enumerable": ("په محاسبوي ډول د شمېر وړ",) * 4,
        "c.e.": ("c.e.",) * 4,
        "axiomatizability": ("د محاسبوي بديهي کېدو وړتيا",) * 4,
        "axiomatizable": ("په محاسبوي ډول بديهي کېدونکې",) * 4,
        "axiomatized": ("بديهي‌کړې",) * 4,
        "decidable": ("د پرېکړې وړ",) * 4,
        "represents": ("تمثيل",) * 4,
    }
)
base.TOKENS = TOKENS

CITATION_ITEMS = r"""
\clearpage
\begin{LTR}\latinfont
\begin{thebibliography}{99}
\bibitem[Benacerraf(1965)]{Benacerraf1965} Paul Benacerraf. 1965. ``What Numbers Could Not Be.'' \emph{The Philosophical Review} 74(1): 47--73.
\bibitem[Frege(1884)]{Frege1884} Gottlob Frege. 1884. \emph{Die Grundlagen der Arithmetik}. Breslau: Wilhelm Koebner.
\bibitem[Cantor(1892)]{Cantor1892} Georg Cantor. 1892. ``Uber eine elementare Frage der Mannigfaltigkeitslehre.'' \emph{Jahresbericht der Deutschen Mathematiker-Vereinigung} 1: 75--78.
\bibitem[Potter(2004)]{Potter2004} Michael Potter. 2004. \emph{Set Theory and Its Philosophy}. Oxford University Press.
\bibitem[Conway(2006)]{Conway2006} John Conway. 2006. ``The Power of Mathematics.'' In \emph{Power}, Cambridge University Press.
\bibitem[O'Connor and Robertson(2005)]{OConnorRobertson:RN} John J. O'Connor and Edmund F. Robertson. 2005. ``The Real Numbers: Stevin to Hilbert.''
\bibitem[Katz and Katz(2012)]{KatzKatz2012} Karin Usadi Katz and Mikhail G. Katz. 2012. ``Stevin Numbers and Reality.'' \emph{Foundations of Science} 17(2): 109--123.
\bibitem[Hilbert(2013)]{EwaldSieg2013} David Hilbert. 2013. \emph{Lectures on the Foundations of Arithmetic and Logic 1917--1933}. Edited by William Bragg Ewald and Wilfried Sieg. Springer.
\bibitem[Dedekind(1888)]{Dedekind1888} Richard Dedekind. 1888. \emph{Was sind und was sollen die Zahlen?} Braunschweig: Vieweg.
\bibitem[Magnus et al.(2021)]{Magnus2021} P. D. Magnus et al. 2021. \emph{Forall x: Calgary. An Introduction to Formal Logic}. Open Logic Project.
\bibitem[Smullyan(1968)]{Smullyan1968} Raymond M. Smullyan. 1968. \emph{First-Order Logic}. New York: Springer.
\bibitem[Zuckerman(1973)]{Zuckerman1973} Martin M. Zuckerman. 1973. ``Formation Sequences for Propositional Formulas.'' \emph{Notre Dame Journal of Formal Logic} 14(1): 134--138.
\end{thebibliography}
\end{LTR}
""".strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_tag_macros_flexible(
    text: str, *, command: str, item_prefix: bool, stats: Counter
) -> str:
    """Resolve tag macros, accepting the two historical two-argument iftags."""
    pattern = re.compile(rf"(?<!\\)\\{command}\b")
    while True:
        matches = list(pattern.finditer(text))
        if not matches:
            return text
        match = matches[0]
        try:
            pos = match.end()
            tags, pos = base.balanced_argument(text, base.skip_tex_space(text, pos))
            yes, pos = base.balanced_argument(text, base.skip_tex_space(text, pos))
            third = base.skip_tex_space(text, pos)
            if third < len(text) and text[third] == "{":
                no, end = base.balanced_argument(text, third)
            elif command == "iftag":
                no, end = "", pos
                stats["iftag_implicit_empty_else"] += 1
            else:
                raise ValueError("tagitem lacks its third argument")
        except ValueError as exc:
            context = text[match.start() : match.start() + 180].replace("\n", "\\n")
            raise ValueError(f"cannot parse \\{command} near {context!r}") from exc
        active = base.selected(tags)
        replacement = yes if active else no
        if command == "tagitem" and replacement.strip() and item_prefix:
            replacement = "\\item " + replacement
        stats[f"{command}_{'selected' if active else 'rejected'}"] += 1
        text = text[: match.start()] + replacement + text[end:]


def replace_probtag_environment(text: str, stats: Counter) -> str:
    begin = re.compile(r"\\begin\{probtag\}\{([^{}]+)\}")
    end_marker = r"\end{probtag}"
    while True:
        matches = list(begin.finditer(text))
        if not matches:
            return text
        match = matches[-1]
        close = text.find(end_marker, match.end())
        if close < 0:
            raise ValueError("unclosed probtag environment")
        body = text[match.end() : close]
        active = base.selected(match.group(1))
        replacement = "\\begin{prob}" + body + "\\end{prob}" if active else ""
        stats[f"probtag_{'selected' if active else 'rejected'}"] += 1
        text = text[: match.start()] + replacement + text[close + len(end_marker) :]


def resolve_profile_conditionals(text: str) -> tuple[str, Counter]:
    stats: Counter = Counter()
    text = replace_tag_macros_flexible(
        text, command="iftag", item_prefix=False, stats=stats
    )
    text = base.replace_tag_environment(text, "tagblock", stats)
    text = base.replace_tag_environment(text, "tagenumerate", stats)
    text = replace_tag_macros_flexible(
        text, command="tagitem", item_prefix=True, stats=stats
    )
    text = base.replace_tagprobs(text, stats)
    text = replace_probtag_environment(text, stats)
    residual = re.search(
        r"\\(?:iftag|tagitem|tagprob|tagendprob)\b|"
        r"\\(?:begin|end)\{(?:tagblock|tagenumerate|probtag)\}",
        text,
    )
    if residual:
        raise ValueError(f"unresolved reader selection construct: {residual.group(0)}")
    return base.prune_segment_anchors(text, stats), stats


def extract_body(text: str) -> tuple[str, bool]:
    if r"\begin{document}" not in text:
        return text, False
    if r"\end{document}" not in text:
        raise ValueError("translated unit has an opening document wrapper only")
    return (
        text.split(r"\begin{document}", 1)[1].rsplit(r"\end{document}", 1)[0],
        True,
    )


def alignment_candidates(rows: list[dict], wrapped: bool) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    inside = not wrapped
    for row in rows:
        raw = row["target"]
        if wrapped and r"\begin{document}" in raw:
            inside = True
        if not inside:
            continue
        candidate = raw
        if r"\begin{document}" in candidate:
            candidate = candidate.split(r"\begin{document}", 1)[1]
        if r"\end{document}" in candidate:
            candidate = candidate.rsplit(r"\end{document}", 1)[0]
        # The alignment ledger preserves the historical checkout's newline
        # representation per block.  The target files are intentionally LF,
        # so normalize only line endings before exact sequential placement.
        candidate = candidate.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
        if candidate:
            candidates.append((candidate, row["segment_id"]))
        if wrapped and r"\end{document}" in raw:
            break
    return candidates


def anchor_aligned_body(text: str, rows: list[dict], unit_id: str) -> str:
    body, wrapped = extract_body(text)
    candidates = alignment_candidates(rows, wrapped)
    output: list[str] = []
    cursor = 0
    for candidate, segment_id in candidates:
        start = body.find(candidate, cursor)
        if start < 0:
            context = candidate[:160].replace("\n", "\\n")
            raise ValueError(
                f"{unit_id} alignment target cannot be located after byte {cursor}: {context!r}"
            )
        output.append(body[cursor:start])
        output.append(f"\\phantomsection\\label{{olpseg:{segment_id}:start}}\n")
        output.append(candidate)
        output.append(f"\n\\label{{olpseg:{segment_id}:end}}")
        cursor = start + len(candidate)
    output.append(body[cursor:])
    return "".join(output)


def remove_imports(text: str) -> str:
    text = re.sub(
        r"\\olimport\*?(?:\[[^\]]*\])?\{[^{}]+\}(?:\[[^\]]*\])?",
        "",
        text,
    )
    return re.sub(r"(?m)^[ \t]*\\OLEnd(?:Chapter|Part)Hook[ \t]*$", "", text)


def expand_tokens(text: str) -> str:
    oblique = re.compile(r"\\psOblique\{!!(?P<cap>\^)?(?P<article>a)?\{(?P<key>[^{}]+)\}(?P<suffix>[sdx]?)\}")

    def replace_oblique(match: re.Match[str]) -> str:
        key = base.normalize_token_key(match.group("key"))
        if key not in TOKENS:
            raise KeyError(f"unmapped oblique source token: {key!r}")
        plural = match.group("suffix") in {"s", "x"}
        return TOKENS[key][3 if plural else 2]

    text = oblique.sub(replace_oblique, text)
    # One inherited Pashto sentence uses the verb token without a following
    # light verb; the other occurrences deliberately add کوي/کړي/کول.
    text = text.replace("!!{represents}~$D$", "تمثيلوي~$D$")
    text = base.expand_tokens(text)

    def replace_printtoken(match: re.Match[str]) -> str:
        switch, raw_key = match.groups()
        key = base.normalize_token_key(raw_key)
        if key not in TOKENS:
            raise KeyError(f"unmapped printtoken key: {key!r}")
        index = {"s": 0, "S": 0, "p": 1, "P": 1}.get(switch)
        if index is None:
            raise KeyError(f"unsupported printtoken switch: {switch!r}")
        return TOKENS[key][index]

    return re.sub(r"\\printtoken\{([^{}]+)\}\{([^{}]+)\}", replace_printtoken, text)


def rewrite_assets(text: str, source_path: str) -> tuple[str, list[Path]]:
    source_dir = Path(source_path).parent
    assets: list[Path] = []
    pattern = re.compile(r"\\olasset(?P<opt>\[[^\]]*\])?\{(?P<path>[^{}]+)\}")

    def replace(match: re.Match[str]) -> str:
        raw = match.group("path")
        if raw.startswith(r"\olpath/"):
            # In the imported OpenLogic tree \olpath denotes the repository
            # content root; this asset lives in the shared top-level assets/.
            relative = Path(raw[len(r"\olpath/") :])
        elif raw.startswith("assets/"):
            relative = Path(raw)
        else:
            relative = source_dir / raw
        absolute = (ROOT / "upstream" / relative).resolve()
        if not absolute.is_file():
            raise FileNotFoundError(f"asset for {source_path} is missing: {absolute}")
        assets.append(absolute)
        return rf"\olasset{match.group('opt') or ''}{{{absolute.as_posix()}}}"

    return pattern.sub(replace, text), assets


def context(text: str) -> tuple[str, str, str, str]:
    file_ids = re.findall(
        r"\\olfileid(?:\[[^\]]*\])?\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}",
        text,
    )
    chapter = re.search(
        r"\\olchapter(?:\[[^\]]*\])?\{([^}]+)\}\{([^}]+)\}\{", text
    )
    part = re.search(r"\\olpart(?:\[[^\]]*\])?\{([^}]+)\}\{", text)
    if file_ids:
        return (*file_ids[0], "section")
    if chapter:
        return chapter.group(1), chapter.group(2), "", "chapter"
    if part:
        return part.group(1), "", "", "part"
    return "", "", "", "front"


def label_keys(text: str) -> set[str]:
    part, chapter, section, role = context(text)
    labels: set[str] = set()
    if role == "part":
        labels.add(f"{part}:::part")
    if role == "chapter":
        labels.add(f"{part}:{chapter}::chap")
    if role == "section" and re.search(r"\\olsection(?:\[[^\]]*\])?\{", text):
        labels.add(f"{part}:{chapter}:{section}:sec")
    for label in re.findall(r"\\ollabel\{([^}]+)\}", text):
        labels.add(f"{part}:{chapter}:{section}:{label}")
    for label in re.findall(r"\\label\{([^}]+)\}", text):
        if not label.startswith("olpseg:"):
            # A small number of inherited sources use already-qualified raw
            # LaTeX labels rather than \ollabel.  They are first-class reader
            # destinations and must participate in duplicate/reference checks.
            labels.add(label)
    return labels


def upstream_label_index(rows: list[dict]) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for row in rows:
        path = ROOT / "upstream" / row["source_path"]
        text = path.read_text(encoding="utf-8")
        ids = re.findall(
            r"\\olfileid(?:\[[^\]]*\])?\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}",
            text,
        )
        chapters = re.findall(
            r"\\olchapter(?:\[[^\]]*\])?\{([^}]+)\}\{([^}]+)\}\{", text
        )
        parts = re.findall(r"\\olpart(?:\[[^\]]*\])?\{([^}]+)\}\{", text)
        contexts = ids or [(part, chapter, "") for part, chapter in chapters]
        if not contexts and parts:
            contexts = [(parts[0], "", "")]

        def add(key: str, line: int) -> None:
            index.setdefault(
                key,
                {"source_path": row["source_path"], "line": line, "unit_id": row["unit_id"]},
            )

        lines = text.splitlines()
        if parts:
            line = next(i for i, value in enumerate(lines, 1) if r"\olpart" in value)
            add(f"{parts[0]}:::part", line)
        if chapters:
            line = next(i for i, value in enumerate(lines, 1) if r"\olchapter" in value)
            for part, chapter in chapters:
                add(f"{part}:{chapter}::chap", line)
        if contexts:
            for part, chapter, section in contexts:
                section_line = next(
                    (i for i, value in enumerate(lines, 1) if r"\olsection" in value), None
                )
                if section_line:
                    add(f"{part}:{chapter}:{section}:sec", section_line)
                for line, value in enumerate(lines, 1):
                    for label in re.findall(r"\\ollabel\{([^}]+)\}", value):
                        add(f"{part}:{chapter}:{section}:{label}", line)
                    for label in re.findall(r"\\label\{([^}]+)\}", value):
                        if not label.startswith("olpseg:"):
                            add(label, line)
    return index


def render_external_references(
    text: str,
    *,
    selected_labels: set[str],
    upstream_labels: dict[str, dict],
) -> tuple[str, Counter]:
    part, chapter, section, _role = context(text)
    counts: Counter = Counter()
    pattern = re.compile(r"\\(?P<command>olref|Olref)((?:\[[^\]]*\]){0,3})\{([^}]+)\}")

    def replace(match: re.Match[str]) -> str:
        line_start = text.rfind("\n", 0, match.start()) + 1
        if text[line_start:match.start()].lstrip().startswith("%"):
            return match.group(0)
        options = re.findall(r"\[([^\]]*)\]", match.group(2))
        key = base.reference_key(part, chapter, section, options, match.group(3))
        if key in selected_labels:
            return match.group(0)
        if key not in upstream_labels:
            raise ValueError(f"unresolved OpenLogic reference has no frozen target: {key}")
        target = upstream_labels[key]
        url = (
            "https://github.com/OpenLogicProject/OpenLogic/blob/"
            f"{UPSTREAM_REVISION}/{target['source_path']}#L{target['line']}"
        ).replace("#", r"\#")
        counts[key] += 1
        return (
            r"\emph{د OpenLogic اړونده سرچينيزه برخه}"
            r"\nobreakspace\LR{\href{" + url + r"}{\latinfont\scriptsize [OLP]}}"
        )

    return pattern.sub(replace, text), counts


def resolve_label_conditionals(text: str, selected_labels: set[str]) -> tuple[str, Counter]:
    """Resolve oliflabeldef after the complete selected label set is known."""
    pattern = re.compile(r"\\oliflabeldef\b")
    stats: Counter = Counter()
    while True:
        matches = list(pattern.finditer(text))
        if not matches:
            return text, stats
        match = matches[0]
        try:
            args, end = base.macro_arguments(text, match.start(), "oliflabeldef", 3)
        except ValueError as exc:
            context = text[match.start() : match.start() + 180].replace("\n", "\\n")
            raise ValueError(f"cannot parse oliflabeldef near {context!r}") from exc
        key, yes, no = args
        active = key in selected_labels
        stats[f"oliflabeldef_{'selected' if active else 'rejected'}"] += 1
        text = text[: match.start()] + (yes if active else no) + text[end:]


def wrap_rtl_math_text(text: str) -> str:
    """Apply the established bidi wrappers without splitting display math.

    The inherited reader helper deliberately targets inline ``$...$`` runs.
    A literal ``$$...$$`` display therefore looks like an empty inline run
    followed by one very long inline run, which can consume later prose.  Keep
    TeX comments and active displays out of that pass, prepare the contents of
    each display independently, and then restore the exact delimiters.
    """

    comments: list[str] = []

    def wrap_fragment(fragment: str) -> str:
        # A few source formulas put inline ``$...$`` fragments inside a
        # ``\text{...}`` argument which itself sits inside outer math.  Hide
        # those text arguments while the outer delimiters are paired, prepare
        # their inner math independently, and restore them afterwards.
        textual: list[str] = []
        pieces: list[str] = []
        fragment_cursor = 0
        for match in re.finditer(r"\\(?:text|intertext)\{", fragment):
            if match.start() < fragment_cursor:
                continue
            argument, end = base.balanced_argument(
                fragment, match.end() - 1
            )
            marker = f"@@OLP_MATH_TEXT_{len(textual):05d}@@"
            command = match.group(0)[:-1]
            prepared_argument = base.wrap_rtl_math_text(argument)
            textual.append(
                command + r"{\RL{" + prepared_argument + "}}"
            )
            pieces.append(fragment[fragment_cursor : match.start()])
            pieces.append(marker)
            fragment_cursor = end
        pieces.append(fragment[fragment_cursor:])
        prepared = base.wrap_rtl_math_text("".join(pieces))
        for index, original in enumerate(textual):
            marker = f"@@OLP_MATH_TEXT_{index:05d}@@"
            if prepared.count(marker) != 1:
                raise ValueError("math-text protection marker was altered")
            prepared = prepared.replace(marker, original)
        return prepared

    def protect_comment(match: re.Match[str]) -> str:
        marker = f"@@OLP_TEX_COMMENT_{len(comments):05d}@@"
        comments.append(match.group(0))
        return marker

    # A percent preceded by a backslash is a printed percent, not a comment.
    text = re.sub(r"(?<!\\)%[^\r\n]*", protect_comment, text)

    delimiters = [match.start() for match in re.finditer(r"(?<!\\)\$\$", text)]
    if len(delimiters) % 2:
        raise ValueError("unpaired active $$ display delimiter")

    displays: list[str] = []
    output: list[str] = []
    cursor = 0
    for index in range(0, len(delimiters), 2):
        start = delimiters[index]
        end = delimiters[index + 1]
        output.append(text[cursor:start])
        marker = f"@@OLP_DISPLAY_MATH_{len(displays):05d}@@"
        displays.append(text[start + 2 : end])
        output.append(marker)
        cursor = end + 2
    output.append(text[cursor:])
    text = wrap_fragment("".join(output))

    for index, display in enumerate(displays):
        marker = f"@@OLP_DISPLAY_MATH_{index:05d}@@"
        if text.count(marker) != 1:
            raise ValueError("display-math protection marker was altered")
        prepared = wrap_fragment(display)
        text = text.replace(marker, "$$" + prepared + "$$")

    for index, comment in enumerate(comments):
        marker = f"@@OLP_TEX_COMMENT_{index:05d}@@"
        if text.count(marker) != 1:
            raise ValueError("TeX-comment protection marker was altered")
        text = text.replace(marker, comment)
    return text


def prepare_unit(text: str, rows: list[dict], row: dict) -> tuple[str, Counter, list[Path]]:
    body = anchor_aligned_body(text, rows, row["unit_id"])
    if row["unit_id"] == "OLP-0039":
        # Frozen upstream non-enumerability-alt.tex closes the outer
        # oliflabeldef argument after the following unconditional sentence,
        # leaving the macro without its required third argument.  Recover the
        # only grammatically and typographically coherent grouping for this
        # generated reader; source and translation bytes remain unchanged.
        old = (
            "شي۔}{} خو اوس مهال دا لږ نرم بيان بايد هېڅ ګډوډي جوړه نۀ کړي۔}"
            "\n\\end{explain}"
        )
        new = (
            "شي۔}}{} خو اوس مهال دا لږ نرم بيان بايد هېڅ ګډوډي جوړه نۀ کړي۔"
            "\n\\end{explain}"
        )
        if body.count(old) != 1:
            raise ValueError("OLP-0039 source-syntax recovery site changed")
        body = body.replace(old, new)
    if row["unit_id"] == "OLP-0040":
        # The two upstream reduction alternatives reuse the same fully
        # qualified raw LaTeX label.  Both units belong in the complete source
        # coverage, but a cumulative reader needs distinct destinations.
        # Preserve the preferred reduction.tex label and disambiguate only the
        # alternative copy in generated readers.
        old = r"\label{sfr:siz:red:prob:nat-nat}"
        new = r"\label{sfr:siz:red-alt:prob:nat-nat}"
        if body.count(old) != 1:
            raise ValueError("OLP-0040 duplicate-label recovery site changed")
        body = body.replace(old, new)
    if row["unit_id"] == "OLP-0151":
        # The translated punctuation following the source's TeX control-space
        # retained the backslash before the Pashto comma, creating the
        # undefined control sequence ``\،``.  Remove only that stale control
        # slash in generated readers; source and translation bytes remain
        # unchanged.
        old = "او~!\\، او د"
        new = "او~!، او د"
        if body.count(old) != 1:
            raise ValueError("OLP-0151 source-syntax recovery site changed")
        body = body.replace(old, new)
    body = remove_imports(body)
    body, assets = rewrite_assets(body, row["source_path"])
    body = wrap_rtl_math_text(expand_tokens(body))
    body, profile_stats = resolve_profile_conditionals(body)
    if re.search(r"!!|\\(?:use|print)token|\\Article|\\article|\\olimport|\\psOblique", body):
        raise ValueError(f"{row['unit_id']} preparation left a source-only macro")
    if unicodedata.normalize("NFC", body) != body:
        raise ValueError(f"prepared unit is not NFC: {row['unit_id']}")
    return body.strip(), profile_stats, assets


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--through-unit", type=int, default=255)
    parser.add_argument("--preamble", type=Path, default=ROOT / "tools" / "cumulative-reader-preamble.tex")
    args = parser.parse_args()
    build_dir = args.build_dir.resolve()
    build_dir.mkdir(parents=True, exist_ok=True)
    if args.through_unit not in (255, 321):
        raise ValueError("supported cumulative reader boundaries are OLP-0255 and OLP-0321")
    expected_ids = [f"OLP-{number:04d}" for number in range(1, args.through_unit + 1)]

    rows = [
        json.loads(line)
        for line in MANIFEST.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    selected = rows[:args.through_unit]
    if [row["unit_id"] for row in selected] != expected_ids:
        raise ValueError(f"manifest does not contain exact OLP-0001..OLP-{args.through_unit:04d} sequence")
    if any(row["source_commit"] != UPSTREAM_REVISION for row in selected):
        raise ValueError("source revision mismatch")

    alignment_rows = [
        json.loads(line)
        for line in ALIGNMENT.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    alignment_by_unit: dict[str, list[dict]] = {}
    for item in alignment_rows:
        alignment_by_unit.setdefault(item["unit_id"], []).append(item)

    prepared: list[tuple[dict, str]] = []
    profile_stats: Counter = Counter()
    input_files: list[dict] = []
    asset_paths: set[Path] = set()
    for row in selected:
        upstream = ROOT / "upstream" / row["source_path"]
        target = ROOT / "ps-Arab-PK" / row["source_path"]
        if not upstream.is_file() or not target.is_file():
            raise FileNotFoundError(row["unit_id"])
        if sha256(upstream) != row["source_sha256"]:
            raise ValueError(f"manifest hash mismatch for {row['unit_id']}")
        target_text = target.read_text(encoding="utf-8")
        if unicodedata.normalize("NFC", target_text) != target_text:
            raise ValueError(f"target is not NFC: {row['unit_id']}")
        body, unit_profile, assets = prepare_unit(
            target_text, alignment_by_unit.get(row["unit_id"], []), row
        )
        prepared.append((row, body))
        profile_stats.update(unit_profile)
        asset_paths.update(assets)
        role = context(body)[3]
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
    for _row, body in prepared:
        overlap = selected_labels & label_keys(body)
        if overlap:
            raise ValueError(f"duplicate selected labels: {sorted(overlap)[:8]}")
        selected_labels.update(label_keys(body))
    upstream_labels = upstream_label_index(rows)

    rendered: list[str] = []
    external_counts: Counter = Counter()
    for row, body in prepared:
        body, label_stats = resolve_label_conditionals(body, selected_labels)
        profile_stats.update(label_stats)
        body, counts = render_external_references(
            body, selected_labels=selected_labels, upstream_labels=upstream_labels
        )
        rendered.append(body)
        external_counts.update(counts)

    preamble = args.preamble.resolve()
    if not preamble.is_file() or not preamble.is_relative_to(ROOT):
        raise ValueError("reader preamble must be a file inside this repository")
    generated = (
        preamble.read_text(encoding="utf-8")
        .replace("OLP_UPSTREAM_PATH", (ROOT / "upstream").as_posix())
        .replace("OLP_READER_UNITS", str(len(selected)))
        + "\n\n"
        + "\n\n".join(rendered)
        + "\n\n"
        + CITATION_ITEMS
        + "\n\n\\end{document}\n"
    )
    # Semantic segment anchors may occur inside amsmath or TikZ displays.  A
    # normal \label there is captured by the enclosing display and can trigger
    # amsmath's "Multiple \label's" error.  Emit the page-only AUX labels
    # directly instead; the EPUB builder continues to consume the preparatory
    # \label form before this final reader-only rewrite.
    generated = re.sub(
        r"\\phantomsection\\label\{olpseg:([^{}]+):start\}",
        r"\\olpseganchor{\1}{start}",
        generated,
    )
    generated = re.sub(
        r"\\label\{olpseg:([^{}]+):end\}",
        r"\\olpseganchor{\1}{end}",
        generated,
    )
    if unicodedata.normalize("NFC", generated) != generated:
        raise ValueError("generated TeX is not NFC")
    if re.search(r"!!|\\(?:use|print)token|\\olimport|\\psOblique", generated):
        raise ValueError("generated TeX contains an unresolved source-only macro")
    reader_tex = build_dir / "reader.tex"
    reader_tex.write_bytes(generated.encode("utf-8"))

    chapter_ids = [row["unit_id"] for row, body in prepared if context(body)[3] == "chapter"]
    part_ids = [row["unit_id"] for row, body in prepared if context(body)[3] == "part"]
    selected_segment_ids = re.findall(r"\\olpseganchor\{([^{}]+)\}\{start\}", generated)
    if selected_segment_ids != re.findall(
        r"\\olpseganchor\{([^{}]+)\}\{end\}", generated
    ):
        raise ValueError("generated semantic segment anchors are crossed")

    record = {
        "schema": "openlogic-ps-Arab-PK-cumulative-reader-inputs/1",
        "status": "prepared",
        "source_revision": UPSTREAM_REVISION,
        "unit_range": {"first": "OLP-0001", "last": f"OLP-{args.through_unit:04d}", "count": args.through_unit},
        "profile": "frozen upstream default: FOL, all primitive connectives and quantifiers, all proof systems, TMs, lambda, novice, math, computer-science and philosophy examples",
        "profile_resolution": {
            "active_tags": sorted(ACTIVE_TAGS),
            "inactive_tags": sorted(INACTIVE_TAGS),
            "resolved_construct_counts": dict(sorted(profile_stats.items())),
        },
        "part_driver_ids": part_ids,
        "chapter_driver_ids": chapter_ids,
        "chapter_count": len(chapter_ids),
        "semantic_segment_count": len(selected_segment_ids),
        "semantic_segment_anchor_encoding": "Direct page-only AUX writes via \\olpseganchor, safe inside amsmath and TikZ displays.",
        "selected_label_count": len(selected_labels),
        "external_reference_rendering": {
            "policy": "Every selected out-of-range or out-of-profile reference is a human-readable Pashto link to its exact label location in the frozen upstream revision.",
            "occurrences": sum(external_counts.values()),
            "references": [
                {
                    "key": key,
                    "occurrences": external_counts[key],
                    **upstream_labels[key],
                }
                for key in sorted(external_counts)
            ],
        },
        "source_syntax_recoveries": [
            {
                "unit_id": "OLP-0039",
                "source_path": "content/sets-functions-relations/size-of-sets/non-enumerability-alt.tex",
                "finding": "The frozen source closes a two-branch oliflabeldef after the following unconditional sentence and therefore supplies no third macro argument.",
                "reader_recovery": "Close the conditional footnote before its empty else branch and retain the following translated sentence unconditionally.",
                "source_bytes_changed": False,
                "target_bytes_changed": False,
            },
            {
                "unit_id": "OLP-0151",
                "source_path": "content/first-order-logic/syntax-and-semantics/first-order-languages.tex",
                "finding": "The translated punctuation after the source's TeX control-space retained a backslash before a Pashto comma, producing the undefined control sequence \\،.",
                "reader_recovery": "Remove the stale control-space backslash while retaining the literal alternate negation symbol and Pashto comma.",
                "source_bytes_changed": False,
                "target_bytes_changed": False,
            },
            {
                "unit_id": "OLP-0040",
                "source_path": "content/sets-functions-relations/size-of-sets/reduction-alt.tex",
                "finding": "The two frozen reduction alternatives reuse the fully qualified raw label sfr:siz:red:prob:nat-nat, which is multiply defined when all source units are included.",
                "reader_recovery": "Retain the preferred reduction.tex label and rename only the generated alternate-reader destination to sfr:siz:red-alt:prob:nat-nat.",
                "source_bytes_changed": False,
                "target_bytes_changed": False,
            },
        ],
        "input_files": input_files,
        "assets": [
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in sorted(asset_paths)
        ],
        "preamble": {
            "path": preamble.relative_to(ROOT).as_posix(),
            "sha256": sha256(preamble),
        },
        "builder": {
            "path": Path(__file__).relative_to(ROOT).as_posix(),
            "sha256": sha256(Path(__file__)),
        },
        "manifest": {"path": MANIFEST.relative_to(ROOT).as_posix(), "sha256": sha256(MANIFEST)},
        "alignment": {"path": ALIGNMENT.relative_to(ROOT).as_posix(), "sha256": sha256(ALIGNMENT)},
        "generated_tex": {
            "path": "reader.tex",
            "bytes": reader_tex.stat().st_size,
            "sha256": sha256(reader_tex),
        },
        "tex_execution_policy": "Run only through tools/guard_tex.ps1 with Global\\InterlanguageTeXSlotV1.",
    }
    (build_dir / "build-inputs.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": "prepared",
                "reader_units": args.through_unit,
                "parts": len(part_ids),
                "chapters": len(chapter_ids),
                "segments": len(selected_segment_ids),
                "external_references": sum(external_counts.values()),
                "reader_tex_bytes": reader_tex.stat().st_size,
                "reader_tex_sha256": sha256(reader_tex),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
