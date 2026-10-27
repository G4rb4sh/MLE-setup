# brand.toml format

A brand is a folder with a `brand.toml` and its assets: logos, an optional
`template.pptx` and an optional `reference.docx`. Decks and documents take
every color, font, logo and company name from it. The scripts never hardcode
them. The code is in `scripts/brand.py`.

## Where brands are searched

`--brand NAME` or `Deck("NAME")` uses the first `NAME/brand.toml` it finds in:

1. `./brands/NAME` (relative to the working directory, or `Deck(..., cwd=...)`)
2. each folder in `MLE_BRANDS_PATH`, separated with `:` on macOS and Linux
3. `~/.mle-setup/brands/NAME`, which is the private `MLE-setup-personal/brands`
   repo, linked
4. `$OD/brands/NAME`, which holds only `neutral`

A path such as `./clients/acme`, `~/brands/acme` or `.../acme/brand.toml` also
works. Any value containing `/` is treated as a path. Brands with client
identity never go in the plugin (see SKILL.md).

## Keys

```toml
name = "acme"                    # defaults to the folder name
description = "Acme corporate"   # free text
style = "modern"                 # modern | outlined | dark: the preset filled in under your values
draft = true                     # set by brand_from_pptx.py; a draft refuses to load until --confirm

[colors]                         # 6-digit hex, with or without "#"; any token you omit comes from the style preset
background = "F4F7FB"            # slide background (content_bg points here by default)
surface = "FFFFFF"               # cards, nodes, table cells
primary = "0F2B5B"               # title/section/final backgrounds, titles, stat panels
on_primary = "FFFFFF"            # text on primary and accent fills
accent = "2870CF"                # kickers, card strips, node borders, Word headings
highlight = "50E6FF"             # bullet markers, rules, big numbers
text = "2D3748"                  # body text
muted = "5A6B85"                 # captions, footers, secondary text
card_border = "E2E8F0"           # card and container borders
done = "3BBBA6"                  # "done" state (nodes, chips)
planned = "FF7043"               # "planned" state (dashed nodes)

[components]                     # any key you omit comes from the style preset
card = "filled"                  # filled | outlined | dark
radius = 0.06                    # corner radius of cards and nodes, as a fraction of the short side (0-0.5)
accent_strip = "top"             # top | left | "none"
content_bg = "background"        # color token for content-slide backgrounds; drawn text picks its contrast against it
node_shape = "rounded"           # rounded | rect

[fonts]
body = "Segoe UI"                # required
heading = "Segoe UI Semibold"    # defaults to body
mono = "Consolas"                # defaults to body

[grid]                           # inches; d.col() uses these values
margin = 0.6
columns = 12
gutter = 0.2

[logos]                          # name = path relative to the brand folder; use any names
light = "logo-light.png"         # Word puts it in the page header
dark = "logo-dark.png"           # Word puts it on the cover band (dark background)

[deck]
footer = "Acme · Confidencial"   # drawn on content slides; Deck(brand, footer="...") overrides it
template = "template.pptx"       # optional: decks start from this file (its slides removed)

[deck.layouts]                   # only with a template: slide factory role = layout name in the template
title = "Title Slide"
section = "Section Header"
content = "Title Only"
final = "Closing"

[docx]
reference = "reference.docx"     # optional pandoc reference doc (styles); the default is built from the brand
company = "Acme"                 # cover "by" line and document author when the front matter has none
cover_band = "primary"           # a token or hex; default primary
heading_color = "accent"         # default accent
code_bg = "F2F2F2"               # default F2F2F2
note_bg = "background"           # default background
rule = "card_border"             # default card_border
```

Validation:
- An unknown key in `[colors]`, `[components]` or `[grid]` raises `BrandError`
  and lists the valid keys.
- So do a bad hex, an unknown style, a missing `fonts.body`, and a missing
  logo, template or reference file.
- Logos are never placed on slides automatically. Use
  `d.image(s, d.brand.logos["light"], ...)` (see `deck-api.md`).

## Style presets

`style` picks the defaults that your values override. Each preset fills in
the colors you leave out and the whole `[components]` table.

| Style | Look | card | accent_strip | node_shape | radius |
| --- | --- | --- | --- | --- | --- |
| `modern` | light grey slides, white filled cards with a top strip, navy and cyan | filled | top | rounded | 0.06 |
| `outlined` | white slides, light grey cards outlined in the accent | outlined | left | rect | 0.08 |
| `dark` | dark navy slides and cards, cyan and teal accents | dark | none | rounded | 0.10 |

In `dark`, the stat_row, maprow, numbered_grid, code_block and compare panels
use `primary`. That color is close to the background, so they barely stand
out. Set a lighter `primary` if they need to pop.

## Making a new look without code

- **Change a few tokens** in an existing brand. For example, set
  `accent = "E91E63"` and `[components] card = "outlined"`.
- **Copy a brand folder** (`neutral` is a clean starting point) and change
  `name` and the values.
- **Create one from scratch**: `uv run "$OD/scripts/new_brand.py" NAME --primary HEX --accent HEX --font NAME [--highlight HEX] [--heading-font NAME] [--logo PATH] [--style modern|outlined|dark] [--out DIR] [--samples]`.
  It writes `brand.toml` (plus `logo.<ext>` with `[logos] light` when `--logo`
  is given) to `~/.mle-setup/brands/NAME` by default. It refuses to overwrite
  an existing folder.
- **Create one from a .pptx**: `brand_from_pptx.py` (see SKILL.md). It writes
  a draft with `style = "outlined"`, theme colors and fonts, `template.pptx`
  and guessed `[deck.layouts]`.

## Template brands

When `[deck] template` is set:
- `Deck` opens the template in memory and removes its slides. The file on
  disk is never written.
- The slide size comes from the template.
- `title_slide`, `section_slide`, `content_slide` and `final_slide` use the
  mapped layouts. A role without a mapping is drawn as usual.
- `blank_slide()` uses the template's "Blank" layout, or else the layout with
  the fewest placeholders, so the master's background shows through.
- Components and primitives are always drawn on top.

Set `[components] content_bg` and the colors to match the template's real
background. Drawn text picks its contrast against `content_bg`, not against
the master. See `gotchas.md` for the other limits of template brands.
