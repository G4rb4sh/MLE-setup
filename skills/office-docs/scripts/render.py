# /// script
# requires-python = ">=3.11"
# dependencies = ["pymupdf", "python-pptx", "python-docx"]
# ///
"""Render a .pptx/.docx to PDF and PNGs so a deck or document can be looked at.

    res = render("out.pptx")          # out.pdf + out-render/01.png, 02.png, ...
    res = render("doc.docx", pdf_only=True)

CLI: `uv run render.py FILE [--build SCRIPT] [--dpi N] [--pdf-only] [--out DIR]` prints the paths.
`--build` first runs SCRIPT (cwd = its folder, this scripts dir prepended to PYTHONPATH)
to regenerate FILE.

PDF backend, in order: macOS PowerPoint (.pptx) / Word (.docx) via osascript, then
`soffice --headless`. Office always works on a temporary copy and closes only that copy
(matched by its full path), so documents the user has open are never touched.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from string import Template

import pymupdf

SCRIPTS = Path(__file__).resolve().parent
OFFICE_APPS = {".pptx": "Microsoft PowerPoint", ".docx": "Microsoft Word"}
EXPORT_TIMEOUT_S = 600
NOT_AUTHORIZED = "-1743"

# App terminology: what a document is called and how it is saved as PDF.
_TERMS = {
    "Microsoft PowerPoint": ("presentation", "save $doc in POSIX file pdfPath as save as PDF"),
    "Microsoft Word": ("document", "save as $doc file name pdfPath file format format PDF"),
}

# Finds the temp copy by comparing `full name` client-side (Word's `whose` filter ignores the
# test). PowerPoint reports a POSIX full name without the /private prefix, Word an HFS one
# with it; all these forms are accepted.
_OSASCRIPT = Template("""\
on findDoc(names)
  tell application "$app"
    repeat with i from 1 to count of ${noun}s
      set fn to full name of $noun i
      if names contains {fn} then return i
    end repeat
  end tell
  return 0
end findDoc

set src to $src
set pdfPath to $pdf
set names to {src, $alt, (POSIX file src) as text}
with timeout of $timeout seconds
  tell application "$app"
    activate -- a backgrounded (App Nap) app can stall `open` for minutes
    open POSIX file src
    set idx to 0
    repeat 240 times
      set idx to my findDoc(names)
      if idx > 0 then exit repeat
      delay 0.25
    end repeat
    if idx = 0 then error "the temporary copy did not open in $app" number 9001
    set failure to missing value
    try
      $save
    on error m number n
      set failure to {m, n}
    end try
    set idx to my findDoc(names)
    if idx > 0 then close $noun idx saving no
    if failure is not missing value then error (item 1 of failure) number (item 2 of failure)
  end tell
end timeout
""")


class RenderUnavailable(RuntimeError):
    """No backend can export this file to PDF (or Office automation is not allowed)."""


@dataclass
class RenderResult:
    pdf: Path
    pngs: list[Path] = field(default_factory=list)


def applescript_quote(path: Path) -> str:
    """The POSIX path as an AppleScript string literal."""
    s = str(path).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'


def office_app(suffix: str) -> str | None:
    """The installed Office app that exports this suffix on macOS, else None."""
    app = OFFICE_APPS.get(suffix.lower())
    if sys.platform != "darwin" or app is None:
        return None
    return app if Path(f"/Applications/{app}.app").exists() else None


def _export_office(app: str, src: Path, pdf: Path) -> Path:
    with tempfile.TemporaryDirectory(prefix="office-docs-render-") as td:
        tmp = Path(td).resolve()
        copy = tmp / f"office-docs-{uuid.uuid4().hex[:8]}{src.suffix.lower()}"
        shutil.copyfile(src, copy)
        out = copy.with_suffix(".pdf")
        alt = Path(str(copy).removeprefix("/private")) if str(copy).startswith("/private/") else copy
        noun, save = _TERMS[app]
        script = _OSASCRIPT.substitute(
            app=app, noun=noun, save=Template(save).substitute(doc=f"{noun} idx"),
            src=applescript_quote(copy), alt=applescript_quote(alt), pdf=applescript_quote(out),
            timeout=EXPORT_TIMEOUT_S,
        )
        r = subprocess.run(["osascript", "-"], input=script, capture_output=True, text=True,
                           timeout=EXPORT_TIMEOUT_S + 30)
        if r.returncode != 0:
            err = r.stderr.strip()
            if NOT_AUTHORIZED in err:
                raise RenderUnavailable(
                    f"Not allowed to control {app} ({err}). Grant Automation permission in "
                    f"System Settings → Privacy & Security → Automation (let your terminal "
                    f"control {app}), then retry."
                )
            raise RuntimeError(f"{app} could not export {src.name} to PDF: {err}")
        if not out.exists():
            raise RuntimeError(f"{app} reported success but wrote no PDF for {src.name}")
        pdf.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(out, pdf)
    return pdf


def _export_soffice(soffice: str, src: Path, pdf: Path) -> Path:
    with tempfile.TemporaryDirectory(prefix="office-docs-render-") as td:
        subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", td, str(src)],
                       check=True, capture_output=True, timeout=EXPORT_TIMEOUT_S)
        out = Path(td) / f"{src.stem}.pdf"
        if not out.exists():
            raise RuntimeError(f"soffice wrote no PDF for {src.name}")
        pdf.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(out, pdf)
    return pdf


def export_pdf(src: Path, pdf: Path) -> Path:
    """Export `src` (.pptx/.docx) to `pdf` with Office on macOS, else soffice."""
    src, pdf = Path(src).resolve(), Path(pdf).resolve()
    app = office_app(src.suffix)
    if app:
        return _export_office(app, src, pdf)
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice:
        return _export_soffice(soffice, src, pdf)
    raise RenderUnavailable(
        f"Cannot export {src.name} to PDF: needs Microsoft PowerPoint/Word on macOS "
        "or LibreOffice (`soffice` on PATH)."
    )


def pdf_to_png(pdf: Path, out_dir: Path, dpi: int = 150) -> list[Path]:
    """One PNG per page: out_dir/01.png, 02.png, ... (stale numbered PNGs are removed)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.png"):
        if old.stem.isdigit():
            old.unlink()
    paths = []
    with pymupdf.open(pdf) as doc:
        width = max(2, len(str(doc.page_count)))
        for i, page in enumerate(doc, 1):
            p = out_dir / f"{i:0{width}d}.png"
            page.get_pixmap(dpi=dpi).save(str(p))
            paths.append(p)
    return paths


def run_build(script: Path) -> None:
    """Run a build script with this scripts dir importable; raise CalledProcessError on failure."""
    script = Path(script).resolve()
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(p for p in (str(SCRIPTS), env.get("PYTHONPATH")) if p)
    subprocess.run([sys.executable, str(script)], cwd=script.parent, env=env, check=True)


def render(path: Path, dpi: int = 150, pdf_only: bool = False, out_dir: Path | None = None) -> RenderResult:
    """Export `path` to a PDF next to it, then PNGs into `out_dir` (default `<stem>-render/`)."""
    path = Path(path).resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    pdf = export_pdf(path, path.with_suffix(".pdf"))
    if pdf_only:
        return RenderResult(pdf)
    out = Path(out_dir) if out_dir else path.with_name(f"{path.stem}-render")
    return RenderResult(pdf, pdf_to_png(pdf, out, dpi))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="render.py", description="Render a .pptx/.docx to PDF and PNGs.")
    ap.add_argument("file")
    ap.add_argument("--build", metavar="SCRIPT", help="run this build script first")
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--pdf-only", action="store_true")
    ap.add_argument("--out", metavar="DIR", help="PNG folder (default: <stem>-render/ next to FILE)")
    args = ap.parse_args(argv)
    try:
        if args.build:
            run_build(Path(args.build))
        res = render(Path(args.file), dpi=args.dpi, pdf_only=args.pdf_only,
                     out_dir=Path(args.out) if args.out else None)
    except subprocess.CalledProcessError as e:
        print(f"build failed: {e}", file=sys.stderr)
        return e.returncode or 1
    except (RuntimeError, FileNotFoundError) as e:  # includes RenderUnavailable
        print(f"render failed: {e}", file=sys.stderr)
        return 2
    print(res.pdf)
    for p in res.pngs:
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
