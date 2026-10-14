#!/usr/bin/env python3
"""Generate Kakoune colorschemes for the justaperlhacker theme family.

Source of truth:
  palettes/fresh/*.json     fresh-editor palettes (primary source)
  palettes/mini/*.lua       Neovim mini.hues "four seasons" palettes
  palettes/vscode/*.json    VS Code color-theme JSON (extra variants)

Output:
  colors/<name>.kak

The palette normalization mirrors the Doom Emacs generator
(doom/scripts/gen_doom_themes.py) so every editor in the family shares one
palette. Only the renderer differs.
"""

import json
import os
import re
from string import Template

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRESH = os.path.join(ROOT, "palettes", "fresh")
VSC = os.path.join(ROOT, "palettes", "vscode")
MINI = os.path.join(ROOT, "palettes", "mini")
OUT = os.path.join(ROOT, "colors")

# Extra variants sourced from the VS Code color-theme JSON (anything not
# already produced from a fresh palette). dankshell-* are intentionally
# excluded -- not part of this family.
VSC_THEMES = [
    "monochrome", "monochrome-amber", "monochrome-chroma", "monochrome-green",
    "chocolatier", "batman", "black-metal", "doom-rouge",
    "black-metal-light", "black-metal-gorgoroth-light",
    "miniwinter-light", "minispring-light", "minisummer-light", "miniautumn-light",
]

# The four "mini.hues" season schemes. miniwinter is already covered by a fresh
# palette, the other three come from the nvim plugin.
MINI_THEMES = ["miniwinter", "minispring", "minisummer", "miniautumn"]


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


def pick(candidates, fallback):
    for c in candidates:
        if c:
            return c
    return fallback


def kak(c):
    """Convert a #rrggbb string to Kakoune's rgb:RRGGBB syntax."""
    if isinstance(c, str) and c.startswith("#"):
        return "rgb:" + c[1:]
    return c


# --------------------------------------------------------------- json access
def path(d, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def rgb(d, *keys, default=None):
    val = path(d, *keys)
    if val is None:
        return default
    if isinstance(val, dict):
        val = val.get("color")
    if isinstance(val, list) and len(val) >= 3:
        return hexs(val)
    if isinstance(val, str):
        return val
    return default


def modifier(d, *keys):
    val = path(d, *keys)
    if isinstance(val, dict):
        return val.get("modifier", [])
    return []


# ------------------------------------------------------------ fresh palettes
def palette_from_fresh(name, data):
    bg = pick([rgb(data, "editor", "bg")], "#1e1e1e")
    fg = pick([rgb(data, "editor", "fg")], "#d4d4d4")
    cursor = pick([rgb(data, "editor", "cursor")], fg)
    inactive_cursor = pick([rgb(data, "editor", "inactive_cursor")], mix(bg, fg, 0.6))
    selection = pick([rgb(data, "editor", "selection_bg")], mix(bg, fg, 0.25))
    cur_line = pick([rgb(data, "editor", "current_line_bg")], mix(bg, fg, 0.08))
    line_nr = pick([rgb(data, "editor", "line_number_fg")], mix(bg, fg, 0.35))
    line_nr_bg = pick([rgb(data, "editor", "line_number_bg")], bg)
    ws = pick([rgb(data, "editor", "whitespace_indicator_fg")], mix(bg, fg, 0.3))
    bracket_match = pick([rgb(data, "editor", "bracket_match_fg")], fg)

    diff_add_bg = pick([rgb(data, "editor", "diff_add_bg")], mix(bg, "#00ff00", 0.15))
    diff_remove_bg = pick([rgb(data, "editor", "diff_remove_bg")], mix(bg, "#ff0000", 0.15))
    diff_modify_bg = pick([rgb(data, "editor", "diff_modify_bg")], mix(bg, "#ffff00", 0.15))

    keyword = pick([rgb(data, "syntax", "keyword")], fg)
    string = pick([rgb(data, "syntax", "string")], fg)
    comment = pick([rgb(data, "syntax", "comment")], mix(bg, fg, 0.5))
    function = pick([rgb(data, "syntax", "function")], fg)
    type_ = pick([rgb(data, "syntax", "type")], fg)
    variable = pick([rgb(data, "syntax", "variable")], fg)
    var_builtin = pick([rgb(data, "syntax", "variable_builtin")], keyword)
    constant = pick([rgb(data, "syntax", "constant")], fg)
    operator = pick([rgb(data, "syntax", "operator")], fg)

    diag_err = pick([rgb(data, "diagnostic", "error_fg")], "#ff5555")
    diag_warn = pick([rgb(data, "diagnostic", "warning_fg")], "#ffd75f")
    diag_info = pick([rgb(data, "diagnostic", "info_fg")], "#82aaff")
    diag_hint = pick([rgb(data, "diagnostic", "hint_fg")], "#98c379")
    diag_err_bg = pick([rgb(data, "diagnostic", "error_bg")], darken(diag_err, 0.7))

    match_bg = pick([rgb(data, "search", "match_bg")], mix(bg, diag_warn, 0.35))
    match_fg = pick([rgb(data, "search", "match_fg")], fg)
    label_bg = pick([rgb(data, "search", "label_bg")], keyword)
    label_fg = pick([rgb(data, "search", "label_fg")], bg)

    popup_bg = pick([rgb(data, "ui", "popup_bg"), rgb(data, "ui", "menu_bg"),
                     rgb(data, "ui", "prompt_bg")], mix(bg, fg, 0.08))
    popup_fg = pick([rgb(data, "ui", "popup_text_fg"), rgb(data, "ui", "menu_fg")], fg)
    sel_bg = pick([rgb(data, "ui", "popup_selection_bg"),
                   rgb(data, "ui", "menu_active_bg"),
                   rgb(data, "ui", "prompt_selection_bg")], mix(bg, fg, 0.2))
    border = pick([rgb(data, "ui", "popup_border_fg"), rgb(data, "ui", "split_separator_fg"),
                   rgb(data, "ui", "menu_border_fg")], mix(bg, fg, 0.3))
    tab_active_bg = pick([rgb(data, "ui", "tab_active_bg")], mix(bg, fg, 0.15))
    tab_active_fg = pick([rgb(data, "ui", "tab_active_fg")], fg)
    tab_inactive_bg = pick([rgb(data, "ui", "tab_inactive_bg")], mix(bg, fg, 0.06))
    tab_inactive_fg = pick([rgb(data, "ui", "tab_inactive_fg")], inactive_cursor)
    status_bg = pick([rgb(data, "ui", "status_bar_bg")], mix(bg, fg, 0.12))
    status_fg = pick([rgb(data, "ui", "status_bar_fg")], fg)
    inline_bg = pick([rgb(data, "ui", "inline_code_bg")], popup_bg)

    base0 = darken(bg, 0.5)
    base1 = mix(bg, fg, 0.05)
    base2 = mix(bg, fg, 0.10)
    base3 = mix(bg, fg, 0.15)
    base4 = border
    base5 = ws
    base6 = mix(bg, fg, 0.45)
    base7 = inactive_cursor
    base8 = fg

    v = {
        "bg": bg, "bg-alt": popup_bg,
        "base0": base0, "base1": base1, "base2": base2, "base3": base3,
        "base4": base4, "base5": base5, "base6": base6, "base7": base7, "base8": base8,
        "fg": fg, "fg-alt": inactive_cursor, "grey": base6,

        "red": diag_err, "light-red": lighten(diag_err, 0.25),
        "orange": constant, "green": diag_hint, "yellow": diag_warn,
        "blue": variable if variable != fg else diag_info,
        "magenta": var_builtin, "cyan": diag_info, "teal": type_,
        "violet": keyword, "pink": string, "rose": type_, "salmon": string,

        "highlight": keyword, "vertical-bar": base4, "selection": selection,
        "builtin": var_builtin, "comments": comment,
        "doc-comments": mix(comment, fg, 0.25), "constants": constant,
        "functions": function, "keywords": keyword, "methods": function,
        "operators": operator, "type": type_, "strings": string,
        "variables": variable, "numbers": constant,
        "region": selection, "error": diag_err, "warning": diag_warn,
        "success": diag_hint, "vc-modified": diag_warn, "vc-added": diag_hint,
        "vc-deleted": diag_err,

        "modeline-bg": status_bg, "modeline-bg-alt": base1,
        "modeline-fg": status_fg, "modeline-fg-alt": base7,
        "modeline-bg-l": darken(bg, 0.1), "modeline-bg-inactive": base1,
        "modeline-bg-inactive-l": bg,

        "cursor": cursor, "cur-line": cur_line,
        "line-nr": line_nr, "line-nr-bg": line_nr_bg,
        "sel-bg": selection, "bracket-match": bracket_match,
        "match-bg": match_bg, "match-fg": match_fg,
        "label-bg": label_bg, "label-fg": label_fg,
        "popup-bg": popup_bg, "popup-fg": popup_fg, "popup-sel-bg": sel_bg,
        "border": border,
        "tab-active-bg": tab_active_bg, "tab-active-fg": tab_active_fg,
        "tab-inactive-bg": tab_inactive_bg, "tab-inactive-fg": tab_inactive_fg,
        "status-bg": status_bg, "status-fg": status_fg, "inline-bg": inline_bg,
        "err-bg": diag_err_bg,

        "diff-add-bg": diff_add_bg, "diff-remove-bg": diff_remove_bg,
        "diff-modify-bg": diff_modify_bg,
    }

    kw_bold = "bold" in modifier(data, "syntax", "keyword")
    kw_italic = "italic" in modifier(data, "syntax", "keyword")

    v["dark-blue"] = darken(v["blue"], 0.4)
    v["dark-cyan"] = darken(v["cyan"], 0.4)
    v["dark-violet"] = darken(v["violet"], 0.4)
    v["dark-red"] = darken(v["red"], 0.35)
    v["dark-green"] = darken(v["green"], 0.35)
    v["light-green"] = lighten(v["green"], 0.2)
    v["light-blue"] = lighten(v["blue"], 0.2)
    v["light-yellow"] = lighten(v["yellow"], 0.2)

    return v, kw_bold, kw_italic, FRESH_NOTE.format(name=name)


# ------------------------------------------------------------ mini.hues palettes
def parse_mini(path):
    text = open(path).read()
    seg = text[text.find("== 'dark'"):]
    block = seg[seg.find("{") + 1:seg.find("}")]
    return dict(re.findall(r"(\w+)\s*=\s*'(#[0-9a-fA-F]{6})'", block))


def palette_from_mini(name):
    p = parse_mini(os.path.join(MINI, name + ".lua"))
    bg, bg_edge, bg_edge2 = p["bg"], p["bg_edge"], p["bg_edge2"]
    bg_mid, bg_mid2 = p["bg_mid"], p["bg_mid2"]
    fg, fg_mid, fg_mid2 = p["fg"], p["fg_mid"], p["fg_mid2"]
    fg_edge, fg_edge2 = p["fg_edge"], p["fg_edge2"]
    accent, accent_bg = p["accent"], p["accent_bg"]
    red, orange = p["red"], p["orange"]
    yellow, green = p["yellow"], p["green"]
    cyan, azure = p["cyan"], p["azure"]
    blue, purple = p["blue"], p["purple"]

    v = {
        "bg": bg, "bg-alt": bg_edge,
        "base0": bg_edge2, "base1": bg_edge, "base2": bg_mid, "base3": bg_mid2,
        "base4": mix(bg_mid2, fg_mid2, 0.5), "base5": fg_mid2, "base6": fg_mid,
        "base7": fg_edge, "base8": fg_edge2,
        "fg": fg, "fg-alt": fg_mid, "grey": fg_mid,

        "red": red, "light-red": red, "orange": orange, "green": green,
        "teal": cyan, "yellow": yellow, "blue": blue, "magenta": purple,
        "violet": purple, "cyan": cyan, "pink": red, "rose": purple, "salmon": orange,

        "highlight": accent, "vertical-bar": accent, "selection": bg_mid2,
        "builtin": azure, "comments": fg_mid2, "doc-comments": fg_mid2,
        "constants": purple, "functions": azure, "keywords": fg, "methods": azure,
        "operators": fg, "type": fg, "strings": green, "variables": yellow,
        "numbers": purple, "region": bg_mid2, "error": red, "warning": yellow,
        "success": green, "vc-modified": cyan, "vc-added": green, "vc-deleted": red,

        "modeline-bg": accent_bg, "modeline-bg-alt": bg_edge,
        "modeline-fg": fg_mid, "modeline-fg-alt": fg_mid2,
        "modeline-bg-l": bg_edge, "modeline-bg-inactive": bg_edge,
        "modeline-bg-inactive-l": bg,

        "cursor": accent, "cur-line": bg_mid, "line-nr": bg_mid2, "line-nr-bg": bg,
        "sel-bg": bg_mid2, "bracket-match": accent,
        "match-bg": accent, "match-fg": bg,
        "label-bg": yellow, "label-fg": bg,
        "popup-bg": bg_edge, "popup-fg": fg, "popup-sel-bg": bg_mid2,
        "border": accent,
        "tab-active-bg": bg_edge, "tab-active-fg": accent,
        "tab-inactive-bg": bg_edge, "tab-inactive-fg": fg_mid,
        "status-bg": accent_bg, "status-fg": fg_mid, "inline-bg": bg_edge,
        "err-bg": p["red_bg"],

        "diff-add-bg": p["green_bg"], "diff-remove-bg": p["red_bg"],
        "diff-modify-bg": p["cyan_bg"],
    }
    for key, t in (("dark-blue", ("blue", 0.4)), ("dark-cyan", ("cyan", 0.4)),
                   ("dark-violet", ("violet", 0.4)), ("dark-red", ("red", 0.35)),
                   ("dark-green", ("green", 0.35))):
        v[key] = darken(v[t[0]], t[1])
    for key, t in (("light-green", ("green", 0.2)), ("light-blue", ("blue", 0.2)),
                   ("light-yellow", ("yellow", 0.2))):
        v[key] = lighten(v[t[0]], t[1])

    return v, False, False, MINI_NOTE.format(name=name)


# ------------------------------------------------------------------ naysayer
def palette_naysayer():
    bg = "#062329"
    v = {
        "bg": bg, "bg-alt": "#0c272c",
        "base0": darken(bg, 0.35), "base1": "#0c272c", "base2": "#102a2f",
        "base3": "#142d31", "base4": "#223838", "base5": "#334441",
        "base6": "#43504a", "base7": "#9e937c", "base8": "#f0e6d8",
        "fg": "#d1b897", "fg-alt": "#afc6ce", "grey": "#43504a",

        "red": "#c74138", "light-red": "#ff0000", "orange": "#ffaa00",
        "green": "#22b59e", "teal": "#8cde94", "yellow": "#ffaa00",
        "blue": "#afc6ce", "magenta": "#7ad0c6", "violet": "#7ad0c6",
        "cyan": "#7ad0c6", "pink": "#15ed05", "rose": "#8cde94", "salmon": "#22b59e",

        "highlight": "#8cde94", "vertical-bar": "#223838", "selection": mix(bg, "#8cde94", 0.30),
        "builtin": "#8cde94", "comments": "#43504a", "doc-comments": "#5a6b60",
        "constants": "#7ad0c6", "functions": "#d1b897", "keywords": "#ffffff",
        "methods": "#d1b897", "operators": "#8cde94", "type": "#8cde94",
        "strings": "#22b59e", "variables": "#afc6ce", "numbers": "#7ad0c6",
        "region": mix(bg, "#8cde94", 0.30), "error": "#c74138", "warning": "#ffaa00",
        "success": "#22b59e", "vc-modified": "#ffaa00", "vc-added": "#22b59e",
        "vc-deleted": "#c74138",

        "modeline-bg": "#102a2f", "modeline-bg-alt": "#0c272c",
        "modeline-fg": "#d1b897", "modeline-fg-alt": "#9e937c",
        "modeline-bg-l": "#0c272c", "modeline-bg-inactive": "#0c272c",
        "modeline-bg-inactive-l": bg,

        "cursor": "#8cde94", "cur-line": "#0c272c", "line-nr": "#9e937c",
        "line-nr-bg": bg, "sel-bg": mix(bg, "#8cde94", 0.30), "bracket-match": "#8cde94",
        "match-bg": "#8cde94", "match-fg": bg,
        "label-bg": "#8cde94", "label-fg": bg,
        "popup-bg": "#102a2f", "popup-fg": "#d1b897", "popup-sel-bg": "#223838",
        "border": "#223838",
        "tab-active-bg": "#142d31", "tab-active-fg": "#8cde94",
        "tab-inactive-bg": "#0c272c", "tab-inactive-fg": "#7ad0c6",
        "status-bg": "#102a2f", "status-fg": "#d1b897", "inline-bg": "#0c272c",
        "err-bg": "#3a1512",

        "diff-add-bg": mix(bg, "#22b59e", 0.28), "diff-remove-bg": "#3a1512",
        "diff-modify-bg": mix(bg, "#ffaa00", 0.22),
    }
    v["dark-blue"] = darken(v["blue"], 0.4)
    v["dark-cyan"] = darken(v["cyan"], 0.4)
    v["dark-violet"] = darken(v["violet"], 0.4)
    v["dark-red"] = darken(v["red"], 0.35)
    v["dark-green"] = darken(v["green"], 0.35)
    v["light-green"] = lighten(v["green"], 0.2)
    v["light-blue"] = lighten(v["blue"], 0.2)
    v["light-yellow"] = lighten(v["yellow"], 0.2)

    return v, False, True, NAYSAYER_NOTE


# ------------------------------------------------------------------ vscode
def _vsc_resolve(color, bg):
    if not color:
        return None
    h = color.lstrip("#")
    try:
        if len(h) == 8:
            r, g, b, a = (int(h[i:i + 2], 16) for i in range(0, 8, 2))
            if a >= 254:
                return "#%02x%02x%02x" % (r, g, b)
            a /= 255.0
            br, bgc, bb = to_rgb(bg)
            return hexs([r * a + br * (1 - a), g * a + bgc * (1 - a), b * a + bb * (1 - a)])
        if len(h) == 6:
            return "#" + h.lower()
        if len(h) == 3:
            return "#" + "".join(c * 2 for c in h).lower()
    except ValueError:
        return None
    return None


def _vsc_find(tokens, targets):
    for target in targets:
        for scopes, fg, style in tokens:
            if fg and target in scopes:
                return fg.lower(), style
    for target in targets:
        for scopes, fg, style in tokens:
            if not fg:
                continue
            if any(s.startswith(target + ".") for s in scopes):
                return fg.lower(), style
    return None, ""


def palette_from_vscode(name):
    d = json.load(open(os.path.join(VSC, name + "-color-theme.json")))
    c = d.get("colors", {})
    tokens = []
    for t in d.get("tokenColors", []):
        scope = t.get("scope")
        if isinstance(scope, str):
            scope = [scope]
        settings = t.get("settings", {})
        tokens.append((scope or [], settings.get("foreground"),
                       settings.get("fontStyle", "")))

    bg = _vsc_resolve(c.get("editor.background"), "#000000") or "#000000"
    bg0 = bg
    fg = _vsc_resolve(c.get("editor.foreground"), "#ffffff") or "#ffffff"

    def col(*keys, default=None):
        for k in keys:
            v = _vsc_resolve(c.get(k), bg0 if default is None else default)
            if v:
                return v
        return default

    selection = col("editor.selectionBackground", default=mix(bg, fg, 0.25))
    cur_line = col("editor.lineHighlightBackground", default=mix(bg, fg, 0.08))
    line_nr = col("editorLineNumber.foreground", default=mix(bg, fg, 0.35))
    cursor = col("editorCursor.foreground", default=fg)
    ws = col("editorWhitespace.foreground", default=mix(bg, fg, 0.3))
    widget = col("editorWidget.background", "editorSuggestWidget.background",
                 "menu.background", default=mix(bg, fg, 0.08))
    panel = col("panel.background", "sideBar.background", default=mix(bg, fg, 0.06))
    border = col("panel.border", "editorGroup.border", "focusBorder", default=mix(bg, fg, 0.3))
    status_bg = col("statusBar.background", default=panel)
    status_fg = col("statusBar.foreground", default=fg)
    tab_ab = col("tab.activeBackground", default=widget)
    tab_af = col("tab.activeForeground", default=fg)
    tab_ib = col("tab.inactiveBackground", default=panel)
    tab_if = col("tab.inactiveForeground", default=mix(bg, fg, 0.6))
    err = col("editorError.foreground", default="#ff5555")
    warn = col("editorWarning.foreground", default="#ffd75f")
    info = col("editorInfo.foreground", default="#82aaff")
    find = col("editor.findMatchBackground", default=mix(bg, fg, 0.3))
    find_hl = col("editor.findMatchHighlightBackground", default=mix(bg, fg, 0.2))
    list_sel = col("list.activeSelectionBackground", "list.hoverBackground",
                   default=selection)

    def syn(*targets):
        fg_, _ = _vsc_find(tokens, list(targets))
        return fg_ or fg

    comment = syn("comment.block.documentation", "comment")
    string = syn("string", "string.quoted", "string.template")
    number = syn("constant.numeric", "constant.numeric.integer")
    constant = syn("constant.language", "constant", "support.constant")
    keyword, kw_style = _vsc_find(tokens, ["keyword", "storage", "storage.type"])
    keyword = keyword or fg
    operator = syn("keyword.operator", "punctuation.definition.operator")
    variable = syn("variable.parameter", "variable.other", "variable")
    var_builtin = syn("variable.language", "variable.special", "variable.other")
    function = syn("entity.name.function", "support.function", "meta.function-call")
    type_, _type_style = _vsc_find(tokens, ["entity.name.type", "support.type",
                                            "entity.name.class", "meta.type"])
    type_ = type_ or fg
    preproc = syn("meta.preprocessor", "entity.name.function.macro",
                  "entity.name.function.preprocessor")

    kw_bold, kw_italic = "bold" in kw_style, "italic" in kw_style

    if sum(to_rgb(bg)) / 765.0 > 0.5:  # light palette
        base = {
            "base0": lighten(bg, 0.5), "base1": lighten(bg, 0.3),
            "base2": lighten(bg, 0.15), "base3": mix(bg, fg, 0.12),
            "base4": border, "base5": mix(bg, fg, 0.35),
            "base6": mix(bg, fg, 0.5), "base7": mix(bg, fg, 0.7), "base8": fg,
        }
    else:
        base = {
            "base0": darken(panel, 0.35), "base1": panel, "base2": widget,
            "base3": mix(bg, fg, 0.12), "base4": border, "base5": ws,
            "base6": line_nr, "base7": mix(bg, fg, 0.6), "base8": fg,
        }

    v = {
        **base,
        "bg": bg, "bg-alt": widget,
        "fg": fg, "fg-alt": mix(bg, fg, 0.6), "grey": line_nr,
        "red": err, "light-red": lighten(err, 0.25), "orange": warn,
        "green": function, "teal": type_, "yellow": warn, "blue": info,
        "magenta": preproc, "violet": preproc, "cyan": info, "pink": string,
        "rose": type_, "salmon": string,

        "highlight": cursor, "vertical-bar": border, "selection": selection,
        "builtin": var_builtin, "comments": comment, "doc-comments": comment,
        "constants": constant, "functions": function, "keywords": keyword,
        "methods": function, "operators": operator, "type": type_,
        "strings": string, "variables": variable, "numbers": number,
        "region": selection, "error": err, "warning": warn, "success": function,
        "vc-modified": warn, "vc-added": function, "vc-deleted": err,

        "modeline-bg": status_bg, "modeline-bg-alt": panel,
        "modeline-fg": status_fg, "modeline-fg-alt": mix(bg, fg, 0.6),
        "modeline-bg-l": panel, "modeline-bg-inactive": panel,
        "modeline-bg-inactive-l": bg,

        "cursor": cursor, "cur-line": cur_line, "line-nr": line_nr,
        "line-nr-bg": bg, "sel-bg": list_sel, "bracket-match": cursor,
        "match-bg": find_hl, "match-fg": fg, "label-bg": find, "label-fg": bg,
        "popup-bg": widget, "popup-fg": fg, "popup-sel-bg": list_sel,
        "border": border,
        "tab-active-bg": tab_ab, "tab-active-fg": tab_af,
        "tab-inactive-bg": tab_ib, "tab-inactive-fg": tab_if,
        "status-bg": status_bg, "status-fg": status_fg, "inline-bg": widget,
        "err-bg": mix(bg, err, 0.30),

        "diff-add-bg": mix(bg, function, 0.30), "diff-remove-bg": mix(bg, err, 0.30),
        "diff-modify-bg": mix(bg, warn, 0.30),

        "dark-blue": darken(info, 0.4), "dark-cyan": darken(info, 0.4),
        "dark-violet": darken(preproc, 0.4), "dark-red": darken(err, 0.35),
        "dark-green": darken(function, 0.35),
        "light-green": lighten(function, 0.2), "light-blue": lighten(info, 0.2),
        "light-yellow": lighten(warn, 0.2),
    }

    return v, kw_bold, kw_italic, VSC_NOTE.format(name=name)


# ----------------------------------------------------------------- rendering
# (kakoune face, palette key, attributes)
FACE_MAP = [
    # --- Code ---
    ("value",          "numbers",         ""),
    ("type",           "type",            ""),
    ("variable",       "variables",       ""),
    ("identifier",     "variables",       ""),
    ("module",         "teal",            ""),
    ("function",       "functions",       ""),
    ("method",         "methods",         ""),
    ("string",         "strings",         ""),
    ("keyword",        "keywords",        ""),
    ("operator",       "operators",       ""),
    ("attribute",      "cyan",            ""),
    ("comment",        "comments",        "i"),
    ("documentation",  "doc-comments",    ""),
    ("meta",           "magenta",         ""),
    ("builtin",        "builtin",         "b"),
    ("constant",       "constants",       ""),
    ("error",          "error",           ""),
    # --- Markup ---
    ("title",          "highlight",       "b"),
    ("header",         "cyan",            ""),
    ("mono",           "fg-alt",          ""),
    ("block",          "violet",          ""),
    ("link",           "highlight",       "u"),
    ("bullet",         "warning",         ""),
    ("list",           "fg",              ""),
    # --- UI: edits / selections ---
    ("Default",            "fg,bg",                  ""),
    ("PrimarySelection",   "bg,selection",           ""),
    ("SecondarySelection", "fg,base2",               ""),
    ("PrimaryCursor",      "bg,cursor",              "fg"),
    ("SecondaryCursor",    "bg,fg-alt",              "fg"),
    ("PrimaryCursorEol",   "bg,cursor",              "fg"),
    ("SecondaryCursorEol", "bg,line-nr",             "fg"),
    ("MatchingChar",       "bracket-match",          "b"),
    # --- UI: status / menus ---
    ("MenuForeground",     "bg,highlight",           ""),
    ("MenuBackground",     "fg,popup-bg",            ""),
    ("MenuInfo",           "highlight",              ""),
    ("Information",        "bg,yellow",              ""),
    ("InlineInformation",  "fg,popup-bg",            ""),
    ("Error",              "bg,error",               ""),
    ("DiagnosticError",    "error",                  ""),
    ("DiagnosticWarning",  "warning",                ""),
    ("StatusLine",         "modeline-fg,modeline-bg", ""),
    ("StatusLineMode",     "modeline-fg",            "b"),
    ("StatusLineInfo",     "modeline-fg",            ""),
    ("StatusLineValue",    "modeline-fg",            "b"),
    ("StatusCursor",       "bg,cursor",              ""),
    ("Prompt",             "highlight",              ""),
    ("BufferPadding",      "base6,bg",               ""),
    # --- UI: highlighters ---
    ("LineNumbers",        "line-nr,line-nr-bg",     ""),
    ("LineNumberCursor",   "highlight,line-nr-bg",   "b"),
    ("LineNumbersWrapped", "line-nr,line-nr-bg",     "i"),
    ("Whitespace",         "base5",                  "f"),
    ("WrapMarker",         "base5",                  "f"),
    ("Search",             "match-fg,match-bg",      ""),
    # --- Diff / VCS ---
    ("DiffAdd",            "success,diff-add-bg",    ""),
    ("DiffRm",             "error,diff-remove-bg",   ""),
    ("DiffMeta",           "highlight,diff-modify-bg", ""),
    ("MercurialCommitComment", "comments",           ""),
]


def face_value(v, spec, kw_bold=False, kw_italic=False):
    colors = []
    for token in spec.split(","):
        # tokens are palette keys, or raw hex/default
        if token in v:
            colors.append(kak(v[token]))
        else:
            colors.append(token)
    return ",".join(colors)


def render(name, v, kw_bold, kw_italic, note):
    if kw_bold:
        kw_attr = "b"
    else:
        kw_attr = ""
    if kw_italic:
        kw_attr += "i"

    out = []
    out.append(f"# {name} theme for Kakoune")
    out.append("#")
    out.append(f"# {note}")
    out.append("#")
    out.append("# Generated by scripts/gen_themes.py -- do not edit by hand.")
    out.append("")

    def emit(header, entries):
        out.append(f"# {header}")
        width = max(len(f) for f, _, _ in entries)
        for face, key, attr in entries:
            if face == "keyword" and kw_attr:
                attr = kw_attr + attr
            val = face_value(v, key)
            if attr:
                val += "+" + attr
            out.append(f"face global {face.ljust(width)} {val}")
        out.append("")

    sections = [
        ("Code", FACE_MAP[0:17]),
        ("Markup", FACE_MAP[17:24]),
        ("UI", FACE_MAP[24:]),
    ]
    for header, entries in sections:
        emit(header, entries)

    out.append("")
    return "\n".join(out)


FRESH_NOTE = ("Ported from the fresh-editor palette (palettes/fresh/{name}.json), "
              "shared across the justaperlhacker editor themes.")
MINI_NOTE = ("Ported from Neovim's mini.hues palette (palettes/mini/{name}.lua).")
NAYSAYER_NOTE = ("Ported from p0209p/naysayer.vim (Neovim) and the "
                 "justaperlhacker VS Code \"naysayer\" theme.")
VSC_NOTE = ("Ported from the justaperlhacker VS Code color theme "
            "(palettes/vscode/{name}-color-theme.json).")


def write_theme(name, v, kw_bold, kw_italic, note):
    dest = os.path.join(OUT, f"{name}.kak")
    with open(dest, "w") as fh:
        fh.write(render(name, v, kw_bold, kw_italic, note))
    print("wrote", os.path.relpath(dest, ROOT))
    return name


def main():
    os.makedirs(OUT, exist_ok=True)
    produced = {}
    names = []

    def add(name, result):
        if name in produced:
            return
        produced[name] = True
        names.append(write_theme(name, *result))

    # 1) fresh-editor palettes
    for fn in sorted(os.listdir(FRESH)):
        if not fn.endswith(".json"):
            continue
        name = fn[:-len(".json")]
        with open(os.path.join(FRESH, fn)) as fh:
            data = json.load(fh)
        add(name, palette_from_fresh(name, data))

    # 2) mini.hues "four seasons" (skip any already produced from fresh)
    for name in MINI_THEMES:
        if os.path.exists(os.path.join(MINI, name + ".lua")):
            add(name, palette_from_mini(name))

    # 3) naysayer
    add("naysayer", palette_naysayer())

    # 4) VS Code variants (only those not already produced)
    for name in VSC_THEMES:
        if os.path.exists(os.path.join(VSC, name + "-color-theme.json")):
            add(name, palette_from_vscode(name))

    print("total:", len(names))


if __name__ == "__main__":
    main()
