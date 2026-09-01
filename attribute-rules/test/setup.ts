// @arcgis/core falls back to an in-process "worker" built on a DocumentFragment when
// no Worker exists (WorkerFallback.js). Node has neither, so expose just the three
// EventTarget methods that fallback consumes instead of pulling in a full DOM.
if (typeof globalThis.document === "undefined") {
  (globalThis as any).document = {
    createDocumentFragment: () => new EventTarget()
  };
}
