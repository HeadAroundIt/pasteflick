"""Capture PasteFlick UI photos for the GitHub README."""

from __future__ import annotations

import os
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

# Same chip in the close-up and the how-to. Keep these in lockstep.
CHIP_CSS = """
.chip{
  display:flex;
  flex-direction:column;
  gap:4px;
  width:max-content;
  max-width:148px;
  padding:5px 5px 4px;
  color:#5c4a2e;
  border-radius:10px;
  background:color-mix(in srgb, #c9a66a 8%, #f7f7f5);
  border:1px solid rgba(201,166,106,.22);
  box-shadow:0 1px 3px rgba(50,40,20,.05);
}
.head{display:flex;align-items:center;justify-content:space-between;gap:4px;min-width:0;}
.kicker{
  flex:none;
  padding:2px 6px;
  font:650 10px/1.2 "Segoe UI Variable Text","Segoe UI",system-ui,sans-serif;
  letter-spacing:-0.01em;
  color:#171410;
  border-radius:6px;
  background:rgba(201,166,106,.48);
  box-shadow:inset 0 1px 0 rgba(244,226,180,.35);
}
.extras{
  position:relative;flex:none;
  width:22px;height:12px;
  border:1px solid rgba(201,166,106,.28);
  border-radius:6px;
  background:rgba(201,166,106,.4);
  box-shadow:inset 0 1px 0 rgba(244,226,180,.12);
}
.extras span{
  position:absolute;top:1px;left:11px;
  width:8px;height:8px;border-radius:4px;background:#171410;
}
.actions{display:flex;align-items:center;gap:2px;}
.actions i{
  width:24px;height:24px;border-radius:7px;
  display:grid;place-items:center;
  background:rgba(201,166,106,.4);
  color:#171410;
  box-shadow:inset 0 1px 0 rgba(244,226,180,.35);
}
.actions svg{display:block;width:13px;height:13px;}
"""

CHIP_HTML = """
    <div class="chip">
      <div class="head"><span class="kicker">PasteFlick</span><span class="extras"><span></span></span></div>
      <div class="actions">
        <i><svg viewBox="0 0 24 24"><rect x="8" y="8" width="11" height="13" rx="2" fill="none" stroke="currentColor" stroke-width="1.75"/><path d="M5 16V5a2 2 0 0 1 2-2h9" fill="none" stroke="currentColor" stroke-width="1.75"/></svg></i>
        <i><svg viewBox="0 0 24 24"><path d="M12 4v10" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/><path d="M8 10l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/><path d="M5 18h14" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/></svg></i>
        <i><svg viewBox="0 0 24 24"><path d="M5 12h11" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/><path d="M12 6l7 6-7 6" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/></svg></i>
      </div>
    </div>
"""


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
html,body{{margin:0;width:114px;height:66px;background:transparent;}}
.stage{{
  box-sizing:border-box;
  width:114px;
  height:66px;
  display:flex;
  align-items:center;
  justify-content:center;
  padding:6px;
  background:#3a3228;
  border-radius:10px;
}}
{CHIP_CSS}
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
html,body{{margin:0;width:784px;height:420px;background:transparent;}}
.stage{{
  box-sizing:border-box;
  width:784px;height:420px;
  padding:32px;
  background:#3a3228;
  border-radius:16px;
}}
.chat{{
  box-sizing:border-box;
  width:100%;height:100%;
  display:grid;
  grid-template-columns:max-content 40px max-content minmax(0,1fr);
  grid-template-rows:auto auto auto;
  column-gap:14px;
  row-gap:28px;
  align-items:center;
  align-content:center;
  padding:28px 40px 28px 28px;
  overflow:visible;
  background:#f7f7f5;
  border-radius:16px;
  color:#171410;
  font-family:"Segoe UI Variable Text","Segoe UI",system-ui,sans-serif;
  letter-spacing:-0.011em;
}}
.title{{
  grid-column:4;grid-row:1;
  margin:0 0 4px;
  font:650 15px/1.2 inherit;
  letter-spacing:-0.02em;
  color:#5c4a2e;
}}
.chip-slot{{
  grid-column:1;grid-row:2;
  z-index:2;
}}
{CHIP_CSS}
.arrow{{
  grid-column:2;grid-row:2;
  display:grid;
  place-items:center;
  color:#c9a66a;
}}
.arrow svg{{display:block;}}
.mark-wrap{{
  position:relative;
  width:30px;
  height:30px;
  display:grid;
  place-items:center;
}}
.mark-wrap.one{{grid-column:3;grid-row:2;}}
.mark-wrap.more{{grid-column:3;grid-row:3;}}
.mark{{
  box-sizing:border-box;
  width:30px;height:30px;border-radius:9px;
  display:grid;place-items:center;
  background:rgba(201,166,106,.55);
  color:#171410;
  box-shadow:
    0 0 0 2px #c9a66a,
    0 0 0 5px rgba(201,166,106,.28),
    inset 0 1px 0 rgba(244,226,180,.35);
}}
.mark svg{{display:block;}}
.mark svg path{{fill:currentColor;}}
.hint{{
  position:absolute;
  top:calc(100% + 5px);
  left:50%;
  transform:translateX(-50%);
  padding:2px 6px;
  font:650 10px/1.2 inherit;
  letter-spacing:-0.01em;
  color:#171410;
  border-radius:6px;
  background:rgba(201,166,106,.48);
  box-shadow:inset 0 1px 0 rgba(244,226,180,.35);
  white-space:nowrap;
}}
.msg{{
  box-sizing:border-box;
  min-width:0;
  max-width:348px;
  margin:0;
  padding:12px 14px;
  border-radius:10px;
  border:1px solid rgba(201,166,106,.22);
  box-shadow:0 1px 3px rgba(50,40,20,.05);
  line-height:1.45;
  font-size:13px;
}}
.msg.user{{grid-column:4;grid-row:2;background:color-mix(in srgb, #c9a66a 12%, #f7f7f5);color:#171410;}}
.msg.asst{{grid-column:4;grid-row:3;background:#f3f1ea;color:#5c4a2e;}}
.role{{
  display:inline-block;margin:0 0 8px;padding:2px 6px;
  font:650 10px/1.2 inherit;
  color:#171410;border-radius:6px;
  background:rgba(201,166,106,.48);
  box-shadow:inset 0 1px 0 rgba(244,226,180,.35);
}}
</style></head>
<body>
  <div class="stage">
    <div class="chat">
      <p class="title">Friday update</p>
      <div class="chip-slot">
{CHIP_HTML}
      </div>
      <div class="arrow" aria-hidden="true">
        <svg viewBox="0 0 40 24" width="36" height="22">
          <path d="M3 12h26" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          <path d="M23 5.5 35 12l-12 6.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
      <div class="mark-wrap one">
        <div class="mark">
          <svg viewBox="0 0 24 24" width="14" height="14"><path fill="none" stroke="currentColor" stroke-width="1.75" stroke-linejoin="round" d="M7 3.75h10A1.25 1.25 0 0 1 18.25 5v16.25L12 17.5l-6.25 3.75V5A1.25 1.25 0 0 1 7 3.75z"/></svg>
        </div>
        <span class="hint">one</span>
      </div>
      <div class="msg user"><span class="role">You</span><div>Can you turn this into a short note I can paste into Slack?</div></div>
      <div class="mark-wrap more">
        <div class="mark">
          <svg viewBox="0 0 24 24" width="14" height="14"><path fill="none" stroke="currentColor" stroke-width="1.75" stroke-linejoin="round" d="M7 3.75h10A1.25 1.25 0 0 1 18.25 5v16.25L12 17.5l-6.25 3.75V5A1.25 1.25 0 0 1 7 3.75z"/></svg>
        </div>
        <span class="hint">or more</span>
      </div>
      <div class="msg asst"><span class="role">Assistant</span><div>Bookmark one message, or a few. Copy on the chip takes that stretch.</div></div>
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
        shot(f"{base}/shot-chip.html?v=10", OUT / "badge.png", 114, 66, "00000000")
        shot(f"{base}/shot-pair.html?v=10", OUT / "popup-pair.png", 688, 616, "00000000")
        shot(f"{base}/shot-popup.html?v=10", OUT / "panel-main.png", 332, 368, "00000000")
        shot(f"{base}/shot-settings.html?v=10", OUT / "panel-settings.png", 332, 616, "00000000")
        shot(f"{base}/shot-chat.html?v=10", OUT / "copy-from.png", 784, 420, "00000000")
    finally:
        httpd.shutdown()
    print("ok")


if __name__ == "__main__":
    main()
