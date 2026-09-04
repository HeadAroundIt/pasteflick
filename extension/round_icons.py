"""Build crisp PasteFlick toolbar icons (heavy supersample + soft alpha)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ICONS = Path(__file__).resolve().parent / "icons"
BG = (243, 241, 234, 255)
PAPER = (201, 166, 106, 255)
FOLD = (156, 118, 58, 255)
INK = (23, 20, 16, 255)
SIZES = (16, 32, 48, 128)


def _page(s: float, size: int | None = None) -> tuple[float, float, float, float]:
    # Toolbar icons read as a tiny square. Fill it — the cream margin is lost at 16–32px.
    if size is not None and size <= 16:
        return s * 0.08, s * 0.04, s * 0.92, s * 0.96
    if size is not None and size <= 32:
        return s * 0.07, s * 0.04, s * 0.93, s * 0.96
    return s * 0.11, s * 0.06, s * 0.89, s * 0.94


def _draw_sheet(d: ImageDraw.ImageDraw, s: float, size: int | None, folded: bool) -> None:
    left, top, right, bottom = _page(s, size)
    page_w = right - left
    d.rounded_rectangle([left, top, right, bottom], radius=page_w * 0.11, fill=PAPER)
    if folded:
        fold = page_w * 0.26
        d.polygon(
            [(right - fold, bottom), (right, bottom - fold), (right, bottom)],
            fill=BG,
        )
        d.polygon(
            [
                (right - fold, bottom),
                (right - fold, bottom - fold),
                (right, bottom - fold),
            ],
            fill=FOLD,
        )
    inset = page_w * 0.16
    lx, rx = left + inset, right - inset
    if size is not None and size <= 16:
        y_fracs, thick = (0.32, 0.50, 0.68), s * 0.08
    elif size is not None and size <= 32:
        y_fracs, thick = (0.32, 0.50, 0.68), s * 0.048
    else:
        y_fracs, thick = (0.32, 0.46, 0.60), s * 0.038
    for y_frac in y_fracs:
        y = s * y_frac
        d.rounded_rectangle([lx, y - thick / 2, rx, y + thick / 2], radius=thick / 2, fill=INK)


def _paint(size: int, scale: int) -> Image.Image:
    canvas = size * scale
    img = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = float(canvas)

    # Smaller toolbar sizes need a larger relative radius or the corners read as square.
    radius = s * (0.26 if size <= 16 else 0.24)
    d.rounded_rectangle([0, 0, canvas - 1, canvas - 1], radius=radius, fill=BG)
    _draw_sheet(d, s, size, folded=True)
    return img


def _soften_alpha(img: Image.Image) -> Image.Image:
    r, g, b, a = img.split()
    soft = a.filter(ImageFilter.GaussianBlur(radius=0.45))
    a2 = ImageChops.lighter(a, soft)
    return Image.merge("RGBA", (r, g, b, a2))


def build(size: int) -> Image.Image:
    scale = 16 if size <= 32 else 8
    big = _paint(size, scale)
    out = big.resize((size, size), Image.Resampling.LANCZOS)
    if size <= 48:
        out = _soften_alpha(out)
    return out


def build_master(size: int = 1024) -> Image.Image:
    img = Image.new("RGB", (size, size), BG[:3])
    d = ImageDraw.Draw(img)
    _draw_sheet(d, float(size), None, folded=True)
    return img


def main() -> None:
    for size in SIZES:
        img = build(size)
        path = ICONS / f"icon{size}.png"
        img.save(path, format="PNG", compress_level=6)
        a = [img.getpixel((x, 1))[3] for x in range(min(12, size))]
        print(f"{path.name} edge_alpha={a}")

    build(256).save(ICONS / "icon256.png", format="PNG", compress_level=6)
    master = ICONS / "icon-master.png"
    build_master().save(master, format="PNG", compress_level=6)
    print(f"{master.name} {build_master().size}")
    print("ok")


if __name__ == "__main__":
    main()
