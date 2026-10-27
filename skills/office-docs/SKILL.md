---
name: office-docs
description: >
  Build editable, branded PowerPoint decks (.pptx) and Word documents (.docx),
  render them to PNG/PDF to check them, and add brands from a client .pptx or
  from scratch. Use when the user says "armá una ppt de status", "deck del
  proyecto", "presentación para el cliente", "pasá el plan a Word", "exportá a
  docx", "documentación de entrega en Word", "sumá esta ppt como plantilla",
  "nueva plantilla/marca". Not for: spreadsheets, editing a client's existing
  deck, writing the content (status-update/handoff).
---

# office-docs: branded decks and Word documents

A deck is a short Python script that draws native, editable shapes with
`Deck`; a Word document is Markdown converted with pandoc. Colors, fonts,
logos and templates come from a **brand** folder, so the same script changes
look by changing `--brand`.

Decks have three layers, and you can use any of them on any slide:
1. **Tokens**: brand colors (`"accent"`, `"primary"`...), fonts, and a grid.
   Any hex (`"E91E63"`) also works wherever a token is accepted.
2. **Primitives**: `rect`, `oval`, `line`, `arrow`, `text` (mixed runs),
   `bullets`, `chip`, `image`, `icon`, `scrim`, `gradient`, `table`, each at a
   free position in inches.
3. **Components**: title/section/content/final slides, cards, stats, compare,
   timeline, chain, diagram nodes and more, all drawn with the primitives.

Components are shortcuts, not limits. If the slide you picture is not a
component, compose it from primitives: a diagram, a dashboard, a cover with a
photo and a scrim. `references/deck-api.md` has every signature and three
full free-composition slides to copy from.

## Paths and commands

`OD` is this skill's folder (the one that contains this SKILL.md). Every script
runs with `uv run` (PEP 723 headers install python-pptx, python-docx and
pymupdf). If pypi.org is blocked, see `references/gotchas.md`.

| Task | Command |
| --- | --- |
| Build a deck and render it | `uv run "$OD/scripts/render.py" out.pptx --build build_deck.py` |
| Layout check only | `uv run "$OD/scripts/deck.py" check out.pptx` |
| Markdown to Word | `uv run "$OD/scripts/md2docx.py" plan.md --brand NAME [-o plan.docx] [--no-word]` |
| Render a file | `uv run "$OD/scripts/render.py" FILE [--dpi 150] [--pdf-only] [--out DIR]` |
| New brand from values | `uv run "$OD/scripts/new_brand.py" NAME --primary HEX --accent HEX --font NAME [--highlight HEX] [--heading-font NAME] [--logo PATH] [--style modern\|outlined\|dark] [--out DIR] [--samples]` |
| Draft brand from a .pptx | `uv run "$OD/scripts/brand_from_pptx.py" SRC.pptx NAME [--out DIR] [--no-samples]` |
| Confirm a reviewed draft | `uv run "$OD/scripts/brand_from_pptx.py" --confirm DIR/NAME` |

`render.py --build` runs the script with its folder as the working directory
and `$OD/scripts` importable, then exports FILE to `FILE.pdf` and PNGs in
`FILE-render/01.png`, `02.png`... Run it from the script's folder. Do not
name the script `deck.py` or `brand.py`, because it would shadow the library.

## Process

1. **Pick the brand.** `--brand NAME` is searched in `./brands/NAME`, then in
   each folder of `MLE_BRANDS_PATH` (colon-separated), then in
   `~/.mle-setup/brands/NAME`, then in `$OD/brands/NAME` (only `neutral` ships
   with the plugin). List what exists with
   `ls ./brands ~/.mle-setup/brands "$OD/brands" 2>/dev/null`. If more than
   one brand fits (client vs. own brand) or none fits, ask.
2. **Write the content first.** Content comes from the user, the repo, or
   the status-update / handoff skills; this skill formats it. For a deck,
   write one line per slide (the message, then what shows it) and keep titles
   under ~55 characters. For a document, write the Markdown with front matter.
3. **Compose.** Write `build_deck.py` in the user's project (not in the
   plugin):
   ```python
   from deck import Deck

   d = Deck("neutral")                       # brand name or folder
   d.title_slide("Sprint 6", "Estado del proyecto", "Revisión con el cliente")
   s, top = d.content_slide("Avance", "Lo que cambió esta semana")
   d.cards_row(s, top, [{"title": "Datos", "lines": ["Ingesta diaria", "Sin nulos"]},
                        {"title": "Modelo", "lines": ["MAPE 8,4 %"], "accent": "done"}])
   s = d.blank_slide()                       # a slide composed freely from primitives
   d.text(s, 0.6, 0.6, 8, 0.8, "Cualquier slide que imagines", size=30, color="primary", bold=True)
   d.final_slide("Gracias", "Preguntas")
   d.save("status.pptx")
   ```
   Use components where they fit and primitives for everything else. Mix the
   two on one slide when it helps: `content_slide` returns the slide and the
   body top, so you can draw anything below the header.
4. **Build and render:** `uv run "$OD/scripts/render.py" status.pptx --build build_deck.py`.
5. **Read the layout check.** `save()` prints lines like
   `layout check: slide 3: overflow TextBox 7 — text needs ~1.20 in, box fits 0.80 in`
   for off-slide shapes, overflowing text, crossing text boxes, and titles over
   55 characters. It is advisory and heuristic; see `references/gotchas.md`.
6. **Look at every PNG** in `status-render/` and fix what you see: overflow,
   overlaps, empty areas, misaligned edges, low contrast, text too small to read
   from a meeting room. Then repeat steps 4–6. The check does not replace looking
   at the slides.
7. **Deliver** the .pptx (it stays editable in PowerPoint). Add the PDF if the
   user asks for it (it sits next to the deck; `--pdf-only` skips the PNGs).
   Do not deliver the build script or the render folder unless asked.

For Word: write `plan.md` with an optional front-matter block. The keys are
`title`, `subtitle`, `client`, `project`, `author`, `version`, `date`, `lang`,
`toc_depth`, `page_break_on_h1` and `shift_headings`. Run `md2docx.py`, then
`render.py plan.docx` and look at the pages. The output has a cover, a table of
contents, a header and footer, styled tables and code, and Mermaid diagrams as
images. Links to other `.md` files become italic titles. pandoc is required
(`brew install pandoc`).

## A new style or look, without code changes

- **Another style preset**: set `style = "modern" | "outlined" | "dark"` in the
  brand. Card, strip, node and background defaults change together.
- **Override tokens**: in `brand.toml`, set any `[colors]` token and any
  `[components]` key (`card`, `radius`, `accent_strip`, `content_bg`,
  `node_shape`), plus `[fonts]` and `[grid]`. See `references/brand-format.md`.
- **A new brand**: create it with `new_brand.py` from a few values, or with
  `brand_from_pptx.py` from a deck someone hands you (see below).
- **One-off look**: compose the slide from primitives with any hex colors, a
  `gradient` or `scrim` over a photo, chips, and custom shapes. Use
  `Deck(brand, footer="...")` to override the footer of one deck.

## Adding a brand

**Never put client data in a brand folder.** A brand holds only colors, fonts,
logos and layouts. It never holds project names, people, numbers, sample text
or client documents. Real brands (Microsoft, clients, Marvik) go in the
private `MLE-setup-personal/brands/`, which is linked as `~/.mle-setup/brands`,
or in a folder listed in `MLE_BRANDS_PATH`. They never go in this plugin.

**From scratch.** Ask the user for primary, accent, body font and, optionally,
highlight, heading font, logo and style. Then run:
`uv run "$OD/scripts/new_brand.py" acme --primary 0F2B5B --accent 2870CF --font "Segoe UI" --samples`.
The brand goes to `~/.mle-setup/brands/acme` unless you pass `--out DIR`. The
samples (`./acme-samples/acme-sample.pptx` and `.docx`) go to the current
folder. Render both, show them to the user, adjust `brand.toml` until they
approve, then delete the samples folder.

**From a .pptx** (a corporate or client template):
1. Run `uv run "$OD/scripts/brand_from_pptx.py" template.pptx acme`. It
   writes a **draft** brand: the template without slides, notes, comments or
   authors, the theme colors and fonts, and guessed layout roles. It also
   prints a report. A draft brand refuses to load.
2. Show the user the whole report: every text found in masters and layouts,
   every image copied to `acme/assets-review/`, and the sample PNGs in
   `acme/assets-review/samples/`. Also say whether a sensitivity label was
   kept. Point out anything that looks client-specific. Tags, chart or
   SmartArt text, and alt text on masters are not reported, so open the
   template's Slide Master and check them by hand.
3. **Wait for the user's explicit confirmation** that nothing client-specific
   remains. If something does, remove it from `acme/template.pptx` in
   PowerPoint (View → Slide Master), or drop the brand and start over.
4. Only then run `uv run "$OD/scripts/brand_from_pptx.py" --confirm ~/.mle-setup/brands/acme`.
   Review `[deck.layouts]` (the roles `title`, `section`, `content`, `final`)
   and set `[colors] content_bg` and the colors to match the template's
   background (see `references/gotchas.md`). `--confirm` only removes the
   draft flag; delete `acme/assets-review/` once the brand is approved.

## References

- `references/deck-api.md`: every `Deck` method with an example, how to compose
  freely, and three full slides built only from primitives (an architecture
  diagram, a KPI dashboard, a narrative with an image).
- `references/brand-format.md`: every `brand.toml` key, the presets, and the
  search path.
- `references/gotchas.md`: known limits and fixes (webp, long titles,
  templates, render on macOS, Word TOC, Mermaid, proxy, GIF, QR).
