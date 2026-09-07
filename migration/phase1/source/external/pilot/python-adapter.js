(() => {
  "use strict";
  const frameURL = new URL("python.html", document.currentScript.src).href;
  function attach() {
    const code = document.querySelector("code#rs-pilot-floating-point-program");
    if (!code || document.getElementById("pilot-python-frame")) return;
    const frame = document.createElement("iframe");
    frame.id = "pilot-python-frame";
    frame.title = "Python computation pilot";
    frame.setAttribute("sandbox", "allow-scripts");
    frame.referrerPolicy = "no-referrer";
    frame.style.cssText = "display:block;width:100%;height:48rem;border:0;";
    window.addEventListener("message", (event) => {
      if (event.source !== frame.contentWindow || event.origin !== "null") return;
      if (event.data?.type === "pilot-python-ready") {
        // An opaque sandbox has no target origin other than '*'.
        frame.contentWindow.postMessage({type: "pilot-python-code", code: code.textContent}, "*");
      }
    });
    frame.src = frameURL;
    code.closest(".code-box").after(frame);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", attach, {once: true});
  else attach();
})();
