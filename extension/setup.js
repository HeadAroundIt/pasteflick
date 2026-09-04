const pathEl = document.getElementById("path");
const copiedEl = document.getElementById("copied");

const fallbackWin = "%LOCALAPPDATA%\\PasteFlick\\extension";
const fallbackMac = "~/Library/Application Support/PasteFlick/extension";
const isMac = /Mac|iPhone|iPad/i.test(navigator.platform || navigator.userAgent);
const fallback = isMac ? fallbackMac : fallbackWin;

async function resolvePath() {
  try {
    const res = await fetch("install-info.json", { cache: "no-store" });
    if (!res.ok) throw new Error("missing");
    const info = await res.json();
    if (info && typeof info.extensionPath === "string" && info.extensionPath.trim()) {
      return info.extensionPath.trim();
    }
  } catch (_) {
    /* installer writes this file; repo copies may not have it yet */
  }
  return fallback;
}

async function init() {
  const path = await resolvePath();
  pathEl.textContent = path;

  document.getElementById("copy").onclick = async () => {
    try {
      await navigator.clipboard.writeText(pathEl.textContent.trim());
      copiedEl.textContent = "Copied";
    } catch (_) {
      copiedEl.textContent = "Select the path and copy it";
    }
  };
}

void init();
