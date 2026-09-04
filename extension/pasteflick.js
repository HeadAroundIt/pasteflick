/**
 * Isolated-world PasteFlick: bookmarks select what the chip copies.
 */
(function () {
  const STORAGE_KEY = "pasteflicks";
  const DRAFT_KEY = "pasteflickDrafts";
  const HOST_ID = "pasteflick-dock-host";
  const LEGACY_HOST_ID = "pasteflick-dock-host";
  const PAGE = "pasteflick-page";
  const EXTENSION = "pasteflick-extension";
  const LEGACY_PAGE = "pasteflick-page";
  const TOOLTIP = "Start PasteFlick here.";
  const COPY_MESSAGE_TIP = "Copy this message.";
  const BOOKMARK_SVG =
    '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">' +
    '<path class="scrolllog-icon" fill="none" stroke="currentColor" stroke-width="1.75" ' +
    'stroke-linejoin="round" d="M7 3.75h10A1.25 1.25 0 0 1 18.25 5v16.25L12 17.5l-6.25 3.75V5A1.25 1.25 0 0 1 7 3.75z"/>' +
    "</svg>";
  const COPY_SVG =
    '<svg viewBox="0 0 24 24" width="13" height="13" aria-hidden="true">' +
    '<rect x="8" y="8" width="11" height="13" rx="2" fill="none" stroke="currentColor" stroke-width="1.75"/>' +
    '<path d="M5 16V5a2 2 0 0 1 2-2h9" fill="none" stroke="currentColor" stroke-width="1.75"/>' +
    "</svg>";
  const SEND_SVG =
    '<svg viewBox="0 0 24 24" width="13" height="13" aria-hidden="true">' +
    '<path d="M5 12h11" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>' +
    '<path d="M12 6l7 6-7 6" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>' +
    "</svg>";
  const SAVE_SVG =
    '<svg viewBox="0 0 24 24" width="13" height="13" aria-hidden="true">' +
    '<path d="M12 4v10" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>' +
    '<path d="M8 10l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>' +
    '<path d="M5 18h14" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>' +
    "</svg>";
  const CHECK_SVG =
    '<svg viewBox="0 0 24 24" width="13" height="13" aria-hidden="true">' +
    '<path d="M5 12.5 9.5 17 19 7" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>' +
    "</svg>";
  const DEST_KEY = "destination";
  const FORMAT_KEY = "fileFormat";
  const AUTOPASTE_KEY = "autoPaste";
  const COPY_EXTRAS_KEY = "copyExtras";
  const EXT_MIME = {
    py: "text/x-python",
    js: "text/javascript",
    mjs: "text/javascript",
    ts: "text/typescript",
    tsx: "text/tsx",
    jsx: "text/jsx",
    json: "application/json",
    md: "text/markdown",
    html: "text/html",
    css: "text/css",
    csv: "text/csv",
    txt: "text/plain",
    xml: "application/xml",
    yaml: "text/yaml",
    yml: "text/yaml",
    pdf: "application/pdf",
    png: "image/png",
    jpg: "image/jpeg",
    jpeg: "image/jpeg",
    gif: "image/gif",
    webp: "image/webp",
    svg: "image/svg+xml",
    mp4: "video/mp4",
    webm: "video/webm",
    wav: "audio/wav",
    mp3: "audio/mpeg",
    zip: "application/zip",
    docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  };
  const LANG_MIME = {
    python: "text/x-python",
    javascript: "text/javascript",
    typescript: "text/typescript",
    json: "application/json",
    html: "text/html",
    css: "text/css",
    markdown: "text/markdown",
    bash: "text/x-sh",
    shell: "text/x-sh",
    sh: "text/x-sh",
    sql: "application/sql",
    mermaid: "text/x-mermaid",
    flowchart: "text/x-mermaid",
    yaml: "text/yaml",
    xml: "application/xml",
    csv: "text/csv",
  };
  const BLOCK_SELECTOR = [
    "pre",
    "table",
    "figure",
    "img",
    "iframe",
    "[contenteditable]",
    "[class*='ProseMirror' i]",
    "[class*='cm-editor' i]",
    "[class*='cm-content' i]",
    "[class*='DocumentEditor' i]",
    "[class*='doc-editor' i]",
    "[class*='writing-block' i]",
    "[data-testid*='file' i]",
    "[data-testid*='attachment' i]",
    "[data-testid*='download' i]",
    "[data-testid*='canvas' i]",
    "[data-testid*='textdoc' i]",
    "[data-testid*='text-doc' i]",
    "[data-testid*='text_doc' i]",
    "[data-testid*='document' i]",
    "[data-testid*='image' i]",
    "[aria-label*='document' i]",
    "[aria-label*='canvas' i]",
    "[class*='mermaid' i]",
    "[data-testid*='mermaid' i]",
    "[data-testid*='diagram' i]",
    "[aria-label*='diagram' i]",
    "[aria-label*='flowchart' i]",
  ].join(",");

  const RAIL_CSS = `
    :host {
      position: absolute;
      top: 0;
      left: 0;
      width: 0;
      display: block;
      z-index: 2147483646;
      pointer-events: none;
      overflow-anchor: none;
      --well: color-mix(in srgb, #c9a66a 6%, #f7f7f5);
      --stroke: rgba(201, 166, 106, 0.22);
      --text: #5c4a2e;
      --paper: #e4d2ae;
      --ink: #171410;
      --chip: rgba(201, 166, 106, 0.4);
      --chip-hot: rgba(201, 166, 106, 0.55);
      --chip-label: rgba(201, 166, 106, 0.48);
      --rim: rgba(201, 166, 106, 0.22);
      --card: color-mix(in srgb, #c9a66a 8%, #f7f7f5);
      --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
      --ease-tap: cubic-bezier(0.32, 0.72, 0, 1);
    }
    [data-pasteflick="highlights"] {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      pointer-events: none;
    }
    [data-pasteflick="highlight"] {
      position: absolute;
      display: none;
      pointer-events: none;
      border-radius: 16px;
      border: 1.5px solid rgba(201, 166, 106, 0.7);
      box-shadow: 0 0 0 1px rgba(33, 28, 22, 0.35);
      opacity: 0;
      transform: scale(0.985);
      transition: opacity 220ms var(--ease-out), transform 280ms var(--ease-out);
    }
    [data-pasteflick="highlight"].is-on {
      opacity: 1;
      transform: none;
    }
    [data-pasteflick="rails"] {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      pointer-events: none;
    }
    [data-pasteflick="silo"] {
      position: absolute;
      pointer-events: none;
      overflow: visible;
      overflow-anchor: none;
      z-index: 1;
    }
    [data-pasteflick="stack"] {
      position: sticky;
      top: var(--stick-top, auto);
      left: 0;
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 8px;
      width: max-content;
      pointer-events: none;
      box-sizing: border-box;
    }
    [data-pasteflick="pin"] {
      position: absolute;
      display: flex;
      flex-direction: column;
      align-items: stretch;
      gap: 4px;
      width: max-content;
      max-width: 124px;
      padding: 5px 5px 4px;
      pointer-events: auto;
      isolation: isolate;
      color: var(--text);
      border-radius: 10px;
      background: var(--card);
      border: 1px solid var(--rim);
      box-shadow: 0 1px 3px rgba(50, 40, 20, 0.05);
      transition: background-color 280ms var(--ease-out), border-color 280ms var(--ease-out), box-shadow 280ms var(--ease-out);
    }
    [data-pasteflick="stack"] > [data-pasteflick="pin"] {
      position: relative;
      top: auto;
      left: auto;
      width: max-content;
      box-sizing: border-box;
    }
    [data-pasteflick="pin"][data-kind="thread"] {
      max-width: 148px;
    }
    [data-pasteflick="pin"][data-kind="message"] {
      padding: 3px;
      max-width: none;
      gap: 2px;
    }
    [data-pasteflick="silo"][data-role="thread"] {
      z-index: 50;
    }
    [data-pasteflick="stack"][data-role="thread"] {
      align-items: flex-start;
    }
    [data-pasteflick="pin"][data-kind="thread"].is-bound {
      box-shadow: 0 0 0 2px rgba(201, 166, 106, 0.5), 0 1px 3px rgba(50, 40, 20, 0.05);
    }
    [data-pasteflick="picks"] {
      position: absolute;
      left: calc(100% + 8px);
      top: 50%;
      display: flex;
      align-items: center;
      padding: 4px 6px 4px 8px;
      border-radius: 10px;
      background: var(--card);
      border: 1px solid var(--rim);
      box-shadow: 0 1px 3px rgba(50, 40, 20, 0.08);
      pointer-events: auto;
      transform: translateY(-50%);
      transform-origin: left center;
      animation: pasteflick-pop 320ms var(--ease-out);
      z-index: 6;
    }
    [data-pasteflick="picks"][hidden] {
      display: none;
    }
    [data-pasteflick="pick"] {
      appearance: none;
      width: 22px;
      height: 22px;
      margin: 0 0 0 -7px;
      padding: 0;
      display: grid;
      place-items: center;
      border: 1px solid rgba(201, 166, 106, 0.35);
      border-radius: 6px;
      background: var(--chip-hot);
      color: var(--ink);
      cursor: pointer;
      animation: pasteflick-pick-in 280ms var(--ease-out) both;
    }
    [data-pasteflick="pick"]:first-child {
      margin-left: 0;
    }
    [data-pasteflick="pick"] .scrolllog-icon {
      fill: currentColor;
    }
    [data-pasteflick="mark"] {
      position: relative;
    }
    [data-pasteflick="mark"].is-joinable:hover {
      transform: scale(1.08);
    }
    [data-pasteflick="mark"].is-joinable::after {
      content: "";
      position: absolute;
      right: -3px;
      top: -3px;
      width: 9px;
      height: 9px;
      border-radius: 50%;
      background:
        linear-gradient(var(--ink), var(--ink)) center / 6px 1.5px no-repeat,
        linear-gradient(var(--ink), var(--ink)) center / 1.5px 6px no-repeat,
        var(--paper);
      box-shadow: 0 0 0 2px var(--card);
      opacity: 0;
      transform: scale(0.6);
      pointer-events: none;
      transition: opacity 160ms var(--ease-out), transform 200ms var(--ease-out);
    }
    [data-pasteflick="mark"].is-joinable:hover::after {
      opacity: 1;
      transform: scale(1);
    }
    [data-pasteflick="mark"].is-active.is-multi {
      box-shadow: 0 0 0 2px rgba(201, 166, 106, 0.7);
    }
    @keyframes pasteflick-pop {
      from { opacity: 0; transform: translateY(-50%) scale(0.7); }
      to { opacity: 1; transform: translateY(-50%) scale(1); }
    }
    @keyframes pasteflick-pick-in {
      from { opacity: 0; transform: translateX(-8px) scale(0.6); }
      to { opacity: 1; transform: none; }
    }
    [data-pasteflick="pin"][data-kind="link"] {
      flex-direction: row;
      align-items: center;
      gap: 2px;
      width: max-content;
      max-width: none;
      padding: 2px;
      border-radius: 8px;
      background: color-mix(in srgb, #c9a66a 10%, #f7f7f5);
      border-color: rgba(201, 166, 106, 0.22);
      box-shadow: none;
    }
    [data-pasteflick="pin"][data-kind="link"] [data-pasteflick="actions"] {
      gap: 2px;
    }
    [data-pasteflick="pin"][data-kind="link"] [data-pasteflick="copy-block"],
    [data-pasteflick="pin"][data-kind="link"] [data-pasteflick="paste-block"],
    [data-pasteflick="pin"][data-kind="link"] [data-pasteflick="save-block"] {
      width: 18px;
      height: 18px;
      border-radius: 6px;
    }
    [data-pasteflick="pin"][data-kind="link"] svg {
      width: 11px;
      height: 11px;
    }
    [data-pasteflick="head"] {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 4px;
      min-width: 0;
    }
    [data-pasteflick="extras"] {
      appearance: none;
      position: relative;
      flex: none;
      width: 22px;
      height: 12px;
      margin: 0;
      padding: 0;
      border: 1px solid rgba(201, 166, 106, 0.28);
      border-radius: 6px;
      background: rgba(23, 20, 16, 0.22);
      cursor: pointer;
      box-shadow: inset 0 1px 0 rgba(244, 226, 180, 0.12);
      transition: background-color 240ms var(--ease-out), border-color 240ms var(--ease-out), filter 240ms var(--ease-out), transform 160ms var(--ease-tap);
    }
    [data-pasteflick="extras"].on {
      background: var(--chip);
      border-color: transparent;
    }
    [data-pasteflick="extras-thumb"] {
      position: absolute;
      top: 1px;
      left: 1px;
      width: 8px;
      height: 8px;
      border-radius: 4px;
      background: var(--paper);
      pointer-events: none;
      transition: left 280ms var(--ease-out), background-color 240ms var(--ease-out);
    }
    [data-pasteflick="extras"].on [data-pasteflick="extras-thumb"] {
      left: 11px;
      background: var(--ink);
    }
    [data-pasteflick="extras"]:hover {
      filter: brightness(1.08);
    }
    [data-pasteflick="extras"]:focus-visible {
      outline: 2px solid rgba(201, 166, 106, 0.7);
      outline-offset: 1px;
    }
    [data-pasteflick="kicker"] {
      min-width: 0;
      flex: 1;
      padding: 2px 6px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font: 650 10px/1.2 "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif;
      letter-spacing: -0.01em;
      color: var(--ink);
      text-shadow: none;
      border-radius: 6px;
      background: var(--chip-label);
      box-shadow: inset 0 1px 0 rgba(244, 226, 180, 0.35);
    }
    [data-pasteflick="pin"][data-kind="block"] [data-pasteflick="kicker"] {
      font-size: 9px;
      padding: 1px 5px;
    }
    [data-pasteflick="actions"] {
      display: flex;
      align-items: center;
      gap: 2px;
    }
    [data-pasteflick="copy-thread"],
    [data-pasteflick="paste-thread"],
    [data-pasteflick="save-thread"],
    [data-pasteflick="copy-message"],
    [data-pasteflick="paste-message"],
    [data-pasteflick="save-message"],
    [data-pasteflick="copy-block"],
    [data-pasteflick="paste-block"],
    [data-pasteflick="save-block"],
    [data-pasteflick="mark"] {
      appearance: none;
      width: 24px;
      height: 24px;
      margin: 0;
      padding: 0;
      flex: none;
      display: grid;
      place-items: center;
      border-radius: 7px;
      border: 1px solid transparent;
      background: var(--chip);
      color: var(--ink);
      cursor: pointer;
      filter: none;
      box-shadow: inset 0 1px 0 rgba(244, 226, 180, 0.35);
      transition: background-color 240ms var(--ease-out), color 240ms var(--ease-out), border-color 240ms var(--ease-out), box-shadow 240ms var(--ease-out), transform 160ms var(--ease-tap), filter 240ms var(--ease-out);
    }
    [data-pasteflick="mark"].is-active {
      background: var(--chip-hot);
      color: var(--ink);
    }
    [data-pasteflick="mark"].is-active .scrolllog-icon {
      fill: currentColor;
    }
    [data-pasteflick="copy-thread"].is-primary,
    [data-pasteflick="paste-thread"].is-primary,
    [data-pasteflick="copy-message"].is-primary,
    [data-pasteflick="paste-message"].is-primary,
    [data-pasteflick="copy-block"].is-primary,
    [data-pasteflick="paste-block"].is-primary {
      color: var(--ink);
      background: var(--chip);
      box-shadow: inset 0 1px 0 rgba(244, 226, 180, 0.35);
    }
    [data-pasteflick="label"] {
      position: absolute;
      left: 0;
      top: calc(100% + 2px);
      min-height: 1em;
      font: 600 10px/1.2 "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif;
      color: var(--ink);
      text-shadow: none;
      padding: 2px 6px;
      outline: none;
      white-space: nowrap;
      border-radius: 6px;
      background: var(--chip-label);
      box-shadow: inset 0 1px 0 rgba(244, 226, 180, 0.35);
    }
    [data-pasteflick="label"][hidden] {
      display: none;
    }
    [data-pasteflick="copy-thread"]:hover,
    [data-pasteflick="paste-thread"]:hover,
    [data-pasteflick="save-thread"]:hover,
    [data-pasteflick="copy-message"]:hover,
    [data-pasteflick="paste-message"]:hover,
    [data-pasteflick="save-message"]:hover,
    [data-pasteflick="copy-block"]:hover,
    [data-pasteflick="paste-block"]:hover,
    [data-pasteflick="save-block"]:hover,
    [data-pasteflick="mark"]:hover,
    [data-pasteflick="copy-thread"].is-primary:hover,
    [data-pasteflick="paste-thread"].is-primary:hover,
    [data-pasteflick="copy-message"].is-primary:hover,
    [data-pasteflick="paste-message"].is-primary:hover,
    [data-pasteflick="copy-block"].is-primary:hover,
    [data-pasteflick="paste-block"].is-primary:hover {
      color: var(--ink);
      background: var(--chip-hot);
    }
    [data-pasteflick="copy-thread"]:active,
    [data-pasteflick="paste-thread"]:active,
    [data-pasteflick="save-thread"]:active,
    [data-pasteflick="copy-message"]:active,
    [data-pasteflick="paste-message"]:active,
    [data-pasteflick="save-message"]:active,
    [data-pasteflick="copy-block"]:active,
    [data-pasteflick="paste-block"]:active,
    [data-pasteflick="save-block"]:active,
    [data-pasteflick="mark"]:active,
    [data-pasteflick="extras"]:active {
      transform: scale(0.94);
    }
    [data-pasteflick="copy-thread"].is-done,
    [data-pasteflick="paste-thread"].is-done,
    [data-pasteflick="save-thread"].is-done,
    [data-pasteflick="copy-message"].is-done,
    [data-pasteflick="paste-message"].is-done,
    [data-pasteflick="save-message"].is-done,
    [data-pasteflick="copy-block"].is-done,
    [data-pasteflick="paste-block"].is-done,
    [data-pasteflick="save-block"].is-done {
      color: var(--ink);
      background: var(--chip);
    }
    [data-pasteflick="copy-thread"] svg,
    [data-pasteflick="paste-thread"] svg,
    [data-pasteflick="save-thread"] svg,
    [data-pasteflick="copy-message"] svg,
    [data-pasteflick="paste-message"] svg,
    [data-pasteflick="save-message"] svg,
    [data-pasteflick="copy-block"] svg,
    [data-pasteflick="paste-block"] svg,
    [data-pasteflick="save-block"] svg,
    [data-pasteflick="mark"] svg {
      display: block;
    }
    [data-pasteflick="copy-thread"]:focus-visible,
    [data-pasteflick="paste-thread"]:focus-visible,
    [data-pasteflick="save-thread"]:focus-visible,
    [data-pasteflick="copy-message"]:focus-visible,
    [data-pasteflick="paste-message"]:focus-visible,
    [data-pasteflick="save-message"]:focus-visible,
    [data-pasteflick="copy-block"]:focus-visible,
    [data-pasteflick="paste-block"]:focus-visible,
    [data-pasteflick="save-block"]:focus-visible,
    [data-pasteflick="mark"]:focus-visible,
    [data-pasteflick="label"]:focus-visible {
      outline: 1px solid var(--paper);
      outline-offset: 2px;
    }
    @media (prefers-reduced-transparency: reduce) {
      [data-pasteflick="pin"],
      [data-pasteflick="pin"][data-kind="block"],
      [data-pasteflick="pin"][data-kind="link"] {
        background: #f7f7f5;
      }
    }
    [data-pasteflick="toast"] {
      position: fixed;
      right: 16px;
      bottom: 16px;
      max-width: min(360px, calc(100vw - 32px));
      padding: 8px 12px;
      border-radius: 10px;
      background: #211c16;
      color: #efe6d4;
      border: 1px solid rgba(201, 166, 106, 0.28);
      font: 600 12px/1.35 "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif;
      pointer-events: none;
      opacity: 0;
      transform: translateY(6px);
      transition: opacity 320ms var(--ease-out), transform 320ms var(--ease-out);
    }
    [data-pasteflick="toast"].is-on {
      opacity: 1;
      transform: none;
    }
    @media (prefers-reduced-motion: reduce) {
      [data-pasteflick="toast"],
      [data-pasteflick="pin"],
      [data-pasteflick="extras"],
      [data-pasteflick="extras-thumb"],
      [data-pasteflick="copy-thread"],
      [data-pasteflick="paste-thread"],
      [data-pasteflick="save-thread"],
      [data-pasteflick="copy-message"],
      [data-pasteflick="paste-message"],
      [data-pasteflick="save-message"],
      [data-pasteflick="copy-block"],
      [data-pasteflick="paste-block"],
      [data-pasteflick="save-block"],
      [data-pasteflick="mark"],
      [data-pasteflick="highlight"],
      [data-pasteflick="picks"],
      [data-pasteflick="pick"] {
        transition: none;
        animation: none;
      }
    }
  `;

  let scanTimer = null;
  let lastConvKey = null;
  let memory = {};
  let lastPrefs = { dest: "clipboard", format: "md" };
  let lastCopyExtras = true;

  function privateApi() {
    return globalThis.PasteFlickPrivate || null;
  }
  const doneTimers = new WeakMap();
  const pinByTarget = new WeakMap();
  const stackByOwner = new WeakMap();
  let placeTimer = 0;
  let stickTimer = 0;
  let scrollIdle = 0;
  let scrolling = false;
  let heldStick = 0;
  let heldSidebar = 8;
  let heldTitleLeft = NaN;
  let lastPickEl = null;
  const geometryObserver =
    typeof ResizeObserver === "function"
      ? new ResizeObserver(() => {
          schedulePlace();
        })
      : null;

  function holdNum(prev, next, slack) {
    if (Number.isFinite(prev) && Math.abs(next - prev) <= slack) return prev;
    return next;
  }

  function conversationKey() {
    const m = String(location.href || "").match(/\/c\/([a-zA-Z0-9-]+)/);
    return m ? "chatgpt:" + m[1] : "";
  }

  function storageSlot() {
    return conversationKey() || ":pending";
  }

  function canonicalRole(role) {
    const r = String(role || "").toLowerCase();
    if (r === "user") return "user";
    if (r === "assistant") return "assistant";
    return "";
  }

  function fingerprintText(text) {
    return String(text || "")
      .replace(/\u00a0/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase()
      .slice(0, 240);
  }

  function fingerprintsMatch(a, b) {
    if (!a || !b) return false;
    if (a === b) return true;
    const n = Math.min(80, a.length, b.length);
    if (n < 24) return false;
    return a.slice(0, n) === b.slice(0, n);
  }

  function messageTextForMark(el) {
    const clone = el.cloneNode(true);
    try {
      clone
        .querySelectorAll("[data-pasteflick], button, nav, [role='toolbar'], [role='menu']")
        .forEach((n) => n.remove());
    } catch (_) {
      /* ignore */
    }
    return String(clone.innerText || clone.textContent || "")
      .replace(/\u00a0/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function messageNodes() {
    const nodes = document.querySelectorAll("[data-message-author-role]");
    const out = [];
    nodes.forEach((el) => {
      if (!canonicalRole(el.getAttribute("data-message-author-role"))) return;
      out.push(el);
    });
    return out;
  }

  function resolvePasteFlickIndex(messages, mark) {
    if (!mark || !messages || !messages.length) return -1;

    const wantedId = String(mark.messageId || "").trim();
    if (wantedId && wantedId.length > 4) {
      const hits = [];
      for (let i = 0; i < messages.length; i++) {
        if (String(messages[i].id || "") === wantedId) hits.push(i);
      }
      if (hits.length === 1) return hits[0];
      if (hits.length > 1) return -1;
    }

    const fp = String(mark.fingerprint || "");
    if (!fp) return -1;

    const fpHits = [];
    for (let i = 0; i < messages.length; i++) {
      const rec = messages[i];
      const mf = rec.fingerprint || fingerprintText(rec.text || "");
      const roleOk = !mark.role || !rec.role || rec.role === mark.role;
      if (roleOk && fingerprintsMatch(fp, mf)) fpHits.push(i);
    }
    if (fpHits.length === 1) return fpHits[0];
    if (fpHits.length > 1 && Number.isInteger(mark.position)) {
      const atPos = fpHits.filter((i) => {
        const pos = messages[i].position;
        return pos === mark.position || i === mark.position;
      });
      if (atPos.length === 1) return atPos[0];
    }
    return -1;
  }

  function describeMessage(el, position, name) {
    return {
      messageId: el.getAttribute("data-message-id") || "",
      role: canonicalRole(el.getAttribute("data-message-author-role")),
      fingerprint: fingerprintText(messageTextForMark(el)),
      position: position,
      markedAt: Date.now(),
      name: String(name || "").trim().slice(0, 40),
    };
  }

  function sameMark(a, b) {
    if (!a || !b) return false;
    if (a.messageId && b.messageId && a.messageId === b.messageId) return true;
    return (
      !!a.fingerprint &&
      a.fingerprint === b.fingerprint &&
      a.role === b.role &&
      a.position === b.position
    );
  }

  function mimeFromName(name) {
    const m = String(name || "").toLowerCase().match(/\.([a-z0-9]{1,8})(?:\?|$)/);
    if (!m) return "";
    return EXT_MIME[m[1]] || "";
  }

  function mimeFromLang(lang) {
    const l = String(lang || "").trim().toLowerCase();
    if (!l) return "text/plain";
    return LANG_MIME[l] || "text/x-" + l.replace(/[^a-z0-9+.-]/g, "");
  }

  function filenameGuess(text) {
    const m = String(text || "").match(/([\w.\-() ]+\.[a-z0-9]{1,8})/i);
    return m ? m[1].trim() : "";
  }

  function absUrl(href) {
    const raw = String(href || "").trim();
    if (!raw || raw === "#" || /^javascript:/i.test(raw)) return "";
    try {
      return new URL(raw, location.href).href;
    } catch (_) {
      return raw;
    }
  }

  function hrefFromNode(node) {
    if (!node || node.nodeType !== 1) return "";
    const tag = node.tagName;
    if (tag === "A") {
      return absUrl(node.href || node.getAttribute("href") || "");
    }
    if (tag === "IMG" || tag === "SOURCE" || tag === "VIDEO") {
      return absUrl(
        node.currentSrc ||
          node.src ||
          node.getAttribute("src") ||
          node.getAttribute("data-src") ||
          "",
      );
    }
    const dl = node.getAttribute && node.getAttribute("download");
    if (dl && node.getAttribute("href")) return absUrl(node.getAttribute("href"));
    return "";
  }

  function fileHref(el) {
    if (!el) return "";
    const direct = hrefFromNode(el);
    if (direct) return direct;
    const inner =
      el.querySelector &&
      el.querySelector("a[href], a[download], img, source, video");
    if (inner) {
      const href = hrefFromNode(inner);
      if (href) return href;
    }
    const chip = downloadChipIn(el);
    if (chip && chip !== el) {
      const nested = fileHref(chip);
      if (nested) return nested;
    }
    const fileId =
      (el.getAttribute && (el.getAttribute("data-file-id") || el.getAttribute("data-id"))) || "";
    if (fileId && /^[a-zA-Z0-9_-]+$/.test(fileId)) {
      const p = privateApi();
      const path = p && p.fileDownloadPath && p.fileDownloadPath(fileId);
      return path ? absUrl(path) : "";
    }
    return "";
  }

  function compactFileShape(el) {
    try {
      return el.getBoundingClientRect().height <= 280;
    } catch (_) {
      return true;
    }
  }

  function fileAttrBlob(el) {
    return (
      String((el && el.getAttribute && el.getAttribute("data-testid")) || "") +
      " " +
      String((el && el.getAttribute && el.getAttribute("aria-label")) || "") +
      " " +
      String((el && el.getAttribute && el.getAttribute("title")) || "") +
      " " +
      String((el && el.className) || "")
    ).toLowerCase();
  }

  function hasFileAttr(el) {
    if (!el || el.nodeType !== 1) return false;
    const blob = fileAttrBlob(el);
    if (/textdoc|text-doc|text_doc|(^|[^a-z])canvas([^a-z]|$)/.test(blob)) return false;
    if (/file-attachment|file-preview|file-chip|file-card|file-row|file-citation/.test(blob)) return true;
    if (/(^|[\s:_-])file([\s:_-]|$)/.test(blob)) return true;
    if (/attachment/.test(blob) || /download/.test(blob)) return true;
    return false;
  }

  function looksLikeWebAddress(text) {
    const t = String(text || "").trim();
    if (!t) return false;
    if (/@/.test(t)) return true;
    if (/^(https?:\/\/|www\.)/i.test(t)) return true;
    const host = t.split(/[/?#]/)[0];
    if (isCodeFilename(host)) return false;
    return /\.(com|org|net|edu|io|gov|co|uk|dev|ai|app|info)(\b|\/|:|$)/i.test(t);
  }

  function looksLikeFilenameChip(el) {
    if (!el || el.nodeType !== 1) return false;
    if (isRealDocument(el)) return false;
    const tag = el.tagName;
    if (tag === "PRE" || tag === "TABLE" || tag === "IMG" || tag === "FIGURE" || tag === "IFRAME" || tag === "CODE") {
      return false;
    }
    if (tag === "A" && !el.hasAttribute("download")) return false;
    if (el.closest && el.closest("pre, table, code")) return false;
    if (!compactFileShape(el)) return false;
    const text = normalizePlain(el.innerText || el.textContent || "");
    if (!text || text.length > 160) return false;
    if (looksLikeWebAddress(text)) return false;
    const lines = text.split(/\n/).map((line) => line.trim()).filter(Boolean);
    if (!lines.length || lines.length > 4) return false;
    const name = filenameGuess(text);
    if (!name) return false;
    if (looksLikeWebAddress(name)) return false;
    const rest = text.replace(name, " ").replace(/\s+/g, " ").trim();
    return rest.length <= 24;
  }

  function isFileChip(el) {
    if (!el || el.nodeType !== 1) return false;
    if (isRealDocument(el)) return false;
    if (hasFileAttr(el) && compactFileShape(el)) return true;
    if (el.hasAttribute && el.hasAttribute("download")) return true;
    const aria = String(el.getAttribute("aria-label") || el.getAttribute("title") || "").toLowerCase();
    if (/\bdownload\b/.test(aria)) return true;
    const label = String(el.innerText || el.textContent || "").replace(/\s+/g, " ").trim();
    if (/^download$/i.test(label)) return true;
    return looksLikeFilenameChip(el);
  }

  function downloadChipIn(el) {
    if (!el) return null;
    if (isFileChip(el)) return el;
    if (!el.querySelector) return null;
    const labeled = el.querySelector(
      "[data-testid*='download' i], [data-testid*='file-attachment' i], [data-testid='file' i], [data-testid*='file-' i], a[download], [aria-label*='download' i]",
    );
    if (labeled) return labeled;
    const nodes = el.querySelectorAll("button, a, [role='button'], div, span, p");
    for (let i = 0; i < nodes.length && i < 48; i++) {
      const t = String(nodes[i].innerText || nodes[i].textContent || "").replace(/\s+/g, " ").trim();
      if (/^download$/i.test(t)) return nodes[i];
    }
    return null;
  }

  function isRealDocument(el) {
    if (!el || el.nodeType !== 1) return false;
    if (isCanvasHost(el) || isEditorSurface(el)) return true;
    if (
      looksLikeDocumentAttr(el) &&
      el.querySelector &&
      el.querySelector("[contenteditable], .ProseMirror, .cm-content, iframe")
    ) {
      return true;
    }
    return false;
  }

  function isFileTarget(el) {
    if (!el || el.nodeType !== 1) return false;
    if (isRealDocument(el)) return false;
    if (isInlineLink(el)) return false;
    const tag = el.tagName;
    if (tag === "PRE" || tag === "TABLE" || tag === "IMG" || tag === "FIGURE" || tag === "IFRAME") return false;
    if (isFileChip(el) || looksLikeFilenameChip(el)) return true;
    if (hasFileAttr(el) && compactFileShape(el)) return true;
    if (!downloadChipIn(el)) return false;
    return compactFileShape(el);
  }

  function linkHref(el) {
    if (!el) return "";
    const raw = String((el.getAttribute && el.getAttribute("href")) || el.href || "").trim();
    const text = normalizePlain((el.innerText || el.textContent || "").replace(/\s+/g, " "));
    if (raw && raw !== "#" && !/^javascript:/i.test(raw)) {
      if (/^mailto:/i.test(raw)) return raw;
      if (/^https?:/i.test(raw) || raw.indexOf("//") === 0) return absUrl(raw);
      if (/^www\./i.test(raw)) return absUrl("https://" + raw);
    }
    if (/^https?:\/\//i.test(text)) return text.split(/\s/)[0];
    if (/^www\./i.test(text)) return "https://" + text.split(/\s/)[0];
    if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(text)) return "mailto:" + text;
    return "";
  }

  function isInlineLink(el) {
    if (!el || el.nodeType !== 1 || el.tagName !== "A") return false;
    if (!el.closest("[data-message-author-role]")) return false;
    if (isComposer(el) || inTopChrome(el)) return false;
    if (el.closest("pre, nav, [role='navigation'], [role='toolbar'], [data-pasteflick]")) return false;
    if (el.hasAttribute("download")) return false;
    const href = linkHref(el);
    if (!href) return false;
    try {
      if (el.getBoundingClientRect().height > 72) return false;
    } catch (_) {
      /* keep the link */
    }
    return true;
  }

  function inlineLinks(messageEl) {
    if (!messageEl || !messageEl.querySelectorAll) return [];
    return Array.from(messageEl.querySelectorAll("a")).filter((el) => isInlineLink(el)).slice(0, 16);
  }

  function describeFileBlock(el) {
    const chip = downloadChipIn(el) || el;
    const text = normalizePlain(el.innerText || "");
    const name =
      filenameGuess((chip && chip.getAttribute && chip.getAttribute("download")) || "") ||
      filenameGuess(el.getAttribute("download") || "") ||
      filenameGuess(el.getAttribute("aria-label") || "") ||
      filenameGuess(
        (chip && chip.getAttribute && (chip.getAttribute("aria-label") || chip.getAttribute("title"))) || "",
      ) ||
      filenameGuess(text);
    return {
      kind: "file",
      type: mimeFromName(name) || "application/octet-stream",
      label: "file",
      title: name || "File",
      name: name || "file",
      href: fileHref(el) || fileHref(chip),
      body: name || "file",
    };
  }

  function isCodeFilename(name) {
    return /\.(py|pyw|pyx|js|mjs|cjs|ts|tsx|jsx|rs|go|java|kt|kts|c|cc|cpp|cxx|h|hpp|cs|rb|php|swift|scala|lua|r|sh|bash|zsh|fish|ksh|ps1|bat|cmd|sql|ipynb|json|yml|yaml|toml|xml|html|htm|css|scss|less|vue|svelte|wasm|lock)$/i.test(
      String(name || ""),
    );
  }

  function isProseDocument(fragment, el) {
    if (!fragment) return false;
    const kind = String(fragment.kind || "");
    if (kind === "code" || kind === "table" || kind === "diagram" || kind === "link" || kind === "image" || kind === "figure") {
      return false;
    }
    const name = fragment.name || fragment.title || "";
    if (isCodeFilename(name)) return false;
    if (/\.(pdf|png|jpe?g|gif|webp|svg|zip|docx|xlsx|pptx|mp3|mp4|wav|webm)$/i.test(name)) return false;
    if (/\.(md|markdown|txt|rst|text)$/i.test(name)) return true;
    const type = String(fragment.type || "");
    if (/^text\/markdown/i.test(type)) return true;
    if (fragment.kind === "document" || fragment.kind === "canvas") return true;
    return false;
  }

  function isBinaryAsset(fragment, el) {
    if (!fragment) return false;
    if (isProseDocument(fragment, el)) return false;
    if (el && isFileTarget(el)) return true;
    const kind = fragment.kind || "";
    if (kind === "document" || kind === "canvas" || kind === "code" || kind === "table" || kind === "diagram") {
      return false;
    }
    if (kind === "file" || kind === "image") return true;
    const type = String(fragment.type || "");
    if (/^image\//i.test(type)) return true;
    if (/^application\/pdf$/i.test(type)) return true;
    if (
      /\.(pdf|png|jpe?g|gif|webp|svg|zip|docx|xlsx|pptx|mp3|mp4|wav|webm)$/i.test(fragment.name || "")
    ) {
      return true;
    }
    return !!(el && fileHref(el) && kind === "block" && fragment.name);
  }

  function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const s = String(reader.result || "");
        const comma = s.indexOf(",");
        resolve(comma >= 0 ? s.slice(comma + 1) : s);
      };
      reader.onerror = () => reject(reader.error || new Error("Couldn't read that file."));
      reader.readAsDataURL(blob);
    });
  }

  async function ingestFileBytes(name, mime, data, dest) {
    dest = actionDest(dest);
    const payload = { name, mime, data, destination: dest };
    if (typeof chrome !== "undefined" && chrome.runtime && chrome.runtime.sendMessage) {
      return new Promise((resolve) => {
        chrome.runtime.sendMessage({ type: "ingest-file", payload }, (res) => {
          const err = chrome.runtime.lastError;
          if (err || !res) {
            resolve({ ok: false, pasted: false, saved: false, path: "", destination: dest });
            return;
          }
          resolve(res);
        });
      });
    }
    const res = await fetch("http://127.0.0.1:8768/api/ingest-file", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Couldn't send that file.");
    const dataRes = await res.json();
    return {
      ok: dataRes.ok !== false,
      pasted: !!dataRes.pasted,
      saved: !!dataRes.saved,
      path: dataRes.path || "",
      destination: dataRes.destination || dest,
      overlay: true,
    };
  }

  async function captureFile(el, fragment, dest) {
    dest = actionDest(dest);
    const nameHint = (fragment && (fragment.name || fragment.title)) || "file";
    const href = (fragment && fragment.href) || fileHref(el);
    const got = await loadFileBytes(el, href, nameHint, (fragment && fragment.type) || "");
    const packed = got && got.data ? got : await loadDocumentAsFile(el, fragment, nameHint);
    if (!packed || !packed.data) throw new Error("Couldn't get that file.");
    const result = await ingestFileBytes(packed.name || nameHint, packed.mime || "", packed.data, dest);
    if (dest === "clipboard") result.clipped = result.ok !== false;
    return result;
  }

  function runtimeSend(type, extra) {
    return new Promise((resolve) => {
      if (!chrome.runtime || !chrome.runtime.sendMessage) {
        resolve(null);
        return;
      }
      chrome.runtime.sendMessage(Object.assign({ type: type }, extra || {}), (res) => {
        if (chrome.runtime.lastError) {
          resolve(null);
          return;
        }
        resolve(res || null);
      });
    });
  }

  function findDownloadControl(el) {
    if (!el) return null;
    const labeled =
      (el.querySelector &&
        el.querySelector("[aria-label*='download' i], [data-testid*='download' i], a[download], [title*='download' i]")) ||
      downloadChipIn(el);
    if (labeled) return labeled;
    const nodes = el.querySelectorAll ? el.querySelectorAll("button, a, [role='button'], div, span, p") : [];
    for (let i = 0; i < nodes.length && i < 48; i++) {
      const t = String(nodes[i].getAttribute("aria-label") || nodes[i].innerText || nodes[i].textContent || "")
        .replace(/\s+/g, " ")
        .trim()
        .toLowerCase();
      if (t === "download" || /^download\b/.test(t)) return nodes[i];
    }
    return isFileChip(el) ? el : null;
  }

  async function loadByClickingDownload(el, nameHint, mimeHint) {
    const btn = findDownloadControl(el);
    if (!btn) return null;
    const armed = await runtimeSend("arm-download");
    if (!armed || !armed.ok) return null;
    try {
      btn.click();
    } catch (_) {
      return null;
    }
    const hit = await runtimeSend("await-download");
    if (!hit || !hit.url) return null;
    try {
      let blob = null;
      if (/^(blob:|data:)/i.test(hit.url)) {
        const res = await fetch(hit.url);
        blob = res.ok ? await res.blob() : null;
      } else {
        blob = await blobFromUrl(hit.url);
      }
      if (hit.id) void runtimeSend("forget-download", { id: hit.id });
      if (!blob || !blob.size) return null;
      if (blob.size > 40 * 1024 * 1024) throw new Error("That file is too big to send this way.");
      const name = String(hit.filename || "").split(/[/\\]/).pop() || nameHint;
      return { name, mime: blob.type || mimeHint, data: await blobToBase64(blob) };
    } catch (err) {
      if (hit.id) void runtimeSend("forget-download", { id: hit.id });
      throw err;
    }
  }

  function grabFileViaPage(el, nameHint, mimeHint) {
    return new Promise((resolve) => {
      if (!el || !el.setAttribute) {
        resolve(null);
        return;
      }
      const requestId = "grab-file-" + Date.now() + "-" + Math.random().toString(16).slice(2);
      el.setAttribute("data-pasteflick-file", requestId);
      const btn = findDownloadControl(el);
      if (btn && btn.setAttribute) btn.setAttribute("data-pasteflick-dl", requestId);
      const done = (result) => {
        try {
          el.removeAttribute("data-pasteflick-file");
          if (btn) btn.removeAttribute("data-pasteflick-dl");
        } catch (_) {
          /* ignore */
        }
        resolve(result);
      };
      const timer = setTimeout(() => {
        window.removeEventListener("message", onMsg);
        done(null);
      }, 12000);
      function onMsg(event) {
        if (event.source !== window) return;
        const data = event.data;
        if (!data || (data.source !== PAGE && data.source !== LEGACY_PAGE) || data.requestId !== requestId) return;
        window.removeEventListener("message", onMsg);
        clearTimeout(timer);
        const hit = data.result;
        if (!hit || (!hit.data && !hit.url)) {
          done(null);
          return;
        }
        if (hit.data) {
          done({
            name: hit.name || nameHint,
            mime: hit.mime || mimeHint,
            data: hit.data,
          });
          return;
        }
        void blobFromUrl(hit.url)
          .then(async (blob) => {
            if (!blob || !blob.size) {
              done(null);
              return;
            }
            if (blob.size > 40 * 1024 * 1024) throw new Error("That file is too big to send this way.");
            done({
              name: hit.name || nameHint,
              mime: blob.type || hit.mime || mimeHint,
              data: await blobToBase64(blob),
            });
          })
          .catch(() => done(null));
      }
      window.addEventListener("message", onMsg);
      window.postMessage(
        {
          source: EXTENSION,
          type: "grab-file",
          requestId: requestId,
          nameHint: nameHint || "",
        },
        "*",
      );
    });
  }

  function namesMatch(a, b) {
    const x = String(a || "").trim().toLowerCase();
    const y = String(b || "").trim().toLowerCase();
    if (!x || !y) return false;
    return x === y || x.indexOf(y) >= 0 || y.indexOf(x) >= 0;
  }

  function fetchBytesViaBackground(url) {
    return new Promise((resolve, reject) => {
      if (!chrome.runtime || !chrome.runtime.sendMessage) {
        reject(new Error("Couldn't get that file."));
        return;
      }
      chrome.runtime.sendMessage({ type: "fetch-bytes", url }, (res) => {
        const err = chrome.runtime.lastError;
        if (err || !res || !res.ok) {
          reject(new Error((res && res.error) || "Couldn't download that file."));
          return;
        }
        resolve({ data: res.data, mime: res.mime || "" });
      });
    });
  }

  async function blobFromUrl(url) {
    try {
      const res = await fetch(url, { credentials: "include" });
      if (res.ok) {
        const blob = await res.blob();
        if (blob && blob.size) return blob;
      }
    } catch (_) {
      /* cross-origin — try the extension background */
    }
    const via = await fetchBytesViaBackground(url);
    const bin = atob(via.data);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return new Blob([bytes], { type: via.mime || "application/octet-stream" });
  }

  async function loadFileBytes(el, href, nameHint, mimeHint) {
    if (href && /^(data:|blob:)/i.test(href)) {
      const res = await fetch(href, { credentials: "include" });
      if (!res.ok) throw new Error("Couldn't get that file.");
      const blob = await res.blob();
      if (!blob.size) throw new Error("That file was empty.");
      return {
        name: nameHint,
        mime: blob.type || mimeHint,
        data: await blobToBase64(blob),
      };
    }
    if (href && href.indexOf("/backend-api/") < 0 && /^https?:/i.test(href)) {
      try {
        const blob = await blobFromUrl(href);
        if (blob && blob.size && blob.type.indexOf("application/json") < 0) {
          return {
            name: nameHint,
            mime: blob.type || mimeHint,
            data: await blobToBase64(blob),
          };
        }
      } catch (_) {
        /* ChatGPT chips often have no usable href — try the file API */
      }
    }
    const p = privateApi();
    if (p && p.tryUnofficialFileBytes) {
      try {
        const fromApi = await p.tryUnofficialFileBytes(el, nameHint, mimeHint, {
          blobFromUrl: blobFromUrl,
          blobToBase64: blobToBase64,
        });
        if (fromApi && fromApi.data) return fromApi;
      } catch (_) {
        /* try the download chip */
      }
    }
    const fromPage = await grabFileViaPage(el, nameHint, mimeHint);
    if (fromPage && fromPage.data) return fromPage;
    const fromClick = await loadByClickingDownload(el, nameHint, mimeHint);
    if (fromClick && fromClick.data) return fromClick;
    return null;
  }

  function textToBase64(text) {
    const bytes = new TextEncoder().encode(text || "");
    let binary = "";
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
      binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
    }
    return btoa(binary);
  }

  function looksLikeChipLabel(text, nameHint) {
    const t = normalizePlain(text);
    if (!t) return true;
    const compact = t.replace(/\s+/g, " ");
    if (nameHint && compact.toLowerCase() === String(nameHint).replace(/\s+/g, " ").toLowerCase()) return true;
    if (compact.length < 96 && /^[\w.\-() ]+\.[a-z0-9]{1,8}(\s+download)?$/i.test(compact)) return true;
    return compact.length < 48 && /\bdownload\b/i.test(compact);
  }

  function fileNameForDoc(nameHint, title) {
    const raw = String(nameHint || title || "document").trim() || "document";
    if (/\.[a-z0-9]{1,8}$/i.test(raw)) return raw;
    return raw + ".md";
  }

  function nearbyDocumentText(el, nameHint) {
    const msg = el && el.closest && el.closest("[data-message-author-role]");
    const host = closestDocumentHost(el, msg || document.body);
    if (host) {
      const body = documentBody(host);
      if (body && !looksLikeChipLabel(body, nameHint)) return body;
    }
    const detached = detachedDocumentHosts();
    for (let i = 0; i < detached.length; i++) {
      const title = documentTitle(detached[i]);
      if (nameHint && namesMatch(title, nameHint)) {
        const body = documentBody(detached[i]);
        if (body && !looksLikeChipLabel(body, nameHint)) return body;
      }
    }
    if (detached.length === 1) {
      const body = documentBody(detached[0]);
      if (body && !looksLikeChipLabel(body, nameHint)) return body;
    }
    return "";
  }

  async function loadDocumentAsFile(el, fragment, nameHint) {
    let text = nearbyDocumentText(el, nameHint);
    let title = (fragment && (fragment.name || fragment.title)) || nameHint || "";
    if (!text || looksLikeChipLabel(text, nameHint)) {
      const p = privateApi();
      if (p && p.conversationPayload && p.textdocsFromConversation) {
        let payload = null;
        try {
          payload = await p.conversationPayload();
        } catch (_) {
          payload = null;
        }
        const docs = payload ? p.textdocsFromConversation(payload) : [];
        const match = p.namesMatch || namesMatch;
        const named = nameHint
          ? docs.filter((d) => match(d.title, nameHint) || match(d.title + ".md", nameHint))
          : [];
        const pick = named.length ? named[named.length - 1] : docs.length === 1 ? docs[0] : null;
        if (pick && pick.content) {
          text = pick.content;
          title = pick.title || title;
        }
      }
    }
    if (!text || looksLikeChipLabel(text, nameHint)) return null;
    const name = fileNameForDoc(nameHint, title);
    return {
      name: name,
      mime: mimeFromName(name) || "text/markdown",
      data: textToBase64(text),
      text: text,
    };
  }

  async function loadProseText(el, fragment) {
    const nameHint = (fragment && (fragment.name || fragment.title)) || "document";
    const href = (fragment && fragment.href) || fileHref(el);
    if (href && /^(data:|blob:)/i.test(href)) {
      try {
        const res = await fetch(href, { credentials: "include" });
        if (res.ok) {
          const text = await res.text();
          if (text && !looksLikeChipLabel(text, nameHint)) {
            return { text: text, name: fileNameForDoc(nameHint, nameHint) };
          }
        }
      } catch (_) {
        /* use the document text instead */
      }
    }
    return loadDocumentAsFile(el, fragment, nameHint);
  }

  function languageFromPre(pre) {
    const code = pre.querySelector("code") || pre;
    const cls = String((code && code.className) || pre.className || "");
    const fromClass = cls.match(/language-([a-z0-9+#._-]+)/i);
    if (fromClass) return fromClass[1];
    const wrap = pre.parentElement && pre.parentElement.parentElement;
    if (!wrap) return "";
    const nodes = wrap.querySelectorAll("span, div");
    for (let i = 0; i < nodes.length && i < 12; i++) {
      const t = String(nodes[i].textContent || "").trim().toLowerCase();
      if (!t || t.length > 24) continue;
      if (/copy|code|edit/.test(t)) continue;
      if (/^[a-z][a-z0-9+#._-]{0,23}$/.test(t)) return t;
    }
    return "";
  }

  function codeTextFromEl(el) {
    const pre = !el ? null : el.tagName === "PRE" ? el : el.closest && el.closest("pre");
    if (!pre) return normalizePlain((el && (el.innerText || el.textContent)) || "");
    return normalizePlain(((pre.querySelector && pre.querySelector("code")) || pre).innerText || "");
  }

  function tableToMarkdown(table) {
    const rows = [];
    table.querySelectorAll("tr").forEach((tr) => {
      const cells = [];
      tr.querySelectorAll("th,td").forEach((cell) => {
        cells.push(
          String(cell.innerText || "")
            .replace(/\u00a0/g, " ")
            .replace(/\|/g, "\\|")
            .replace(/\s+/g, " ")
            .trim(),
        );
      });
      if (cells.length) rows.push(cells);
    });
    if (!rows.length) return normalizePlain(table.innerText);
    const width = rows.reduce((n, r) => Math.max(n, r.length), 0);
    const padded = rows.map((r) => {
      const next = r.slice();
      while (next.length < width) next.push("");
      return next;
    });
    const header = padded[0];
    const lines = [
      "| " + header.join(" | ") + " |",
      "| " + header.map(() => "---").join(" | ") + " |",
    ];
    for (let i = 1; i < padded.length; i++) {
      lines.push("| " + padded[i].join(" | ") + " |");
    }
    return lines.join("\n");
  }

  function normalizePlain(text) {
    return String(text || "")
      .replace(/\u00a0/g, " ")
      .replace(/[ \t]+\n/g, "\n")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }

  function imageType(img) {
    const src = String((img.currentSrc || img.src || "") + " " + (img.getAttribute("srcset") || ""));
    if (/image\/png|\.png(?:\?|$)/i.test(src)) return "image/png";
    if (/image\/jpeg|\.jpe?g(?:\?|$)/i.test(src)) return "image/jpeg";
    if (/image\/gif|\.gif(?:\?|$)/i.test(src)) return "image/gif";
    if (/image\/webp|\.webp(?:\?|$)/i.test(src)) return "image/webp";
    if (/image\/svg|\.svg(?:\?|$)/i.test(src)) return "image/svg+xml";
    const mime = mimeFromName(src);
    return mime || "image/*";
  }

  function looksLikeDocumentAttr(el) {
    const testid = String(el.getAttribute("data-testid") || "").toLowerCase();
    const aria = String(el.getAttribute("aria-label") || "").toLowerCase();
    if (/textdoc|text-doc|text_doc|canvas/.test(testid)) return true;
    if (/(^|[^a-z])document/.test(testid)) return true;
    if (/document|canvas/.test(aria)) return true;
    return false;
  }

  function isEditorSurface(el) {
    if (!el) return false;
    if (el.getAttribute("contenteditable") === "true" || el.getAttribute("contenteditable") === "") {
      return true;
    }
    const cls = String(el.className || "");
    return /ProseMirror|cm-editor|cm-content|DocumentEditor|doc-editor|writing-block/i.test(cls);
  }

  function isCanvasHost(el) {
    const blob =
      String(el.getAttribute("data-testid") || "") +
      " " +
      String(el.getAttribute("aria-label") || "") +
      " " +
      String(el.className || "");
    return /canvas/i.test(blob);
  }

  function colorLuma(color) {
    const m = String(color || "").match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
    if (!m) return null;
    return 0.2126 * +m[1] + 0.7152 * +m[2] + 0.0722 * +m[3];
  }

  function isBigEnough(el, minH, minW) {
    try {
      const r = el.getBoundingClientRect();
      return r.height >= minH && r.width >= minW;
    } catch (_) {
      return false;
    }
  }

  function isLightDocumentCard(el) {
    try {
      if (!isBigEnough(el, 100, 160)) return false;
      const st = window.getComputedStyle(el);
      const luma = colorLuma(st.backgroundColor);
      if (luma == null || luma < 220) return false;
      const msg = el.closest("[data-message-author-role]");
      if (!msg || el === msg) return false;
      const msgLuma = colorLuma(window.getComputedStyle(msg).backgroundColor);
      if (msgLuma != null && luma - msgLuma < 40) return false;
      const text = String(el.innerText || "").trim();
      if (text.length < 8 && !el.querySelector("iframe, [contenteditable]")) return false;
      return true;
    } catch (_) {
      return false;
    }
  }

  function isChromeControl(el) {
    if (!el || !el.closest) return true;
    const tag = el.tagName;
    if (tag === "BUTTON" || tag === "A" || tag === "SVG" || tag === "INPUT" || tag === "TEXTAREA") {
      return true;
    }
    if (el.closest("[role='toolbar'], [role='menu'], [role='navigation'], nav")) return true;
    return false;
  }

  function isComposer(el) {
    if (!el || !el.closest) return false;
    return !!el.closest(
      "#prompt-textarea, [data-testid='prompt-textarea'], [data-testid*='composer' i], form",
    );
  }

  function isDiagramHost(el) {
    if (!el || el.nodeType !== 1) return false;
    const blob =
      String(el.getAttribute("data-testid") || "") +
      " " +
      String(el.getAttribute("aria-label") || "") +
      " " +
      String(el.className || "") +
      " " +
      String(el.getAttribute("id") || "");
    if (/mermaid|flowchart|diagram/i.test(blob)) return true;
    if (el.tagName === "PRE") {
      const lang = languageFromPre(el);
      if (/mermaid|flowchart/i.test(lang)) return true;
      const code = el.querySelector("code");
      if (code && /language-mermaid/i.test(String(code.className || ""))) return true;
    }
    if (el.querySelector && el.querySelector("code.language-mermaid, .mermaid")) return true;
    return false;
  }

  function mermaidBody(el) {
    const pre = el.tagName === "PRE" ? el : el.querySelector && el.querySelector("pre");
    if (pre) {
      const lang = languageFromPre(pre) || "mermaid";
      const raw = normalizePlain((pre.querySelector("code") || pre).innerText);
      if (raw) return "```" + lang + "\n" + raw + "\n```";
    }
    const code = el.querySelector && el.querySelector("code");
    if (code) {
      const raw = normalizePlain(code.innerText);
      if (
        raw &&
        /^(graph|flowchart|sequenceDiagram|classDiagram|stateDiagram|erDiagram|journey|gantt|pie|mindmap|gitGraph)/i.test(
          raw.trim(),
        )
      ) {
        return "```mermaid\n" + raw + "\n```";
      }
    }
    const text = normalizePlain(el.innerText || el.textContent || "");
    return text || "[flowchart]";
  }

  function isDocumentHost(el) {
    if (!el || el.nodeType !== 1) return false;
    const tag = el.tagName;
    if (tag === "PRE" || tag === "TABLE" || tag === "IMG" || tag === "CODE") return false;
    if (tag === "BUTTON" || tag === "A" || tag === "SVG" || tag === "INPUT" || tag === "TEXTAREA") {
      return false;
    }
    if (isChromeControl(el) || isComposer(el)) return false;
    if (tag === "IFRAME") return isBigEnough(el, 80, 120);
    if (looksLikeDocumentAttr(el)) return true;
    if (isEditorSurface(el)) return isBigEnough(el, 80, 120);
    return isLightDocumentCard(el);
  }

  function closestDocumentHost(el, root) {
    let n = el;
    while (n && n.nodeType === 1) {
      if (isDocumentHost(n)) return n;
      if (root && n === root) break;
      n = n.parentElement;
    }
    return null;
  }

  function textFromNode(node) {
    if (!node) return "";
    try {
      if (node.shadowRoot) {
        const t = normalizePlain(node.shadowRoot.textContent);
        if (t.length > 8) return t;
      }
    } catch (_) {
      /* ignore */
    }
    return normalizePlain(node.innerText || node.textContent || "");
  }

  function documentBody(el) {
    if (!el) return "";
    if (el.tagName === "IFRAME") {
      try {
        const doc = el.contentDocument;
        if (doc && doc.body) return normalizePlain(doc.body.innerText);
      } catch (_) {
        /* cross-origin */
      }
      return "";
    }
    const iframe = el.querySelector && el.querySelector("iframe");
    if (iframe) {
      const nested = documentBody(iframe);
      if (nested) return nested;
    }
    const edit =
      el.querySelector &&
      el.querySelector("[contenteditable], .ProseMirror, .cm-content, [role='textbox']");
    const fromEdit = textFromNode(edit);
    if (fromEdit.length >= 8) return fromEdit;
    return textFromNode(el);
  }

  function documentTitle(el) {
    const named =
      filenameGuess(el.getAttribute("aria-label") || "") ||
      filenameGuess(el.getAttribute("title") || "");
    if (named) return named;
    const heading =
      el.querySelector &&
      el.querySelector("h1, h2, h3, [data-testid*='title' i], [class*='filename' i]");
    if (heading) {
      const t = normalizePlain(heading.innerText).split("\n")[0].slice(0, 60);
      if (t) return t;
    }
    return "";
  }

  function describeBlock(el) {
    if (!el) return null;
    if (isInlineLink(el)) {
      const href = linkHref(el);
      const shown = normalizePlain(el.innerText || "") || href.replace(/^mailto:/i, "");
      return {
        kind: "link",
        type: "text/uri-list",
        label: "link",
        title: shown,
        name: "",
        href,
        body: href.replace(/^mailto:/i, ""),
      };
    }
    if (isFileTarget(el)) return describeFileBlock(el);
    if (isDocumentHost(el)) {
      const titleGuess = documentTitle(el);
      const body = documentBody(el);
      const kind = isCanvasHost(el) ? "canvas" : "document";
      return {
        kind,
        type: "text/markdown",
        label: kind,
        title: titleGuess || (kind === "canvas" ? "Canvas" : "Document"),
        name: titleGuess,
        body: body || (kind === "canvas" ? "[canvas]" : "[document]"),
      };
    }
    if (isDiagramHost(el) || (el.tagName === "SVG" && isDiagramHost(el.parentElement || el))) {
      const raw = mermaidBody(el);
      return {
        kind: "diagram",
        type: "text/x-mermaid",
        label: "flowchart",
        title: "Flowchart",
        name: "",
        body: raw,
      };
    }
    if (el.tagName === "PRE" || (el.closest && el.closest("pre") === el)) {
      const pre = el.tagName === "PRE" ? el : el.closest("pre");
      const lang = languageFromPre(pre);
      const raw = codeTextFromEl(pre);
      const fence = "```" + (lang || "") + "\n" + raw + "\n```";
      return {
        kind: "code",
        type: mimeFromLang(lang),
        label: lang ? lang + " code" : "code block",
        title: lang ? lang + " code" : "Code",
        name: "",
        body: fence,
        text: raw,
      };
    }
    if (el.tagName === "TABLE") {
      return {
        kind: "table",
        type: "text/markdown",
        label: "table",
        title: "Table",
        name: "",
        body: tableToMarkdown(el),
      };
    }
    if (el.tagName === "IMG") {
      const src = el.currentSrc || el.src || "";
      const alt = String(el.alt || "").trim();
      const type = imageType(el);
      const lines = [];
      if (alt) lines.push(alt);
      if (src) lines.push(src);
      lines.push("type: " + type);
      return {
        kind: "image",
        type,
        label: "image",
        title: alt || "Image",
        name: filenameGuess(src) || filenameGuess(alt),
        href: absUrl(src),
        body: lines.join("\n"),
      };
    }
    if (el.tagName === "FIGURE") {
      const img = el.querySelector("img");
      if (img) return describeBlock(img);
      return {
        kind: "figure",
        type: "text/plain",
        label: "figure",
        title: "Figure",
        name: "",
        body: normalizePlain(el.innerText),
      };
    }

    const text = normalizePlain(el.innerText);
    const name = filenameGuess(text) || filenameGuess(el.getAttribute("download") || "");
    const type = mimeFromName(name) || "unknown";
    const testid = String(el.getAttribute("data-testid") || "").toLowerCase();
    let kind = "block";
    if (/canvas/.test(testid)) kind = "canvas";
    else if (/textdoc|text-doc|text_doc|document/.test(testid)) kind = "document";
    else if (/file|attachment|download/.test(testid)) kind = "file";
    else if (/image/.test(testid)) kind = "image";
    const title =
      name ||
      (kind === "file" ? "File" : kind === "canvas" ? "Canvas" : kind === "document" ? "Document" : "Block");
    if (kind === "document" || kind === "canvas") {
      const body = documentBody(el) || text;
      return {
        kind,
        type: "text/markdown",
        label: kind,
        title,
        name: name || title,
        body: body || "[" + kind + "]",
      };
    }
    const bodyLines = [];
    if (name) bodyLines.push(name);
    bodyLines.push("type: " + type);
    if (text && text !== name) bodyLines.push("", text);
    return {
      kind,
      type,
      label: type !== "unknown" ? kind + " · " + type : kind,
      title,
      name,
      href: fileHref(el),
      body: bodyLines.join("\n"),
    };
  }

  function isIgnorableBlock(el, messageEl) {
    if (!el || el.nodeType !== 1) return true;
    if (el.closest("[data-pasteflick]")) return true;
    if (messageEl && !messageEl.contains(el)) return true;
    if (isFileTarget(el) || isFileChip(el)) return false;
    const docHost = closestDocumentHost(el, messageEl);
    if (docHost && docHost !== el) return true;
    if (isDocumentHost(el) || looksLikeDocumentAttr(el)) return false;
    if (isDiagramHost(el)) return false;
    if (el.tagName === "IMG") {
      const w = el.naturalWidth || el.width || 0;
      const h = el.naturalHeight || el.height || 0;
      if ((w && w < 32) || (h && h < 32)) return true;
      if (el.closest("pre, button, svg, nav, [role='toolbar']")) return true;
    }
    if (el.tagName !== "PRE" && el.closest("pre")) return true;
    if (el.tagName !== "TABLE" && el.closest("table")) return true;
    if (el.tagName === "IMG" && el.closest("figure")) return true;
    if (el.hasAttribute("contenteditable")) {
      try {
        if (el.getBoundingClientRect().height < 80) return true;
      } catch (_) {
        return true;
      }
    }
    if (
      el.tagName !== "PRE" &&
      el.tagName !== "TABLE" &&
      el.tagName !== "IMG" &&
      el.tagName !== "FIGURE" &&
      el.tagName !== "IFRAME" &&
      el.querySelector("pre, table, figure")
    ) {
      return true;
    }
    return false;
  }

  function contentBlocks(messageEl) {
    const out = [];
    const add = (el) => {
      if (isIgnorableBlock(el, messageEl)) return;
      out.push(el);
    };
    messageEl.querySelectorAll(BLOCK_SELECTOR).forEach(add);
    messageEl
      .querySelectorAll(
        "[data-testid*='textdoc' i], [data-testid*='text-doc' i], [data-testid*='text_doc' i], [data-testid*='canvas' i], [data-testid*='document' i]",
      )
      .forEach((el) => {
        if (el.closest("[data-pasteflick]")) return;
        out.push(el);
      });
    messageEl.querySelectorAll("div, a, button, li, [data-testid]").forEach((el) => {
      if (el.closest("pre, table, [data-pasteflick]")) return;
      if (hasFileAttr(el) || looksLikeFilenameChip(el)) add(el);
    });
    messageEl.querySelectorAll("div, article, section").forEach((el) => {
      if (el.offsetHeight >= 100 && isLightDocumentCard(el)) add(el);
    });
    return outermost(out);
  }

  function leftoverAfterFiles(messageEl, fileEls) {
    let text = String((messageEl && messageEl.innerText) || "");
    (fileEls || []).forEach((el) => {
      const chunk = String((el && el.innerText) || "");
      if (chunk) text = text.split(chunk).join("\n");
    });
    text = text.replace(/^\s*(you|chatgpt|assistant|user)\s+/i, "");
    text = text.replace(/\bworked for\b[^\n]*/gi, "");
    text = text.replace(
      /\b(python|javascript|typescript|markdown|shell|bash|zsh|json|html|css|file|code|pdf|image|document|text)\b/gi,
      "",
    );
    return normalizePlain(text);
  }

  function shouldHideMessagePin(messageEl) {
    const blocks = contentBlocks(messageEl);
    const files = blocks.filter((el) => isFileTarget(el));
    if (blocks.some((el) => !isFileTarget(el))) return false;
    if (!files.length) return false;
    return leftoverAfterFiles(messageEl, files).length < 12;
  }

  function detachedDocumentHosts() {
    const out = [];
    const add = (el) => {
      if (!el || isDockHost(el)) return;
      if (el.closest("[data-message-author-role]")) return;
      if (isComposer(el) || isChromeControl(el)) return;
      if (el.closest("[class*='sidebar' i], #sidebar")) return;
      if (!isDocumentHost(el)) return;
      if (isIgnorableBlock(el, el)) return;
      out.push(el);
    };
    document
      .querySelectorAll(
        [
          "[data-testid*='canvas' i]",
          "[data-testid*='textdoc' i]",
          "[data-testid*='text-doc' i]",
          "[data-testid*='text_doc' i]",
          "[data-testid*='document' i]",
          "[aria-label*='canvas' i]",
          "[class*='DocumentEditor' i]",
          "[class*='doc-editor' i]",
        ].join(","),
      )
      .forEach(add);
    return outermost(out);
  }

  function outermost(els) {
    const unique = [];
    els.forEach((el) => {
      if (unique.indexOf(el) < 0) unique.push(el);
    });
    return unique.filter((el) => {
      const nestedIn = unique.filter((other) => other !== el && other.contains(el));
      if (nestedIn.some((parent) => isFileTarget(parent))) return false;
      if (
        nestedIn.length &&
        !(isFileTarget(el) && nestedIn.every((parent) => !isRealDocument(parent) && !isFileTarget(parent)))
      ) {
        return false;
      }
      const kids = unique.filter((other) => other !== el && el.contains(other));
      if (kids.some((kid) => isFileTarget(kid)) && !isRealDocument(el) && !isFileTarget(el)) {
        return false;
      }
      return true;
    });
  }

  function capture(mode, extra) {
    if (typeof globalThis.PasteFlickCapture === "function") {
      return globalThis.PasteFlickCapture(mode, extra);
    }
    const api = window.__transcriptCopy;
    if (api && mode === "chip" && typeof api.captureChip === "function") {
      return api.captureChip(extra);
    }
    if (api && mode === "single-message" && typeof api.captureMessage === "function") {
      return api.captureMessage(extra && extra.target, extra);
    }
    if (api && mode === "copy-fragment" && typeof api.captureFragment === "function") {
      return api.captureFragment(extra && extra.fragment, extra);
    }
    return Promise.reject(new Error("Copy is not ready. Refresh the tab."));
  }

  let toastTimer = null;
  function showToast(message, ok) {
    const el = layerRoot().querySelector('[data-pasteflick="toast"]');
    if (!el) return;
    el.textContent = message;
    el.style.color = ok === false ? "#e2b4ae" : "";
    el.classList.add("is-on");
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove("is-on"), 1800);
  }

  function actionDest(dest) {
    if (dest === "cursor") return "cursor";
    if (dest === "file") return "file";
    return "clipboard";
  }

  function captureOpts(dest) {
    dest = actionDest(dest);
    return {
      destination: dest,
      autoPaste: dest === "cursor",
      fileFormat: lastPrefs.format === "pdf" ? "pdf" : "md",
      copyExtras: dest === "cursor" ? false : lastCopyExtras,
    };
  }

  function actionOk(dest, result) {
    if (dest === "file") return !!(result && (result.saved || result.path));
    if (dest === "cursor") return !!(result && result.pasted);
    return !(result && result.clipped === false);
  }

  async function copyChip(dest, btn) {
    dest = actionDest(dest);
    if (dest === "file") await getDestination();
    try {
      const marks = await getActiveMarks();
      const result = await capture("chip", Object.assign({ marks }, captureOpts(dest)));
      const label =
        result && result.source === "pasteflick"
          ? "Bookmark"
          : result && result.source === "messages"
            ? "Messages"
            : "Thread";
      const ok = actionOk(dest, result);
      showToast(resultToast(label, result), ok);
      if (ok) markActionDone(btn, dest);
    } catch (err) {
      showToast((err && err.message) || String(err), false);
    }
  }

  async function copyMessage(el, dest, btn) {
    dest = actionDest(dest);
    if (dest === "file") await getDestination();
    const nodes = messageNodes();
    const position = nodes.indexOf(el);
    const target = describeMessage(el, position >= 0 ? position : 0);
    try {
      const result = await capture("single-message", Object.assign({ target }, captureOpts(dest)));
      const ok = actionOk(dest, result);
      showToast(resultToast("Message", result), ok);
      if (ok) markActionDone(btn, dest);
    } catch (err) {
      showToast((err && err.message) || String(err), false);
    }
  }

  async function copyBlock(el, btn, dest) {
    dest = actionDest(dest);
    if (dest === "file") await getDestination();
    const fragment = describeBlock(el);
    if (isProseDocument(fragment, el)) {
      try {
        const packed = await loadProseText(el, fragment);
        const text = packed && packed.text;
        if (!text) {
          showToast("Couldn't get that markdown.", false);
          return;
        }
        const frag = {
          kind: "document",
          type: "text/markdown",
          label: "markdown",
          title: packed.name || fragment.title || "Markdown",
          name: packed.name || fragment.name,
          body: text,
        };
        const result = await capture("copy-fragment", Object.assign({ fragment: frag }, captureOpts(dest)));
        const label = frag.title || "markdown";
        const ok = actionOk(dest, result);
        showToast(resultToast(label, result), ok);
        if (ok) markActionDone(btn, dest);
      } catch (err) {
        showToast((err && err.message) || String(err), false);
      }
      return;
    }
    if (isBinaryAsset(fragment, el)) {
      try {
        const result = await captureFile(el, fragment, dest);
        const label = (fragment && (fragment.name || fragment.title)) || "file";
        const ok = actionOk(dest, result);
        showToast(resultToast(label, result), ok);
        if (ok) markActionDone(btn, dest);
      } catch (err) {
        showToast((err && err.message) || String(err), false);
      }
      return;
    }
    if (fragment && fragment.kind === "code") {
      const raw = (fragment.text && String(fragment.text).trim()) || codeTextFromEl(el);
      if (!raw) {
        showToast("Nothing to copy in that block.", false);
        return;
      }
      const fenced = fragment.body || "```\n" + raw + "\n```";
      const frag = Object.assign({}, fragment, {
        type: dest === "file" ? "text/markdown" : "text/plain",
        body: dest === "file" ? fenced : raw,
      });
      try {
        const opts = Object.assign({}, captureOpts(dest));
        if (dest === "file") opts.fileFormat = "md";
        const result = await capture("copy-fragment", Object.assign({ fragment: frag }, opts));
        const label = dest === "file" ? "markdown" : fragment.title || "code";
        const ok = actionOk(dest, result);
        showToast(resultToast(label, result), ok);
        if (ok) markActionDone(btn, dest);
      } catch (err) {
        showToast((err && err.message) || String(err), false);
      }
      return;
    }
    if (!fragment || !fragment.body) {
      showToast("Nothing to copy in that block.", false);
      return;
    }
    try {
      const result = await capture("copy-fragment", Object.assign({ fragment }, captureOpts(dest)));
      const label = fragment.title || fragment.label || "block";
      const ok = actionOk(dest, result);
      showToast(resultToast(label, result), ok);
      if (ok) markActionDone(btn, dest);
    } catch (err) {
      showToast((err && err.message) || String(err), false);
    }
  }

  function setButtonContent(btn, svg, label) {
    btn.innerHTML = svg + (label ? '<span data-pasteflick="copy-label">' + label + "</span>" : "");
  }

  function extrasTip(on) {
    return on
      ? "Include title and notes with Copy and Save. Fling still sends what you see."
      : "Copy and Save just the text. Fling still sends what you see.";
  }

  function paintExtrasSwitch(btn, on) {
    if (!btn) return;
    btn.classList.toggle("on", !!on);
    btn.setAttribute("aria-checked", on ? "true" : "false");
    const tip = extrasTip(!!on);
    btn.title = tip;
    btn.setAttribute("aria-label", tip);
  }

  function applyExtrasVisuals(on) {
    lastCopyExtras = on !== false;
    const host = dockHost();
    const shadow = host && host.shadowRoot;
    if (!shadow) return;
    shadow.querySelectorAll('[data-pasteflick="extras"]').forEach((btn) => {
      paintExtrasSwitch(btn, lastCopyExtras);
    });
  }

  async function getCopyExtras() {
    const api = storageApi();
    if (!api) return lastCopyExtras;
    try {
      const data = await api.local.get(COPY_EXTRAS_KEY);
      lastCopyExtras = data[COPY_EXTRAS_KEY] !== false;
      return lastCopyExtras;
    } catch (_) {
      return lastCopyExtras;
    }
  }

  async function setCopyExtras(on) {
    lastCopyExtras = !!on;
    applyExtrasVisuals(lastCopyExtras);
    const api = storageApi();
    if (api) {
      try {
        await api.local.set({ [COPY_EXTRAS_KEY]: lastCopyExtras });
      } catch (_) {
        /* keep the in-memory switch */
      }
    }
  }

  function makeExtrasSwitch() {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.setAttribute("data-pasteflick", "extras");
    btn.setAttribute("role", "switch");
    const thumb = document.createElement("span");
    thumb.setAttribute("data-pasteflick", "extras-thumb");
    btn.appendChild(thumb);
    paintExtrasSwitch(btn, lastCopyExtras);
    btn.addEventListener("mousedown", (event) => {
      event.preventDefault();
      event.stopPropagation();
    });
    btn.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      void setCopyExtras(!lastCopyExtras);
    });
    return btn;
  }

  function makeHead(kickerText) {
    const head = document.createElement("div");
    head.setAttribute("data-pasteflick", "head");
    head.appendChild(makeKicker(kickerText));
    head.appendChild(makeExtrasSwitch());
    return head;
  }

  function makeKicker(text) {
    const el = document.createElement("span");
    el.setAttribute("data-pasteflick", "kicker");
    el.textContent = text;
    return el;
  }

  function makeActionButton(kind, dest, what, primary) {
    dest = actionDest(dest);
    const tip = dest === "cursor" ? pasteTip(what) : dest === "file" ? saveTip(what) : copyTip(what);
    const btn = makeIconButton(kind, tip, destGlyph(dest));
    btn.setAttribute("data-dest", dest);
    btn.setAttribute("data-action-what", what);
    if (primary) btn.classList.add("is-primary");
    return btn;
  }

  function makeIconButton(kind, title, svg, label) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.setAttribute("data-pasteflick", kind);
    btn.title = title;
    btn.setAttribute("aria-label", title);
    setButtonContent(btn, svg, label || "");
    btn.addEventListener("mousedown", (event) => {
      event.preventDefault();
      event.stopPropagation();
    });
    return btn;
  }

  function storageApi() {
    try {
      return typeof chrome !== "undefined" && chrome.storage && chrome.storage.local
        ? chrome.storage
        : null;
    } catch (_) {
      return null;
    }
  }

  async function readStore() {
    const api = storageApi();
    if (!api) return { ...memory };
    try {
      const data = await api.local.get(STORAGE_KEY);
      const map = data && data[STORAGE_KEY] && typeof data[STORAGE_KEY] === "object" ? data[STORAGE_KEY] : {};
      memory = { ...map };
      return { ...map };
    } catch (_) {
      return { ...memory };
    }
  }

  async function writeStore(map) {
    memory = { ...map };
    const api = storageApi();
    if (!api) return;
    await api.local.set({ [STORAGE_KEY]: map });
  }

  async function readDrafts() {
    const api = storageApi();
    if (!api) return {};
    try {
      const data = await api.local.get(DRAFT_KEY);
      const map = data && data[DRAFT_KEY] && typeof data[DRAFT_KEY] === "object" ? data[DRAFT_KEY] : {};
      return { ...map };
    } catch (_) {
      return {};
    }
  }

  async function writeDrafts(map) {
    const api = storageApi();
    if (!api) return;
    await api.local.set({ [DRAFT_KEY]: map });
  }

  async function getDraftName() {
    const drafts = await readDrafts();
    return String(drafts[storageSlot()] || drafts[":pending"] || "").trim().slice(0, 40);
  }

  async function setDraftName(name) {
    const drafts = await readDrafts();
    const key = storageSlot();
    const trimmed = String(name || "").trim().slice(0, 40);
    if (trimmed) drafts[key] = trimmed;
    else delete drafts[key];
    await writeDrafts(drafts);
  }

  function displayName(mark) {
    const named = mark && String(mark.name || "").trim();
    return named || "PasteFlick";
  }

  async function getDestination() {
    const api = storageApi();
    if (!api) {
      lastPrefs = { dest: "clipboard", format: "md" };
      return lastPrefs;
    }
    try {
      const data = await api.local.get([DEST_KEY, FORMAT_KEY, AUTOPASTE_KEY]);
      const dest =
        data[DEST_KEY] === "clipboard" || data[DEST_KEY] === "cursor" || data[DEST_KEY] === "file"
          ? data[DEST_KEY]
          : data[AUTOPASTE_KEY]
            ? "cursor"
            : "clipboard";
      lastPrefs = { dest, format: data[FORMAT_KEY] === "pdf" ? "pdf" : "md" };
      return lastPrefs;
    } catch (_) {
      lastPrefs = { dest: "clipboard", format: "md" };
      return lastPrefs;
    }
  }

  function destGlyph(dest) {
    if (dest === "cursor") return SEND_SVG;
    if (dest === "file") return SAVE_SVG;
    return COPY_SVG;
  }

  function blockCardLabel(fragment) {
    if (!fragment) return "Inside";
    if (fragment.kind === "code") {
      const lang = String(fragment.title || "").replace(/ code$/i, "").trim();
      if (!lang) return "Code";
      return lang.charAt(0).toUpperCase() + lang.slice(1);
    }
    if (fragment.kind === "document") return fragment.name || "Document";
    if (fragment.kind === "canvas") return fragment.name || "Canvas";
    if (fragment.kind === "diagram") return "Flowchart";
    if (fragment.name) return fragment.name;
    return fragment.title || "Inside";
  }

  function destDoneLabel(dest) {
    if (dest === "cursor") return "Pasted";
    if (dest === "file") return "Saved";
    return "Copied";
  }

  function copyTip(what) {
    if (/transcript/i.test(what)) return "Copy the transcript.";
    if (/bookmark/i.test(what)) return "Copy from the bookmark.";
    if (/selected/i.test(what)) return "Copy the selected messages.";
    return "Copy " + what + ".";
  }

  function pasteTip(what) {
    if (/transcript/i.test(what)) return "Fling the transcript.";
    if (/bookmark/i.test(what)) return "Fling from the bookmark.";
    if (/selected/i.test(what)) return "Fling the selected messages.";
    if (what === "this file") return "Send this file.";
    if (what === "this link") return "Send this link.";
    return "Fling what you see.";
  }

  function saveTip(what) {
    if (/transcript/i.test(what)) return "Save the transcript.";
    if (/bookmark/i.test(what)) return "Save from the bookmark.";
    if (/selected/i.test(what)) return "Save the selected messages.";
    return "Save " + what + ".";
  }

  function actionTip(dest, what) {
    dest = actionDest(dest);
    if (dest === "cursor") return pasteTip(what);
    if (dest === "file") return saveTip(what);
    return copyTip(what);
  }

  function restoreActionButton(btn) {
    if (!btn) return;
    const dest = actionDest(btn.getAttribute("data-dest"));
    const what = btn.getAttribute("data-action-what") || "this";
    const tip = actionTip(dest, what);
    setButtonContent(btn, destGlyph(dest), "");
    btn.title = tip;
    btn.setAttribute("aria-label", tip);
    btn.setAttribute("data-dest", dest);
  }

  function applyDestinationVisuals(dest, format) {
    lastPrefs = { dest: dest || "clipboard", format: format === "pdf" ? "pdf" : "md" };
  }

  function markActionDone(btn, dest) {
    if (!btn) return;
    const prev = doneTimers.get(btn);
    if (prev) clearTimeout(prev);
    const text = destDoneLabel(dest);
    btn.classList.add("is-done");
    setButtonContent(btn, CHECK_SVG, "");
    btn.title = text + ".";
    btn.setAttribute("aria-label", text + ".");
    const timer = setTimeout(() => {
      btn.classList.remove("is-done");
      restoreActionButton(btn);
      doneTimers.delete(btn);
    }, 1400);
    doneTimers.set(btn, timer);
  }

  function resultToast(copied, result) {
    if (result && result.clipped === false) return "Couldn't write the clipboard.";
    if (result && result.saved) {
      const name = String(result.path || "").split(/[/\\]/).pop();
      return name ? "Saved " + copied + " · " + name : "Saved " + copied + ".";
    }
    if (result && result.pasted) return copied + " copied and pasted.";
    if (result && result.destination === "cursor") {
      if (!result.overlay) return copied + " copied. Couldn't auto-paste.";
      return copied + " copied. Couldn't paste into the last app.";
    }
    if (result && result.destination === "file") {
      return (result.note && String(result.note)) || "Couldn't save.";
    }
    return copied + " copied.";
  }

  async function migratePending(newKey) {
    if (!newKey) return;
    const map = await readStore();
    if (map[":pending"] && !map[newKey]) {
      map[newKey] = map[":pending"];
      delete map[":pending"];
      await writeStore(map);
    } else if (map[":pending"] && map[newKey]) {
      delete map[":pending"];
      await writeStore(map);
    }
    const drafts = await readDrafts();
    if (drafts[":pending"] && !drafts[newKey]) {
      drafts[newKey] = drafts[":pending"];
      delete drafts[":pending"];
      await writeDrafts(drafts);
    } else if (drafts[":pending"] && drafts[newKey]) {
      delete drafts[":pending"];
      await writeDrafts(drafts);
    }
  }

  function asMarks(value) {
    if (!value) return [];
    if (Array.isArray(value)) return value.filter((m) => m && typeof m === "object");
    if (value.marks && Array.isArray(value.marks)) {
      return value.marks.filter((m) => m && typeof m === "object");
    }
    if (typeof value === "object" && (value.messageId || value.fingerprint)) return [value];
    return [];
  }

  async function getActiveMarks() {
    const key = storageSlot();
    const map = await readStore();
    let marks = asMarks(map[key]);
    if (!marks.length && key !== ":pending") marks = asMarks(map[":pending"]);
    return marks;
  }

  async function getActivePasteFlick() {
    const marks = await getActiveMarks();
    return marks[0] || null;
  }

  async function setActiveMarks(marks) {
    const key = storageSlot();
    const map = await readStore();
    const list = (marks || []).filter(Boolean);
    if (!list.length) {
      delete map[key];
      delete map[":pending"];
    } else if (list.length === 1) {
      map[key] = list[0];
      if (key !== ":pending") delete map[":pending"];
    } else {
      map[key] = { marks: list, name: namedMark(list[0]) || "" };
      if (key !== ":pending") delete map[":pending"];
    }
    await writeStore(map);
  }

  async function setActivePasteFlick(mark) {
    await setActiveMarks(mark ? [mark] : []);
  }

  async function setPasteFlickName(name) {
    const trimmed = String(name || "").trim().slice(0, 40);
    const marks = await getActiveMarks();
    if (marks.length) {
      marks.forEach((mark) => {
        mark.name = trimmed;
      });
      await setActiveMarks(marks);
    }
    await setDraftName(trimmed);
    await applyActiveVisuals();
    return { name: trimmed, hasMark: !!marks.length };
  }

  function conversationScroller() {
    const msg = document.querySelector("[data-message-author-role]");
    let node = msg ? msg.parentElement : null;
    let overflowParent = null;
    while (node && node !== document.body && node !== document.documentElement) {
      try {
        const st = window.getComputedStyle(node);
        if (/(auto|scroll|overlay)/.test(st.overflowY)) {
          if (!overflowParent) overflowParent = node;
          if (node.scrollHeight > node.clientHeight + 24) {
            return node;
          }
        }
      } catch (_) {
        /* keep walking */
      }
      node = node.parentElement;
    }
    return overflowParent || msg || document.scrollingElement || document.documentElement;
  }

  function scrollerRect(scroller) {
    if (
      scroller === document.scrollingElement ||
      scroller === document.documentElement ||
      scroller === document.body
    ) {
      return { top: 0, left: 0 };
    }
    return scroller.getBoundingClientRect();
  }

  function localBox(el, scroller) {
    const ar = el.getBoundingClientRect();
    const sr = scrollerRect(scroller);
    return {
      top: ar.top - sr.top + scroller.scrollTop,
      left: ar.left - sr.left + scroller.scrollLeft,
      bottom: ar.bottom - sr.top + scroller.scrollTop,
      right: ar.right - sr.left + scroller.scrollLeft,
      width: ar.width,
      height: ar.height,
    };
  }

  function lastTurnBottom(scroller) {
    const nodes = messageNodes();
    let bottom = 0;
    for (let i = 0; i < nodes.length; i++) {
      try {
        const box = localBox(turnRoot(nodes[i]), scroller);
        if (rectOk(box) && box.bottom > bottom) bottom = box.bottom;
      } catch (_) {
        /* skip a turn that's mid-layout */
      }
    }
    if (bottom >= 1) return Math.ceil(bottom);
    return Math.max(scroller.clientHeight || 0, 1);
  }

  function mountHost(host) {
    if (!host) return conversationScroller();
    const scroller = conversationScroller();
    try {
      if (window.getComputedStyle(scroller).position === "static") {
        scroller.style.position = "relative";
      }
    } catch (_) {
      /* leave the scroller as-is */
    }
    const tall = lastTurnBottom(scroller);
    host.style.position = "absolute";
    host.style.top = "0px";
    host.style.left = "0px";
    host.style.right = "auto";
    host.style.width = "0px";
    host.style.height = tall + "px";
    host.style.zIndex = "2147483646";
    host.style.overflow = "visible";
    host.style.pointerEvents = "none";
    host.style.overflowAnchor = "none";
    if (host.parentElement !== scroller) scroller.appendChild(host);
    const rails = host.shadowRoot && host.shadowRoot.querySelector('[data-pasteflick="rails"]');
    if (rails) {
      rails.style.height = tall + "px";
      rails.style.overflow = "visible";
      rails.style.overflowAnchor = "none";
    }
    return scroller;
  }

  function dockHost() {
    const host = document.getElementById(HOST_ID) || document.getElementById(LEGACY_HOST_ID);
    if (host && host.id !== HOST_ID) host.id = HOST_ID;
    return host;
  }

  function layerRoot() {
    let host = dockHost();
    if (host && host.shadowRoot) {
      mountHost(host);
      return host.shadowRoot;
    }
    host = document.createElement("div");
    host.id = HOST_ID;
    host.setAttribute("data-pasteflick", "host");
    const shadow = host.attachShadow({ mode: "open" });
    const style = document.createElement("style");
    style.textContent = RAIL_CSS;
    const highlights = document.createElement("div");
    highlights.setAttribute("data-pasteflick", "highlights");
    const rails = document.createElement("div");
    rails.setAttribute("data-pasteflick", "rails");
    const toast = document.createElement("div");
    toast.setAttribute("data-pasteflick", "toast");
    shadow.appendChild(style);
    shadow.appendChild(highlights);
    shadow.appendChild(rails);
    shadow.appendChild(toast);
    mountHost(host);
    return shadow;
  }

  function pageIsLight() {
    const html = document.documentElement;
    if (html.classList.contains("light")) return true;
    if (html.classList.contains("dark")) return false;
    const theme = html.getAttribute("data-theme") || html.getAttribute("data-color-scheme") || "";
    if (/light/i.test(theme)) return true;
    if (/dark/i.test(theme)) return false;
    const bg = getComputedStyle(document.body || html).backgroundColor || "";
    const m = bg.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/);
    if (m) {
      const lum = (0.2126 * Number(m[1]) + 0.7152 * Number(m[2]) + 0.0722 * Number(m[3])) / 255;
      return lum > 0.62;
    }
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches;
  }

  function syncScheme() {
    const host = dockHost();
    if (!host) return;
    host.setAttribute("data-scheme", "light");
  }

  function turnRoot(el) {
    if (!el || !el.closest) return el;
    return el.closest('[data-testid^="conversation-turn"]') || el.closest("article") || el;
  }

  function isLeftRailRect(r) {
    if (!r) return false;
    const vw = window.innerWidth || 800;
    const vh = window.innerHeight || 800;
    const mid = vw / 2;
    if (r.left > 80) return false;
    if (r.width < 40 || r.height < 80) return false;
    if (r.width > Math.min(420, vw * 0.38)) return false;
    if (r.right >= mid) return false;
    if (r.height < Math.min(160, vh * 0.25) && r.width > r.height * 1.4) return false;
    return true;
  }

  function sidebarRight(force) {
    const candidates = document.querySelectorAll("nav, aside, [class*='sidebar' i]");
    let best = 8;
    candidates.forEach((el) => {
      if (!el.getBoundingClientRect) return;
      const r = el.getBoundingClientRect();
      if (!isLeftRailRect(r)) return;
      if (r.right + 6 > best) best = r.right + 6;
    });
    heldSidebar = force ? best : holdNum(heldSidebar, best, 3);
    return heldSidebar;
  }

  function inTopChrome(el) {
    if (!el || !el.closest) return false;
    if (el.closest("header, [role='banner']")) return true;
    let node = el;
    for (let i = 0; i < 10 && node && node !== document.body; i++) {
      try {
        const st = window.getComputedStyle(node);
        if (st.position === "sticky" || st.position === "fixed") {
          const r = node.getBoundingClientRect();
          if (r.top <= 16 && r.height <= 180 && r.bottom < (window.innerHeight || 800) * 0.5) return true;
        }
      } catch (_) {
        /* ignore */
      }
      node = node.parentElement;
    }
    return false;
  }

  function headerBottom() {
    let bottom = 0;
    const bump = (el) => {
      if (!el || isDockHost(el)) return;
      try {
        const r = el.getBoundingClientRect();
        if (r.top > 40 || r.height < 18 || r.height > 280 || r.width < 80) return;
        if (r.bottom > bottom) bottom = r.bottom;
      } catch (_) {
        /* ignore */
      }
    };
    document.querySelectorAll("header, [role='banner']").forEach(bump);
    const labeled = document.querySelectorAll("[class*='sticky' i], [class*='top-0' i]");
    for (let i = 0; i < labeled.length && i < 48; i++) {
      const el = labeled[i];
      try {
        const st = window.getComputedStyle(el);
        if (st.position === "sticky" || st.position === "fixed") bump(el);
      } catch (_) {
        /* ignore */
      }
    }
    const x = Math.min((window.innerWidth || 800) - 80, Math.max(280, (window.innerWidth || 800) * 0.42));
    const stack = document.elementsFromPoint ? document.elementsFromPoint(x, 10) : [];
    for (let i = 0; i < stack.length && i < 16; i++) {
      const el = stack[i];
      if (!el || isDockHost(el)) continue;
      try {
        const st = window.getComputedStyle(el);
        if (st.position === "sticky" || st.position === "fixed") bump(el);
      } catch (_) {
        /* ignore */
      }
    }
    return bottom;
  }

  function headerStickTop(scroller) {
    const sr = scrollerRect(scroller);
    const hb = headerBottom();
    const raw = (hb > 8 ? hb + 6 : 16) - sr.top;
    heldStick = holdNum(heldStick, raw, 2);
    return Math.max(0, Math.round(heldStick));
  }

  function pinSilo(pin) {
    const p = pin && pin.parentElement;
    if (p && p.getAttribute("data-pasteflick") === "silo") return p;
    const stack = p;
    if (stack && stack.getAttribute("data-pasteflick") === "stack") {
      const silo = stack.parentElement;
      return silo && silo.getAttribute("data-pasteflick") === "silo" ? silo : null;
    }
    return null;
  }

  function stackOwnerForPin(pin) {
    const anchor = pin && pin._anchor;
    if (!anchor) return null;
    const message =
      (anchor.closest && anchor.closest("[data-message-author-role]")) ||
      (pin.getAttribute("data-kind") === "message" ? anchor : null);
    return (message && turnRoot(message)) || turnRoot(anchor) || anchor;
  }

  function watchGeometry(el) {
    if (!geometryObserver || !el || el._pasteflickObserved) return;
    try {
      geometryObserver.observe(el);
      el._pasteflickObserved = true;
    } catch (_) {
      /* ResizeObserver is a best-effort reflow signal */
    }
  }

  function stackForOwner(owner, rails) {
    if (!owner || !rails) return null;
    let stack = stackByOwner.get(owner);
    if (stack && stack.isConnected) return stack;
    const silo = document.createElement("div");
    silo.setAttribute("data-pasteflick", "silo");
    stack = document.createElement("div");
    stack.setAttribute("data-pasteflick", "stack");
    stack._owner = owner;
    silo._owner = owner;
    silo.appendChild(stack);
    rails.appendChild(silo);
    stackByOwner.set(owner, stack);
    watchGeometry(owner);
    return stack;
  }

  function dockPin(pin) {
    const rails = railsLayer();
    if (!pin || !rails) return pin;
    if (pin.getAttribute("data-kind") === "thread") return pin;
    if (pin.getAttribute("data-kind") === "link") {
      const old = pinSilo(pin);
      if (pin.parentElement !== rails) rails.appendChild(pin);
      if (old && !old.querySelector('[data-pasteflick="pin"]')) old.remove();
      return pin;
    }
    const owner = stackOwnerForPin(pin);
    const stack = stackForOwner(owner, rails);
    if (!stack) return pin;
    const oldStack =
      pin.parentElement && pin.parentElement.getAttribute("data-pasteflick") === "stack"
        ? pin.parentElement
        : null;
    if (pin.parentElement !== stack) stack.appendChild(pin);
    if (oldStack && oldStack !== stack && !oldStack.querySelector('[data-pasteflick="pin"]')) {
      const oldSilo = oldStack.parentElement;
      oldStack.remove();
      if (oldSilo) oldSilo.remove();
    }
    watchGeometry(pin._anchor);
    return pin;
  }

  function removePin(pin) {
    const silo = pinSilo(pin);
    const stack =
      pin.parentElement && pin.parentElement.getAttribute("data-pasteflick") === "stack"
        ? pin.parentElement
        : null;
    pin.remove();
    if (stack && stack.querySelector('[data-pasteflick="pin"]')) return;
    if (silo) silo.remove();
  }

  function setPinAway(pin, away) {
    if (!pin) return;
    if (away) {
      if (pin._away) return;
      pin._away = true;
      pin.style.visibility = "hidden";
      pin.style.pointerEvents = "none";
      pin.style.transform = "";
      pin.style.opacity = "";
      pin.style.position = "";
      pin.style.top = "";
      pin._stackShift = 0;
      pin._headerHidden = false;
      return;
    }
    if (!pin._away && pin.style.visibility !== "hidden") return;
    pin._away = false;
    pin.style.visibility = "visible";
    pin.style.pointerEvents = "auto";
  }

  function rectOk(r) {
    return !!(r && r.width >= 1 && r.height >= 1);
  }

  function paintPins() {
    const rails = railsLayer();
    if (!rails) return;
    rails.querySelectorAll('[data-pasteflick="pin"]').forEach((pin) => {
      if (pin.getAttribute("data-kind") !== "link") return;
      if (!Number.isFinite(pin._wantTop) || !Number.isFinite(pin._wantLeft)) return;
      const keep = (prev, next) =>
        Number.isFinite(prev) && Math.abs(next - prev) < 0.6 ? prev : Math.round(next);
      const top = keep(pin._paintTop, pin._wantTop);
      const left = keep(pin._paintLeft, pin._wantLeft);
      if (pin._paintTop !== top) {
        pin._paintTop = top;
        pin.style.top = top + "px";
      }
      if (pin._paintLeft !== left) {
        pin._paintLeft = left;
        pin.style.left = left + "px";
      }
    });
  }

  function placePin(pin, anchorEl, minLeft, scroller, relayout) {
    if (!pin || !anchorEl || !anchorEl.getBoundingClientRect) return;
    if (pin.getAttribute("data-kind") !== "link") return;
    scroller = scroller || conversationScroller();
    const ar = localBox(anchorEl, scroller);
    if (!rectOk(ar)) return;
    const pinW = pin.offsetWidth || 64;
    const pinH = pin.offsetHeight || 22;
    let left = ar.right + 4;
    const maxLeft = Math.max(8, (scroller.scrollWidth || window.innerWidth || 0) - pinW - 8);
    if (left > maxLeft) left = maxLeft;
    const top = ar.top + Math.max(0, (ar.height - pinH) / 2);
    if (
      !relayout &&
      Number.isFinite(pin._lockTop) &&
      Math.abs(top - pin._lockTop) < 8 &&
      Number.isFinite(pin._lockLeft) &&
      Math.abs(left - pin._lockLeft) < 8
    ) {
      pin._naturalTop = pin._lockTop;
      pin._naturalLeft = pin._lockLeft;
      pin._wantTop = pin._lockTop;
      pin._wantLeft = pin._lockLeft;
      pin._offscreen = false;
      return;
    }
    pin._naturalTop = top;
    pin._naturalLeft = left;
    pin._wantLeft = left;
    pin._wantTop = top;
    pin._lockTop = top;
    pin._lockLeft = left;
    pin._offscreen = false;
  }

  function layoutMessageStacks(rails, scroller) {
    const gap = 22;
    rails.querySelectorAll('[data-pasteflick="stack"]').forEach((stack) => {
      if (stack.getAttribute("data-role") === "thread") return;
      const silo = stack.parentElement;
      const owner = stack._owner;
      const pins = Array.from(stack.children).filter(
        (el) => el.getAttribute && el.getAttribute("data-pasteflick") === "pin",
      );
      if (!pins.length || !silo || !owner || !owner.isConnected) {
        if (silo) silo.remove();
        return;
      }
      pins.sort((a, b) => {
        const ak = a.getAttribute("data-kind") === "message" ? 0 : 1;
        const bk = b.getAttribute("data-kind") === "message" ? 0 : 1;
        if (ak !== bk) return ak - bk;
        let at = 0;
        let bt = 0;
        try {
          at = localBox(a._anchor, scroller).top;
          bt = localBox(b._anchor, scroller).top;
        } catch (_) {
          /* preserve DOM order when an anchor is between layouts */
        }
        return at - bt;
      });
      pins.forEach((pin) => {
        if (pin.parentElement !== stack || stack.lastElementChild !== pin) stack.appendChild(pin);
        pin._stackShift = 0;
        pin.style.transform = "";
        setPinAway(pin, false);
      });

      const messagePin = pins.find((pin) => pin.getAttribute("data-kind") === "message");
      const messageAnchor = messagePin && messagePin._anchor;
      const baseAnchor = messageAnchor || pins[0]._anchor || owner;
      let ownerBox;
      let baseBox;
      try {
        ownerBox = localBox(owner, scroller);
        baseBox = localBox(baseAnchor, scroller);
      } catch (_) {
        return;
      }
      if (!rectOk(ownerBox) || !rectOk(baseBox)) return;
      const edge = messageAnchor ? baseBox.left : ownerBox.left;
      const naturalTop = Math.round(baseBox.top + (messagePin ? 2 : 0));
      const stackW = Math.ceil(stack.offsetWidth || 90);
      const stackH = Math.ceil(stack.offsetHeight || 0);
      if (stackW < 2 || stackH < 2) return;
      const gutterRight = Math.round(edge - gap);
      const left = gutterRight - stackW;
      const ownerBottom = Math.max(ownerBox.bottom, naturalTop + stackH);
      const siloH = Math.max(stackH, Math.ceil(ownerBottom - naturalTop));

      silo.style.top = naturalTop + "px";
      silo.style.left = left + "px";
      silo.style.width = stackW + "px";
      silo.style.height = siloH + "px";
      stack._naturalTop = naturalTop;
      stack._ownerTop = ownerBox.top;
      stack._ownerBottom = ownerBox.bottom;
      stack._gutterRight = gutterRight;
      stack._stackH = stackH;

      pins.forEach((pin) => {
        const pinTop = naturalTop + pin.offsetTop;
        const pinLeft = left + stackW - pin.offsetWidth;
        pin._naturalTop = pinTop;
        pin._wantTop = pinTop;
        pin._lockTop = pinTop;
        pin._naturalLeft = pinLeft;
        pin._wantLeft = pinLeft;
        pin._lockLeft = pinLeft;
        pin._gutterRight = gutterRight;
        pin._ownerTop = ownerBox.top;
        pin._ownerBottom = ownerBox.bottom;
        pin._siloH = siloH;
        pin._offscreen = false;
      });
    });
  }

  function packHeaderStick() {
    const host = dockHost();
    const rails = host && host.shadowRoot && host.shadowRoot.querySelector('[data-pasteflick="rails"]');
    if (!rails) return;
    const scroller = conversationScroller();
    const sr = scrollerRect(scroller);
    const scrollTop = scroller.scrollTop || 0;
    const stickBase = headerStickTop(scroller);
    const gap = 10;
    const items = [];
    const parked = [];

    const threadStack = rails.querySelector('[data-pasteflick="stack"][data-role="thread"]');
    if (threadStack) {
      const silo = threadStack.parentElement;
      threadStack.style.setProperty("--stick-top", Math.max(0, Math.round(stickBase)) + "px");
      threadStack._stickTop = stickBase;
      threadStack.style.opacity = "";
      threadStack.style.pointerEvents = "";
      if (silo) silo.style.zIndex = "50";
      threadStack.querySelectorAll('[data-pasteflick="pin"]').forEach((pin) => {
        pin._stackPresent = true;
        pin._stickTop = stickBase;
        pin._stackShift = 0;
        pin._headerHidden = false;
        pin.style.opacity = "";
        pin.style.pointerEvents = "auto";
      });
    }

    rails.querySelectorAll('[data-pasteflick="stack"]').forEach((stack) => {
      if (stack.getAttribute("data-role") === "thread") return;
      const silo = stack.parentElement;
      if (!silo || !Number.isFinite(stack._naturalTop) || !Number.isFinite(stack._ownerBottom)) return;
      const box = stack.getBoundingClientRect();
      const w = Math.ceil(box.width || stack.offsetWidth || 0);
      const h = Math.ceil(stack._stackH || box.height || stack.offsetHeight || 0);
      if (w < 2 || h < 2) return;
      const left = Number.parseFloat(silo.style.left);
      if (!Number.isFinite(left)) return;
      items.push({
        stack,
        silo,
        h,
        left,
        right: left + w,
        naturalTop: stack._naturalTop,
        naturalView: sr.top + stack._naturalTop - scrollTop,
        ownerBottomView: sr.top + stack._ownerBottom - scrollTop,
      });
    });

    items.sort((a, b) => a.naturalTop - b.naturalTop);
    items.forEach((it) => {
      let stick = stickBase;
      parked.forEach((prev) => {
        const sameRail =
          it.left < prev.right - 1 ||
          (Number.isFinite(it.stack._gutterRight) &&
            Number.isFinite(prev.stack._gutterRight) &&
            Math.abs(it.stack._gutterRight - prev.stack._gutterRight) < 18);
        if (!sameRail || it.right <= prev.left + 1) return;
        stick = Math.max(stick, prev.stick + prev.h + gap);
      });

      const reached = it.naturalView <= sr.top + stick + 8;
      const fill = it.ownerBottomView > sr.top + stick + it.h + 2;
      const occupy = reached && fill;
      it.stack.style.setProperty("--stick-top", Math.max(0, Math.round(stick)) + "px");
      it.stack._stickTop = stick;
      it.silo.style.zIndex = occupy ? String(40 - parked.length) : "1";
      if (occupy) {
        parked.push({
          stack: it.stack,
          stick,
          h: it.h,
          left: it.left,
          right: it.right,
        });
      }

      const hidden = reached && !fill;
      it.stack.style.opacity = hidden ? "0" : "";
      it.stack.style.pointerEvents = hidden ? "none" : "";
      it.stack.querySelectorAll('[data-pasteflick="pin"]').forEach((pin) => {
        pin._stackPresent = occupy;
        pin._stickTop = stick;
        pin._stackShift = 0;
        pin._headerHidden = hidden;
        pin.style.opacity = hidden ? "0" : "";
        pin.style.pointerEvents = hidden ? "none" : "auto";
      });
    });
  }

  function scheduleStickPack() {
    if (stickTimer) return;
    stickTimer = requestAnimationFrame(() => {
      stickTimer = 0;
      packHeaderStick();
    });
  }

  function paintHighlight(highlight, el, scroller) {
    if (!highlight || !el) return;
    const rect = localBox(turnRoot(el), scroller || conversationScroller());
    highlight.style.top = Math.round(rect.top - 4) + "px";
    highlight.style.left = Math.round(rect.left - 4) + "px";
    highlight.style.width = Math.round(rect.width + 8) + "px";
    highlight.style.height = Math.round(rect.height + 8) + "px";
  }

  function placeAllPins(relayout) {
    const root = layerRoot();
    const host = dockHost();
    const scroller = mountHost(host);
    const rails = root.querySelector('[data-pasteflick="rails"]');
    if (!rails) return;
    const sr = scrollerRect(scroller);
    const sideLocal = sidebarRight(relayout) - sr.left + scroller.scrollLeft;
    const minLeft = sideLocal > 4 ? sideLocal : 0;
    const pins = rails.querySelectorAll('[data-pasteflick="pin"]');
    if (relayout) {
      pins.forEach((pin) => {
        pin._lockLeft = undefined;
        pin._lockTop = undefined;
        pin._gutterRight = undefined;
      });
    }
    pins.forEach((pin) => {
      dockPin(pin);
      if (pin.getAttribute("data-kind") === "link") {
        placePin(pin, pin._anchor, minLeft, scroller, relayout);
      }
    });
    layoutMessageStacks(rails, scroller);
    placeThreadChip(scroller);
    paintPins();
    packHeaderStick();
    paintHighlights(root, scroller);
  }

  function paintHighlights(root, scroller) {
    const layer = root.querySelector('[data-pasteflick="highlights"]');
    if (!layer) return;
    layer.querySelectorAll('[data-pasteflick="highlight"].is-on').forEach((box) => {
      if (box._anchor && box._anchor.isConnected) paintHighlight(box, box._anchor, scroller);
    });
  }

  function schedulePlace() {
    if (placeTimer) cancelAnimationFrame(placeTimer);
    placeTimer = requestAnimationFrame(() => placeAllPins(false));
  }

  function scheduleRelayout() {
    if (placeTimer) cancelAnimationFrame(placeTimer);
    placeTimer = requestAnimationFrame(() => placeAllPins(true));
  }

  function railsLayer() {
    return layerRoot().querySelector('[data-pasteflick="rails"]');
  }

  function threadTitleLeft(scroller) {
    const sr = scrollerRect(scroller);
    const raw = sidebarRight(false) - sr.left + (scroller.scrollLeft || 0);
    heldTitleLeft = holdNum(heldTitleLeft, Math.round(raw), 4);
    return Math.round(heldTitleLeft);
  }

  function threadColumnEdge(scroller) {
    const nodes = messageNodes();
    for (let i = 0; i < nodes.length; i++) {
      try {
        const box = localBox(nodes[i], scroller);
        if (rectOk(box)) return box.left;
      } catch (_) {
        /* try the next mounted message */
      }
    }
    const sr = scrollerRect(scroller);
    return sidebarRight(false) - sr.left + 96;
  }

  function ensureThreadChip() {
    const rails = railsLayer();
    if (!rails) return null;
    let silo = rails.querySelector('[data-pasteflick="silo"][data-role="thread"]');
    let stack = silo && silo.querySelector('[data-pasteflick="stack"]');
    let pin = stack && stack.querySelector('[data-pasteflick="pin"][data-kind="thread"]');
    if (pin && pin.isConnected) return pin;

    if (!silo) {
      silo = document.createElement("div");
      silo.setAttribute("data-pasteflick", "silo");
      silo.setAttribute("data-role", "thread");
      stack = document.createElement("div");
      stack.setAttribute("data-pasteflick", "stack");
      stack.setAttribute("data-role", "thread");
      silo.appendChild(stack);
      rails.appendChild(silo);
    } else if (!stack) {
      stack = document.createElement("div");
      stack.setAttribute("data-pasteflick", "stack");
      stack.setAttribute("data-role", "thread");
      silo.appendChild(stack);
    }

    pin = document.createElement("div");
    pin.setAttribute("data-pasteflick", "pin");
    pin.setAttribute("data-kind", "thread");

    const copyBtn = makeActionButton("copy-thread", "clipboard", "the transcript", true);
    copyBtn.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      void copyChip("clipboard", copyBtn);
    });
    const pasteBtn = makeActionButton("paste-thread", "cursor", "the transcript", false);
    pasteBtn.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      void copyChip("cursor", pasteBtn);
    });
    const saveBtn = makeActionButton("save-thread", "file", "the transcript", false);
    saveBtn.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      void copyChip("file", saveBtn);
    });

    const actions = document.createElement("div");
    actions.setAttribute("data-pasteflick", "actions");
    actions.appendChild(copyBtn);
    actions.appendChild(saveBtn);
    actions.appendChild(pasteBtn);

    pin.appendChild(makeHead("PasteFlick"));
    pin.appendChild(actions);
    const picks = document.createElement("div");
    picks.setAttribute("data-pasteflick", "picks");
    picks.hidden = true;
    pin.appendChild(picks);
    stack.appendChild(pin);
    return pin;
  }

  function placeThreadChip(scroller) {
    const pin = ensureThreadChip();
    if (!pin) return;
    const stack = pin.parentElement;
    const silo = stack && stack.parentElement;
    if (!stack || !silo) return;
    scroller = scroller || conversationScroller();
    const stackW = Math.ceil(stack.offsetWidth || 124);
    const stackH = Math.ceil(stack.offsetHeight || 56);
    const left = threadTitleLeft(scroller);
    const tall = lastTurnBottom(scroller);
    const stick = headerStickTop(scroller);
    silo.style.top = "0px";
    silo.style.left = Math.round(left) + "px";
    silo.style.width = stackW + "px";
    silo.style.height = tall + "px";
    stack.style.setProperty("--stick-top", Math.max(0, stick) + "px");
    stack._naturalTop = 0;
    stack._ownerTop = 0;
    stack._ownerBottom = tall;
    stack._gutterRight = left + stackW;
    stack._stackH = stackH;
    stack._stickTop = stick;
    pin._gutterRight = left + stackW;
    pin._offscreen = false;
    pin._headerHidden = false;
  }

  function ensureMessagePin(el) {
    let pin = pinByTarget.get(el);
    if (pin && pin.isConnected) return pin;
    pin = document.createElement("div");
    pin.setAttribute("data-pasteflick", "pin");
    pin.setAttribute("data-kind", "message");
    pin.setAttribute("data-message-id", el.getAttribute("data-message-id") || "");
    pin._anchor = el;

    const markBtn = makeIconButton("mark", TOOLTIP, BOOKMARK_SVG);
    markBtn.setAttribute("aria-pressed", "false");
    let pressTimer = 0;
    let joinedByPress = false;
    markBtn.addEventListener("pointerdown", (event) => {
      if (event.button) return;
      joinedByPress = false;
      if (pressTimer) clearTimeout(pressTimer);
      pressTimer = setTimeout(() => {
        pressTimer = 0;
        joinedByPress = true;
        void onMarkClick(el, { metaKey: true, _join: true });
      }, 380);
    });
    const clearPress = () => {
      if (pressTimer) clearTimeout(pressTimer);
      pressTimer = 0;
    };
    markBtn.addEventListener("pointerup", clearPress);
    markBtn.addEventListener("pointerleave", clearPress);
    markBtn.addEventListener("pointercancel", clearPress);
    markBtn.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      if (joinedByPress) {
        joinedByPress = false;
        return;
      }
      void onMarkClick(el, event);
    });

    const actions = document.createElement("div");
    actions.setAttribute("data-pasteflick", "actions");
    actions.appendChild(markBtn);

    const name = document.createElement("span");
    name.setAttribute("data-pasteflick", "label");
    name.hidden = true;
    bindLabel(name);

    pin.appendChild(actions);
    pin.appendChild(name);
    dockPin(pin);
    pinByTarget.set(el, pin);
    return pin;
  }

  function ensureBlockPin(blockEl) {
    let pin = pinByTarget.get(blockEl);
    if (pin && pin.isConnected) return pin;
    const fragment = describeBlock(blockEl);
    const cardLabel = blockCardLabel(fragment);
    const isLink = !!(fragment && fragment.kind === "link") || isInlineLink(blockEl);
    const what = isLink
      ? "this link"
      : isBinaryAsset(fragment, blockEl)
        ? "this file"
        : isProseDocument(fragment, blockEl)
          ? (fragment && (fragment.name || fragment.title)) || "this markdown"
          : (fragment && (fragment.title || fragment.label)) || cardLabel || "this block";
    const pastePrimary = !!(fragment && fragment.kind === "code");
    pin = document.createElement("div");
    pin.setAttribute("data-pasteflick", "pin");
    pin.setAttribute("data-kind", isLink ? "link" : "block");
    pin.setAttribute("data-block-card", isLink ? "Link" : cardLabel);
    pin.setAttribute("data-block-kind", (fragment && fragment.kind) || "block");
    pin._anchor = blockEl;

    const copyBtn = makeActionButton("copy-block", "clipboard", what, !pastePrimary);
    copyBtn.setAttribute("data-block-label", (fragment && fragment.label) || "block");
    copyBtn.setAttribute("data-block-type", (fragment && fragment.type) || "");
    copyBtn.setAttribute("data-block-card", cardLabel);
    copyBtn.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      void copyBlock(blockEl, copyBtn, "clipboard");
    });

    const pasteBtn = makeActionButton("paste-block", "cursor", what, pastePrimary);
    pasteBtn.setAttribute("data-block-card", cardLabel);
    pasteBtn.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      void copyBlock(blockEl, pasteBtn, "cursor");
    });

    const saveBtn = makeActionButton("save-block", "file", what, false);
    saveBtn.setAttribute("data-block-card", cardLabel);
    saveBtn.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      void copyBlock(blockEl, saveBtn, "file");
    });

    const actions = document.createElement("div");
    actions.setAttribute("data-pasteflick", "actions");
    actions.appendChild(copyBtn);
    actions.appendChild(saveBtn);
    actions.appendChild(pasteBtn);

    if (!isLink) pin.appendChild(makeHead(cardLabel));
    pin.appendChild(actions);
    dockPin(pin);
    pinByTarget.set(blockEl, pin);
    return pin;
  }

  function pinFor(el) {
    if (!el) return null;
    const direct = pinByTarget.get(el);
    if (direct && direct.isConnected) return direct;
    const nested = el.querySelectorAll("*");
    for (let i = 0; i < nested.length; i++) {
      const pin = pinByTarget.get(nested[i]);
      if (pin && pin.isConnected) return pin;
    }
    return null;
  }

  async function onMarkClick(el, event) {
    const nodes = messageNodes();
    const position = nodes.indexOf(el);
    const current = await getActiveMarks();
    const kept = namedMark(current[0]) || (await getDraftName());
    const next = describeMessage(el, position >= 0 ? position : 0, kept);
    const additive = !!(event && (event.metaKey || event.ctrlKey || event._join));
    const range = !!(event && event.shiftKey && current.length);
    let marks = current.slice();
    const existing = marks.findIndex((m) => sameMark(m, next));

    if (range) {
      const anchor = lastPickEl && nodes.indexOf(lastPickEl) >= 0 ? lastPickEl : elForMark(current[current.length - 1], nodes);
      const from = anchor ? nodes.indexOf(anchor) : position;
      const lo = Math.min(from, position);
      const hi = Math.max(from, position);
      marks = [];
      if (lo >= 0 && hi >= 0) {
        for (let i = lo; i <= hi; i++) marks.push(describeMessage(nodes[i], i, kept));
      }
    } else if (additive) {
      if (existing >= 0) marks.splice(existing, 1);
      else marks.push(next);
    } else if (existing >= 0 && marks.length === 1) {
      if (kept) await setDraftName(kept);
      marks = [];
    } else {
      marks = [next];
    }

    lastPickEl = marks.length ? el : null;
    await setActiveMarks(marks);
    await applyActiveVisuals();
  }

  function elForMark(mark, nodes) {
    if (!mark || !nodes || !nodes.length) return null;
    const records = nodes.map((el, i) => ({
      el,
      id: el.getAttribute("data-message-id") || "",
      role: canonicalRole(el.getAttribute("data-message-author-role")),
      text: messageTextForMark(el),
      fingerprint: fingerprintText(messageTextForMark(el)),
      position: i,
    }));
    const idx = resolvePasteFlickIndex(records, mark);
    return idx >= 0 ? records[idx].el : null;
  }

  function editingLabel() {
    const host = dockHost();
    const active = (host && host.shadowRoot && host.shadowRoot.activeElement) || document.activeElement;
    return active && active.getAttribute && active.getAttribute("data-pasteflick") === "label" ? active : null;
  }

  function namedMark(mark) {
    return mark && String(mark.name || "").trim();
  }

  function bindLabel(label) {
    label.setAttribute("spellcheck", "false");
    label.setAttribute("role", "textbox");
    label.setAttribute("aria-label", "Name this PasteFlick");
    label.title = "Name this mark";

    const stop = (event) => event.stopPropagation();
    ["mousedown", "mouseup", "click", "dblclick", "keydown", "keyup", "keypress", "input", "paste"].forEach((type) => {
      label.addEventListener(type, stop);
    });

    label.addEventListener("click", (event) => {
      event.preventDefault();
      beginRename(label);
    });

    label.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        label.blur();
      }
      if (event.key === "Escape") {
        event.preventDefault();
        label.textContent = label.getAttribute("data-saved") || "PasteFlick";
        label.blur();
      }
    });

    label.addEventListener("input", () => {
      const text = String(label.textContent || "");
      if (text.length <= 40) return;
      label.textContent = text.slice(0, 40);
      const range = document.createRange();
      range.selectNodeContents(label);
      range.collapse(false);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
    });

    label.addEventListener("paste", (event) => {
      event.preventDefault();
      const text = String((event.clipboardData || window.clipboardData).getData("text") || "")
        .replace(/\s+/g, " ")
        .trim()
        .slice(0, 40);
      document.execCommand("insertText", false, text);
    });

    label.addEventListener("blur", () => {
      void commitRename(label);
    });
  }

  function beginRename(label) {
    if (label.isContentEditable) return;
    label.setAttribute("data-saved", String(label.textContent || "").trim());
    label.setAttribute("contenteditable", "plaintext-only");
    label.focus();
    const range = document.createRange();
    range.selectNodeContents(label);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
  }

  async function commitRename(label) {
    label.removeAttribute("contenteditable");
    const raw = String(label.textContent || "").replace(/\s+/g, " ").trim().slice(0, 40);
    const next = !raw || /^pasteflick$/i.test(raw) ? "" : raw;
    await setPasteFlickName(next);
  }

  function chipWhat(count) {
    if (count >= 2) return "the selected messages";
    if (count === 1) return "the bookmark";
    return "the transcript";
  }

  function syncChipBound(count) {
    const pin = layerRoot().querySelector('[data-pasteflick="pin"][data-kind="thread"]');
    if (!pin) return;
    pin.classList.toggle("is-bound", count > 0);
    const what = chipWhat(count);
    pin.querySelectorAll("[data-action-what]").forEach((btn) => {
      if (btn.classList.contains("is-done")) return;
      btn.setAttribute("data-action-what", what);
      restoreActionButton(btn);
    });
  }

  function paintPickStack(activeEls) {
    const pin = layerRoot().querySelector('[data-pasteflick="pin"][data-kind="thread"]');
    if (!pin) return;
    let picks = pin.querySelector('[data-pasteflick="picks"]');
    if (!picks) {
      picks = document.createElement("div");
      picks.setAttribute("data-pasteflick", "picks");
      pin.appendChild(picks);
    }
    const ids = activeEls.map((el, i) => el.getAttribute("data-message-id") || "#" + i).join("|");
    if (picks._pickKey === ids) {
      picks.hidden = activeEls.length < 2;
      return;
    }
    picks._pickKey = ids;
    picks.innerHTML = "";
    if (activeEls.length < 2) {
      picks.hidden = true;
      return;
    }
    picks.hidden = false;
    activeEls.forEach((el, i) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.setAttribute("data-pasteflick", "pick");
      btn.style.animationDelay = i * 40 + "ms";
      btn.innerHTML = BOOKMARK_SVG;
      btn.title = "";
      btn.setAttribute("aria-label", "Drop this bookmark");
      btn.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        void onMarkClick(el, { metaKey: true, _join: true });
      });
      picks.appendChild(btn);
    });
  }

  function syncHighlights(activeEls) {
    const root = layerRoot();
    let layer = root.querySelector('[data-pasteflick="highlights"]');
    if (!layer) {
      layer = document.createElement("div");
      layer.setAttribute("data-pasteflick", "highlights");
      root.insertBefore(layer, root.querySelector('[data-pasteflick="rails"]'));
    }
    const boxes = Array.from(layer.querySelectorAll('[data-pasteflick="highlight"]'));
    while (boxes.length < activeEls.length) {
      const box = document.createElement("div");
      box.setAttribute("data-pasteflick", "highlight");
      layer.appendChild(box);
      boxes.push(box);
    }
    boxes.forEach((box, i) => {
      const el = activeEls[i];
      if (!el) {
        box.classList.remove("is-on");
        box.style.display = "none";
        box._anchor = null;
        return;
      }
      box._anchor = el;
      box.classList.add("is-on");
      box.style.display = "block";
      paintHighlight(box, el);
    });
  }

  async function applyActiveVisuals() {
    const marks = await getActiveMarks();
    const nodes = messageNodes();
    const records = nodes.map((el, i) => ({
      el,
      id: el.getAttribute("data-message-id") || "",
      role: canonicalRole(el.getAttribute("data-message-author-role")),
      text: messageTextForMark(el),
      fingerprint: fingerprintText(messageTextForMark(el)),
      position: i,
    }));
    const activeEls = [];
    marks.forEach((mark) => {
      const idx = resolvePasteFlickIndex(records, mark);
      if (idx >= 0 && activeEls.indexOf(records[idx].el) < 0) activeEls.push(records[idx].el);
    });
    activeEls.sort((a, b) => nodes.indexOf(a) - nodes.indexOf(b));
    const multi = activeEls.length >= 2;
    const custom = namedMark(marks[0]);
    const labelText = custom || "PasteFlick";
    const focused = editingLabel();
    const root = layerRoot();

    root.querySelectorAll('[data-pasteflick="pin"][data-kind="message"]').forEach((pin) => {
      const on = !!(pin._anchor && activeEls.indexOf(pin._anchor) >= 0);
      const btn = pin.querySelector('[data-pasteflick="mark"]');
      const label = pin.querySelector('[data-pasteflick="label"]');
      if (btn) {
        btn.classList.toggle("is-active", on);
        btn.classList.toggle("is-multi", on && multi);
        btn.classList.toggle("is-joinable", !on && activeEls.length === 1);
        btn.setAttribute("aria-pressed", on ? "true" : "false");
      }
      if (label && label !== focused) {
        label.hidden = !(on && !multi);
        label.textContent = on && !multi ? labelText : "PasteFlick";
        if (on && !multi && custom) label.setAttribute("data-custom", "1");
        else label.removeAttribute("data-custom");
      }
    });

    syncChipBound(activeEls.length);
    paintPickStack(activeEls);
    syncHighlights(activeEls);
  }

  function scan() {
    layerRoot();
    syncScheme();
    const rails = railsLayer();
    const seen = new Set();
    const threadPin = ensureThreadChip();
    if (threadPin) seen.add(threadPin);
    messageNodes().forEach((el) => {
      seen.add(ensureMessagePin(el));
    });
    if (rails) {
      rails.querySelectorAll('[data-pasteflick="pin"]').forEach((pin) => {
        if (pin.getAttribute("data-kind") === "thread" || seen.has(pin)) {
          pin._misses = 0;
          return;
        }
        if (scrolling) return;
        pin._misses = (pin._misses || 0) + 1;
        const live = pin._anchor && pin._anchor.isConnected;
        if (!live || pin._misses >= 4) removePin(pin);
      });
    }
    placeAllPins(false);
    void applyActiveVisuals();
    void getCopyExtras().then((on) => applyExtrasVisuals(on));
    void getDestination().then((prefs) => applyDestinationVisuals(prefs.dest, prefs.format));
  }

  function scheduleScan() {
    if (scrolling) return;
    if (scanTimer) return;
    scanTimer = setTimeout(() => {
      scanTimer = 0;
      scan();
    }, 32);
  }

  function settleAfterScroll() {
    scrolling = false;
    scrollIdle = 0;
    const rails = railsLayer();
    if (!rails) {
      scan();
      return;
    }
    let needPlace = false;
    ensureThreadChip();
    messageNodes().forEach((el) => {
      const had = pinByTarget.get(el);
      if (!had || !had.isConnected) {
        ensureMessagePin(el);
        needPlace = true;
      }
    });
    rails.querySelectorAll('[data-pasteflick="pin"]').forEach((pin) => {
      if (pin.getAttribute("data-kind") === "thread") return;
      const live = pin._anchor && pin._anchor.isConnected;
      if (!live) {
        removePin(pin);
        return;
      }
      if (pin._away) setPinAway(pin, false);
      if (!Number.isFinite(pin._wantTop) || !Number.isFinite(pin._wantLeft)) needPlace = true;
    });
    if (needPlace) placeAllPins(false);
    packHeaderStick();
  }

  function noteScroll() {
    scrolling = true;
    scheduleStickPack();
    if (scrollIdle) clearTimeout(scrollIdle);
    scrollIdle = setTimeout(settleAfterScroll, 140);
  }

  function isDockHost(node) {
    if (!node || node === document || node === document.documentElement) return false;
    if (node.id === HOST_ID || node.id === LEGACY_HOST_ID) return true;
    if (node.closest && (node.closest("#" + HOST_ID) || node.closest("#" + LEGACY_HOST_ID))) return true;
    try {
      const root = node.getRootNode && node.getRootNode();
      const host = root && root.host;
      if (host && (host.id === HOST_ID || host.id === LEGACY_HOST_ID)) return true;
    } catch (_) {
      /* ignore */
    }
    return false;
  }

  function mutationLooksLikeNewTurn(records) {
    for (let i = 0; i < records.length; i++) {
      const rec = records[i];
      if (isDockHost(rec.target)) continue;
      const added = rec.addedNodes;
      for (let j = 0; j < added.length; j++) {
        const node = added[j];
        if (!node || node.nodeType !== 1) continue;
        if (isDockHost(node)) continue;
        if (node.getAttribute && node.getAttribute("data-message-author-role")) return true;
        if (node.querySelector && node.querySelector("[data-message-author-role]")) return true;
      }
    }
    return false;
  }

  async function onNavigate() {
    const key = conversationKey();
    if (key === lastConvKey) return;
    const prev = lastConvKey;
    lastConvKey = key;
    heldTitleLeft = NaN;
    heldStick = 0;
    if (key && prev === "") await migratePending(key);
    scan();
  }

  let started = false;

  function start() {
    if (started) return;
    started = true;
    lastConvKey = conversationKey();
    scan();

    const observer = new MutationObserver((records) => {
      let relevant = false;
      for (let i = 0; i < records.length; i++) {
        if (!isDockHost(records[i].target)) {
          relevant = true;
          break;
        }
      }
      if (!relevant) return;
      if (mutationLooksLikeNewTurn(records)) {
        if (scrolling) return;
        if (scanTimer) {
          clearTimeout(scanTimer);
          scanTimer = 0;
        }
        scan();
        return;
      }
      scheduleScan();
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });

    window.addEventListener(
      "scroll",
      () => {
        const host = dockHost();
        if (host) {
          const scroller = conversationScroller();
          if (host.parentElement !== scroller) mountHost(host);
        }
        noteScroll();
      },
      { capture: true, passive: true },
    );
    window.addEventListener("resize", scheduleRelayout);

    window.addEventListener("popstate", () => void onNavigate());
    window.addEventListener("hashchange", () => void onNavigate());
    ["pushState", "replaceState"].forEach((name) => {
      const orig = history[name];
      if (typeof orig !== "function") return;
      history[name] = function () {
        const ret = orig.apply(this, arguments);
        void onNavigate();
        return ret;
      };
    });
    setInterval(() => void onNavigate(), 800);

    const api = storageApi();
    if (api && api.onChanged) {
      api.onChanged.addListener((changes, area) => {
        if (area !== "local") return;
        if (changes[STORAGE_KEY]) void applyActiveVisuals();
        if (changes[DEST_KEY] || changes[FORMAT_KEY] || changes[AUTOPASTE_KEY]) {
          void getDestination().then((prefs) => applyDestinationVisuals(prefs.dest, prefs.format));
        }
        if (changes[COPY_EXTRAS_KEY]) {
          lastCopyExtras = changes[COPY_EXTRAS_KEY].newValue !== false;
          applyExtrasVisuals(lastCopyExtras);
        }
      });
    }
  }

  globalThis.PasteFlick = {
    getActive: getActivePasteFlick,
    getActives: getActiveMarks,
    setActive: setActivePasteFlick,
    setName: setPasteFlickName,
    getDraft: getDraftName,
    pinFor: pinFor,
    dockRoot: layerRoot,
    scan: scan,
    placeAll: function () {
      placeAllPins(true);
    },
  };

  if (document.body) start();
  else document.addEventListener("DOMContentLoaded", start, { once: true });
})();
