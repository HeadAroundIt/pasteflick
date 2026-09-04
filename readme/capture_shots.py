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
  align-items:flex-start;
  justify-content:center;
  gap:24px;
  padding:24px;
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
.settings{height:636px;}
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
            html = """<!doctype html>
<html><head><meta charset="utf-8"><style>
html,body{margin:0;width:400px;height:200px;background:transparent;}
.stage{
  box-sizing:border-box;
  width:400px;
  height:200px;
  display:flex;
  align-items:stretch;
  justify-content:stretch;
  padding:10px;
  background:#3a3228;
  border-radius:16px;
}
.chip{
  display:flex;
  flex-direction:column;
  justify-content:space-between;
  gap:12px;
  flex:1;
  min-width:0;
  min-height:0;
  padding:8px;
  color:#5c4a2e;
  border-radius:12px;
  background:color-mix(in srgb, #c9a66a 8%, #f7f7f5);
  border:1px solid rgba(201,166,106,.22);
  box-shadow:0 1px 3px rgba(50,40,20,.05);
}
.head{display:flex;align-items:stretch;justify-content:space-between;gap:10px;}
.kicker{
  flex:1;
  display:grid;
  place-items:center;
  padding:8px 12px;
  font:650 18px/1.2 "Segoe UI Variable Text","Segoe UI",system-ui,sans-serif;
  letter-spacing:-0.01em;
  color:#171410;
  border-radius:8px;
  background:rgba(201,166,106,.48);
  box-shadow:inset 0 1px 0 rgba(244,226,180,.35);
}
.extras{
  position:relative;
  flex:none;
  align-self:center;
  width:42px;height:22px;
  border:1px solid rgba(201,166,106,.28);
  border-radius:11px;
  background:rgba(23,20,16,.22);
  box-shadow:inset 0 1px 0 rgba(244,226,180,.12);
}
.extras span{
  position:absolute;top:4px;left:4px;
  width:12px;height:12px;border-radius:6px;background:#e4d2ae;
}
.actions{display:flex;align-items:stretch;gap:8px;flex:1;min-height:0;}
.actions i{
  flex:1;
  min-height:0;
  border-radius:10px;
  display:grid;place-items:center;
  background:rgba(201,166,106,.4);
  color:#171410;
  box-shadow:inset 0 1px 0 rgba(244,226,180,.35);
}
.actions svg{display:block;width:22px;height:22px;}
</style></head>
<body>
  <div class="stage">
    <div class="chip">
      <div class="head"><span class="kicker">PasteFlick</span><span class="extras"><span></span></span></div>
      <div class="actions">
        <i><svg viewBox="0 0 24 24" width="18" height="18"><rect x="8" y="8" width="11" height="13" rx="2" fill="none" stroke="currentColor" stroke-width="1.75"/><path d="M5 16V5a2 2 0 0 1 2-2h9" fill="none" stroke="currentColor" stroke-width="1.75"/></svg></i>
        <i><svg viewBox="0 0 24 24" width="18" height="18"><path d="M12 4v10" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/><path d="M8 10l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/><path d="M5 18h14" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/></svg></i>
        <i><svg viewBox="0 0 24 24" width="18" height="18"><path d="M5 12h11" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/><path d="M12 6l7 6-7 6" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/></svg></i>
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
        if name in {"shot-popup.html", "shot-settings.html"}:
            if name == "shot-popup.html":
                inner, w, h, pad = "/popup.html?shot=1", 300, 336, 20
            else:
                inner, w, h, pad = "/popup-settings.html?shot=1", 300, 636, 20
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
iframe{{border:0;width:{w}px;height:{h}px;border-radius:16px;overflow:hidden;background:transparent;}}
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
            html = """<!doctype html>
<html><head><meta charset="utf-8"><style>
html,body{margin:0;width:784px;height:420px;background:transparent;}
.stage{
  box-sizing:border-box;
  width:784px;height:420px;
  padding:32px;
  background:#3a3228;
  border-radius:16px;
}
.chat{
  box-sizing:border-box;
  width:100%;height:100%;
  display:grid;
  grid-template-columns:max-content 52px max-content minmax(0,1fr);
  grid-template-rows:auto auto auto;
  column-gap:0;
  row-gap:14px;
  align-items:center;
  align-content:center;
  padding:28px 48px 28px 28px;
  background:#f7f7f5;
  border-radius:16px;
  color:#171410;
  font-family:"Segoe UI Variable Text","Segoe UI",system-ui,sans-serif;
  letter-spacing:-0.011em;
}
.title{
  grid-column:4;grid-row:1;
  margin:0 0 4px;
  font:650 15px/1.2 inherit;
  letter-spacing:-0.02em;
  color:#5c4a2e;
}
.chip{
  grid-column:1;grid-row:2;
  display:flex;flex-direction:column;gap:6px;
  width:max-content;
  padding:8px 8px 7px;
  border-radius:12px;
  background:color-mix(in srgb, #c9a66a 8%, #f7f7f5);
  border:1px solid rgba(201,166,106,.22);
  box-shadow:
    0 0 0 3px #c9a66a,
    0 0 0 7px rgba(201,166,106,.28),
    0 8px 18px rgba(50,40,20,.16);
}
.head{display:flex;align-items:center;justify-content:space-between;gap:6px;}
.kicker{
  padding:3px 8px;
  font:650 12px/1.2 inherit;
  color:#171410;
  border-radius:6px;
  background:rgba(201,166,106,.48);
  box-shadow:inset 0 1px 0 rgba(244,226,180,.35);
}
.extras{
  position:relative;width:26px;height:14px;
  border:1px solid rgba(201,166,106,.28);
  border-radius:7px;
  background:rgba(23,20,16,.22);
}
.extras span{
  position:absolute;top:2px;left:2px;
  width:8px;height:8px;border-radius:4px;background:#e4d2ae;
}
.actions{display:flex;align-items:center;gap:4px;}
.actions i{
  width:28px;height:28px;border-radius:8px;
  display:grid;place-items:center;
  background:rgba(201,166,106,.4);
  color:#171410;
  box-shadow:inset 0 1px 0 rgba(244,226,180,.35);
}
.arrow{
  grid-column:2;grid-row:2;
  display:flex;
  align-items:center;
  justify-content:center;
  width:52px;height:36px;
  filter:drop-shadow(0 1px 0 #5c4a2e);
}
.arrow .shaft{
  width:26px;height:6px;
  background:#c9a66a;
  border-radius:3px 0 0 3px;
  box-shadow:0 0 0 1.5px #5c4a2e;
}
.arrow .head{
  width:0;height:0;
  border-top:9px solid transparent;
  border-bottom:9px solid transparent;
  border-left:14px solid #c9a66a;
  filter:drop-shadow(1px 0 0 #5c4a2e);
}
.mark{
  width:30px;height:30px;border-radius:9px;
  display:grid;place-items:center;
  background:rgba(201,166,106,.4);
  color:#171410;
  box-shadow:inset 0 1px 0 rgba(244,226,180,.35);
}
.mark svg{display:block;}
.mark.on{
  grid-column:3;grid-row:2;
  background:rgba(201,166,106,.55);
  box-shadow:
    0 0 0 3px #c9a66a,
    0 0 0 7px rgba(201,166,106,.28),
    0 8px 18px rgba(50,40,20,.16),
    inset 0 1px 0 rgba(244,226,180,.35);
}
.mark.on svg path{fill:currentColor;}
.mark.off{
  grid-column:3;grid-row:3;
  opacity:.5;
}
.user{grid-column:4;grid-row:2;}
.asst{grid-column:4;grid-row:3;}
.msg{
  max-width:380px;
  margin:0;
  padding:12px 14px;
  border-radius:10px;
  border:1px solid rgba(201,166,106,.22);
  box-shadow:0 1px 3px rgba(50,40,20,.05);
  line-height:1.45;
  font-size:13px;
}
.user .msg{background:color-mix(in srgb, #c9a66a 12%, #f7f7f5);color:#171410;}
.asst .msg{background:#f3f1ea;color:#5c4a2e;}
.role{
  display:inline-block;margin:0 0 8px;padding:2px 6px;
  font:650 10px/1.2 inherit;
  color:#171410;border-radius:6px;
  background:rgba(201,166,106,.48);
  box-shadow:inset 0 1px 0 rgba(244,226,180,.35);
}
</style></head>
<body>
  <div class="stage">
    <div class="chat">
      <p class="title">Friday update</p>
      <div class="chip">
        <div class="head"><span class="kicker">PasteFlick</span><span class="extras"><span></span></span></div>
        <div class="actions">
          <i><svg viewBox="0 0 24 24" width="13" height="13"><rect x="8" y="8" width="11" height="13" rx="2" fill="none" stroke="currentColor" stroke-width="1.75"/><path d="M5 16V5a2 2 0 0 1 2-2h9" fill="none" stroke="currentColor" stroke-width="1.75"/></svg></i>
          <i><svg viewBox="0 0 24 24" width="13" height="13"><path d="M12 4v10" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/><path d="M8 10l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/><path d="M5 18h14" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/></svg></i>
          <i><svg viewBox="0 0 24 24" width="13" height="13"><path d="M5 12h11" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/><path d="M12 6l7 6-7 6" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/></svg></i>
        </div>
      </div>
      <div class="arrow" aria-hidden="true"><span class="shaft"></span><span class="head"></span></div>
      <div class="mark on">
        <svg viewBox="0 0 24 24" width="14" height="14"><path fill="none" stroke="currentColor" stroke-width="1.75" stroke-linejoin="round" d="M7 3.75h10A1.25 1.25 0 0 1 18.25 5v16.25L12 17.5l-6.25 3.75V5A1.25 1.25 0 0 1 7 3.75z"/></svg>
      </div>
      <div class="user">
        <div class="msg"><span class="role">You</span><div>Can you turn this into a short note I can paste into Slack?</div></div>
      </div>
      <div class="mark off">
        <svg viewBox="0 0 24 24" width="14" height="14"><path fill="none" stroke="currentColor" stroke-width="1.75" stroke-linejoin="round" d="M7 3.75h10A1.25 1.25 0 0 1 18.25 5v16.25L12 17.5l-6.25 3.75V5A1.25 1.25 0 0 1 7 3.75z"/></svg>
      </div>
      <div class="asst">
        <div class="msg"><span class="role">Assistant</span><div>Shipped the chip under the chat title. Copy, Save, and Fling sit in one place, and the bookmark still marks where you left off.</div></div>
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
        shot(f"{base}/shot-chip.html", OUT / "flick.png", 400, 200, "00000000")
        shot(f"{base}/shot-pair.html", OUT / "pair.png", 672, 684, "00000000")
        shot(f"{base}/shot-popup.html", OUT / "popup.png", 340, 376, "00000000")
        shot(f"{base}/shot-settings.html", OUT / "settings.png", 340, 676, "00000000")
        shot(f"{base}/shot-chat.html", OUT / "thread.png", 784, 420, "00000000")
    finally:
        httpd.shutdown()
    print("ok")


if __name__ == "__main__":
    main()
