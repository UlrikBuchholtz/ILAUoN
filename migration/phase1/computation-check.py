#!/usr/bin/env python3
"""Real Chromium checks. --overlay serves new pilot assets over an unchanged build."""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
from threading import Thread

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("built_root", type=Path)
    parser.add_argument("report", type=Path, help="Fresh external JSON report path")
    parser.add_argument("--overlay", action="store_true")
    parser.add_argument("--chromium", default="/usr/bin/chromium")
    args = parser.parse_args()
    pilot = Path(__file__).resolve().parent
    workspace = pilot.parents[1]
    baseline = (Path.home() / "tmp/ila/phase0").resolve()
    args.built_root = args.built_root.expanduser().resolve(strict=True)
    destination = args.report.expanduser()
    args.report = destination.resolve()
    if (destination.is_symlink() or args.report.exists() or not args.report.parent.is_dir()
            or any(args.report.is_relative_to(root) for root in (workspace, baseline, args.built_root))):
        parser.error("Report must be fresh with an existing parent, outside the repository, served root, and baseline")
    assets = pilot / "source" / "external" / "pilot"
    names = ("python-adapter.js", "python-frame.js", "python.html", "python.css")
    inputs = {"/external/pilot/" + name: (assets if args.overlay else args.built_root / "external/pilot") / name
              for name in names}
    inputs["/pilot-subspaces-computation.html"] = args.built_root / "pilot-subspaces-computation.html"
    # Serve these exact bytes so a concurrent rebuild cannot invalidate their hashes.
    snapshots = {url: path.read_bytes() for url, path in inputs.items()}
    if args.overlay:
        url = "/pilot-subspaces-computation.html"
        snapshots[url] = snapshots[url].replace(b"</head>", b'<script src="external/pilot/python-adapter.js" defer></script></head>')

    class Handler(SimpleHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def log_message(self, *_args):
            pass

        def do_GET(self):
            name = self.path.split("?")[0]
            if name in snapshots:
                data = snapshots[name]
                self.send_response(200)
                self.send_header("Content-Type", self.guess_type(name) + "; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                super().do_GET()

    class Server(ThreadingHTTPServer):
        daemon_threads = False
        block_on_close = True

    report = {"created": datetime.now(timezone.utc).isoformat(),
              "built_root": str(args.built_root.resolve()), "overlay": args.overlay,
              "inputs": {url: {"path": str(inputs[url]), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                         for url, data in snapshots.items()},
              "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "current_source_sha256": {name: hashlib.sha256((assets / name).read_bytes()).hexdigest() for name in names},
              "results": [], "runtime_requests": [], "errors": []}

    def check(name, passed, **details):
        report["results"].append({"test": name, "status": "pass" if passed else "fail", **details})

    server = server_thread = None
    # Reserve exclusively before starting the browser; never overwrite earlier evidence.
    report_stream = args.report.open("x")
    try:
        server = Server(("127.0.0.1", 0), partial(Handler, directory=str(args.built_root)))
        server_thread = Thread(target=server.serve_forever, name="computation-http")
        server_thread.start()
        with sync_playwright() as p, ExitStack() as cleanup:
            browser = p.chromium.launch(
                executable_path=None if args.chromium == "playwright" else args.chromium,
                headless=True, chromium_sandbox=True)
            cleanup.callback(browser.close)
            report["chromium_sandbox"] = True
            report["chromium"] = browser.version
            page = browser.new_page()
            page.on("request", lambda r: report["runtime_requests"].append(r.url)
                    if "/pyodide/" in r.url else None)
            page.on("pageerror", lambda e: report["errors"].append(str(e)))
            page.goto(f"http://127.0.0.1:{server.server_port}/pilot-subspaces-computation.html")
            frame_element = page.locator("#pilot-python-frame")
            frame_element.wait_for()
            frame = frame_element.element_handle().content_frame()
            frame.wait_for_function("!document.querySelector('#run').disabled")
            source = page.locator("#rs-pilot-floating-point-program").text_content()
            report["initial_code_sha256"] = hashlib.sha256(source.encode("utf-8")).hexdigest()
            check("derived-source", frame.locator("#code").input_value() == source)
            page.wait_for_timeout(1200)
            check("lazy-runtime", not report["runtime_requests"])
            check("sandbox", frame_element.get_attribute("sandbox") == "allow-scripts")
            isolation = frame.evaluate("""() => {
                const result = {origin: self.origin};
                try { parent.document.body; result.parentBlocked = false; }
                catch { result.parentBlocked = true; }
                try { localStorage.setItem('pilot', 'x'); result.storageBlocked = false; }
                catch { result.storageBlocked = true; }
                return result;
            }""")
            check("opaque-origin", isolation == {"origin": "null", "parentBlocked": True, "storageBlocked": True}, evidence=isolation)
            frame.evaluate("window.postMessage({type:'pilot-python-code', code:'forged'}, '*')")
            check("reject-nonparent-packet", frame.locator("#code").input_value() == source)

            def run(code=None):
                if code is not None:
                    frame.locator("#code").fill(code)
                frame.locator("#run").click()

            def completed():
                frame.wait_for_function("document.querySelector('#status').textContent === 'Completed.'", timeout=125000)
                return frame.locator("#output").text_content()

            frame.get_by_label("Python source", exact=True).focus()
            page.keyboard.press("Tab")
            check("keyboard-run-focus", frame.locator("#run").evaluate("e => e === document.activeElement")
                  and frame_element.evaluate("e => e === document.activeElement"))
            page.keyboard.press("Enter")
            actual = completed()
            # The input build must be trusted: this subprocess is not a Python sandbox.
            native = subprocess.run([sys.executable, "-c", source], capture_output=True, text=True, check=True, timeout=15).stdout
            check("native-output", actual == native, browser=actual, native=native)
            report["versions"] = frame.locator("#versions").text_content()
            report["native_versions"] = subprocess.check_output(
                [sys.executable, "-c", "import sys,sympy; print(sys.version); print(sympy.__version__)"], text=True, timeout=15)
            check("version-pins", report["versions"] == "Pyodide 0.29.3; Python 3.13.2; SymPy 1.13.3; mpmath 1.3.0"
                  and report["native_versions"].rstrip().endswith("1.14.0"))
            check("runtime-loaded", bool(report["runtime_requests"]))
            run("""marker = 42
import builtins, sys, sympy
from js import globalThis
builtins._pilot_mutation = True
sympy._pilot_mutation = True
sys.path.append('/pilot-mutated-path')
globalThis._pilot_mutation = True
with open('/tmp/pilot-state', 'w') as f:
    f.write('mutated')
print('first')""")
            completed()
            run("""import builtins, sys, sympy, os, json
from js import globalThis
print('marker' in globals())
print(json.dumps({
    'builtins': hasattr(builtins, '_pilot_mutation'),
    'sympy_module': hasattr(sympy, '_pilot_mutation'),
    'sys_path': '/pilot-mutated-path' in sys.path,
    'worker_javascript': hasattr(globalThis, '_pilot_mutation'),
    'virtual_filesystem': os.path.exists('/tmp/pilot-state'),
}))""")
            state_output = completed().splitlines()
            check("fresh-globals", state_output[0] == "False")
            state = json.loads(state_output[1])
            report["cross_run_mutations_preserved"] = state
            check("fresh-runtime-state", not any(state.values()), evidence=state)
            run("while True: pass")
            frame.wait_for_function("document.querySelector('#status').textContent === 'Running...'", timeout=125000)
            check("single-execution", frame.locator("#run").is_disabled())
            frame.locator("#code").focus(timeout=3000)
            page.keyboard.press("Tab")
            check("keyboard-stop-focus", frame.locator("#stop").evaluate("e => e === document.activeElement"))
            page.keyboard.press("Space")
            check("infinite-stop", frame.locator("#status").text_content().startswith("Stopped."))
            run("print('restarted')")
            check("restart", completed() == "restarted\n")
            run("if :")
            frame.wait_for_function("document.querySelector('#status').textContent.includes('error')", timeout=125000)
            check("syntax-error", "SyntaxError" in frame.locator("#output").text_content())
            frame.locator("#code").focus()
            page.keyboard.press("Tab")
            page.keyboard.press("Tab")
            check("keyboard-reset-focus", frame.locator("#reset").evaluate("e => e === document.activeElement"))
            page.keyboard.press("Enter")
            check("reset", frame.locator("#code").input_value() == source and frame.locator("#output").text_content() == "")
            run()
            check("reset-rerun", completed() == native)
            run("print('x' * 50000)")
            bounded = completed()
            check("bounded-output", len(bounded) <= 20020 and "[Output truncated]" in bounded, length=len(bounded))
            run("input('prompt')")
            frame.wait_for_function("document.querySelector('#status').textContent.includes('error')", timeout=125000)
            stdin_error = frame.locator("#output").text_content()
            check("stdin-unsupported", any(s in stdin_error for s in ("stdin is unsupported", "OSError", "EOFError")), output=stdin_error)
            run("while True: pass")
            frame.wait_for_function("document.querySelector('#status').textContent.startsWith('Run timed out')", timeout=155000)
            check("run-timeout", frame.locator("#run").is_enabled())
            run("while True: pass")
            frame.wait_for_function("document.querySelector('#status').textContent === 'Running...'", timeout=125000)
            frame.locator("#reset").click(timeout=3000)
            page.wait_for_timeout(300)
            check("reset-running-stale", frame.locator("#code").input_value() == source and frame.locator("#output").text_content() == "" and frame.locator("#status").text_content().startswith("Reset."))
            page.set_viewport_size({"width": 390, "height": 844})
            check("mobile-width", frame.evaluate("document.documentElement.scrollWidth <= innerWidth"))
            blocked = frame.evaluate("""() => new Promise(resolve => {
                const timeout = setTimeout(() => { document.removeEventListener('securitypolicyviolation', listener); resolve(null); }, 3000);
                function listener(event) {
                    if (event.effectiveDirective !== 'connect-src') return;
                    clearTimeout(timeout);
                    document.removeEventListener('securitypolicyviolation', listener);
                    resolve({directive: event.effectiveDirective, uri: event.blockedURI, disposition: event.disposition});
                }
                document.addEventListener('securitypolicyviolation', listener);
                fetch('https://example.com/pilot-disallowed').catch(() => {});
            })""")
            check("off-allowlist-connect-blocked", blocked is not None and blocked["directive"] == "connect-src"
                  and blocked["disposition"] == "enforce" and blocked["uri"].startswith("https://example.com"), evidence=blocked)
            # Hold the CDN request and advance only UI timers, not the real network.
            held = []
            page.route("https://cdn.jsdelivr.net/pyodide/**", lambda route: held.append(route))
            page.clock.install()
            run()
            page.wait_for_timeout(300)
            page.clock.fast_forward(120001)
            frame.wait_for_function("document.querySelector('#status').textContent.startsWith('Load timed out')")
            check("load-timeout", frame.locator("#run").is_enabled())
            for route in held:
                route.abort()
            page.unroute("https://cdn.jsdelivr.net/pyodide/**")
            check("no-ui-errors", not report["errors"], errors=report["errors"])
    except (Exception, KeyboardInterrupt) as exc:
        report["failure"] = str(exc)
        check("harness", False, error=f"{type(exc).__name__}: {exc}")
    finally:
        if server_thread is not None and server_thread.is_alive():
            server.shutdown()
        if server is not None:
            server.server_close()
        if server_thread is not None:
            server_thread.join()
        report["server_closed"] = True
        report["counts"] = {s: sum(r["status"] == s for r in report["results"]) for s in ("pass", "fail")}
        with report_stream as stream:
            json.dump(report, stream, indent=2)
    print(json.dumps({"report": str(args.report), "counts": report["counts"], "failure": report.get("failure")}))
    return 1 if report.get("failure") or report["counts"]["fail"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
