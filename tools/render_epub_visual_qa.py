#!/usr/bin/env python3
"""Render representative EPUB XHTML views for visual quality assurance."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


CASES = (
    ("title", "title.xhtml", "body", 0),
    ("navigation", "nav.xhtml", "nav", 0),
    ("sets-diagram", "chapter-01.xhtml", ".figure", 0),
    ("relations-diagram", "chapter-02.xhtml", ".figure", 0),
    ("function-diagram", "chapter-03.xhtml", ".figure", 0),
    ("proof-system-overview", "chapter-08.xhtml", ".proof-tree", 0),
    ("sequent-calculus-rules", "chapter-09.xhtml", ".proof-rules", 3),
    ("sequent-proof-tree", "chapter-09.xhtml", ".proof-tree", 20),
    ("natural-deduction", "chapter-10.xhtml", ".proof-tree", 25),
    ("tableau", "chapter-11.xhtml", ".tableau", 10),
    ("axiomatic-derivation", "chapter-12.xhtml", ".derivation", 2),
    ("completeness", "chapter-13.xhtml", ".semantic.thm", 0),
    ("syntax-table", "chapter-15.xhtml", ".data-table", 0),
    ("first-order-semantics", "chapter-16.xhtml", ".semantic.defn", 4),
    ("model-theory", "chapter-19.xhtml", ".semantic.thm", 2),
    ("interpolation-diagram", "chapter-21.xhtml", ".figure", 0),
    ("lindstrom-diagram", "chapter-22.xhtml", ".figure", 0),
    ("recursive-functions", "chapter-23.xhtml", ".semantic.defn", 1),
    ("computability-history", "chapter-24.xhtml", ".history", 0),
    ("turing-tape", "chapter-25.xhtml", ".figure", 0),
    ("turing-state-machine", "chapter-25.xhtml", ".figure", 4),
)

VIEWPORTS = (
    ("wide", 1440, 1100),
    ("reader", 768, 1024),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--browser", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=str(args.browser),
            headless=True,
        )
        browser_version = browser.version
        for viewport_name, viewport_width, viewport_height in VIEWPORTS:
            context = browser.new_context(
                viewport={"width": viewport_width, "height": viewport_height},
                device_scale_factor=1,
            )
            context.route(
                "**/favicon.ico",
                lambda route: route.fulfill(status=204, content_type="image/x-icon"),
            )
            for name, document, selector, index in CASES:
                page = context.new_page()
                console_errors: list[str] = []
                page_errors: list[str] = []
                page.on(
                    "console",
                    lambda message: console_errors.append(message.text)
                    if message.type == "error"
                    else None,
                )
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                url = f"{args.base_url.rstrip('/')}/{document}"
                page.goto(url, wait_until="networkidle")
                page.evaluate("document.fonts.ready")
                page.wait_for_function(
                    "Array.from(document.images).every((image) => image.complete)"
                )
                target = page.locator(selector).nth(index)
                target.wait_for(state="visible")
                target.scroll_into_view_if_needed()
                page.wait_for_timeout(250)

                box = target.bounding_box()
                if box is None:
                    raise RuntimeError(f"No visible box for {selector} in {document}")
                document_height = page.evaluate("document.documentElement.scrollHeight")
                document_width = page.evaluate("document.documentElement.scrollWidth")
                viewport_client_width = page.evaluate(
                    "document.documentElement.clientWidth"
                )
                image_count = page.locator("img").count()
                broken_image_count = page.evaluate(
                    "Array.from(document.images).filter((image) => "
                    "image.complete && image.naturalWidth === 0).length"
                )
                mathml_count = page.locator("math").count()
                top = max(0, box["y"] - 180)
                height = min(viewport_height, document_height - top)
                output = args.output_dir / f"{viewport_name}-{name}.png"
                image_bytes = page.screenshot(
                    path=str(output),
                    clip={
                        "x": 0,
                        "y": top,
                        "width": viewport_width,
                        "height": height,
                    },
                )

                records.append(
                    {
                        "name": name,
                        "viewport": {
                            "name": viewport_name,
                            "width": viewport_width,
                            "height": viewport_height,
                            "device_scale_factor": 1,
                        },
                        "url": url,
                        "selector": selector,
                        "selector_index": index,
                        "document_title": page.title(),
                        "html_lang": page.locator("html").get_attribute("lang"),
                        "html_dir": page.locator("html").get_attribute("dir"),
                        "computed_body_direction": page.locator("body").evaluate(
                            "element => getComputedStyle(element).direction"
                        ),
                        "document_width": document_width,
                        "viewport_client_width": viewport_client_width,
                        "horizontal_overflow": document_width > viewport_client_width,
                        "image_count": image_count,
                        "broken_image_count": broken_image_count,
                        "mathml_count": mathml_count,
                        "target_box": box,
                        "console_errors": console_errors,
                        "page_errors": page_errors,
                        "screenshot": str(output),
                        "screenshot_bytes": len(image_bytes),
                        "screenshot_sha256": hashlib.sha256(image_bytes).hexdigest(),
                    }
                )
                page.close()
            context.close()

        browser.close()

    receipt = {
        "schema": "openlogic-ps-Arab-PK-epub-visual-qa/2",
        "browser": {"executable": str(args.browser), "version": browser_version},
        "cases": records,
    }
    receipt_path = args.output_dir / "visual-qa.json"
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(receipt_path)


if __name__ == "__main__":
    main()
