"""Render PasteFlick README chrome in the app’s cream / gold / ink type."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
ICONS = ROOT.parent / "extension" / "icons"
OUT = ROOT
SCALE = 2
WIDTH = 760 * SCALE
CARD = (243, 241, 234, 255)
PANEL = (236, 230, 218, 255)
TEXT = (92, 74, 46, 255)
MUTED = (138, 115, 88, 255)
INK = (23, 20, 16, 255)
CHIP = (225, 208, 178, 255)
GOLD = (201, 166, 106, 255)
STROKE = (201, 166, 106, 56)
RULE = (201, 166, 106, 88)
FONTS = Path(r"C:\Windows\Fonts")
PAD = 40 * SCALE


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), size * SCALE)


def measure(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=fnt)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for word in words:
        trial = (cur + " " + word).strip()
        if measure(draw, trial, fnt)[0] <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_paragraph(
    img: Image.Image,
    text: str,
    fnt: ImageFont.FreeTypeFont,
    x: int,
    y: int,
    max_width: int,
    fill: tuple[int, int, int, int],
    leading: float = 1.42,
) -> int:
    d = ImageDraw.Draw(img)
    for line in wrap(d, text, fnt, max_width):
        d.text((x, y), line, font=fnt, fill=fill)
        y += int(fnt.size * leading)
    return y


def draw_lines(
    img: Image.Image,
    lines: list[str],
    fnt: ImageFont.FreeTypeFont,
    x: int,
    y: int,
    fill: tuple[int, int, int, int],
    leading: float = 1.16,
) -> int:
    d = ImageDraw.Draw(img)
    for line in lines:
        d.text((x, y), line, font=fnt, fill=fill)
        y += int(fnt.size * leading)
    return y


def paragraph_height(text: str, fnt: ImageFont.FreeTypeFont, max_width: int, leading: float = 1.42) -> int:
    probe = Image.new("RGBA", (8, 8))
    d = ImageDraw.Draw(probe)
    return int(fnt.size * leading) * max(1, len(wrap(d, text, fnt, max_width)))


def kicker(label: str, size: int = 12) -> Image.Image:
    fnt = font("seguisb.ttf", size)
    probe = Image.new("RGBA", (8, 8))
    d = ImageDraw.Draw(probe)
    tw, th = measure(d, label, fnt)
    pad_x, pad_y = 7 * SCALE, 2 * SCALE
    img = Image.new("RGBA", (tw + pad_x * 2, th + pad_y * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, img.width - 1, img.height - 1], radius=6 * SCALE, fill=CHIP)
    bbox = d.textbbox((0, 0), label, font=fnt)
    d.text(
        ((img.width - tw) // 2 - bbox[0], (img.height - th) // 2 - bbox[1]),
        label,
        font=fnt,
        fill=INK,
    )
    return img


def draw_rule(img: Image.Image, x: int, y: int, width: int) -> int:
    d = ImageDraw.Draw(img)
    d.rectangle([x, y, x + width, y + SCALE], fill=RULE)
    return y + SCALE


def section_head(img: Image.Image, eyebrow: str, title: str, x: int, y: int, inner: int) -> int:
    chip = kicker(eyebrow, 12)
    img.alpha_composite(chip, (x, y))
    y += chip.height + 4 * SCALE
    y = draw_paragraph(img, title, font("seguisb.ttf", 28), x, y, inner, INK, 1.12)
    y += 12 * SCALE
    y = draw_rule(img, x, y, inner)
    return y + 22 * SCALE


def draw_subhead(img: Image.Image, text: str, x: int, y: int, inner: int) -> int:
    return draw_paragraph(img, text, font("seguisb.ttf", 16), x, y, inner, INK, 1.2)


def draw_tiles(
    img: Image.Image,
    items: list[tuple[str, str]],
    x: int,
    y: int,
    inner: int,
    gap: int = 12,
) -> int:
    n = len(items)
    gap_px = gap * SCALE
    col_w = (inner - gap_px * (n - 1)) // n
    pad = 16 * SCALE
    title_f = font("seguisb.ttf", 15)
    body_f = font("segoeui.ttf", 13)
    text_w = col_w - pad * 2
    heights = []
    for title, body in items:
        h = pad
        h += paragraph_height(title, title_f, text_w, 1.2)
        h += 8 * SCALE
        h += paragraph_height(body, body_f, text_w, 1.36)
        h += pad - int(body_f.size * 0.36)
        heights.append(h)
    tile_h = max(heights)
    d = ImageDraw.Draw(img)
    for i, (title, body) in enumerate(items):
        cx = x + i * (col_w + gap_px)
        d.rounded_rectangle([cx, y, cx + col_w - 1, y + tile_h], radius=10 * SCALE, fill=PANEL)
        ty = y + pad
        ty = draw_paragraph(img, title, title_f, cx + pad, ty, text_w, INK, 1.2)
        ty += 6 * SCALE
        draw_paragraph(img, body, body_f, cx + pad, ty, text_w, TEXT, 1.36)
    return y + tile_h


def draw_steps(img: Image.Image, steps: list[str], x: int, y: int, inner: int) -> int:
    num_f = font("seguisb.ttf", 14)
    text_f = font("seguisb.ttf", 16)
    d = ImageDraw.Draw(img)
    size = 32 * SCALE
    for i, label in enumerate(steps, 1):
        d.ellipse([x, y, x + size, y + size], fill=CHIP)
        n = str(i)
        tw, th = measure(d, n, num_f)
        bbox = d.textbbox((0, 0), n, font=num_f)
        d.text(
            (x + (size - tw) // 2 - bbox[0], y + (size - th) // 2 - bbox[1]),
            n,
            font=num_f,
            fill=INK,
        )
        tx = x + size + 14 * SCALE
        tw_avail = inner - size - 14 * SCALE
        # Keep the action on one visual line when it fits.
        d.text((tx, y + (size - text_f.size) // 2 - 2 * SCALE), label, font=text_f, fill=INK)
        _ = tw_avail
        y += size + 14 * SCALE
    return y


def sheet() -> Image.Image:
    return Image.new("RGBA", (WIDTH, 2600 * SCALE), (0, 0, 0, 0))


def finish(content: Image.Image, name: str) -> None:
    bbox = content.getbbox()
    if bbox is None:
        raise RuntimeError(f"empty {name}")
    bottom = bbox[3] + PAD
    h = bottom + 8 * SCALE
    content = content.crop((0, 0, WIDTH, min(content.height, h)))
    img = Image.new("RGBA", (WIDTH, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(
        [SCALE, SCALE * 2, WIDTH - SCALE, h - SCALE],
        radius=14 * SCALE,
        fill=(50, 40, 20, 14),
    )
    d.rounded_rectangle(
        [0, 0, WIDTH - 1, h - SCALE * 3],
        radius=14 * SCALE,
        fill=CARD,
        outline=STROKE,
        width=SCALE,
    )
    img.alpha_composite(content)
    out = img.resize((img.width // SCALE, img.height // SCALE), Image.Resampling.LANCZOS)
    path = OUT / name
    out.save(path, format="PNG", compress_level=6)
    print(path.name, out.size)


CHROME = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Google/Chrome/Application/chrome.exe"


def make_button(label: str, size: int = 16, cup: bool = False) -> Image.Image:
    if cup:
        return make_tip_button(label, size)
    fnt = font("seguisb.ttf", size)
    probe = Image.new("RGBA", (8, 8))
    d0 = ImageDraw.Draw(probe)
    bbox = d0.textbbox((0, 0), label, font=fnt)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad_x, pad_y = 22 * SCALE, 14 * SCALE
    bw, bh = tw + pad_x * 2, th + pad_y * 2
    chip = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(chip)
    d.rounded_rectangle([0, 0, bw - 1, bh - 1], radius=10 * SCALE, fill=GOLD)
    d.text((bw // 2, bh // 2), label, font=fnt, fill=INK, anchor="mm")
    return chip


def make_tip_button(label: str, size: int = 13) -> Image.Image:
    if not CHROME.is_file():
        raise RuntimeError("Chrome not found")
    semibold = Path(os.environ.get("WINDIR", r"C:\\Windows")) / "Fonts" / "seguisb.ttf"
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
@font-face {{
  font-family: "Segoe UI Variable Text";
  src: url("seguisb.ttf") format("truetype");
  font-weight: 600 1000;
  font-style: normal;
  font-display: block;
}}
html,body{{margin:0;background:transparent;}}
a{{
  box-sizing:border-box;
  display:inline-flex;
  align-items:center;
  justify-content:center;
  gap:8px;
  height:32px;
  padding:1px 16px 2px 14px;
  border-radius:7px;
  background:#c9a66a;
  color:#171410;
  font:600 13px/1 "Segoe UI Variable Text","Segoe UI Semibold","Segoe UI",sans-serif;
  letter-spacing:-0.018em;
  text-decoration:none;
  box-shadow:inset 0 1px 0 rgba(244,226,180,.45);
}}
svg{{display:block;flex:none;}}
</style></head>
<body>
<a>
  <svg viewBox="0 0 16 16" width="15" height="15" aria-hidden="true">
    <path fill="none" stroke="currentColor" stroke-width="1.55" stroke-linejoin="round" d="M3.4 5.6h7.2v4.3A2.6 2.6 0 0 1 8 12.5H6a2.6 2.6 0 0 1-2.6-2.6V5.6z"/>
    <path fill="none" stroke="currentColor" stroke-width="1.55" stroke-linecap="round" d="M10.6 6.4h1.15a1.7 1.7 0 1 1 0 3.4H10.6"/>
  </svg>
  {label}
</a>
</body></html>"""
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        if semibold.is_file():
            (folder / "seguisb.ttf").write_bytes(semibold.read_bytes())
        page = folder / "tip.html"
        dest = folder / "tip.png"
        page.write_text(html, encoding="utf-8")
        cmd = [
            str(CHROME),
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-first-run",
            "--force-device-scale-factor=2",
            "--window-size=280,80",
            "--default-background-color=00000000",
            f"--screenshot={dest}",
            "--virtual-time-budget=2000",
            page.as_uri(),
        ]
        subprocess.run(cmd, check=True)
        img = Image.open(dest).convert("RGBA")
    bbox = img.getbbox()
    if bbox is None:
        raise RuntimeError("empty tip button")
    return img.crop(bbox)


def save_button(label: str, name: str, size: int = 16, cup: bool = False) -> Image.Image:
    chip = make_button(label, size, cup)
    out = chip.resize((chip.width // SCALE, chip.height // SCALE), Image.Resampling.LANCZOS)
    path = OUT / name
    out.save(path, format="PNG", compress_level=6)
    print(path.name, out.size)
    return chip


def build_hero() -> None:
    img = sheet()
    x = PAD
    y = PAD
    inner = WIDTH - PAD * 2
    icon = (
        Image.open(ICONS / "icon48.png")
        .convert("RGBA")
        .resize((44 * SCALE, 44 * SCALE), Image.Resampling.LANCZOS)
    )
    brand = kicker("PasteFlick", 13)
    img.alpha_composite(icon, (x, y))
    img.alpha_composite(brand, (x + icon.width + 12 * SCALE, y + (icon.height - brand.height) // 2))
    y += max(icon.height, brand.height) + 28 * SCALE
    y = draw_lines(
        img,
        ["Copy from ChatGPT.", "Flick it into the last app."],
        font("seguisb.ttf", 32),
        x,
        y,
        INK,
        1.14,
    )
    y += 16 * SCALE
    y = draw_paragraph(
        img,
        "Windows  ·  Brave, Chrome, Edge, Chromium, Arc  ·  ChatGPT only  ·  Not affiliated with OpenAI",
        font("segoeui.ttf", 13),
        x,
        y,
        inner,
        MUTED,
        1.4,
    )
    y += 20 * SCALE
    y = draw_rule(img, x, y, inner)
    y += 20 * SCALE
    y = draw_paragraph(
        img,
        "Long chats fight the clipboard. PasteFlick sits on the conversation as one chip: take a highlight, or the thread you can see, then Copy, Save, or Flick it into Word, Notes, Cursor — wherever you just were.",
        font("segoeui.ttf", 16),
        x,
        y,
        inner,
        TEXT,
        1.45,
    )
    y += 12 * SCALE
    draw_paragraph(
        img,
        "It copies what is already on the page — not turns ChatGPT has not rendered yet.",
        font("segoeui.ttf", 13),
        x,
        y,
        inner,
        MUTED,
        1.4,
    )
    finish(img, "intro-type.png")


def build_what() -> None:
    img = sheet()
    x = PAD
    y = PAD
    inner = WIDTH - PAD * 2
    y = section_head(img, "On the chat", "What you get", x, y, inner)
    body = font("segoeui.ttf", 16)
    small = font("segoeui.ttf", 13)
    y = draw_paragraph(
        img,
        "One chip under the chat title. Highlight a passage, or take the visible thread — then Copy, Save, or Flick. ChatGPT’s own buttons stay where they are.",
        body,
        x,
        y,
        inner,
        TEXT,
        1.45,
    )
    y += 14 * SCALE
    y = draw_paragraph(
        img,
        "Bookmark a message, or a few. Each pin shows 1 of 3. Deselect slides out under the chip with the count, so you can clear the set in one tap.",
        body,
        x,
        y,
        inner,
        TEXT,
        1.45,
    )
    y += 14 * SCALE
    y = draw_subhead(img, "The toolbar icon", x, y, inner)
    y += 8 * SCALE
    y = draw_paragraph(
        img,
        "On a chat it opens the thread as a document. Highlight, copy, or save as Markdown. Settings is the gear. The chip is still the fast path while you read.",
        small,
        x,
        y,
        inner,
        MUTED,
        1.4,
    )
    y += 24 * SCALE
    y = draw_subhead(img, "Where it goes", x, y, inner)
    y += 8 * SCALE
    y = draw_paragraph(img, "Pick one in Settings.", small, x, y, inner, MUTED, 1.4)
    y += 12 * SCALE
    y = draw_tiles(
        img,
        [
            ("Clipboard", "Ready to paste when you are."),
            ("Flick", "Into the last app you were in."),
            ("File", "Markdown or PDF, in a folder you pick."),
        ],
        x,
        y,
        inner,
    )
    y += 16 * SCALE
    draw_paragraph(
        img,
        "The first time you copy, allow clipboard access if ChatGPT or the browser asks.",
        small,
        x,
        y,
        inner,
        MUTED,
        1.4,
    )
    finish(img, "what-you-get-type.png")


def draw_paras(
    img: Image.Image,
    paras: list[str],
    fnt: ImageFont.FreeTypeFont,
    x: int,
    y: int,
    inner: int,
    fill: tuple[int, int, int, int],
    leading: float = 1.45,
    gap: int = 14,
) -> int:
    for i, para in enumerate(paras):
        if i:
            y += gap * SCALE
        y = draw_paragraph(img, para, fnt, x, y, inner, fill, leading)
    return y


def build_support() -> None:
    img = sheet()
    x = PAD
    y = PAD
    inner = WIDTH - PAD * 2
    y = section_head(img, "If you like it", "Support", x, y, inner)
    y = draw_paras(
        img,
        [
            "I'm Ryan Dunham, a Louisiana entrepreneur. I've worked in IT and consulting, run the Pie Eyed food business, and helped operate a brewery. Now I'm making software with AI coding agents — I describe the idea, they help write it, and I decide what ships. PasteFlick is my first public release.",
            "If this helped you, consider supporting my work. A $5 tip helps pay for my development time, fixes, testing, and future tools. I'm earning a living from this work.",
        ],
        font("segoeui.ttf", 16),
        x,
        y,
        inner,
        TEXT,
    )
    y += 20 * SCALE
    btn = make_button("Leave a tip", 13, cup=True)
    note_f = font("segoeui.ttf", 14)
    note = "Optional — other amounts are welcome."
    well_pad = 18 * SCALE
    note_h = int(note_f.size * 1.4)
    well_h = well_pad + btn.height + 12 * SCALE + note_h + well_pad - int(note_f.size * 0.28)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(
        [x, y, x + inner - 1, y + well_h],
        radius=12 * SCALE,
        fill=PANEL,
        outline=STROKE,
        width=SCALE,
    )
    bx = x + (inner - btn.width) // 2
    by = y + well_pad
    img.alpha_composite(btn, (bx, by))
    d0 = ImageDraw.Draw(img)
    tw, _ = measure(d0, note, note_f)
    d0.text(
        (x + (inner - tw) // 2, by + btn.height + 12 * SCALE),
        note,
        font=note_f,
        fill=MUTED,
    )
    y += well_h + 16 * SCALE
    draw_paragraph(
        img,
        "Sharing PasteFlick with someone who'd use it helps too.",
        font("segoeui.ttf", 13),
        x,
        y,
        inner,
        MUTED,
        1.4,
    )
    finish(img, "support-type.png")


def build_privacy() -> None:
    img = sheet()
    x = PAD
    y = PAD
    inner = WIDTH - PAD * 2
    y = section_head(img, "On your machine", "Privacy", x, y, inner)
    draw_paras(
        img,
        [
            "The extension reads the open ChatGPT page. A small Windows helper on this computer handles Flick into the last app and saving a file.",
            "Copied chat text is not sent to me. Updates check GitHub, and the tip button opens Ko-fi.",
        ],
        font("segoeui.ttf", 16),
        x,
        y,
        inner,
        TEXT,
    )
    finish(img, "privacy-type.png")


def build_install() -> None:
    img = sheet()
    x = PAD
    y = PAD
    inner = WIDTH - PAD * 2
    y = section_head(img, "Windows", "Install", x, y, inner)
    body = font("segoeui.ttf", 16)
    small = font("segoeui.ttf", 13)
    y = draw_paragraph(
        img,
        "Download the zip, extract it, and run Install PasteFlick.bat.",
        body,
        x,
        y,
        inner,
        TEXT,
        1.45,
    )
    y += 14 * SCALE
    y = draw_paragraph(
        img,
        "Copy to the clipboard works on its own. Flick and PDF save use a small Windows helper that Setup installs and starts with Windows. You do not install Python.",
        body,
        x,
        y,
        inner,
        TEXT,
        1.45,
    )
    y += 24 * SCALE
    y = draw_subhead(img, "Finish in the browser", x, y, inner)
    y += 8 * SCALE
    y = draw_paragraph(
        img,
        "Browsers will not silently install extensions. Setup opens a short guide, copies the folder path, and launches your Extensions page.",
        body,
        x,
        y,
        inner,
        TEXT,
        1.45,
    )
    y += 12 * SCALE
    y = draw_steps(
        img,
        [
            "Turn on Developer mode",
            "Click Load unpacked",
            "Paste the path and open that folder",
        ],
        x,
        y,
        inner,
    )
    y += 4 * SCALE
    y = draw_paragraph(
        img,
        "Leave Developer mode on. Repeat in each Chromium browser you use. After that, updates come from GitHub on login.",
        small,
        x,
        y,
        inner,
        MUTED,
        1.4,
    )
    y += 24 * SCALE
    y = draw_subhead(img, "Uninstall", x, y, inner)
    y += 8 * SCALE
    y = draw_paragraph(
        img,
        r"%LOCALAPPDATA%\PasteFlick\Uninstall.bat",
        font("segoeui.ttf", 15),
        x,
        y,
        inner,
        TEXT,
        1.4,
    )
    y += 8 * SCALE
    draw_paragraph(
        img,
        r"Then remove the extension from the browser if it is still listed. Share the latest release or a clone of this repo — not a working folder, and not %LOCALAPPDATA%\PasteFlick.",
        small,
        x,
        y,
        inner,
        MUTED,
        1.4,
    )
    finish(img, "setup-type.png")
    save_button("Get the Windows zip", "windows-zip-type.png", 16)
    save_button("Leave a tip", "tip-btn-type.png", 13, cup=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    build_hero()
    build_what()
    build_support()
    build_install()
    build_privacy()
    print("ok")


if __name__ == "__main__":
    main()
