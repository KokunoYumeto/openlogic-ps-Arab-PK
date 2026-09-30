"""Prepare a cumulative Pashto reader within the full 722-unit source manifest.

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
    {"TMs", "lambda", "novice", "math", "compsci", "phil", "cmplCCS", "cmplMCS",
     "prvBox", "prvDiamond"}
)
INACTIVE_TAGS = base.INACTIVE_TAGS | frozenset(
    {"defBox", "defDiamond", "probBox", "probDiamond",
     "probFalse", "probTrue", "proband"}
)
base.ACTIVE_TAGS = ACTIVE_TAGS
base.INACTIVE_TAGS = INACTIVE_TAGS
base.INACTIVE_TAGS = INACTIVE_TAGS

TOKENS = dict(base.TOKENS)
TOKENS.update(
    {
        "proof": ("ثبوت", "ثبوتونه", "ثبوت", "ثبوتونو"),
        "provable": ("د ثابتولو وړ",) * 4,
        "prove": ("ثابت",) * 4,
        "height": ("لوړوالے", "لوړوالي", "لوړوالي", "لوړوالو"),
        # Frozen open-logic-config.sty:1672--1678: exact diagram colours and names.
        "colorC": ("سور",) * 4,
        "colorD": ("آبي",) * 4,
        "colorE": ("زرغون",) * 4,
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
        "lambda define": ("لامبډا-تعريف", "لامبډا-تعريفوي", "لامبډا-تعريف", "لامبډا-تعريفوي"),
        "lambda defined": ("لامبډا-تعريف",) * 4,
        "lambda definable": ("د لامبډا په وسيله د تعريف وړ",) * 4,
        "parameter": ("پارامېټر", "پارامېټرونه", "پارامېټر", "پارامېټرونو"),
        "relational model": (
            "اړيکيز مدل", "اړيکيز مدلونه", "اړيکيز مدل", "اړيکيز مدلونو"
        ),
    }
)
base.TOKENS = TOKENS

def bibliography_inputs(body: str, build_dir: Path) -> tuple[str, dict]:
    """Use the exact frozen database; do not hand-select a small bibliography."""
    source = ROOT / "upstream" / "bib" / "open-logic.bib"
    database = source.read_text(encoding="utf-8")
    keys = set(re.findall(r"@\w+\s*\{\s*([^,\s]+)\s*,", database))
    cited: set[str] = set()
    for match in re.finditer(r"\\cite[a-zA-Z]*\*?(?:\[[^\]]*\])*\{([^{}]*)\}", body):
        cited.update(key.strip() for key in match[1].split(","))
    missing = cited - keys
    if missing:
        raise ValueError(f"cited keys absent from frozen bibliography: {sorted(missing)}")
    # Bibliography notes can cite other entries. Select their finite closure on
    # the first pass, so BibTeX need not discover missing note citations later.
    starts = list(re.finditer(r"@\w+\s*\{\s*([^,\s]+)\s*,", database))
    entries = {match[1]: database[match.start():starts[i + 1].start() if i + 1 < len(starts) else len(database)]
               for i, match in enumerate(starts)}
    assert set(entries) == keys
    selected = set(cited)
    for _ in range(len(keys) + 1):
        dependencies: set[str] = set()
        for key in sorted(selected):
            entry = entries[key]
            for match in re.finditer(r"\\cite[a-zA-Z]*\*?(?:\[[^\]]*\])*\{([^{}]*)\}", entry):
                dependencies.update(item.strip() for item in match[1].split(","))
            dependencies.update(re.findall(r'\bcrossref\s*=\s*[{"]([^}"]+)[}"]', entry, re.I))
        if dependencies - keys:
            raise ValueError(f"bibliography dependency keys absent from frozen database: {sorted(dependencies - keys)}")
        expanded = selected | dependencies
        if expanded == selected:
            break
        selected = expanded
    else:
        raise ValueError("finite bibliography citation closure did not converge")
    additional = sorted(selected - cited)
    dependency = build_dir / "open-logic.bib"
    dependency.write_bytes(source.read_bytes())
    tex = r"""\clearpage
\begin{LTR}\latinfont
""" + (r"\nocite{" + ",".join(additional) + "}\n" if additional else "") + r"""\bibliographystyle{plainnat}
\bibliography{open-logic}
\end{LTR}"""
    return tex, {
        "source_path": source.relative_to(ROOT).as_posix(),
        "source_sha256": sha256(source),
        "build_dependency": dependency.name,
        "build_dependency_sha256": sha256(dependency),
        "cited_keys": sorted(cited),
        "bibliography_note_dependency_keys": additional,
        "selected_keys_including_dependencies": sorted(selected),
        "database_key_count": len(keys),
        "missing_keys": [],
        "style": "plainnat",
        "execution": "BibTeX inside the same acquired guarded job, after XeLaTeX pass one",
    }


def photo_inputs(body: str) -> tuple[str, dict, set[Path]]:
    """Require every selected portrait, complete original credit and localization."""
    photo_ids = sorted(set(re.findall(r"\\olphoto(?:\[[^\]]*\])?\{([a-z-]+)\}", body)))
    assets: set[Path] = set()
    sections: list[str] = []
    for photo_id in photo_ids:
        directory = ROOT / "assets" / "photos" / photo_id
        image = directory / f"{photo_id}-small.png"
        original = directory / f"{photo_id}-credit.tex"
        localized = ROOT / "ps-Arab-PK" / "photocredits" / f"{photo_id}-credit.tex"
        for path in (image, original, localized, directory / "README.md"):
            if not path.is_file():
                raise FileNotFoundError(f"required portrait dependency: {path.relative_to(ROOT)}")
            assets.add(path)
        sections.append(
            r"\par\medskip\noindent "
            + localized.read_text(encoding="utf-8").strip()
            + "\n\n" + r"\textbf{د اصلي سرچينې بشپړ انتساب او شرطونه:}"
            + "\n" + r"\begin{LTR}\latinfont\small "
            + original.read_text(encoding="utf-8").strip()
            + "\n" + r"\end{LTR}" + "\n"
        )
    if photo_ids:
        assets.add(ROOT / "assets" / "photos" / "README.md")
        assets.add(ROOT / "ps-Arab-PK" / "photocredits" / "INTRO.tex")
        tex = (r"\clearpage\chapter*{د انځورونو سرچينې او د کارولو شرطونه}"
               + "\n" + r"\addcontentsline{toc}{chapter}{د انځورونو سرچينې او د کارولو شرطونه}"
               + "\n" + (ROOT / "ps-Arab-PK" / "photocredits" / "INTRO.tex").read_text(encoding="utf-8")
               + "\n" + "\n".join(sections))
    else:
        tex = ""
    return tex, {"photo_ids": photo_ids, "originals_and_localized_credits_complete": True,
                 "component_terms": "Preserved per image; noncommercial permissions are not blanket CC BY 4.0."}, assets


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
    # TeX ignores the source's line break between !! and its article token.
    # Normalize it in the generated reader, preserving the frozen/target files.
    text = re.sub(r"!!\s+(?=[\^a{])", "!!", text)
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


def integrate_accepted_alternates(prepared: list[tuple[dict, str]]) -> tuple[list[tuple[dict, str]], list[dict]]:
    """Place completed legacy alternatives inside their corresponding chapters.

    Later source units include an entire experimental proof-theory part. They
    require their own translated drivers and import order, not a generic tail
    appendix or an assumption that every remaining file is an alternative.
    """
    primary = [(row, body) for row, body in prepared if int(row['unit_id'][-4:]) <= 642]
    additions: dict[str, list[tuple[dict, str]]] = {}
    records = []
    for row, body in prepared:
        if int(row['unit_id'][-4:]) <= 642:
            continue
        if row['unit_id'] not in {'OLP-0643', 'OLP-0644', 'OLP-0645', 'OLP-0646', 'OLP-0647', 'OLP-0648', 'OLP-0649', 'OLP-0650', 'OLP-0651', 'OLP-0652', 'OLP-0653', 'OLP-0654'}:
            raise ValueError(f"{row['unit_id']} requires a source-grounded reader integration mapping")
        parent = Path(row['source_path']).parent
        chapter_rows = [(r, b) for r, b in primary if Path(r['source_path']).parent == parent]
        if not chapter_rows or not any(context(b)[3] == 'chapter' for r, b in chapter_rows):
            raise ValueError(f"missing translated chapter driver for {row['unit_id']}")
        anchor = chapter_rows[-1][0]['unit_id']
        part, chapter, section, role = context(body)
        if row['unit_id'] in {'OLP-0653', 'OLP-0654'}:
            # The frozen model-theory driver places its optional nonstandard
            # arithmetic section after DLO, whose theorem the proof uses.
            # Normal modal logics uses uniform substitution, K and Dual after
            # their schema semantics, before moving to entailment.
            anchor = 'OLP-0190' if row['unit_id'] == 'OLP-0653' else 'OLP-0417'
            expected_context = ('mod', 'bas', 'dlo') if row['unit_id'] == 'OLP-0653' else ('nml', 'syn', 'sch')
            if not any(r['unit_id'] == anchor and Path(r['source_path']).parent == parent and context(b)[:3] == expected_context for r, b in primary):
                raise ValueError('nonstandard arithmetic/modal definitions require their translated source context')
        if row['unit_id'] in {'OLP-0651', 'OLP-0652'}:
            # The legacy conversion stub introduces the complete alpha section.
            # The legacy LK text is an explicitly disclosed classical comparison
            # following the actual many-valued rules, not their replacement.
            anchor = 'OLP-0361' if row['unit_id'] == 'OLP-0651' else 'OLP-0406'
            if not any(r['unit_id'] == anchor and Path(r['source_path']).parent == parent for r, b in primary):
                raise ValueError('legacy conversion/LK comparison requires its translated source context')
        if row['unit_id'] in {'OLP-0649', 'OLP-0650'}:
            # Truth sets extend the existing relational-model semantics. The
            # frozen lambda driver lists lists.tex as an optional import after
            # truth values. Retain both complete sections in those contexts.
            anchor = 'OLP-0500' if row['unit_id'] == 'OLP-0649' else 'OLP-0377'
            if not any(r['unit_id'] == anchor and Path(r['source_path']).parent == parent for r, b in primary):
                raise ValueError('truth-set/list section requires its translated source context')
        if row['unit_id'] in {'OLP-0647', 'OLP-0648'}:
            # Define C before the beta-function/recursion construction; place
            # the complete legacy representability argument after its modern
            # proof, inside the same chapter. Unit IDs follow filename order.
            anchor = 'OLP-0291' if row['unit_id'] == 'OLP-0648' else 'OLP-0297'
            if not any(r['unit_id'] == anchor and context(b)[:2] == ('inc', 'req') for r, b in primary):
                raise ValueError('C definition/proof requires its translated representability chapter')
        if row['unit_id'] in {'OLP-0645', 'OLP-0646'}:
            # The alternate combined outline and its full introduction belong
            # before the preferred separate syntax and semantics exposition.
            anchor = 'OLP-0149'
            if not any(r['unit_id'] == anchor and context(b) == ('fol', 'syn', '', 'chapter') for r, b in primary):
                raise ValueError('combined first-order outline requires its preferred syntax driver')
        if row['unit_id'] == 'OLP-0646':
            original = r'\olchapter{fol}{syn}{نحو او معنٰی پوهنه}'
            if role != 'chapter' or body.count(original) != 1:
                raise ValueError('combined first-order chapter outline changed')
            replacement = r'\paragraph{د سرچينې ګډ باب: نحو او معنٰی پوهنه}'
            body = body.replace(original, replacement)
            body = (r'\olfileid{fol}{syn}{combined-driver-olp0646}' + '\n'
                    + r'\paragraph{د ګډې سرچينې ترتيب}' + '\n'
                    + 'دا ګډ سرليک د لاندې نحو او معنٰی پوهنې دواړو پرلهپسې بابونو سرچينه‌يي ترتيب ښيي؛ اصلي پنځلس واردات په سمون وړ ګډ فايل کښې خوندي دي، او اړوند برخې دلته بې له تکراري بابونو راځي۔\n'
                    + body)
            additions.setdefault(anchor, []).insert(0, (row, body))
            records.append({'unit_id': row['unit_id'], 'source_path': row['source_path'],
                            'placement_after_unit': anchor, 'chapter_directory': parent.as_posix(),
                            'original_context': ['fol', 'syn', ''], 'reader_context': ['fol', 'syn', 'combined-driver-olp0646'],
                            'policy': 'Combined editable chapter driver retains all fifteen imports; reader preserves its complete localized heading and outline role before the corresponding separate syntax/semantics chapters, without opening a duplicate chapter. Header semantic anchors retained; editable bytes unchanged.'})
            continue
        if role != 'section' or not part or not chapter or not section:
            raise ValueError(f"alternate context is incomplete: {row['unit_id']}")
        revised_section = section + '-' + row['unit_id'].lower().replace('-', '')
        original_command = rf"\olfileid{{{part}}}{{{chapter}}}{{{section}}}"
        revised_command = rf"\olfileid{{{part}}}{{{chapter}}}{{{revised_section}}}"
        if body.count(original_command) != 1:
            raise ValueError(f"alternate has ambiguous file identity: {row['unit_id']}")
        before_anchors = re.findall(r'\\(?:phantomsection\\label|label)\{(olpseg:[^{}]+)\}', body)
        body = body.replace(original_command, revised_command)
        # Internal references follow the alternate; other chapters continue to
        # refer to the preferred existing section. Raw fully qualified labels
        # and explicit three-option references also require the local namespace.
        old_prefix, new_prefix = f'{part}:{chapter}:{section}:', f'{part}:{chapter}:{revised_section}:'
        body = body.replace(old_prefix, new_prefix)
        body = body.replace(f'[{part}][{chapter}][{section}]', f'[{part}][{chapter}][{revised_section}]')
        after_anchors = re.findall(r'\\(?:phantomsection\\label|label)\{(olpseg:[^{}]+)\}', body)
        if before_anchors != after_anchors:
            raise ValueError(f"alternate semantic anchors changed: {row['unit_id']}")
        heading = ('د منجمدې سرچينې بشپړه اړونده برخه' if row['unit_id'] in {'OLP-0649', 'OLP-0650', 'OLP-0651', 'OLP-0652', 'OLP-0653', 'OLP-0654'}
                   else 'د منجمدې سرچينې بشپړ بديل متن')
        body = (r'\paragraph{' + heading + r': \LR{' + row['unit_id'] + '}}\n') + body
        if row['unit_id'] == 'OLP-0654':
            # The corrected654 render still left the definition's opening
            # line at the foot of page550 and its clauses on page551.
            # Start the complete, short definition on a fresh page, before
            # its semantic start anchor, so the heading stays with K/Dual.
            definition_start = r'\phantomsection\label{olpseg:OLP-0654-B009:start}'
            if body.count(definition_start) != 1:
                raise ValueError('normal-modal definition start anchor missing')
            body = body.replace(definition_start,
                                '\n' + r'\clearpage' + '\n' + definition_start, 1)
            # Actual654 PDF page550 placed the following entailment diagram
            # between the normal-logic definition and its K/Dual clauses.
            # Finish this page before importing entailment, so its floats
            # cannot move backwards into this complete definition.
            body += '\n' + r'\clearpage' + '\n'
        additions.setdefault(anchor, []).append((row, body))
        records.append({'unit_id': row['unit_id'], 'source_path': row['source_path'],
                        'placement_after_unit': anchor, 'chapter_directory': parent.as_posix(),
                        'original_context': [part, chapter, section],
                        'reader_context': [part, chapter, revised_section],
                        'policy': 'Complete source section inside its corresponding existing physical chapter; legacy scope/incompleteness disclosed where applicable; independent local labels and self references; no duplicate chapter. All semantic anchors retained. Editable source bytes unchanged.'})
    ordered = []
    for row, body in primary:
        ordered.append((row, body))
        ordered.extend(additions.get(row['unit_id'], []))
    if sorted(row['unit_id'] for row, body in ordered) != sorted(row['unit_id'] for row, body in prepared):
        raise ValueError('reader integration changed unit coverage')
    return ordered, records


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


def resolve_tag_references(text: str, unit_id: str, selected_labels: set[str]) -> tuple[str, list[dict]]:
    """Resolve active tag references against actual selected theorem labels.

    The legacy maximal-consistency alternative predates the split of prv and
    ppr. Its logical properties now live at these verified modern destinations.
    Editable source identifiers remain unchanged. Resolving lists here also
    avoids empty cleveref entries from the upstream double-comma accumulator.
    """
    migrated = {
        'provability-land-left': ('provability-land', 1, 'provability-land-left'),
        'provability-land-right': ('provability-land', 2, 'provability-land-right'),
        'provability-lor-left': ('provability-lor', 1, None),
        'provability-lor-right': ('provability-lor', 2, None),
        'provability-mp': ('provability-lif', 1, 'provability-lif-left'),
        'provability-lif': ('provability-lif', 2, 'provability-lif-right'),
    }
    records: list[dict] = []
    pattern = re.compile(r'\\tagrefs\{((?:[^{}]|\{[^{}]*\})*)\}')

    def replace(match: re.Match[str]) -> str:
        targets: list[str] = []
        item_ordinals: set[int] = set()
        for raw in match.group(1).split(','):
            entry = re.fullmatch(r'\s*([A-Za-z][A-Za-z0-9-]*)/\{([^{}]+)\}\s*', raw)
            if not entry:
                raise ValueError(f'malformed tagged reference in {unit_id}: {raw}')
            tag, original = entry.groups()
            if tag not in ACTIVE_TAGS and tag not in INACTIVE_TAGS:
                raise ValueError(f'unknown reference tag in {unit_id}: {tag}')
            if tag not in ACTIVE_TAGS:
                continue
            target = original
            item_label = None
            item_ordinal = None
            legacy = re.fullmatch(r'fol:(seq|ntd):prv:prop:(provability-[a-z-]+)', original)
            if unit_id == 'OLP-0644' and legacy and legacy[2] in migrated:
                theorem, item_ordinal, item = migrated[legacy[2]]
                target = f'fol:{legacy[1]}:ppr:prop:{theorem}'
                item_ordinals.add(item_ordinal)
                if item:
                    item_label = f'fol:{legacy[1]}:ppr:prop:{item}'
                    if item_label not in selected_labels:
                        raise ValueError(f'unresolved theorem item in {unit_id}: {item_label}')
            if target not in selected_labels:
                raise ValueError(f'unresolved active tagged reference in {unit_id}: {original} -> {target}')
            if target not in targets:
                targets.append(target)
            records.append({'unit_id': unit_id, 'tag': tag, 'source_label': original,
                            'reader_label': target, 'legacy_label_migrated': target != original,
                            'reader_item_label': item_label, 'reader_item_ordinal': item_ordinal})
        if not targets:
            raise ValueError(f'empty active tagged reference in {unit_id}')
        if len(item_ordinals) > 1:
            raise ValueError(f'mixed theorem-item destinations in {unit_id}')
        suffix = (' (لومړۍ فقره)' if item_ordinals == {1}
                  else ' (دويمه فقره)' if item_ordinals == {2} else '')
        return r'\cref{' + ','.join(targets) + '}' + suffix

    return pattern.sub(replace, text), records


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
    if row["unit_id"] == "OLP-0061":
        # This one translated sentence puts its Pashto full stop in outer
        # display math. Move the same punctuation into the existing text
        # argument so the reader uses its Pashto font, not cmr10.
        old = r"\text{که $\pValue{v}(!A) = \False $ وي}۔"
        new = r"\text{که $\pValue{v}(!A) = \False $ وي۔}"
        if body.count(old) != 1:
            raise ValueError("OLP-0061 math-text punctuation recovery site changed")
        body = body.replace(old, new)
    if row["unit_id"] == "OLP-0426":
        # The frozen source closes the indcase argument before its math
        # delimiter in the iff case. Repair only that grouping in the reader;
        # all formula tokens and both editable witnesses remain unchanged.
        old = r"\liff \ST_x(!C))}$.}{}"
        new = r"\liff \ST_x(!C))$.}}{}"
        if body.count(old) != 1:
            raise ValueError("OLP-0426 source-syntax recovery site changed")
        body = body.replace(old, new)
    body = remove_imports(body)
    body, assets = rewrite_assets(body, row["source_path"])
    body = wrap_rtl_math_text(expand_tokens(body))
    body, profile_stats = resolve_profile_conditionals(body)
    if row["unit_id"] in {"OLP-0471", "OLP-0472"}:
        # Removing inactive proof-rule branches leaves paragraph breaks inside
        # display math. TeX interprets those as \par and aborts. Whitespace
        # recovery only; require the exact known count and retain every symbol.
        expected = {"OLP-0471": 1, "OLP-0472": 5}[row["unit_id"]]
        recovered = 0

        def recover_display(match: re.Match[str]) -> str:
            nonlocal recovered
            result, count = re.subn(r"\n(?:[ \t]*\n)+", "\n", match[0])
            recovered += count
            return result

        body = re.sub(r"(?s)(?<!\\)\\\[.*?(?<!\\)\\\]", recover_display, body)
        if recovered != expected:
            raise ValueError(f"{row['unit_id']} display paragraph recovery sites changed: {recovered}")
        profile_stats["modal_display_paragraph_break_recoveries"] += recovered
    if row["unit_id"] in {"OLP-0634", "OLP-0636", "OLP-0637"}:
        # Exact retained quotations need their own reading direction inside
        # Pashto prose. Keep the original words and punctuation intact.
        pattern = (r"\\emph\{(in rebus mathematicis errores qu\\`\{a\}m minimi\s+non sunt contemnendi)\}"
                   if row["unit_id"] == "OLP-0634" else
                   r"\\emph\{(je le vois, mais je ne le crois\s+pas\.?)\}")
        expected = {"OLP-0634": 1, "OLP-0636": 1, "OLP-0637": 2}[row["unit_id"]]
        body, count = re.subn(pattern, lambda m: r"\emph{\LR{\latinfont " + m[1] + "}}", body)
        if count != expected:
            raise ValueError(f"{row['unit_id']} retained Latin quotation sites changed: {count}")
        profile_stats["retained_latin_quote_direction_recoveries"] += count
    if row["unit_id"] in {"OLP-0479", "OLP-0487"}:
        # Include tabular padding and rule widths in the two observed wide
        # correspondence tables; content and mathematical tokens stay exact.
        old = r"p{.48\textwidth}"
        new = r"p{\dimexpr .5\linewidth-2\tabcolsep-2\arrayrulewidth\relax}"
        if body.count(old) != 2:
            raise ValueError(f"{row['unit_id']} correspondence table columns changed")
        body = body.replace(old, new)
        profile_stats["correspondence_table_column_recoveries"] += 2
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
    if not 1 <= args.through_unit <= 722:
        raise ValueError("cumulative reader boundary must be between OLP-0001 and OLP-0722")
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

    prepared, alternate_integration = integrate_accepted_alternates(prepared)
    selected_labels: set[str] = set()
    for _row, body in prepared:
        overlap = selected_labels & label_keys(body)
        if overlap:
            raise ValueError(f"duplicate selected labels: {sorted(overlap)[:8]}")
        selected_labels.update(label_keys(body))
    upstream_labels = upstream_label_index(rows)

    rendered: list[str] = []
    external_counts: Counter = Counter()
    tagged_reference_bindings: list[dict] = []
    for row, body in prepared:
        body, label_stats = resolve_label_conditionals(body, selected_labels)
        profile_stats.update(label_stats)
        body, tag_bindings = resolve_tag_references(body, row['unit_id'], selected_labels)
        tagged_reference_bindings.extend(tag_bindings)
        body, counts = render_external_references(
            body, selected_labels=selected_labels, upstream_labels=upstream_labels
        )
        rendered.append(body)
        external_counts.update(counts)

    preamble = args.preamble.resolve()
    if not preamble.is_file() or not preamble.is_relative_to(ROOT):
        raise ValueError("reader preamble must be a file inside this repository")
    rendered_body = "\n\n".join(rendered)
    bibliography_tex, bibliography_record = bibliography_inputs(rendered_body, build_dir)
    photo_tex, photo_record, photo_assets = photo_inputs(rendered_body)
    asset_paths.update(photo_assets)
    generated = (
        preamble.read_text(encoding="utf-8")
        .replace("OLP_UPSTREAM_PATH", (ROOT / "upstream").as_posix())
        .replace("OLP_READER_UNITS_PS", str(len(selected)).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")))
        .replace("OLP_READER_UNITS", str(len(selected)))
        .replace("OLP_ASSETS_PATH", (ROOT / "assets").as_posix())
        + "\n\n"
        + rendered_body
        + "\n\n"
        + bibliography_tex
        + "\n\n" + photo_tex
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
        "alternate_integration": alternate_integration,
        "tagged_reference_bindings": tagged_reference_bindings,
        "reader_unit_order": [row['unit_id'] for row, body in prepared],
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
                "unit_ids": ["OLP-0634", "OLP-0636", "OLP-0637"],
                "finding": "Four retained Latin/French quotations inherit RTL word order in Pashto prose.",
                "reader_recovery": "Isolate only the four exact original quotations as LTR Latin text. Words and punctuation unchanged.",
                "source_bytes_changed": False,
                "target_bytes_changed": False,
            },
            {
                "unit_ids": ["OLP-0479", "OLP-0487"],
                "finding": "Two correspondence tables omit padding/rules in their column width allocation.",
                "reader_recovery": "Account for tabular padding and rules in all four column widths; preserve every cell and formula.",
                "source_bytes_changed": False,
                "target_bytes_changed": False,
            },
            {
                "unit_ids": ["OLP-0471", "OLP-0472"],
                "source_paths": ["content/normal-modal-logic/sequent-calculus/introduction.tex",
                                 "content/normal-modal-logic/sequent-calculus/rules-for-K.tex"],
                "finding": "Resolved inactive proof-rule branches leave six paragraph breaks inside four display-math blocks, causing Missing $ inserted.",
                "reader_recovery": "Remove only these six known generated paragraph breaks; exact count required. All formula tokens and proof-rule order retained.",
                "source_bytes_changed": False,
                "target_bytes_changed": False,
            },
            {
                "unit_id": "OLP-0061",
                "source_path": "content/propositional-logic/syntax-and-semantics/valuations-sat.tex",
                "finding": "One translated Pashto full stop after the final ternary-connective branch sits in outer display math and generates cmr10 missing-glyph warnings.",
                "reader_recovery": "Retain that punctuation inside its existing Pashto text argument; symbolic formula tokens are unchanged.",
                "source_bytes_changed": False,
                "target_bytes_changed": False,
            },
            {
                "unit_id": "OLP-0426",
                "source_path": "content/normal-modal-logic/frame-definability/second-order-definability.tex",
                "finding": "The frozen source and translated witness close the indcase argument before the math delimiter in the standard-translation iff case.",
                "reader_recovery": "Close math before both macro arguments. All symbolic formula tokens remain in their original order.",
                "source_bytes_changed": False,
                "target_bytes_changed": False,
            },
            {
                "unit_id": "OLP-0447",
                "source_path": "content/normal-modal-logic/completeness/truth-lemma.tex",
                "finding": "The optional exercise tag list uses undeclared probFalse/probTrue and lowercase proband; the frozen default config makes the other prob tags false while all primitive proof cases are active.",
                "reader_recovery": "Resolve these three optional-exercise tags as inactive in this explicit default-profile reader. No proof case or translated source file is changed; the complete exercise remains in the editable source.",
                "source_bytes_changed": False,
                "target_bytes_changed": False,
            },
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
        "bibliography": bibliography_record,
        "portraits": photo_record,
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
