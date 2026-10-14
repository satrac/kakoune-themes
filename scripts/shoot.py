#!/usr/bin/env python3
"""Render theme screenshots by driving Kakoune's JSON UI.

Kakoune's `-ui json` emits a resolved face for every display atom, so we can
faithfully rasterize a real editor frame (buffer + status line) without a
terminal emulator.

Usage:
    python3 scripts/shoot.py [theme ...]        # default: every theme
    python3 scripts/shoot.py --montage          # also build screenshots/overview.png

Output: screenshots/<theme>.png
"""

import json
import os
import select
import subprocess
import sys
import tempfile
import time

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
COLORS = os.path.join(ROOT, "colors")
OUT = os.path.join(ROOT, "screenshots")

KAK = os.environ.get("KAK", "kak")
COLS, ROWS = 84, 30

FONT_DIR = "/usr/share/fonts/TTF"
FONT_SIZE = 27
LINE_GAP = 6

SAMPLE = '''#!/usr/bin/env python3
"""Theme preview for the justaperlhacker palettes."""

import math
from dataclasses import dataclass


@dataclass
class Vector:
    x: float
    y: float

    def __add__(self, other: "Vector") -> "Vector":
        return Vector(self.x + other.x, self.y + other.y)

    @property
    def length(self) -> float:
        # euclidean norm
        return math.sqrt(self.x ** 2 + self.y ** 2)


def main(vectors: list[Vector]) -> None:
    total = sum((v.length for v in vectors), 0.0)
    print(f"{len(vectors)} vectors, total length {total:.2f}")


if __name__ == "__main__":
    main([Vector(3, 4), Vector(1, 2)])
'''

# Selection in the sample (line.column, 1-based): the class name in __add__.
SELECT = "select 14.16,14.22"

NAMED = {
    "black": (0x00, 0x00, 0x00), "red": (0xcd, 0x00, 0x00),
    "green": (0x00, 0xcd, 0x00), "yellow": (0xcd, 0xcd, 0x00),
    "blue": (0x00, 0x00, 0xee), "magenta": (0xcd, 0x00, 0xcd),
    "cyan": (0x00, 0xcd, 0xcd), "white": (0xe5, 0xe5, 0xe5),
    "bright-black": (0x7f, 0x7f, 0x7f), "bright-red": (0xff, 0x00, 0x00),
    "bright-green": (0x00, 0xff, 0x00), "bright-yellow": (0xff, 0xff, 0x00),
    "bright-blue": (0x5c, 0x5c, 0xff), "bright-magenta": (0xff, 0x00, 0xff),
    "bright-cyan": (0x00, 0xff, 0xff), "bright-white": (0xff, 0xff, 0xff),
}


def parse_color(value, base):
    if not value or value == "default":
        return base
    if value.startswith("#") and len(value) == 7:
        return (int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16))
    if value.startswith("rgb:") and len(value) == 10:
        h = value[4:]
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    if value in NAMED:
        return NAMED[value]
    return base


def resolve(face, base_fg, base_bg):
    fg = parse_color(face.get("fg"), base_fg)
    bg = parse_color(face.get("bg"), base_bg)
    attrs = set(face.get("attributes", []))
    if "reverse" in attrs:
        fg, bg = bg, fg
    return fg, bg, attrs


def capture(theme, workdir):
    cfg = tempfile.mkdtemp(prefix="kakshot-")
    kcfg = os.path.join(cfg, "kak")
    os.makedirs(kcfg, exist_ok=True)
    link = os.path.join(kcfg, "colors")
    if not os.path.exists(link):
        os.symlink(COLORS, link)

    env = dict(os.environ)
    env["XDG_CONFIG_HOME"] = cfg
    env["TERM"] = "xterm-256color"
    env["COLORTERM"] = "truecolor"

    commands = "\n".join([
        f"colorscheme {theme}",
        "add-highlighter global/number-lines number-lines",
        SELECT,
        'set-option global modelinefmt "%val{bufname} %val{cursor_line}:'
        '%val{cursor_char_column} {{context_info}} {{mode_info}}"',
    ])

    proc = subprocess.Popen(
        [KAK, "-ui", "json", "-s", f"shot-{theme}-{os.getpid()}",
         "-e", commands, "sample.py"],
        cwd=workdir, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, bufsize=0)

    def send(obj):
        proc.stdin.write((json.dumps(obj) + "\n").encode())
        proc.stdin.flush()

    send({"jsonrpc": "2.0", "method": "resize", "params": [COLS, ROWS]})

    os.set_blocking(proc.stdout.fileno(), False)
    buf = b""
    draw = status = None
    last_activity = time.time()
    deadline = time.time() + 8
    while time.time() < deadline:
        r, _, _ = select.select([proc.stdout], [], [], 0.1)
        if r:
            data = proc.stdout.read()
            if data:
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    try:
                        msg = json.loads(line)
                    except ValueError:
                        continue
                    if msg.get("method") == "draw":
                        draw = msg["params"]
                        last_activity = time.time()
                    elif msg.get("method") == "draw_status":
                        status = msg["params"]
                        last_activity = time.time()
        elif draw is not None and status is not None and time.time() - last_activity > 0.4:
            break
    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()
    return draw, status


def build_grid(draw, status):
    lines, _cursor, buf_default, _padding, _widget = draw
    bg_fg = parse_color(buf_default.get("fg"), (0, 0, 0))
    bg_bg = parse_color(buf_default.get("bg"), (0, 0, 0))

    prompt, content, _cpos, mode_line, status_default, _style = status
    st_fg = parse_color(status_default.get("fg"), bg_fg)
    st_bg = parse_color(status_default.get("bg"), bg_bg)

    def width(line):
        return sum(max(1, len(a["contents"].rstrip("\n"))) for a in line)

    ncols = max([COLS] + [width(l) for l in lines] +
                [width(prompt) + width(content), width(mode_line)])

    blank = lambda fg, bg: (" ", fg, bg, frozenset())

    grid = []
    for line in lines:
        row = [blank(bg_fg, bg_bg) for _ in range(ncols)]
        col = 0
        for atom in line:
            fg, bg, attrs = resolve(atom["face"], bg_fg, bg_bg)
            for ch in atom["contents"]:
                if ch == "\n" or col >= ncols:
                    continue
                row[col] = (ch, fg, bg, attrs)
                col += 1
        grid.append(row)

    srow = [blank(st_fg, st_bg) for _ in range(ncols)]
    col = 0
    for atom in prompt + content:
        fg, bg, attrs = resolve(atom["face"], st_fg, st_bg)
        for ch in atom["contents"]:
            if col >= ncols:
                break
            srow[col] = (ch, fg, bg, attrs)
            col += 1
    start = max(0, ncols - width(mode_line))
    for atom in mode_line:
        fg, bg, attrs = resolve(atom["face"], st_fg, st_bg)
        for ch in atom["contents"]:
            if start >= ncols:
                break
            srow[start] = (ch, fg, bg, attrs)
            start += 1
    grid.append(srow)
    return grid


def load_fonts():
    def f(name):
        return ImageFont.truetype(os.path.join(FONT_DIR, f"JetBrainsMono-{name}.ttf"),
                                  FONT_SIZE)
    return {"": f("Regular"), "b": f("Bold"), "i": f("Italic"),
            "bi": f("BoldItalic")}


def render(grid, path, fonts):
    probe = fonts[""]
    cell_w = probe.getlength("M")
    ascent, descent = probe.getmetrics()
    line_h = ascent + descent + LINE_GAP
    ncols = len(grid[0])
    nrows = len(grid)

    img = Image.new("RGB", (round(ncols * cell_w), round(nrows * line_h)), (0, 0, 0))
    d = ImageDraw.Draw(img)
    y_off = LINE_GAP // 2

    for r, row in enumerate(grid):
        y = round(r * line_h)
        # backgrounds as runs
        c = 0
        while c < ncols:
            bg = row[c][2]
            c2 = c + 1
            while c2 < ncols and row[c2][2] == bg:
                c2 += 1
            d.rectangle([round(c * cell_w), y, round(c2 * cell_w), y + line_h], fill=bg)
            c = c2
        # glyphs
        for c, (ch, fg, _bg, attrs) in enumerate(row):
            if ch == " ":
                continue
            style = ("b" if "bold" in attrs else "") + ("i" if "italic" in attrs else "")
            font = fonts.get(style, fonts[""])
            x = round(c * cell_w)
            d.text((x + 1, y + y_off), ch, font=font, fill=fg)
            if attrs & {"underline", "curly_underline", "double_underline"}:
                uy = y + line_h - 3
                d.line([(x, uy), (x + cell_w, uy)], fill=fg, width=2)
            if "strikethrough" in attrs:
                sy = y + line_h // 2
                d.line([(x, sy), (x + cell_w, sy)], fill=fg, width=2)

    img.save(path)
    return img


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    montage = "--montage" in sys.argv
    os.makedirs(OUT, exist_ok=True)
    workdir = tempfile.mkdtemp(prefix="kakshot-src-")
    with open(os.path.join(workdir, "sample.py"), "w") as f:
        f.write(SAMPLE)

    themes = args or sorted(
        os.path.splitext(f)[0] for f in os.listdir(COLORS) if f.endswith(".kak"))
    fonts = load_fonts()

    for theme in themes:
        draw, status = capture(theme, workdir)
        if draw is None or status is None:
            print(f"!! no frame captured for {theme}", file=sys.stderr)
            continue
        grid = build_grid(draw, status)
        path = os.path.join(OUT, f"{theme}.png")
        render(grid, path, fonts)
        print("wrote", os.path.relpath(path, ROOT))

    if montage:
        make_montage(themes, fonts)


def _grid_montage(names, cols, thumb_w, path, label_font):
    thumbs = []
    for name in names:
        img = Image.open(os.path.join(OUT, f"{name}.png"))
        h = round(img.height * thumb_w / img.width)
        thumbs.append((name, img.resize((thumb_w, h), Image.LANCZOS)))
    label_h = 34
    pad = 20
    cell_h = max(t.height for _, t in thumbs) + label_h
    rows = (len(thumbs) + cols - 1) // cols
    canvas = Image.new("RGB",
                       (pad + cols * (thumb_w + pad), pad + rows * (cell_h + pad)),
                       (30, 30, 30))
    d = ImageDraw.Draw(canvas)
    for i, (name, t) in enumerate(thumbs):
        r, c = divmod(i, cols)
        x = pad + c * (thumb_w + pad)
        y = pad + r * (cell_h + pad)
        canvas.paste(t, (x, y))
        d.text((x + 2, y + t.height + 6), name, font=label_font, fill=(200, 200, 200))
    if path.endswith((".jpg", ".jpeg")):
        canvas.save(path, quality=88, optimize=True)
    else:
        canvas.save(path)
    print("wrote", os.path.relpath(path, ROOT))


def make_montage(themes, fonts):
    label_font = ImageFont.truetype(os.path.join(FONT_DIR, "JetBrainsMono-Regular.ttf"), 20)
    picks = [t for t in ["gruvbox", "tokyo-night", "black-metal-gorgoroth",
                         "miniwinter", "naysayer", "monochrome"] if t in themes]
    if picks:
        _grid_montage(picks, cols=2, thumb_w=760,
                      path=os.path.join(OUT, "overview.png"), label_font=label_font)
    _grid_montage(sorted(themes), cols=4, thumb_w=480,
                  path=os.path.join(OUT, "all.jpg"), label_font=label_font)


if __name__ == "__main__":
    main()
