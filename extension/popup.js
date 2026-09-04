const statusEl = document.getElementById("status");
const selectViewBtn = document.getElementById("select-view");
const fullBtn = document.getElementById("full");
const fromMarkBtn = document.getElementById("from-pasteflick");
const openFromMarkBtn = document.getElementById("open-from-pasteflick");
const destCopy = document.getElementById("dest-copy");
const pastePrefHint = document.getElementById("paste-pref-hint");
const folderPathEl = document.getElementById("folder-path");
const folderPick = document.getElementById("folder-pick");
const autoPasteBtn = document.getElementById("auto-paste");
const autoPasteLock = document.getElementById("auto-paste-lock");
const viewHome = document.getElementById("view-home");
const viewSettings = document.getElementById("view-settings");
const destBtns = Array.from(document.querySelectorAll("[data-dest]"));
const formatBtns = Array.from(document.querySelectorAll("[data-format]"));
const OVERLAY = "http://127.0.0.1:8768";
const UPDATE_OVERLAY = "http://127.0.0.1:8769";
const DEST_KEY = "destination";
const FORMAT_KEY = "fileFormat";
const AUTOPASTE_KEY = "autoPaste";

let currentDest = "clipboard";
let currentFormat = "md";
let lastMarkName = "";
let installInfoPromise;

function installInfo() {
  if (!installInfoPromise) {
    installInfoPromise = fetch(chrome.runtime.getURL("install-info.json"), { cache: "no-store" })
      .then((res) => (res.ok ? res.json() : {}))
      .catch(() => ({}));
  }
  return installInfoPromise;
}

async function apiHeaders(extra) {
  const info = await installInfo();
  const headers = { ...(extra || {}) };
  if (info && info.apiToken) headers["X-PasteFlick-Token"] = info.apiToken;
  return headers;
}

async function updateStatus() {
  for (const base of [OVERLAY, UPDATE_OVERLAY]) {
    try {
      const res = await fetch(base + "/api/update-status", { signal: AbortSignal.timeout(500) });
      if (res.ok) return await res.json();
    } catch (_) {
      /* try the next local helper */
    }
  }
  return null;
}

function setStatus(text, kind) {
  statusEl.textContent = text;
  statusEl.className = kind || "";
}

function isChatGptUrl(url) {
  return /^https:\/\/(chatgpt\.com|chat\.openai\.com)\//i.test(url || "");
}

async function pingTab(tabId) {
  return chrome.tabs.sendMessage(tabId, { type: "ping" });
}

async function ensureScripts(tabId) {
  try {
    await pingTab(tabId);
    return;
  } catch (_) {
    // Content script missing — common right after install / before refresh.
  }

  await chrome.scripting.executeScript({
    target: { tabId },
    files: ["extractor.js"],
    world: "MAIN",
  });
  await chrome.scripting.executeScript({
    target: { tabId },
    files: ["pasteflick.js", "content.js"],
  });

  await new Promise((r) => setTimeout(r, 75));

  let lastErr;
  for (let i = 0; i < 8; i++) {
    try {
      await pingTab(tabId);
      return;
    } catch (err) {
      lastErr = err;
      await new Promise((r) => setTimeout(r, 100));
    }
  }
  throw lastErr || new Error("Couldn't reach the chat. Refresh the tab and try again.");
}

async function capture(tabId, mode) {
  return chrome.tabs.sendMessage(tabId, { type: "capture", mode });
}

function setBusy(busy) {
  selectViewBtn.disabled = busy;
  fullBtn.disabled = busy;
  if (busy) {
    fromMarkBtn.disabled = true;
    openFromMarkBtn.disabled = true;
  }
}

function markLabel(name) {
  const raw = String(name || "").trim();
  return raw || "PasteFlick";
}

async function run(mode) {
  setBusy(true);
  const destHintText =
    currentDest === "file" ? "Saving…" : currentDest === "cursor" ? "Flicking…" : "Copying…";
  setStatus(
    mode === "select-view" || mode === "open-from-pasteflick"
      ? "Opening…"
      : mode === "from-pasteflick"
        ? currentDest === "file"
          ? "Saving from PasteFlick…"
          : currentDest === "cursor"
            ? "Flicking from PasteFlick…"
            : "Copying from PasteFlick…"
        : destHintText,
  );

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.id) throw new Error("No active tab");
    const url = tab.url || "";
    if (!isChatGptUrl(url)) {
      throw new Error("Open a chat first.");
    }

    await ensureScripts(tab.id);
    const response = await capture(tab.id, mode);
    if (!response || !response.ok) {
      throw new Error((response && response.error) || "Capture failed");
    }
    const r = response.result || {};

    if (mode === "select-view" || mode === "open-from-pasteflick" || r.opened) {
      setStatus("Highlight, then copy.", "ok");
      window.close();
      return;
    }

    const bits = [];
    if (mode === "from-pasteflick" || r.source === "pasteflick") {
      bits.push("Copied from " + markLabel(lastMarkName));
    } else {
      bits.push(r.partial ? "Partial DOM copy" : "Full thread copied");
    }
    if (r.turn_count) bits.push(r.turn_count + " turns");
    bits.push((r.character_count || 0).toLocaleString() + " chars");
    if (r.clipped) bits.push("clipboard");
    if (r.pasted) bits.push("auto-pasted");
    if (r.saved) {
      const name = String(r.path || "").split(/[/\\]/).pop();
      bits.push(name ? "saved " + name : "saved");
    }
    if (r.overlay) bits.push("desktop overlay");
    if (r.note) bits.push(r.note);
    setStatus(bits.join(" · "), "ok");
  } catch (err) {
    let msg = err && err.message ? err.message : String(err);
    if (/Receiving end does not exist|Could not establish connection/i.test(msg)) {
      msg = "Refresh the tab, then try again.";
    }
    setStatus(msg, "err");
  } finally {
    setBusy(false);
    await refreshMarkStatus({ preserveStatus: true });
  }
}

async function activeChatTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.id || !isChatGptUrl(tab.url || "")) return null;
  return tab;
}

async function refreshMarkStatus(opts) {
  const preserveStatus = !!(opts && opts.preserveStatus);
  try {
    const tab = await activeChatTab();
    if (!tab) {
      fromMarkBtn.disabled = true;
      openFromMarkBtn.disabled = true;
      lastMarkName = "";
      if (!preserveStatus) setStatus("Open a chat.");
      return;
    }

    let res = null;
    try {
      res = await chrome.tabs.sendMessage(tab.id, { type: "pasteflick-status" });
    } catch (_) {
      fromMarkBtn.disabled = true;
      openFromMarkBtn.disabled = true;
      lastMarkName = "";
      if (!preserveStatus) setStatus("Click the bookmark on the left of a message.");
      return;
    }

    const has = !!(res && res.hasMark);
    const name = (res && res.name) || (res && res.mark && res.mark.name) || "";
    lastMarkName = String(name || "").trim();
    fromMarkBtn.disabled = !has;
    openFromMarkBtn.disabled = !has;
    if (!preserveStatus) {
      if (has) setStatus(markLabel(lastMarkName) + " ready.");
      else setStatus("Cards stay on the left of each message.");
    }
  } catch (_) {
    fromMarkBtn.disabled = true;
    openFromMarkBtn.disabled = true;
    lastMarkName = "";
    if (!preserveStatus) setStatus("Open a chat.");
  }
}

selectViewBtn.addEventListener("click", () => run("select-view"));
fullBtn.addEventListener("click", () => run("full"));
fromMarkBtn.addEventListener("click", () => run("from-pasteflick"));
openFromMarkBtn.addEventListener("click", () => run("open-from-pasteflick"));

document.getElementById("add-browser").addEventListener("click", (event) => {
  event.preventDefault();
  chrome.tabs.create({ url: chrome.runtime.getURL("setup.html") });
});

document.getElementById("tip-kofi").addEventListener("click", (event) => {
  event.preventDefault();
  chrome.tabs.create({ url: "https://ko-fi.com/ryandunham" });
});

document.getElementById("open-settings").addEventListener("click", () => {
  viewHome.hidden = true;
  viewSettings.hidden = false;
  void refreshFolder();
});

document.getElementById("back-home").addEventListener("click", () => {
  viewSettings.hidden = true;
  viewHome.hidden = false;
  void refreshMarkStatus();
});

function readDest(data) {
  const dest = data && data[DEST_KEY];
  if (dest === "clipboard" || dest === "cursor" || dest === "file") return dest;
  return data && data[AUTOPASTE_KEY] ? "cursor" : "clipboard";
}

function destLabel(dest, format) {
  if (dest === "cursor") return "Copies flick into the last app.";
  if (dest === "file") {
    return format === "pdf" ? "Copies save as PDF." : "Copies save as Markdown.";
  }
  return "Copies stay on the clipboard.";
}

function pastePrefLabel(dest) {
  if (dest === "cursor") return "On — copies also paste.";
  if (dest === "file") return "Off for File.";
  return "Stays on the clipboard.";
}

function shortPath(path) {
  const raw = String(path || "").replace(/\//g, "\\");
  if (!raw) return "Documents\\PasteFlick";
  const parts = raw.split("\\").filter(Boolean);
  if (parts.length <= 2) return raw;
  return parts.slice(-2).join("\\");
}

let pickingFolder = false;

function showFolder(path) {
  const line = shortPath(path);
  folderPathEl.textContent = line;
  folderPathEl.title = path || line;
  folderPick.title = path || line;
}

async function overlayReachable() {
  try {
    const res = await fetch(OVERLAY + "/api/health", { signal: AbortSignal.timeout(200) });
    return res.ok;
  } catch (_) {
    return false;
  }
}

async function pickFolderFromSettings() {
  if (await overlayReachable()) {
    try {
      const headers = await apiHeaders({ "Content-Type": "application/json" });
      const res = await fetch(OVERLAY + "/api/export-dir", {
        method: "POST",
        headers,
        body: "{}",
      });
      const data = res.ok ? await res.json() : null;
      if (data && data.dir) showFolder(data.dir);
    } catch (_) {
      /* popup closed when the folder window opened — one picker is already up */
    }
    return;
  }
  try {
    const res = await chrome.runtime.sendMessage({ type: "pick-export-dir-saveas" });
    if (chrome.runtime.lastError) return;
    if (res && res.dir) showFolder(res.dir);
  } catch (_) {
    /* no fallback picker */
  }
}

function setDestUi(dest, format) {
  currentDest = dest;
  currentFormat = format === "pdf" ? "pdf" : "md";
  destCopy.textContent = destLabel(currentDest, currentFormat).replace(/\.$/, "");
  pastePrefHint.textContent = pastePrefLabel(currentDest);

  const pasteOn = currentDest === "cursor";
  autoPasteBtn.classList.toggle("on", pasteOn);
  autoPasteBtn.setAttribute("aria-pressed", pasteOn ? "true" : "false");
  autoPasteBtn.title = pasteOn
    ? "Flick on — copies also paste"
    : "Flick off — copies stay on the clipboard";

  autoPasteLock.classList.toggle("on", pasteOn);
  autoPasteLock.setAttribute("aria-checked", pasteOn ? "true" : "false");

  const sendDest = currentDest === "file" ? "file" : "clipboard";
  destBtns.forEach((btn) => {
    const on = btn.getAttribute("data-dest") === sendDest;
    btn.classList.toggle("on", on);
    btn.setAttribute("aria-pressed", on ? "true" : "false");
  });
  formatBtns.forEach((btn) => {
    const on = btn.getAttribute("data-format") === currentFormat;
    btn.classList.toggle("on", on);
    btn.setAttribute("aria-pressed", on ? "true" : "false");
  });
}

async function persistDest(dest, format) {
  const nextDest = dest || currentDest;
  const nextFormat = format || currentFormat;
  await chrome.storage.local.set({
    [DEST_KEY]: nextDest,
    [FORMAT_KEY]: nextFormat,
    [AUTOPASTE_KEY]: nextDest === "cursor",
  });
  setDestUi(nextDest, nextFormat);
}

function toggleAutoPaste() {
  void persistDest(currentDest === "cursor" ? "clipboard" : "cursor", currentFormat);
}

async function refreshDestination() {
  try {
    const data = await chrome.storage.local.get([DEST_KEY, FORMAT_KEY, AUTOPASTE_KEY]);
    const dest = readDest(data);
    const format = data[FORMAT_KEY] === "pdf" ? "pdf" : "md";
    if (data[DEST_KEY] !== dest) {
      await persistDest(dest, format);
    } else {
      setDestUi(dest, format);
    }
  } catch (_) {
    setDestUi("clipboard", "md");
  }
  await refreshFolder();
}

async function refreshFolder() {
  showFolder("Documents\\PasteFlick");
  try {
    const res = await fetch(OVERLAY + "/api/export-settings");
    if (!res.ok) return;
    const data = await res.json();
    const dir = data && data.dir;
    if (dir) showFolder(dir);
  } catch (_) {
    /* overlay not running — default folder is used once it is */
  }
}

destBtns.forEach((btn) => {
  btn.addEventListener("click", () => {
    const picked = btn.getAttribute("data-dest");
    if (picked === "clipboard" && currentDest === "cursor") return;
    void persistDest(picked, currentFormat);
  });
});

formatBtns.forEach((btn) => {
  btn.addEventListener("click", () => {
    void persistDest(currentDest, btn.getAttribute("data-format"));
  });
});

autoPasteBtn.addEventListener("click", toggleAutoPaste);
autoPasteLock.addEventListener("click", toggleAutoPaste);

folderPick.addEventListener("click", () => {
  if (pickingFolder || folderPick.disabled) return;
  pickingFolder = true;
  folderPick.disabled = true;
  void pickFolderFromSettings().finally(() => {
    pickingFolder = false;
    folderPick.disabled = false;
  });
});

async function showVersion() {
  const local = chrome.runtime.getManifest().version || "";
  let line = "PasteFlick " + local;
  try {
    const data = await updateStatus();
    const disk = data && data.version;
    if (disk && disk !== local) line += " · updating";
  } catch (_) {
    /* helper not up */
  }
  document.getElementById("version").textContent = line;
}

void showVersion();
void refreshMarkStatus();
void refreshDestination();
