(() => {
  "use strict";
  // This function is serialized into a Blob: no Python runs on the UI thread.
  function pythonWorker() {
    const CDN = "https://cdn.jsdelivr.net/pyodide/v0.29.3/full/";
    const nativeFetch = self.fetch.bind(self);
    self.fetch = (url, options = {}) => nativeFetch(url, {...options, credentials: "omit", referrerPolicy: "no-referrer"});
    let used = 0;
    let generation;
    const send = (type, data = {}) => self.postMessage({type, generation, ...data});
    function output(text) {
      const remaining = 20000 - used;
      if (remaining <= 0) return;
      const part = text.slice(0, remaining);
      used += part.length;
      send("output", {text: part});
      if (used === 20000) send("output", {text: "\n[Output truncated]\n"});
    }
    self.onmessage = async ({data}) => {
      generation = data.generation;
      used = 0;
      let globals;
      try {
        importScripts(CDN + "pyodide.js");
        const runtime = await loadPyodide({indexURL: CDN, stdin: () => { throw new Error("stdin is unsupported"); }});
        runtime.setStdout({batched: (text) => output(text + "\n")});
        runtime.setStderr({batched: (text) => output(text + "\n")});
        await runtime.loadPackage("sympy", {messageCallback: () => {}, errorCallback: (text) => output(text + "\n")});
        const versions = "Pyodide " + runtime.version + "; " + runtime.runPython("import sys, sympy, mpmath\n'Python ' + sys.version.split()[0] + '; SymPy ' + sympy.__version__ + '; mpmath ' + mpmath.__version__");
        send("loaded");
        globals = runtime.toPy({__name__: "__main__"});
        await runtime.runPythonAsync(data.code, {globals});
        send("success", {versions});
      } catch (error) {
        output(String(error));
        send("failure");
      } finally {
        if (globals) globals.destroy();
      }
    };
  }
  const editor = document.getElementById("code");
  const run = document.getElementById("run");
  const stop = document.getElementById("stop");
  const reset = document.getElementById("reset");
  const status = document.getElementById("status");
  const output = document.getElementById("output");
  const versions = document.getElementById("versions");
  let original;
  let worker;
  let generation = 0;
  let timer;
  let busy = false;
  function idle(message) {
    clearTimeout(timer);
    // Fresh globals alone do not reset modules, builtins, or the virtual filesystem.
    if (worker) { worker.terminate(); worker = undefined; }
    generation++;
    busy = false;
    run.disabled = false;
    stop.disabled = true;
    status.textContent = message;
  }
  function deadline(milliseconds, message) {
    clearTimeout(timer);
    timer = setTimeout(() => idle(message), milliseconds);
  }
  window.addEventListener("message", (event) => {
    if (event.source !== parent || original !== undefined) return;
    if (event.data?.type !== "pilot-python-code" || typeof event.data.code !== "string") return;
    original = event.data.code;
    editor.value = original;
    editor.disabled = run.disabled = reset.disabled = false;
    status.textContent = "Ready. Runtime has not loaded.";
  });
  run.addEventListener("click", () => {
    if (busy || original === undefined) return;
    busy = true;
    run.disabled = true;
    stop.disabled = false;
    output.textContent = "";
    status.textContent = "Loading Python and SymPy...";
    const token = ++generation;
    const url = URL.createObjectURL(new Blob(["(" + pythonWorker.toString() + ")()"], {type: "text/javascript"}));
    try { worker = new Worker(url); }
    catch (error) { idle("Worker could not start: " + String(error)); return; }
    finally { URL.revokeObjectURL(url); }
    worker.onmessage = ({data}) => {
      if (!busy || token !== generation || data.generation !== token) return;
      if (data.type === "output" && typeof data.text === "string") {
        output.textContent += data.text.slice(0, Math.max(0, 20020 - output.textContent.length));
      } else if (data.type === "loaded") {
        status.textContent = "Running...";
        deadline(30000, "Run timed out. Worker discarded.");
      } else if (data.type === "success") {
        versions.textContent = String(data.versions).slice(0, 300);
        idle("Completed.");
      } else if (data.type === "failure") idle("Python or loading error. Worker discarded.");
    };
    worker.onerror = (event) => {
      if (token !== generation) return;
      event.preventDefault();
      idle("Worker error. Check CDN connectivity and browser CSP support.");
    };
    deadline(120000, "Load timed out. Worker discarded.");
    worker.postMessage({code: editor.value, generation: token});
  });
  stop.addEventListener("click", () => idle("Stopped. Worker discarded."));
  reset.addEventListener("click", () => {
    idle("Reset. Runtime will reload on Run.");
    editor.value = original;
    output.textContent = "";
    versions.textContent = "Pinned runtime: Pyodide 0.29.3; bundled SymPy 1.13.3.";
  });
  parent.postMessage({type: "pilot-python-ready"}, "*");
})();
