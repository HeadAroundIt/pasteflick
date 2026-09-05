/**
 * Isolated-world bridge: popup ↔ MAIN extractor via window.postMessage.
 */

if (globalThis.__pasteflickBridge) {
  /* already attached in this isolated world */
} else {
globalThis.__pasteflickBridge = true;

const PAGE = "pasteflick-page";
const EXTENSION = "pasteflick-extension";
const LEGACY_PAGE = "pasteflick-page";

function fromPage(data) {
  return data && (data.source === PAGE || data.source === LEGACY_PAGE);
}

function ingestViaBackground(payload) {
  payload = payload || {};
  return new Promise((resolve) => {
    if (!chrome.runtime || !chrome.runtime.sendMessage) {
      resolve({
        ok: false,
        pasted: false,
        saved: false,
        path: "",
        destination: payload.destination || "",
      });
      return;
    }
    chrome.runtime.sendMessage({ type: "ingest", payload }, (res) => {
      const err = chrome.runtime.lastError;
      if (err || !res) {
        resolve({
          ok: false,
          pasted: false,
          saved: false,
          path: "",
          destination: payload.destination || "",
        });
        return;
      }
      resolve(res);
    });
  });
}

window.addEventListener("message", (event) => {
  if (event.source !== window) return;
  const data = event.data;
  if (!fromPage(data)) return;

  if (data.type === "open-settings") {
    toggleSettingsFrame();
    return;
  }
  if (data.type === "close-settings") {
    toggleSettingsFrame(false);
    return;
  }
  if (data.type === "save-file") {
    const payload = data.payload || {};
    if (!chrome.runtime || !chrome.runtime.sendMessage) {
      window.postMessage(
        {
          source: EXTENSION,
          type: "save-file-result",
          requestId: data.requestId,
          result: { ok: false },
        },
        "*",
      );
      return;
    }
    chrome.runtime.sendMessage(
      {
        type: "save-file",
        markdown: payload.markdown || "",
        title: payload.title || "transcript",
        format: "md",
      },
      (res) => {
        const err = chrome.runtime.lastError;
        window.postMessage(
          {
            source: EXTENSION,
            type: "save-file-result",
            requestId: data.requestId,
            result: err ? { ok: false } : res || { ok: false },
          },
          "*",
        );
      },
    );
    return;
  }
  if (data.type === "set-copy-extras") {
    if (chrome.storage && chrome.storage.local) {
      void chrome.storage.local.set({ copyExtras: !!data.copyExtras });
    }
    return;
  }
  if (data.type !== "ingest") return;
  void ingestViaBackground(data.payload).then((result) => {
    window.postMessage(
      {
        source: EXTENSION,
        type: "ingest-result",
        requestId: data.requestId,
        result,
      },
      "*",
    );
  });
});

function readDestination(data) {
  const dest = data && data.destination;
  if (dest === "clipboard" || dest === "cursor" || dest === "file") return dest;
  return data && data.autoPaste ? "cursor" : "clipboard";
}

function requestCapture(mode, extra) {
  extra = extra || {};
  const requestId = "sm-" + Math.random().toString(36).slice(2);
  return Promise.resolve()
    .then(() => {
      const needDest = !extra.destination;
      const needExtras = extra.copyExtras == null;
      if (!needDest && !needExtras) return extra;
      if (!chrome.storage || !chrome.storage.local) {
        if (needExtras) extra.copyExtras = false;
        return extra;
      }
      return chrome.storage.local
        .get(["destination", "fileFormat", "autoPaste", "copyExtras"])
        .then((data) => {
          if (needDest) {
            extra.destination = readDestination(data);
            extra.fileFormat = data.fileFormat === "pdf" ? "pdf" : "md";
            extra.autoPaste = extra.destination === "cursor";
          }
          if (needExtras) extra.copyExtras = data.copyExtras === true;
          return extra;
        });
    })
    .then((opts) => {
      extra = opts || extra;
      extra.destination = extra.destination || "clipboard";
      extra.fileFormat = extra.fileFormat === "pdf" ? "pdf" : "md";
      extra.autoPaste = extra.destination === "cursor";
      if (
        mode !== "select-view" &&
        mode !== "open" &&
        mode !== "open-from-pasteflick" &&
        extra.destination === "cursor"
      ) {
        extra.copyExtras = false;
      } else if (extra.copyExtras == null) extra.copyExtras = false;
      return new Promise((resolve, reject) => {
        const timer = setTimeout(() => {
          window.removeEventListener("message", onMessage);
          reject(new Error("Timed out talking to the page extractor"));
        }, 20000);

        function onMessage(event) {
          if (event.source !== window) return;
          const data = event.data;
          if (!fromPage(data)) return;
          if (data.requestId !== requestId) return;
          clearTimeout(timer);
          window.removeEventListener("message", onMessage);
          if (data.error) reject(new Error(data.error));
          else resolve(data.result);
        }

        window.addEventListener("message", onMessage);
        window.postMessage(
          {
            source: EXTENSION,
            requestId,
            mode: mode || "select-view",
            scrollMark: extra.scrollMark || null,
            target: extra.target || null,
            fragment: extra.fragment || null,
            marks: extra.marks || null,
            autoPaste: extra.autoPaste,
            destination: extra.destination,
            fileFormat: extra.fileFormat,
            copyExtras: extra.copyExtras === true,
          },
          "*",
        );
      }).then((result) => deliverFileIfNeeded(result, extra));
    });
}

function deliverFileIfNeeded(result, extra) {
  result = result || {};
  if (extra.destination !== "file" || result.saved || result.opened) {
    if (result.markdown) delete result.markdown;
    return result;
  }
  const markdown = result.markdown || "";
  delete result.markdown;
  if (!markdown || !chrome.runtime || !chrome.runtime.sendMessage) {
    result.note = result.note || "Start the PasteFlick overlay to save files.";
    return result;
  }
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(
      {
        type: "save-file",
        markdown,
        title: result.title || "transcript",
        format: extra.fileFormat,
      },
      (dl) => {
        const err = chrome.runtime.lastError;
        result.saved = !!(dl && dl.ok) && !err;
        if (result.saved) {
          result.path = dl.filename || "";
          result.note =
            extra.fileFormat === "pdf"
              ? "Overlay not running — saved Markdown instead of PDF"
              : "Saved with the browser";
        } else {
          result.note = "Start the PasteFlick overlay to save files.";
        }
        resolve(result);
      },
    );
  });
}

globalThis.PasteFlickCapture = requestCapture;
globalThis.PasteFlickCapture = requestCapture;

function markName(mark) {
  return mark && String(mark.name || "").trim() ? String(mark.name).trim() : "";
}

function activePasteFlick() {
  const api = globalThis.PasteFlick;
  if (!api || typeof api.getActive !== "function") return Promise.resolve(null);
  return Promise.resolve(api.getActive());
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (!msg || !msg.type) return false;

  if (msg.type === "ping") {
    sendResponse({ ok: true, pong: true });
    return false;
  }

  if (msg.type === "pasteflick-status") {
    const api = globalThis.PasteFlick;
    const pending = [
      activePasteFlick(),
      api && typeof api.getDraft === "function" ? Promise.resolve(api.getDraft()) : Promise.resolve(""),
    ];
    Promise.all(pending)
      .then(([mark, draft]) =>
        sendResponse({
          ok: true,
          hasMark: !!mark,
          mark: mark || null,
          name: markName(mark) || String(draft || "").trim(),
        }),
      )
      .catch((err) => sendResponse({ ok: false, error: err.message || String(err) }));
    return true;
  }

  if (msg.type === "pasteflick-rename") {
    const api = globalThis.PasteFlick;
    if (!api || typeof api.setName !== "function") {
      sendResponse({ ok: false, error: "PasteFlick is not ready." });
      return false;
    }
    Promise.resolve(api.setName(msg.name || ""))
      .then((result) => sendResponse({ ok: true, ...(result || {}) }))
      .catch((err) => sendResponse({ ok: false, error: err.message || String(err) }));
    return true;
  }

  if (msg.type !== "capture") return false;

  const mode = msg.mode || "selection";
  const needMark = mode === "from-pasteflick" || mode === "open-from-pasteflick";
  const pending = needMark
    ? activePasteFlick().then((mark) => {
        if (!mark) {
          throw new Error("No PasteFlick in this chat. Click the bookmark on the left of a message.");
        }
        return requestCapture(mode, { scrollMark: mark });
      })
    : requestCapture(mode);

  pending
    .then((result) => sendResponse({ ok: true, result }))
    .catch((err) => sendResponse({ ok: false, error: err.message || String(err) }));
  return true;
});

function keepWorker() {
  try {
    if (!chrome.runtime || !chrome.runtime.id) return;
    const port = chrome.runtime.connect({ name: "pasteflick" });
    port.onDisconnect.addListener(() => {
      setTimeout(keepWorker, 1200);
    });
  } catch (_) {
    setTimeout(keepWorker, 2000);
  }
}

keepWorker();

if (chrome.storage && chrome.storage.onChanged) {
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area !== "local" || !changes.copyExtras) return;
    window.postMessage(
      {
        source: EXTENSION,
        type: "copy-extras-changed",
        copyExtras: changes.copyExtras.newValue === true,
      },
      "*",
    );
  });
}

const SETTINGS_FRAME_ID = "pasteflick-settings-frame";

function closeSettingsFrame() {
  const el = document.getElementById(SETTINGS_FRAME_ID);
  if (el) el.remove();
}

function toggleSettingsFrame(open) {
  const existing = document.getElementById(SETTINGS_FRAME_ID);
  if (open === false || (open == null && existing)) {
    closeSettingsFrame();
    return;
  }
  if (existing) return;
  if (!chrome.runtime || !chrome.runtime.getURL) return;

  const wrap = document.createElement("div");
  wrap.id = SETTINGS_FRAME_ID;
  wrap.setAttribute("data-pasteflick", "settings-frame");
  wrap.style.cssText =
    "position:fixed;inset:0;z-index:2147483647;display:flex;align-items:center;justify-content:center;padding:24px;box-sizing:border-box;background:rgba(50,40,20,.22);";
  wrap.addEventListener("click", (event) => {
    if (event.target === wrap) closeSettingsFrame();
  });

  const frame = document.createElement("iframe");
  frame.title = "PasteFlick settings";
  frame.src = chrome.runtime.getURL("popup.html?settings=1");
  frame.style.cssText =
    "width:300px;height:0;visibility:hidden;border:0;border-radius:10px;background:transparent;box-shadow:0 12px 32px rgba(50,40,20,.18);";
  wrap.appendChild(frame);
  document.documentElement.appendChild(wrap);
}

window.addEventListener("message", (event) => {
  const data = event.data;
  if (!data || data.source !== "pasteflick-settings") return;
  if (data.type === "close") closeSettingsFrame();
  if (data.type === "height") {
    const wrap = document.getElementById(SETTINGS_FRAME_ID);
    const iframe = wrap && wrap.querySelector("iframe");
    if (!iframe) return;
    const cap = Math.max(200, Math.floor(window.innerHeight * 0.9));
    const next = Math.max(200, Math.min(Number(data.height) || 0, cap));
    iframe.style.height = next + "px";
    iframe.style.visibility = "visible";
  }
});
}

