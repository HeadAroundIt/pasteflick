/**
 * MAIN-world extractor on the chat page.
 * Selection-first; skips Dropbox/Drive-style connector embeds.
 * ChatGPT writing documents / canvas text is copied, not stripped.
 */
(function () {
  const OVERLAY = "http://127.0.0.1:8768";
  const PAGE = "pasteflick-page";
  const EXTENSION = "pasteflick-extension";
  const LEGACY_EXTENSION = "pasteflick-extension";

  function fromExtension(data) {
    return data && (data.source === EXTENSION || data.source === LEGACY_EXTENSION);
  }

  // Third-party connectors that should not be copied as transcript text.
  // In-chat file chips, code, links, and writing documents stay in the copy.
  const EMBED_SELECTOR = [
    "embed",
    "object",
    "webview",
    "[data-testid*='image-detail' i]",
    "[data-testid*='connector' i]",
    "[data-testid*='dropbox' i]",
    "[data-testid*='gdrive' i]",
    "[data-testid*='google-drive' i]",
    "[data-testid*='onedrive' i]",
    "[data-testid*='notion' i]",
    "[class*='dropbox' i]",
    "[aria-label*='Dropbox' i]",
    "[aria-label*='Google Drive' i]",
    "[aria-label*='OneDrive' i]",
  ].join(",");

  const UI_CHROME_SELECTOR = [
    "button",
    "nav",
    "[role='toolbar']",
    "[role='menu']",
    "[data-testid*='copy']",
    "[data-testid*='share']",
    "[data-testid*='good-response']",
    "[data-testid*='bad-response']",
  ].join(",");

  const SCROLLLOG_SELECTOR = "[data-pasteflick]";
  const PASTEFLICK_NONE =
    "No PasteFlick in this chat. Click the bookmark on the left of a message.";
  const PASTEFLICK_MISSING =
    "Couldn't find the PasteFlick. Place a new mark on a message, then try again.";

  /**
   * Opening the extension popup clears the page selection. Cache the last
   * real highlight so "Copy selection" still uses what you highlighted.
   */
  let lastSelectionSnapshot = null;
  let selectionCacheTimer = null;
  let lastDestination = "clipboard";
  let lastFileFormat = "md";
  let lastCopyExtras = true;

  function pageTitle() {
    const el =
      document.querySelector("h1") ||
      document.querySelector("[data-testid='conversation-title']");
    const t = (el && el.textContent) || document.title || "Chat";
    return String(t).replace(/\s*[—–-]\s*ChatGPT\s*$/i, "").trim() || "Chat";
  }

  function conversationIdFromUrl(url) {
    const m = String(url || location.href).match(/\/c\/([a-zA-Z0-9-]+)/);
    return m ? m[1] : null;
  }

  function isDiagramNode(el) {
    if (!el || typeof el.closest !== "function") return false;
    try {
      if (
        el.closest(
          "[class*='mermaid' i], [data-testid*='mermaid' i], [data-testid*='diagram' i], [aria-label*='diagram' i], [aria-label*='flowchart' i]",
        )
      ) {
        return true;
      }
    } catch (_) {
      /* ignore selector failures */
    }
    const blob =
      String(el.className || "") +
      " " +
      String((el.getAttribute && el.getAttribute("data-testid")) || "") +
      " " +
      String((el.getAttribute && el.getAttribute("aria-label")) || "");
    return /mermaid|flowchart|diagram/i.test(blob);
  }

  function isInsideEmbed(node) {
    const el = node.nodeType === 1 ? node : node.parentElement;
    if (!el || typeof el.closest !== "function") return false;
    if (isDiagramNode(el)) return false;
    try {
      return !!el.closest(EMBED_SELECTOR);
    } catch (_) {
      return false;
    }
  }

  function isInsideScrollLog(node) {
    const el = node.nodeType === 1 ? node : node.parentElement;
    if (!el || typeof el.closest !== "function") return false;
    try {
      return !!el.closest(SCROLLLOG_SELECTOR);
    } catch (_) {
      return false;
    }
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

  function asMarkRecords(items, textKey) {
    const key = textKey || "text";
    return items.map((item, i) => {
      const text = item[key] || item.body || item.text || "";
      return {
        id: item.id || "",
        role: canonicalRole(item.role),
        text,
        fingerprint: fingerprintText(text),
        position: i,
      };
    });
  }

  function normalizeText(text) {
    return String(text || "")
      .replace(/\u00a0/g, " ")
      .replace(/[ \t]+\n/g, "\n")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }

  function textFromRangeSkippingEmbeds(range) {
    const root = range.commonAncestorContainer;
    const rootEl = root.nodeType === 1 ? root : root.parentElement;
    if (!rootEl) return normalizeText(range.toString());

    const walker = document.createTreeWalker(rootEl, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        if (!node.nodeValue) return NodeFilter.FILTER_REJECT;
        if (isInsideEmbed(node) || isInsideScrollLog(node)) return NodeFilter.FILTER_REJECT;
        try {
          const nodeRange = document.createRange();
          nodeRange.selectNodeContents(node);
          // Reject text completely outside the selection.
          if (range.compareBoundaryPoints(Range.END_TO_START, nodeRange) <= 0) {
            return NodeFilter.FILTER_REJECT;
          }
          if (range.compareBoundaryPoints(Range.START_TO_END, nodeRange) >= 0) {
            return NodeFilter.FILTER_REJECT;
          }
        } catch (_) {
          return NodeFilter.FILTER_REJECT;
        }
        return NodeFilter.FILTER_ACCEPT;
      },
    });

    const chunks = [];
    let skippedEmbed = false;
    let node;
    while ((node = walker.nextNode())) {
      let text = node.nodeValue || "";
      if (node === range.startContainer && node === range.endContainer) {
        text = text.slice(range.startOffset, range.endOffset);
      } else if (node === range.startContainer) {
        text = text.slice(range.startOffset);
      } else if (node === range.endContainer) {
        text = text.slice(0, range.endOffset);
      }
      if (text) chunks.push(text);
    }

    // Also detect whether embeds were present in the selection (for a note).
    try {
      const probe = range.cloneContents();
      if (probe.querySelector && probe.querySelector(EMBED_SELECTOR)) {
        skippedEmbed = true;
      }
    } catch (_) {
      /* ignore */
    }

    return {
      text: normalizeText(chunks.join("")),
      skippedEmbed,
    };
  }

  function getSelectionText() {
    const sel = window.getSelection && window.getSelection();
    if (!sel || sel.isCollapsed || !sel.rangeCount) {
      return { text: "", skippedEmbed: false };
    }
    const parts = [];
    let skippedEmbed = false;
    for (let i = 0; i < sel.rangeCount; i++) {
      const piece = textFromRangeSkippingEmbeds(sel.getRangeAt(i));
      if (piece.text) parts.push(piece.text);
      if (piece.skippedEmbed) skippedEmbed = true;
    }
    return {
      text: normalizeText(parts.join("\n\n")),
      skippedEmbed,
    };
  }

  function roleHeading(role) {
    if (role === "user") return "User";
    if (role === "assistant") return "Assistant";
    return String(role || "Unknown");
  }

  function privateApi() {
    const p = globalThis.PasteFlickPrivate;
    return p && p.fetchConversation ? p : null;
  }

  function copyHeader(title, url, note) {
    if (!lastCopyExtras) return "";
    const heading = String(title || "Chat").trim() || "Chat";
    const lines = ["---", "title: " + JSON.stringify(heading)];
    if (url) lines.push("url: " + JSON.stringify(String(url)));
    const extra = String(note || "").trim();
    if (extra) lines.push("note: " + JSON.stringify(extra));
    lines.push("---", "");
    return lines.join("\n");
  }

  function formatMarkdown(title, turns, url, partial, note) {
    const bits = [];
    if (partial) bits.push("partial — only messages currently mounted were captured");
    if (note) bits.push(note);
    const header = copyHeader(title, url, bits.join(" · "));
    const lines = header ? [header] : [];
    const skipRole = !lastCopyExtras && turns.length === 1;
    for (const turn of turns) {
      if (!skipRole) {
        lines.push("## " + turn.role);
        lines.push("");
      }
      lines.push(turn.body.replace(/\s+$/g, ""));
      lines.push("");
    }
    return lines.join("\n").replace(/\s+$/g, "") + "\n";
  }

  function wrapSelection(text, title, url, skippedEmbed) {
    const body = normalizeText(text);
    const heading = title || "Selection";
    const note = skippedEmbed
      ? "embedded documents/apps (e.g. Dropbox/Canvas) were skipped"
      : "";
    const markdown = copyHeader(heading, url, note) + body + "\n";
    const blocks = body.split(/\n\n+/).filter((b) => b.trim());
    return {
      title: heading,
      markdown,
      turn_count: body ? Math.max(1, blocks.length) : 0,
      character_count: markdown.length,
      partial: false,
      source: "selection",
      url: url || "",
      status_note: note,
    };
  }

  function wrapFragment(fragment) {
    if (!fragment || !String(fragment.body || "").trim()) {
      throw new Error("Nothing to copy in that block.");
    }
    const title = fragment.title || fragment.label || "Block";
    const meta = [];
    if (fragment.kind) meta.push(fragment.kind);
    if (fragment.type) meta.push(fragment.type);
    if (fragment.name) meta.push(fragment.name);
    const out = wrapSelection(String(fragment.body), title, location.href, false);
    out.source = fragment.kind === "message" ? "message" : "block";
    out.status_note = meta.join(" · ") || "single message";
    if (fragment.kind === "message") {
      out.status_note = "single message";
    }
    out.turn_count = 1;
    out.markdown =
      copyHeader(title, location.href, out.status_note) +
      String(fragment.body).replace(/\s+$/g, "") +
      "\n";
    out.character_count = out.markdown.length;
    return out;
  }

  function inlineFrames(clone, original) {
    const srcFrames = original.querySelectorAll("iframe");
    const dstFrames = clone.querySelectorAll("iframe");
    dstFrames.forEach((n, i) => {
      let text = "";
      try {
        const doc = srcFrames[i] && srcFrames[i].contentDocument;
        if (doc && doc.body) text = normalizeText(doc.body.innerText);
      } catch (_) {
        /* cross-origin */
      }
      const stub = document.createElement("p");
      stub.textContent = text || "[embedded frame]";
      n.replaceWith(stub);
    });
  }

  function languageFromPreEl(pre) {
    const code = (pre.querySelector && pre.querySelector("code")) || pre;
    const cls = String((code && code.className) || pre.className || "");
    const m = cls.match(/language-([a-z0-9+#._-]+)/i);
    return m ? m[1] : "";
  }

  function expandLinksInClone(clone) {
    clone.querySelectorAll("a[href]").forEach((a) => {
      if (a.hasAttribute("download")) return;
      const href = String(a.getAttribute("href") || a.href || "").trim();
      if (!href || href === "#" || /^javascript:/i.test(href)) return;
      if (/^(data:|blob:)/i.test(href)) return;
      let abs = href;
      if (/^mailto:/i.test(href)) {
        abs = href.replace(/^mailto:/i, "");
      } else if (/^https?:/i.test(href) || href.indexOf("//") === 0) {
        try {
          abs = new URL(href, location.href).href;
        } catch (_) {
          abs = href;
        }
      } else if (/^www\./i.test(href)) {
        abs = "https://" + href;
      } else {
        return;
      }
      const text = normalizeText(a.innerText || a.textContent || "");
      const stub = document.createElement("span");
      if (!text || text === abs || text === href || text === abs.replace(/^https?:\/\//i, "")) {
        stub.textContent = abs;
      } else {
        stub.textContent = "[" + text + "](" + abs + ")";
      }
      a.replaceWith(stub);
    });
  }

  function fencePresInClone(clone) {
    clone.querySelectorAll("pre").forEach((pre) => {
      const code = pre.querySelector("code") || pre;
      const lang = languageFromPreEl(pre);
      const raw = normalizeText(code.innerText || code.textContent || "");
      const stub = document.createElement("p");
      stub.textContent = "```" + lang + "\n" + raw + "\n```";
      pre.replaceWith(stub);
    });
    clone
      .querySelectorAll(
        "[class*='mermaid' i], [data-testid*='mermaid' i], [data-testid*='diagram' i], [aria-label*='flowchart' i], [aria-label*='diagram' i]",
      )
      .forEach((host) => {
        host.querySelectorAll("svg").forEach((svg) => svg.remove());
      });
  }

  function scrubMessageClone(clone, original) {
    try {
      clone.querySelectorAll(SCROLLLOG_SELECTOR).forEach((n) => n.remove());
      clone.querySelectorAll(UI_CHROME_SELECTOR).forEach((n) => n.remove());
      clone.querySelectorAll(EMBED_SELECTOR).forEach((n) => n.remove());
      clone.querySelectorAll("img").forEach((img) => {
        const src = img.currentSrc || img.src || "";
        const alt = String(img.alt || "").trim();
        const bits = [];
        if (alt) bits.push(alt);
        if (src) bits.push(src);
        const stub = document.createElement("p");
        stub.textContent = bits.join("\n") || "[image]";
        img.replaceWith(stub);
      });
      inlineFrames(clone, original);
      expandLinksInClone(clone);
      fencePresInClone(clone);
    } catch (_) {
      /* ignore selector failures */
    }
  }

  function messageTextForCopy(el) {
    const clone = el.cloneNode(true);
    scrubMessageClone(clone, el);
    return normalizeText(clone.innerText || clone.textContent || "");
  }

  async function extractSingleMessage(target) {
    if (!target) throw new Error("No message selected.");
    const url = location.href;
    const title = pageTitle();
    const id = conversationIdFromUrl(url);

    const priv = privateApi();
    if (id && lastDestination !== "cursor" && priv) {
      try {
        const payload = await priv.fetchConversation(id);
        const turns = priv.turnsFromPayload(payload);
        const idx = resolvePasteFlickIndex(asMarkRecords(turns, "body"), target);
        if (idx >= 0) {
          const heading = (payload && payload.title) || title;
          return payloadFromTurns(
            heading,
            [turns[idx]],
            url,
            false,
            "single message",
            "message",
          );
        }
      } catch (_) {
        /* fall through to DOM */
      }
    }

    const nodes = document.querySelectorAll("[data-message-author-role]");
    const messages = [];
    nodes.forEach((el) => {
      if (isInsideScrollLog(el)) return;
      const role = el.getAttribute("data-message-author-role") || "unknown";
      const text = messageTextForCopy(el);
      if (!text) return;
      messages.push({
        role,
        text,
        id: el.getAttribute("data-message-id") || "",
      });
    });
    const idx = resolvePasteFlickIndex(asMarkRecords(messages, "text"), target);
    if (idx < 0) throw new Error("Couldn't find that message.");
    const picked = messages[idx];
    return payloadFromTurns(
      title,
      [{ role: roleHeading(picked.role), body: picked.text }],
      url,
      true,
      "single message · visible DOM",
      "message",
    );
  }

  function messageTextExcludingEmbeds(el) {
    return messageTextForCopy(el);
  }

  function scrapeDomMessages() {
    const nodes = document.querySelectorAll("[data-message-author-role]");
    const messages = [];
    nodes.forEach((el) => {
      if (isInsideScrollLog(el)) return;
      const role = el.getAttribute("data-message-author-role") || "unknown";
      const text = messageTextExcludingEmbeds(el);
      if (!text) return;
      messages.push({
        role,
        text,
        id: el.getAttribute("data-message-id") || "",
      });
    });
    return messages;
  }

  function scrapeVisibleMessages() {
    const nodes = document.querySelectorAll("[data-message-author-role]");
    const messages = [];
    nodes.forEach((el) => {
      if (isInsideScrollLog(el)) return;
      const role = el.getAttribute("data-message-author-role") || "unknown";
      const text = messageTextForCopy(el);
      if (!text) return;
      messages.push({
        role,
        text,
        id: el.getAttribute("data-message-id") || "",
      });
    });
    return messages;
  }

  function fromVisibleDom(title, url) {
    const messages = scrapeVisibleMessages();
    const turns = messages.map((m) => ({
      role: roleHeading(m.role),
      body: m.text,
    }));
    const markdown = formatMarkdown(title, turns, url, true, "");
    return {
      title,
      markdown,
      turn_count: turns.length,
      character_count: markdown.length,
      partial: true,
      source: "dom",
      url: url || "",
      status_note: "",
    };
  }

  function fromDom(title, url) {
    const messages = scrapeDomMessages();
    const turns = messages.map((m) => ({
      role: roleHeading(m.role),
      body: m.text,
    }));
    const markdown = formatMarkdown(
      title,
      turns,
      url,
      true,
      "embedded documents/apps were skipped",
    );
    return {
      title,
      markdown,
      turn_count: turns.length,
      character_count: markdown.length,
      partial: true,
      source: "dom",
      url: url || "",
      status_note: "embedded documents/apps were skipped",
    };
  }

  function rangeIntersectsNode(range, node) {
    try {
      const nodeRange = document.createRange();
      nodeRange.selectNodeContents(node);
      // Completely before or after => no intersection.
      if (range.compareBoundaryPoints(Range.END_TO_START, nodeRange) <= 0) return false;
      if (range.compareBoundaryPoints(Range.START_TO_END, nodeRange) >= 0) return false;
      return true;
    } catch (_) {
      return false;
    }
  }

  /**
   * Same path full-thread DOM uses: read whole message bubbles, strip embeds.
   * Scoped to bubbles that intersect the user's highlight.
   */
  function messagesIntersectingSelection() {
    const sel = window.getSelection && window.getSelection();
    if (!sel || sel.isCollapsed || !sel.rangeCount) return [];

    const ranges = [];
    for (let i = 0; i < sel.rangeCount; i++) ranges.push(sel.getRangeAt(i));

    const out = [];
    const nodes = document.querySelectorAll("[data-message-author-role]");
    nodes.forEach((el) => {
      let hit = false;
      for (let i = 0; i < ranges.length; i++) {
        if (rangeIntersectsNode(ranges[i], el)) {
          hit = true;
          break;
        }
      }
      if (!hit) return;
      if (isInsideScrollLog(el)) return;
      const text = messageTextExcludingEmbeds(el);
      if (!text) return;
      out.push({
        role: el.getAttribute("data-message-author-role") || "unknown",
        text,
        id: el.getAttribute("data-message-id") || "",
      });
    });
    return out;
  }

  function fromSelectedMessages(title, url, messages) {
    const turns = messages.map((m) => ({
      role: roleHeading(m.role),
      body: m.text,
    }));
    const markdown = formatMarkdown(
      title,
      turns,
      url,
      false,
      "selection via chat messages; embeds skipped",
    );
    return {
      title,
      markdown,
      turn_count: turns.length,
      character_count: markdown.length,
      partial: false,
      source: "selection",
      url: url || "",
      status_note: "selection via chat messages; embeds skipped",
    };
  }

  /**
   * When message ids are available, reuse the working full-thread API and
   * keep only the highlighted messages.
   */
  async function extractSelectionViaApi(title, url, selectedMessages) {
    const priv = privateApi();
    const id = conversationIdFromUrl(url);
    if (!priv || !id) return null;
    const wanted = new Set(
      selectedMessages.map((m) => m.id).filter((x) => x && String(x).length > 4),
    );
    if (!wanted.size) return null;
    try {
      const payload = await priv.fetchConversation(id);
      const turns = priv.selectionTurns(payload, wanted);
      if (!turns.length) return null;
      const heading = (payload && payload.title) || title;
      const markdown = formatMarkdown(
        heading,
        turns,
        url,
        false,
        "selection via API; document embeds omitted",
      );
      return {
        title: heading,
        markdown,
        turn_count: turns.length,
        character_count: markdown.length,
        partial: false,
        source: "selection",
        url,
        status_note: "selection via API; document embeds omitted",
      };
    } catch (_) {
      return null;
    }
  }

  function payloadFromTurns(title, turns, url, partial, note, source) {
    const markdown = formatMarkdown(title, turns, url, !!partial, note || "");
    return {
      title,
      markdown,
      turn_count: turns.length,
      character_count: markdown.length,
      partial: !!partial,
      source: source || "pasteflick",
      url: url || "",
      status_note: note || "",
    };
  }

  async function extractFromPasteFlick(mark) {
    if (!mark) throw new Error(PASTEFLICK_NONE);
    const url = location.href;
    const title = pageTitle();
    const id = conversationIdFromUrl(url);

    const priv = privateApi();
    if (id && lastDestination !== "cursor" && priv) {
      try {
        const payload = await priv.fetchConversation(id);
        const turns = priv.turnsFromPayload(payload);
        const idx = resolvePasteFlickIndex(asMarkRecords(turns, "body"), mark);
        if (idx >= 0) {
          const heading = (payload && payload.title) || title;
          return payloadFromTurns(
            heading,
            turns.slice(idx),
            url,
            false,
            "from PasteFlick",
            "pasteflick",
          );
        }
      } catch (_) {
        /* API unavailable or unusable — try visible DOM next. */
      }
    }

    const messages =
      lastDestination === "cursor" ? scrapeVisibleMessages() : scrapeDomMessages();
    const idx = resolvePasteFlickIndex(asMarkRecords(messages, "text"), mark);
    if (idx < 0) throw new Error(PASTEFLICK_MISSING);
    const sliced = messages.slice(idx).map((m) => ({
      role: roleHeading(m.role),
      body: m.text,
    }));
    return payloadFromTurns(
      title,
      sliced,
      url,
      true,
      lastDestination === "cursor" ? "" : "from PasteFlick · visible DOM, embeds skipped",
      "pasteflick",
    );
  }

  async function extractFull() {
    const url = location.href;
    const title = pageTitle();
    if (lastDestination === "cursor") {
      return fromVisibleDom(title, url);
    }
    const id = conversationIdFromUrl(url);
    if (!id) throw new Error("Open a chat first.");
    const priv = privateApi();
    if (!priv) {
      return fromDom(title, url);
    }
    try {
      const payload = await priv.fetchConversation(id);
      const turns = priv.turnsFromPayload(payload);
      const heading = (payload && payload.title) || title;
      const markdown = formatMarkdown(heading, turns, url, false, "");
      return {
        title: heading,
        markdown,
        turn_count: turns.length,
        character_count: markdown.length,
        partial: false,
        source: "api",
        url,
      };
    } catch (err) {
      const fallback = fromDom(title, url);
      fallback.status_note =
        "API failed (" + ((err && err.message) || err) + "); used visible DOM, embeds skipped";
      return fallback;
    }
  }

  function captureSelectionSnapshot() {
    const sel = window.getSelection && window.getSelection();
    if (!sel || sel.isCollapsed || !sel.rangeCount) {
      // Collapsed (e.g. popup focus) — keep the previous snapshot.
      return;
    }

    const messages = messagesIntersectingSelection();
    const selected = getSelectionText();
    const raw = String(sel.toString() || "").trim();

    // Need either intersecting chat bubbles or usable text.
    if (!messages.length && selected.text.length < 8 && raw.length < 8) return;

    lastSelectionSnapshot = {
      at: Date.now(),
      messages,
      text: selected.text || normalizeText(raw),
      skippedEmbed: !!selected.skippedEmbed,
    };
  }

  function scheduleSelectionCache() {
    if (selectionCacheTimer) clearTimeout(selectionCacheTimer);
    selectionCacheTimer = setTimeout(captureSelectionSnapshot, 40);
  }

  function resolveSelectionInputs() {
    const liveMessages = messagesIntersectingSelection();
    const liveText = getSelectionText();
    const liveRaw = String(
      (window.getSelection && window.getSelection() && window.getSelection().toString()) || "",
    ).trim();

    const liveOk =
      liveMessages.length > 0 || liveText.text.length >= 8 || liveRaw.length >= 8;

    if (liveOk) {
      return {
        messages: liveMessages,
        text: liveText.text || normalizeText(liveRaw),
        skippedEmbed: !!liveText.skippedEmbed,
        fromCache: false,
      };
    }

    if (lastSelectionSnapshot) {
      return {
        messages: lastSelectionSnapshot.messages || [],
        text: lastSelectionSnapshot.text || "",
        skippedEmbed: !!lastSelectionSnapshot.skippedEmbed,
        fromCache: true,
      };
    }

    return { messages: [], text: "", skippedEmbed: false, fromCache: false };
  }

  async function extractSelectionOrFull(preferSelection) {
    const url = location.href;
    const title = pageTitle();

    if (preferSelection === false) {
      return extractFull();
    }

    // Never silently fall through to full thread when the user asked for a selection.
    const pick = resolveSelectionInputs();

    if (pick.messages.length) {
      // Partial highlight inside one bubble → prefer exact text when we have it.
      if (pick.messages.length === 1 && pick.text.length >= 8) {
        const whole = pick.messages[0].text || "";
        if (pick.text.length < whole.length * 0.92) {
          return wrapSelection(pick.text, title, url, pick.skippedEmbed);
        }
      }

      const viaApi = await extractSelectionViaApi(title, url, pick.messages);
      if (viaApi) {
        if (pick.fromCache) {
          viaApi.status_note = (viaApi.status_note || "") + " (from cached highlight)";
        }
        return viaApi;
      }
      const out = fromSelectedMessages(title, url, pick.messages);
      if (pick.fromCache) {
        out.status_note = (out.status_note || "") + " (from cached highlight)";
      }
      return out;
    }

    if (pick.text.length >= 8) {
      return wrapSelection(pick.text, title, url, pick.skippedEmbed);
    }

    throw new Error(
      "No text selected. Highlight the chat text you want, then click Copy selection again.",
    );
  }

  async function writeClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (_) {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand("copy");
      ta.remove();
      return ok;
    }
  }

  function resolveDestination(extra) {
    extra = extra || {};
    const dest = extra.destination;
    if (dest === "clipboard" || dest === "cursor" || dest === "file") return dest;
    if (extra.autoPaste) return "cursor";
    return lastDestination || "clipboard";
  }

  function wantsCopyExtras(extra) {
    extra = extra || {};
    if (resolveDestination(extra) === "cursor") return false;
    if (extra.copyExtras == null) return lastCopyExtras;
    return !!extra.copyExtras;
  }

  function resolveFormat(extra) {
    extra = extra || {};
    if (extra.fileFormat === "pdf" || extra.format === "pdf") return "pdf";
    if (extra.fileFormat === "md" || extra.format === "md") return "md";
    return lastFileFormat || "md";
  }

  async function ingestDirect(payload, dest, format) {
    try {
      const res = await fetch(OVERLAY + "/api/ingest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: AbortSignal.timeout(8000),
        body: JSON.stringify({
          title: payload.title || "",
          markdown: payload.markdown || "",
          url: payload.url || location.href,
          source: payload.source || "selection",
          partial: !!payload.partial,
          turn_count: payload.turn_count || 0,
          character_count: payload.character_count || (payload.markdown || "").length,
          copy_to_clipboard: false,
          auto_paste: dest === "cursor",
          save: dest === "file",
          destination: dest,
          format: dest === "file" ? format : "md",
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

  function ingestThroughExtension(payload, dest, format) {
    return new Promise((resolve) => {
      const requestId = "ing-" + Math.random().toString(36).slice(2);
      const timer = setTimeout(() => {
        window.removeEventListener("message", onMessage);
        resolve(null);
      }, 8000);

      function onMessage(event) {
        if (event.source !== window) return;
        const data = event.data;
        if (!fromExtension(data)) return;
        if (data.type !== "ingest-result" || data.requestId !== requestId) return;
        clearTimeout(timer);
        window.removeEventListener("message", onMessage);
        resolve(data.result || null);
      }

      window.addEventListener("message", onMessage);
      window.postMessage(
        {
          source: PAGE,
          type: "ingest",
          requestId,
          payload: {
            title: payload.title || "",
            markdown: payload.markdown || "",
            url: payload.url || location.href,
            source: payload.source || "selection",
            partial: !!payload.partial,
            turn_count: payload.turn_count || 0,
            character_count: payload.character_count || (payload.markdown || "").length,
            destination: dest,
            format: dest === "file" ? format : "md",
          },
        },
        "*",
      );
    });
  }

  async function ingest(payload) {
    const dest = payload.destination || lastDestination || "clipboard";
    const format = payload.format || lastFileFormat || "md";
    if (location.protocol === "https:") {
      const bridged = await ingestThroughExtension(payload, dest, format);
      if (bridged) return bridged;
    }
    return ingestDirect(payload, dest, format);
  }

  const SELECT_VIEW_ID = "pasteflick-select-view";

  function removeSelectView() {
    const el = document.getElementById(SELECT_VIEW_ID);
    if (el) el.remove();
    document.documentElement.style.overflow = "";
  }

  function selectionInside(el) {
    const sel = window.getSelection && window.getSelection();
    if (!sel || sel.isCollapsed || !sel.rangeCount) return "";
    const range = sel.getRangeAt(0);
    if (!el.contains(range.commonAncestorContainer)) return "";
    return normalizeText(sel.toString());
  }

  function showToast(host, message, ok) {
    let toast = host.querySelector("[data-toast]");
    if (!toast) {
      toast = document.createElement("div");
      toast.setAttribute("data-toast", "1");
      toast.className = "sm-hint";
      host.appendChild(toast);
    }
    toast.style.color = ok
      ? "var(--muted)"
      : "color-mix(in srgb, var(--red) 45%, var(--text))";
    toast.textContent = message;
  }

  async function openSelectView(preloaded) {
    removeSelectView();
    document.documentElement.style.overflow = "hidden";

    const shell = document.createElement("div");
    shell.id = SELECT_VIEW_ID;
    shell.setAttribute("data-pasteflick", "select-view");
    shell.setAttribute("role", "dialog");
    shell.setAttribute("aria-modal", "true");

    const style = document.createElement("style");
    style.setAttribute("data-pasteflick", "style");
    style.textContent = `
      #${SELECT_VIEW_ID} {
        --bg0:#171410;--bg1:#211c16;--well:#110e0b;--text:#efe6d4;
        --muted:#9d8f76;--faint:#72685a;--earth:#c4a060;--paper:#e4d2ae;
        --red:#b24c42;--pick:color-mix(in srgb,#c9a66a 11%,#171410);
        --stroke:rgba(232,208,156,.10);--stroke-strong:rgba(201,166,106,.24);
        --shine:rgba(244,226,180,.08);--rim:rgba(201,166,106,.32);
        position:fixed;inset:0;z-index:2147483646;display:flex;
        align-items:center;justify-content:center;padding:24px;box-sizing:border-box;
        font-family:"Segoe UI Variable Text",Segoe UI,system-ui,sans-serif;
        font-weight:450;letter-spacing:-.011em;color:var(--text);
      }
      #${SELECT_VIEW_ID} .sm-back {
        position:absolute;inset:0;background:rgba(10,8,5,.76);
      }
      #${SELECT_VIEW_ID} .sm-panel {
        position:relative;z-index:1;width:min(860px,100%);height:min(820px,92vh);
        display:flex;flex-direction:column;background:var(--bg0);color:var(--text);
        border-radius:20px;box-shadow:inset 0 1px 0 var(--shine);overflow:hidden;
      }
      #${SELECT_VIEW_ID} .sm-panel::after {
        content:"";position:absolute;inset:1px;border:1px solid var(--rim);
        border-radius:19px;pointer-events:none;
      }
      #${SELECT_VIEW_ID} .sm-titlebar {
        display:flex;align-items:center;justify-content:space-between;gap:8px;
        padding:10px 16px 8px;min-height:44px;flex:none;
        box-shadow:inset 0 -1px 0 var(--stroke);
      }
      #${SELECT_VIEW_ID} .sm-brand {
        font-size:15px;font-weight:650;letter-spacing:-.02em;
      }
      #${SELECT_VIEW_ID} .sm-ghost {
        appearance:none;border:0;background:transparent;color:var(--muted);
        width:28px;height:28px;border-radius:8px;cursor:pointer;font:inherit;
        transition:background 120ms ease,color 120ms ease;
      }
      #${SELECT_VIEW_ID} .sm-ghost:hover {
        background:rgba(232,208,156,.09);color:var(--text);
      }
      #${SELECT_VIEW_ID} .sm-body {
        flex:1;overflow:auto;padding:16px;background:var(--well);
      }
      #${SELECT_VIEW_ID} .sm-meta {
        margin:0 0 12px;font-size:11px;color:var(--muted);
      }
      #${SELECT_VIEW_ID} .sm-pre {
        margin:0;white-space:pre-wrap;word-break:break-word;
        font-family:ui-monospace,Cascadia Mono,Consolas,monospace;
        font-size:12.5px;line-height:1.45;color:var(--text);
        user-select:text;cursor:text;
      }
      #${SELECT_VIEW_ID} .sm-foot {
        padding:12px 16px;flex:none;background:var(--bg0);
        box-shadow:inset 0 1px 0 var(--stroke);
      }
      #${SELECT_VIEW_ID} .sm-row { display:flex;gap:8px; }
      #${SELECT_VIEW_ID} .sm-btn {
        height:36px;padding:0 14px;border-radius:11px;
        border:1px solid var(--stroke);background:var(--bg1);color:var(--text);
        font:inherit;font-weight:600;cursor:pointer;
        transition:background 120ms ease,border-color 120ms ease,transform 80ms ease;
      }
      #${SELECT_VIEW_ID} .sm-btn.primary {
        background:color-mix(in srgb,var(--earth) 16%,var(--bg1));
        border-color:var(--stroke-strong);
      }
      #${SELECT_VIEW_ID} .sm-btn:hover:not(:disabled) {
        background:var(--pick);border-color:var(--stroke-strong);
      }
      #${SELECT_VIEW_ID} .sm-btn.primary:hover:not(:disabled) {
        background:color-mix(in srgb,var(--earth) 22%,var(--bg1));
      }
      #${SELECT_VIEW_ID} .sm-btn:active:not(:disabled) { transform:translateY(1px); }
      #${SELECT_VIEW_ID} .sm-btn:disabled { color:var(--faint);cursor:default; }
      #${SELECT_VIEW_ID} .sm-hint {
        margin-top:10px;font-size:12px;line-height:1.35;min-height:16px;color:var(--faint);
      }
    `;

    const backdrop = document.createElement("div");
    backdrop.className = "sm-back";
    backdrop.addEventListener("click", removeSelectView);

    const panel = document.createElement("div");
    panel.className = "sm-panel";

    const header = document.createElement("div");
    header.className = "sm-titlebar";
    header.innerHTML =
      '<div class="sm-brand">PasteFlick</div>' +
      '<button type="button" class="sm-ghost" aria-label="Close">✕</button>';

    const body = document.createElement("div");
    body.className = "sm-body";

    const loading = document.createElement("div");
    loading.className = "sm-meta";
    loading.textContent = "Loading…";
    body.appendChild(loading);

    const footer = document.createElement("div");
    footer.className = "sm-foot";

    const row = document.createElement("div");
    row.className = "sm-row";

    function makeBtn(label, primary) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = primary ? "sm-btn primary" : "sm-btn";
      btn.textContent = label;
      btn.addEventListener("mousedown", (e) => e.preventDefault());
      return btn;
    }

    const copySelBtn = makeBtn("Copy selection", true);
    const copyAllBtn = makeBtn("Copy all", false);
    copySelBtn.disabled = true;
    copyAllBtn.disabled = true;
    row.appendChild(copySelBtn);
    row.appendChild(copyAllBtn);
    footer.appendChild(row);

    const closeBtn = header.querySelector(".sm-ghost");
    panel.appendChild(header);
    panel.appendChild(body);
    panel.appendChild(footer);
    shell.appendChild(style);
    shell.appendChild(backdrop);
    shell.appendChild(panel);
    document.documentElement.appendChild(shell);

    const onKey = (e) => {
      if (e.key === "Escape") {
        e.preventDefault();
        cleanup();
      }
    };
    function cleanup() {
      document.removeEventListener("keydown", onKey, true);
      removeSelectView();
    }
    document.addEventListener("keydown", onKey, true);
    closeBtn.addEventListener("click", cleanup);

    let fullPayload = null;
    let textEl = null;

    try {
      fullPayload = preloaded || (await extractFull());
      body.innerHTML = "";

      const meta = document.createElement("div");
      meta.className = "sm-meta";
      meta.textContent =
        (fullPayload.title || "Chat") +
        " · " +
        (fullPayload.turn_count || 0) +
        " turns · " +
        (fullPayload.character_count || 0).toLocaleString() +
        " chars" +
        (fullPayload.partial ? " · partial" : "") +
        (fullPayload.source === "pasteflick" ? " · from PasteFlick" : "");

      textEl = document.createElement("pre");
      textEl.className = "sm-pre";
      textEl.textContent = fullPayload.markdown || "";

      body.appendChild(meta);
      body.appendChild(textEl);
      copySelBtn.disabled = false;
      copyAllBtn.disabled = false;
    } catch (err) {
      loading.textContent = "Couldn't load the thread.";
      showToast(footer, loading.textContent, false);
      return {
        ok: false,
        opened: true,
        error: (err && err.message) || String(err),
      };
    }

    copyAllBtn.addEventListener("click", async () => {
      try {
        const clipped = await writeClipboard(fullPayload.markdown);
        fullPayload.destination = lastDestination;
        fullPayload.format = lastFileFormat;
        const overlayRes = await ingest(fullPayload);
        showToast(
          footer,
          clipped
            ? outcomeMessage("All " + (fullPayload.character_count || 0).toLocaleString() + " chars", overlayRes, clipped)
            : "Clipboard write failed.",
          clipped,
        );
      } catch (err) {
        showToast(footer, (err && err.message) || String(err), false);
      }
    });

    copySelBtn.addEventListener("click", async () => {
      try {
        const selected = selectionInside(textEl);
        if (!selected || selected.length < 1) {
          showToast(footer, "Highlight some text first.", false);
          return;
        }
        const payload = wrapSelection(
          selected,
          fullPayload.title || pageTitle(),
          fullPayload.url || location.href,
          false,
        );
        payload.status_note = "selected in PasteFlick view";
        payload.destination = lastDestination;
        payload.format = lastFileFormat;
        const clipped = await writeClipboard(payload.markdown);
        const overlayRes = await ingest(payload);
        showToast(
          footer,
          clipped
            ? outcomeMessage("Selection", overlayRes, clipped)
            : "Clipboard write failed.",
          clipped,
        );
      } catch (err) {
        showToast(footer, (err && err.message) || String(err), false);
      }
    });

    return {
      ok: true,
      opened: true,
      source: "select-view",
      partial: !!fullPayload.partial,
      turn_count: fullPayload.turn_count || 0,
      character_count: fullPayload.character_count || 0,
      title: fullPayload.title || "",
      note: "",
    };
  }

  function outcomeMessage(label, overlayRes, clipped) {
    if (!clipped) return "Clipboard write failed.";
    if (overlayRes && overlayRes.saved) {
      const name = String(overlayRes.path || "").split(/[/\\]/).pop();
      return name ? label + " saved · " + name : label + " saved.";
    }
    if (overlayRes && overlayRes.pasted) return label + " copied and pasted.";
    if (overlayRes && overlayRes.destination === "cursor") {
      if (!overlayRes.ok) return label + " copied. Couldn't auto-paste.";
      return label + " copied. Couldn't paste into the last app.";
    }
    return label + " copied.";
  }

  async function runCapture(mode, scrollMark, extra) {
    extra = extra || {};
    lastDestination = resolveDestination(extra);
    lastFileFormat = resolveFormat(extra);
    lastCopyExtras = wantsCopyExtras(extra);
    if (mode === "select-view" || mode === "open") {
      return openSelectView();
    }
    if (mode === "open-from-pasteflick") {
      const payload = await extractFromPasteFlick(scrollMark);
      return openSelectView(payload);
    }
    let payload;
    if (mode === "from-pasteflick") {
      payload = await extractFromPasteFlick(scrollMark);
    } else if (mode === "single-message") {
      payload = await extractSingleMessage(extra.target || scrollMark);
    } else if (mode === "copy-fragment") {
      payload = wrapFragment(extra.fragment);
    } else {
      payload = await extractSelectionOrFull(mode !== "full");
    }
    const clipped = await writeClipboard(payload.markdown);
    payload.destination = lastDestination;
    payload.format = lastFileFormat;
    const overlayRes = await ingest(payload);
    return {
      ok: true,
      clipped,
      overlay: !!(overlayRes && overlayRes.ok),
      pasted: !!(overlayRes && overlayRes.pasted),
      saved: !!(overlayRes && overlayRes.saved),
      path: (overlayRes && overlayRes.path) || "",
      destination: lastDestination,
      format: lastFileFormat,
      markdown: lastDestination === "file" ? payload.markdown : "",
      source: payload.source,
      partial: !!payload.partial,
      turn_count: payload.turn_count || 0,
      character_count: payload.character_count || 0,
      title: payload.title || "",
      note: payload.status_note || "",
    };
  }

  window.__transcriptCopy = {
    captureSelection: () => runCapture("selection"),
    captureFull: () => runCapture("full"),
    openSelectView: () => openSelectView(),
    captureFromPasteFlick: (mark) => runCapture("from-pasteflick", mark),
    openFromPasteFlick: (mark) => runCapture("open-from-pasteflick", mark),
    captureMessage: (target, extra) =>
      runCapture("single-message", null, Object.assign({}, extra || {}, { target })),
    captureFragment: (fragment, extra) =>
      runCapture("copy-fragment", null, Object.assign({}, extra || {}, { fragment })),
    getSelectionText: () => getSelectionText().text,
    resolvePasteFlickIndex,
    fingerprintText,
  };

  document.addEventListener("selectionchange", scheduleSelectionCache, true);
  document.addEventListener("mouseup", scheduleSelectionCache, true);
  document.addEventListener("keyup", scheduleSelectionCache, true);
  // Seed once in case the user selected before the script injected.
  scheduleSelectionCache();

  window.addEventListener("message", (event) => {
    if (event.source !== window) return;
    const data = event.data;
    if (!fromExtension(data)) return;
    if (data.type === "grab-file") {
      const grab = globalThis.PasteFlickPrivate && globalThis.PasteFlickPrivate.grabChatFile;
      if (!grab) {
        window.postMessage({ source: PAGE, requestId: data.requestId, result: null }, "*");
        return;
      }
      void grab(data)
        .then((result) => {
          window.postMessage({ source: PAGE, requestId: data.requestId, result: result }, "*");
        })
        .catch(() => {
          window.postMessage({ source: PAGE, requestId: data.requestId, result: null }, "*");
        });
      return;
    }
    if (data.type) return;
    const modes = {
      full: "full",
      selection: "selection",
      "select-view": "select-view",
      open: "select-view",
      "from-pasteflick": "from-pasteflick",
      "open-from-pasteflick": "open-from-pasteflick",
      "single-message": "single-message",
      "copy-fragment": "copy-fragment",
    };
    const mode = modes[data.mode] || "select-view";
    const requestId = data.requestId;
    runCapture(mode, data.scrollMark || null, {
      target: data.target || null,
      fragment: data.fragment || null,
      autoPaste: !!data.autoPaste,
      destination: data.destination || "",
      fileFormat: data.fileFormat || data.format || "",
      copyExtras: data.copyExtras,
    })
      .then((result) => {
        window.postMessage(
          { source: PAGE, requestId, result },
          "*",
        );
      })
      .catch((err) => {
        window.postMessage(
          {
            source: PAGE,
            requestId,
            error: (err && err.message) || String(err),
          },
          "*",
        );
      });
  });
})();
