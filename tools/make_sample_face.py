"""Generates assets/sample-face.png: a clean illustrated portrait used only for
the live settings preview.  It never leaves the app and is not a real person, so
there are no likeness or copyright concerns.  Run once; the PNG is committed.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

W, H = 300, 360
SKIN = (242, 205, 168)
SKIN_SHADE = (232, 190, 150)
HAIR = (58, 46, 77)
BROW = (74, 60, 96)
EYE = (60, 50, 70)
MOUTH = (176, 108, 96)
SHIRT = (208, 208, 214)
BG_TOP = (236, 236, 240)
BG_BOTTOM = (222, 222, 228)


def _vertical_gradient(size, top, bottom) -> Image.Image:
    base = Image.new("RGB", size, top)
    draw = ImageDraw.Draw(base)
    for y in range(size[1]):
        t = y / size[1]
        draw.line([(0, y), (size[0], y)], fill=tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return base


def build() -> Image.Image:
    img = _vertical_gradient((W, H), BG_TOP, BG_BOTTOM)
    draw = ImageDraw.Draw(img)

    # Shoulders / shirt.
    draw.ellipse((30, 300, 270, 470), fill=SHIRT)
    # Neck.
    draw.rounded_rectangle((128, 250, 172, 315), radius=18, fill=SKIN_SHADE)
    # Hair back.
    draw.ellipse((66, 44, 234, 250), fill=HAIR)
    # Face.
    draw.ellipse((80, 70, 220, 262), fill=SKIN)
    # Ears.
    draw.ellipse((72, 150, 96, 194), fill=SKIN)
    draw.ellipse((204, 150, 228, 194), fill=SKIN)
    # Hair top sweep, sitting over the forehead.
    draw.pieslice((70, 46, 230, 210), start=180, end=360, fill=HAIR)
    draw.ellipse((150, 70, 226, 150), fill=HAIR)
    # Eyebrows.
    draw.line((104, 150, 138, 146), fill=BROW, width=6)
    draw.line((162, 146, 196, 150), fill=BROW, width=6)
    # Eyes.
    for cx in (121, 179):
        draw.ellipse((cx - 15, 162, cx + 15, 184), fill=(255, 255, 255))
        draw.ellipse((cx - 7, 166, cx + 7, 180), fill=EYE)
    # Nose.
    draw.line((150, 178, 150, 208), fill=SKIN_SHADE, width=6)
    draw.arc((138, 196, 162, 214), start=20, end=160, fill=SKIN_SHADE, width=4)
    # Smile.
    draw.arc((124, 200, 176, 240), start=15, end=165, fill=MOUTH, width=7)

    return img.filter(ImageFilter.SMOOTH_MORE)


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "assets" / "sample-face.png"
    build().save(out, "PNG")
    print(f"wrote {out}")
