#!/usr/bin/env python3
"""Bounded phase1 Chromium measurements; requires fresh external evidence paths."""

import argparse
from collections import Counter
from datetime import datetime, timezone
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import Error, sync_playwright


VIEWPORTS = {"desktop": {"width": 1440, "height": 1000},
             "mobile": {"width": 390, "height": 844}}
FLAGS = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"]
COMPOSE = ("external/demos/compose3d.html?mat2=1,1,0:0,1,1&mat1=1,0:0,1:1,0"
           "&rangeT=off&rangeU=off&rangeTU=off&range=5&closed=true")
PAGES = {"pilot-products": COMPOSE,
         "pilot-reflection-projection": None,
         "pilot-row-reduction": "external/demos/rowred1.html",
         "pilot-bases-vectors": "external/demos/vector.html",
         "pilot-subspaces-computation": "external/pilot/python.html",
         "pilot-determinants": None}
VISIBLE = {"pilot-products": ["pilot-product-sizes"],
           "pilot-row-reduction": ["pilot-row-operation-invariant"],
           "pilot-bases-vectors": ["pilot-basis-cardinality", "linindep-not-any"],
           "pilot-determinants": ["pilot-product-invertible-proof"]}


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def measure(browser, base, artifacts, report):
    results, visits = report["results"], report["visits"]

    def check(name, passed, **evidence):
        results.append({"test": name, "status": "pass" if passed else "fail",
                         "evidence": evidence})

    def warn(name, **evidence):
        results.append({"test": name, "status": "warn", "evidence": evidence})

    def unique_ids(page, name):
        duplicates = page.locator("[id]").evaluate_all("""es => {
            const counts = new Map();
            es.forEach(e => counts.set(e.id, (counts.get(e.id) || 0) + 1));
            return [...counts].filter(([id, count]) => count > 1);
        }""")
        check(name + ":unique-ids", not duplicates, duplicates=duplicates)

    def toggle(page, item, key, opened):
        summary = item.locator(":scope > summary")
        summary.focus()
        summary.press(key)
        item.evaluate("""async (e, opened) => {
            for (let i = 0; i < 100; i++) {
                if (e.open === opened && !e.getAnimations().length) return;
                await new Promise(r => setTimeout(r, 50));
            }
            throw new Error('Disclosure did not settle');
        }""", opened)
        return summary.evaluate("e => e === document.activeElement")

    def scroll_math(page, name):
        page.wait_for_timeout(200)
        boxes = page.locator(".displaymath")
        for i in range(boxes.count()):
            box = boxes.nth(i)
            if not box.is_visible():
                continue
            data = box.evaluate("""e => ({id:e.id, width:e.clientWidth,
                scroll:e.scrollWidth, tab:e.getAttribute('tabindex'),
                label:e.getAttribute('aria-label') || e.getAttribute('aria-labelledby')})""")
            test = name + ":math-scroll:" + (data["id"] or str(i))
            vertical = box.evaluate("""e => {
                const r=e.getBoundingClientRect();
                return {height:e.clientHeight, scrollHeight:e.scrollHeight,
                    overflowX:getComputedStyle(e).overflowX,
                    overflowY:getComputedStyle(e).overflowY,
                    containers:[...e.querySelectorAll('mjx-container, mjx-math')].map(m => {
                        const b=m.getBoundingClientRect(), s=getComputedStyle(m);
                        return {tag:m.tagName, top:b.top-r.top, bottom:b.bottom-r.top,
                            overflowY:s.overflowY, height:m.clientHeight, scrollHeight:m.scrollHeight};
                    })};
            }""")
            check(test + ":horizontal-only", vertical["overflowX"] == "auto" and
                  vertical["overflowY"] == "hidden" and
                  all(c["overflowY"] not in ("auto", "scroll") or
                      c["scrollHeight"] <= c["height"] for c in vertical["containers"]), **vertical)
            check(test + ":unclipped-height", vertical["scrollHeight"] <= vertical["height"] + 1 and
                  all(c["top"] >= -1 and c["bottom"] <= vertical["height"] + 1
                      for c in vertical["containers"]), **vertical)
            overflow = data["scroll"] > data["width"] + 1
            check(test + ":tab-stop", data["tab"] == "0" and bool(data["label"]) if overflow
                  else data["tab"] is None, **data)
            if not overflow:
                continue
            box.scroll_into_view_if_needed()
            box.evaluate("e => { e.scrollLeft = 0; }")
            edges = box.evaluate("""e => {
                const r=e.getBoundingClientRect(), m=e.querySelector('mjx-math');
                return {boxLeft:r.left, boxRight:r.right, viewport:innerWidth,
                    mathLeft:m?.getBoundingClientRect().left};
            }""")
            box.focus()
            box.press("ArrowRight")
            page.wait_for_timeout(200)
            right = box.evaluate("e => e.scrollLeft")
            check(test + ":arrow-right", right > 0, scroll_left=right)
            box.evaluate("e => { e.scrollLeft = e.scrollWidth; }")
            end = box.evaluate("""e => ({scroll:e.scrollLeft,
                max:e.scrollWidth-e.clientWidth,
                mathRight:e.querySelector('mjx-math')?.getBoundingClientRect().right,
                boxRight:e.getBoundingClientRect().right})""")
            box.press("ArrowLeft")
            page.wait_for_timeout(200)
            left = box.evaluate("e => e.scrollLeft")
            check(test + ":arrow-left", left < end["scroll"], before=end["scroll"], after=left)
            check(test + ":reachable-edges", edges["boxLeft"] >= -1 and
                  edges["boxRight"] <= edges["viewport"] + 1 and
                  edges["mathLeft"] is not None and edges["mathLeft"] >= edges["boxLeft"] - 1 and
                  abs(end["scroll"] - end["max"]) <= 1 and end["mathRight"] is not None and
                  end["mathRight"] <= end["boxRight"] + 1, start=edges, end=end)
            box.evaluate("e => { e.scrollLeft = 0; }")

    def attempt(name, action):
        try:
            action()
        except (Error, AssertionError, ValueError, KeyError, TypeError) as exc:
            check(name, False, error=str(exc)[:2000])

    def attach(page, record):
        page.on("requestfailed", lambda r: record["network_errors"].append(
            {"kind": "requestfailed", "url": r.url, "error": r.failure}))
        page.on("response", lambda r: record["network_errors"].append(
            {"kind": "http", "url": r.url, "status": r.status}) if r.status >= 400 else None)
        page.on("pageerror", lambda e: record["runtime_errors"].append(str(e)))
        page.on("console", lambda m: record["console"].append(
            {"type": m.type, "text": m.text}) if m.type in ("error", "warning") else None)

    def visit(context, path, name):
        page = context.new_page()
        record = {"name": name, "url": base + path, "network_errors": [],
                  "runtime_errors": [], "console": [], "captures": []}
        visits.append(record)
        attach(page, record)
        page.on("popup", lambda p: attach(p, record))

        def navigate():
            response = page.goto(base + path, wait_until="domcontentloaded", timeout=20000)
            check(name + ":navigation", response is not None and response.status == 200,
                  status=response.status if response else None)
        attempt(name + ":navigation", navigate)
        page.wait_for_timeout(1800)
        return page, record

    def capture(page, record, suffix=""):
        path = artifacts / (record["name"] + suffix + ".png")
        page.screenshot(path=str(path), full_page=True, timeout=20000)
        record["captures"].append({"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                   "url": page.url, "viewport": page.viewport_size,
                                   "full_page": True})
        check(record["name"] + suffix + ":screenshot", True)

    for device, viewport in VIEWPORTS.items():
        context = browser.new_context(viewport=viewport, device_scale_factor=1)
        context.set_default_timeout(8000)
        for section, demo in PAGES.items():
            name = section + "-" + device
            page, record = visit(context, section + ".html", name)

            def math():
                page.wait_for_function("window.MathJax?.startup?.document && document.querySelector('mjx-container[jax=CHTML]')")
                page.evaluate("async () => { await MathJax.startup.promise; await document.fonts.ready; }")
                data = page.evaluate("""() => ({
                    chtml: document.querySelectorAll('mjx-container[jax="CHTML"]').length,
                    svg_math: document.querySelectorAll('mjx-container[jax="SVG"]').length,
                    merror: document.querySelectorAll('mjx-merror, merror, [data-mml-node="merror"]').length,
                    tables: document.querySelectorAll('mjx-mtable').length,
                    matrix_containers: [...document.querySelectorAll('mjx-container[jax="CHTML"]')].filter(e => e.querySelector('mjx-mtable')).length,
                    unprocessed: [...document.querySelectorAll('.process-math')].filter(e => !e.querySelector('mjx-container')).length
                })""")
                record["math"] = data
                check(name + ":chtml", data["chtml"] > 0 and data["svg_math"] == 0 and data["unprocessed"] == 0, **data)
                check(name + ":no-merror", data["merror"] == 0, **data)
                check(name + ":matrix-containers", data["matrix_containers"] > 0 if section in
                      ("pilot-products", "pilot-row-reduction") else True, **data)
            attempt(name + ":math", math)

            def typography():
                fonts = page.locator('body, .ptx-banner .title, main .heading, main .para, '
                                     'main summary, main th, main td, #ptx-toc .title, '
                                     '#ptx-navbar .name').evaluate_all("""es => es.map(e => ({
                    tag:e.tagName, class:e.className, family:getComputedStyle(e).fontFamily
                }))""")
                loaded = page.evaluate("""async () => {
                    const styles=['normal 400','italic 400','normal 700','italic 700'];
                    return Promise.all(styles.map(async s => ({style:s,
                        count:(await document.fonts.load(s + ' 16px CharterBT')).length,
                        loaded:document.fonts.check(s + ' 16px CharterBT')})));
                }""")
                check(name + ":charter-text", bool(fonts) and all(
                    f["family"].split(",")[0].strip(' "') == "CharterBT" for f in fonts), fonts=fonts)
                check(name + ":charter-faces-loaded", all(
                    f["count"] == 1 and f["loaded"] for f in loaded), faces=loaded)
                icon = page.locator('#ptx-toc-toggle .icon').evaluate("e => getComputedStyle(e).fontFamily")
                check(name + ":icon-font-preserved", "Material Symbols" in icon, family=icon)
            attempt(name + ":typography", typography)

            def menu_layout():
                button = page.locator('#ptx-toc-toggle')
                sidebar = page.locator('#ptx-sidebar')
                text = page.locator('main .para').first
                before = text.bounding_box()
                initially_open = button.get_attribute('aria-expanded') == 'true'
                check(name + ":menu-initial", initially_open == (page.viewport_size["width"] > 936))
                for opened in (not initially_open, initially_open):
                    button.click()
                    page.wait_for_timeout(100)
                    after = text.bounding_box()
                    check(name + ":menu-state:" + str(opened), sidebar.is_visible() == opened and
                          button.get_attribute('aria-expanded') == str(opened).lower())
                    # At 801-936px the upstream menu is an in-flow tablet panel,
                    # not the persistent desktop slot or fixed mobile overlay.
                    width = page.viewport_size["width"]
                    if width > 936 or width <= 800:
                        check(name + ":menu-text-stable:" + str(width) + ":" + str(opened), all(
                            abs(before[k] - after[k]) <= 1 for k in ('x', 'width', 'height')),
                            before=before, after=after)
                    if not opened:
                        sidebar.locator('a').first.evaluate('e => e.focus()')
                        check(name + ":hidden-menu-unfocusable", sidebar.evaluate(
                            'e => !e.contains(document.activeElement)'))
            attempt(name + ":menu-layout", menu_layout)

            def contracts():
                if demo:
                    page.locator("iframe").first.wait_for(state="attached")
                frames = page.locator("iframe").evaluate_all("es => es.map(e => ({src:e.getAttribute('src'), title:e.title, url:e.src}))")
                check(name + ":iframe-contract", len(frames) == (1 if demo else 0) and all(
                    f["title"].strip() and f["url"] == base + demo and
                    (f["src"] == demo or (section == "pilot-subspaces-computation" and
                                          f["src"] == base + demo)) for f in frames), frames=frames)
                layout = page.evaluate("""() => ({width: innerWidth, scroll_width: document.documentElement.scrollWidth,
                    overflowing: [...document.querySelectorAll('main *')].filter(e => {
                        const r=e.getBoundingClientRect(); return r.width && (r.right > innerWidth+1 || r.left < -1);
                    }).slice(0,20).map(e => ({tag:e.tagName,id:e.id,class:e.className}))})""")
                check(name + ":document-overflow", layout["scroll_width"] <= layout["width"], **layout)
                for frame in page.locator("iframe").all():
                    bounds = frame.evaluate("""e => {const r=e.getBoundingClientRect(),
                        p=e.parentElement.getBoundingClientRect(); return {left:r.left,right:r.right,
                        width:r.width,viewport:innerWidth,parentLeft:p.left,parentRight:p.right,
                        minWidth:getComputedStyle(e).minWidth};}""")
                    check(name + ":iframe-viewport", bounds["width"] > 0 and bounds["left"] >= -1 and
                          bounds["right"] <= bounds["viewport"] + 1 and
                          bounds["left"] >= bounds["parentLeft"] - 1 and
                          bounds["right"] <= bounds["parentRight"] + 1, **bounds)
                for frame in page.frames[1:]:
                    if "/external/demos/" not in frame.url:
                        continue
                    interior = frame.evaluate("""() => ({width:innerWidth,
                        scroll:document.documentElement.scrollWidth,
                        htmlOverflow:getComputedStyle(document.documentElement).overflowX,
                        bodyOverflow:getComputedStyle(document.body).overflowX,
                        beyondViewport:[...document.body.querySelectorAll('*')].filter(e => {
                            const r=e.getBoundingClientRect(); return r.width && r.height &&
                                (r.left < -1 || r.right > innerWidth+1);
                        }).slice(0,8).map(e => {const r=e.getBoundingClientRect(); return {
                            tag:e.tagName,id:e.id,left:r.left,right:r.right};})})""")
                    if interior["scroll"] > interior["width"] + 1 or interior["beyondViewport"]:
                        warn(name + ":legacy-iframe-interior", url=frame.url, **interior,
                             limitation="Legacy interior exceeds its responsive iframe; inspect its own clipping/scrolling. Parent bounds passing does not establish interior accessibility.")
                unique_ids(page, name + ":initial")
            attempt(name + ":contracts", contracts)

            def disclosures():
                if section == "pilot-reflection-projection":
                    for ident in ("pilot-reflection-e1", "pilot-reflection-e2", "pilot-reflection-e3"):
                        image = page.locator('img[src="generated/latex-image/' + ident + '.svg"]')
                        data = image.evaluate("e => ({complete:e.complete,width:e.naturalWidth,height:e.naturalHeight,alt:e.alt})")
                        check(name + ":diagram:" + ident, data["complete"] and data["width"] > 0 and
                              data["height"] > 0 and bool(data["alt"]), **data)
                for ident in VISIBLE.get(section, []):
                    item = page.locator('[id="' + ident + '"]')
                    check(name + ":visible:" + ident, item.count() == 1 and item.is_visible() and
                          item.evaluate("e => e.tagName !== 'DETAILS' && !e.closest('details:not([open])')"))
                if section == "pilot-bases-vectors":
                    for ident in ("pilot-ordered-basis", "pilot-hidden-content"):
                        item = page.locator("#" + ident)
                        closed = item.evaluate("e => e.matches('details.remark:not([open])')")
                        focus_open = toggle(page, item, "Enter", True)
                        opened = item.locator(":scope > article").is_visible()
                        focus_closed = toggle(page, item, "Space", False)
                        check(name + ":remark-keyboard:" + ident, closed and opened and focus_open and
                              focus_closed, initially_closed=closed, content_visible=opened)
                    title = page.locator("#dimension-defn-basis .title")
                    check(name + ":essential-title", title.is_visible() and "Essential: Basis" in title.inner_text())
                    image = page.locator("#pilot-number-line img")
                    data = image.evaluate("e => ({src:e.currentSrc,complete:e.complete,width:e.naturalWidth,height:e.naturalHeight})")
                    check(name + ":numberline-image", data["complete"] and data["width"] > 0 and data["height"] > 0, **data)
                if section == "pilot-subspaces-computation":
                    check(name + ":table-headers", page.locator('#pilot-four-subspaces th').count() == 6)
                    targets = page.locator('[id="pilot-synthetic-footnote"]')
                    check(name + ":footnote-target", targets.count() == 1, count=targets.count(),
                           text=targets.first.text_content() if targets.count() else None)
                    note = targets.first
                    closed = note.evaluate("e => e.matches('details:not([open])')")
                    focus = toggle(page, note, "Enter", True)
                    check(name + ":footnote-enter", closed and focus and
                          note.locator(":scope > .ptx-footnote__contents").is_visible())
                    note.locator(":scope > summary").press("Escape")
                    page.wait_for_timeout(200)
                    escape = note.evaluate("""e => ({open:e.open,
                        focusOnSummary:document.activeElement === e.querySelector('summary')})""")
                    check(name + ":footnote-escape-focus", escape["focusOnSummary"], **escape)
                    if escape["open"]:
                        warn(name + ":footnote-escape-not-closed", **escape,
                             limitation="Escape leaves the native disclosure open; shim does not implement restoration.")
                        toggle(page, note, "Enter", False)
                    unique_ids(page, name + ":footnote-opened")
                if section == "pilot-determinants":
                    outer = page.locator("#pilot-multilinearity")
                    inner = page.locator("#pilot-multilinearity-proof")
                    check(name + ":multilinearity-initially-hidden",
                          outer.evaluate("e => e.matches('details.paragraphs:not([open])')") and
                          not page.locator("#det-defn-linear-prop").is_visible())
                    check(name + ":nested-proof-initially-hidden",
                          inner.evaluate("e => e.matches('details:not([open])')"))
                    focus_outer = toggle(page, outer, "Enter", True)
                    check(name + ":multilinearity-enter", focus_outer and
                          page.locator("#det-defn-linear-prop").is_visible() and
                          not inner.evaluate("e => e.open"))
                    focus_inner = toggle(page, inner, "Enter", True)
                    check(name + ":nested-proof-enter", focus_inner and
                          inner.locator(":scope > article").is_visible())
                    scroll_math(page, name + ":nested-open")
                    check(name + ":nested-proof-space", toggle(page, inner, "Space", False))
                    check(name + ":multilinearity-space", toggle(page, outer, "Space", False))
            attempt(name + ":disclosures", disclosures)
            attempt(name + ":scroll-math", lambda: scroll_math(page, name))

            if section == "pilot-products" and device == "desktop":
                def resize_layout():
                    for width in (937, 936, 800, 390, 1440):
                        page.set_viewport_size({"width": width, "height": viewport["height"]})
                        # Restore the theme's default state before testing its breakpoint.
                        page.locator('#ptx-sidebar').evaluate(
                            "e => e.classList.remove('hidden', 'visible')")
                        page.locator('#ptx-toc-toggle').evaluate("""e => e.setAttribute(
                            'aria-expanded', getComputedStyle(document.querySelector('#ptx-sidebar')).display !== 'none')""")
                        page.wait_for_timeout(200)
                        menu_layout()
                        scroll_math(page, name + ":resize:" + str(width))
                        check(name + ":resize-overflow:" + str(width), page.evaluate(
                            'document.documentElement.scrollWidth <= innerWidth'))
                attempt(name + ":resize-layout", resize_layout)
                page.set_viewport_size(viewport)

            def xrefs():
                links = page.locator("main a[data-knowl]")
                for i in range(links.count()):
                    link = links.nth(i)
                    test = name + ":xref:" + str(i)
                    link.focus()
                    link.press("Enter")
                    uid = link.get_attribute("data-knowl-uid")
                    output = page.locator("#knowl-uid-" + uid)
                    output.wait_for(state="visible")
                    page.wait_for_function("id => {const e=document.getElementById(id); return e && !e.textContent.includes('Loading') && !e.getAnimations().length;}", arg="knowl-uid-" + uid)
                    check(test + ":enter", "active" in (link.get_attribute("class") or "").split() and
                          output.locator(".knowl-output__error").count() == 0,
                          target=link.get_attribute("data-knowl"))
                    unique_ids(page, test + ":open")
                    typography()
                    attempt(test + ":scroll-math", lambda: scroll_math(page, test + ":open"))
                    # Focus a real descendant when available, to distinguish
                    # retained trigger focus from actual focus restoration.
                    descendant = output.locator('a[href]:not([tabindex="-1"]), button, [tabindex="0"]').first
                    if descendant.count():
                        descendant.focus()
                    else:
                        link.focus()
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(200)
                    focus = link.evaluate("""e => {const a=document.activeElement; return {
                        onTrigger:a===e,tag:a.tagName,id:a.id,connected:a.isConnected,
                        visible:!!(a.getClientRects().length),open:e.classList.contains('active')};}""")
                    check(test + ":escape-focus-usable", focus["connected"] and focus["visible"] and
                          focus["tag"] != "BODY", **focus)
                    if focus["open"] or not focus["onTrigger"]:
                        warn(test + ":escape-restoration", **focus,
                             limitation="Missing-globals shim does not close knowls or restore descendant focus to the trigger.")
                    if focus["open"]:
                        link.focus()
                        link.press("Enter")
                        output.wait_for(state="hidden")
                        check(test + ":enter-close", link.evaluate("e => e === document.activeElement"))
            attempt(name + ":xrefs", xrefs)
            attempt(name + ":final-ids", lambda: unique_ids(page, name + ":final"))
            attempt(name + ":capture", lambda: capture(page, record))
            page.close()
            if section == "pilot-determinants":
                fragment, fragment_record = visit(context, section + ".html#det-defn-linear-prop", name + "-fragment")

                def fragment_access():
                    target = fragment.locator("#det-defn-linear-prop")
                    data = target.evaluate("""e => {const r=e.getBoundingClientRect(); return {
                        closedAncestors:[...document.querySelectorAll('details:not([open])')].filter(d=>d.contains(e)).map(d=>d.id),
                        top:r.top,bottom:r.bottom,height:r.height,viewport:innerHeight};}""")
                    check(name + ":direct-fragment", target.is_visible() and not data["closedAncestors"] and
                          data["height"] > 0 and data["bottom"] > 0 and data["top"] < data["viewport"], **data)
                    check(name + ":fragment-keeps-proof-hidden",
                          not fragment.locator("#pilot-multilinearity-proof").evaluate("e => e.open"))
                attempt(name + ":fragment-access", fragment_access)
                attempt(name + ":fragment-capture", lambda: capture(fragment, fragment_record))
                fragment.close()
        context.close()

    context = browser.new_context(viewport=VIEWPORTS["desktop"])
    context.set_default_timeout(15000)
    for demo, path in [("vector", PAGES["pilot-bases-vectors"]), ("compose3d", COMPOSE),
                       ("rowred1", PAGES["pilot-row-reduction"])]:
        page, record = visit(context, path, demo)

        def state():
            if demo == "vector":
                page.wait_for_function("window.mathbox && document.querySelectorAll('.dg input').length >= 3")
                values = page.locator(".dg input[type=text]").evaluate_all("es => es.slice(0,3).map(e => Number(e.value))")
                check("vector:default-state", values == [5, 3, 4], controls=values,
                      caption=page.locator("#vector-here").inner_text())
            elif demo == "compose3d":
                page.wait_for_function("window.demo3 && demo3.vector")
                data = page.evaluate("""() => ({vectors:[demo1.vector,demo2.vector,demo3.vector],
                    matrix_columns:[demo2.rangeU.vectors,demo3.rangeT.vectors,demo3.rangeTU.vectors].map(m => m.map(v => [v.x,v.y,v.z])),
                    captions:[1,2,3].map(i => document.querySelector('#matrix'+i+'-here').textContent)})""")
                check("compose3d:default-state", data["vectors"] == [[-1, 2, 0], [-1, 2, -1], [1, 1, 0]], **data)
                check("compose3d:matrix-state", data["matrix_columns"] == [
                    [[1, 0, 1], [0, 1, 0], [0, 0, 0]],
                    [[1, 0, 0], [1, 1, 0], [0, 1, 0]],
                    [[1, 1, 0], [1, 1, 0], [0, 0, 0]]],
                    matrix_columns=data["matrix_columns"], convention="3D-padded column vectors")
            else:
                page.wait_for_function("window.slideshow && window.rrmat.loaded")
                before = page.evaluate("rrmat.state.matrix")
                check("rowred1:initial-state", before == [[1, 2, 3, 6], [2, -3, 2, 14], [3, 1, -1, -2]], matrix=before)
                for slide in (1, 2):
                    page.locator(".next-button").click()
                    page.wait_for_function("n => slideshow.currentSlideNum === n && !slideshow.playing", arg=slide)
                expected = page.evaluate("rrmat.state.matrix")
                check("rowred1:next", expected != before, matrix=expected, caption=page.locator(".caption").inner_text())
                with page.expect_popup() as popup:
                    page.locator(".my-turn button").click()
                child = popup.value
                try:
                    child.wait_for_load_state("domcontentloaded")
                    child.wait_for_function("window.rrmat && rrmat.loaded")
                    query = parse_qs(urlsplit(child.url).query)
                    actual = child.evaluate("rrmat.state.matrix")
                    check("rowred1:handoff-history", actual == expected and bool(query.get("ops", [""])[0])
                          and int(query.get("cur", ["0"])[0]) > 0 and
                          urlsplit(child.url).path == "/external/demos/rrinter.html",
                          url=child.url, query=query, expected=expected, actual=actual,
                          history=child.locator(".history").inner_text())
                    capture(child, record, "-handoff")
                finally:
                    child.close()
            canvases = page.locator("canvas").evaluate_all("es => es.map(e => ({width:e.width,height:e.height}))")
            check(demo + ":canvas-present", len(canvases) == (3 if demo == "compose3d" else 1)
                  and all(c["width"] > 0 and c["height"] > 0 for c in canvases), canvases=canvases)
        attempt(demo + ":state", state)
        attempt(demo + ":capture", lambda: capture(page, record))
        page.close()
    context.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    output, artifacts = args.output.resolve(), args.artifacts.resolve()
    workspace = Path(__file__).resolve().parents[2]
    baseline = (Path.home() / "tmp/ila/phase0").resolve()
    if not root.is_dir():
        parser.error("root must be a directory")
    for path in (output, artifacts):
        if (path.exists() or path.is_relative_to(root) or path.is_relative_to(workspace)
                or path.is_relative_to(baseline)):
            parser.error("evidence paths must be fresh and outside the served tree, workspace, and baseline")
    if artifacts.is_relative_to(output):
        parser.error("artifacts cannot be inside the report file")
    artifacts.mkdir(parents=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {"schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
              "root": str(root), "viewports": VIEWPORTS, "results": [], "visits": [],
              "limitations": ["Chromium only; mobile viewport is not touch/device emulation.",
                              "CHTML/table counts and runtime state are smoke measurements, not proof of mathematical correctness.",
                              "Canvas dimensions and screenshots do not prove WebGL scene or pixel correctness.",
                              "Bounded waits, live external dependencies; network failures reported separately.",
                                "Matrix containers include aligned equation tables; keyboard checks are not an accessibility audit.",
                                "Warnings record legacy iframe interior overflow and incomplete Escape focus restoration, not acceptance."]}
    input_hash = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            parser.error("served tree must not contain symlinks")
        if path.is_file():
            record = [path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()]
            input_hash.update((json.dumps(record, ensure_ascii=True) + "\n").encode())
    report["input_tree_sha256"] = input_hash.hexdigest()
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(root)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path="/usr/bin/chromium", headless=True, args=FLAGS)
            try:
                report["browser"] = {"version": browser.version, "executable": "/usr/bin/chromium",
                                     "flags": FLAGS, "LD_PRELOAD": os.environ.get("LD_PRELOAD")}
                measure(browser, f"http://127.0.0.1:{server.server_port}/", artifacts, report)
            finally:
                browser.close()
    except Exception as exc:
        report["results"].append({"test": "harness", "status": "fail", "evidence": {"error": str(exc)}})
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        counts = Counter(r["status"] for r in report["results"])
        report["summary"] = {"pass": counts["pass"], "fail": counts["fail"], "warn": counts["warn"],
                             "network_errors": sum(len(v["network_errors"]) for v in report["visits"]),
                             "runtime_errors": sum(len(v["runtime_errors"]) for v in report["visits"]),
                             "screenshots": sum(len(v["captures"]) for v in report["visits"])}
        output.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n")
    print(json.dumps({"output": str(output), **report["summary"]}))
    return int(bool(counts["fail"] or report["summary"]["network_errors"] or report["summary"]["runtime_errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
