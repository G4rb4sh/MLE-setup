# /// script
# requires-python = ">=3.11"
# dependencies = ["python-pptx", "python-docx", "pymupdf"]
# ///
"""Create a brand folder from a few parameters.

    folder = new_brand("acme", Path("brands"), primary="0F2B5B", accent="#2870cf", font="Inter")

CLI: `uv run new_brand.py NAME --primary HEX --accent HEX --font NAME [--highlight HEX]
[--heading-font NAME] [--logo PATH] [--style modern|outlined|dark] [--out DIR] [--samples]`.
Default `--out` is ~/.mle-setup/brands. `--samples` also writes a 4-slide sample deck and a
sample document to ./NAME-samples/ to show the user before using the brand.

Only primary, accent, highlight and on_primary are written; every other token comes from the
style preset. Without --highlight it is the accent lightened (or darkened, for a light primary)
so it stands out on primary; on_primary is white or the preset text color, whichever contrasts
more with primary. The toml writer here (`dump_toml`) is shared with brand_from_pptx.py.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

from brand import STYLE_PRESETS, Brand, BrandError, load_brand, normalize_hex

DEFAULT_OUT = Path("~/.mle-setup/brands")
WHITE, BLACK = "FFFFFF", "000000"
HIGHLIGHT_MIX = 0.4  # how far the derived highlight moves from accent toward white/black
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


# ── colors ──
def mix(a: str, b: str, t: float) -> str:
    """Hex between `a` (t=0) and `b` (t=1)."""
    ca, cb = (bytes.fromhex(x) for x in (a, b))
    return "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(ca, cb, strict=True))


def luminance(c: str) -> float:
    """WCAG relative luminance of a 6-digit hex."""
    ch = [v / 255 for v in bytes.fromhex(c)]
    r, g, b = (v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in ch)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    lo, hi = sorted((luminance(a), luminance(b)))
    return (hi + 0.05) / (lo + 0.05)


def best_contrast(bg: str, *candidates: str) -> str:
    """The candidate that stands out most on `bg` (first wins ties)."""
    return max(candidates, key=lambda c: contrast(bg, c))


# ── brand.toml writing ──
def toml_value(v: object) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int | float):
        return repr(v)
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)  # JSON string escapes are valid TOML basic strings
    raise TypeError(f"cannot write {type(v).__name__} to brand.toml")


def dump_toml(data: dict, header: str = "") -> str:
    """Nested dicts of str/bool/number -> TOML text; `header` lines become comments on top."""
    lines = [f"# {ln}".rstrip() for ln in header.splitlines()]

    def table(d: dict, path: list[str]) -> None:
        scalars = {k: v for k, v in d.items() if not isinstance(v, dict)}
        if path:
            lines.extend(["", "[" + ".".join(path) + "]"])
        lines.extend(f"{k} = {toml_value(v)}" for k, v in scalars.items())
        for k, v in d.items():
            if isinstance(v, dict):
                table(v, [*path, k])

    table(data, [])
    return "\n".join(lines).lstrip("\n") + "\n"


def check_name(name: str) -> None:
    if not _NAME.fullmatch(name or ""):
        raise BrandError(f"brand name {name!r}: use letters, digits, '.', '_' or '-' (it is a folder name)")


def brand_folder(out_dir: Path, name: str) -> Path:
    """`out_dir/name`, refusing to overwrite an existing brand."""
    check_name(name)
    folder = Path(out_dir).expanduser() / name
    if (folder / "brand.toml").exists():
        raise BrandError(f"{folder / 'brand.toml'} already exists; pick another name or delete that folder")
    return folder


# ── new brand ──
def new_brand(name: str, out_dir: Path, primary: str, accent: str, font: str, highlight: str | None = None,
              heading_font: str | None = None, logo: Path | None = None, style: str = "modern") -> Path:
    """Write `out_dir/name/brand.toml` (+ the logo); return the folder. The brand loads as is (no draft)."""
    if style not in STYLE_PRESETS:
        raise BrandError(f"style {style!r} unknown; valid: {', '.join(STYLE_PRESETS)}")
    if not font or not font.strip():
        raise BrandError("font: a font name is required")
    preset = STYLE_PRESETS[style]["colors"]
    primary = normalize_hex(primary, "primary")
    accent = normalize_hex(accent, "accent")
    on_primary = best_contrast(primary, WHITE, preset["text"])
    if highlight is None:
        highlight = mix(accent, WHITE if on_primary == WHITE else BLACK, HIGHLIGHT_MIX)
    colors = {"primary": primary, "on_primary": on_primary, "accent": accent,
              "highlight": normalize_hex(highlight, "highlight")}
    if preset["card_border"] == preset["accent"]:  # the preset outlines cards in its accent: keep that link
        colors["card_border"] = accent
    if logo is not None and not Path(logo).expanduser().is_file():
        raise BrandError(f"logo: file not found: {logo}")
    folder = brand_folder(out_dir, name)

    data: dict = {"name": name, "description": "", "style": style, "colors": colors,
                  "fonts": {"body": font.strip(), "heading": (heading_font or font).strip()}}
    folder.mkdir(parents=True, exist_ok=True)
    if logo is not None:
        logo = Path(logo).expanduser()
        target = f"logo{logo.suffix.lower()}"
        shutil.copyfile(logo, folder / target)
        data["logos"] = {"light": target}
    header = (f"Brand {name!r}, created by new_brand.py. Tokens not listed here come from the "
              f"{style!r} style preset;\nadd them under [colors] to override (see brands/neutral/brand.toml).")
    (folder / "brand.toml").write_text(dump_toml(data, header), encoding="utf-8")
    load_brand(folder)  # fail now, not at first use
    return folder


# ── samples ──
SAMPLE_MD = """\
---
title: Documento de ejemplo
subtitle: Muestra de la marca
---

# Contexto

Este documento muestra títulos, texto, una tabla, una cita y código con la marca.

> **Nota:** el contenido es de ejemplo.

## Estado

| Componente | Estado |
|------------|--------|
| Datos      | Listo  |
| Modelo     | En curso |

## Código

```python
print("hola")
```
"""


def sample_deck(brand: Brand, out: Path) -> Path:
    """Write a 4-slide sample deck to `out`."""
    from deck import Deck

    d = Deck(brand)
    sample_slides(d)
    out.parent.mkdir(parents=True, exist_ok=True)
    d.save(out)
    return out


def sample_slides(d) -> None:
    """Title, content + cards, compare and final slides on Deck `d`: enough to judge colors and fonts."""
    d.title_slide("Muestra", f"Marca {d.brand.name}", "Deck de ejemplo")
    s, top = d.content_slide("Contenido", "Tres tarjetas")
    d.cards_row(s, top, [{"title": t, "lines": ["Primera línea", "Segunda línea"]}
                         for t in ("Uno", "Dos", "Tres")])
    s, top = d.content_slide("Comparación", "Antes y después")
    d.compare(s, top, "Antes", ["Proceso manual", "Sin métricas"], "Después", ["Automático", "Medido"])
    d.final_slide("Gracias", "Preguntas")


def _sample_docx(brand: Brand, folder: Path) -> Path | None:
    """Sample .docx via md2docx; None (with a warning) when pandoc is missing."""
    from md2docx import build_docx

    md = folder / f"{brand.name}-sample.md"
    md.write_text(SAMPLE_MD, encoding="utf-8")
    try:
        return build_docx(md, brand, folder / f"{brand.name}-sample.docx", use_word=False)
    except RuntimeError as e:
        print(f"sample document skipped: {e}", file=sys.stderr)
        return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="new_brand.py", description="Create a brand folder from parameters.")
    ap.add_argument("name")
    ap.add_argument("--primary", required=True, metavar="HEX", help="titles, dark panels, cover band")
    ap.add_argument("--accent", required=True, metavar="HEX", help="card strips, markers, links")
    ap.add_argument("--font", required=True, metavar="NAME", help="body font (and headings by default)")
    ap.add_argument("--highlight", metavar="HEX", help="kickers on primary (default: derived from accent)")
    ap.add_argument("--heading-font", metavar="NAME")
    ap.add_argument("--logo", metavar="PATH", help="logo for light backgrounds, copied into the folder")
    ap.add_argument("--style", default="modern", choices=list(STYLE_PRESETS))
    ap.add_argument("--out", default=str(DEFAULT_OUT), metavar="DIR", help=f"default: {DEFAULT_OUT}")
    ap.add_argument("--samples", action="store_true", help="write a sample deck and document to ./NAME-samples/")
    args = ap.parse_args(argv)
    try:
        folder = new_brand(args.name, Path(args.out), args.primary, args.accent, args.font,
                           highlight=args.highlight, heading_font=args.heading_font,
                           logo=Path(args.logo) if args.logo else None, style=args.style)
        print(folder)
        if args.samples:
            brand = load_brand(folder)
            samples = Path.cwd() / f"{args.name}-samples"
            print(sample_deck(brand, samples / f"{args.name}-sample.pptx"))
            docx = _sample_docx(brand, samples)
            if docx:
                print(docx)
    except (BrandError, ValueError, OSError) as e:
        print(f"new_brand failed: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
