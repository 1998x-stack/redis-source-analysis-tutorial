#!/usr/bin/env python3
"""Visual and interaction QA for the static Redis tutorial; requires Playwright."""
from __future__ import annotations
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUT = ROOT / "qa" / "browser"
URLS = [DOCS / "index.html"] + [DOCS / "chapters" / f"{i:02d}.html" for i in range(1, 29)]
VIEWPORTS = (360, 390, 1440)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for file in URLS:
            for width in VIEWPORTS:
                page = browser.new_page(
                    viewport={"width": width, "height": 900},
                    device_scale_factor=1,
                )
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
                page.goto(file.resolve().as_uri(), wait_until="load")
                page.wait_for_timeout(250)
                page.evaluate("""async () => {
                    const images = Array.from(document.images);
                    images.forEach(img => { img.loading = 'eager'; });
                    await Promise.all(images.map(img => img.decode().catch(() => null)));
                }""")
                page.evaluate("window.scrollTo(0,0)")
                state = page.evaluate("""() => {
                    const ids = [...document.querySelectorAll('[id]')].map(node => node.id);
                    const duplicates = [...new Set(ids.filter((id, index) => ids.indexOf(id) !== index))];
                    const brokenAnchors = [...document.querySelectorAll('a[href^="#"]')]
                        .filter(anchor => !document.getElementById(decodeURIComponent(anchor.hash.slice(1))))
                        .map(anchor => anchor.getAttribute('href'));
                    return {
                        width: innerWidth,
                        scrollWidth: document.documentElement.scrollWidth,
                        h1: document.querySelectorAll('h1').length,
                        brokenImages: [...document.images].filter(img => !img.complete || img.naturalWidth === 0).map(img => img.src),
                        chapterCards: document.querySelectorAll('.chapter-card').length,
                        duplicateIds: duplicates,
                        brokenAnchors
                    };
                }""")
                label = file.stem if file.name != "index.html" else "home"
                page.screenshot(path=str(OUT / f"{label}-{width}.png"), full_page=True)
                if state["scrollWidth"] > state["width"]:
                    errors.append("horizontal viewport overflow")
                if state["h1"] != 1:
                    errors.append("expected one h1")
                if state["brokenImages"]:
                    errors.append("broken images: " + str(state["brokenImages"]))
                if state["duplicateIds"]:
                    errors.append("duplicate ids: " + str(state["duplicateIds"]))
                if state["brokenAnchors"]:
                    errors.append("broken in-page anchors: " + str(state["brokenAnchors"]))

                if label == "home":
                    if state["chapterCards"] != 28:
                        errors.append("homepage does not contain 28 chapters")
                    page.locator("[data-filter='rewritten']").click()
                    if page.locator(".chapter-card:visible").count() != 28:
                        errors.append("rewritten filter does not show all 28 chapters")

                if label == "04":
                    page.locator("#sim-sds").evaluate(
                        "(el) => { el.value = '23'; el.dispatchEvent(new Event('input',{bubbles:true})); }"
                    )
                    if "23" not in page.locator("[data-output]").inner_text():
                        errors.append("SDS interactive demo did not update")

                if label in ("06", "07", "08", "09", "10"):
                    demo = page.locator("[data-deep-demo] select")
                    if demo.count() != 1:
                        errors.append("expected one active new-article demo")
                    else:
                        before = page.locator("[data-deep-demo] [data-output]").inner_text()
                        if demo.locator("option").count() >= 2:
                            demo.select_option(index=1)
                            after = page.locator("[data-deep-demo] [data-output]").inner_text()
                            if before == after or not after.strip():
                                errors.append("new demo did not update")

                if label in ("11", "12", "13", "14", "15"):
                    demos = page.locator("[data-third-demo]")
                    if demos.count() < 1:
                        errors.append("missing third-batch interactive explanation")
                    for i in range(demos.count()):
                        demo = demos.nth(i)
                        select = demo.locator("select")
                        output = demo.locator("[data-output]")
                        if select.count() != 1 or output.count() != 1:
                            errors.append("invalid third-batch interactive markup")
                            continue
                        before = output.inner_text()
                        if select.locator("option").count() >= 2:
                            select.select_option(index=1)
                            after = output.inner_text()
                            if not before.strip() or after == before or not after.strip():
                                errors.append("third-batch interactive explanation did not update")

                if label in ("16", "17", "18", "19", "20"):
                    demos = page.locator("[data-fourth-demo]")
                    if demos.count() != 1:
                        errors.append("expected one fourth-batch interactive explanation")
                    else:
                        select = demos.locator("select")
                        output = demos.locator("[data-output]")
                        if select.count() != 1 or output.count() != 1:
                            errors.append("invalid fourth-batch interactive markup")
                        else:
                            before = output.inner_text()
                            if select.locator("option").count() >= 2:
                                select.select_option(index=1)
                                after = output.inner_text()
                                if not before.strip() or after == before or not after.strip():
                                    errors.append("fourth-batch interactive explanation did not update")

                if label in ("21", "22", "23", "24", "25"):
                    demos = page.locator("[data-fifth-demo]")
                    if demos.count() != 1:
                        errors.append("expected one fifth-batch interactive explanation")
                    else:
                        select = demos.locator("select")
                        output = demos.locator("[data-output]")
                        if select.count() != 1 or output.count() != 1:
                            errors.append("invalid fifth-batch interactive markup")
                        else:
                            before = output.inner_text()
                            if select.locator("option").count() >= 2:
                                select.select_option(index=1)
                                after = output.inner_text()
                                if not before.strip() or after == before or not after.strip():
                                    errors.append("fifth-batch interactive explanation did not update")
                    if page.locator("figure.diagram-pan img").count() != 3:
                        errors.append("expected 3 fifth-batch mechanism diagrams")
                    if page.locator(".article-aside .toc-links a").count() < 8:
                        errors.append("fifth-batch TOC too sparse")

                if label in ("26", "27", "28"):
                    expected = {"26": 2, "27": 1, "28": 2}[label]
                    demos = page.locator("[data-final-demo]")
                    if demos.count() != expected:
                        errors.append(f"expected {expected} final-batch interactive models; got {demos.count()}")
                    for i in range(demos.count()):
                        demo = demos.nth(i)
                        select = demo.locator("select")
                        output = demo.locator("[data-output]")
                        if select.count() != 1 or output.count() != 1:
                            errors.append("invalid final-batch interactive markup")
                            continue
                        before = output.inner_text()
                        if select.locator("option").count() >= 2:
                            select.select_option(index=1)
                            after = output.inner_text()
                            if not before.strip() or after == before or not after.strip():
                                errors.append("final-batch interactive explanation did not update")
                    if page.locator("figure.diagram-pan img").count() != 3:
                        errors.append("expected 3 final-batch mechanism diagrams")
                    if page.locator(".article-aside .toc-links a").count() < 8:
                        errors.append("final-batch TOC too sparse")

                results.append({
                    "page": label,
                    "width": width,
                    "status": "pass" if not errors else "fail",
                    "errors": errors,
                })
                page.close()
        browser.close()

    (OUT / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    for item in results:
        print(f"{item['page']} {item['width']}: {item['status']} {item['errors']}")
    if any(item["status"] != "pass" for item in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
