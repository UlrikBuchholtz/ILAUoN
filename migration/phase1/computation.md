# Phase 1 Python Computation Pilot

## Integration

Load `external/pilot/python-adapter.js` on book pages through the parent XSL's
`html.js.extra`. Copy the four `source/external/pilot/python*` assets into the
built `external/pilot/` directory, preserving their relative paths. No runtime
binaries or environment changes are needed. Serve over HTTP(S), not `file:`.
The component needs JavaScript, workers, WebAssembly, and access to jsDelivr.
An upstream HTTP CSP must also permit the frame and its runtime requirements;
a meta policy cannot relax an HTTP policy.

The adapter does nothing on pages without `code#rs-pilot-floating-point-program`.
This is the actual ID rendered in run-005 for source program
`pilot-floating-point-program`. It reads the rendered code's `textContent` and
inserts the iframe after its `.code-box`; the static listing stays intact.
Neither `main.ptx`, the previous build, nor the compat assets are changed.
The old source paragraph saying browser execution is untested remains unchanged
by design; this report and the new component describe the newer evidence.

## Pins

All runtime requests use the fixed prefix
`https://cdn.jsdelivr.net/pyodide/v0.29.3/full/`.

| Component | Version / Package |
| --- | --- |
| Pyodide | 0.29.3 |
| Browser Python | 3.13.2 |
| SymPy | 1.13.3, `sympy-1.13.3-py3-none-any.whl` |
| mpmath | 1.3.0, `mpmath-1.3.0-py3-none-any.whl` |
| Native comparison | Python 3.12.14, SymPy 1.14.0 |

Release `pyodide-lock.json` was checked using webfetch, with package fields
also extracted using curl and the existing external Python environment.
The checked 0.27.7, 0.28.3, 0.29.0, 0.29.2, and 0.29.3 bundles contain SymPy
1.13.3. **The requested SymPy 1.14.0 parity is not met by this bundled runtime.**
No unreviewed wheel source or second CDN has been added to conceal that gap.
The floating-point listing nevertheless produces byte-for-byte identical output
to the native 1.14.0 fixture, including Unicode pretty-printing.

The 0.29.3 lock contains an unexpected `info.version` of `0.28.0.dev0`, so that
metadata is not used as runtime version evidence. Chromium reports
`Pyodide 0.29.3; Python 3.13.2; SymPy 1.13.3; mpmath 1.3.0` on successful runs.
Lock package SHA-256 values:

```text
sympy  56d438f823c08b2a08231400dcf1f640374192d7b1df0f55c4171bd708227b5f
mpmath 75c33edefd4b92311926ddbfa7aac6731a61b3b5ac0562bc8f8d420e23328d46
```

## Execution And Limits

- First Run constructs a dedicated Blob worker and loads Python plus SymPy.
- Only one execution can be active. Each execution gets a new globals dictionary.
- Successful runs reuse the runtime. Imported modules and interpreter state are
  not reset by fresh globals; this is not a fresh interpreter per execution.
- Stop terminates the worker, including infinite Python loops. Errors and timeouts
  also discard it. Reset additionally restores the rendered source and clears
  output and version results. A discarded worker is recreated on the next Run,
  not eagerly during Reset.
- Generation checks reject stale worker results after Stop, Reset, or completion.
- Loading has a 120-second deadline; execution has a separate 30-second deadline.
- Output is capped at 20,000 characters plus a 20-character truncation notice in
  both the normal worker output path and the frame receiver. Output and status
  use text nodes, never HTML. This is not a memory quota on Python allocations.
- stdin is unsupported. Pyodide can translate the throwing stdin callback into
  `OSError`; this is reported as a Python error rather than opening a prompt.

## Security Scope

The iframe has **only** `sandbox="allow-scripts"`, never `allow-same-origin`.
Its origin is opaque (`null`). The parent accepts ready messages only from that
iframe's window with opaque origin; the child accepts its initial source packet
only from `parent`. The wildcard postMessage target is necessary for the opaque
recipient, not a substitute for validating `event.source`.

The iframe is the origin-isolation boundary. **The worker is not a security
boundary**: Python can use JavaScript interop, mutate worker state, and forge
worker messages. It is used to keep ordinary Python execution off the UI thread
and make termination possible. Fresh globals are not a security mechanism.

The frame CSP denies resources by default, allows local component JS/CSS, Blob
workers, and the pinned jsDelivr runtime path for scripts and connections.
`unsafe-eval` is needed for the runtime's JavaScript/WebAssembly machinery.
Fetch calls used by the loader/package path are wrapped with `credentials:
"omit"` and no referrer; classic importScripts does not expose that option.
The opaque origin prevents same-origin book credentials/storage access.
There is no persistence API in the component. The initial same-site frame
navigation is still an ordinary browser request, not a credentialless iframe.

Untrusted code may access the allowlisted CDN outbound, including URL query
strings. This is **not offline or exfiltration-proof**, and CDN availability and
integrity are dependencies. CSP allowlists and package pins are not a full
supply-chain integrity system. Browser memory exhaustion, hostile JS interop,
message floods, browser defects, and timer throttling remain risks. This is a
working Phase 1 pilot, not a fully production-hardened arbitrary-code service.

## Reproduction

Run against a final build that includes the adapter and assets:

```bash
LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libstdc++.so.6 \
  /home/ulrik/tmp/ila/phase1/venv/bin/python \
  migration/phase1/computation-check.py \
  /absolute/path/to/output/html \
  /existing/external/directory/fresh-computation-report.json
```

The script uses system `/usr/bin/chromium`, its own ephemeral loopback server,
and the existing Playwright/native SymPy environment. It refuses to overwrite
reports. Add `--overlay` to test current component assets against an old build:
only the four component assets and the adapter script insertion are served as
an in-memory overlay; nothing in that build is written. The native fixture is
executed from the rendered listing, not a duplicated code sample.

Checks cover source extraction, no runtime requests before Run, exact sandbox,
opaque origin, blocked parent DOM/storage, rejected nonparent source message,
native output and runtime versions, fresh globals, single execution, infinite
Stop/restart, syntax error, Reset/rerun, output cap, stdin, real 30-second run
timeout, Reset during execution, stale-result suppression, mobile width,
off-allowlist fetch denial, load timeout, and UI errors. The load-timeout test
holds CDN requests and advances Playwright's UI clock by 120 seconds; the run
timeout uses real elapsed time. This is Chromium coverage, not cross-browser
certification.

External reports `computation-001.json` and `computation-002.json` preserve the
initial failures (package progress mixed with output; stdin error wording).
`/home/ulrik/tmp/ila/phase1/computation-003.json` records 22 passes, zero failures.
The final report `/home/ulrik/tmp/ila/phase1/computation-004.json` records
**23 passes, zero failures** on Chromium 150.0.7871.100, including the explicit
version-pin assertion. Both successful runs used the unchanged run-005 HTML
with the component overlay. Rerun without `--overlay` to verify final-build
integration; that integration has not been changed or tested here.
