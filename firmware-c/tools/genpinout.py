#!/usr/bin/env python3
"""Generate the Raspberry Pi Pico pinout diagram for the SPIDriver firmware.

Produces images/pico-pinout.svg; rasterize with:
    rsvg-convert -w 1060 images/pico-pinout.svg -o images/pico-pinout.png
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "images", "pico-pinout.svg")

# 10 px per mm; Pico board is 51 x 21 mm
S = 10
BW, BH = 51 * S, 21 * S
PITCH = 2.54 * S

# ---- colors ---------------------------------------------------------------
C_BOARD = "#1a6b43"
C_BOARD_DK = "#155736"
C_PAD = "#d4b26a"
C_DIM = "#9db8a5"

C_SPI = "#f0a92e"  # target SPI bus
C_AUX = "#e05fd0"  # A / B aux outputs
C_LCD = "#46a0f0"  # LCD bus (SPI0)
C_ADC = "#f2d24c"  # analog inputs
C_PWR = "#e2574c"  # power
C_GND = "#7d8a80"  # ground

# ---- pin data: (number, label, function, color-or-None) -------------------
# bottom row, left -> right (pins 1..20)
BOTTOM = [
    (1, "GP0", None, None),
    (2, "GP1", None, None),
    (3, "GND", "GND", C_GND),
    (4, "GP2", "SCK", C_LCD),
    (5, "GP3", "MOSI", C_LCD),
    (6, "GP4", "DC", C_LCD),
    (7, "GP5", "CS", C_LCD),
    (8, "GND", "GND", C_GND),
    (9, "GP6", "A", C_AUX),
    (10, "GP7", "B", C_AUX),
    (11, "GP8", "MISO", C_SPI),
    (12, "GP9", "CS", C_SPI),
    (13, "GND", "GND", C_GND),
    (14, "GP10", "SCK", C_SPI),
    (15, "GP11", "MOSI", C_SPI),
    (16, "GP12", None, None),
    (17, "GP13", None, None),
    (18, "GND", "GND", C_GND),
    (19, "GP14", None, None),
    (20, "GP15", None, None),
]
# top row, left -> right (pins 40..21)
TOP = [
    (40, "VBUS", "VBUS", C_PWR),
    (39, "VSYS", None, None),
    (38, "GND", "GND", C_GND),
    (37, "3V3EN", None, None),
    (36, "3V3", "3V3", C_PWR),
    (35, "VREF", None, None),
    (34, "GP28", None, None),
    (33, "AGND", "GND", C_GND),
    (32, "GP27", "CURR", C_ADC),
    (31, "GP26", "VBUS", C_ADC),
    (30, "RUN", None, None),
    (29, "GP22", None, None),
    (28, "GND", "GND", C_GND),
    (27, "GP21", None, None),
    (26, "GP20", None, None),
    (25, "GP19", None, None),
    (24, "GP18", None, None),
    (23, "GND", "GND", C_GND),
    (22, "GP17", None, None),
    (21, "GP16", None, None),
]

# ---- svg helpers ----------------------------------------------------------
parts = []
W = BW + 2 * S
H = 380


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def rect(x, y, w, h, fill, rx=0, stroke=None):
    s = f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx:.1f}" fill="{fill}"'
    if stroke:
        s += f' stroke="{stroke}" stroke-width="1"'
    parts.append(s + "/>")


def text(x, y, s, size, fill, anchor="middle", bold=False, mono=True):
    font = "DejaVu Sans Mono" if mono else "DejaVu Sans"
    w = ' font-weight="bold"' if bold else ""
    parts.append(
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{font}" font-size="{size}"'
        f' fill="{fill}" text-anchor="{anchor}"{w}>{esc(s)}</text>'
    )


# ---- board ----------------------------------------------------------------
OX, OY = S, S + 8
rect(OX, OY, BW, BH, C_BOARD, rx=12)
rect(OX, OY, BW, BH, C_BOARD, rx=12, stroke="#123f27")

# USB connector on the left short edge
usb_y = OY + BH / 2 - 40
rect(OX - 26, usb_y, 26, 80, "#b9bec3", rx=3)
rect(OX - 12, usb_y + 8, 12, 64, "#3d444c")

# RP2040 chip + silkscreen
rect(OX + 220, OY + 45, 60, 60, "#0d0d0d", rx=6)
text(OX + 250, OY + 75, "RP2040", 10, "#ffffff")
text(OX + 250, OY + 115, "SPIDriver", 13, "#ffffff", bold=True)

# mounting holes
for hx in (OX + 12, OX + BW - 12):
    parts.append(
        f'<circle cx="{hx:.1f}" cy="{OY + BH / 2:.1f}" r="6" fill="{C_BOARD_DK}"/>'
    )


# ---- pins ----------------------------------------------------------------
def pinpad(x, y, pin, label, func, color):
    """x,y = top-left of pad; pad extends outward from the board edge."""
    pad = C_PAD if color is None else color
    stroke = C_PAD if color is None else "#00000055"
    rect(x, y, 15, 20, pad, rx=3, stroke=stroke)
    if func:
        text(x + 7.5, y + 10, str(pin), 6.5, "#101010", mono=True)
    else:
        text(x + 7.5, y + 10, str(pin), 7, "#5c4a2a", mono=True)
    # labels inside the board
    lx = x + 7.5
    tcol = color if color else C_DIM
    if color in (C_ADC, C_SPI, C_AUX):
        tcol = color
    fsize = 8 if len(label) <= 5 else 7
    if y < OY + BH / 2:  # top row: labels below the pad
        text(lx, y + 32, label, fsize, tcol, bold=bool(func))
        if func:
            text(lx, y + 43, func, 8.5, tcol, bold=True)
    else:  # bottom row: labels above the pad
        text(lx, y - 12, label, fsize, tcol, bold=bool(func))
        if func:
            text(lx, y - 2, func, 8.5, tcol, bold=True)


for i, (pin, label, func, color) in enumerate(BOTTOM):
    px = OX + 12 + i * PITCH
    pinpad(px, OY + BH - 18, pin, label, func, color)
for i, (pin, label, func, color) in enumerate(TOP):
    px = OX + 12 + i * PITCH
    pinpad(px, OY - 2, pin, label, func, color)


# ---- legend --------------------------------------------------------------
text(
    OX + BW / 2,
    OY + BH + 14,
    "Raspberry Pi Pico \u00b7 SPIDriver pinout \u00b7 top view, USB on the left",
    11.5,
    "#ffffff",
    bold=True,
    mono=False,
)
ly = OY + BH + 34
items = [
    (
        C_LCD,
        "LCD (SPI0):  SCK (GP2)  MOSI (GP3)  DC (GP4)  CS (GP5)  RESET tied to 3V3",
    ),
    (C_SPI, "target SPI1:  SCK (GP10)  MOSI (GP11)  MISO (GP8)  CS (GP9)"),
    (C_AUX, "aux outputs:  A (GP6)  B (GP7)"),
    (C_ADC, "analog:  VBUS (GP26 / ADC0)  current (GP27 / ADC1)  temp = internal ADC4"),
    (C_PWR, "power:  VBUS (pin 40)  3V3 (pin 36)"),
    (C_GND, "GND"),
]
for i, (color, label) in enumerate(items):
    yy = ly + i * 18
    rect(OX + 6, yy, 14, 12, color, rx=2)
    text(OX + 30, yy + 11, label, 10.5, "#ffffff", anchor="start", mono=True)

parts.insert(
    0,
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
    f'viewBox="0 0 {W} {H}">\n<rect width="100%" height="100%" fill="#20262b"/>',
)
parts.append("</svg>")

try:
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(parts) + "\n")
except OSError as e:
    raise SystemExit(f"cannot write {OUT}: {e}") from e

print("wrote", OUT)
