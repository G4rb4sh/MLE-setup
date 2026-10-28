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
(addressed by its unique file name), so documents the user has open are never touched.
The copy and the PDF live in a fresh folder inside the app's sandbox container when this
process may write there (else the system temp dir), so the sandboxed app does not ask for
file access ("Grant File Access").
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from string import Template

import pymupdf

SCRIPTS = Path(__file__).resolve().parent
OFFICE_APPS = {".pptx": "Microsoft PowerPoint", ".docx": "Microsoft Word"}
EXPORT_TIMEOUT_S = 600
NOT_AUTHORIZED = "-1743"
DIALOG_OPEN = "-9074"
# Sandbox containers: Office can always read and write here without asking the user.
_CONTAINERS = {"Microsoft PowerPoint": "com.microsoft.Powerpoint", "Microsoft Word": "com.microsoft.Word"}
OFFICE_GROUP = "UBF8T346G9.Office"
WORKDIR_PREFIX = "office-docs-render-"

# App terminology: what a document is called and how it is saved as PDF.
_TERMS = {
    "Microsoft PowerPoint": ("presentation", "save $doc in POSIX file pdfPath as save as PDF"),
    "Microsoft Word": ("document", "save as $doc file name pdfPath file format format PDF"),
}

# Every save/close names the copy by its unique file name (`$noun nm`), so the app resolves the
# target inside the same Apple event that acts on it; a missing name errors (-1728) instead of
# hitting another document. Never address documents by index or with `whose` (Word ignores it).
_OSASCRIPT = Template("""\
set src to $src
set nm to $name
$setup
with timeout of $timeout seconds
  tell application "$app"
    activate -- a backgrounded (App Nap) app can stall `open` for minutes
    open POSIX file src
    set opened to false
    repeat 240 times
      if exists $noun nm then
        set opened to true
        exit repeat
      end if
      delay 0.25
    end repeat
    if not opened then
      try
        close $noun nm saving no
      end try
      error "the temporary copy did not open in $app within 60 s; it may still appear there later (close it without saving)" number 9001
    end if
    set failure to missing value
    try
      $action
    on error m number n
      set failure to {m, n}
    end try
    try
      close $noun nm saving no
    on error m number n
      if failure is missing value then set failure to {m, n}
    end try
    if failure is not missing value then error (item 1 of failure) number (item 2 of failure)
  end tell
end timeout
""")

# Best-effort cleanup after osascript itself timed out: close the copy only if it is there.
_CLEANUP = Template("""\
with timeout of 30 seconds
  tell application "$app"
    try
      close $noun $name saving no
    end try
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


def temp_copy_name(suffix: str) -> str:
    """A file name no user document has, so Office can address the copy by name alone."""
    return f"office-docs-{uuid.uuid4().hex[:8]}{suffix.lower()}"


def office_script(app: str, copy: Path, action: str, setup: str = "",
                  timeout: int = EXPORT_TIMEOUT_S) -> str:
    """AppleScript that opens `copy`, runs `action` on it and closes it without saving.

    In `action`, `$doc` is the copy addressed by name (e.g. `document nm`); `setup` runs
    before the `tell` block. The copy is closed even when `action` fails, then the error
    is re-raised.
    """
    noun = _TERMS[app][0]
    return _OSASCRIPT.substitute(
        app=app, noun=noun, action=Template(action).substitute(doc=f"{noun} nm"), setup=setup,
        src=applescript_quote(copy), name=applescript_quote(Path(copy.name)), timeout=timeout,
    )


def run_office_script(app: str, copy: Path, script: str,
                      timeout: int = EXPORT_TIMEOUT_S) -> subprocess.CompletedProcess:
    """Run `script` with osascript (stdin). On timeout, close `copy` by name (best effort), re-raise."""
    try:
        return subprocess.run(["osascript", "-"], input=script, capture_output=True, text=True,
                              timeout=timeout + 30)
    except subprocess.TimeoutExpired:
        cleanup = _CLEANUP.substitute(app=app, noun=_TERMS[app][0],
                                      name=applescript_quote(Path(copy.name)))
        subprocess.run(["osascript", "-"], input=cleanup, capture_output=True, text=True, timeout=60)
        raise


def office_sandbox_dirs(app: str) -> list[Path]:
    """Folders the sandboxed `app` can use without a file-access prompt, most specific first."""
    home = Path.home()
    return [home / "Library/Containers" / _CONTAINERS[app] / "Data/tmp",
            home / "Library/Group Containers" / OFFICE_GROUP]


@contextmanager
def office_workdir(app: str) -> Iterator[Path]:
    """A new `office-docs-render-*` folder for `app`'s temp copy and output, removed by exact path.

    Created inside the app's sandbox container when it exists and is writable (macOS may deny
    other apps' containers to this process), else in the system temp dir.
    """
    work = None
    for base in office_sandbox_dirs(app):
        try:
            work = Path(tempfile.mkdtemp(prefix=WORKDIR_PREFIX, dir=base))
            break
        except OSError:
            continue
    if work is None:
        work = Path(tempfile.mkdtemp(prefix=WORKDIR_PREFIX))
    try:
        yield work
    finally:
        shutil.rmtree(work, ignore_errors=True)


def dialog_hint(app: str, err: str) -> str:
    """Extra advice when `app` is blocked by an open dialog (error -9074), else ""."""
    if DIALOG_OPEN not in err:
        return ""
    return (f" {app} is showing a dialog (e.g. Grant File Access): press Esc in {app}, "
            f"then retry.")


def permission_hint(app: str, err: str) -> str | None:
    """The fix for a -1743 (Automation not allowed) error, else None."""
    if NOT_AUTHORIZED not in err:
        return None
    return (f"Not allowed to control {app} ({err}). Grant Automation permission in "
            f"System Settings → Privacy & Security → Automation (let your terminal "
            f"control {app}), then retry.")


def _office_script(app: str, copy: Path, out: Path) -> str:
    return office_script(app, copy, _TERMS[app][1], setup=f"set pdfPath to {applescript_quote(out)}")


def _export_office(app: str, src: Path, pdf: Path) -> Path:
    with office_workdir(app) as td:
        copy = td / temp_copy_name(src.suffix)
        shutil.copyfile(src, copy)
        out = copy.with_suffix(".pdf")
        r = run_office_script(app, copy, _office_script(app, copy, out))
        if r.returncode != 0:
            err = r.stderr.strip()
            hint = permission_hint(app, err)
            if hint:
                raise RenderUnavailable(hint)
            raise RuntimeError(f"{app} could not export {src.name} to PDF: {err}"
                               f"{dialog_hint(app, err)}")
        if not out.exists():
            raise RuntimeError(f"{app} reported success but wrote no PDF for {src.name}")
        pdf.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(out, pdf)
    return pdf


def _export_soffice(soffice: str, src: Path, pdf: Path) -> Path:
    with tempfile.TemporaryDirectory(prefix=WORKDIR_PREFIX) as td:
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
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired) as e:  # + RenderUnavailable
        print(f"render failed: {e}", file=sys.stderr)
        return 2
    print(res.pdf)
    for p in res.pngs:
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
