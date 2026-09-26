#!/usr/bin/env python3
"""Replay accepted cumulative PDF labels into the EPUB reference map."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import build_cumulative_epub as epub
import build_cumulative_reader as reader


EXPECTED_REFERENCES = 587


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_group(text: str, index: int) -> tuple[str, int]:
    if index >= len(text) or text[index] != "{":
        raise ValueError(f"expected group at offset {index}")
    depth = 1
    cursor = index + 1
    while cursor < len(text):
        character = text[cursor]
        if character == "\\" and cursor + 1 < len(text):
            if text[cursor + 1] in "{}":
                cursor += 2
                continue
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return text[index + 1 : cursor], cursor + 1
        cursor += 1
    raise ValueError(f"unclosed group at offset {index}")


def parse_aux(path: Path) -> dict[str, dict]:
    text = path.read_text(encoding="utf-8")
    marker = r"\newlabel"
    labels: dict[str, dict] = {}
    cursor = 0
    while True:
        start = text.find(marker, cursor)
        if start < 0:
            break
        index = start + len(marker)
        key, index = read_group(text, index)
        payload, cursor = read_group(text, index)
        if key.endswith("@cref"):
            continue
        values: list[str] = []
        value_cursor = 0
        while value_cursor < len(payload):
            while (
                value_cursor < len(payload)
                and payload[value_cursor].isspace()
            ):
                value_cursor += 1
            if value_cursor == len(payload):
                break
            value, value_cursor = read_group(payload, value_cursor)
            values.append(value)
        if len(values) < 4:
            raise ValueError(f"malformed newlabel payload for {key}")
        if key in labels:
            raise ValueError(f"duplicate newlabel in AUX: {key}")
        labels[key] = {
            "number": values[0],
            "page": values[1],
            "title_tex": values[2],
            "target": values[3],
        }
    return labels


def expected_keys() -> set[str]:
    units, _ = epub.load_units()
    keys: set[str] = set()
    for unit in units:
        # TeX comments may contain draft labels. They do not enter the PDF
        # AUX and must not become EPUB destinations.
        unit_keys = reader.label_keys(epub.strip_comments(unit.text))
        overlap = keys & unit_keys
        if overlap:
            raise ValueError(f"duplicate content labels: {sorted(overlap)[:8]}")
        keys.update(unit_keys)
    if len(keys) != EXPECTED_REFERENCES:
        raise ValueError(
            f"expected {EXPECTED_REFERENCES} content labels, found {len(keys)}"
        )
    return keys


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--through-unit", type=int, choices=(255, 321), default=255)
    parser.add_argument("--primary-aux", type=Path, required=True)
    parser.add_argument("--replay-aux", type=Path, required=True)
    parser.add_argument("--primary-pdf", type=Path, required=True)
    parser.add_argument("--replay-pdf", type=Path, required=True)
    parser.add_argument("--pdf-record-path", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    global EXPECTED_REFERENCES
    if args.through_unit == 321:
        EXPECTED_REFERENCES = 785
        reader.EXPECTED_IDS = [f"OLP-{number:04d}" for number in range(1, 322)]
        epub.THROUGH_UNIT = 321
        epub.CHAPTER_COUNT = 31

    primary_aux = args.primary_aux.resolve()
    replay_aux = args.replay_aux.resolve()
    primary_pdf = args.primary_pdf.resolve()
    replay_pdf = args.replay_pdf.resolve()
    if primary_aux.read_bytes() != replay_aux.read_bytes():
        raise ValueError("primary and replay AUX files differ")
    if primary_pdf.read_bytes() != replay_pdf.read_bytes():
        raise ValueError("primary and replay PDF files differ")

    expected = expected_keys()
    primary_labels = parse_aux(primary_aux)
    replay_labels = parse_aux(replay_aux)
    if primary_labels != replay_labels:
        raise ValueError("primary and replay parsed labels differ")
    missing = sorted(expected - set(primary_labels))
    if missing:
        raise ValueError(f"accepted AUX lacks content labels: {missing[:8]}")
    references: dict[str, dict] = {}
    for key in sorted(expected):
        label = primary_labels[key]
        if not label["number"] or not label["target"]:
            raise ValueError(f"label lacks number or target: {key}")
        references[key] = {
            "number": label["number"],
            "title_tex": label["title_tex"],
            "target": label["target"],
        }

    record = {
        "schema": "openlogic-ps-Arab-PK-epub-reference-map/1",
        "status": "accepted_pdf_numbering_replayed",
        "scope": {
            "first_unit": "OLP-0001",
            "last_unit": f"OLP-{args.through_unit:04d}",
            "unit_count": args.through_unit,
        },
        "accepted_pdf": {
            "path": args.pdf_record_path,
            "bytes": primary_pdf.stat().st_size,
            "sha256": sha256(primary_pdf),
        },
        "accepted_aux": {"sha256": sha256(primary_aux)},
        "independent_replay_aux": {"sha256": sha256(replay_aux)},
        "reference_count": len(references),
        "references": references,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": record["status"],
                "references": len(references),
                "pdf_sha256": record["accepted_pdf"]["sha256"],
                "output": str(args.output.resolve()),
            }
        )
    )


if __name__ == "__main__":
    main()
