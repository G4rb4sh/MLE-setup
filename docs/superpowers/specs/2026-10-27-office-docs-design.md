# office-docs: decks and Word documents with swappable brands

Date: 2026-10-27. Status: draft for approval.

## Intent

Nicolás regularly produces two kinds of documents:

- **Decks (.pptx)** for project status and project showcases (sprint readouts,
  client presentations), and sometimes class material.
- **Word documents (.docx)** for production plans and technical documentation
  handed to clients.

He already has proven tooling, written inside two projects:

- `~/Documents/Microsoft/clases/mayo/ppt_lib.py` (~500 lines): a python-pptx
  helper library (title/section/content/final slides, cards, stats, compare,
  timeline, chain diagram, map rows, numbered grid, code block, images with
  contain-fit, speaker notes). Six decks use it. Palette and fonts are hardcoded.
- `~/Documents/Microsoft/clases/mayo/render_deck.py`: optional build, then
  pptx -> PDF via PowerPoint (osascript, closing open presentations first so the
  disk version is exported) -> PNG via PyMuPDF, so the agent can look at slides.
- `~/Documents/Microsoft/clases/sprint_readout/create_clinicas_template_ppt.py`:
  builds slides on top of someone else's template (`newppt.pptx`): deletes its
  slides and uses its named layouts. Its own look: grey cards with blue
  border, accent1 strips, Fluent icons, theme font (Aptos).
- `~/Documents/Microsoft/clases/ppts_eli/create_ceibal_ppt.py`: a dark look
  (background 1E2438, cyan/teal/orange accents) drawn from free primitives:
  rect, rounded rect, oval, translucent scrim, gradient scrim, arrows, rich
  text runs, chips, diagram nodes with a done/planned state (dashed border),
  containers, legends, header/footer. The user does not need this deck kept;
  its primitives and diagram pieces are worth reusing.
- `~/Documents/Microsoft/ai4g/ute/docs/exportar_docx.py` (~690 lines): Markdown
  -> .docx in the Microsoft *Delivery Guide* look: generated pandoc reference
  doc (styles), Mermaid blocks rendered to PNG (LR flipped to TB), cover page
  with color band and logo, styled tables, header/footer with title, version and
  page, TOC completed by Word via osascript (or "update fields on open"),
  OOXML property ordering fix. Client, project, palette and document list are
  hardcoded.
- Lessons in `~/Documents/Microsoft/clases/CLAUDE.md` (python-pptx cannot read
  webp; titles over ~55 chars wrap; export from a copy or after closing
  PowerPoint; corporate proxy breaks pip SSL; QR with `segno`; GIF compression
  with ffmpeg two-pass palette).

The goal is to turn that into one reusable kit where the **brand** (colors,
fonts, logos, template) is swappable and new brands are easy to add, either
from a .pptx someone hands him or from scratch. Brands change and grow over
time (Microsoft/AI4G, Marvik, future clients).

## Goals

1. One skill, `office-docs`, that an agent uses to create a deck or a Word
   document for a given brand and verifies the result visually.
2. Deck library generalized from `ppt_lib`, driven by a brand. **As dynamic
   as possible** (user requirement): the agent or a person must be able to
   build whatever slide they imagine, in different styles and shapes, without
   being limited to a fixed set of components.
3. Output stays **editable in PowerPoint** by Nicolás and coworkers (user
   decision): native shapes and text, no slides made of images.
4. Markdown -> .docx exporter generalized from `exportar_docx.py`, driven by a
   brand plus per-document front-matter.
5. Render to PDF/PNG for verification (and PDF as a deliverable).
6. Add a brand **from a given .pptx** (extract theme colors, fonts, layouts,
   keep a sanitized template) or **create a new one** (ask colors, fonts, logo).
7. Brands can be shared with coworkers by copying a folder.

## Non-goals

- Excel generation (no current use case; add when one appears).
- Editing arbitrary existing client decks slide by slide.
- Migrating the existing `clases` and `ute` projects to the kit (they keep
  working as they are; migration is a later, separate request).
- Windows rendering (PowerPoint COM). Building works anywhere; render is
  macOS-first with LibreOffice as fallback when installed.
- Copying or deriving from Anthropic's `docx/pptx/xlsx/pdf` skills (proprietary
  license; in Claude Code they can be installed alongside, not copied).
- Keyword-based skill routing (deferred).

## Anti-goals (failure even if it works)

- **Client data inside a brand.** A brand contains only visual identity:
  colors, fonts, logos, layouts. No project names, people, numbers, sample
  text, or client documents. User requirement: "nunca dejar datos de clientes
  en las plantillas".
- Real brands (Microsoft logos/templates, Marvik, clients) in the public repo.
- The same code in two repos (it would drift).
- Heavy mandatory dependencies when the machine already has Office.

## Where things live (user decision)

- **Public `MLE-setup`**: the generic code and skill, plus one neutral example
  brand (no third-party logos). Path: `skills/office-docs/`.
- **Private `MLE-setup-personal`**: the real brands, `brands/<name>/`,
  including everything Microsoft (logos, templates). User: "los de microsoft y
  eso van al personal que es privado". The user is unsure about publishing
  brands but will share them with coworkers.
- Sharing with coworkers = they install the MLE-setup plugin and receive the
  brand folders (zip or private repo access). No packaging script for now.

## Approaches considered

- **A. Generic scripts + brand folders (chosen).** Skill with process and
  parametrized scripts; each brand is a folder. Adding a brand = adding a
  folder. Cost: generalize two scripts that hardcode project data.
- **B. Skill with instructions and examples only.** Little to maintain, but
  each project re-invents the code and results drift.
- **C. Always start from the client's template file.** Most faithful when a
  template exists, but own designs would need a template first, and the drawn
  components of `ppt_lib` (cards, timeline, compare) would be lost.

Chosen: A, borrowing C: when a brand has a template, title/section/content
slides use its layouts; drawn components always use brand colors.

For the deck library itself (how to make it dynamic):

- **Three layers in python-pptx (chosen):** brand tokens, free primitives,
  components built from primitives, plus a render-and-look loop. Any slide can
  be composed from primitives; components are shortcuts, not limits. Output is
  native and editable.
- **Fixed component set only** (today's `ppt_lib`): consistent, but anything
  outside the menu needs new library code.
- **Design in HTML, convert to pptx:** the most freedom, but the result is hard
  to edit in PowerPoint. Rejected: output must stay editable.
- **One script per style** (modern / outlined / dark): three copies of the same
  components that drift. Rejected in favor of style presets driven by tokens.

## Design

### Layout

```
MLE-setup/skills/office-docs/
  SKILL.md                 process, triggers, when not to use
  references/
    deck-components.md     API of deck.py: primitives and components, one example each,
                           plus a few "free composition" examples built from primitives
    gotchas.md             lessons (webp, title length, export, proxy, GIF, QR, Mermaid)
    brand-format.md        brand.toml reference
  scripts/
    brand.py               load/validate a brand, resolve brand search path
    deck.py                deck library (from ppt_lib), brand-aware
    md2docx.py             Markdown -> .docx (from exportar_docx.py), brand-aware
    render.py              pptx/docx -> PDF -> PNG
    brand_from_pptx.py     create a brand folder from a .pptx
    new_brand.py           create a brand folder from parameters
  brands/neutral/brand.toml
  tests/                   pytest, run with uv
MLE-setup-personal/brands/
  ai4g-modern/             ppt_lib palette (navy/blue/cyan, Segoe UI)
  microsoft-delivery/      docx Delivery Guide look + Microsoft logos
  ai4g-readout/            sanitized layouts of the AI4G readout template
```

### Brand folder

`brand.toml` (read with stdlib `tomllib`, no YAML dependency) plus optional
assets:

```toml
name = "ai4g-modern"
description = "AI For Good Lab, modern own design"
style = "modern"    # modern | outlined | dark: component defaults

[colors]            # hex without '#'
primary = "0F2B5B"  # dark: title backgrounds, headings
accent  = "2870CF"
highlight = "50E6FF"
text = "2D3748"
muted = "5A6B85"
background = "F4F7FB"
surface = "FFFFFF"  # cards
card_border = "E2E8F0"
done = "3BBBA6"
planned = "FF7043"

[grid]              # inches; optional, defaults from slide size
margin = 0.6
columns = 12
gutter = 0.2

[fonts]
body = "Segoe UI"
heading = "Segoe UI"
mono = "Consolas"

[logos]             # paths relative to the brand folder, optional
light = "logo.png"  # for light backgrounds
dark = "logo-white.png"

[deck]
footer = "AI For Good Lab Uruguay"
template = "template.pptx"   # optional; without it slides are drawn
[deck.layouts]               # only with template: role -> layout name
title = "Title Slide - Earth"
content = "Title & Content AI4G"

[docx]
reference = "reference.docx" # optional; without it styles are generated from colors/fonts
cover_band = "0072C6"
company = "Microsoft"
```

Brand search order for `--brand NAME`: `./brands/NAME` in the current project,
then each directory in `MLE_BRANDS_PATH` (colon-separated), then
`~/.mle-setup/brands/NAME`, then the plugin's `brands/NAME`. The personal
repo's `bin/link-skills.*` also links `~/.mle-setup/brands` ->
`MLE-setup-personal/brands` so real brands resolve on every machine.

### Decks

Three layers in `deck.py` (one module or a small package; builder's choice),
all reading the brand, none with hardcoded colors or fonts:

1. **Tokens** (from `brand.toml`): semantic colors (background, surface,
   primary, accent, highlight, text, muted, border, done, planned), fonts,
   slide size, a layout grid (margins, columns, gutter) and a `style` preset
   that sets component defaults: `modern` (ppt_lib: filled cards, navy/cyan),
   `outlined` (readout: light cards with accent border, accent strips, icons)
   or `dark` (Ceibal: dark background, rounded nodes, chips). Brands can
   override any token.
2. **Primitives**: free-position building blocks in grid or inch units: rect,
   rounded rect, oval, line/connector, arrow, rich text (mixed runs: bold,
   color, size), chip/pill, icon, image (contain-fit), translucent scrim and
   gradient, table. Every argument can override the tokens. This layer is what
   lets the agent draw any slide it imagines.
3. **Components** built only from primitives: the `ppt_lib` set (title,
   section, content, final, cards_row, stat_row, compare, timeline, chain,
   maprow, numbered_grid, code_block, image_slide, image_row, split_image,
   speaker notes) plus the Ceibal diagram pieces (node with done/planned state,
   labeled arrow, container, legend, header with kicker/lead, page footer).
   Components render in the brand's style preset. New components are added
   when a pattern repeats; one-off slides use primitives directly.

With a template: open it, remove its slides, and use the mapped layouts for
title/section/content/final (title in the layout's placeholder, theme fonts);
without a template, these slides are drawn. Component signatures stay close to
`ppt_lib` so existing knowledge transfers; exact compatibility is not required.

**Layout check** (`deck.py check out.pptx` or automatic on save): reports
shapes outside the slide, text likely overflowing its box (estimated from font
size, box size and text length), unintended overlaps, and titles over ~55
characters. It is a warning list, not a blocker.

A deck is a short Python script in the user's project that imports the live
`deck.py` from the plugin (no pinned copies; changes to the library reach old
deck scripts, accepted). `render.py --build deck_script.py` sets PYTHONPATH and
runs it, then renders.

### Word documents

`md2docx.py doc.md --brand NAME [-o out.docx] [--no-word]`. Per-document data
moves from the hardcoded `DOCUMENTOS` dict to YAML-like front-matter parsed
minimally (key: value lines) or a sibling `doc.toml`: title, subtitle, client,
project, author, version, lang, toc_depth, page_break_on_h1,
shift_headings. Brand gives styles, cover band, logos and company. Keeps:
Mermaid rendering (optional; skipped with a warning if npx/Chrome missing),
cross-.md links turned into italic titles, cover, tables, header/footer, TOC via
Word or update-on-open, OOXML property ordering.

### Render

`render.py file.(pptx|docx) [--build script.py] [--dpi 150] [--pdf-only]`:
macOS exports a temporary copy through PowerPoint or Word via osascript and
closes **only that copy** (never the user's open documents); otherwise
`soffice --headless` if installed; otherwise it says render is unavailable.
PNGs go to a sibling folder for the agent to inspect.

### Adding a brand

- **From a .pptx** (`brand_from_pptx.py deck.pptx NAME --out DIR`): read the
  theme color and font schemes, slide size and layout names; save
  `template.pptx` with **all slides removed** and core properties (author,
  company, title, comments) cleared; extract images used by masters/layouts
  into `assets-review/`; list any text found in masters/layouts. It writes a
  draft `brand.toml` and renders one sample slide per layout. A sensitivity
  label (`docMetadata/LabelInfo.xml`) is **kept** and reported, never stripped
  silently. The agent then
  shows the user the extracted text, images and samples and asks for explicit
  confirmation that nothing client-specific remains before the brand is used.
- **From scratch** (`new_brand.py NAME --primary ... --accent ... --font ...
  [--logo path]`): the skill asks the user for these values, writes the folder,
  and renders a sample deck and a sample document for approval.

### Skill behavior (SKILL.md)

Triggers (Spanish and English): "armá una ppt de status", "deck del proyecto",
"presentación para el cliente", "pasá el plan a Word", "exportá a docx",
"documentación de entrega en Word", "sumá esta ppt como plantilla", "nueva
plantilla/marca". Not for: spreadsheets, editing a client's existing deck,
writing the content itself (status-update / handoff produce content; this skill
formats it).

Process: pick brand (ask if ambiguous) -> write content first (Markdown or deck
script) -> compose slides from components, dropping to primitives for anything
they don't cover -> build -> layout check -> render -> look at PNGs and fix
(overflow, overlaps, empty space, inconsistent alignment) -> deliver pptx/docx
(+ PDF if asked). Never put client data in a
brand folder. `status-update` and `handoff` get one line pointing here for
formatting.

### Dependencies and environment

Python >= 3.11. `python-pptx`, `python-docx`, `pymupdf` declared as PEP 723
inline metadata in each script and run with `uv run` (uv is installed);
fallback documented: a venv with those packages. pandoc required for .docx;
Node + Chrome only for Mermaid. Corporate proxy: installs may need to run
outside the sandbox (documented in gotchas).

### Verification

- pytest (via uv): brand loading and search order; a smoke deck using every
  primitive and every component in each style preset (modern, outlined, dark)
  with the neutral brand; the layout check flags a deliberately overflowing box
  and an off-slide shape; md2docx on a sample Markdown with table,
  code, image and cross-link (Mermaid test skipped when unavailable);
  brand_from_pptx on a generated pptx asserts no slides remain and core
  properties are empty.
- Manual, local only (never committed): brand_from_pptx on
  `clases/newppt.pptx`; rebuild one existing deck (e.g. the Clinicas readout)
  with `ai4g-readout` and one `mayo` deck with `ai4g-modern`, and check renders
  are the same visual family (not pixel-identical); export
  `ute/docs/plan_prod.md` with `microsoft-delivery` and compare with the
  current `docx/plan_prod.docx`. Source folders are read-only.
- `copilot skill list` shows `office-docs`; Claude Code `plugin validate` passes.

## Left to the builder

- Internal structure of the scripts and how much of `ppt_lib`'s private helpers
  to keep; exact `brand.toml` keys beyond the ones above.
- Front-matter vs sibling `doc.toml` for document metadata (pick one).
- Whether render reuses one osascript helper for PowerPoint and Word.
- Neutral brand palette.

## Calls I made (to review)

- Brand format TOML, read with stdlib (avoids a YAML dependency).
- Brand search path including `~/.mle-setup/brands` linked to the private repo.
- `uv run` with PEP 723 metadata instead of a shared venv.
- Initial private brands: `ai4g-modern` (style modern), `microsoft-delivery`
  (docx), `ai4g-readout` (template + style outlined); Marvik later. The dark
  Ceibal look ships only as the `dark` preset, not as a brand.
- Three style presets as token sets, not separate scripts.
- Deck scripts import the live library; drift accepted.
- Render closes only its own temporary copy.
- Layout check is advisory (warnings), not blocking.
- Sensitivity labels are kept and reported by `brand_from_pptx`.
