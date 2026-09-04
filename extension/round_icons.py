"""Build crisp PasteFlick toolbar icons (heavy supersample + soft alpha)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ICONS = Path(__file__).resolve().parent / "icons"
BG = (24, 23, 22, 255)
PAPER = (196, 168, 130, 255)
FOLD = (158, 132, 100, 255)
INK = (24, 23, 22, 255)
SIZES = (16, 32, 48, 128)


def _paint(size: int, scale: int) -> Image.Image:
    canvas = size * scale
    img = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = float(canvas)

    # Smaller toolbar sizes need a larger relative radius or the corners read as square.
    radius = s * (0.26 if size <= 16 else 0.24)
    d.rounded_rectangle([0, 0, canvas - 1, canvas - 1], radius=radius, fill=BG)

    if size <= 16:
        left, top, right, bottom = s * 0.28, s * 0.18, s * 0.72, s * 0.82
        d.rounded_rectangle([left, top, right, bottom], radius=s * 0.10, fill=PAPER)
        for y_frac in (0.42, 0.58):
            y = s * y_frac
            t = s * 0.05
            d.rounded_rectangle([s * 0.36, y - t, s * 0.64, y + t], radius=t, fill=INK)
        return img

    left, top, right, bottom = s * 0.30, s * 0.16, s * 0.70, s * 0.84
    d.rounded_rectangle([left, top, right, bottom], radius=s * 0.07, fill=PAPER)

    fold = s * 0.14
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

    line_count = 2 if size <= 32 else 3
    y_fracs = (0.38, 0.52) if line_count == 2 else (0.36, 0.46, 0.56)
    thick = s * (0.034 if size <= 32 else 0.028)
    for y_frac in y_fracs:
        y = s * y_frac
        d.rounded_rectangle(
            [s * 0.38, y - thick / 2, s * 0.62, y + thick / 2],
            radius=thick / 2,
            fill=INK,
        )
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


def main() -> None:
    for size in SIZES:
        img = build(size)
        path = ICONS / f"icon{size}.png"
        img.save(path, format="PNG", compress_level=6)
        a = [img.getpixel((x, 1))[3] for x in range(min(12, size))]
        print(f"{path.name} edge_alpha={a}")

    build(256).save(ICONS / "icon256.png", format="PNG", compress_level=6)
    print("ok")


if __name__ == "__main__":
    main()
