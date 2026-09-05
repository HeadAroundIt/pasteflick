"""Capture PasteFlick UI photos for the GitHub README."""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "extension"
TESTBED = ROOT / "testbed"
OUT = ROOT / "readme" / "shots"
CHROME = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Google/Chrome/Application/chrome.exe"
EXT_JS = (EXT / "pasteflick.js").read_text(encoding="utf-8")


def _js_concat(name: str) -> str:
    match = re.search(
        rf"const {name} =\s*((?:(?:'[^']*'|\"[^\"]*\")\s*\+\s*)*(?:'[^']*'|\"[^\"]*\"))\s*;",
        EXT_JS,
    )
    if not match:
        raise SystemExit(f"missing {name} in pasteflick.js")
    return "".join(a or b for a, b in re.findall(r"'([^']*)'|\"([^\"]*)\"", match.group(1)))


def _rail_shot_css() -> str:
    key = "const RAIL_CSS = `"
    start = EXT_JS.index(key) + len(key)
    end = EXT_JS.index("`;", start)
    raw = EXT_JS[start:end]
    host = re.search(r":host\s*\{(.*?)\n    \}", raw, re.S)
    if not host:
        raise SystemExit("missing :host in RAIL_CSS")
    vars_only = []
    for line in host.group(1).splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            vars_only.append("      " + stripped)
    rest = raw[host.end() :]
    return (
        ".pf-host {\n"
        + "\n".join(vars_only)
        + "\n    }\n"
        + rest
        + """
    .pf-host [data-pasteflick="pin"] {
      position: relative;
      top: auto;
      left: auto;
      pointer-events: none;
    }
    .pf-host button { cursor: default; }
    .pf-host * { transition: none !important; animation: none !important; }
"""
    )


RAIL_SHOT_CSS = _rail_shot_css()
COPY_SVG = _js_concat("COPY_SVG")
SAVE_SVG = _js_concat("SAVE_SVG")
SEND_SVG = _js_concat("SEND_SVG")
BOOKMARK_SVG = _js_concat("BOOKMARK_SVG")

# Same live chip in the close-up and the how-to.
CHIP_HTML = f"""
    <div class="pf-host">
      <div data-pasteflick="pin" data-kind="thread">
        <div data-pasteflick="head">
          <span data-pasteflick="kicker">PasteFlick</span>
          <button type="button" data-pasteflick="extras" class="on" role="switch">
            <span data-pasteflick="extras-thumb"></span>
          </button>
        </div>
        <div data-pasteflick="actions">
          <button type="button" data-pasteflick="copy-thread" class="is-primary">{COPY_SVG}</button>
          <button type="button" data-pasteflick="save-thread">{SAVE_SVG}</button>
          <button type="button" data-pasteflick="paste-thread">{SEND_SVG}</button>
        </div>
      </div>
    </div>
"""
MARK_ON = f'<button type="button" data-pasteflick="mark" class="is-active" aria-pressed="true">{BOOKMARK_SVG}</button>'
MARK_OFF = f'<button type="button" data-pasteflick="mark" aria-pressed="false">{BOOKMARK_SVG}</button>'


def _count_chip(n: int, total: int) -> str:
    return f'<span data-pasteflick="label">{n} of {total}</span>'


def _mark_pin(btn: str, count: str = "") -> str:
    return (
        '<div data-pasteflick="pin" data-kind="message">'
        f'<div data-pasteflick="actions">{btn}</div>'
        f"{count}"
        "</div>"
    )


MARK_PIN_ON_1 = _mark_pin(MARK_ON, _count_chip(1, 2))
MARK_PIN_ON_2 = _mark_pin(MARK_ON, _count_chip(2, 2))
MARK_PIN_OFF = _mark_pin(MARK_OFF)


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        pass

    def do_GET(self) -> None:  # noqa: N802
        raw = self.path.split("?", 1)[0]
        name = raw.lstrip("/")
        if name in {"extractor.js", "pasteflick.js"}:
            data = (EXT / name).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if name == "shot-select-panel.html":
            html = """<!doctype html>
<html><head><meta charset="utf-8"><style>
html,body{margin:0;background:transparent;}
.panel{
  box-sizing:border-box;width:420px;height:480px;
  display:flex;flex-direction:column;
  background:color-mix(in srgb,#c9a66a 8%,#f7f7f5);color:#5c4a2e;
  border-radius:10px;border:1px solid rgba(201,166,106,.22);
  font-family:"Segoe UI Variable Text",Segoe UI,system-ui,sans-serif;
  font-weight:450;letter-spacing:-.011em;overflow:hidden;
}
.titlebar{
  display:flex;align-items:center;justify-content:space-between;gap:8px;
  padding:10px 16px 8px;min-height:44px;flex:none;
  box-shadow:inset 0 -1px 0 rgba(201,166,106,.22);
}
.brand{
  padding:3px 8px;font:650 12px/1.2 inherit;letter-spacing:-.01em;
  color:#171410;border-radius:6px;background:rgba(201,166,106,.48);
  box-shadow:inset 0 1px 0 rgba(244,226,180,.35);
}
.chrome{display:flex;align-items:center;gap:2px;}
.ghost{
  width:28px;height:28px;border:0;border-radius:7px;background:transparent;
  color:#8a7358;display:grid;place-items:center;
}
.body{
  flex:1;overflow:hidden;padding:16px;
  background:color-mix(in srgb,#c9a66a 6%,#f7f7f5);
}
.meta{margin:0 0 12px;font-size:11px;color:#8a7358;}
.pre{
  margin:0;white-space:pre-wrap;font-family:ui-monospace,Cascadia Mono,Consolas,monospace;
  font-size:12.5px;line-height:1.45;color:#5c4a2e;
}
.foot{
  padding:12px 16px;flex:none;
  box-shadow:inset 0 1px 0 rgba(201,166,106,.22);
}
.row{display:flex;flex-wrap:wrap;gap:8px;}
.btn{
  height:34px;padding:0 14px;border-radius:7px;
  border:1px solid rgba(201,166,106,.22);
  background:color-mix(in srgb,#c9a66a 6%,#f7f7f5);color:#5c4a2e;
  font:650 13px/1 inherit;
}
.btn.primary{
  background:rgba(201,166,106,.4);border-color:transparent;color:#171410;
  box-shadow:inset 0 1px 0 rgba(244,226,180,.35);
}
</style></head>
<body>
  <div class="panel">
    <div class="titlebar">
      <span class="brand">PasteFlick</span>
      <div class="chrome">
        <span class="ghost" aria-hidden="true"><svg viewBox="0 0 24 24" width="18" height="18"><circle cx="12" cy="12" r="3.05" fill="none" stroke="currentColor" stroke-width="1.85"/><path fill="none" stroke="currentColor" stroke-width="1.85" stroke-linecap="round" d="M12 3.7v2.15M12 18.15v2.15M3.7 12h2.15M18.15 12h2.15M6.22 6.22l1.52 1.52M16.26 16.26l1.52 1.52M6.22 17.78l1.52-1.52M16.26 7.74l1.52-1.52"/></svg></span>
        <span class="ghost" aria-hidden="true">✕</span>
      </div>
    </div>
    <div class="body">
      <p class="meta">Friday note · 3 turns · 1,240 chars</p>
      <pre class="pre">You
Can you draft the Friday note?

Assistant
Here's a first pass you can drop in as-is.

You
Make it two sentences, and keep the Friday deadline.</pre>
    </div>
    <div class="foot">
      <div class="row">
        <span class="btn primary">Copy selection</span>
        <span class="btn">Copy all</span>
        <span class="btn">Save .md</span>
      </div>
    </div>
  </div>
</body></html>"""
            data = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if name == "shot-pair.html":
            html = """<!doctype html>
<html><head><meta charset="utf-8"><style>
html,body{margin:0;height:100%;background:transparent;}
.stage{
  box-sizing:border-box;
  width:100%;
  height:100%;
  display:flex;
  align-items:center;
  justify-content:center;
  gap:24px;
  padding:16px 28px;
  background:#3a3228;
  border-radius:16px;
}
iframe{
  border:0;
  border-radius:10px;
  overflow:hidden;
  background:transparent;
}
.view{width:420px;height:480px;}
.settings{width:300px;height:560px;}
</style></head>
<body>
  <div class="stage">
    <iframe class="view" src="/shot-select-panel.html" title="Selection view" scrolling="no"></iframe>
    <iframe class="settings" src="/popup-settings.html?shot=1" title="Settings" scrolling="no"></iframe>
  </div>
  <script>
    function fit(frame) {
      const doc = frame.contentDocument;
      if (!doc) return;
      const shell = doc.querySelector(".shell") || doc.querySelector(".panel");
      if (!shell) return;
      const h = Math.ceil(shell.getBoundingClientRect().height);
      if (h > 8) frame.style.height = h + "px";
    }
    function all() {
      document.querySelectorAll("iframe").forEach(fit);
    }
    document.querySelectorAll("iframe").forEach((frame) => {
      frame.addEventListener("load", () => fit(frame));
    });
    setInterval(all, 120);
  </script>
</body></html>"""
            data = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if name == "shot-chip.html":
            html = f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
html,body{{margin:0;width:152px;height:96px;background:transparent;}}
.stage{{
  box-sizing:border-box;
  width:152px;
  height:96px;
  display:flex;
  align-items:center;
  justify-content:center;
  padding:16px;
  background:#3a3228;
  border-radius:14px;
}}
{RAIL_SHOT_CSS}
</style></head>
<body>
  <div class="stage">
{CHIP_HTML}
  </div>
</body></html>"""
            data = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if name in {"shot-popup.html", "shot-settings.html"}:
            if name == "shot-popup.html":
                inner, w, h, pad = "/popup.html?shot=1", 300, 200, 16
            else:
                inner, w, h, pad = "/popup-settings.html?shot=1", 300, 560, 16
            html = f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
html,body{{margin:0;height:100%;background:transparent;}}
.stage{{
  box-sizing:border-box;
  width:100%;
  height:100%;
  display:flex;
  align-items:center;
  justify-content:center;
  padding:{pad}px;
  background:#3a3228;
  border-radius:16px;
}}
iframe{{border:0;width:{w}px;height:{h}px;border-radius:10px;overflow:hidden;background:transparent;}}
</style></head>
<body>
  <div class="stage"><iframe src="{inner}" scrolling="no"></iframe></div>
  <script>
    function fit() {{
      const frame = document.querySelector("iframe");
      const doc = frame && frame.contentDocument;
      const shell = doc && doc.querySelector(".shell");
      if (!shell) return;
      const h = Math.ceil(shell.getBoundingClientRect().height);
      if (h > 8) frame.style.height = h + "px";
    }}
    document.querySelector("iframe").addEventListener("load", fit);
    setInterval(fit, 120);
  </script>
</body></html>"""
            data = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if name == "shot-chat.html":
            html = f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
html,body{{margin:0;width:840px;height:520px;background:transparent;}}
.stage{{
  box-sizing:border-box;
  width:840px;height:520px;
  padding:24px;
  background:#3a3228;
  border-radius:16px;
}}
.chat{{
  box-sizing:border-box;
  width:100%;height:100%;
  display:grid;
  grid-template-columns:max-content 100px 32px minmax(0,1fr);
  grid-template-rows:auto auto auto auto;
  column-gap:0;
  row-gap:14px;
  align-items:center;
  align-content:center;
  padding:28px 30px 28px 22px;
  overflow:visible;
  background:#f8f8f8;
  border-radius:16px;
  color:#171410;
  font-family:"Segoe UI Variable Text","Segoe UI",system-ui,sans-serif;
  letter-spacing:-0.011em;
}}
.title{{
  grid-column:4;grid-row:1;
  margin:0 0 2px;
  font:650 15px/1.2 inherit;
  letter-spacing:-0.02em;
  color:#5c4a2e;
}}
.chip-slot{{
  grid-column:1;grid-row:2 / 5;
  align-self:center;
  display:flex;
  align-items:center;
  z-index:2;
}}
.chip-slot .pf-host{{zoom:1.62;flex:none;}}
.stem{{
  flex:none;
  width:20px;
  height:2px;
  margin-left:4px;
  background:#c9a66a;
  border-radius:1px;
}}
{RAIL_SHOT_CSS}
.guide{{
  position:relative;
  align-self:stretch;
  color:#c9a66a;
}}
.guide.one{{grid-column:2;grid-row:2;}}
.guide.skip{{grid-column:2;grid-row:3;}}
.guide.more{{grid-column:2;grid-row:4;}}
.v{{
  position:absolute;
  left:0;
  width:2px;
  background:currentColor;
  border-radius:1px;
}}
.guide.one .v{{top:50%;bottom:0;}}
.guide.skip .v{{top:0;bottom:0;}}
.guide.more .v{{top:0;height:50%;}}
.arm{{
  position:absolute;
  left:0;right:8px;
  top:50%;
  margin-top:-1px;
  height:2px;
  display:flex;
  align-items:center;
  color:#c9a66a;
}}
.arm .seg{{
  flex:1 1 0;
  min-width:6px;
  height:2px;
  background:currentColor;
  border-radius:1px;
}}
.arm .cap{{
  flex:none;
  padding:0 8px;
  margin:0;
  background:#f8f8f8;
  font:650 11px/1 inherit;
  letter-spacing:-0.02em;
  color:#171410;
  white-space:nowrap;
  transform:translateY(-3px);
}}
.arm svg{{
  display:block;
  flex:none;
  width:9px;height:9px;
  margin-left:1px;
}}
.mark-wrap{{
  width:44px;
  min-height:32px;
  display:flex;
  justify-content:center;
  align-items:flex-start;
  overflow:visible;
}}
.mark-wrap.one{{grid-column:3;grid-row:2;}}
.mark-wrap.skip{{grid-column:3;grid-row:3;}}
.mark-wrap.more{{grid-column:3;grid-row:4;}}
.chat [data-pasteflick="mark"].is-active{{
  background:var(--chip);
  box-shadow:inset 0 1px 0 rgba(244,226,180,.35);
}}
.msg{{
  box-sizing:border-box;
  min-width:0;
  max-width:328px;
  margin:0;
  margin-left:16px;
  padding:12px 14px;
  border-radius:16px;
  line-height:1.45;
  font-size:13px;
}}
.msg.one,.msg.more{{
  grid-column:4;
  background:#fff;
  color:#171410;
  border:1.5px solid rgba(201,166,106,.7);
  box-shadow:0 0 0 1px rgba(33,28,22,.35);
}}
.msg.one{{grid-row:2;}}
.msg.more{{grid-row:4;}}
.msg.skip{{
  grid-column:4;grid-row:3;
  background:#f3f1ea;
  color:#8a7358;
  border:1px solid rgba(201,166,106,.22);
  box-shadow:0 1px 3px rgba(50,40,20,.05);
  border-radius:10px;
}}
.role{{
  display:inline-block;margin:0 0 8px;padding:2px 6px;
  font:650 10px/1.2 inherit;
  color:#171410;border-radius:6px;
  background:rgba(201,166,106,.48);
  box-shadow:inset 0 1px 0 rgba(244,226,180,.35);
}}
.msg.skip .role{{
  background:rgba(201,166,106,.22);
  box-shadow:none;
  color:#8a7358;
}}
</style></head>
<body>
  <div class="stage">
    <div class="chat pf-host">
      <p class="title">Friday update</p>
      <div class="chip-slot">
{CHIP_HTML}
        <span class="stem" aria-hidden="true"></span>
      </div>
      <div class="guide one" aria-hidden="true">
        <span class="v"></span>
        <div class="arm">
          <span class="seg"></span>
          <span class="cap">one</span>
          <span class="seg"></span>
          <svg viewBox="0 0 10 10"><path d="M1.5 1.5 8.5 5 1.5 8.5" fill="none" stroke="currentColor" stroke-width="1.85" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </div>
      </div>
      <div class="mark-wrap one">{MARK_PIN_ON_1}</div>
      <div class="msg one"><span class="role">You</span><div>Can you turn this into a short note I can paste into Slack?</div></div>
      <div class="guide skip" aria-hidden="true"><span class="v"></span></div>
      <div class="mark-wrap skip">{MARK_PIN_OFF}</div>
      <div class="msg skip"><span class="role">Assistant</span><div>Here's a first pass you can drop in as-is.</div></div>
      <div class="guide more" aria-hidden="true">
        <span class="v"></span>
        <div class="arm">
          <span class="seg"></span>
          <span class="cap">or more</span>
          <span class="seg"></span>
          <svg viewBox="0 0 10 10"><path d="M1.5 1.5 8.5 5 1.5 8.5" fill="none" stroke="currentColor" stroke-width="1.85" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </div>
      </div>
      <div class="mark-wrap more">{MARK_PIN_ON_2}</div>
      <div class="msg more"><span class="role">You</span><div>Make it two sentences, and keep the Friday deadline.</div></div>
    </div>
  </div>
</body></html>"""
            data = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if name == "popup-settings.html":
            html = (EXT / "popup.html").read_text(encoding="utf-8")
            html = html.replace("<html lang=\"en\">", "<html lang=\"en\" class=\"shot\">", 1)
            html = html.replace('id="view-home"', 'id="view-home" hidden', 1)
            html = html.replace('id="view-settings" hidden', 'id="view-settings"', 1)
            ver = json.loads((EXT / "manifest.json").read_text(encoding="utf-8")).get("version", "")
            html = html.replace('id="version"></p>', f'id="version">PasteFlick {ver}</p>', 1)
            data = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if name == "mock-chatgpt.html" or name.startswith("c/"):
            target = TESTBED / "mock-chatgpt.html"
            data = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if name.startswith("icons/"):
            path = EXT / name
            if path.is_file():
                data = path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
        if name in {"popup.html", "setup.html"}:
            path = EXT / name
            html = path.read_text(encoding="utf-8")
            if name == "popup.html" and "shot=1" in self.path:
                html = html.replace("<html lang=\"en\">", "<html lang=\"en\" class=\"shot\">", 1)
            data = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self.send_error(404)


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def shot(url: str, dest: Path, width: int, height: int, bg: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp.png")
    cmd = [
        str(CHROME),
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-first-run",
        "--force-device-scale-factor=2",
        f"--window-size={width},{height}",
        f"--default-background-color={bg}",
        f"--screenshot={tmp}",
        "--virtual-time-budget=5000",
        url,
    ]
    subprocess.run(cmd, check=True, cwd=str(ROOT))
    tmp.replace(dest)
    print(dest.name, dest.stat().st_size)


def main() -> None:
    if not CHROME.is_file():
        raise SystemExit("Chrome not found")
    port = free_port()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.2)
    base = f"http://127.0.0.1:{port}"
    try:
        # New filenames so GitHub doesn't serve stale shots.
        shot(f"{base}/shot-chip.html?v=22", OUT / "the-chip.png", 152, 96, "00000000")
        shot(f"{base}/shot-pair.html?v=16", OUT / "view-and-settings.png", 840, 620, "00000000")
        shot(f"{base}/shot-popup.html?v=17", OUT / "panel-main.png", 332, 240, "00000000")
        shot(f"{base}/shot-settings.html?v=16", OUT / "panel-settings.png", 332, 656, "00000000")
        shot(f"{base}/shot-chat.html?v=28", OUT / "marks-in-order.png", 840, 540, "00000000")
    finally:
        httpd.shutdown()
    print("ok")


if __name__ == "__main__":
    main()
