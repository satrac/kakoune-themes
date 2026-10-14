# justaperlhacker Kakoune Themes

A collection of low-saturation color schemes for the
[Kakoune](https://kakoune.org) editor, ported from the matching
[Fresh](https://github.com/sinelaw/fresh), Neovim, VS Code and Doom Emacs
themes so every editor in the family shares one palette.

All themes live in [`colors/`](colors/) and are plain Kakoune `face`
definitions, so they work with any terminal that supports truecolor.

## Included themes

Light/dark pairs:

- **Black Metal**
- **Black Metal Gorgoroth**
- **Miniautumn**
- **Minispring**
- **Minisummer**
- **Miniwinter**

Dark themes:

- **Batman**, **Chocolatier**, **Doom Rouge**, **Everforest**, **Fleury**,
  **Gruvbox**, **Kanso**, **Kimbie Dark**, **Kimbox**, **Kraihnight**,
  **Monochrome** (plus **Amber**, **Chroma**, **Green**), **Naysayer**,
  **Nightfly**, **Rose Pine**, **Tokyo Night**, **Vague**, **VSCode Red**

## Install

Copy or symlink the `colors/` directory into your Kakoune config:

```sh
make install              # -> $XDG_CONFIG_HOME/kak/colors (default ~/.config/kak)
# or
mkdir -p ~/.config/kak
ln -s "$PWD/colors" ~/.config/kak/colors
```

Then select a theme from inside Kakoune:

```
:colorscheme gruvbox
```

To make it your default, add it to `~/.config/kak/kakrc`:

```kak
colorscheme gruvbox
```

If you use a plugin manager that supports Kakoune (e.g. `plug.kak`,
[`kakoune-plug`](https://github.com/andreyorst/plug.kak)), point it at this
repository and it will pick up `colors/` automatically.

## Development

The themes are generated from the source palettes in [`palettes/`](palettes/)
(fresh-editor JSON, Neovim mini.hues Lua, and VS Code color-theme JSON).

```sh
make generate   # regenerate colors/*.kak
make validate   # source every theme with kak to catch syntax errors
make list       # list available themes
```

`make generate` requires Python 3 (standard library only). `make validate`
requires a `kak` binary (override with `KAK=/path/to/kak`).

## Adding a theme

1. Drop a fresh-editor palette into `palettes/fresh/<name>.json`, **or** a
   VS Code color-theme JSON into `palettes/vscode/<name>-color-theme.json`
   (register it in `VSC_THEMES` in `scripts/gen_themes.py`).
2. Run `make generate`.

The renderer maps the normalized palette onto Kakoune's code, markup, UI and
diff faces; the palette normalization is shared with the Doom Emacs generator
so the colors stay identical across editors.

## License

[MIT](LICENSE) © 2026 justaperlhacker
