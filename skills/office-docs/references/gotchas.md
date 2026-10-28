# Gotchas

These are the known limits and their fixes. Most of them come from building
the earlier decks and documents this kit replaces.

## Content and layout

- **Long titles wrap.** Titles over about 55 characters wrap to two lines and
  push the body down. The layout check flags `long_title` on shapes named
  `"title"` and on title placeholders. Shorten the title or move detail to
  the kicker or lead.
- **The layout check is advisory and heuristic.** It estimates text size at
  about 0.5 em per glyph and 1.2 line height. It skips boxes with autofit and
  flags overlaps only between text shapes that cross without one containing
  the other.
  - Template placeholders inherit autofit and font size from the layout, so on
    template slides an overflow warning can be a false positive or a false
    negative.
  - Rotation and groups are only approximated.
  - Text boxes that exactly touch can flag as overlapping because of floating
    point. Leave a small gap.
  - An `OK` does not replace looking at the PNGs.
- **Empty lists** passed to `cards_row`, `stat_row`, `timeline` or `image_row`
  raise `ZeroDivisionError`. Pass at least one item or skip the component.
- **Dark style:** `stat_row`, `maprow`, `numbered_grid`, `code_block` and the
  right panel of `compare` fill with `primary`, which in `dark` is close to the
  background. Set a lighter `primary` in the brand, or compose those panels
  with `surface`.
- **Images:** python-pptx cannot read `.webp`, and `image()` raises with a
  hint. Convert first, for example with `sips -s format png in.webp --out in.png`
  on macOS. GIFs stay animated in PowerPoint, but the PNGs show a single frame.
- **Logos** are not placed on slides automatically (see `deck-api.md`). In
  Word, `[logos] light` goes in the page header and `dark` goes on the cover band.
- **Build script name:** do not call it `deck.py` or `brand.py`. The script's
  folder comes first on `sys.path`, so that name would shadow the library.

## Template brands (brands with `[deck] template`)

- **Set `content_bg` and the colors to match the template's background.**
  Content drawn on template slides picks its text contrast against
  `[components] content_bg`, not the master. On a dark template with the
  default light `content_bg`, drawn text comes out dark on dark.
- **Mapped content slides get no drawn footer or page number.** The footer is
  whatever the master shows, and python-pptx does not copy the layout's
  slide-number placeholder, so there is no page number unless the master
  draws one. Call `d.footer(s)` to draw one yourself.
- **The kicker is dropped** on layouts with no subtitle or small body
  placeholder to hold it.
- **`content_slide(kicker, "")`** with an empty title breaks on template
  layouts. Always pass a title.
- **Several masters:** decks use the layouts of the first master only. The
  `brand_from_pptx.py` report notes this.

## Render on macOS (`render.py`)

- It drives PowerPoint (.pptx) or Word (.docx) through AppleScript on a
  **temporary copy with a unique name** (`office-docs-xxxxxxxx`), and it
  addresses that copy only by name. It never touches other open documents,
  and it never exports a stale version that is open in the app.
- **Office comes to the front** while it renders.
- **The first run may need the Automation permission:** System Settings →
  Privacy & Security → Automation lets your terminal control PowerPoint or
  Word. Without it, render fails with error -1743 and prints this hint.
- **"Grant File Access" ("Conceder acceso al archivo") dialog:** Office is
  sandboxed, so render puts the `office-docs-xxxxxxxx` copy and its PDF in a
  fresh `office-docs-render-*` folder inside the app's own container
  (`~/Library/Containers/com.microsoft.Powerpoint/Data/tmp`, or `...Word...`),
  else the Office group container, and deletes that folder afterwards. Office
  can always read and write there, so the dialog should no longer appear.
  If macOS does not let your terminal write into the container ("access data
  from other apps"), render falls back to the system temp folder, where the
  dialog can still show up: render then waits until it times out (600 s), and
  later renders fail right away with error -9074 (the message says so) until
  the dialog is closed. Press Esc or click Cancel in PowerPoint/Word, then run
  the render again. Allowing the terminal to access other apps' data avoids
  the fallback. macOS decides this per app: Word's container (and the Office
  group containers) can be off limits ("Operation not permitted") even when
  PowerPoint's is writable, so `.docx` renders and the Word TOC fill may still
  use the system temp folder and can still hit the dialog.
- A render that hangs for another reason times out after 600 s and closes
  the copy by name.
- `--out DIR` deletes numbered PNGs (`01.png`...) that are already in DIR, so
  stale pages do not linger. Point it at a folder used only for renders.
- **The LibreOffice fallback is untested.** It is the `soffice --headless`
  path used when Office is not installed (Linux, or a Mac without Office).

## Word (`md2docx.py`)

- **Filling the TOC can take about 80 s per build** (closer to 20 s when Word
  is already running). Word opens a temporary copy
  and updates the fields. `--no-word` skips that step. Word then asks to
  update fields when the document is opened, and the TOC fills when the user
  says yes.
- **Mermaid** runs through `npx -y @mermaid-js/mermaid-cli`, which uses the npx
  cache and needs Node and Chrome.
  - Behind a corporate proxy, the first download can hang.
  - Each block times out after 300 s. A block that fails stays as a code
    block, and the build continues.
  - `flowchart LR` and `graph LR` turn into top-to-bottom (TB) so they fit
    the page.
- **Front matter** is a `---` block at the very top of the file. A document
  that starts with a horizontal rule `---` gets it parsed as front matter, so
  start with a heading or text instead.
- Labels follow `lang` (es/en), but the default `date` is always written in
  Spanish. Set `date:` explicitly for English documents.
- Links to other `.md` files become italic text, because the document is
  standalone.
- Without `[docx] code_bg`, code blocks use F2F2F2 in every brand.

## Python dependencies and the network

- Scripts declare their dependencies in PEP 723 headers and run with
  `uv run`, which installs them on first use.
- **If pypi.org is blocked (corporate network or proxy SSL errors)**, set
  `UV_DEFAULT_INDEX` to your corporate mirror in your shell environment, or
  run the install outside the sandbox.
- **Never hardcode an index URL in repo files.** This is a binding rule.
- Fallback without uv: create a venv with `python-pptx`, `python-docx` and
  `pymupdf`. Then run the scripts with that venv's `python` instead of
  `uv run`, for example `python "$OD/scripts/render.py" out.pptx --build build_deck.py`.
- pandoc is required for `.docx` (`brew install pandoc`).

## Brands from a client .pptx (`brand_from_pptx.py`)

- **The report lists every text in masters and layouts**, placeholder
  prompts included. Review it for client names, project names, people and
  numbers before `--confirm`.
- **Not stripped and not reported:** tags, chart and SmartArt text, and alt
  text on masters. Check them manually in PowerPoint (View → Slide Master).
- **Sensitivity labels are kept on purpose** and reported. Decks built from
  the template inherit the label.
- Not cleared either: the `Template` field in `app.xml` and the core dates.
- A hyperlink on a master that points to a removed relationship can make
  PowerPoint offer to repair the file. Remove that link from the template.
- Layout roles are guessed from layout names. Check `[deck.layouts]` against
  the layout names listed in the report.

## Handy recipes

- **QR code** for a slide:
  `uv run --with segno python -c "import segno; segno.make('https://example.com').save('qr.png', scale=14, border=2, dark='#0F2B5B')"`,
  then `d.image(s, "qr.png", ...)`.
- **Compressing a GIF** with ffmpeg in two passes, with a palette and no
  dither:
  `ffmpeg -i in.gif -vf "fps=10,scale=960:-1:flags=lanczos,palettegen=max_colors=64" pal.png`, then
  `ffmpeg -i in.gif -i pal.png -lavfi "fps=10,scale=960:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=none" out.gif`.
