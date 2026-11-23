#!/usr/bin/env python3
"""The World in One Day -- Sunday, 22 November 2026.

A front page drawn entirely in code: standard library only, no network,
no randomness, no wall clock. Running this file twice writes byte-identical
PNG bytes to $MAKEFUN_OUTPUT_DIR/entry.png (or ./out/entry.png).

Design: a broadsheet front page. A masthead names the day, a hero story
carries the biggest news of the day (the collapse of the COP31 climate
talks), six illustrated cards carry the next stories, and an "Also today"
ticker carries nine more. Every story was checked against real reporting
of 21-22 November 2026; see SOURCES.md for the source of each story.
"""

import os
import struct
import sys
import zlib

WIDTH = 1024
HEIGHT = 1024

# ---------------------------------------------------------------- palette
PAPER = (247, 242, 231)
INK = (20, 20, 20)
GREY = (110, 105, 95)
RED = (176, 30, 36)
NAVY = (29, 58, 95)
TEAL = (15, 107, 92)
SKY = (140, 190, 225)
SEA = (38, 84, 130)
GOLD = (198, 148, 42)
CREAM = (252, 248, 238)
DARK = (32, 34, 40)
ORANGE = (214, 110, 44)
GREEN = (46, 125, 70)
LIGHT_BLUE = (178, 210, 235)
SAND = (226, 205, 160)

# ------------------------------------------------------------- PNG writer
def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(path, width, height, pixels):
    """pixels: bytearray of width*height*3 RGB bytes, top row first."""
    raw = b"".join(
        b"\x00" + bytes(pixels[y * width * 3:(y + 1) * width * 3])
        for y in range(height)
    )
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += _chunk(b"IDAT", zlib.compress(raw, 9))
    png += _chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(png)
    return png


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, width, height, bg):
        self.w = width
        self.h = height
        self.px = bytearray(width * height * 3)
        self.fill_rect(0, 0, width, height, bg)

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = color

    def fill_rect(self, x, y, w, h, color):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i], self.px[i + 1], self.px[i + 2] = color

    def rect_outline(self, x, y, w, h, color, t=1):
        self.fill_rect(x, y, w, t, color)
        self.fill_rect(x, y + h - t, w, t, color)
        self.fill_rect(x, y, t, h, color)
        self.fill_rect(x + w - t, y, t, h, color)

    def line(self, x0, y0, x1, y1, color, t=1):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        x, y = x0, y0
        while True:
            self.fill_rect(x - t // 2, y - t // 2, t, t, color)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

    def fill_circle(self, cx, cy, r, color):
        for yy in range(cy - r, cy + r + 1):
            dx = int((r * r - (yy - cy) ** 2) ** 0.5) if abs(yy - cy) <= r else 0
            self.fill_rect(cx - dx, yy, dx * 2 + 1, 1, color)

    def circle_outline(self, cx, cy, r, color, t=2):
        for a in range(360):
            import math
            rad = math.radians(a)
            self.fill_rect(
                int(cx + r * math.cos(rad)) - t // 2,
                int(cy + r * math.sin(rad)) - t // 2, t, t, color)

    def fill_triangle(self, p1, p2, p3, color):
        xs = sorted([p1, p2, p3], key=lambda p: p[1])
        (x1, y1), (x2, y2), (x3, y3) = xs
        if y1 == y3:
            return
        for yy in range(y1, y3 + 1):
            if yy < y2:
                xa = x1 + (x2 - x1) * (yy - y1) / max(1, y2 - y1)
                xb = x1 + (x3 - x1) * (yy - y1) / max(1, y3 - y1)
            else:
                xa = x2 + (x3 - x2) * (yy - y2) / max(1, y3 - y2)
                xb = x1 + (x3 - x1) * (yy - y1) / max(1, y3 - y1)
            self.fill_rect(int(min(xa, xb)), yy, int(abs(xb - xa)) + 1, 1, color)


# ------------------------------------------------- bitmap font (own design)
# Each glyph: 7 rows of 5 bits, top row first, "#" = on.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "a": ("00000", "00000", "01110", "00001", "01111", "10001", "01111"),
    "b": ("10000", "10000", "11110", "10001", "10001", "10001", "11110"),
    "c": ("00000", "00000", "01110", "10000", "10000", "10001", "01110"),
    "d": ("00001", "00001", "01111", "10001", "10001", "10001", "01111"),
    "e": ("00000", "00000", "01110", "10001", "11111", "10000", "01110"),
    "f": ("00110", "01000", "01000", "11110", "01000", "01000", "01000"),
    "g": ("00000", "00000", "01111", "10001", "10001", "01111", "00001"),
    "h": ("10000", "10000", "11110", "10001", "10001", "10001", "10001"),
    "i": ("00000", "00100", "00000", "01100", "00100", "00100", "01110"),
    "j": ("00010", "00000", "00110", "00010", "00010", "00010", "01100"),
    "k": ("10000", "10000", "10010", "10100", "11000", "10100", "10010"),
    "l": ("01100", "00100", "00100", "00100", "00100", "00100", "01110"),
    "m": ("00000", "00000", "11010", "10101", "10101", "10101", "10101"),
    "n": ("00000", "00000", "11110", "10001", "10001", "10001", "10001"),
    "o": ("00000", "00000", "01110", "10001", "10001", "10001", "01110"),
    "p": ("00000", "00000", "11110", "10001", "10001", "11110", "10000"),
    "q": ("00000", "00000", "01111", "10001", "10001", "01111", "00001"),
    "r": ("00000", "00000", "10110", "11001", "10000", "10000", "10000"),
    "s": ("00000", "00000", "01111", "10000", "01110", "00001", "11110"),
    "t": ("01000", "01000", "11100", "01000", "01000", "01000", "00110"),
    "u": ("00000", "00000", "10001", "10001", "10001", "10011", "01101"),
    "v": ("00000", "00000", "10001", "10001", "10001", "01010", "00100"),
    "w": ("00000", "00000", "10001", "10101", "10101", "10101", "01010"),
    "x": ("00000", "00000", "10001", "01010", "00100", "01010", "10001"),
    "y": ("00000", "00000", "10001", "10001", "01111", "00001", "00110"),
    "z": ("00000", "00000", "11111", "00010", "00100", "01000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "*": ("00000", "10101", "01110", "11111", "01110", "10101", "00000"),
}


def text_width(text, scale):
    return len(text) * 6 * scale - scale


def draw_text(cv, x, y, text, scale, color):
    """Draw text left-aligned at (x, y); returns the width in pixels."""
    cx = x
    for ch in text:
        glyph = FONT.get(ch, FONT[" "])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == "1":
                    cv.fill_rect(cx + col * scale, y + row * scale,
                                 scale, scale, color)
        cx += 6 * scale
    return cx - x - scale


def draw_text_centered(cv, x, y, w, text, scale, color):
    tw = text_width(text, scale)
    draw_text(cv, x + (w - tw) // 2, y, text, scale, color)


def wrap(text, max_chars):
    """Greedy word wrap; returns a list of lines, each <= max_chars."""
    words = text.split(" ")
    lines, cur = [], ""
    for word in words:
        if not cur:
            cur = word
        elif len(cur) + 1 + len(word) <= max_chars:
            cur += " " + word
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_wrapped(cv, x, y, text, scale, color, max_chars, leading=None):
    """Draw wrapped text; returns the y just below the last line."""
    if leading is None:
        leading = 7 * scale + 2
    for line in wrap(text, max_chars):
        draw_text(cv, x, y, line, scale, color)
        y += leading
    return y


# ------------------------------------------------------------- illustrations
def draw_globe(cv, cx, cy, r, sea_c, land_c):
    cv.fill_circle(cx, cy, r, sea_c)
    cv.circle_outline(cx, cy, r, INK, 2)
    cv.fill_circle(cx - r // 3, cy - r // 4, r // 4, land_c)
    cv.fill_circle(cx + r // 4, cy + r // 5, r // 3, land_c)
    cv.fill_circle(cx + r // 5, cy - r // 2, r // 6, land_c)
    cv.fill_circle(cx - r // 2, cy + r // 3, r // 6, land_c)


def draw_burst(cv, cx, cy, r, color):
    """An explosion starburst: eight spikes around a filled centre."""
    import math
    for k in range(8):
        ang = math.radians(k * 45)
        x2 = int(cx + r * math.cos(ang))
        y2 = int(cy + r * math.sin(ang))
        cv.fill_triangle((cx, cy),
                         (int(cx + (r // 3) * math.cos(ang + 0.35)),
                          int(cy + (r // 3) * math.sin(ang + 0.35))),
                         (x2, y2), color)
        cv.fill_triangle((cx, cy),
                         (int(cx + (r // 3) * math.cos(ang - 0.35)),
                          int(cy + (r // 3) * math.sin(ang - 0.35))),
                         (x2, y2), color)
    cv.fill_circle(cx, cy, max(3, r // 3), color)


def draw_ship(cv, x, y, w, h, hull_c, deck_c):
    """A warship seen from the side, bow to the right."""
    cv.fill_triangle((x + w, y + h // 3), (x + w, y + h),
                     (x + int(w * 0.72), y + h), hull_c)
    cv.fill_rect(x, y + h // 3, int(w * 0.72), int(h * 0.67), hull_c)
    cv.fill_rect(x + int(w * 0.18), y, int(w * 0.30), h // 3, deck_c)
    cv.fill_rect(x + int(w * 0.52), y + h // 6, 4, h // 4, deck_c)
    cv.fill_rect(x + int(w * 0.60), y, 3, h // 3, deck_c)
    cv.fill_rect(x + int(w * 0.08), y + h // 2, int(w * 0.12), 4, deck_c)


def draw_block(cv, x, y, w, h, wall_c, win_c, broken=False):
    """An apartment block with a lit window grid; optionally collapsed."""
    cv.fill_rect(x, y, w, h, wall_c)
    cols, rows = max(2, w // 22), max(2, h // 20)
    for r in range(rows):
        for c in range(cols):
            wx = x + 6 + c * ((w - 12) // cols)
            wy = y + 6 + r * ((h - 12) // rows)
            cv.fill_rect(wx, wy, 9, 8, win_c)
    if broken:
        rubble = (96, 90, 82)
        cv.fill_triangle((x + w, y + h // 4), (x + w, y + h // 2),
                         (x + int(w * 0.6), y + h // 2), rubble)
        cv.fill_rect(x + int(w * 0.62), y + h // 2 - 4, 14, 5, rubble)
        cv.fill_rect(x + int(w * 0.78), y + h // 2 - 3, 10, 4, rubble)
        cv.fill_rect(x + int(w * 0.68), y + h - 12, 26, 6, rubble)
        cv.fill_circle(x + int(w * 0.8), y + int(h * 0.62), 11, (150, 146, 138))
        cv.fill_circle(x + int(w * 0.66), y + int(h * 0.74), 8, (150, 146, 138))


def draw_dome(cv, cx, base_y, w, color):
    """A capitol dome sized to its panel: drum, columns, half-dome, finial."""
    r = 24
    cv.fill_rect(cx - w // 2, base_y - 10, w, 10, color)
    for i in range(5):
        x = cx - w // 2 + 6 + i * ((w - 12) // 5)
        cv.fill_rect(x, base_y - 26, 6, 16, color)
    for yy in range(base_y - 26 - r, base_y - 26 + 1):
        dx = int((r * r - (yy - (base_y - 26)) ** 2) ** 0.5)
        cv.fill_rect(cx - dx, yy, dx * 2 + 1, 1, color)
    cv.fill_rect(cx - 2, base_y - 26 - r - 6, 4, 7, color)
    cv.fill_circle(cx, base_y - 26 - r - 7, 3, RED)


def draw_towers(cv, x, base_y, w, color):
    """Refinery towers with pipes and a flare."""
    for i, tw in enumerate((16, 12, 20)):
        tx = x + i * 34
        cv.fill_rect(tx, base_y - 52 + i * 6, tw, 52 - i * 6, color)
        cv.fill_rect(tx - 2, base_y - 56 + i * 6, tw + 4, 4, color)
    cv.line(x + 8, base_y - 52, x + 70, base_y - 30, color, 3)
    cv.fill_circle(x + 74, base_y - 58, 5, ORANGE)
    cv.fill_circle(x + 74, base_y - 58, 9, GOLD)


def draw_badge(cv, cx, cy, r, gold_c, star_c):
    cv.fill_circle(cx, cy, r, gold_c)
    cv.circle_outline(cx, cy, r, INK, 2)
    cv.fill_circle(cx, cy, r - 6, star_c)
    import math
    pts = []
    for k in range(5):
        ang = math.radians(-90 + k * 72)
        pts.append((int(cx + (r - 10) * math.cos(ang)),
                    int(cy + (r - 10) * math.sin(ang))))
        ang2 = math.radians(-90 + k * 72 + 36)
        pts.append((int(cx + (r - 10) * 0.45 * math.cos(ang2)),
                    int(cy + (r - 10) * 0.45 * math.sin(ang2))))
    for k in range(5):
        cv.fill_triangle((cx, cy), pts[2 * k], pts[2 * k + 1], INK)
        cv.fill_triangle((cx, cy), pts[2 * k + 1],
                         pts[(2 * k + 2) % 10], INK)


def draw_cuffs(cv, x, y, color):
    cv.circle_outline(x, y, 11, color, 3)
    cv.circle_outline(x + 34, y, 11, color, 3)
    cv.line(x + 11, y - 6, x + 23, y - 6, color, 3)
    cv.line(x + 11, y + 6, x + 23, y + 6, color, 3)


def draw_server(cv, x, y, w, h, color):
    cv.fill_rect(x, y, w, h, color)
    cv.rect_outline(x, y, w, h, INK, 2)
    for r in range(4):
        yy = y + 6 + r * ((h - 12) // 4)
        cv.fill_rect(x + 6, yy, w - 12, 3, INK)
        for c, lc in enumerate((RED, GOLD, GREEN, SKY)):
            cv.fill_rect(x + 8 + c * 10, yy + 6, 5, 5, lc)


def draw_magnifier(cv, cx, cy, r, color):
    cv.circle_outline(cx, cy, r, color, 4)
    cv.line(cx + int(r * 0.7), cy + int(r * 0.7),
            cx + r + 12, cy + r + 12, color, 5)


# ------------------------------------------------------------ scene panels
def scene_hero(cv, x, y, w, h):
    """COP31: a globe under a hot sun, crossed by a red no-deal slash."""
    cv.fill_rect(x, y, w, h, SKY)
    cv.fill_circle(x + 42, y + 30, 18, GOLD)
    draw_globe(cv, x + w // 2 + 20, y + h // 2 + 6, 62, SEA, GREEN)
    cv.line(x + 30, y + h - 26, x + w - 30, y + h - 26, INK, 2)
    for sx in (x + 60, x + 130, x + 200):
        cv.fill_rect(sx, y + h - 52, 14, 26, DARK)
        cv.fill_circle(sx + 7, y + h - 56, 5, (150, 146, 138))
    cv.line(x + w // 2 - 52, y + 18, x + w // 2 + 92, y + h - 40, RED, 6)
    cv.fill_rect(x + w - 108, y + 14, 92, 26, RED)
    draw_text(cv, x + w - 100, y + 20, "NO DEAL", 2, CREAM)


def scene_ship(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, NAVY)
    cv.fill_circle(x + w - 34, y + 22, 10, CREAM)
    draw_ship(cv, x + 26, y + h - 58, w - 60, 34, (120, 124, 128), CREAM)
    cv.fill_rect(x, y + h - 22, w, 4, SKY)
    cv.fill_rect(x, y + h - 14, w, 4, SKY)
    draw_burst(cv, x + w // 2 + 8, y + 26, 16, ORANGE)
    cv.fill_circle(x + 40, y + 22, 3, CREAM)
    cv.line(x + 40, y + 22, x + 48, y + 14, CREAM, 1)


def scene_flats(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, LIGHT_BLUE)
    draw_block(cv, x + 30, y + 10, 110, h - 22, SAND, (90, 90, 100),
               broken=True)
    draw_block(cv, x + 160, y + 22, 84, h - 34, (200, 190, 170),
               (90, 90, 100))
    cv.fill_circle(x + w - 40, y + h - 30, 12, (150, 146, 138))
    cv.fill_circle(x + w - 58, y + h - 22, 8, (150, 146, 138))


def scene_dome(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, NAVY)
    for sx in (x + 24, x + 76, x + 128, x + 180, x + 232, x + 280):
        cv.fill_circle(sx, y + 16, 3, CREAM)
    draw_dome(cv, x + 92, y + h - 8, 120, CREAM)
    draw_text(cv, x + 190, y + h - 52, "258", 4, RED)


def scene_bahrain(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (232, 170, 110))
    cv.fill_circle(x + w - 40, y + 24, 14, GOLD)
    draw_towers(cv, x + 30, y + h - 8, 120, DARK)
    cv.line(x + 210, y + 12, x + 150, y + 44, CREAM, 3)
    draw_burst(cv, x + 150, y + 48, 15, RED)
    cv.fill_circle(x + 210, y + 12, 4, ORANGE)


def scene_chapo(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (30, 70, 52))
    draw_badge(cv, x + 78, y + h // 2, 30, GOLD, CREAM)
    draw_cuffs(cv, x + 168, y + h // 2, CREAM)
    draw_text(cv, x + 226, y + h // 2 - 8, "FBI", 2, CREAM)


def scene_fbi(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, DARK)
    draw_server(cv, x + 24, y + 8, 120, h - 16, (58, 62, 72))
    draw_server(cv, x + 160, y + 8, 120, h - 16, (58, 62, 72))
    draw_magnifier(cv, x + 212, y + h // 2, 26, RED)
    draw_text(cv, x + 26, y + h - 24, "NCIC", 2, CREAM)


# ------------------------------------------------------------------- cards
# (kicker, headline, deck, scene)
CARDS = [
    ("CONFLICT - LIBYA",
     "WARSHIP HIT AT BENGHAZI PORT",
     "Suspected Ukrainian drone hits a Russian warship.",
     scene_ship),
    ("WAR - UKRAINE",
     "FLATS COLLAPSE IN STRIKE NEAR KYIV",
     "Russian strike flattens flats in Dymer; 3 killed.",
     scene_flats),
    ("POLITICS - USA",
     "DEMOCRATS WIN HOUSE BY 258",
     "North Carolina recount seals biggest majority since 1992.",
     scene_dome),
    ("MIDDLE EAST - BAHRAIN",
     "IRAN STRIKES HIT BAHRAIN SITE",
     "Missiles hit a civilian site; two hurt. Tankers burn near Hormuz.",
     scene_bahrain),
    ("JUSTICE - MEXICO",
     "EL CHAPO ISIDRO CAPTURED",
     "FBI most-wanted boss seized in a Sinaloa raid; 11 killed.",
     scene_chapo),
    ("CYBER - USA",
     "FBI PROBES HACK OF CRIME FILES",
     "Apparent breach of the NCIC database is under investigation.",
     scene_fbi),
]

# (lead-in, rest of the line)
TICKER = [
    ("MARKETS", "S&P 500 down 3.7%, Nikkei down 5.06% as AI sell-off bites"),
    ("SPORT", "Alcaraz beats Zverev 6-2, 7-6 to win first ATP Finals title"),
    ("INDONESIA", "Candy factory fire in Banten kills 3; dozens missing"),
    ("WEST BANK", "Settlers torch 12 vehicles; Israel opens inquiry"),
    ("SPACE", "BepiColombo enters orbit around Mercury after 8-year trip"),
    ("TRADE", "EU and Indonesia sign landmark deal after a decade of talks"),
    ("SEOUL", "Education minister quits over exam AI-cheating row"),
    ("SUDAN", "Drone strikes kill five children in Khartoum"),
    ("NIGERIA", "At least 24 dead as boat capsizes on way to a funeral"),
]


# --------------------------------------------------------------------- page
MARGIN = 28
CONTENT_W = WIDTH - 2 * MARGIN


def draw_page():
    cv = Canvas(WIDTH, HEIGHT, PAPER)

    # Top bar: edition left, date right.
    draw_text(cv, MARGIN, 14, "SUNDAY EDITION", 2, GREY)
    draw_text(cv, WIDTH - MARGIN - text_width("22 NOVEMBER 2026", 2), 14,
              "22 NOVEMBER 2026", 2, GREY)
    cv.fill_rect(MARGIN, 38, CONTENT_W, 2, INK)

    # Masthead.
    draw_text_centered(cv, MARGIN, 48, CONTENT_W, "THE WORLD IN ONE DAY",
                       6, INK)

    # Dateline, framed by rules.
    cv.fill_rect(MARGIN, 98, CONTENT_W, 2, RED)
    draw_text_centered(cv, MARGIN, 104, CONTENT_W,
                       "SUNDAY, 22 NOVEMBER 2026", 3, RED)
    cv.fill_rect(MARGIN, 130, CONTENT_W, 2, RED)

    # Hero: COP31.
    hx, hy, hw, hh = MARGIN, 140, CONTENT_W, 212
    cv.rect_outline(hx, hy, hw, hh, INK, 2)
    draw_text(cv, hx + 16, hy + 16, "CLIMATE - ANTALYA, TURKEY", 2, RED)
    draw_text(cv, hx + 16, hy + 40, "COP31 ENDS", 4, INK)
    draw_text(cv, hx + 16, hy + 72, "WITH NO DEAL", 4, INK)
    draw_wrapped(cv, hx + 16, hy + 112,
                 "After 17 days in Antalya, the summit closes two days "
                 "late with no deal. About 130 parties rejected the draft.",
                 2, INK, 46)
    cv.fill_rect(hx + 16, hy + 176, 10, 10, RED)
    draw_text(cv, hx + 32, hy + 174, "LONGEST UN CLIMATE SUMMIT ON RECORD",
              2, INK)
    scene_hero(cv, hx + 584, hy + 10, 368, hh - 20)

    # Cards: three columns, two rows.
    card_w, card_h, gap = 312, 216, 16
    for i, (kicker, headline, deck, scene) in enumerate(CARDS):
        col, row = i % 3, i // 3
        cx = MARGIN + col * (card_w + gap)
        cy = 364 + row * (card_h + 12)
        cv.rect_outline(cx, cy, card_w, card_h, INK, 2)
        scene(cv, cx + 2, cy + 2, card_w - 4, 68)
        draw_text(cv, cx + 10, cy + 78, kicker, 2, RED)
        head_lines = wrap(headline, 16)
        hyy = cy + 96
        for line in head_lines:
            draw_text(cv, cx + 10, hyy, line, 3, INK)
            hyy += 22
        draw_wrapped(cv, cx + 10, hyy + 4, deck, 2, INK, 24, leading=15)

    # Ticker: nine more stories.
    ty = 820
    cv.fill_rect(MARGIN, ty, CONTENT_W, 2, INK)
    draw_text(cv, MARGIN, ty + 8, "ALSO TODAY", 2, RED)
    draw_text(cv, MARGIN + text_width("ALSO TODAY", 2) + 12, ty + 8,
              "NINE MORE STORIES FROM SUNDAY", 2, GREY)
    ly = ty + 28
    for lead, rest in TICKER:
        cv.fill_rect(MARGIN, ly + 3, 8, 8, RED)
        draw_text(cv, MARGIN + 16, ly, lead + ":", 2, RED)
        draw_text(cv, MARGIN + 16 + text_width(lead + ": ", 2), ly, rest,
                  2, INK)
        ly += 15

    # Footer: sources.
    draw_text_centered(cv, MARGIN, 988, CONTENT_W,
                       "SOURCES: BBC - AP - REUTERS - CNN - AL JAZEERA - "
                       "AFP - ONE TURN", 2, GREY)
    draw_text_centered(cv, MARGIN, 1002, CONTENT_W,
                       "DRAWN BY CODE - NO PHOTOGRAPHS - STORIES AS "
                       "REPORTED 21-22 NOVEMBER 2026", 2, GREY)
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "out")
    os.makedirs(out_dir, exist_ok=True)
    cv = draw_page()
    path = os.path.join(out_dir, "entry.png")
    write_png(path, WIDTH, HEIGHT, cv.px)
    size = os.path.getsize(path)
    print(f"wrote {path} ({size} bytes, {WIDTH}x{HEIGHT})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
