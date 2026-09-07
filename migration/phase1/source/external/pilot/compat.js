(() => {
  "use strict";

  // 2.52.3's legacy Enter/Escape handler reads these absent globals.
  // Containment only: empty stacks do not implement knowl focus restoration.
  if (typeof window.knowl_focus_stack === "undefined") window.knowl_focus_stack = [];
  if (typeof window.knowl_focus_stack_uid === "undefined") window.knowl_focus_stack_uid = [];
  if (typeof window.just_hit_escape === "undefined") window.just_hit_escape = false;

  function start() {
    let pending = false;
    const observed = new WeakSet();
    const owned = new WeakSet();
    const sizes = new ResizeObserver(schedule);

    function schedule() {
      if (pending) return;
      pending = true;
      requestAnimationFrame(() => {
        pending = false;
        document.querySelectorAll(".displaymath").forEach((box) => {
          // Observe both viewport and typeset content (including late fonts).
          [box, ...box.querySelectorAll("mjx-container")].forEach((element) => {
            if (!observed.has(element)) {
              observed.add(element);
              sizes.observe(element);
            }
          });
          const overflow = box.clientWidth > 0 && box.scrollWidth > box.clientWidth + 1;
          if (overflow && !box.hasAttribute("tabindex")) {
            box.setAttribute("tabindex", "0");
            owned.add(box);
            if (!box.hasAttribute("aria-label") && !box.hasAttribute("aria-labelledby")) {
              box.setAttribute("aria-label", "Scrollable display mathematics");
              box.dataset.pilotScrollLabel = "true";
            }
          } else if (!overflow && owned.has(box)) {
            box.removeAttribute("tabindex");
            owned.delete(box);
            if (box.dataset.pilotScrollLabel) {
              box.removeAttribute("aria-label");
              delete box.dataset.pilotScrollLabel;
            }
          }
        });
      });
    }

    // Knowls and MathJax can insert content after the initial page load.
    new MutationObserver(schedule).observe(document.body, { childList: true, subtree: true });
    document.addEventListener("toggle", schedule, true);
    window.addEventListener("resize", schedule);
    document.fonts.ready.then(schedule);
    schedule();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
