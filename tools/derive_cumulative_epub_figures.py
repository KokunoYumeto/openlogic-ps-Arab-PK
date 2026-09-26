#!/usr/bin/env python3
"""Derive the v0.7 figure inventory from the tagged editable sources."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import build_cumulative_epub as epub
import build_cumulative_reader as reader


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--reference-map", type=Path,
        default=Path(__file__).resolve().parents[1] / "evidence" / "V070_EPUB_REFERENCE_MAP.json",
    )
    args = parser.parse_args()

    reader.EXPECTED_IDS = [f"OLP-{number:04d}" for number in range(1, 322)]
    epub.THROUGH_UNIT = 321
    epub.CHAPTER_COUNT = 31
    units, _provenance = epub.load_units()

    reference_record = json.loads(args.reference_map.read_text(encoding="utf-8"))
    if reference_record["status"] != "accepted_pdf_numbering_replayed" or reference_record["reference_count"] != 785:
        raise ValueError("v0.7 reference map is not the accepted 785-key map")
    references = reference_record["references"]
    targets = epub.build_reference_targets(units, references)
    state = epub.TransformState(
        tokens=epub.TokenRegistry(),
        reference_map=references,
        reference_targets=targets,
    )
    for unit in units:
        epub.transform_unit(unit, state)
    if (state.stats["segment_start_anchors"], state.stats["segment_end_anchors"], len(state.figures)) != (3414, 3414, 31):
        raise ValueError("v0.7 segment or figure inventory differs from the accepted scope")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(state.figures, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"units": len(units), "segments": 3414, "figures": 31, "output": str(args.output.resolve())}))


if __name__ == "__main__":
    main()
