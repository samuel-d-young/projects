"""A tiny stand-in for ESPHome's Display drawing API, on a PIL canvas.

The grow-clock faces in mini-round-clock-with-display.yaml are drawn with
`filled_circle`, `filled_rectangle`, `line` and `print`. This class offers the
same calls with the same argument order, so a face can be sketched here in the
same primitives and the coordinates copied into the lambda unchanged.

It is a MIRROR of the C++ and not the source of truth: the YAML is what runs.
If the two ever disagree, the panel is right and this file is wrong.

Faithful where it matters:
  - integer pixel coordinates, top-left origin, y down;
  - `filled_circle(cx, cy, r)` covers the same pixels as ESPHome's midpoint
    fill (radius r inclusive);
  - `print` honours ESPHome's TextAlign anchors and uses the same Roboto TTF
    ESPHome downloaded for the build, at the same pixel size.
Not faithful: 4bpp anti-aliasing is PIL's, not ESPHome's; close enough to
judge a layout, not to compare single pixels.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))

# ESPHome downloads gfonts://Roboto into <build dir>/.esphome/font/. The
# preview looks in a few places and falls back to DejaVu so the *layout* still
# renders even where the exact face is missing.
_FONT_CANDIDATES = [
    os.environ.get("GROW_PREVIEW_FONT", ""),
    os.path.join(HERE, "Roboto-Regular.ttf"),
    os.path.join(HERE, "..", ".esphome", "font", "Roboto@400@False@v1.ttf"),
    "/usr/share/fonts/truetype/roboto/Roboto-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def find_font_file() -> str:
    for p in _FONT_CANDIDATES:
        if p and os.path.exists(p):
            return p
    raise FileNotFoundError("no TTF found; set GROW_PREVIEW_FONT")


@dataclass(frozen=True)
class Color:
    r: int
    g: int
    b: int

    def rgb(self):
        return (self.r, self.g, self.b)


BLACK = Color(0, 0, 0)
WHITE = Color(255, 255, 255)


def dim(c: Color, k: float) -> Color:
    return Color(int(c.r * k), int(c.g * k), int(c.b * k))


class TextAlign:
    # ESPHome's TextAlign is a bit-set; the preview only needs the anchors
    # the faces use. Values are (x anchor, y anchor) for PIL's `anchor` arg.
    TOP_LEFT = ("l", "a")
    TOP_CENTER = ("m", "a")
    TOP_RIGHT = ("r", "a")
    CENTER_LEFT = ("l", "m")
    CENTER = ("m", "m")
    CENTER_RIGHT = ("r", "m")
    BOTTOM_LEFT = ("l", "d")
    BOTTOM_CENTER = ("m", "d")
    BOTTOM_RIGHT = ("r", "d")
    BASELINE_CENTER = ("m", "s")


class Font:
    def __init__(self, size: int, path: str | None = None):
        self.size = size
        self.path = path or find_font_file()
        self.font = ImageFont.truetype(self.path, size)


class Canvas:
    """Draw calls named and ordered like esphome::display::Display."""

    def __init__(self, w: int, h: int, round_: bool = False):
        self.w, self.h, self.round = w, h, round_
        self.im = Image.new("RGB", (w, h), (0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

    # -- ESPHome API -------------------------------------------------------
    def get_width(self):
        return self.w

    def get_height(self):
        return self.h

    def fill(self, c: Color):
        self.d.rectangle([0, 0, self.w - 1, self.h - 1], fill=c.rgb())

    def filled_rectangle(self, x1, y1, w, h, c: Color):
        if w <= 0 or h <= 0:
            return
        self.d.rectangle([x1, y1, x1 + w - 1, y1 + h - 1], fill=c.rgb())

    def rectangle(self, x1, y1, w, h, c: Color):
        self.d.rectangle([x1, y1, x1 + w - 1, y1 + h - 1], outline=c.rgb())

    def filled_circle(self, cx, cy, r, c: Color):
        self.d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c.rgb())

    def circle(self, cx, cy, r, c: Color):
        self.d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=c.rgb())

    def filled_ring(self, cx, cy, r1, r2, c: Color):
        # ESPHome: radius1 outer, radius2 inner.
        ro, ri = max(r1, r2), min(r1, r2)
        mask = Image.new("L", (self.w, self.h), 0)
        md = ImageDraw.Draw(mask)
        md.ellipse([cx - ro, cy - ro, cx + ro, cy + ro], fill=255)
        md.ellipse([cx - ri, cy - ri, cx + ri, cy + ri], fill=0)
        self.im.paste(Image.new("RGB", (self.w, self.h), c.rgb()), mask=mask)

    def line(self, x1, y1, x2, y2, c: Color):
        self.d.line([x1, y1, x2, y2], fill=c.rgb(), width=1)

    def horizontal_line(self, x, y, w, c: Color):
        self.filled_rectangle(x, y, w, 1, c)

    def vertical_line(self, x, y, h, c: Color):
        self.filled_rectangle(x, y, 1, h, c)

    def filled_triangle(self, x1, y1, x2, y2, x3, y3, c: Color):
        self.d.polygon([(x1, y1), (x2, y2), (x3, y3)], fill=c.rgb())

    def print(self, x, y, font: Font, c: Color, align, text: str):
        ax, ay = align
        self.d.text((x, y), text, font=font.font, fill=c.rgb(), anchor=ax + ay)

    # -- preview only --------------------------------------------------------
    def image(self, scale: int = 1) -> Image.Image:
        im = self.im
        if self.round:
            # A round panel only shows the inscribed disc; everything else is
            # bezel. Paint the corners dark grey so the preview is honest about
            # what is off-panel.
            mask = Image.new("L", (self.w, self.h), 0)
            ImageDraw.Draw(mask).ellipse([0, 0, self.w - 1, self.h - 1], fill=255)
            bezel = Image.new("RGB", (self.w, self.h), (28, 28, 28))
            im = Image.composite(im, bezel, mask)
        if scale != 1:
            im = im.resize((self.w * scale, self.h * scale), Image.NEAREST)
        return im
