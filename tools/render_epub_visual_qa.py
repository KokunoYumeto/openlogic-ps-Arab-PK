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
    ("proof-tree", "chapter-03.xhtml", ".proof-tree", 0),
    ("existential-rule", "chapter-04.xhtml", ".proof-rules", 6),
    ("tableau", "chapter-05.xhtml", ".tableau", 0),
    ("completeness", "chapter-07.xhtml", "main", 0),
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
                target = page.locator(selector).nth(index)
                target.wait_for(state="visible")
                target.scroll_into_view_if_needed()
                page.wait_for_timeout(250)

                box = target.bounding_box()
                if box is None:
                    raise RuntimeError(f"No visible box for {selector} in {document}")
                document_height = page.evaluate("document.documentElement.scrollHeight")
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
                        "horizontal_overflow": page.evaluate(
                            "document.documentElement.scrollWidth > document.documentElement.clientWidth"
                        ),
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
        "schema": "openlogic-ps-Arab-PK-epub-visual-qa/1",
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
