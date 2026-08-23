#!/usr/bin/env python3
"""Generate the wiring diagrams as SVG (and PNG if cairosvg is available).

    python3 wiring.py

Rail-style layout: 5V along the top, GND along the bottom, signal in between.
Every wire is colour-coded the way you should actually cut the loom:
    red = +5V, black = GND, yellow = LED data, blue = display signal.
"""
import math
import sys

F = "DejaVu Sans, Helvetica, sans-serif"
RED, BLK, YEL, BLU, GRN = "#d6453d", "#2b2b2b", "#e0a92b", "#3d78d6", "#3d9a5c"
INK, MUTED, PAPER, CARD = "#1b1b1b", "#6b6b6b", "#faf7f0", "#ffffff"


class SVG:
    def __init__(self, w, h, title):
        self.w, self.h, self.title = w, h, title
        self.o = []

    def add(self, s):
        self.o.append(s)

    def rect(self, x, y, w, h, fill=CARD, stroke=INK, sw=2, rx=8, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def text(self, x, y, s, size=15, fill=INK, anchor="start", weight="normal"):
        s = (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        self.add(f'<text x="{x}" y="{y}" font-family="{F}" font-size="{size}" '
                 f'fill="{fill}" text-anchor="{anchor}" font-weight="{weight}">{s}</text>')

    def line(self, pts, color=BLK, w=3, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        p = " ".join(f"{x},{y}" for x, y in pts)
        self.add(f'<polyline points="{p}" fill="none" stroke="{color}" '
                 f'stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"{d}/>')

    def dot(self, x, y, r=5, fill=BLK):
        self.add(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}"/>')

    def circle(self, x, y, r, fill="none", stroke=INK, sw=2):
        self.add(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{sw}"/>')

    def save(self, path):
        head = (f'<?xml version="1.0" encoding="UTF-8"?>\n'
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" '
                f'height="{self.h}" viewBox="0 0 {self.w} {self.h}">'
                f'<rect width="{self.w}" height="{self.h}" fill="{PAPER}"/>')
        open(path, "w").write(head + "".join(self.o) + "</svg>")


def resistor(s, x, y, label):
    """Zigzag, drawn horizontally centred on (x, y)."""
    w, h = 46, 11
    pts = [(x - w / 2, y)]
    for i in range(6):
        pts.append((x - w / 2 + w * (i + 0.5) / 6, y + (h if i % 2 == 0 else -h)))
    pts.append((x + w / 2, y))
    s.line(pts, YEL, 3)
    s.text(x, y - 22, label, 14, INK, "middle", "bold")


def capacitor(s, x, y0, y1, label):
    """Vertical electrolytic between two rails."""
    mid = (y0 + y1) / 2
    s.line([(x, y0), (x, mid - 9)], RED, 3)
    s.line([(x, mid + 9), (x, y1)], BLK, 3)
    s.add(f'<line x1="{x-22}" y1="{mid-9}" x2="{x+22}" y2="{mid-9}" stroke="{INK}" stroke-width="3"/>')
    s.add(f'<line x1="{x-22}" y1="{mid+9}" x2="{x+22}" y2="{mid+9}" stroke="{INK}" stroke-width="3"/>')
    s.text(x + 30, mid - 2, label, 14, INK, "start", "bold")
    s.text(x + 30, mid + 17, "+ to 5V", 12, MUTED)


def led_ring(s, cx, cy, r, n, label):
    s.circle(cx, cy, r, CARD, INK, 2)
    s.circle(cx, cy, r - 34, PAPER, INK, 2)
    for i in range(n):
        a = 2 * math.pi * i / n - math.pi / 2
        s.circle(cx + (r - 17) * math.cos(a), cy + (r - 17) * math.sin(a), 6.5,
                 "#f2e9d8", MUTED, 1.5)
    s.text(cx, cy - 6, label, 16, INK, "middle", "bold")
    s.text(cx, cy + 15, f"{n} x WS2812B", 13, MUTED, "middle")


def ring_pad(s, cx, cy, r, deg, color, label, out=42):
    """Land a wire on the ring's outer edge at a clock angle, stub outward."""
    a = math.radians(deg - 90)
    x0, y0 = cx + r * math.cos(a), cy + r * math.sin(a)
    x1, y1 = cx + (r + out) * math.cos(a), cy + (r + out) * math.sin(a)
    s.line([(x0, y0), (x1, y1)], color, 3)
    right = math.cos(a) > 0.1
    below = abs(math.cos(a)) <= 0.1
    if below:
        s.text(x1 + 16, y1 + 5, label, 13, color, "start", "bold")
    else:
        s.text(x1 + (14 if right else -14), y1 + 5, label, 13, color,
               "start" if right else "end", "bold")
    return x1, y1


def notes(s, x, y, w, title, items):
    h = 44 + 25 * len(items)
    s.rect(x, y, w, h, "#f2ecdf", "#d8cdb4", 2, 10)
    s.text(x + 18, y + 28, title, 16, INK, "start", "bold")
    for i, t in enumerate(items):
        s.text(x + 18, y + 54 + 25 * i, t, 14, INK)
    return h


# =============================================================================
def diagram_d1mini(path):
    s = SVG(1580, 1130, "D1 mini")
    s.text(50, 52, "Test clock — Wemos D1 mini (ESP8266) + 24-LED WS2812B ring", 26, INK, "start", "bold")
    s.text(50, 80, "Red = +5V   Black = GND   Yellow = LED data.  Ground connects FIRST and disconnects LAST.", 15, MUTED)

    RAIL5, RAILG = 150, 690
    s.line([(120, RAIL5), (1440, RAIL5)], RED, 4)
    s.line([(120, RAILG), (1440, RAILG)], BLK, 4)
    s.text(120, RAIL5 - 14, "+5V rail", 14, RED, "start", "bold")
    s.text(880, RAILG - 16, "GND rail  —  common ground is mandatory", 14, BLK, "middle", "bold")

    # PSU
    s.rect(60, 300, 210, 190)
    s.text(165, 335, "5V supply", 18, INK, "middle", "bold")
    s.text(165, 362, "2A minimum", 14, MUTED, "middle")
    s.text(165, 392, "or USB — but then", 13, MUTED, "middle")
    s.text(165, 411, "cap brightness (note 4)", 13, MUTED, "middle")
    s.line([(165, 300), (165, RAIL5)], RED, 3)
    s.line([(165, 490), (165, RAILG)], BLK, 3)
    s.dot(165, RAIL5, 5, RED)
    s.dot(165, RAILG, 5, BLK)

    # D1 mini
    s.rect(400, 285, 250, 220)
    s.text(525, 322, "Wemos D1 mini", 19, INK, "middle", "bold")
    s.text(525, 346, "ESP8266", 14, MUTED, "middle")
    for py, lbl, col in ((392, "5V", RED), (432, "G", BLK), (472, "D2 / GPIO4", YEL)):
        s.text(414, py + 5, lbl, 15, INK)
        s.line([(400, py), (370, py)], col, 3)
    s.line([(370, 392), (370, RAIL5)], RED, 3); s.dot(370, RAIL5, 5, RED)
    s.line([(370, 432), (330, 432), (330, RAILG)], BLK, 3); s.dot(330, RAILG, 5, BLK)

    # data path: D2 -> shifter -> resistor -> DIN
    s.line([(370, 472), (300, 472), (300, 800)], YEL, 3)
    s.line([(300, 800), (700, 800)], YEL, 3)
    s.rect(700, 745, 220, 110, CARD, INK, 2)
    s.text(810, 780, "74AHCT125", 17, INK, "middle", "bold")
    s.text(810, 803, "3.3V -> 5V level shift", 13, MUTED, "middle")
    s.text(810, 828, "recommended, note 3", 12, GRN, "middle")
    s.line([(920, 800), (1010, 800)], YEL, 3)
    resistor(s, 1055, 800, "470 ohm")
    s.line([(1100, 800), (1150, 800), (1150, 570)], YEL, 3)
    s.line([(700, 763), (660, 763), (660, RAIL5)], RED, 2.5); s.dot(660, RAIL5, 4, RED)
    s.line([(700, 840), (620, 840), (620, RAILG)], BLK, 2.5); s.dot(620, RAILG, 4, BLK)

    # ring — wires land on the outer edge and route AROUND it, never across
    CX, CY, RR = 1150, 400, 128
    led_ring(s, CX, CY, RR, 24, "LED ring")
    vx, vy = ring_pad(s, CX, CY, RR, 305, RED, "VCC")
    s.line([(vx, vy), (985, vy), (985, RAIL5)], RED, 3); s.dot(985, RAIL5, 5, RED)
    gx, gy = ring_pad(s, CX, CY, RR, 55, BLK, "GND")
    s.line([(gx, gy), (1330, gy), (1330, RAILG)], BLK, 3); s.dot(1330, RAILG, 5, BLK)
    dx, dy = ring_pad(s, CX, CY, RR, 180, YEL, "DIN")
    capacitor(s, 1420, RAIL5, RAILG, "1000uF")

    notes(s, 50, 900, 1480, "Before you power it", [
        "1.  Ground first on, last off. The DIN threshold is referenced to the ring's ground — no shared return, no defined logic level.",
        "2.  Power the ring BEFORE the D1 mini. Otherwise it back-powers parasitically through the data pin and can damage the MCU.",
        "3.  The 470 ohm resistor goes at the RING end of the wire, not the D1 mini end. If you fit the 74AHCT125, put the resistor on its output.",
        "4.  24 LEDs at full white is ~1.44A — more than a PC USB port gives. On USB, keep Brightness at or below 30% (the config defaults to 30).",
        "5.  Never USB and an external supply at the same time. Flash over USB with the supply unplugged, then use OTA.",
    ])
    s.save(path)


def diagram_s3(path):
    s = SVG(1700, 1270, "S3")
    s.text(50, 52, "Mini Round Clock — ESP32-S3-N16R8 + 24-LED ring (92/71mm) + 360x360 display",
           26, INK, "start", "bold")
    s.text(50, 80, "Red = +5V   Orange = +3V3   Black = GND   Yellow = LED data   Blue = display QSPI",
           15, MUTED)

    RAIL5, RAIL3, RAILG = 150, 208, 820
    s.line([(120, RAIL5), (1580, RAIL5)], RED, 4)
    s.line([(120, RAIL3), (1080, RAIL3)], "#e07a2b", 4)
    s.line([(120, RAILG), (1580, RAILG)], BLK, 4)
    s.text(120, RAIL5 - 14, "+5V rail", 14, RED, "start", "bold")
    s.text(1094, RAIL3 + 5, "+3V3 rail  (display only — the ring is the sole 5V load)",
           13, "#e07a2b")
    s.text(760, RAILG - 16, "GND rail  —  common ground is mandatory", 14, BLK, "middle", "bold")

    # supply
    s.rect(60, 360, 200, 170)
    s.text(160, 396, "5V supply", 18, INK, "middle", "bold")
    s.text(160, 422, "2A minimum", 14, MUTED, "middle")
    s.line([(160, 360), (160, RAIL5)], RED, 3); s.dot(160, RAIL5, 5, RED)
    s.line([(160, 530), (160, RAILG)], BLK, 3); s.dot(160, RAILG, 5, BLK)

    # ESP32-S3 — power on the left, display bus on the right
    s.rect(360, 300, 300, 430)
    s.text(510, 338, "ESP32-S3-N16R8", 19, INK, "middle", "bold")
    s.text(510, 362, "16MB flash / 8MB octal PSRAM", 13, MUTED, "middle")
    s.text(510, 384, "PSRAM is mandatory here", 13, GRN, "middle", "bold")
    for py, lbl, col in ((424, "5V", RED), (462, "3V3", "#e07a2b"),
                         (500, "GND", BLK), (700, "GPIO5  LED data", YEL)):
        s.text(374, py + 5, lbl, 14, INK)
        s.line([(360, py), (330, py)], col, 3)
    s.line([(330, 424), (330, RAIL5)], RED, 3); s.dot(330, RAIL5, 5, RED)
    s.line([(330, 462), (300, 462), (300, RAIL3)], "#e07a2b", 3); s.dot(300, RAIL3, 5, "#e07a2b")
    s.line([(330, 500), (272, 500), (272, RAILG)], BLK, 3); s.dot(272, RAILG, 5, BLK)

    qspi = [(430, "GPIO18   CLK"), (470, "GPIO46/13/11/12   D0-D3"),
            (510, "GPIO14   CS"), (550, "GPIO47   RST"), (590, "GPIO44   BL")]
    for py, lbl in qspi:
        s.text(646, py + 5, lbl, 13, INK, "end")
        s.line([(660, py), (790, py)], BLU, 2.5)

    # display
    s.rect(790, 300, 310, 360, CARD, BLU, 2.5)
    for py, _ in qspi:
        s.add(f'<rect x="784" y="{py-7}" width="12" height="14" fill="{BLU}"/>')
    s.circle(960, 452, 96, PAPER, BLU, 2)
    s.circle(960, 452, 84, "#eef3fb", BLU, 1)
    s.text(960, 446, "360 x 360", 18, INK, "middle", "bold")
    s.text(960, 470, "ST77916 QSPI", 13, MUTED, "middle")
    s.text(945, 604, "1.85\" round LCD", 15, INK, "middle", "bold")
    s.text(945, 626, "ESPHome model: ESP-VOCAT", 12.5, MUTED, "middle")
    s.line([(840, 300), (840, RAIL3)], "#e07a2b", 2.5); s.dot(840, RAIL3, 4, "#e07a2b")
    s.text(852, 292, "3V3", 12, "#e07a2b")
    s.line([(790, 640), (730, 640), (730, RAILG)], BLK, 2.5); s.dot(730, RAILG, 4, BLK)
    s.text(742, 632, "GND", 12, BLK)

    # ring, well clear of the display
    CX, CY, RR = 1340, 452, 118
    led_ring(s, CX, CY, RR, 24, "LED ring")
    vx, vy = ring_pad(s, CX, CY, RR, 300, RED, "VCC")
    s.line([(vx, vy), (1200, vy), (1200, RAIL5)], RED, 3); s.dot(1200, RAIL5, 5, RED)
    gx, gy = ring_pad(s, CX, CY, RR, 60, BLK, "GND")
    s.line([(gx, gy), (1500, gy), (1500, RAILG)], BLK, 3); s.dot(1500, RAILG, 5, BLK)
    dx, dy = ring_pad(s, CX, CY, RR, 180, YEL, "DIN")

    # LED data: down the left, along the bottom, resistor at the ring end
    s.line([(330, 700), (300, 700), (300, 960), (1180, 960)], YEL, 3)
    resistor(s, 1230, 960, "470 ohm")
    s.line([(1276, 960), (1340, 960), (1340, dy)], YEL, 3)

    capacitor(s, 1560, RAIL5, RAILG, "1000uF")

    notes(s, 50, 1030, 1600, "Before you power it", [
        "1.  THE DISPLAY PINS ABOVE ARE THE ESP-VoCat REFERENCE VALUES, not your panel's. Check your module's pinout and edit the substitutions first.",
        "2.  The panel is a 3.3V device — do NOT feed it 5V. The LED ring is the only 5V load here.",
        "3.  Ground first on, last off. Power the ring before the S3. Never USB and the external supply at the same time.",
        "4.  470 ohm at the RING end of the data wire. Add a 74AHCT125 if you see flicker or a wrong first pixel.",
        "5.  PSRAM is not optional: ESPHome's ST77916 model declares requires={\"psram\"} and will refuse to compile without it.",
    ])
    s.save(path)


def main():
    diagram_d1mini("wiring-d1mini.svg")
    diagram_s3("wiring-s3-round.svg")
    print("Wrote wiring-d1mini.svg, wiring-s3-round.svg")
    try:
        import cairosvg
        for n, w, h in (("wiring-d1mini", 1580, 1130), ("wiring-s3-round", 1700, 1270)):
            cairosvg.svg2png(url=f"{n}.svg", write_to=f"{n}.png",
                             output_width=w, output_height=h)
            print(f"  rendered {n}.png")
    except ImportError:
        print("  (cairosvg missing, SVG only)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
