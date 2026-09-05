#!/usr/bin/env python3
"""Bounded Chromium baseline; assertion failures are evidence, not exit failures.

Run with LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libstdc++.so.6 .venv/bin/python
scripts/phase0_browser.py --root /tmp/opencode/ila-phase0-output
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import Error, sync_playwright


VIEWPORTS = {"desktop": {"width": 1440, "height": 1000},
             "mobile": {"width": 390, "height": 844}}
CHAPTERS = ["vectors", "vector-spans", "row-reduction", "matrix-multiplication",
            "determinants-cofactors", "dds", "least-squares"]
METRICS = """() => ({scrollWidth: document.documentElement.scrollWidth,
    innerWidth, scrollY, iframes: document.querySelectorAll('iframe').length,
    canvases: document.querySelectorAll('canvas').length})"""
# Read on an animation frame: WebGL buffers need not preserve their contents.
PIXELS = """() => new Promise(resolve => {
    const timer = setTimeout(() => resolve({error: 'animation frame timeout'}), 2500);
    requestAnimationFrame(() => {
        clearTimeout(timer);
        try {
            resolve([...document.querySelectorAll('canvas')].map(c => {
                const t = document.createElement('canvas'); t.width = t.height = 128;
                const ctx = t.getContext('2d'); ctx.drawImage(c, 0, 0, 128, 128);
                const p = ctx.getImageData(0, 0, 128, 128).data;
                const colors = new Set(); let nonwhite = 0;
                for (let i = 0; i < p.length; i += 4) {
                    colors.add([p[i], p[i+1], p[i+2], p[i+3]].join(','));
                    if (p[i+3] > 0 && Math.min(p[i],p[i+1],p[i+2]) < 240) nonwhite++;
                }
                return {width: c.width, height: c.height, colors: colors.size, nonwhite};
            }));
        } catch (e) { resolve({error: String(e)}); }
    });
})"""


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def baseline(browser, base, artifacts, settle_ms):
    results, visits = [], []

    def check(name, passed, **evidence):
        results.append({"test": name, "status": "pass" if passed else "fail",
                        "evidence": evidence})

    def visit(context, path, name):
        page = context.new_page()
        record = {"name": name, "requested_url": base + path, "events": []}
        visits.append(record)
        pending = {}

        def event(kind, url, message, **extra):
            item = {"kind": kind, "url": url, "message": message[:1500], **extra}
            for old in record["events"]:
                if all(old.get(k) == v for k, v in item.items()):
                    old["count"] += 1
                    return
            record["events"].append({**item, "count": 1})

        def attach(p):
            p.on("console", lambda m: event("console", m.location.get("url") or p.url,
                                            m.text, level=m.type)
                 if m.type in ("error", "warning") else None)
            p.on("pageerror", lambda e: event("pageerror", p.url, str(e)))
            p.on("request", lambda r: pending.update({r: r.url}))
            p.on("requestfinished", lambda r: pending.pop(r, None))
            p.on("requestfailed", lambda r: (pending.pop(r, None),
                 event("requestfailed", r.url, r.failure or "unknown")))
            p.on("response", lambda r: event("http", r.url, str(r.status))
                 if r.status >= 400 else None)

        attach(page)
        page.on("popup", attach)
        try:
            response = page.goto(base + path, wait_until="domcontentloaded", timeout=15000)
            record["http_status"] = response.status if response else None
        except Error as e:
            event("navigation", base + path, str(e))
        page.wait_for_timeout(settle_ms)
        record["_pending"] = pending
        return page, record

    def capture(page, record, suffix=""):
        path = artifacts / (record["name"] + suffix + ".png")
        page.screenshot(path=str(path), full_page=False, timeout=10000)
        record.setdefault("captures", []).append({"path": str(path), "url": page.url,
            "pending_requests": sorted(set(record["_pending"].values())),
            "layout": page.evaluate(METRICS), "frames": [
                {"url": f.url, **f.evaluate(METRICS)} for f in page.frames]})

    def attempt(name, page, action):
        try:
            action()
        except (Error, AssertionError, ValueError, KeyError, TypeError) as e:
            check(name, False, url=page.url, error=str(e)[:1500])

    def active_pixels(data):
        return isinstance(data, list) and bool(data) and all(
            c["width"] > 0 and c["height"] > 0 and c["colors"] > 8
            and c["nonwhite"] > 20 for c in data)

    for device, viewport in VIEWPORTS.items():
        context = browser.new_context(viewport=viewport, device_scale_factor=1)
        context.set_default_timeout(5000)
        for chapter in CHAPTERS:
            page, record = visit(context, chapter + ".html", f"{chapter}-{device}")

            def chapter_capture():
                # Prefer the first embedded illustration; otherwise the chapter heading.
                target = page.locator("iframe").first
                if not target.count():
                    target = page.locator("section.section").first
                record["portion"] = target.evaluate("e => ({tag: e.tagName, id: e.id, src: e.getAttribute('src')})")
                target.evaluate("e => window.scrollTo(0, e.getBoundingClientRect().top + scrollY - 90)")
                page.wait_for_timeout(500)
                capture(page, record)
                layout = page.evaluate(METRICS)
                check(record["name"] + "-layout", layout["scrollWidth"] <= layout["innerWidth"],
                      url=page.url, **layout)

            attempt(record["name"], page, chapter_capture)
            if chapter == "vectors":
                def knowl():
                    link = page.locator('.hidden-knowl-wrapper a[knowl]:not([knowl=""])').first
                    evidence = {"url": page.url, "knowl": link.get_attribute("knowl"),
                                "tabIndex": link.evaluate("e => e.tabIndex")}
                    link.focus()
                    link.press("Enter")
                    output = page.locator('.knowl-output:visible').first
                    output.wait_for(state="visible")
                    evidence["text_length"] = len(output.inner_text())
                    check(f"knowl-disclosure-{device}", evidence["text_length"] > 30, **evidence)
                    capture(page, record, "-knowl")
                    link.press("Enter")
                    output.wait_for(state="hidden")
                    check(f"knowl-collapse-{device}", True, url=page.url)

                attempt(f"knowl-disclosure-{device}", page, knowl)
                if device == "mobile":
                    def menu():
                        page.reload(wait_until="domcontentloaded", timeout=15000)
                        page.wait_for_timeout(settle_ms)
                        toggle = page.locator('.toggle-button:visible').first
                        reached = False
                        for _ in range(20):
                            page.keyboard.press("Tab")
                            if toggle.evaluate("e => e === document.activeElement"):
                                reached = True
                                break
                        check("mobile-menu-tab-reachable", reached, url=page.url)
                        if not reached:
                            return
                        toc = page.locator('#toc')
                        before = toc.is_visible()
                        page.keyboard.press("Enter")
                        page.wait_for_timeout(400)
                        opened = toc.is_visible()
                        check("mobile-menu-enter-opens", not before and opened, url=page.url)
                        check("mobile-menu-expanded-semantics", toggle.get_attribute("aria-expanded") == "true",
                              url=page.url, aria_expanded=toggle.get_attribute("aria-expanded"))
                        capture(page, record, "-menu")
                        page.keyboard.press("Escape")
                        page.wait_for_timeout(300)
                        check("mobile-menu-escape-closes", not toc.is_visible(), url=page.url)

                    attempt("mobile-menu-keyboard", page, menu)
            page.close()
        context.close()

    context = browser.new_context(viewport=VIEWPORTS["desktop"])
    context.set_default_timeout(5000)
    page, record = visit(context, "demos/vector.html", "vector-demo")

    def vector():
        page.wait_for_function("window.mathbox && document.querySelector('.dg input')")
        pixels = page.evaluate(PIXELS)
        check("vector-canvas-active", active_pixels(pixels), url=page.url, pixels=pixels)
        before = page.locator('#vector-here').inner_text()
        control = page.locator('.dg input').first
        old_value = control.input_value()
        page.locator('.dg .slider').first.click(position={"x": 30, "y": 5})
        page.wait_for_timeout(400)
        after = page.locator('#vector-here').inner_text()
        check("vector-coordinate-slider", before != after and control.input_value() != old_value,
              url=page.url, before=before, after=after,
              input_before=old_value, input_after=control.input_value())

    attempt("vector-demo", page, vector)
    attempt("vector-screenshot", page, lambda: capture(page, record))
    page.close()

    page, record = visit(context, "demos/rowred1.html", "rowred1")

    def rowred():
        page.wait_for_function("window.slideshow && window.rrmat.loaded")
        before = page.locator('.caption').inner_text()
        page.locator('.next-button').click()
        page.wait_for_function("document.querySelector('.caption').innerText !== 'We want to \"solve\" this matrix.'")
        page.wait_for_function("slideshow.currentSlideNum === 1 && !slideshow.playing", timeout=15000)
        check("rowred1-next", page.locator('.caption').inner_text() != before,
              url=page.url, caption=page.locator('.caption').inner_text())
        # Advance through an actual elimination, not only the introductory highlight.
        page.locator('.next-button').click()
        page.wait_for_function("slideshow.currentSlideNum === 2 && !slideshow.playing", timeout=15000)
        expected = page.evaluate("rrmat.state.matrix")
        capture(page, record)
        with page.expect_popup() as popup:
            page.locator('.my-turn button').click()
        child = popup.value
        try:
            child.wait_for_load_state("domcontentloaded", timeout=15000)
            child.wait_for_timeout(settle_ms)
            query = parse_qs(urlsplit(child.url).query, keep_blank_values=True)
            loaded = child.evaluate("window.rrmat ? rrmat.state.matrix : null")
            check("rowred1-handoff-state", loaded == expected and bool(query.get("ops", [""])[0]),
                  url=child.url, query=query, expected_matrix=expected, actual_matrix=loaded)
            capture(child, record, "-handoff")
        finally:
            child.close()

    attempt("rowred1-next-handoff", page, rowred)
    if not record.get("captures"):
        attempt("rowred1-screenshot", page, lambda: capture(page, record))
    page.close()

    page, record = visit(context, "demos/rrinter.html?mat=1,2,3:4,5,6&augment=1", "rrinter")

    def operation():
        page.wait_for_function("window.slideshow && window.rrmat.loaded")
        before = page.evaluate("rrmat.state.matrix")
        old_url = page.url
        page.locator('.ops-control.row-mult .row-button').first.click()
        page.locator('.ops-control.row-mult input').fill("2")
        page.locator('.ops-label.row-mult button').click()
        page.wait_for_function("rrmat.state.matrix[0][0] === 2")
        page.wait_for_timeout(2000)
        after = page.evaluate("rrmat.state.matrix")
        check("rrinter-multiply-row", after == [[2, 4, 6], [4, 5, 6]] and page.url != old_url,
              url=page.url, before=before, after=after, previous_url=old_url)
        capture(page, record)

    attempt("rrinter-multiply-row", page, operation)
    page.close()

    page, record = visit(context, "demos/dynamics3.html?mat=0.7,0.1:-0.5,1.3&v1=1,0&v2=0,1&vec=true&size=20&y=7,9&flow=false", "dynamics3")

    def dynamics():
        pixels = page.evaluate(PIXELS)
        check("dynamics3-scene", active_pixels(pixels), url=page.url, pixels=pixels)
        controls = page.locator('.dg .function:visible').count()
        check("dynamics3-multiply-gui", controls > 0, url=page.url,
              visible_function_controls=controls, gui_container_children=page.locator('#gui-container').evaluate("e => e.children.length"),
              source_observation="autoPlace:false GUI is created but never appended to gui-container")
        capture(page, record)

    attempt("dynamics3", page, dynamics)
    page.close()

    page, record = visit(context, "demos/compose3d.html?mat1=2,0,0:0,1,0:0,0,1&mat2=1,0,0:0,3,0:0,0,1&x=1,2,3", "compose3d")

    def compose():
        page.wait_for_function("window.demo3 && demo3.vector")
        vectors = page.evaluate("[demo1.vector, demo2.vector, demo3.vector]")
        pixels = page.evaluate(PIXELS)
        check("compose-linked-scenes", vectors == [[1, 2, 3], [2, 2, 3], [2, 6, 3]]
              and len(pixels) == 3 and active_pixels(pixels), url=page.url, vectors=vectors, pixels=pixels)
        axes = page.locator('.dg input[type=checkbox]').first
        axes.uncheck()
        visibility = page.evaluate("[1,2,3].map(i => window['mathbox'+i].select('.view'+i+'-axes').get('visible'))")
        check("compose-linked-axes-control", visibility == [False, False, False],
              url=page.url, axes_visible=visibility)
        capture(page, record)

    attempt("compose3d", page, compose)
    page.close()
    context.close()
    for record in visits:
        record["pending_after_close"] = sorted(set(record.pop("_pending").values()))
    return {"summary": dict(Counter(r["status"] for r in results)),
            "results": results, "visits": visits}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("migration/baseline-browser.json"))
    parser.add_argument("--artifacts", type=Path, default=Path("migration/artifacts/browser"))
    parser.add_argument("--executable", default="/usr/bin/chromium")
    parser.add_argument("--settle-ms", type=int, default=1800)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    if not root.is_dir() or not 0 <= args.settle_ms <= 10000:
        parser.error("root must be a directory; settle-ms must be between 0 and 10000")
    for path in (args.output, args.artifacts):
        if path.resolve().is_relative_to(root):
            parser.error("evidence must be outside the served output tree")
    args.artifacts.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(root)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    report = {"schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
              "root": str(root), "viewports": VIEWPORTS,
              "limitations": [
                  "Chromium only; mobile is a viewport, not device/touch emulation. No PDF or fragment-link audit.",
                  "No request interception, dependency substitution, source edits, or custom WebGL flags; Playwright/system defaults are recorded.",
                  "DOMContentLoaded navigation capped at 15s, then bounded settling; external failures and pending requests retained.",
                  "Canvas activity is a 128x128 color sample, not proof of mathematical or visual correctness.",
                  "Viewport screenshots only; selected chapter portions, not exhaustive page coverage.",
                  "Keyboard smoke checks are not a full accessibility audit; animations and network can vary.",
                  "Generated manifest.json is a web-app manifest, not a page inventory; chapter names use actual output files."]}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=args.executable, headless=True, timeout=30000)
            try:
                probe = browser.new_page()
                probe.goto("chrome://version", wait_until="domcontentloaded", timeout=15000)
                report["browser"] = {"version": browser.version, "executable": args.executable,
                    "headless": True, "launch_timeout_ms": 30000, "custom_flags": [],
                    "command_line": probe.locator('#command_line').inner_text(),
                    "webgl": probe.evaluate("!!document.createElement('canvas').getContext('webgl')"),
                    "LD_PRELOAD": os.environ.get("LD_PRELOAD"), "settle_ms": args.settle_ms}
                probe.close()
                report.update(baseline(browser, f"http://127.0.0.1:{server.server_port}/", args.artifacts, args.settle_ms))
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n")
    print(json.dumps({"output": str(args.output), **report["summary"]}))


if __name__ == "__main__":
    main()
