import subprocess
import sys

import pytest
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_AUTO_SIZE

from conftest import SCRIPTS
from deck_check import Issue, check_file, check_presentation
from test_components import STYLES, _deck, _png, build_smoke


def _kinds(issues):
    return [i.kind for i in issues]


@pytest.mark.parametrize("style", STYLES)
def test_clean_deck_no_issues(make_brand, tmp_path, style):
    d = _deck(make_brand, style)
    build_smoke(d, _png(tmp_path / "img.png", 300, 200))
    assert check_presentation(d.prs) == []


def test_off_slide(make_brand):
    d = _deck(make_brand, "modern")
    s = d.blank_slide()
    d.rect(s, 12.8, 1, 1, 1)
    d.rect(s, 12.3, 3, 1.04, 1)  # 0.013 in past the edge: tolerated
    issues = check_presentation(d.prs)
    assert _kinds(issues) == ["off_slide"]
    assert issues[0].slide == 1


def test_overflow(make_brand):
    d = _deck(make_brand, "modern")
    s = d.blank_slide()
    d.text(s, 1, 1, 3, 0.5, "x" * 300, size=18)
    d.text(s, 1, 3, 3, 0.5, "corto", size=18)
    assert _kinds(check_presentation(d.prs)) == ["overflow"]


def test_overflow_skips_autofit(make_brand):
    d = _deck(make_brand, "modern")
    s = d.blank_slide()
    sh = d.text(s, 1, 1, 3, 0.5, "x" * 300, size=18)
    sh.text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE  # normAutofit
    sh2 = d.text(s, 5, 1, 3, 0.5, "x" * 300, size=18)
    sh2.text_frame.auto_size = MSO_AUTO_SIZE.SHAPE_TO_FIT_TEXT  # spAutoFit
    assert check_presentation(d.prs) == []


def test_overflow_default_insets_and_size(make_brand):
    d = _deck(make_brand, "modern")
    s = d.blank_slide()
    # 0.5 in box, default 0.05 in top/bottom insets -> 0.4 in = 28.8 pt usable; one 18 pt line = 21.6 pt.
    box = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 914400, 914400, 914400 * 3, 914400 // 2)
    box.text_frame.text = "una línea"
    assert check_presentation(d.prs) == []
    box.text_frame.add_paragraph().text = "otra"  # 43.2 pt > 1.05 * 28.8 pt
    assert _kinds(check_presentation(d.prs)) == ["overflow"]


def test_overlap_text_only(make_brand):
    d = _deck(make_brand, "modern")
    s = d.blank_slide()
    d.text(s, 1, 1, 3, 1, "uno")
    d.text(s, 2, 1.5, 3, 1, "dos")
    assert _kinds(check_presentation(d.prs)) == ["overlap"]

    d = _deck(make_brand, "modern")
    s = d.blank_slide()
    d._card_body(s, 1, 1, 4, 3)
    d.text(s, 1.3, 1.2, 3, 1, "dentro de la card")
    d.rect(s, 4.5, 2.5, 3, 1)  # crosses the card but not its text: ignored
    d.text(s, 6, 4, 2, 1, "texto")
    d.rect(s, 5, 3.5, 2, 1, fill=None, line="accent")  # crosses the text box, but has no text or fill
    assert check_presentation(d.prs) == []


def test_covered_by_later_fill_or_picture(make_brand, tmp_path):
    d = _deck(make_brand, "modern")
    s = d.blank_slide()
    d.text(s, 1, 1, 3, 1, "tapado")
    d.rect(s, 2, 1.5, 3, 1)  # filled, drawn after the text, crosses it
    s = d.blank_slide()
    d.text(s, 1, 4, 3, 1, "bajo una imagen")
    d.image(s, _png(tmp_path / "i.png", 30, 20), 1.5, 4.5, 3, 2, fit="stretch")
    issues = check_presentation(d.prs)
    assert [(i.slide, i.kind) for i in issues] == [(1, "covered"), (2, "covered")]
    assert issues[0].detail.startswith("covered by ")


def test_covered_ignores_shapes_behind_or_containing(make_brand):
    d = _deck(make_brand, "modern")
    s = d.blank_slide()
    d.rect(s, 1, 1, 4, 3)  # drawn first: a background
    d.text(s, 1.5, 1.5, 4, 1, "sobre el fondo")
    d.text(s, 7, 1, 2, 1, "dentro")
    d.rect(s, 6.5, 0.5, 3, 2, opacity=30)  # later but fully contains the text (a scrim)
    d.text(s, 7, 4, 2, 1, "toca")
    d.rect(s, 9, 4, 1, 1)  # only touches the text box edge
    assert check_presentation(d.prs) == []


def test_two_biased_card_rows_flagged(make_brand):
    d = _deck(make_brand, "modern")
    s, top = d.content_slide("k", "Dos filas")
    row = [{"title": "A", "lines": ["uno", "dos"]}, {"title": "B", "lines": ["tres"]}]
    d.cards_row(s, top, row, height=2.1)
    d.cards_row(s, top + 2.1 + 0.3, row, height=2.1)  # caller ignores the bias: rows overlap
    assert "covered" in _kinds(check_presentation(d.prs))


def test_overlap_containment_between_texts(make_brand):
    d = _deck(make_brand, "modern")
    s = d.blank_slide()
    d.rect(s, 1, 1, 4, 3).text_frame.text = "fondo"
    d.text(s, 1.5, 1.5, 2, 1, "dentro")
    assert check_presentation(d.prs) == []


def test_long_title(make_brand):
    d = _deck(make_brand, "modern")
    d.content_slide("k", "t" * 60)
    d.content_slide("k", "t" * 55)
    issues = [i for i in check_presentation(d.prs) if i.kind == "long_title"]
    assert len(issues) == 1
    assert issues[0].slide == 1 and issues[0].shape == "title"


def test_issue_str():
    assert str(Issue(3, "TextBox 4", "overflow", "needs 2.0 in")) == "slide 3: overflow TextBox 4 — needs 2.0 in"


def _bad_deck(make_brand, tmp_path):
    d = _deck(make_brand, "modern")
    s = d.blank_slide()
    d.text(s, 1, 1, 3, 0.5, "x" * 300, size=18)
    out = tmp_path / "bad.pptx"
    d.prs.save(str(out))
    return out


def test_check_file(make_brand, tmp_path):
    assert _kinds(check_file(_bad_deck(make_brand, tmp_path))) == ["overflow"]


def test_cli_exit_zero(make_brand, tmp_path):
    bad = _bad_deck(make_brand, tmp_path)
    r = subprocess.run([sys.executable, str(SCRIPTS / "deck.py"), "check", str(bad)],
                       capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert "overflow" in r.stdout and "slide 1:" in r.stdout


def test_cli_ok(make_brand, tmp_path):
    d = _deck(make_brand, "modern")
    d.content_slide("k", "Título")
    out = tmp_path / "ok.pptx"
    d.prs.save(str(out))
    r = subprocess.run([sys.executable, str(SCRIPTS / "deck.py"), "check", str(out)],
                       capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 0 and r.stdout.strip() == "OK"


def test_save_prints_issues_and_returns_count(make_brand, tmp_path, capsys):
    d = _deck(make_brand, "modern")
    s = d.blank_slide()
    d.text(s, 1, 1, 3, 0.5, "x" * 300, size=18)
    assert d.save(tmp_path / "o.pptx") == 1
    err = capsys.readouterr().err
    assert "overflow" in err


def test_save_survives_check_crash(make_brand, tmp_path, capsys, monkeypatch):
    import deck

    def boom(prs):
        raise RuntimeError("odd shape")

    monkeypatch.setattr(deck, "check_presentation", boom)
    d = _deck(make_brand, "modern")
    d.blank_slide()
    assert d.save(tmp_path / "o.pptx") == 1
    assert (tmp_path / "o.pptx").is_file()
    assert "odd shape" in capsys.readouterr().err
