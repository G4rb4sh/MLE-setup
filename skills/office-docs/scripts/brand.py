"""Brand loading: find a brand folder, read brand.toml, merge it over a style preset.

A brand is a folder with `brand.toml` plus optional assets (logos, template.pptx,
reference.docx). Every color, font and company name used by decks and documents
comes from here; scripts never hardcode them.
"""

from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

COLOR_TOKENS = (
    "background", "surface", "primary", "on_primary", "accent", "highlight",
    "text", "muted", "card_border", "done", "planned",
)

CARD_KINDS = ("filled", "outlined", "dark")
ACCENT_STRIPS = ("top", "left", None)
NODE_SHAPES = ("rounded", "rect")

STYLE_PRESETS: dict[str, dict] = {
    # ppt_lib: navy titles, filled white cards with a colored top strip, cyan highlights.
    "modern": {
        "colors": {
            "background": "F4F7FB", "surface": "FFFFFF", "primary": "0F2B5B",
            "on_primary": "FFFFFF", "accent": "2870CF", "highlight": "50E6FF",
            "text": "2D3748", "muted": "5A6B85", "card_border": "E2E8F0",
            "done": "3BBBA6", "planned": "FF7043",
        },
        "components": {
            "card": "filled", "radius": 0.06, "accent_strip": "top",
            "content_bg": "background", "node_shape": "rounded",
        },
    },
    # Sprint readout: white slides, light grey cards outlined in the accent color.
    "outlined": {
        "colors": {
            "background": "FFFFFF", "surface": "F2F2F2", "primary": "156082",
            "on_primary": "FFFFFF", "accent": "0078D4", "highlight": "3BBBA6",
            "text": "000000", "muted": "595959", "card_border": "0078D4",
            "done": "3BBBA6", "planned": "8A8A8A",
        },
        "components": {
            "card": "outlined", "radius": 0.08, "accent_strip": "left",
            "content_bg": "background", "node_shape": "rect",
        },
    },
    # Ceibal: dark navy background, dark cards, cyan/teal accents, rounded nodes.
    "dark": {
        "colors": {
            "background": "1E2438", "surface": "252C40", "primary": "1A2035",
            "on_primary": "FFFFFF", "accent": "00BCD4", "highlight": "1DE9B6",
            "text": "D0D6E8", "muted": "8891AA", "card_border": "2E3756",
            "done": "00BCD4", "planned": "FF7043",
        },
        "components": {
            "card": "dark", "radius": 0.10, "accent_strip": None,
            "content_bg": "background", "node_shape": "rounded",
        },
    },
}

GRID_DEFAULTS = {"margin": 0.6, "columns": 12.0, "gutter": 0.2}
DOCX_COLOR_KEYS = ("cover_band", "heading_color", "code_bg", "note_bg", "rule")

PLUGIN_BRANDS = Path(__file__).resolve().parent.parent / "brands"

_HEX = re.compile(r"[0-9A-Fa-f]{6}")


class BrandError(Exception):
    pass


class BrandNotFound(BrandError):
    pass


@dataclass(frozen=True)
class Brand:
    name: str
    root: Path
    description: str
    style: str
    colors: dict[str, str]
    components: dict
    fonts: dict[str, str]
    logos: dict[str, Path]
    footer: str
    template: Path | None
    layouts: dict[str, str]
    grid: dict[str, float]
    docx: dict
    draft: bool


def normalize_hex(value: str, key: str) -> str:
    """'#2870cf' -> '2870CF'; anything else that is not 6 hex digits raises BrandError naming `key`."""
    s = value.strip().removeprefix("#") if isinstance(value, str) else ""
    if not _HEX.fullmatch(s):
        raise BrandError(f"{key}: invalid hex color {value!r} (expected 6 hex digits, e.g. 2870CF)")
    return s.upper()


def brand_search_path(cwd: Path | None = None) -> list[Path]:
    """Where `--brand NAME` is looked up, in priority order."""
    dirs = [Path(cwd or Path.cwd()) / "brands"]
    dirs += [Path(p).expanduser() for p in os.environ.get("MLE_BRANDS_PATH", "").split(os.pathsep) if p]
    dirs += [Path.home() / ".mle-setup" / "brands", PLUGIN_BRANDS]
    return dirs


def find_brand(name: str, cwd: Path | None = None) -> Path:
    dirs = brand_search_path(cwd)
    for d in dirs:
        if (d / name / "brand.toml").is_file():
            return d / name
    listed = "\n".join(f"  {d}" for d in dirs)
    raise BrandNotFound(f"brand {name!r} not found (no {name}/brand.toml) in:\n{listed}")


def _resolve_folder(name_or_path: str | Path, cwd: Path | None) -> Path:
    if isinstance(name_or_path, Path) or "/" in name_or_path or os.sep in name_or_path:
        p = Path(name_or_path).expanduser()
        if p.name == "brand.toml":
            p = p.parent
        if not (p / "brand.toml").is_file():
            raise BrandNotFound(f"no brand.toml in {p}")
        return p
    return find_brand(name_or_path, cwd)


def _table(data: dict, key: str) -> dict:
    value = data.get(key, {})
    if not isinstance(value, dict):
        raise BrandError(f"[{key}] must be a table")
    return value


def _asset(root: Path, value: object, key: str) -> Path:
    if not isinstance(value, str) or not value:
        raise BrandError(f"{key}: expected a file path relative to the brand folder")
    path = root / value
    if not path.is_file():
        raise BrandError(f"{key}: file not found: {path}")
    return path


def _color(value: object, key: str, colors: dict[str, str]) -> str:
    """A docx color may name a token ('accent') or be a hex."""
    if isinstance(value, str) and value in colors:
        return colors[value]
    return normalize_hex(value, key)  # type: ignore[arg-type]


def _components(preset: dict, overrides: dict) -> dict:
    comps = dict(preset)
    for k, v in overrides.items():
        key = f"components.{k}"
        if k not in comps:
            raise BrandError(f"{key}: unknown component setting (valid: {', '.join(preset)})")
        if k == "accent_strip" and v == "none":
            v = None
        allowed = {"card": CARD_KINDS, "accent_strip": ACCENT_STRIPS,
                   "content_bg": COLOR_TOKENS, "node_shape": NODE_SHAPES}.get(k)
        if allowed is not None and v not in allowed:
            shown = ", ".join("none" if a is None else a for a in allowed)
            raise BrandError(f"{key}: {v!r} is not one of {shown}")
        if k == "radius":
            if not isinstance(v, int | float) or isinstance(v, bool):
                raise BrandError(f"{key}: expected a number")
            v = float(v)
        comps[k] = v
    return comps


def load_brand(name_or_path: str | Path, cwd: Path | None = None, allow_draft: bool = False) -> Brand:
    """Load a brand by name (search path) or folder path; brand values override the style preset."""
    root = _resolve_folder(name_or_path, cwd).resolve()
    toml_path = root / "brand.toml"
    try:
        data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise BrandError(f"{toml_path}: invalid TOML: {e}") from e

    name = str(data.get("name", root.name))
    draft = bool(data.get("draft", False))
    if draft and not allow_draft:
        raise BrandError(
            f"brand {name!r} is a draft (draft = true in {toml_path}). Review it and remove "
            "the flag, or pass --confirm to use it anyway."
        )

    style = data.get("style", "modern")
    if style not in STYLE_PRESETS:
        raise BrandError(f"style {style!r} unknown in {toml_path}; valid: {', '.join(STYLE_PRESETS)}")
    preset = STYLE_PRESETS[style]

    colors = dict(preset["colors"])
    for k, v in _table(data, "colors").items():
        if k not in COLOR_TOKENS:
            raise BrandError(f"colors.{k}: unknown color token (valid: {', '.join(COLOR_TOKENS)})")
        colors[k] = normalize_hex(v, f"colors.{k}")

    fonts_in = _table(data, "fonts")
    if not isinstance(fonts_in.get("body"), str) or not fonts_in["body"]:
        raise BrandError(f"fonts.body is required in {toml_path}")
    fonts = {
        "body": fonts_in["body"],
        "heading": str(fonts_in.get("heading", fonts_in["body"])),
        "mono": str(fonts_in.get("mono", fonts_in["body"])),
    }

    logos = {k: _asset(root, v, f"logos.{k}") for k, v in _table(data, "logos").items()}

    deck = _table(data, "deck")
    template = _asset(root, deck["template"], "deck.template") if "template" in deck else None
    layouts = deck.get("layouts", {})
    if not isinstance(layouts, dict):
        raise BrandError("[deck.layouts] must be a table")

    grid = dict(GRID_DEFAULTS)
    for k, v in _table(data, "grid").items():
        if k not in GRID_DEFAULTS:
            raise BrandError(f"grid.{k}: unknown grid setting (valid: {', '.join(GRID_DEFAULTS)})")
        if not isinstance(v, int | float) or isinstance(v, bool):
            raise BrandError(f"grid.{k}: expected a number")
        grid[k] = float(v)

    docx_in = _table(data, "docx")
    docx: dict = {
        "reference": _asset(root, docx_in["reference"], "docx.reference") if "reference" in docx_in else None,
        "cover_band": colors["primary"],
        "company": str(docx_in.get("company", "")),
    }
    for k in DOCX_COLOR_KEYS:
        if k in docx_in:
            docx[k] = _color(docx_in[k], f"docx.{k}", colors)

    return Brand(
        name=name,
        root=root,
        description=str(data.get("description", "")),
        style=style,
        colors=colors,
        components=_components(preset["components"], _table(data, "components")),
        fonts=fonts,
        logos=logos,
        footer=str(deck.get("footer", "")),
        template=template,
        layouts={str(k): str(v) for k, v in layouts.items()},
        grid=grid,
        docx=docx,
        draft=draft,
    )
