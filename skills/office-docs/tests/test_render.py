import os
import subprocess
import sys
from pathlib import Path

import pymupdf
import pytest

import render
from conftest import SCRIPTS
from render import RenderUnavailable, applescript_quote, export_pdf, pdf_to_png, run_build
from test_components import _deck, _png, build_smoke


def _pdf(path, pages):
    doc = pymupdf.open()
    for i in range(pages):
        doc.new_page(width=400, height=300).insert_text((50, 100), f"page {i + 1}")
    doc.save(str(path))
    doc.close()
    return path


def test_pdf_to_png(tmp_path):
    out = tmp_path / "png"
    out.mkdir()
    (out / "07.png").write_bytes(b"stale")
    pngs = pdf_to_png(_pdf(tmp_path / "x.pdf", 2), out, dpi=72)
    assert [p.name for p in pngs] == ["01.png", "02.png"]
    assert sorted(p.name for p in out.iterdir()) == ["01.png", "02.png"]
    pix = pymupdf.Pixmap(str(pngs[0]))
    assert (pix.width, pix.height) == (400, 300)


def test_applescript_quote():
    q = applescript_quote(Path('/a/Overview Técnico — Q3 "x".pptx'))
    assert q.startswith('"') and q.endswith('"')
    assert '\\"x\\"' in q
    assert "Técnico — Q3" in q
    assert applescript_quote(Path("/a/b\\c")) == '"/a/b\\\\c"'


def test_run_build_sets_pythonpath(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTHONPATH", "/somewhere/else")
    out = tmp_path / "env.txt"
    script = tmp_path / "build.py"
    script.write_text(
        "import os, pathlib\n"
        "pathlib.Path('env.txt').write_text(os.environ['PYTHONPATH'])\n"
        "import deck\n",
        encoding="utf-8",
    )
    run_build(script)
    pp = out.read_text().split(os.pathsep)
    assert pp[0] == str(SCRIPTS)
    assert "/somewhere/else" in pp

    bad = tmp_path / "bad.py"
    bad.write_text("raise SystemExit(3)\n", encoding="utf-8")
    with pytest.raises(subprocess.CalledProcessError):
        run_build(bad)


def test_unavailable(monkeypatch, tmp_path):
    monkeypatch.setattr(render, "office_app", lambda suffix: None)
    monkeypatch.setattr(render.shutil, "which", lambda name: None)
    monkeypatch.setattr(render.sys, "platform", "linux")
    src = tmp_path / "deck.pptx"
    src.write_bytes(b"")
    with pytest.raises(RenderUnavailable) as e:
        export_pdf(src, tmp_path / "deck.pdf")
    msg = str(e.value)
    assert "PowerPoint" in msg and "soffice" in msg


def test_office_app_detection(monkeypatch):
    monkeypatch.setattr(render.sys, "platform", "linux")
    assert render.office_app(".pptx") is None
    monkeypatch.setattr(render.sys, "platform", "darwin")
    monkeypatch.setattr(render.Path, "exists", lambda self: True)
    assert render.office_app(".pptx") == "Microsoft PowerPoint"
    assert render.office_app(".docx") == "Microsoft Word"
    assert render.office_app(".txt") is None


def test_render_defaults(monkeypatch, tmp_path):
    def fake_export(src, pdf):
        return _pdf(pdf, 3)

    monkeypatch.setattr(render, "export_pdf", fake_export)
    src = tmp_path / "deck.pptx"
    src.write_bytes(b"")
    res = render.render(src, dpi=50)
    assert res.pdf == tmp_path / "deck.pdf"
    assert [p.name for p in res.pngs] == ["01.png", "02.png", "03.png"]
    assert all(p.parent == tmp_path / "deck-render" for p in res.pngs)

    only = render.render(src, pdf_only=True)
    assert only.pngs == []


@pytest.mark.skipif(os.environ.get("OFFICE_DOCS_RENDER") != "1", reason="set OFFICE_DOCS_RENDER=1")
def test_real_export(make_brand, tmp_path):
    d = _deck(make_brand, "modern")
    build_smoke(d, _png(tmp_path / "img.png", 300, 200))
    folder = tmp_path / "Carpeta con espacio — ñ"
    folder.mkdir()
    path = folder / "deck.pptx"
    d.save(path)
    res = render.render(path, dpi=40)
    assert res.pdf.exists()
    assert len(res.pngs) >= 1


@pytest.mark.skipif(os.environ.get("OFFICE_DOCS_RENDER") != "1", reason="set OFFICE_DOCS_RENDER=1")
def test_real_export_docx(tmp_path):
    from docx import Document

    folder = tmp_path / 'Carpeta "doc" — ñ'
    folder.mkdir()
    path = folder / "doc.docx"
    doc = Document()
    doc.add_heading("Hola", 1)
    doc.add_paragraph("Un párrafo.")
    doc.save(str(path))
    res = render.render(path, dpi=40)
    assert len(res.pngs) >= 1


def test_not_authorized(monkeypatch, tmp_path):
    def fake_run(cmd, input, **kw):
        return subprocess.CompletedProcess(cmd, 1, "", "execution error: Not authorized to send "
                                           "Apple events to Microsoft PowerPoint. (-1743)")

    monkeypatch.setattr(render, "office_app", lambda suffix: "Microsoft PowerPoint")
    monkeypatch.setattr(render.subprocess, "run", fake_run)
    src = tmp_path / "deck.pptx"
    src.write_bytes(b"")
    with pytest.raises(RenderUnavailable, match="Privacy & Security → Automation"):
        export_pdf(src, tmp_path / "deck.pdf")
