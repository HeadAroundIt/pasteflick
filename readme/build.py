"""Render PasteFlick README chrome in the app’s cream / gold / ink type."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
ICONS = ROOT.parent / "extension" / "icons"
OUT = ROOT
SCALE = 2
WIDTH = 680 * SCALE
CARD = (243, 241, 234, 255)
TEXT = (92, 74, 46, 255)
MUTED = (138, 115, 88, 255)
INK = (23, 20, 16, 255)
CHIP = (225, 208, 178, 255)
STROKE = (201, 166, 106, 56)
FONTS = Path(r"C:\Windows\Fonts")
PAD = 28 * SCALE


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


def kicker(label: str, size: int = 12) -> Image.Image:
    fnt = font("seguisb.ttf", size)
    probe = Image.new("RGBA", (8, 8))
    d = ImageDraw.Draw(probe)
    tw, th = measure(d, label, fnt)
    pad_x, pad_y = 10 * SCALE, 5 * SCALE
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


def sheet() -> Image.Image:
    return Image.new("RGBA", (WIDTH, 2200 * SCALE), (0, 0, 0, 0))


def finish(content: Image.Image, name: str) -> None:
    bbox = content.getbbox()
    if bbox is None:
        raise RuntimeError(f"empty {name}")
    bottom = bbox[3] + PAD
    h = bottom + 6 * SCALE
    content = content.crop((0, 0, WIDTH, min(content.height, h)))
    img = Image.new("RGBA", (WIDTH, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(
        [SCALE, SCALE * 2, WIDTH - SCALE, h - SCALE],
        radius=10 * SCALE,
        fill=(50, 40, 20, 14),
    )
    d.rounded_rectangle(
        [0, 0, WIDTH - 1, h - SCALE * 3],
        radius=10 * SCALE,
        fill=CARD,
        outline=STROKE,
        width=SCALE,
    )
    img.alpha_composite(content)
    out = img.resize((img.width // SCALE, img.height // SCALE), Image.Resampling.LANCZOS)
    path = OUT / name
    out.save(path, format="PNG", compress_level=6)
    print(path.name, out.size)


def save_raw(img: Image.Image, name: str) -> None:
    out = img.resize((img.width // SCALE, img.height // SCALE), Image.Resampling.LANCZOS)
    path = OUT / name
    out.save(path, format="PNG", compress_level=6)
    print(path.name, out.size)


def build_hero() -> None:
    img = sheet()
    x = PAD
    y = PAD
    inner = WIDTH - PAD * 2
    icon = (
        Image.open(ICONS / "icon48.png")
        .convert("RGBA")
        .resize((40 * SCALE, 40 * SCALE), Image.Resampling.LANCZOS)
    )
    brand = kicker("PasteFlick", 13)
    img.alpha_composite(icon, (x, y))
    img.alpha_composite(brand, (x + icon.width + 10 * SCALE, y + (icon.height - brand.height) // 2))
    y += max(icon.height, brand.height) + 18 * SCALE
    y = draw_paragraph(
        img,
        "Copy from ChatGPT. Flick it into the last app you were using.",
        font("seguisb.ttf", 16),
        x,
        y,
        inner,
        INK,
        1.28,
    )
    y += 10 * SCALE
    y = draw_paragraph(
        img,
        "Windows  ·  Brave, Chrome, Edge, Chromium, Arc  ·  ChatGPT only  ·  Not affiliated with OpenAI",
        font("segoeui.ttf", 12),
        x,
        y,
        inner,
        MUTED,
        1.35,
    )
    y += 16 * SCALE
    y = draw_paragraph(
        img,
        "Long chats fight the clipboard. PasteFlick sits on the conversation as one chip: take a highlight, or the thread you can see, then Copy, Save, or Fling it into Word, Notes, Cursor — wherever you just were.",
        font("segoeui.ttf", 14),
        x,
        y,
        inner,
        TEXT,
    )
    y += 10 * SCALE
    draw_paragraph(
        img,
        "It copies what is on the page. Turns ChatGPT has not rendered yet are not in the copy.",
        font("segoeui.ttf", 12),
        x,
        y,
        inner,
        MUTED,
        1.4,
    )
    finish(img, "hero.png")


def row(img: Image.Image, label: str, rest: str, x: int, y: int, inner: int) -> int:
    chip = kicker(label, 11)
    img.alpha_composite(chip, (x, y))
    fnt = font("segoeui.ttf", 13)
    text_x = x + chip.width + 10 * SCALE
    d = ImageDraw.Draw(img)
    d.text((text_x, y + (chip.height - fnt.size) // 2 - 2 * SCALE), f"—  {rest}", font=fnt, fill=TEXT)
    return y + chip.height + 8 * SCALE


def build_what() -> None:
    img = sheet()
    x = PAD
    y = PAD
    inner = WIDTH - PAD * 2
    head = kicker("What you get", 12)
    img.alpha_composite(head, (x, y))
    y += head.height + 16 * SCALE
    body = font("segoeui.ttf", 14)
    small = font("segoeui.ttf", 12)
    y = draw_paragraph(
        img,
        "One chip under the chat title. Highlight a passage, or take the visible thread — then Copy, Save, or Fling. ChatGPT’s own buttons stay where they are.",
        body,
        x,
        y,
        inner,
        TEXT,
    )
    y += 12 * SCALE
    y = draw_paragraph(
        img,
        "Pin any message. Copy from PasteFlick starts at that pin, so you can take the rest of the conversation without dragging a selection.",
        body,
        x,
        y,
        inner,
        TEXT,
    )
    y += 16 * SCALE
    y = draw_paragraph(img, "The toolbar popup is there when you want it.", small, x, y, inner, MUTED, 1.4)
    y += 8 * SCALE
    y = row(img, "Copy selection", "the highlight you made", x, y, inner)
    y = row(img, "Copy thread", "the conversation currently on the page", x, y, inner)
    y = row(img, "Copy from PasteFlick", "from your pin onward", x, y, inner)
    y += 8 * SCALE
    y = draw_paragraph(img, "Choose where the text goes.", small, x, y, inner, MUTED, 1.4)
    y += 8 * SCALE
    y = row(img, "Clipboard", "ready to paste when you are", x, y, inner)
    y = row(img, "Fling", "into the last app you were in", x, y, inner)
    y = row(img, "File", "Markdown or PDF, in a folder you pick", x, y, inner)
    y += 8 * SCALE
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
    finish(img, "what.png")


def build_support() -> None:
    img = sheet()
    x = PAD
    y = PAD
    inner = WIDTH - PAD * 2
    head = kicker("Support", 12)
    img.alpha_composite(head, (x, y))
    y += head.height + 16 * SCALE
    y = draw_paragraph(
        img,
        "Help me keep creating useful apps and sharing them freely. Your $5 contribution supports new ideas, continued development, and more tools for everyone.",
        font("segoeui.ttf", 14),
        x,
        y,
        inner,
        TEXT,
    )
    y += 12 * SCALE
    y = draw_paragraph(
        img,
        "No pressure—just genuine appreciation!",
        font("segoeui.ttf", 13),
        x,
        y,
        inner,
        MUTED,
        1.4,
    )
    finish(img, "support.png")


def build_privacy() -> None:
    img = sheet()
    x = PAD
    y = PAD
    inner = WIDTH - PAD * 2
    head = kicker("Privacy", 12)
    img.alpha_composite(head, (x, y))
    y += head.height + 16 * SCALE
    draw_paragraph(
        img,
        "Runs in your browser. Copied text stays on your device. Fling uses a local helper on your computer.",
        font("segoeui.ttf", 14),
        x,
        y,
        inner,
        TEXT,
    )
    finish(img, "privacy.png")


def build_install() -> None:
    img = sheet()
    x = PAD
    y = PAD
    inner = WIDTH - PAD * 2
    head = kicker("Install", 12)
    img.alpha_composite(head, (x, y))
    y += head.height + 16 * SCALE
    body = font("segoeui.ttf", 14)
    small = font("segoeui.ttf", 12)
    y = draw_paragraph(img, "Windows only. Download the zip, extract it, and run Install PasteFlick.bat.", body, x, y, inner, TEXT)
    y += 12 * SCALE
    y = draw_paragraph(
        img,
        "Copy to the clipboard works on its own. Fling and PDF save use a small Windows helper that Setup installs and starts with Windows. You do not install Python.",
        body,
        x,
        y,
        inner,
        TEXT,
    )
    y += 16 * SCALE
    y = draw_paragraph(img, "Finish in the browser", font("seguisb.ttf", 13), x, y, inner, INK, 1.3)
    y += 8 * SCALE
    y = draw_paragraph(
        img,
        "Browsers will not silently install extensions. Setup opens a short guide, copies the folder path, and launches your Extensions page.",
        body,
        x,
        y,
        inner,
        TEXT,
    )
    y += 10 * SCALE
    y = row(img, "1", "Turn on Developer mode", x, y, inner)
    y = row(img, "2", "Click Load unpacked", x, y, inner)
    y = row(img, "3", "Paste the path and open that folder", x, y, inner)
    y += 8 * SCALE
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
    y += 16 * SCALE
    y = draw_paragraph(img, "Uninstall", font("seguisb.ttf", 13), x, y, inner, INK, 1.3)
    y += 8 * SCALE
    y = draw_paragraph(img, "%LOCALAPPDATA%\\PasteFlick\\Uninstall.bat", font("segoeui.ttf", 13), x, y, inner, TEXT, 1.4)
    y += 8 * SCALE
    draw_paragraph(
        img,
        "Then remove the extension from the browser if it is still listed. Share the latest release or a clone of this repo — not a working folder, and not %LOCALAPPDATA%\\PasteFlick.",
        small,
        x,
        y,
        inner,
        MUTED,
        1.4,
    )
    finish(img, "install.png")

    gold = (201, 166, 106, 255)
    label = "Get the Windows zip"
    fnt = font("seguisb.ttf", 13)
    probe = Image.new("RGBA", (8, 8))
    d0 = ImageDraw.Draw(probe)
    tw, th = measure(d0, label, fnt)
    pad_x, pad_y = 16 * SCALE, 10 * SCALE
    chip = Image.new("RGBA", (tw + pad_x * 2, th + pad_y * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(chip)
    d.rounded_rectangle([0, 0, chip.width - 1, chip.height - 1], radius=7 * SCALE, fill=gold)
    bbox = d.textbbox((0, 0), label, font=fnt)
    d.text(
        ((chip.width - tw) // 2 - bbox[0], (chip.height - th) // 2 - bbox[1]),
        label,
        font=fnt,
        fill=INK,
    )
    save_raw(chip, "get-zip.png")


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
