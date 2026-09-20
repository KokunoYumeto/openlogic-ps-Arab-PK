#!/usr/bin/env python3
"""Prepare guarded XeLaTeX inputs and deterministically render EPUB SVG figures."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_FIGURES = 20
SVG_NS = "http://www.w3.org/2000/svg"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def semantic_inventory_sha256(figures: list[dict]) -> str:
    payload = json.dumps(
        figures,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_inventory(path: Path) -> list[dict]:
    figures = json.loads(path.read_text(encoding="utf-8"))
    if len(figures) != EXPECTED_FIGURES:
        raise ValueError(
            f"expected {EXPECTED_FIGURES} figures, found {len(figures)}"
        )
    expected_ids = [
        f"figure-{number:03d}"
        for number in range(1, EXPECTED_FIGURES + 1)
    ]
    if [figure["id"] for figure in figures] != expected_ids:
        raise ValueError("figure IDs are not complete and ordered")
    for figure in figures:
        if figure["source_kind"] not in {"olasset", "inline_tikz"}:
            raise ValueError(f"unknown figure source kind: {figure}")
        if not figure["tex_body"].strip():
            raise ValueError(f"empty TeX body for {figure['id']}")
    return figures


def document(body: str) -> str:
    upstream = (ROOT / "upstream").as_posix()
    return rf"""\documentclass[tikz,border=3pt]{{standalone}}
\usepackage{{fontspec}}
\setmainfont[Script=Arabic]{{Amiri}}
\newfontfamily\latinfont{{Latin Modern Roman}}
\usepackage{{amsmath,amssymb,amsfonts,mathrsfs,mathtools,nicefrac,stmaryrd}}
\usepackage{{xparse,etoolbox,xpunctuate,mfirstuc}}
\usepackage{{graphicx,tikz,xcolor}}
\usetikzlibrary{{arrows,automata,positioning,calc,decorations.pathmorphing}}
\usepackage{{bidi}}
\newcommand*{{\DeclareDocumentMacro}}[2]{{\def#1{{#2}}}}
\NewDocumentCommand{{\settexttoken}}{{m s m m o o}}{{}}
\makeatletter
\input{{{upstream}/sty/open-logic-formulas.sty}}
\input{{{upstream}/sty/open-logic-selective.sty}}
\input{{{upstream}/open-logic-config.sty}}
\makeatother
\begin{{document}}
\begin{{LTR}}
{body}
\end{{LTR}}
\end{{document}}
"""


def prepare(inventory_path: Path, build_dir: Path) -> None:
    figures = load_inventory(inventory_path)
    build_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    for figure in figures:
        base = figure["id"]
        tex_path = build_dir / f"{base}.tex"
        tex_path.write_text(
            document(figure["tex_body"]),
            encoding="utf-8",
            newline="\n",
        )
        record = {
            "id": base,
            "unit_id": figure["unit_id"],
            "source_kind": figure["source_kind"],
            "source_path": figure["source_path"],
            "tex": {
                "path": str(tex_path),
                "bytes": tex_path.stat().st_size,
                "sha256": sha256(tex_path),
            },
        }
        if figure["source_path"]:
            source_path = Path(figure["source_path"]).resolve()
            source_path.relative_to(ROOT)
            record["source_asset"] = {
                "path": source_path.relative_to(ROOT).as_posix(),
                "bytes": source_path.stat().st_size,
                "sha256": sha256(source_path),
            }
        records.append(record)
    record_path = build_dir / "figure-inputs.json"
    record_path.write_text(
        json.dumps(
            {
                "schema": "openlogic-ps-Arab-PK-cumulative-epub-figure-inputs/1",
                "status": "prepared_for_guarded_tex",
                "inventory": {
                    "path": str(inventory_path.resolve()),
                    "bytes": inventory_path.stat().st_size,
                    "sha256": sha256(inventory_path),
                },
                "figure_count": len(records),
                "document_bases": [record["id"] for record in records],
                "figures": records,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "prepared_for_guarded_tex",
                "figure_count": len(records),
                "build_dir": str(build_dir),
                "input_record": str(record_path),
            }
        )
    )


def convert(inventory_path: Path, build_dir: Path, output_dir: Path) -> None:
    figures = load_inventory(inventory_path)
    inputs_path = build_dir / "figure-inputs.json"
    inputs = json.loads(inputs_path.read_text(encoding="utf-8"))
    if (
        inputs.get("schema")
        != "openlogic-ps-Arab-PK-cumulative-epub-figure-inputs/1"
        or inputs.get("status") != "prepared_for_guarded_tex"
        or inputs.get("inventory", {}).get("sha256")
        != sha256(inventory_path)
        or inputs.get("figure_count") != len(figures)
    ):
        raise ValueError("prepared figure inputs differ from the inventory")
    receipt_path = build_dir / "TEX_RECEIPT.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8-sig"))
    if not receipt.get("acquired") or receipt.get("status") != "processes-completed":
        raise ValueError("guarded TeX receipt is not successful")
    bases = [figure["id"] for figure in figures]
    passes = receipt.get("passes", [])
    if [item.get("document") for item in passes] != bases:
        raise ValueError("guarded TeX receipt does not cover the exact figure set")
    if any(item.get("exit_code") != 0 for item in passes):
        raise ValueError("a guarded TeX figure pass failed")

    pdftocairo = shutil.which("pdftocairo")
    if not pdftocairo:
        raise FileNotFoundError("pdftocairo is required")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    replay_dir = output_dir.with_name(output_dir.name + "-replay")
    if replay_dir.exists():
        shutil.rmtree(replay_dir)
    output_dir.mkdir(parents=True)
    replay_dir.mkdir(parents=True)
    environment = {
        **os.environ,
        "SOURCE_DATE_EPOCH": "1788480000",
        "FORCE_SOURCE_DATE": "1",
    }

    records: list[dict] = []
    for figure in figures:
        base = figure["id"]
        pdf = build_dir / f"{base}.pdf"
        if not pdf.is_file():
            raise FileNotFoundError(pdf)
        outputs = [
            output_dir / f"{base}.svg",
            replay_dir / f"{base}.svg",
        ]
        diagnostics: list[str] = []
        for output in outputs:
            command = [
                pdftocairo,
                "-svg",
                str(pdf),
                str(output),
            ]
            result = subprocess.run(
                command,
                cwd=build_dir,
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="strict",
                check=False,
            )
            diagnostics.append(result.stdout + result.stderr)
            if result.returncode:
                raise RuntimeError(
                    f"pdftocairo failed for {base}: {diagnostics[-1]}"
                )
        if outputs[0].read_bytes() != outputs[1].read_bytes():
            raise ValueError(f"non-deterministic SVG replay for {base}")
        root = ET.fromstring(outputs[0].read_bytes())
        if root.tag != f"{{{SVG_NS}}}svg":
            raise ValueError(f"invalid SVG root for {base}")
        if not root.attrib.get("viewBox"):
            raise ValueError(f"SVG lacks viewBox for {base}")
        for element in root.iter():
            for value in element.attrib.values():
                if "file:" in value or str(ROOT) in value:
                    raise ValueError(f"SVG leaks a local path for {base}")
        records.append(
            {
                "id": base,
                "unit_id": figure["unit_id"],
                "source_kind": figure["source_kind"],
                "pdf": {
                    "bytes": pdf.stat().st_size,
                    "sha256": sha256(pdf),
                },
                "svg": {
                    "path": str(outputs[0]),
                    "bytes": outputs[0].stat().st_size,
                    "sha256": sha256(outputs[0]),
                    "viewBox": root.attrib["viewBox"],
                },
                "deterministic_replay": True,
                "converter_diagnostics": diagnostics[0].strip().splitlines(),
            }
        )
    record_path = output_dir / "figure-render.json"
    record_path.write_text(
        json.dumps(
            {
                "schema": "openlogic-ps-Arab-PK-cumulative-epub-figure-render/1",
                "status": "accepted",
                "figure_count": len(records),
                "inventory": {
                    "path": str(inventory_path),
                    "bytes": inventory_path.stat().st_size,
                    "sha256": sha256(inventory_path),
                    "semantic_sha256": semantic_inventory_sha256(figures),
                },
                "figure_inputs": {
                    "path": str(inputs_path),
                    "sha256": sha256(inputs_path),
                },
                "guarded_tex_receipt": {
                    "path": str(receipt_path),
                    "sha256": sha256(receipt_path),
                },
                "pdftocairo": (
                    lambda result: (result.stdout + result.stderr)
                    .strip()
                    .splitlines()[0]
                )(
                    subprocess.run(
                    [pdftocairo, "-v"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    check=True,
                    )
                ),
                "figures": records,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "accepted",
                "figure_count": len(records),
                "output_dir": str(output_dir),
                "render_record": str(record_path),
            }
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--phase", choices=("prepare", "convert"), required=True
    )
    args = parser.parse_args()
    if args.phase == "prepare":
        prepare(args.inventory.resolve(), args.build_dir.resolve())
    else:
        if args.output_dir is None:
            parser.error("--output-dir is required for --phase convert")
        convert(
            args.inventory.resolve(),
            args.build_dir.resolve(),
            args.output_dir.resolve(),
        )


if __name__ == "__main__":
    main()
