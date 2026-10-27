# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx", "pymupdf"]
# ///
"""Markdown to a branded, editable Word document (via pandoc).

    out = build_docx(Path("plan.md"), load_brand("neutral"))   # plan.docx next to the md

CLI: `uv run md2docx.py DOC.md --brand NAME [-o OUT] [--no-word]`.

Per-document data comes from a leading front-matter block of `key: value` lines (see
`DocMeta` for the keys); without `title`, the first H1 (or the file name) is the title.
A leading H1 equal to the title moves to the cover. The output has a cover, a TOC,
header and footer, styled tables and code, all from the brand. Fenced `mermaid` blocks
become images when `npx` (Node.js) and Chrome are available; otherwise they stay as code.
Links to other `.md` files become italic text. With Microsoft Word (macOS) the TOC is
filled on a temporary copy; otherwise Word fills it when the document is opened.

Needs pandoc on PATH (`brew install pandoc`).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, fields
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

from brand import Brand, BrandError, load_brand
from docx_brand import (
    add_cover,
    add_header_footer,
    fill_toc_with_word,
    fix_property_order,
    labels,
    make_reference_docx,
    style_tables,
    update_fields_on_open,
)

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
CHROME_PATHS = ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",)
MERMAID_TIMEOUT_S = 300

# Links to another .md are useless outside the repo: keep their text, in italics.
# Horizontal rules (`---`) separate parts in Markdown; in Word, headings already do.
LUA_FILTER = r"""
function Link(el)
  if el.target:match("^%a[%w+.-]*:") then return nil end
  local path = el.target:gsub("[#?].*$", "")
  if path:lower():match("%.md$") then return pandoc.Emph(el.content) end
end

function HorizontalRule()
  return {}
end
"""

_TRUE = {"true", "yes", "si", "sí", "1"}
_FALSE = {"false", "no", "0"}


def spanish_date(day: dt.date) -> str:
    return f"{day.day} de {MESES[day.month - 1]} de {day.year}"


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    """A leading `---` ... `---` block of `key: value` lines -> (dict, rest). No block: ({}, text)."""
    lines = text.removeprefix("\ufeff").splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return {}, text
    end = next((i for i, ln in enumerate(lines[1:], 1) if ln.strip() in ("---", "...")), None)
    if end is None:
        return {}, text
    meta: dict[str, str] = {}
    for ln in lines[1:end]:
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        key, sep, value = s.partition(":")
        if not sep or not key.strip():
            raise ValueError(f"front matter line {s!r}: expected `key: value`")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        meta[key.strip()] = value
    return meta, "".join(lines[end + 1:])


@dataclass
class DocMeta:
    title: str
    subtitle: str = ""
    client: str = ""
    project: str = ""
    author: str = ""
    version: str = "1.0"
    date: str = ""  # empty: today, in Spanish ("27 de octubre de 2026")
    lang: str = "es-UY"
    toc_depth: int = 3
    page_break_on_h1: bool = True
    shift_headings: int = 0

    def __post_init__(self) -> None:
        if not self.date:
            self.date = spanish_date(dt.date.today())

    @classmethod
    def from_dict(cls, d: dict[str, str], fallback_title: str) -> DocMeta:
        """Front-matter values -> DocMeta; unknown keys or bad numbers/booleans raise ValueError."""
        valid = [f.name for f in fields(cls)]
        unknown = sorted(set(d) - set(valid))
        if unknown:
            raise ValueError(f"unknown front matter key(s) {', '.join(unknown)}; valid: {', '.join(valid)}")
        kw: dict[str, object] = {}
        for k, v in d.items():
            if k in ("toc_depth", "shift_headings"):
                try:
                    kw[k] = int(v)
                except ValueError:
                    raise ValueError(f"{k}: expected an integer, got {v!r}") from None
            elif k == "page_break_on_h1":
                if v.lower() not in _TRUE | _FALSE:
                    raise ValueError(f"{k}: expected true or false, got {v!r}")
                kw[k] = v.lower() in _TRUE
            else:
                kw[k] = v
        kw["title"] = kw.get("title") or fallback_title
        return cls(**kw)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# Markdown preparation

_FENCE = re.compile(r"^\s*(```|~~~)")


def _first_h1(md: str) -> str | None:
    in_code = False
    for line in md.splitlines():
        if _FENCE.match(line):
            in_code = not in_code
        elif not in_code and (m := re.match(r"#\s+(.+?)\s*#*\s*$", line)):
            return m.group(1)
    return None


def _drop_title_h1(md: str, title: str) -> str:
    """Remove a leading `# <title>`: the title is on the cover."""
    m = re.match(r"\s*#\s+(.+?)\s*#*\s*(\n+|$)", md)
    return md[m.end():] if m and m.group(1) == title else md


def _chrome() -> str | None:
    env = os.environ.get("PUPPETEER_EXECUTABLE_PATH")
    candidates = [env] if env else []
    candidates += CHROME_PATHS
    candidates += [shutil.which(n) for n in ("google-chrome", "chromium", "chromium-browser", "chrome")]
    return next((c for c in candidates if c and Path(c).exists()), None)


def _mermaid_config(brand: Brand | None) -> dict:
    if brand is None:
        return {"theme": "default"}
    c = brand.colors
    return {"theme": "base", "themeVariables": {
        "fontFamily": f"{brand.fonts['body']}, Arial, sans-serif",
        "primaryColor": f"#{c['background']}", "primaryBorderColor": f"#{c['accent']}",
        "primaryTextColor": f"#{c['text']}", "lineColor": f"#{c['muted']}",
    }}


_MERMAID = re.compile(r"^```mermaid[ \t]*\n(.*?)^```[ \t]*$\n?", re.M | re.S)


def render_mermaid(md: str, workdir: Path, brand: Brand | None = None) -> str:
    """Replace fenced `mermaid` blocks with PNG images rendered into `workdir`.

    Left-to-right flowcharts become top-to-bottom (they fit a portrait page). Needs `npx`
    (mermaid-cli) and Chrome; without them, one warning and the blocks stay as code.
    A block that fails to render stays as code too, with a warning.
    """
    if not _MERMAID.search(md):
        return md
    npx, chrome = shutil.which("npx"), _chrome()
    if npx is None or chrome is None:
        missing = " and ".join(n for n, p in (("npx (Node.js)", npx), ("Google Chrome", chrome)) if p is None)
        print(f"warning: {missing} not found; mermaid blocks kept as code.", file=sys.stderr)
        return md
    workdir = Path(workdir)
    puppeteer = workdir / "puppeteer.json"
    puppeteer.write_text(json.dumps({"executablePath": chrome}), encoding="utf-8")
    config = workdir / "mermaid.json"
    config.write_text(json.dumps(_mermaid_config(brand)), encoding="utf-8")
    count = 0

    def replace(m: re.Match[str]) -> str:
        nonlocal count
        count += 1
        src = workdir / f"diagram-{count}.mmd"
        png = src.with_suffix(".png")
        src.write_text(re.sub(r"^(\s*(?:flowchart|graph))\s+LR\b", r"\1 TB", m.group(1), flags=re.M),
                       encoding="utf-8")
        try:
            subprocess.run(
                [npx, "-y", "@mermaid-js/mermaid-cli", "-p", str(puppeteer), "-c", str(config),
                 "-i", str(src), "-o", str(png), "-s", "3", "-b", "transparent"],
                check=True, capture_output=True, text=True, timeout=MERMAID_TIMEOUT_S,
                env={**os.environ, "PUPPETEER_SKIP_DOWNLOAD": "1"},
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
            detail = getattr(e, "stderr", None) or e
            print(f"warning: diagram {count} kept as code: {str(detail).strip()}", file=sys.stderr)
            return m.group(0)
        return f"![](<{png}>){{height=10cm}}\n"

    return _MERMAID.sub(replace, md)


# --------------------------------------------------------------------------- #
# pandoc

def _highlight_args(work: Path) -> list[str]:
    """Tango token colors without tango's background, so code blocks show the brand's code_bg."""
    theme = json.loads(subprocess.run(["pandoc", "--print-highlight-style", "tango"],
                                      capture_output=True, text=True, check=True).stdout)
    theme["background-color"] = None
    path = work / "code.theme"
    path.write_text(json.dumps(theme), encoding="utf-8")
    out = subprocess.run(["pandoc", "--version"], capture_output=True, text=True, check=True).stdout
    m = re.search(r"pandoc\S*\s+(\d+)\.(\d+)", out)
    new = m is not None and (int(m.group(1)), int(m.group(2))) >= (3, 8)
    return ["--syntax-highlighting" if new else "--highlight-style", str(path)]


def _pandoc(md: Path, out: Path, reference: Path, lua: Path, meta: DocMeta, cwd: Path) -> None:
    cmd = ["pandoc", str(md), "-f", "gfm+attributes", "-o", str(out),
           "--reference-doc", str(reference), "--lua-filter", str(lua),
           "--toc", "--toc-depth", str(meta.toc_depth), *_highlight_args(md.parent),
           "-M", f"lang={meta.lang}", "-M", f"toc-title={labels(meta.lang)['toc']}"]
    if meta.shift_headings:
        cmd.append(f"--shift-heading-level-by={meta.shift_headings}")
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.stderr.strip():
        print(r.stderr.strip(), file=sys.stderr)
    if r.returncode != 0:
        raise RuntimeError(f"pandoc failed ({r.returncode}) on {md.name}")


def _center_images(doc) -> None:
    for p in doc.paragraphs:
        if p._p.find(".//" + qn("wp:inline")) is not None:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER


def build_docx(md_path: Path, brand: Brand, out: Path | None = None, use_word: bool = True) -> Path:
    """Build the branded .docx for `md_path` (default `<stem>.docx` next to it); return its path."""
    if shutil.which("pandoc") is None:
        raise RuntimeError("pandoc not found on PATH (macOS: brew install pandoc)")
    md_path = Path(md_path).resolve()
    out = Path(out).resolve() if out else md_path.with_suffix(".docx")
    front, body = parse_front_matter(md_path.read_text(encoding="utf-8"))
    meta = DocMeta.from_dict(front, fallback_title=_first_h1(body) or md_path.stem)
    body = _drop_title_h1(body, meta.title)

    with tempfile.TemporaryDirectory(prefix="office-docs-md2docx-") as td:
        work = Path(td)
        source = work / "document.md"
        source.write_text(render_mermaid(body, work, brand), encoding="utf-8")
        reference = make_reference_docx(brand, work / "reference.docx", meta.page_break_on_h1)
        lua = work / "filter.lua"
        lua.write_text(LUA_FILTER, encoding="utf-8")
        out.parent.mkdir(parents=True, exist_ok=True)
        _pandoc(source, out, reference, lua, meta, cwd=md_path.parent)

    doc = Document(str(out))
    style_tables(doc, brand)
    _center_images(doc)
    add_header_footer(doc, meta, brand)
    add_cover(doc, meta, brand)
    props = doc.core_properties
    props.title = meta.title
    props.subject = meta.subtitle or meta.project
    props.author = meta.author or brand.docx.get("company", "")
    props.language = meta.lang
    doc.save(str(out))
    fix_property_order(out)
    if not (use_word and fill_toc_with_word(out)):
        update_fields_on_open(out)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="md2docx.py", description="Markdown to a branded Word document.")
    ap.add_argument("md", help="the Markdown file")
    ap.add_argument("--brand", required=True, help="brand name or folder")
    ap.add_argument("-o", "--out", help="output .docx (default: <stem>.docx next to the md)")
    ap.add_argument("--no-word", action="store_true",
                    help="do not open Word to fill the TOC (Word fills it when the file is opened)")
    args = ap.parse_args(argv)
    try:
        out = build_docx(Path(args.md), load_brand(args.brand),
                         out=Path(args.out) if args.out else None, use_word=not args.no_word)
    except (BrandError, ValueError, RuntimeError, OSError) as e:
        print(f"md2docx failed: {e}", file=sys.stderr)
        return 2
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
