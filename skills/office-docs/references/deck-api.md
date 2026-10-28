# Deck API

Everything a build script can call. The signatures are copied from
`scripts/deck.py`, `scripts/deck_prims.py` and `scripts/deck_components.py`.
Read those files for the details.

## Setup

```python
from deck import Deck

d = Deck("neutral")          # brand name, brand folder, or a Brand object
s = d.blank_slide()
d.text(s, 0.6, 0.6, 8, 0.8, "Hola", size=28, font="heading", bold=True)
d.save("out.pptx")           # prints "layout check: ..." lines to stderr, returns the slide count
```

Run it with `uv run "$OD/scripts/render.py" out.pptx --build build_deck.py`. The
script runs from its own folder with `$OD/scripts` importable, so relative image
paths resolve against that folder. Do not call the script `deck.py` or `brand.py`,
because it would shadow the library.

- **Units:** inches, as floats. Without a template the slide is 13.333 × 7.5 in
  (16:9), and `d.W` and `d.H` hold the real size. Use them instead of literals.
- **Colors:** use a brand token (`background`, `surface`, `primary`,
  `on_primary`, `accent`, `highlight`, `text`, `muted`, `card_border`, `done`,
  `planned`) or a hex (`"E91E63"`, `"#e91e63"`). `fill=None` is transparent.
- **Fonts:** `"body"`, `"heading"` and `"mono"` map to the brand fonts. Any
  other string is a literal font name.
- **Z-order:** each shape is drawn above the ones before it. Draw backgrounds
  first, then shapes, then text.
- **Return values:** every primitive returns the python-pptx shape, so you can
  still set `.name`, `.rotation` or anything else python-pptx allows.

## Deck

| Member | What it is |
| --- | --- |
| `Deck(brand, footer=None, cwd=None)` | `footer` overrides `[deck] footer` for this deck; `cwd` is where `./brands` is searched |
| `d.W`, `d.H` | slide width and height in inches |
| `d.brand` | the loaded brand: `.colors`, `.fonts`, `.components`, `.grid`, `.logos` (name → Path), `.footer`, `.template`, `.layouts`, `.docx` |
| `d.prs` | the python-pptx `Presentation` (escape hatch) |
| `d.page` | number of slides added so far (used by `footer`) |
| `d.footer_text` | the footer in use |
| `d.color(c) -> RGBColor` | a token or hex as an `RGBColor`; raises `ValueError` otherwise |
| `d.font(role) -> str` | a font name for `body`, `heading`, `mono`, or the string itself |
| `d.col(start, span=1) -> (x, w)` | x and width of grid columns `[start, start+span)`, 0-based, 12 columns by default |
| `d.layout(role)` | the template layout mapped to `role` in `[deck.layouts]`, or `None` |
| `d.blank_slide(bg=None) -> Slide` | an empty slide; `bg=None` uses `components.content_bg` (with a template, the master's background) |
| `d.notes(slide, text)` | sets the speaker notes |
| `d.save(path) -> int` | writes the .pptx, prints the layout check, returns the slide count |

```python
x, w = d.col(0, 6)                       # left half
d.notes(s, "Qué decir en esta slide.")
```

CLI: `uv run "$OD/scripts/deck.py" check FILE.pptx` prints one issue per line,
or `OK`. It always exits 0.

## Primitives

Each example below assumes `d` and a slide `s`.

**`rect(s, x, y, w, h, fill="surface", line=None, line_w=1.0, dash=False, radius=None, opacity=None)`**:
a rectangle. `radius` (0–0.5, a fraction of the short side) makes it rounded,
and `opacity` is 0–100.
```python
d.rect(s, 0.6, 1.8, 4, 2.5, fill="surface", line="card_border", radius=0.06)
```

**`oval(s, x, y, w, h, fill="accent", line=None)`**
```python
d.oval(s, 5.0, 1.8, 0.6, 0.6, fill="highlight")
```

**`line(s, x1, y1, x2, y2, color="muted", width=1.5, dash=False, arrow_end=False)`**:
a straight connector. `arrow_end` puts an arrowhead at `(x2, y2)`.
```python
d.line(s, 4.7, 3.0, 6.2, 3.0, color="muted", width=1.75, arrow_end=True)
```

**`arrow(s, x, y, w, h, color="accent", direction="right")`**: a block arrow.
`direction` is right, left, up or down.
```python
d.arrow(s, 6.4, 2.9, 0.8, 0.25, direction="right")
```

**`text(s, x, y, w, h, content, size=14, color="text", font="body", bold=False, italic=False, align="left", anchor="top", line_spacing=1.05)`**:
a text box. `content` can be:
- a string, where `\n` splits paragraphs;
- a list of paragraphs, where each paragraph is a string or a list of runs, and
  each run is a string or a dict with the keys `text`, `size`, `color`, `bold`,
  `italic` and `font`.

`align` is left, center, right or justify. `anchor` is top, middle or bottom.
```python
d.text(s, 0.6, 4.6, 6, 0.9, [
    ["Ahorro de ", {"text": "16 h/semana", "bold": True, "color": "accent"}],
    [{"text": "estimado sobre el proceso actual", "size": 11, "color": "muted"}],
], size=18)
```

**`bullets(s, x, y, w, h, items, size=15, marker_color="highlight", spread=True, lead_color="primary")`**:
- `"Lead: rest"` makes the lead bold in `lead_color`.
- An item that starts with two spaces is a sub-bullet.
- `spread` spaces the items out to fill the height.
```python
d.bullets(s, 7.4, 1.8, 5.3, 2.6, ["Datos: ingesta diaria", "  sin nulos desde marzo", "Modelo: MAPE 8,4 %"])
```

**`chip(s, x, y, label, fill="accent", color="on_primary", size=9, w=None, h=0.26)`**:
a pill label. `w=None` sizes it from the text.
```python
d.chip(s, 0.6, 5.7, "EN PRODUCCIÓN", fill="done")
```

**`image(s, path, x, y, w, h, fit="contain", caption=None, frame=False, caption_color="muted")`**:
- `fit` is `contain` (whole image, centered), `cover` (cropped to fill) or `stretch`.
- A caption takes the bottom 0.45 in of the box.
- `.webp` raises `ValueError`; convert it to PNG first. GIFs stay animated.
```python
d.image(s, "photo.png", 7.4, 4.6, 2.6, 1.9, fit="cover", frame=True)
```

**`icon(s, path, x, y, size=0.5)`**: an image contain-fitted in a square.
```python
d.icon(s, "photo.png", 10.3, 4.6, size=0.5)
```

**`scrim(s, x, y, w, h, color, opacity)`**: a semi-transparent rectangle
(opacity 0–100) that dims what is behind it, for example text over a photo.
```python
d.scrim(s, 7.4, 4.6, 2.6, 1.9, "primary", 45)
```

**`gradient(s, x, y, w, h, color, a0, a1, angle=0)`**: a rectangle whose
opacity fades from `a0` to `a1` (0–100). `angle=0` runs left to right and
`angle=90` runs top to bottom.
```python
d.gradient(s, 7.4, 5.4, 2.6, 1.1, "primary", 0, 85, angle=90)
```

**`table(s, x, y, w, rows, header=True, col_widths=None, size=12)`**: a native,
editable table. `rows` is a list of equal-length lists, and the first row is
the header when `header=True`.
```python
d.table(s, 10.3, 1.8, 2.4, [["Frente", "%"], ["Datos", "100"], ["Modelo", "80"]], col_widths=[1.6, 0.8], size=11)
```

## Slide factories

Without a template, these slides are drawn in the brand's style. With a
template brand, `title`, `section`, `content` and `final` use the layouts
mapped in `[deck.layouts]` and fill their placeholders. Unmapped roles are
drawn.

| Call | Returns |
| --- | --- |
| `d.title_slide(kicker, title, subtitle)` | slide |
| `d.section_slide(number, title, image=None, caption=None, kicker="SECCIÓN")` | slide. `number` is a string, and the kicker reads `{kicker} {number}` (`kicker="PART"` gives `PART 02`). An `image` replaces the big number; on a template layout it goes behind the layout's text. |
| `d.content_slide(kicker, title)` | `(slide, top)`: a header plus a footer with the page number; `top` is where the body starts |
| `d.final_slide(title, subtitle)` | slide |
| `d.image_slide(kicker, title, path, caption=None)` | slide: a content slide with one large framed image |

```python
d.title_slide("Sprint 6", "Estado del proyecto", "Revisión con el cliente")
d.section_slide("02", "Resultados")
d.section_slide("03", "Next steps", kicker="PART")
s, top = d.content_slide("Avance", "Lo que cambió esta semana")
d.final_slide("Gracias", "Preguntas")
d.image_slide("Evidencia", "Pronóstico vs. real", "photo.png", caption="Semana 42")
```

**`header(s, kicker, title, lead=None) -> top`** and **`footer(s, page=None)`**
draw the content-slide header and footer on any slide, for example on a
`blank_slide()` you compose freely. The title shape is named `"title"`.
```python
s = d.blank_slide()
top = d.header(s, "Contexto", "Por qué ahora", lead="Tres señales en el último trimestre.")
d.footer(s)
```

## Components

They draw full-width rows inside the margins, starting at `top`, which usually
comes from `content_slide` or `header`. An empty list raises
`ZeroDivisionError` in `cards_row`, `stat_row`, `timeline`, `chain`,
`numbered_grid` and `image_row`, so pass at least one item. `maprow`,
`compare` and `code_block` accept empty lists and draw no items.

`cards_row`, `compare` and `code_block` take `valign`:
- `"bias"` (the default) moves the block down by 30% of the free space below
  it, so a lone block sits a bit lower than `top`.
- `"top"` starts the block exactly at `top`. Use it to stack blocks.

All three return the y below the block, so the next block can start there.

**`cards_row(s, top, cards, height=3.2, valign="bias") -> y`**: the items are
`{title, lines, accent?, tag?, icon?}`. The style comes from
`components.card` and `components.accent_strip`.
```python
d.cards_row(s, top, [
    {"title": "Datos", "lines": ["Ingesta diaria", "Sin nulos"], "tag": "listo"},
    {"title": "Modelo", "lines": ["MAPE 8,4 %"], "accent": "done"},
    {"title": "API", "lines": ["En diseño"], "accent": "planned", "icon": "photo.png"},
])
```

**Stacking rows:** pass `valign="top"` and start each row at the y the
previous one returned. With the default `"bias"`, each row moves down as if it
were alone on the slide, and the rows overlap.
```python
s, top = d.content_slide("Plan", "Dos frentes")
y = d.cards_row(s, top, [{"title": "Datos", "lines": ["Ingesta diaria"]},
                         {"title": "Modelo", "lines": ["MAPE 8,4 %"]}], height=2.0, valign="top")
d.cards_row(s, y + 0.3, [{"title": "API", "lines": ["En diseño"]},
                         {"title": "Monitoreo", "lines": ["Drift"]}], height=2.0, valign="top")
```

**`stat_row(s, top, stats)`**: big numbers on `primary` panels. The items are
`{big, cap}`.
```python
d.stat_row(s, top, [{"big": "8,4 %", "cap": "MAPE semanal"}, {"big": "48", "cap": "tiendas"}])
```

**`compare(s, top, ltitle, litems, rtitle, ritems, valign="bias") -> y`**: a
neutral "before" on the left and a highlighted "after" on the right. The
panels are 3.7 in tall.
```python
d.compare(s, top, "Hoy", ["Planillas a mano", "2 días"], "Con el modelo", ["Automático", "2 horas"])
```

**`timeline(s, top, steps, box_h=2.5)`**: numbered steps. Each step is `{t, a}`
(a title and an annotation such as a date).
```python
d.timeline(s, top + 0.4, [{"t": "Datos", "a": "Sem 1-2"}, {"t": "Modelo", "a": "Sem 3-5"}, {"t": "Piloto", "a": "Sem 6"}])
```

**`chain(s, x, y, w, h, steps, accent="accent", size=12)`**: boxes joined by
arrows. Each step is `{t, a?}`. You choose the position.
```python
d.chain(s, 0.6, 2.0, 12.1, 1.1, [{"t": "ERP", "a": "diario"}, {"t": "Features"}, {"t": "Forecast"}])
```

**`maprow(s, top, rows) -> y`**: rows of «chip → lead and text». Each row is
`(chip, lead, rest)`. Returns the y below the last row.
```python
y = d.maprow(s, top, [("Ventas", "Forecast semanal", "por tienda y SKU"), ("Compras", "Sugerido", "")])
```

**`numbered_grid(s, top, items, height=None)`**: two columns of numbered
items. Each item is `(num, label)`, and both are strings.
```python
d.numbered_grid(s, top, [("1", "Acceso a datos"), ("2", "Validar métricas"), ("3", "Piloto"), ("4", "Rollout")])
```

**`code_block(s, top, lines, height=3.6, note=None, valign="bias") -> y`**:
monospaced lines on a `primary` panel. Lines that start with `"# "` are
highlighted. The returned y is below the note when there is one.
```python
d.code_block(s, top, ["# entrenar", "uv run train.py --cfg prod.toml"], height=1.6, note="Corre cada lunes.")
```

**`image_row(s, top, items, height=None)`**: images scaled to one common
height so their captions line up. The items are `{path, caption?}`.
```python
d.image_row(s, top, [{"path": "photo.png", "caption": "Antes"}, {"path": "photo.png", "caption": "Después"}])
```

**`split_image(s, top, path, items, side="right", ratio=0.4, caption=None)`**:
bullets on one side and an image on the other. `ratio` is the image's share of
the width.
```python
d.split_image(s, top, "photo.png", ["Contexto: tres planillas", "Dolor: dos días"], side="right", ratio=0.45)
```

## Diagram pieces

**`node(s, x, y, w, h, label, sub=None, accent="accent", state="done", shape=None) -> box`**:
- `state` is `"done"` or `"planned"`; planned has a dashed border and a dimmer fill.
- `shape` is `rounded` or `rect` and defaults to `components.node_shape`.

**`labeled_arrow(s, x, y, w, label=None, color="accent")`**: a right arrow
from `x` to `x + w` at height `y`, with a small label above it.

**`container(s, x, y, w, h, label)`**: a grouping box. Draw it before the
nodes that go inside it.

**`legend(s, x, y, items=None)`**: a key for the node states. It defaults to
`[("Hecho", "done"), ("Planeado", "planned")]`.

```python
d.container(s, 0.6, 1.9, 8.2, 2.4, "Nube del cliente")
d.node(s, 1.0, 2.6, 2.0, 1.0, "Ingesta", "nocturna")
d.labeled_arrow(s, 3.1, 3.0, 1.0, "diario")
d.node(s, 4.2, 2.6, 2.0, 1.0, "API", "REST", state="planned")
d.legend(s, 0.6, 4.5)
```

## Composing freely

The components above are only shortcuts. A slide can be any arrangement of
primitives: one `blank_slide()` plus rects, lines, text and images placed
wherever the idea needs them. Use this path whenever the slide you picture is
not a component, for example a custom diagram, a dashboard, a cover photo with
a scrim, a 2×2 matrix, a funnel or a before/after with real numbers.

- **Place things on the grid.** `x, w = d.col(start, span)` keeps edges
  aligned across slides. `m = d.brand.grid["margin"]` and `d.W - 2 * m` give
  the usable width.
- **Mix freely.** `content_slide` gives you a header and a footer, and
  `top` is where your own drawing starts. `header()` and `footer()` work on a
  blank slide too.
- **Text on shapes:** draw the shape first, then a `text` box over it with
  `anchor="middle"`. The layout check flags `covered` when a filled shape or
  a picture drawn *after* a text box crosses it, because it hides part of the
  text. A shape drawn before the text (a background) or one that fully
  contains the text box (a scrim) is fine. Leave a few hundredths of an inch
  between text boxes that sit next to each other, because exactly touching
  boxes can flag as an overlap.
- **Titles:** name your own title shape `"title"` (`d.text(...).name = "title"`)
  so the check warns when it runs past 55 characters.
- **Colors:** tokens keep the slide on-brand under any `--brand`, while a hex
  is fixed. Use `on_primary` for text on `primary` or `accent` fills.
- **Logos** are not placed automatically. Draw one with
  `d.image(s, d.brand.logos["light"], x, y, w, h)`. Check
  `"light" in d.brand.logos` first, because the neutral brand has none.
- **Charts:** for a few bars, use rects (example 2), which are easy to style.
  For real data, a native, editable chart works through python-pptx:
  ```python
  from pptx.chart.data import CategoryChartData
  from pptx.enum.chart import XL_CHART_TYPE
  from pptx.util import Inches

  data = CategoryChartData()
  data.categories = ["S1", "S2", "S3"]
  data.add_series("MAPE", (14.2, 11.5, 8.4))
  gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.6), Inches(1.8), Inches(6), Inches(3.5), data)
  series = gf.chart.plots[0].series[0]
  series.format.fill.solid()
  series.format.fill.fore_color.rgb = d.color("accent")
  ```
- **Beyond the primitives:** any python-pptx call works on `s` or `d.prs`, for
  example `shape.rotation = 15`, the other `MSO_SHAPE` autoshapes through
  `s.shapes.add_shape`, or a group with `g = s.shapes.add_group_shape()`
  followed by `d.rect(g, ...)` and `d.text(g, ...)`. The layout check only
  approximates rotated shapes and groups.

The three examples below use only primitives and tokens. Each one runs as is
with `render.py --build`, and the layout check prints `OK` for each.

### Example 1: architecture diagram with done and planned nodes

```python
from deck import Deck

d = Deck("neutral")
s = d.blank_slide()
m = d.brand.grid["margin"]
W = d.W - 2 * m

# Header drawn by hand: kicker, title (named "title" so the check measures its length), rule.
d.text(s, m, 0.45, W, 0.3, "ARQUITECTURA", size=12, color="accent", font="heading", bold=True)
d.text(s, m, 0.78, W, 0.6, "Del dato crudo a la predicción", size=28, color="primary",
       font="heading", bold=True).name = "title"
d.rect(s, m, 1.45, 0.9, 0.07, fill="highlight")


def node(x, y, w, h, label, sub, planned=False):
    """Done: solid accent border. Planned: dashed border, dimmer fill, muted text."""
    d.rect(s, x, y, w, h, fill="background" if planned else "surface",
           line="planned" if planned else "accent", line_w=1.5, dash=planned, radius=0.12)
    d.text(s, x + 0.1, y, w - 0.2, h, [
        [{"text": label, "bold": True, "font": "heading", "color": "muted" if planned else "primary"}],
        [{"text": sub, "size": 10, "color": "muted"}],
    ], size=14, align="center", anchor="middle")


# Container (grouping box) with its label, then the nodes on top of it.
cx, cy, cw, ch = m, 1.9, W, 4.3
d.rect(s, cx, cy, cw, ch, fill=None, line="card_border", line_w=1.0, radius=0.04)
d.text(s, cx + 0.25, cy + 0.15, 3.0, 0.3, "Nube del cliente", size=10, color="muted", bold=True)

nw, nh, gap = 2.3, 1.3, 0.75
y = cy + 0.7
steps = [("Fuentes", "ERP + CSV diarios", False), ("Ingesta", "pipeline nocturno", False),
         ("Modelo", "forecast semanal", False), ("API", "REST para el BI", True)]
x0 = cx + (cw - 4 * nw - 3 * gap) / 2
for i, (label, sub, planned) in enumerate(steps):
    x = x0 + i * (nw + gap)
    node(x, y, nw, nh, label, sub, planned)
    if i < len(steps) - 1:
        d.line(s, x + nw + 0.08, y + nh / 2, x + nw + gap - 0.08, y + nh / 2, color="muted", width=1.75,
               arrow_end=True)

# A planned branch below the model, with a dashed connector and a chip.
mx = x0 + 2 * (nw + gap)
node(mx, y + nh + 0.9, nw, 0.9, "Monitoreo", "drift y alertas", planned=True)
d.line(s, mx + nw / 2, y + nh, mx + nw / 2, y + nh + 0.9, color="planned", width=1.5, dash=True, arrow_end=True)
d.chip(s, x0, y + nh + 1.22, "MVP en producción", fill="done")

# Legend.
ly = cy + ch + 0.3
for i, (label, planned) in enumerate([("Hecho", False), ("Planeado", True)]):
    lx = m + i * 1.7
    d.rect(s, lx, ly + 0.03, 0.3, 0.2, fill="background" if planned else "surface",
           line="planned" if planned else "accent", line_w=1.5, dash=planned, radius=0.2)
    d.text(s, lx + 0.4, ly, 1.1, 0.26, label, size=11, color="text")

d.notes(s, "Hoy funciona de punta a punta hasta el modelo; la API y el monitoreo son la próxima etapa.")
d.save("arch.pptx")
```

### Example 2: KPI dashboard

```python
from deck import Deck

d = Deck("neutral")
s = d.blank_slide()
m = d.brand.grid["margin"]
W = d.W - 2 * m

d.text(s, m, 0.45, W, 0.3, "SPRINT 6 · ESTADO", size=12, color="accent", font="heading", bold=True)
d.text(s, m, 0.78, W, 0.6, "El modelo ya supera al baseline", size=28, color="primary",
       font="heading", bold=True).name = "title"

# Four KPI cards on the 12-column grid (3 columns each).
kpis = [("MAPE", "8,4 %", "−3,1 pp", "done"), ("Cobertura", "92 %", "+12 %", "done"),
        ("Latencia p95", "340 ms", "+40 ms", "planned"), ("Tiendas", "48 / 60", "en curso", "accent")]
top, h = 1.7, 1.75
for i, (label, value, delta, tone) in enumerate(kpis):
    x, w = d.col(3 * i, 3)
    d.rect(s, x, top, w, h, fill="surface", line="card_border", radius=0.06)
    d.rect(s, x, top, 0.08, h, fill=tone)
    d.text(s, x + 0.3, top + 0.2, w - 0.5, 0.3, label.upper(), size=11, color="muted", font="heading", bold=True)
    d.text(s, x + 0.3, top + 0.55, w - 0.5, 0.7, value, size=34, color="primary", font="heading", bold=True)
    d.chip(s, x + 0.3, top + 1.32, delta, fill=tone, size=10)

# Bar chart from rects: weekly error. The dashed baseline is drawn first, so the bars cover it.
cx, cw = d.col(0, 7)
cy, chh = 3.85, 2.55
d.text(s, cx, cy, cw, 0.3, "Error semanal (MAPE %)", size=12, color="text", font="heading", bold=True)
values = [14.2, 12.8, 11.5, 10.9, 9.6, 8.4]
base_y, plot_h, vmax = cy + chh, chh - 0.55, 15
by = base_y - plot_h * 12 / vmax
d.line(s, cx, by, cx + cw, by, color="planned", width=1.25, dash=True)
d.text(s, cx + cw - 1.6, by - 0.3, 1.6, 0.25, "baseline 12,0", size=10, color="planned", bold=True, align="right")
bw = (cw - 0.2) / len(values)
for i, v in enumerate(values):
    bh = plot_h * v / vmax
    bx = cx + 0.1 + i * bw
    d.rect(s, bx + 0.12, base_y - bh, bw - 0.24, bh, fill="accent" if i == len(values) - 1 else "highlight")
    d.text(s, bx + 0.05, base_y - bh + 0.08, bw - 0.1, 0.25, f"{v:.1f}".replace(".", ","), size=11,
           color="on_primary", bold=True, align="center")
d.line(s, cx, base_y, cx + cw, base_y, color="card_border", width=1.0)

# Progress bars: track + fill + label + value.
px, pw = d.col(8, 4)
d.text(s, px, cy, pw, 0.3, "Avance por frente", size=12, color="text", font="heading", bold=True)
for i, (label, pct) in enumerate([("Datos", 1.0), ("Modelo", 0.8), ("API", 0.35), ("Monitoreo", 0.1)]):
    y = cy + 0.55 + i * 0.5
    d.text(s, px, y, pw - 0.7, 0.25, label, size=11)
    d.text(s, px + pw - 0.6, y, 0.6, 0.25, f"{pct:.0%}", size=11, color="muted", bold=True, align="right")
    d.rect(s, px, y + 0.29, pw, 0.1, fill="card_border", radius=0.5)
    d.rect(s, px, y + 0.29, max(pw * pct, 0.1), 0.1, fill="done" if pct == 1 else "accent", radius=0.5)

d.text(s, m, d.H - 0.55, W, 0.25, "Fuente: backtesting sobre las últimas seis semanas.", size=9, color="muted")
d.save("kpis.pptx")
```

### Example 3: two-column narrative with an image

```python
from pathlib import Path

from deck import Deck

PHOTO = Path("photo.png")
if not PHOTO.exists():  # placeholder so the example runs as is; use your own image instead
    import pymupdf

    w, h = 480, 360
    px = bytes(c for y in range(h) for x in range(w) for c in (30 + 120 * x // w, 80 + 90 * y // h, 110))
    pymupdf.Pixmap(pymupdf.csRGB, w, h, px, False).save(str(PHOTO))

d = Deck("neutral")
s = d.blank_slide()
m = d.brand.grid["margin"]

# Left: the story (columns 0-5). Right: a full-height image (columns 7-11) bleeding to the slide edge.
lx, lw = d.col(0, 6)
d.text(s, lx, 0.9, lw, 0.3, "EL PROBLEMA", size=12, color="accent", font="heading", bold=True)
d.text(s, lx, 1.25, lw, 1.3, "Cada lunes, tres personas arman el pronóstico a mano",
       size=30, color="primary", font="heading", bold=True, line_spacing=1.0).name = "title"
d.text(s, lx, 2.85, lw, 1.2, [
    ["El equipo de planificación cruza ", {"text": "cuatro planillas", "bold": True},
     " y tarda ", {"text": "dos días", "bold": True, "color": "accent"}, " en tener una cifra."],
    ["Cuando llega, la semana ya empezó."],
], size=16, line_spacing=1.15)
d.bullets(s, lx, 4.35, lw, 1.9, [
    "Costo: 16 horas-persona por semana",
    "Riesgo: errores de copia sin trazabilidad",
    "Oportunidad: los datos ya están en el ERP",
], size=14)

ix, _ = d.col(7, 5)
iw, ih = d.W - ix, d.H
d.image(s, PHOTO, ix, 0, iw, ih, fit="cover")
d.gradient(s, ix, ih - 2.4, iw, 2.4, "primary", 0, 85, angle=90)  # transparent at top -> dark at the bottom
d.chip(s, ix + 0.4, 0.4, "ANTES", fill="planned")
d.text(s, ix + 0.4, ih - 1.25, iw - 0.8, 0.8, [
    [{"text": "2 días", "size": 30, "bold": True, "font": "heading", "color": "on_primary"}],
    [{"text": "de la exportación del ERP al pronóstico", "size": 12, "color": "on_primary"}],
])

d.save("story.pptx")
```
