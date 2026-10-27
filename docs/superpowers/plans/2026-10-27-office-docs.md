# office-docs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A skill `office-docs` that builds editable decks (.pptx) and Word
documents (.docx) from swappable brand folders, renders them for visual
verification, and creates new brands from a .pptx or from scratch.

**Architecture:** Python scripts under `skills/office-docs/scripts/`. A brand
is a folder with `brand.toml`; `brand.py` loads it. Decks have three layers:
tokens (brand + style preset), free primitives, components built only from
primitives; an advisory layout check runs on save. `md2docx.py` drives pandoc
plus python-docx post-processing. `render.py` exports through PowerPoint/Word
(macOS) or LibreOffice and rasterizes with PyMuPDF.

**Tech Stack:** Python >= 3.11, python-pptx, python-docx, PyMuPDF, pandoc,
optional Node `@mermaid-js/mermaid-cli` + Chrome, osascript, uv, pytest.

**Spec:** `docs/superpowers/specs/2026-10-27-office-docs-design.md`

**Source code to port (read-only, never modify):**
- `~/Documents/Microsoft/clases/mayo/ppt_lib.py` (components, `_bullets`, `_est_lines`, `_fit`)
- `~/Documents/Microsoft/clases/mayo/render_deck.py` (osascript export, PyMuPDF)
- `~/Documents/Microsoft/clases/ppts_eli/create_ceibal_ppt.py` (primitives lines 59-266)
- `~/Documents/Microsoft/clases/sprint_readout/create_clinicas_template_ppt.py` (template use, outlined look)
- `~/Documents/Microsoft/ai4g/ute/docs/exportar_docx.py` (docx pipeline)
- `~/Documents/Microsoft/clases/CLAUDE.md` lines ~92-336 (gotchas)

## Global Constraints

- Python >= 3.11 (`tomllib`). Dependencies only: python-pptx, python-docx, pymupdf (+ pytest for tests). No YAML library.
- Every CLI script carries PEP 723 inline metadata and runs with `uv run SCRIPT`.
- Test command (TEST_CMD), from the MLE-setup root:
  `uv run --python ">=3.11" --with pytest --with python-pptx --with python-docx --with pymupdf pytest skills/office-docs/tests -q`
  If package download fails with SSL errors (corporate proxy), rerun outside the sandbox.
- Public API units are **inches as floats**; colors are a **token name** (`"accent"`) or a **hex** (`"2870CF"`, `"#2870cf"` also accepted).
- No colors, fonts or company names hardcoded in scripts: everything comes from the brand or the style preset.
- **No client data in any brand**: only colors, fonts, logos, layouts. Real brands (Microsoft, AI4G, Marvik, clients) live only in `MLE-setup-personal/brands/`. Public repo ships only `brands/neutral` (no third-party logos).
- Output must stay editable in PowerPoint: native shapes and text, never whole slides as images.
- Render never closes or modifies documents the user has open; it works on a temporary copy and closes only that copy.
- The layout check is advisory: it prints warnings, never fails a build.
- Never modify files under `~/Documents/Microsoft/`.
- Branch: before Task 1, the pending uncommitted changes in both repos are committed (user decides at plan review); work happens on branch `office-docs` in each repo. No push.
- Every commit ends with:
  `Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>` and
  `Copilot-Session: c15bce25-1784-4a89-b675-f652b54692e6`.

## Review Focus

1. Paths and text with spaces, accents and em dashes (the user's real files are named like `Overview Técnico de Proyectos — Q3 2026 1.pptx`): render and md2docx must work with them. Tests in Task 6 and Task 7.
2. A brand whose `deck.layouts` names a layout the template doesn't have: a clear error listing the available layout names, not a silent fallback. Test in Task 4.
3. Hex colors with `#`, lowercase, or invalid (`"12345"`, `"navy"` that isn't a token): normalize the valid ones; for invalid ones, raise an error that names the brand key. Tests in Tasks 1 and 2.
4. Images that python-pptx can't read (`.webp`) or missing files: an error that says to convert to PNG or gives the missing path, not a library traceback. Test in Task 2.
5. A .pptx whose masters/layouts contain client text (e.g. "Cliente X", a project name): it is listed in the report, and the draft brand cannot be loaded until it is confirmed. Test in Task 8.

---

## File Structure

```
MLE-setup/skills/office-docs/
  SKILL.md
  .gitignore                  __pycache__/  .pytest_cache/  *-render/
  references/deck-api.md      primitives + components, one example each, 3 free-composition examples
  references/brand-format.md  brand.toml reference (all keys, defaults, search order)
  references/gotchas.md       webp, title length, export, proxy, GIF, QR, Mermaid
  brands/neutral/brand.toml
  scripts/brand.py            Brand, STYLE_PRESETS, search path, load/validate
  scripts/deck.py             Deck class (core, template), re-exports; CLI `check`
  scripts/deck_prims.py       Primitives mixin
  scripts/deck_components.py  Components mixin (ppt_lib set + Ceibal diagram pieces)
  scripts/deck_check.py       advisory layout check
  scripts/render.py           pptx/docx -> PDF -> PNG, --build runner
  scripts/md2docx.py          front-matter, pandoc, Mermaid, CLI
  scripts/docx_brand.py       reference doc, cover, tables, header/footer, OOXML fixes
  scripts/brand_from_pptx.py
  scripts/new_brand.py
  tests/conftest.py           adds scripts/ to sys.path; fixtures: neutral brand, tmp brand factory
  tests/test_*.py             one per script
MLE-setup-personal/
  brands/ai4g-modern/  brands/microsoft-delivery/  brands/ai4g-readout/
  bin/link-skills.sh  bin/link-skills.ps1  README.md
```

---

### Task 1: Brand loading, style presets, neutral brand

**Files:**
- Create: `skills/office-docs/scripts/brand.py`, `skills/office-docs/brands/neutral/brand.toml`, `skills/office-docs/.gitignore`, `skills/office-docs/tests/conftest.py`, `skills/office-docs/tests/test_brand.py`

**Interfaces:**
- Produces:
  - `COLOR_TOKENS = ("background","surface","primary","on_primary","accent","highlight","text","muted","card_border","done","planned")`
  - `STYLE_PRESETS: dict[str, dict]` for `"modern"`, `"outlined"` and `"dark"`. Each has `"colors"`, the default for every token, and `"components"`. The `"components"` keys are `card` (`"filled"|"outlined"|"dark"`), `radius: float`, `accent_strip` (`"top"|"left"|None`), `content_bg` (a token) and `node_shape` (`"rounded"|"rect"`).
    - modern: ppt_lib palette (NAVY 0F2B5B, BLUE 2870CF, CYAN 50E6FF, BG F4F7FB, CARD_BORDER E2E8F0, TEXT 2D3748, MUTED 5A6B85).
    - outlined: readout palette (card F2F2F2, border/accent 0078D4, accent1 156082, text 000000, grey 595959).
    - dark: Ceibal palette (BG 1E2438, CARD 252C40, CY 00BCD4, TE 1DE9B6, OR FF7043, TXT D0D6E8, MUT 8891AA).
  - `@dataclass(frozen=True) class Brand`:
    - identity and look: `name: str`, `root: Path`, `description: str`, `style: str`, `colors: dict[str,str]` (uppercase hex, preset merged with brand), `components: dict`, `fonts: dict[str,str]` (body, heading, mono).
    - assets: `logos: dict[str, Path]`.
    - deck: `footer: str`, `template: Path | None`, `layouts: dict[str,str]`.
    - layout: `grid: dict[str,float]` (margin 0.6, columns 12, gutter 0.2 by default).
    - docx: `docx: dict` (reference: Path|None, cover_band, company, plus optional heading_color, code_bg, note_bg, rule).
    - review: `draft: bool`.
  - `class BrandError(Exception)`, `class BrandNotFound(BrandError)`
  - `PLUGIN_BRANDS: Path`, which is `scripts/../brands`.
  - `brand_search_path(cwd: Path | None = None) -> list[Path]` returns, in order: `cwd/brands`, each entry of `MLE_BRANDS_PATH` (split on `os.pathsep`), `~/.mle-setup/brands` and `PLUGIN_BRANDS`.
  - `find_brand(name: str, cwd: Path | None = None) -> Path`
  - `load_brand(name_or_path: str | Path, cwd: Path | None = None, allow_draft: bool = False) -> Brand`
  - `normalize_hex(value: str, key: str) -> str`

- [ ] **Step 1: Write failing tests** in `test_brand.py`:
  - `test_neutral_loads`: `b = load_brand("neutral")`; `b.style == "modern"`; `set(COLOR_TOKENS) <= b.colors.keys()`; `b.template is None`.
  - `test_search_order(tmp_path, monkeypatch)`: create a brand `x` in `tmp_path/proj/brands/x` and in `tmp_path/env/x`; set `MLE_BRANDS_PATH=tmp_path/env`; assert `find_brand("x", cwd=tmp_path/"proj")` is under `proj`; remove the proj copy, assert it resolves under `env`.
  - `test_not_found_lists_dirs`: `pytest.raises(BrandNotFound)`; message contains every dir of `brand_search_path()`.
  - `test_hex_normalized`: brand with `accent = "#2870cf"` loads as `"2870CF"`.
  - `test_invalid_hex_names_key`: `primary = "12345"` raises `BrandError` with `"colors.primary"` in message.
  - `test_unknown_style`: `style = "fancy"` raises `BrandError` listing the three styles.
  - `test_missing_asset`: `[logos] light = "nope.png"` raises `BrandError` with the path.
  - `test_draft_refused`: `draft = true` raises `BrandError` mentioning `--confirm`; `allow_draft=True` loads.
  - `test_brand_overrides_preset`: `style="dark"`, `[colors] accent="FF0000"` gives accent `FF0000`, background from dark preset `1E2438`.
- [ ] **Step 2:** Run TEST_CMD. Expected: FAIL (ImportError on `brand`).
- [ ] **Step 3: Implement `brand.py`, the neutral brand, conftest, .gitignore.** `conftest.py` inserts `scripts/` at `sys.path[0]` and provides `make_brand(tmp_path) -> Callable[[str, str], Path]` (name, toml text → folder). Neutral brand: `style = "modern"`, grey/teal palette of the builder's choosing, fonts `Calibri`/`Calibri`/`Consolas`, footer `""`, no logos.
- [ ] **Step 4:** Run TEST_CMD. Expected: all pass.
- [ ] **Step 5: Commit** `feat(office-docs): brand loading and style presets`.

---

### Task 2: Deck core and primitives

**Files:**
- Create: `scripts/deck.py`, `scripts/deck_prims.py`, `tests/test_prims.py`

**Interfaces:**
- Consumes: `load_brand`, `Brand`, `BrandError` (Task 1).
- Produces:
  - `class Deck(Primitives, Components)` in `deck.py` (Components is an empty mixin stub until Task 3), with:
    - `__init__(self, brand: str | Path | Brand, footer: str | None = None, cwd: Path | None = None)`. Without a template it builds a blank 13.333x7.5 in presentation.
    - Attributes: `prs`, `brand`, `W: float`, `H: float`, `page: int`.
    - `color(self, c: str) -> RGBColor`. Accepts a token or a hex; anything else raises `ValueError` naming the value and the valid tokens.
    - `font(self, role: str) -> str`. Maps `"body"|"heading"|"mono"` to the brand font; any other string passes through as a literal font name.
    - `col(self, start: int, span: int = 1) -> tuple[float, float]`. Returns grid x and width.
    - `blank_slide(self, bg: str | None = None) -> Slide`. `None` uses `components["content_bg"]`.
    - `notes(self, slide, text: str) -> Slide`
    - `save(self, path: str | Path) -> int`. Returns the slide count. After Task 5 it also prints check warnings.
  - `class Primitives` in `deck_prims.py`. Every method takes the slide first and returns the created shape (or text frame).
    - Shapes and lines:
      - `rect(s, x, y, w, h, fill="surface", line=None, line_w=1.0, dash=False, radius=None, opacity=None)`
      - `oval(s, x, y, w, h, fill="accent", line=None)`
      - `line(s, x1, y1, x2, y2, color="muted", width=1.5, dash=False, arrow_end=False)`
      - `arrow(s, x, y, w, h, color="accent", direction="right")`. `direction` is one of `right`, `left`, `up`, `down`. Draws a block arrow.
    - Text:
      - `text(s, x, y, w, h, content, size=14, color="text", font="body", bold=False, italic=False, align="left", anchor="top", line_spacing=1.05)`
        - `content` is `str` or a list of paragraphs. A paragraph is `str` or a list of runs. A run is `str` or a dict with `text` plus optional `size`, `color`, `bold`, `italic` and `font`.
        - `"\n"` in a str splits paragraphs.
      - `bullets(s, x, y, w, h, items, size=15, marker_color="highlight", spread=True)`. Ports `ppt_lib._bullets` semantics. `"Lead: rest"` bolds the lead in `primary`, and a leading two-space indent makes a sub-bullet.
      - `chip(s, x, y, label, fill="accent", color="on_primary", size=9, w=None, h=0.26)`. `w=None` auto-sizes from the label length.
    - Images and effects:
      - `image(s, path, x, y, w, h, fit="contain", caption=None, frame=False)`. Contain-fit is centered (port `_fit`). Raises `ValueError("... .webp no soportado por python-pptx: convertir a PNG")` for `.webp` and `FileNotFoundError` with the path when missing.
      - `icon(s, path, x, y, size=0.5)`
      - `scrim(s, x, y, w, h, color, opacity)`. `opacity` runs 0–100.
      - `gradient(s, x, y, w, h, color, a0, a1, angle=0)`. Alpha goes from `a0` to `a1`; port `grad_scrim`.
    - `table(s, x, y, w, rows: list[list[str]], header=True, col_widths=None, size=12)`. Header fill is `primary` with `on_primary` text.

- [ ] **Step 1: Write failing tests** (`test_prims.py`, deck from `"neutral"`):
  - `test_color_tokens_and_hex`: `d.color("accent")` equals the neutral accent; `d.color("#00ff00") == RGBColor(0,0xFF,0)`; `pytest.raises(ValueError, match="navy")` for `"navy"`.
  - `test_rect_units_and_fill`: `sh = d.rect(s, 1, 1, 2, 1, fill="primary")`; `sh.left == Inches(1)`; `sh.fill.fore_color.rgb == d.color("primary")`.
  - `test_text_runs`: `d.text(s,0,0,4,1,[[{"text":"A","bold":True},"b"],"second"])`; two paragraphs; first has runs `A`(bold) and `b`.
  - `test_bullets_lead_and_sub`: items `["Uno: detalle", "  sub"]`; first paragraph has a bold run `"Uno: "`; second paragraph text contains `sub`.
  - `test_image_webp_rejected`, `test_image_missing`: messages as above.
  - `test_image_contain_fit(tmp_path)`: 200x100 PNG (write with PyMuPDF `fitz.Pixmap`) into a 2x2 box: picture width 2 in, height 1 in, top offset 0.5 in.
  - `test_scrim_alpha`: the shape XML contains `<a:alpha val="40000"/>` for opacity 40.
  - `test_table_header`: 2x2 table; cell (0,0) fill is `primary`.
  - `test_save_counts(tmp_path)`: two blank slides → `save` returns 2 and the file reopens.
- [ ] **Step 2:** Run TEST_CMD. Expected: FAIL.
- [ ] **Step 3: Implement** `deck.py` core and `deck_prims.py` (port helpers from ppt_lib and Ceibal; replace module constants with `self.color/self.font`).
- [ ] **Step 4:** Run TEST_CMD. Expected: pass.
- [ ] **Step 5: Commit** `feat(office-docs): deck core and primitives`.

---

### Task 3: Components in three style presets

**Files:**
- Create: `scripts/deck_components.py`, `tests/test_components.py`

**Interfaces:**
- Consumes: `Deck`, all `Primitives` (Task 2). Components draw **only** through primitives.
- Produces: `class Components` methods. Arguments and dict keys follow `ppt_lib` for the ported components.
  - Slides:
    - `title_slide(kicker, title, subtitle) -> Slide`
    - `section_slide(number, title, image=None, caption=None) -> Slide`
    - `content_slide(kicker, title) -> tuple[Slide, float]`. The float is the body top in inches.
    - `final_slide(title, subtitle) -> Slide`
    - `image_slide(kicker, title, path, caption=None) -> Slide`
  - Building blocks:
    - `header(s, kicker, title, lead=None) -> float`. Names the title shape `"title"`.
    - `footer(s, page: int | None = None)`. Writes `brand.footer` and the page number.
  - Content components:
    - `cards_row(s, top, cards, height=3.2)`. `cards` items are `{title, lines, accent?, tag?, icon?}`.
    - `stat_row(s, top, stats)`. Items are `{big, cap}`.
    - `compare(s, top, ltitle, litems, rtitle, ritems)`
    - `timeline(s, top, steps, box_h=2.5)`. Steps use ppt_lib's step keys.
    - `chain(s, x, y, w, h, steps, accent="accent", size=12)`
    - `maprow(s, top, rows)`
    - `numbered_grid(s, top, items, height=None)`
    - `code_block(s, top, lines, height=3.6, note=None)`
    - `image_row(s, top, items, height=None)`
    - `split_image(s, top, path, items, side="right", ratio=0.4, caption=None)`
  - Diagram pieces (ported from Ceibal):
    - `node(s, x, y, w, h, label, sub=None, accent="accent", state="done", shape=None)`. `state` is `"done"` or `"planned"`; `planned` draws a dashed border and a dimmer fill. `shape=None` falls back to `components["node_shape"]`.
    - `labeled_arrow(s, x, y, w, label=None, color="accent")`
    - `container(s, x, y, w, h, label)`
    - `legend(s, x, y, items=None)`. `None` means `[("Hecho","done"),("Planeado","planned")]`.
  - How each style draws a card (`components["card"]`):
    - `filled`: surface fill, `card_border` line, and an accent strip (`top`).
    - `outlined`: surface fill with a 1.5 pt line in the card's accent, and an accent strip on the `left`.
    - `dark`: surface fill, no line, rounded corners.

- [ ] **Step 1: Write failing tests:**
  - `test_smoke_all_components[modern|outlined|dark]` (parametrized over brands made with `make_brand` per style):
    - Build one slide per component and run every slide factory.
    - Save, reopen, and assert the slide count.
    - Every shape lies within `0..W` x `0..H`.
  - `test_card_style_differs`: for each style, find the card body shape (name it `"card"` in the implementation):
    - outlined: `line.color.rgb == accent`.
    - filled: `line.color.rgb == card_border`.
    - dark: `line.fill.type` is background/none.
  - `test_planned_node_dashed`: `node(..., state="planned")` line `dash_style` is not None; done node is None.
  - `test_content_slide_returns_top`: `top > 1.0` and `< 2.5`; the title shape is named `"title"`.
  - `test_footer_from_brand`: brand footer `"Lab X"` appears in the content slide text.
- [ ] **Step 2:** Run TEST_CMD. Expected: FAIL.
- [ ] **Step 3: Implement** `deck_components.py`; port the ppt_lib layout math, reading sizes and colors from tokens and `components`.
- [ ] **Step 4:** Run TEST_CMD. Expected: pass.
- [ ] **Step 5: Commit** `feat(office-docs): deck components with style presets`.

---

### Task 4: Template-backed decks

**Files:**
- Modify: `scripts/deck.py` (init with template), `scripts/deck_components.py` (title/section/content/final use layouts when mapped)
- Test: `tests/test_template.py`

**Interfaces:**
- Consumes: `Brand.template`, `Brand.layouts` (roles `title`, `section`, `content`, `final`).
- Produces:
  - When `brand.template` is set, `Deck.__init__` opens a copy, removes every existing slide (drops `sldId` entries and their relationships), and sets `W`/`H` from the template.
  - `Deck.layout(role: str) -> SlideLayout | None`. Raises `BrandError` when the mapped name is missing. The message lists `[l.name for l in prs.slide_layouts]`.
  - The slide factories, when a role is mapped:
    - add the slide on that layout;
    - put the title (and the subtitle or kicker, when a placeholder exists) into the placeholders;
    - remove the unused empty placeholders.
  - `content_slide` returns `top` = title placeholder bottom + 0.25. Unmapped roles fall back to drawn slides.

- [ ] **Step 1: Write failing tests.** The fixture saves the python-pptx default template (`Presentation()`) with 2 slides to `tmp/template.pptx`, and a brand maps `title="Title Slide"`, `content="Title Only"`.
  - `test_template_slides_removed`: `Deck(brand)` has 0 slides.
  - `test_title_uses_layout`: `title_slide("k","T","sub")`:
    - `slide.slide_layout.name == "Title Slide"`
    - `slide.shapes.title.text == "T"`
  - `test_no_empty_placeholders`: after a `content_slide`, no placeholder with an empty text frame remains.
  - `test_missing_layout_lists_available`: mapping `content="Nope"` raises `BrandError` whose message contains `"Title Only"`.
  - `test_unmapped_role_drawn`: `final_slide` with no `final` mapping succeeds on the blank layout.
- [ ] **Step 2:** Run TEST_CMD. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4:** Run TEST_CMD. Expected: pass (including Task 3 smoke tests).
- [ ] **Step 5: Commit** `feat(office-docs): template-backed decks`.

---

### Task 5: Advisory layout check

**Files:**
- Create: `scripts/deck_check.py`, `tests/test_check.py`
- Modify: `scripts/deck.py` (`save` prints issues to stderr; `python deck.py check FILE` CLI)

**Interfaces:**
- Produces:
  - `@dataclass Issue(slide: int, shape: str, kind: str, detail: str)`.
    - `slide` is 1-based.
    - `kind` is one of `off_slide`, `overflow`, `overlap` or `long_title`.
  - `check_presentation(prs) -> list[Issue]` and `check_file(path) -> list[Issue]`.
  - CLI `deck.py check FILE`: prints one line per issue and `OK` when the list is empty, and always exits 0.
- Rules (exact):
  - `off_slide`: any shape whose bbox exceeds the slide by more than 0.02 in.
  - `overflow`: text frame with no autofit, where the estimated height exceeds 1.05 x the box height minus its insets.
    - Estimated height = Σ paragraphs `lines * size_pt * 1.2`.
    - `lines` uses ppt_lib `_est_lines`: chars per line = `max(10, int(width_pt / (size_pt*0.5)))`.
    - `size_pt` is the paragraph's max run size, or 18 when unknown.
  - `overlap`: two shapes that **both have non-empty text** and whose bboxes intersect, where neither box contains the other.
  - `long_title`: a shape named `"title"` or a title placeholder with text longer than 55 characters.

- [ ] **Step 1: Write failing tests:**
  - `test_clean_deck_no_issues`: the modern smoke deck from Task 3 returns `[]`. If it doesn't, fix the components, not the rule.
  - `test_off_slide`: rect at x=12.8, w=1 → one `off_slide`.
  - `test_overflow`: 300 chars at size 18 in a 3x0.5 box → `overflow`.
  - `test_overlap_text_only`: two text boxes crossing → `overlap`. Text on top of a card that contains it → none.
  - `test_long_title`: a 60-char title → `long_title`.
  - `test_cli_exit_zero`: subprocess `python deck.py check bad.pptx` returns 0 and stdout contains `overflow`.
- [ ] **Step 2:** Run TEST_CMD. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4:** Run TEST_CMD. Expected: pass.
- [ ] **Step 5: Commit** `feat(office-docs): advisory layout check`.

---

### Task 6: Render

**Files:**
- Create: `scripts/render.py`, `tests/test_render.py`

**Interfaces:**
- Produces:
  - `class RenderUnavailable(RuntimeError)`
  - `@dataclass RenderResult(pdf: Path, pngs: list[Path])`
  - `applescript_quote(path: Path) -> str`. Returns the POSIX path as an AppleScript string literal, escaping `\` and `"`.
  - `export_pdf(src: Path, pdf: Path) -> Path`. The backend is chosen in this order:
    1. On macOS, when PowerPoint (for .pptx) or Word (for .docx) is installed, copy `src` to a fresh temp dir and export that copy through osascript, closing **only the document whose full name is the temp copy**.
    2. Otherwise, `soffice --headless --convert-to pdf`.
    3. Otherwise, raise `RenderUnavailable` naming both options.
  - `pdf_to_png(pdf: Path, out_dir: Path, dpi: int = 150) -> list[Path]`. Writes `01.png`, `02.png`, and so on.
  - `run_build(script: Path) -> None`. Runs `sys.executable script` with `cwd=script.parent` and `PYTHONPATH` set to the scripts dir, prepended to the existing `PYTHONPATH`. Raises `CalledProcessError` on failure.
  - `render(path: Path, dpi=150, pdf_only=False, out_dir: Path | None = None) -> RenderResult`. The PDF goes next to `path`, and PNGs go to `<stem>-render/` by default.
  - CLI: `render.py FILE [--build SCRIPT] [--dpi N] [--pdf-only] [--out DIR]`. It prints the paths.

- [ ] **Step 1: Write failing tests:**
  - `test_pdf_to_png(tmp_path)`: a 2-page PDF made with fitz → 2 PNGs named `01.png`, `02.png`.
  - `test_applescript_quote`: `Path('/a/Overview Técnico — Q3 "x".pptx')` → a result that starts and ends with `"` and contains `\"x\"`.
  - `test_run_build_sets_pythonpath(tmp_path)`: the script writes `os.environ["PYTHONPATH"]` to a file. It starts with the scripts dir. A script that imports `deck` runs without error.
  - `test_unavailable(monkeypatch)`: force no Office and no soffice (`shutil.which` → None, `sys.platform` patched) → `RenderUnavailable`.
  - `test_real_export` (skipped unless `OFFICE_DOCS_RENDER=1`): the smoke deck saved under `tmp_path/"Carpeta con espacio — ñ"/deck.pptx` renders to ≥1 PNG.
- [ ] **Step 2:** Run TEST_CMD. Expected: FAIL.
- [ ] **Step 3: Implement.** Port the osascript from `render_deck.py`, replacing "close all presentations" with closing the presentation/document whose full name equals the temp copy.
- [ ] **Step 4:** Run TEST_CMD. Expected: pass. Then run `OFFICE_DOCS_RENDER=1 <TEST_CMD> -k real_export`. Expected: pass on this Mac.
- [ ] **Step 5: Manual check:**
  1. Open any .pptx in PowerPoint.
  2. Run `uv run skills/office-docs/scripts/render.py <smoke deck>`.
  3. Confirm the first presentation is still open and unchanged.
- [ ] **Step 6: Commit** `feat(office-docs): render to PDF and PNG`.

---

### Task 7: Markdown to Word

**Files:**
- Create: `scripts/md2docx.py`, `scripts/docx_brand.py`, `tests/test_md2docx.py`, `tests/data/sample.md` (+ `tests/data/img.png` generated in a fixture, not committed)

**Interfaces:**
- Consumes: `load_brand`, `Brand.docx`, `Brand.colors`, `Brand.fonts`, `Brand.logos`.
- Produces:
  - `md2docx.py`:
    - `parse_front_matter(text: str) -> tuple[dict[str, str], str]`. The front matter is a leading `---` block of `key: value` lines; there is no YAML library. Without a block it returns `({}, text)`.
    - `@dataclass DocMeta`:
      - `title: str`; `subtitle=""`, `client=""`, `project=""`, `author=""`, `version="1.0"`, `lang="es-UY"`.
      - `date: str = ""`. Empty means today in Spanish, e.g. "27 de octubre de 2026".
      - `toc_depth: int = 3`, `page_break_on_h1: bool = True`, `shift_headings: int = 0`.
    - `DocMeta.from_dict(d: dict[str,str], fallback_title: str) -> DocMeta`. Unknown keys raise `ValueError` listing the valid keys. `fallback_title` is the first H1, or else the file stem.
    - `render_mermaid(md: str, workdir: Path) -> str`. It replaces fenced `mermaid` blocks with PNG images, turning `LR` into `TB`. When `npx` or Chrome is missing, it prints one warning and leaves the blocks as code.
    - `build_docx(md_path: Path, brand: Brand, out: Path | None = None, use_word: bool = True) -> Path`. The default `out` is `<stem>.docx` next to the md.
    - CLI: `md2docx.py DOC.md --brand NAME [-o OUT] [--no-word]`.
  - `docx_brand.py` (port from `exportar_docx.py`; every color comes from the brand):
    - `make_reference_docx(brand, dest: Path, page_break_on_h1: bool) -> Path`
    - `add_cover(doc, meta, brand)`
    - `style_tables(doc, brand)`
    - `add_header_footer(doc, meta, brand)`
    - `fill_toc_with_word(docx: Path) -> bool`
    - `update_fields_on_open(docx: Path)`
    - `fix_property_order(docx: Path)`. Keeps `_ORDEN` as is.
    - Color mapping:
      - headings use `docx.heading_color`, falling back to `colors.accent`;
      - the cover band uses `docx.cover_band`, falling back to `colors.primary`;
      - code uses `docx.code_bg`, falling back to `"F2F2F2"`;
      - notes use `docx.note_bg`, falling back to `colors.background`;
      - the footer rule uses `docx.rule`, falling back to `colors.card_border`;
      - text uses `colors.text`, and muted text uses `colors.muted`.
  - Cross-document links `[Text](other.md)` become italic `Text` with no hyperlink (Lua filter).

- [ ] **Step 1: Write failing tests** (skip the module if `shutil.which("pandoc")` is None).
  - `sample.md` contains: front matter (`title: Plan de producción`, `client: Demo`, `version: 0.9`), H1/H2, a 3x2 table, a code block, `![img](img.png)` and `[Arquitectura](arquitectura.md)`.
  - Copy it to `tmp_path/"Docs con espacio — ñ"` and build with `use_word=False` and the neutral brand.
  - `test_front_matter_parse`: values as above; unknown key `colour: x` raises `ValueError` mentioning `version`.
  - `test_docx_built`, all on the output:
    - the file exists;
    - the document text contains `Plan de producción` (cover) and `0.9`;
    - `len(doc.tables) >= 1`, ignoring cover layout tables if any;
    - `doc.inline_shapes` has at least one image.
  - `test_cross_link_italic`: there is a run with text `Arquitectura` and `italic=True`, and `"arquitectura.md"` does not appear in `word/_rels/document.xml.rels`.
  - `test_heading_font_from_brand`: the `Heading 1` style font name equals `brand.fonts["heading"]`.
  - `test_header_has_title`: `doc.sections[0].header` text contains the title.
  - `test_mermaid_missing_tools(monkeypatch)`: `shutil.which("npx")` → None. A doc with a mermaid block still builds, and its text contains the mermaid source.
- [ ] **Step 2:** Run TEST_CMD. Expected: FAIL.
- [ ] **Step 3: Implement** by porting `exportar_docx.py`. Remove `DOCUMENTOS`, `CLIENTE`, `PROYECTO`, `AUTOR`, the hardcoded colors and the logo paths.
- [ ] **Step 4:** Run TEST_CMD. Expected: pass.
- [ ] **Step 5: Commit** `feat(office-docs): markdown to Word with brands`.

---

### Task 8: New brands (from .pptx, from scratch)

**Files:**
- Create: `scripts/brand_from_pptx.py`, `scripts/new_brand.py`, `tests/test_new_brands.py`

**Interfaces:**
- Consumes: `load_brand(..., allow_draft=True)`, `Deck`, `render` (optional samples).
- Produces:
  - `@dataclass ExtractReport`:
    - `brand_dir: Path`, `layouts: list[str]`
    - `texts: list[tuple[str, str]]`, where each pair is (location like `"layout 'Title Slide' / TextBox 3"`, text)
    - `images: list[Path]`, `has_label: bool`, `samples: list[Path]`
  - `brand_from_pptx(src: Path, name: str, out_dir: Path, render_samples: bool = True) -> ExtractReport`:
    - Writes `out_dir/name/template.pptx` with **0 slides**.
    - Clears the core properties: `author`, `last_modified_by`, `title`, `subject`, `keywords`, `comments`, `category`. Also clears `Company` and `Manager` in `docProps/app.xml`.
    - A sensitivity label (`docMetadata/LabelInfo.xml`) is kept untouched, and `has_label=True` is reported.
    - Master/layout images are copied to `assets-review/`.
    - Lists every non-empty text in masters/layouts. Placeholder prompt text is included.
    - Writes a draft `brand.toml` with `draft = true` and `style = "outlined"`. It maps the theme colors as follows:
      - `primary` = dk2, `accent` = accent1, `highlight` = accent2
      - `text` = dk1, `background` = lt1, `surface` = lt2
      - `muted` = the builder's choice from the theme
    - Fonts: heading = major latin, body = minor latin.
    - Layout guesses (case-insensitive substring match):
      - `title` matches "title slide";
      - `content` matches "title and content", "title & content" or "title only";
      - `section` matches "section".
  - `confirm_brand(brand_dir: Path) -> None`. Removes the `draft` line from `brand.toml`.
  - CLI `brand_from_pptx.py SRC NAME [--out DIR] [--no-samples]`. It prints the report. A second command, `brand_from_pptx.py --confirm DIR`, confirms the brand.
  - `new_brand(name, out_dir, primary, accent, font, highlight=None, heading_font=None, logo=None, style="modern") -> Path`. Writes a valid brand that loads without `allow_draft`; the logo is copied into the folder.
  - CLI `new_brand.py NAME --primary HEX --accent HEX --font NAME [--highlight HEX] [--heading-font NAME] [--logo PATH] [--style S] [--out DIR] [--samples]`.
    - The default `--out` is `~/.mle-setup/brands`.
    - `--samples` writes a 4-slide sample deck (title, content+cards, compare, final) and a sample docx to `./NAME-samples/`.

- [ ] **Step 1: Write failing tests.** The fixture builds `client.pptx` with python-pptx:
  - 2 slides with text "Proyecto Secreto";
  - a textbox "Cliente X" added to the "Title Slide" layout;
  - core author "Ana";
  - a `docMetadata/LabelInfo.xml` injected by rewriting the zip.

  Tests:
  - `test_slides_removed_and_props_cleared`: the template has 0 slides and `core_properties.author == ""`. No part of the template zip contains "Proyecto Secreto".
  - `test_layout_text_reported`: `("Cliente X")` appears in `report.texts` with a location naming `Title Slide`.
  - `test_label_kept`: `report.has_label` is true and the template zip still has `docMetadata/LabelInfo.xml`.
  - `test_draft_blocked_until_confirm`: `load_brand(dir)` raises `BrandError`. After `confirm_brand(dir)` it loads, and `brand.layouts["title"] == "Title Slide"`.
  - `test_new_brand_loads(tmp_path)`: `new_brand("acme", tmp_path, "#112233", "445566", "Arial")` loads. `colors["primary"] == "112233"` and `fonts["body"] == "Arial"`.
  - `test_new_brand_deck_builds`: a Deck from it runs `title_slide` and `cards_row` and saves.
- [ ] **Step 2:** Run TEST_CMD. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4:** Run TEST_CMD. Expected: pass.
- [ ] **Step 5: Commit** `feat(office-docs): create brands from pptx or scratch`.

---

### Task 9: Skill, references, pointers, README

**Files:**
- Create: `skills/office-docs/SKILL.md`, `references/deck-api.md`, `references/brand-format.md`, `references/gotchas.md`
- Modify: `skills/status-update/SKILL.md` (append 1 line), `skills/handoff/SKILL.md` (append 1 line), `README.md:14` (skill list), `skills/setup-gardener/SKILL.md` (map row for brands: public `skills/office-docs/brands/neutral`, private `MLE-setup-personal/brands`, `MLE_BRANDS_PATH`)

**Content pinned by the spec:**
- `SKILL.md` frontmatter:
  - `name: office-docs`
  - `description`: Spanish and English triggers: "armá una ppt de status", "deck del proyecto", "presentación para el cliente", "pasá el plan a Word", "exportá a docx", "documentación de entrega en Word", "sumá esta ppt como plantilla", "nueva plantilla/marca". Also "Not for: spreadsheets, editing a client's existing deck, writing the content (status-update/handoff)".
  - Under 1024 chars, same style as the other MLE skill descriptions.
- Body: the process from the spec, in order:
  1. Pick the brand (ask if ambiguous).
  2. Write the content.
  3. Compose with components, dropping to primitives when needed.
  4. Build with `render.py --build`.
  5. Read the layout check output.
  6. Look at the PNGs and fix.
  7. Deliver.
- Body, continued:
  - The rule "never put client data in a brand folder".
  - The new-brand flow: show the report texts, images and samples, wait for explicit confirmation, then run `--confirm`.
  - The exact commands for each script, with `uv run`.
- `deck-api.md`: every primitive and component signature from Tasks 2–4, with one example each, plus 3 free-composition examples built only from primitives: an architecture diagram with done/planned nodes, a KPI dashboard, and a two-column narrative with an image.
- `gotchas.md`: the items listed in the spec's Intent section.
- Pointer line for status-update/handoff: `Para pasarlo a ppt o Word con la marca del cliente, usar la skill office-docs.`

- [ ] **Step 1:** Write the files.
- [ ] **Step 2: Verify discovery.**
  1. `copilot skill list` (from a fresh shell with the plugin dir) shows `office-docs`.
  2. `"$HOME/.vscode/extensions/anthropic.claude-code-2.1.304-darwin-arm64/resources/native-binary/claude" plugin validate .` passes.
  3. Every command in SKILL.md, run against the neutral brand, succeeds.
- [ ] **Step 3: Verify the example code in `deck-api.md`.** Extract the three composition examples into a temp script, run it with `render.py --build`, and check that the layout check prints `OK`.
- [ ] **Step 4:** Run TEST_CMD. Expected: pass.
- [ ] **Step 5: Commit** `feat(office-docs): skill docs and cross-references`.

---

### Task 10: Private brands and brand link (MLE-setup-personal)

**Files:**
- Create in `~/Documents/mio/MLE-setup-personal`: `brands/ai4g-modern/brand.toml`, `brands/microsoft-delivery/{brand.toml,microsoft-logo.png,microsoft-logo-blanco.png}`, `brands/ai4g-readout/` (generated)
- Modify: `bin/link-skills.sh`, `bin/link-skills.ps1`, `README.md`

**Interfaces:**
- Consumes: `brand_from_pptx`, `confirm_brand`, `load_brand`, `md2docx`, `render`.
- Produces: `~/.mle-setup/brands` as a symlink to `MLE-setup-personal/brands`. Link-skills applies the same conflict rules to it as to skill links: it is idempotent, and it exits 1 when the link points elsewhere or when a non-link exists at that path.

Brand values:
- `ai4g-modern`:
  - Style `modern` with the exact ppt_lib palette: primary 0F2B5B, accent 2870CF, highlight 50E6FF, background F4F7FB, card_border E2E8F0, text 2D3748, muted 5A6B85.
  - Fonts Segoe UI / Segoe UI / Consolas.
  - Footer `AI For Good Lab Uruguay`.
- `microsoft-delivery`:
  - Fonts Segoe UI / Segoe UI Semibold / Consolas.
  - Colors: accent 0078D4, text 262626, muted 85878B.
  - `[docx]`: heading_color 008AC8, cover_band 0072C6, code_bg F2F2F2, note_bg EFF6FC, rule BFBFBF, company `Microsoft`.
  - Logos `light = "microsoft-logo.png"`, `dark = "microsoft-logo-blanco.png"`, copied from `ute/docs/assets/`.
- `ai4g-readout`: generated from `~/Documents/Microsoft/clases/newppt.pptx`.

- [ ] **Step 1:** Write `ai4g-modern` and `microsoft-delivery`. Verify that `load_brand` loads each with `MLE_BRANDS_PATH=<personal>/brands`.
- [ ] **Step 2: Generate the readout brand.**
  1. Run `uv run .../brand_from_pptx.py ~/Documents/Microsoft/clases/newppt.pptx ai4g-readout --out <personal>/brands`.
  2. Map `deck.layouts`: `title = "Title Slide - Earth"`, `content = "Title & Content AI4G"`.
- [ ] **Step 3: USER CHECKPOINT.**
  1. Show Nicolás the report texts, the `assets-review/` images, the sample renders and the label status.
  2. Stop until he confirms that no client data remains.
  3. Then run `--confirm` and delete `assets-review/` (keep only the logos he approves).
- [ ] **Step 4: Update the link scripts.** Change `link-skills.sh`/`.ps1` to create the brands link. Run each twice: the first run reports `OK`, and the second makes no changes and reports no error. Check that `readlink ~/.mle-setup/brands` points to the brands folder. Update README with one line.
- [ ] **Step 5: Manual comparisons.** Outputs go to `/tmp/office-docs-compare/`, never to the source folders.
  - Rebuild 3 slides from the Clinicas readout with `ai4g-readout`.
  - Rebuild 3 slides from one `mayo` deck with `ai4g-modern`.
  - Export `ute/docs/plan_prod.md` with `microsoft-delivery` (copy the md and its images to /tmp first).
  - Render everything and put the PNGs next to the originals' renders. The pass criterion is "same visual family". Show Nicolás.
- [ ] **Step 6: Commit** in MLE-setup-personal: `feat: brands for office-docs and brands link`.

---

## Self-review notes

- Spec coverage: goals 1–7 map to Tasks 1–10; non-goals are untouched. Anti-goals are covered by Global Constraints, Task 8 (draft gate, label kept) and Task 10 (user checkpoint).
- Builder choices left open: neutral palette, internal helper names, the exact preset sizes and margins, and the `muted` mapping in brand_from_pptx.
