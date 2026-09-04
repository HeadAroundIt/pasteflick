const OVERLAY = "http://127.0.0.1:8768";
const UPDATE_OVERLAY = "http://127.0.0.1:8769";
const CHAT_TAB_URLS = [
  "https://chatgpt.com/*",
  "https://chat.openai.com/*",
  "https://*.chatgpt.com/*",
];

let pickingSaveAs = false;
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

function normalizedPath(path) {
  return String(path || "").replace(/\\/g, "/").replace(/\/+$/, "").toLowerCase();
}

async function updateStatus() {
  for (const base of [OVERLAY, UPDATE_OVERLAY]) {
    try {
      const res = await fetch(base + "/api/update-status", { signal: AbortSignal.timeout(800) });
      if (res.ok) return await res.json();
    } catch (_) {
      /* try the next local helper */
    }
  }
  return null;
}

function loadedVersion() {
  return (chrome.runtime.getManifest().version || "").trim();
}

async function markLoadedVersion() {
  const version = loadedVersion();
  try {
    await chrome.action.setBadgeText({ text: "" });
    await chrome.action.setTitle({ title: "PasteFlick " + version });
  } catch (_) {
    /* toolbar title is best-effort */
  }
  try {
    await chrome.storage.local.set({ loadedVersion: version, loadedAt: Date.now() });
  } catch (_) {
    /* ignore */
  }
  return version;
}

async function refreshChatTabs() {
  try {
    const tabs = await chrome.tabs.query({ url: CHAT_TAB_URLS });
    await Promise.all(
      tabs.map((tab) => (tab.id ? chrome.tabs.reload(tab.id) : Promise.resolve())),
    );
  } catch (err) {
    console.warn("PasteFlick: could not refresh chat tabs", err);
  }
}

async function applyVersionChange(reason) {
  const previous = await chrome.storage.local.get("loadedVersion").catch(() => ({}));
  const version = await markLoadedVersion();
  const changed = !previous.loadedVersion || previous.loadedVersion !== version;
  if (reason === "install" || reason === "update" || changed) {
    console.info("PasteFlick " + version + " (" + (reason || "sync") + ")");
    await refreshChatTabs();
  }
}

chrome.runtime.onInstalled.addListener((details) => {
  void applyVersionChange(details.reason);
});

chrome.runtime.onStartup.addListener(() => {
  void markLoadedVersion();
  void reloadIfDiskNewer();
});

const UPDATE_ALARM = "pasteflick-update";

async function reloadIfDiskNewer() {
  try {
    const [data, info] = await Promise.all([updateStatus(), installInfo()]);
    const disk = String((data && data.version) || "").trim();
    const running = loadedVersion();
    const sameInstall =
      data &&
      info &&
      normalizedPath(data.extensionPath) &&
      normalizedPath(data.extensionPath) === normalizedPath(info.extensionPath);
    if (sameInstall && disk && running && disk !== running) {
      chrome.runtime.reload();
    }
  } catch (_) {
    /* helper not up yet */
  }
}

try {
  chrome.alarms.create(UPDATE_ALARM, { periodInMinutes: 30, delayInMinutes: 1 });
} catch (_) {
  /* alarms permission missing on an old load */
}

if (chrome.alarms && chrome.alarms.onAlarm) {
  chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm && alarm.name === UPDATE_ALARM) void reloadIfDiskNewer();
  });
}

void reloadIfDiskNewer();

function safeName(title) {
  const raw = String(title || "transcript").trim() || "transcript";
  const cleaned = raw.replace(/[^a-zA-Z0-9._-]+/g, " ").trim().slice(0, 80);
  return cleaned || "transcript";
}

function folderFromFilename(name) {
  const raw = String(name || "");
  const cut = Math.max(raw.lastIndexOf("\\"), raw.lastIndexOf("/"));
  return cut > 0 ? raw.slice(0, cut) : "";
}

async function rememberDir(dir) {
  try {
    const headers = await apiHeaders({ "Content-Type": "application/json" });
    const res = await fetch(OVERLAY + "/api/export-dir", {
      method: "POST",
      headers,
      body: JSON.stringify({ path: dir }),
    });
    const data = res.ok ? await res.json() : null;
    if (data && data.dir) return data.dir;
  } catch (_) {
    /* overlay not running — still return the picked path */
  }
  return dir;
}

function pickFolderSaveAs() {
  if (pickingSaveAs) return Promise.resolve({ ok: false, busy: true });
  pickingSaveAs = true;
  return new Promise((resolve) => {
    const finish = (result) => {
      pickingSaveAs = false;
      resolve(result);
    };
    chrome.downloads.download(
      {
        url: "data:text/plain;charset=utf-8,",
        filename: "PasteFlick.txt",
        saveAs: true,
        conflictAction: "uniquify",
      },
      (id) => {
        const err = chrome.runtime.lastError;
        if (err || !id) {
          finish({ ok: false });
          return;
        }

        const done = (dir) => {
          chrome.downloads.onChanged.removeListener(onChanged);
          chrome.downloads.removeFile(id, () => chrome.downloads.erase({ id }));
          if (!dir) {
            finish({ ok: false });
            return;
          }
          void rememberDir(dir).then((saved) => finish({ ok: true, dir: saved || dir }));
        };

        function onChanged(delta) {
          if (delta.id !== id) return;
          if (delta.state && delta.state.current === "interrupted") {
            done("");
            return;
          }
          if (!delta.state || delta.state.current !== "complete") return;
          chrome.downloads.search({ id }, (items) => {
            const filename = items && items[0] && items[0].filename;
            done(folderFromFilename(filename));
          });
        }

        chrome.downloads.onChanged.addListener(onChanged);
      },
    );
  });
}

async function ingestOverlay(payload) {
  payload = payload || {};
  const dest = payload.destination || "clipboard";
  try {
    const headers = await apiHeaders({ "Content-Type": "application/json" });
    const res = await fetch(OVERLAY + "/api/ingest", {
      method: "POST",
      headers,
      signal: AbortSignal.timeout(8000),
      body: JSON.stringify({
        title: payload.title || "",
        markdown: payload.markdown || "",
        url: payload.url || "",
        source: payload.source || "selection",
        partial: !!payload.partial,
        turn_count: payload.turn_count || 0,
        character_count: payload.character_count || (payload.markdown || "").length,
        copy_to_clipboard: false,
        auto_paste: dest === "cursor",
        save: dest === "file",
        destination: dest,
        format: dest === "file" ? payload.format || "md" : "md",
      }),
    });
    if (!res.ok) return { ok: false, pasted: false, saved: false, path: "", destination: dest };
    let data = {};
    try {
      data = await res.json();
    } catch (_) {
      data = {};
    }
    return {
      ok: true,
      pasted: !!data.pasted,
      saved: !!data.saved,
      path: data.path || "",
      destination: data.destination || dest,
    };
  } catch (_) {
    return { ok: false, pasted: false, saved: false, path: "", destination: dest };
  }
}

async function ingestFileOverlay(payload) {
  payload = payload || {};
  const dest = payload.destination || "clipboard";
  try {
    const headers = await apiHeaders({ "Content-Type": "application/json" });
    const res = await fetch(OVERLAY + "/api/ingest-file", {
      method: "POST",
      headers,
      signal: AbortSignal.timeout(30000),
      body: JSON.stringify({
        name: payload.name || "file",
        mime: payload.mime || "",
        data: payload.data || "",
        destination: dest,
      }),
    });
    if (!res.ok) {
      if (dest === "file") return downloadBytesFallback(payload);
      return { ok: false, pasted: false, saved: false, path: "", destination: dest };
    }
    let data = {};
    try {
      data = await res.json();
    } catch (_) {
      data = {};
    }
    return {
      ok: data.ok !== false,
      pasted: !!data.pasted,
      saved: !!data.saved,
      path: data.path || "",
      destination: data.destination || dest,
      overlay: true,
    };
  } catch (_) {
    if (dest === "file") return downloadBytesFallback(payload);
    return { ok: false, pasted: false, saved: false, path: "", destination: dest };
  }
}

function downloadBytesFallback(payload) {
  payload = payload || {};
  const rawName = String(payload.name || "file").replace(/[\\/]+/g, " ").trim() || "file";
  const name = "PasteFlick/Files/" + rawName;
  const mime = payload.mime || "application/octet-stream";
  const url = "data:" + mime + ";base64," + String(payload.data || "");
  return new Promise((resolve) => {
    chrome.downloads.download(
      {
        url,
        filename: name,
        saveAs: false,
        conflictAction: "uniquify",
      },
      (id) => {
        const err = chrome.runtime.lastError;
        resolve({
          ok: !err && !!id,
          saved: !err && !!id,
          pasted: false,
          path: name,
          destination: "file",
        });
      },
    );
  });
}

function arrayBufferToBase64(buf) {
  const bytes = new Uint8Array(buf);
  const chunk = 0x8000;
  let binary = "";
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}

async function fetchBytes(url) {
  const href = String(url || "");
  if (!href || (href.indexOf("https://") !== 0 && href.indexOf("http://") !== 0)) {
    return { ok: false, error: "Couldn't get that file." };
  }
  try {
    const res = await fetch(href, { credentials: "include" });
    if (!res.ok) return { ok: false, error: "Couldn't download that file." };
    const buf = await res.arrayBuffer();
    if (!buf.byteLength) return { ok: false, error: "That file was empty." };
    return {
      ok: true,
      data: arrayBufferToBase64(buf),
      mime: (res.headers.get("content-type") || "").split(";")[0].trim(),
    };
  } catch (err) {
    return { ok: false, error: (err && err.message) || "Couldn't download that file." };
  }
}

const downloadArm = { on: false, item: null, waiters: [] };

chrome.downloads.onCreated.addListener((item) => {
  if (!downloadArm.on || !item) return;
  const url = item.finalUrl || item.url || "";
  if (!url || url.indexOf("data:text/plain") === 0) return;
  downloadArm.on = false;
  downloadArm.item = { url: url, filename: item.filename || "", id: item.id };
  downloadArm.waiters.splice(0).forEach((fn) => fn(downloadArm.item));
});

function armDownload() {
  downloadArm.on = true;
  downloadArm.item = null;
  return { ok: true };
}

function awaitDownload() {
  if (downloadArm.item) return Promise.resolve(downloadArm.item);
  if (!downloadArm.on) return Promise.resolve(null);
  return new Promise((resolve) => {
    const timer = setTimeout(() => {
      downloadArm.on = false;
      resolve(null);
    }, 10000);
    downloadArm.waiters.push((item) => {
      clearTimeout(timer);
      resolve(item);
    });
  });
}

function forgetDownload(id) {
  if (!id) return;
  try {
    chrome.downloads.cancel(id, () => chrome.downloads.erase({ id: id }));
  } catch (_) {
    /* ignore */
  }
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && (msg.type === "pick-export-dir-saveas" || msg.type === "pick-export-dir")) {
    void pickFolderSaveAs().then(sendResponse);
    return true;
  }

  if (msg && msg.type === "ingest") {
    void ingestOverlay(msg.payload).then(sendResponse);
    return true;
  }

  if (msg && msg.type === "ingest-file") {
    void ingestFileOverlay(msg.payload).then(sendResponse);
    return true;
  }

  if (msg && msg.type === "fetch-bytes") {
    void fetchBytes(msg.url).then(sendResponse);
    return true;
  }

  if (msg && msg.type === "arm-download") {
    sendResponse(armDownload());
    return false;
  }

  if (msg && msg.type === "await-download") {
    void awaitDownload().then(sendResponse);
    return true;
  }

  if (msg && msg.type === "forget-download") {
    forgetDownload(msg.id);
    sendResponse({ ok: true });
    return false;
  }

  if (!msg || msg.type !== "save-file") return false;
  const markdown = String(msg.markdown || "");
  if (!markdown) {
    sendResponse({ ok: false, error: "Nothing to save" });
    return false;
  }
  const name = "PasteFlick/Exports/" + safeName(msg.title) + ".md";
  const url = "data:text/markdown;charset=utf-8," + encodeURIComponent(markdown);
  chrome.downloads.download(
    {
      url,
      filename: name,
      saveAs: true,
      conflictAction: "uniquify",
    },
    (id) => {
      const err = chrome.runtime.lastError;
      sendResponse({
        ok: !err && !!id,
        id: id || 0,
        filename: name,
        error: err ? err.message : "",
      });
    },
  );
  return true;
});
