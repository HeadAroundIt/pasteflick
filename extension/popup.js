const pastePrefHint = document.getElementById("paste-pref-hint");
const folderPathEl = document.getElementById("folder-path");
const folderPick = document.getElementById("folder-pick");
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
const params = new URLSearchParams(location.search);
const embedded = params.get("settings") === "1" || window !== window.top;

let currentDest = "clipboard";
let currentFormat = "md";
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

function closeEmbedded() {
  if (window === window.top) return false;
  window.parent.postMessage({ source: "pasteflick-settings", type: "close" }, "*");
  return true;
}

function reportFrameHeight() {
  if (!embedded) return;
  const h = Math.ceil(document.documentElement.scrollHeight);
  window.parent.postMessage({ source: "pasteflick-settings", type: "height", height: h }, "*");
}

function showSettings() {
  viewHome.hidden = true;
  viewSettings.hidden = false;
  reportFrameHeight();
  requestAnimationFrame(reportFrameHeight);
  void refreshFolder();
}

function showHome() {
  if (closeEmbedded()) return;
  viewSettings.hidden = true;
  viewHome.hidden = false;
}

document.getElementById("add-browser").addEventListener("click", (event) => {
  event.preventDefault();
  chrome.tabs.create({ url: chrome.runtime.getURL("setup.html") });
});

document.getElementById("tip-kofi").addEventListener("click", (event) => {
  event.preventDefault();
  chrome.tabs.create({ url: "https://ko-fi.com/ryandunham" });
});

document.getElementById("open-settings").addEventListener("click", showSettings);
document.getElementById("back-home").addEventListener("click", showHome);

function readDest(data) {
  const dest = data && data[DEST_KEY];
  if (dest === "clipboard" || dest === "cursor" || dest === "file") return dest;
  return data && data[AUTOPASTE_KEY] ? "cursor" : "clipboard";
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
  pastePrefHint.textContent = pastePrefLabel(currentDest);

  const pasteOn = currentDest === "cursor";
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
  reportFrameHeight();
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
    if (!res.ok) {
      reportFrameHeight();
      return;
    }
    const data = await res.json();
    const dir = data && data.dir;
    if (dir) showFolder(dir);
  } catch (_) {
    /* overlay not running — default folder is used once it is */
  }
  reportFrameHeight();
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
  const el = document.getElementById("version");
  el.textContent = local;
  reportFrameHeight();
  try {
    const data = await updateStatus();
    const disk = data && data.version;
    if (disk && disk !== local) el.textContent = local + " · updating";
  } catch (_) {
    /* helper not up */
  }
}

if (embedded) {
  document.documentElement.classList.add("embedded");
  showSettings();
}
void showVersion();
void refreshDestination();
