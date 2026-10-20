#!/usr/bin/env python3
"""10x Editor color-scheme parser and palette normalizer.

The upstream 10x settings live in slynch8/10x ColorSchemes/*.10x_settings.
A copy of those settings is kept in palettes/10x/.

This module exposes the same normalized palette keys used by the fresh,
mini.hues and VS Code generators in this repository, so the Neovim, Doom
Emacs and Kakoune renderers can share one palette.
"""

import glob
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SETTINGS = os.path.join(ROOT, "palettes", "10x")
SUFFIX = ".10x_settings"

# Custom colors are defined in every upstream 10x scheme. They are the best
# source for generic accent roles (orange, green, blue, ...).
CUSTOM_FALLBACK = {
    1: "#72d8dc",
    2: "#ff8c00",
    3: "#ffd370",
    4: "#6fd85b",
    5: "#5e73ff",
    6: "#d661d8",
    7: "#6099d6",
    8: "#acd35f",
    9: "#9ac5d1",
    10: "#d67171",
}


# ---------------------------------------------------------------- color utils
def clamp(x):
    return max(0, min(255, int(round(x))))


def to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def hexs(rgb):
    return "#%02x%02x%02x" % tuple(clamp(c) for c in rgb)


def mix(a, b, t):
    ra, rb = to_rgb(a), to_rgb(b)
    return hexs([ra[i] + (rb[i] - ra[i]) * t for i in range(3)])


def darken(c, t):
    return mix(c, "#000000", t)


def lighten(c, t):
    return mix(c, "#ffffff", t)


def luminance(c):
    r, g, b = to_rgb(c)
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0


def parse_rgb(value):
    """Parse a 10x RGB value, tolerating stray comments/separators."""
    if not value:
        return None
    value = value.split("#", 1)[0].strip()
    if not value or value.lower() == "default":
        return None
    nums = re.findall(r"\d{1,3}", value)
    if len(nums) < 3:
        return None
    rgb = [int(n) for n in nums[:3]]
    if any(n < 0 or n > 255 for n in rgb):
        return None
    return hexs(rgb)


def read_settings(path):
    data = {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or line.lstrip().startswith("#"):
                continue
            match = re.match(r"^([^:]+):\s*(.*)$", line)
            if match:
                data[match.group(1).strip()] = match.group(2).strip()
    return data


def slug(name):
    """Filesystem/theme-safe name, e.g. 'VS+VAX Light' -> 'vs-plus-vax-light'."""
    s = name.replace("+", " plus ")
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "-", s)
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return re.sub(r"-+", "-", s)


def themes():
    for path in sorted(glob.glob(os.path.join(SETTINGS, "*" + SUFFIX))):
        name = os.path.basename(path)[:-len(SUFFIX)]
        yield name, path


# --------------------------------------------------------------- normalization
def normalize(name, data):
    def col(*keys, default=None):
        for key in keys:
            value = parse_rgb(data.get(key))
            if value:
                return value
        return default

    def custom(index):
        return col("Language.Custom%d" % index,
                   default=CUSTOM_FALLBACK.get(index))

    ui_bg = col("UI.UI", "Editor.Background", default="#000000")
    ui_fg = col("UI.UI Text", "Editor.Text", "Language.Text",
                default="#ffffff")

    bg = col("Language.Background", "Editor.Background", "UI.UI",
             default=ui_bg)
    fg = col("Language.Text", "Editor.Text", "UI.UI Text", default=ui_fg)
    light = luminance(bg) > 0.5

    if not ui_bg:
        ui_bg = bg
    if not ui_fg:
        ui_fg = fg

    keyword = col("Language.Keyword", default=fg)
    control = col("Language.ControlFlowKeyword", default=keyword)
    type_ = col("Language.Type", default=keyword)
    preproc = col("Language.Preprocessor", default=keyword)
    comment = col("Language.Comment", default=mix(bg, fg, 0.5))
    doc_comment = col("Language.DocComment", default=comment)
    string = col("Language.String", default=fg)
    number = col("Language.Number", default=fg)
    function = col("Language.Function", default=fg)
    method = col("Language.MemberFunction", default=function)
    variable = col("Language.Variable", default=fg)
    member_var = col("Language.MemberVariable", default=variable)
    class_ = col("Language.Class", default=type_)
    enum = col("Language.Enum", default=class_)
    enum_value = col("Language.Enum Value", default=enum)
    namespace = col("Language.Namespace", default=type_)
    typedef = col("Language.Typedef", default=type_)
    operator = col("Language.Operator", default=fg)
    brace = col("Language.Brace", default=fg)
    bracket = col("Language.Bracket", default=brace)
    square = col("Language.SquareBracket", default=brace)
    semicolon = col("Language.SemiColon", default=operator)
    comma = col("Language.Comma", default=operator)
    heading = col("Language.Heading", default=keyword)
    bold_text = col("Language.Bold", default=keyword)
    italic_text = col("Language.Italic", default=keyword)
    link = col("Language.Link", default=custom(7))
    html_element = col("Html.ElementName", default=function)
    html_attribute = col("Html.AttributeName", default=preproc)
    html_string = col("Html.String", default=string)
    html_operator = col("Html.Operator", default=operator)

    selection_bg = col("Editor.Selection Back", default=mix(bg, fg, 0.25))
    selection_fg = col("Editor.Selection Fore", default=fg)
    cur_line = col("Editor.Current Line", default=mix(bg, fg, 0.08))
    line_nr = col("Editor.Line Numbers", default=mix(bg, fg, 0.40))
    margin = col("Editor.Margin", default=bg)
    whitespace = col("Editor.Whitespace", default=mix(bg, fg, 0.30))
    cursor = col("Editor.Cursor", default=fg)

    menu_bg = col("UI.Menu", default=ui_bg)
    menu_hl = col("UI.Menu (highlighted)", default=selection_bg)
    menu_selected = col("UI.Menu (selected)", default=mix(bg, fg, 0.15))
    active_tab_bg = col("UI.Panels.Active Tab", default=mix(bg, fg, 0.20))
    active_tab_fg = col("UI.Panels.Active Tab Text", default=ui_fg)
    inactive_tab_bg = col("UI.Panels.Inactive Tab", default=mix(bg, fg, 0.08))
    inactive_tab_fg = col("UI.Panels.Inactive Tab Text", default=ui_fg)
    status_bg = col("Editor.StatusBarColour", default=ui_bg)
    status_fg = col("Editor.StatusBarTextColour", default=ui_fg)

    search_bg = col("UI.SearchHighlight", default=mix(bg, fg, 0.25))
    find_hl = col("Editor.Find.Text Highlight", default=mix(bg, fg, 0.20))
    bracket_hl = col("Editor.Find.Bracket Highlight", default=mix(bg, fg, 0.15))
    error = col("Build.BuildError", "UI.10xOutputError", default="#ff5555")
    warning = col("Build.BuildWarning", "UI.10xOutputWarning",
                  default="#ffd75f")
    bookmark = col("Editor.Bookmark", default=warning)
    breakpoint = col("Editor.Breakpoint", default=error)

    border = col("UI.App Border (active)", default=mix(bg, fg, 0.30))
    vertical_bar = col("UI.App Border (inactive)", default=border)

    red = custom(10) or class_ or error
    orange = custom(2) or warning
    green = custom(4) or preproc
    yellow = custom(3) or warning
    blue = custom(5) or custom(7) or "#61afef"
    violet = enum or custom(6)
    cyan = custom(1) or "#56b6c2"
    pink = enum_value or custom(6)
    teal = typedef or type_
    salmon = class_ or red
    success = custom(4) or green

    if light:
        base0 = lighten(bg, 0.50)
        base1 = lighten(bg, 0.30)
        base2 = lighten(bg, 0.15)
        base3 = mix(bg, fg, 0.12)
        base4 = border
        base5 = mix(bg, fg, 0.35)
        base6 = mix(bg, fg, 0.50)
        base7 = mix(bg, fg, 0.70)
        base8 = fg
    else:
        base0 = darken(bg, 0.35)
        base1 = menu_bg
        base2 = mix(bg, fg, 0.07)
        base3 = mix(bg, fg, 0.12)
        base4 = border
        base5 = whitespace
        base6 = line_nr
        base7 = mix(bg, fg, 0.60)
        base8 = fg

    v = {
        "bg": bg, "bg-alt": menu_bg,
        "base0": base0, "base1": base1, "base2": base2, "base3": base3,
        "base4": base4, "base5": base5, "base6": base6, "base7": base7,
        "base8": base8,
        "fg": fg, "fg-alt": mix(bg, fg, 0.60), "grey": base6,

        "red": red, "light-red": lighten(red, 0.25),
        "orange": orange, "green": green, "teal": teal, "yellow": yellow,
        "blue": blue, "magenta": preproc, "violet": violet, "cyan": cyan,
        "pink": pink, "rose": type_, "salmon": salmon,

        "highlight": keyword, "vertical-bar": vertical_bar,
        "selection": selection_bg, "builtin": typedef or type_,
        "comments": comment, "doc-comments": doc_comment,
        "constants": number, "functions": function, "keywords": control,
        "methods": method, "operators": operator, "type": type_,
        "strings": string, "variables": variable, "numbers": number,
        "region": selection_bg, "error": error, "warning": warning,
        "success": success, "vc-modified": warning, "vc-added": success,
        "vc-deleted": error,

        "modeline-bg": status_bg, "modeline-bg-alt": base1,
        "modeline-fg": status_fg, "modeline-fg-alt": base7,
        "modeline-bg-l": darken(bg, 0.10) if not light else lighten(bg, 0.10),
        "modeline-bg-inactive": base1, "modeline-bg-inactive-l": bg,

        "cursor": cursor, "cur-line": cur_line, "line-nr": line_nr,
        "line-nr-bg": margin, "sel-bg": selection_bg,
        "bracket-match": cursor, "match-bg": find_hl, "match-fg": selection_fg,
        "label-bg": search_bg, "label-fg": ui_fg,
        "popup-bg": menu_bg, "popup-fg": ui_fg, "popup-sel-bg": menu_selected,
        "border": border,
        "tab-active-bg": active_tab_bg, "tab-active-fg": active_tab_fg,
        "tab-inactive-bg": inactive_tab_bg, "tab-inactive-fg": inactive_tab_fg,
        "status-bg": status_bg, "status-fg": status_fg, "inline-bg": menu_bg,
        "err-bg": mix(bg, error, 0.25),

        "diff-add-bg": mix(bg, success, 0.20),
        "diff-remove-bg": mix(bg, error, 0.20),
        "diff-modify-bg": mix(bg, warning, 0.20),

        "rain1": custom(1), "rain2": custom(2), "rain3": custom(3),
        "rain4": custom(4), "rain5": custom(5), "rain6": custom(6),

        # Extra 10x roles used by the Neovim renderer.
        "preproc": preproc, "class": class_, "enum": enum,
        "enum-value": enum_value, "namespace": namespace,
        "typedef": typedef, "member-var": member_var,
        "brace": brace, "bracket": bracket, "square": square,
        "semicolon": semicolon, "comma": comma, "heading": heading,
        "bold-text": bold_text, "italic-text": italic_text, "link": link,
        "html-element": html_element, "html-attribute": html_attribute,
        "html-string": html_string, "html-operator": html_operator,
        "bookmark": bookmark, "breakpoint": breakpoint,
        "menu-hl": menu_hl, "bracket-hl": bracket_hl,
        "selection-fg": selection_fg,
    }

    v["dark-blue"] = darken(v["blue"], 0.40)
    v["dark-cyan"] = darken(v["cyan"], 0.40)
    v["dark-violet"] = darken(v["violet"], 0.40)
    v["dark-red"] = darken(v["red"], 0.35)
    v["dark-green"] = darken(v["green"], 0.35)
    v["light-green"] = lighten(v["green"], 0.20)
    v["light-blue"] = lighten(v["blue"], 0.20)
    v["light-yellow"] = lighten(v["yellow"], 0.20)

    ansi = [
        bg, red, success, yellow, blue, preproc, cyan, fg,
        base6, lighten(red, 0.30), lighten(success, 0.30),
        lighten(yellow, 0.30), lighten(blue, 0.30), lighten(preproc, 0.30),
        lighten(cyan, 0.30), "#000000" if light else "#ffffff",
    ]
    for i, color in enumerate(ansi):
        v["term%d" % i] = color

    meta = {
        "name": name,
        "slug": slug(name),
        "light": light,
        "comment_italic": False,
        "kw_bold": False,
        "kw_italic": False,
        "type_bold": False,
        "type_italic": False,
        "keyword": keyword,
        "control": control,
        "preproc": preproc,
        "class": class_,
        "enum": enum,
        "enum_value": enum_value,
        "namespace": namespace,
        "typedef": typedef,
        "member_var": member_var,
        "brace": brace,
        "bracket": bracket,
        "square": square,
        "semicolon": semicolon,
        "comma": comma,
        "heading": heading,
        "bold_text": bold_text,
        "italic_text": italic_text,
        "link": link,
        "bookmark": bookmark,
        "breakpoint": breakpoint,
        "menu_hl": menu_hl,
        "bracket_hl": bracket_hl,
        "selection_fg": selection_fg,
    }
    return v, meta


def palette(name, data):
    """Return the Doom/Kakoune-style tuple used by the existing renderers."""
    v, meta = normalize(name, data)
    return v, meta["kw_bold"], meta["kw_italic"], meta


def all_palettes():
    for name, path in themes():
        yield name, path, read_settings(path)
