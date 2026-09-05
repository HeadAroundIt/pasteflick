"""Capture PasteFlick UI photos for the GitHub README."""

from __future__ import annotations

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
MARK_ON = f'<button type="button" data-pasteflick="mark" class="is-active is-multi" aria-pressed="true">{BOOKMARK_SVG}</button>'
MARK_OFF = f'<button type="button" data-pasteflick="mark" aria-pressed="false">{BOOKMARK_SVG}</button>'


def _mark_pin(btn: str) -> str:
    return (
        '<div data-pasteflick="pin" data-kind="message">'
        f'<div data-pasteflick="actions">{btn}</div>'
        "</div>"
    )


MARK_PIN_ON = _mark_pin(MARK_ON)
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
  padding:16px 32px;
  background:#3a3228;
  border-radius:16px;
}
iframe{
  border:0;
  width:300px;
  border-radius:10px;
  overflow:hidden;
  background:transparent;
}
.home{height:336px;}
.settings{height:584px;}
</style></head>
<body>
  <div class="stage">
    <iframe class="home" src="/popup.html?shot=1" title="Popup"></iframe>
    <iframe class="settings" src="/popup-settings.html?shot=1" title="Settings"></iframe>
  </div>
  <script>
    function fit(frame) {
      const doc = frame.contentDocument;
      if (!doc) return;
      const shell = doc.querySelector(".shell");
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
                inner, w, h, pad = "/popup.html?shot=1", 300, 336, 16
            else:
                inner, w, h, pad = "/popup-settings.html?shot=1", 300, 584, 16
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
  <div class="stage"><iframe src="{inner}"></iframe></div>
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
html,body{{margin:0;width:840px;height:540px;background:transparent;}}
.stage{{
  box-sizing:border-box;
  width:840px;height:540px;
  padding:24px;
  background:#3a3228;
  border-radius:16px;
}}
.chat{{
  box-sizing:border-box;
  width:100%;height:100%;
  display:grid;
  grid-template-columns:max-content 96px minmax(0,1fr);
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
  grid-column:3;grid-row:1;
  margin:0 0 2px;
  padding-left:56px;
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
  left:0;right:4px;
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
.turn{{
  display:grid;
  grid-template-columns:32px minmax(0,1fr);
  column-gap:12px;
  align-items:center;
  box-sizing:border-box;
  min-width:0;
  padding:12px 14px 12px 12px;
  border-radius:16px;
  border:1.5px solid transparent;
}}
.turn.one{{grid-column:3;grid-row:2;}}
.turn.skip{{grid-column:3;grid-row:3;}}
.turn.more{{grid-column:3;grid-row:4;}}
.turn.on{{
  background:#fff;
  border-color:rgba(201,166,106,.7);
  box-shadow:0 0 0 1px rgba(33,28,22,.35);
}}
.mark-wrap{{
  width:32px;
  height:32px;
  display:grid;
  place-items:center;
}}
.msg{{
  box-sizing:border-box;
  min-width:0;
  margin:0;
  padding:12px 14px;
  border-radius:10px;
  line-height:1.45;
  font-size:13px;
  background:color-mix(in srgb, #c9a66a 8%, #fff);
  color:#171410;
}}
.turn.skip .msg{{
  background:#f3f1ea;
  color:#8a7358;
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
      <div class="turn one on">
        <div class="mark-wrap">{MARK_PIN_ON}</div>
        <div class="msg"><span class="role">You</span><div>Can you turn this into a short note I can paste into Slack?</div></div>
      </div>
      <div class="guide skip" aria-hidden="true"><span class="v"></span></div>
      <div class="turn skip">
        <div class="mark-wrap">{MARK_PIN_OFF}</div>
        <div class="msg"><span class="role">Assistant</span><div>Here's a first pass you can drop in as-is.</div></div>
      </div>
      <div class="guide more" aria-hidden="true">
        <span class="v"></span>
        <div class="arm">
          <span class="seg"></span>
          <span class="cap">or more</span>
          <span class="seg"></span>
          <svg viewBox="0 0 10 10"><path d="M1.5 1.5 8.5 5 1.5 8.5" fill="none" stroke="currentColor" stroke-width="1.85" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </div>
      </div>
      <div class="turn more on">
        <div class="mark-wrap">{MARK_PIN_ON}</div>
        <div class="msg"><span class="role">You</span><div>Make it two sentences, and keep the Friday deadline.</div></div>
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
        if name == "popup-settings.html":
            html = (EXT / "popup.html").read_text(encoding="utf-8")
            html = html.replace("<html lang=\"en\">", "<html lang=\"en\" class=\"shot\">", 1)
            html = html.replace('id="view-home"', 'id="view-home" hidden', 1)
            html = html.replace('id="view-settings" hidden', 'id="view-settings"', 1)
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
        shot(f"{base}/shot-pair.html?v=13", OUT / "the-panels.png", 688, 616, "00000000")
        shot(f"{base}/shot-popup.html?v=13", OUT / "panel-main.png", 332, 368, "00000000")
        shot(f"{base}/shot-settings.html?v=13", OUT / "panel-settings.png", 332, 616, "00000000")
        shot(f"{base}/shot-chat.html?v=25", OUT / "the-pick.png", 840, 540, "00000000")
    finally:
        httpd.shutdown()
    print("ok")


if __name__ == "__main__":
    main()
