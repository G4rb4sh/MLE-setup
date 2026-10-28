import os
from pathlib import Path

import pytest

from brand import (
    COLOR_TOKENS,
    PLUGIN_BRANDS,
    STYLE_PRESETS,
    BrandError,
    BrandNotFound,
    brand_search_path,
    find_brand,
    load_brand,
)

FONTS = '[fonts]\nbody = "Arial"\n'


def test_neutral_loads():
    b = load_brand("neutral")
    assert b.name == "neutral"
    assert b.style == "modern"
    assert set(COLOR_TOKENS) <= b.colors.keys()
    assert b.template is None
    assert b.fonts == {"body": "Calibri", "heading": "Calibri", "mono": "Consolas"}
    assert b.grid == {"margin": 0.6, "columns": 12.0, "gutter": 0.2}
    assert b.draft is False


def test_presets_complete():
    for name, preset in STYLE_PRESETS.items():
        assert set(preset["colors"]) == set(COLOR_TOKENS), name
        assert preset["components"].keys() == {
            "card", "radius", "accent_strip", "content_bg", "node_shape"
        }, name
        assert preset["components"]["content_bg"] in COLOR_TOKENS, name


def test_search_order(tmp_path, monkeypatch):
    toml = 'style = "modern"\n' + FONTS
    proj = tmp_path / "proj" / "brands" / "x"
    env = tmp_path / "env" / "x"
    for d in (proj, env):
        d.mkdir(parents=True)
        (d / "brand.toml").write_text(toml)
    monkeypatch.setenv("MLE_BRANDS_PATH", str(tmp_path / "env"))
    assert find_brand("x", cwd=tmp_path / "proj") == proj
    (proj / "brand.toml").unlink()
    proj.rmdir()
    assert find_brand("x", cwd=tmp_path / "proj") == env


def test_search_path_order(tmp_path, monkeypatch):
    monkeypatch.setenv("MLE_BRANDS_PATH", os.pathsep.join([str(tmp_path / "a"), str(tmp_path / "b")]))
    assert brand_search_path(tmp_path) == [
        tmp_path / "brands",
        tmp_path / "a",
        tmp_path / "b",
        Path.home() / ".mle-setup" / "brands",
        PLUGIN_BRANDS,
    ]


def test_not_found_lists_dirs():
    with pytest.raises(BrandNotFound) as e:
        find_brand("does-not-exist-anywhere")
    for d in brand_search_path():
        assert str(d) in str(e.value)


def test_hex_normalized(make_brand):
    folder = make_brand("b", FONTS + '[colors]\naccent = "#2870cf"\n')
    assert load_brand(folder).colors["accent"] == "2870CF"


def test_invalid_hex_names_key(make_brand):
    folder = make_brand("b", FONTS + '[colors]\nprimary = "12345"\n')
    with pytest.raises(BrandError, match=r"colors\.primary"):
        load_brand(folder)


def test_unknown_color_token(make_brand):
    folder = make_brand("b", FONTS + '[colors]\nprimry = "123456"\n')
    with pytest.raises(BrandError, match=r"colors\.primry"):
        load_brand(folder)


def test_unknown_style(make_brand):
    folder = make_brand("b", 'style = "fancy"\n' + FONTS)
    with pytest.raises(BrandError) as e:
        load_brand(folder)
    for style in ("modern", "outlined", "dark"):
        assert style in str(e.value)


def test_missing_asset(make_brand):
    folder = make_brand("b", FONTS + '[logos]\nlight = "nope.png"\n')
    with pytest.raises(BrandError, match="nope.png"):
        load_brand(folder)


def test_assets_resolved(make_brand):
    folder = make_brand("b", FONTS + '[logos]\nlight = "logo.png"\n[deck]\ntemplate = "t.pptx"\n'
                        '[deck.layouts]\ntitle = "Title Slide"\n')
    (folder / "logo.png").write_bytes(b"x")
    (folder / "t.pptx").write_bytes(b"x")
    b = load_brand(folder)
    assert b.logos == {"light": folder.resolve() / "logo.png"}
    assert b.template == folder.resolve() / "t.pptx"
    assert b.layouts == {"title": "Title Slide"}


@pytest.mark.parametrize("value", ["../outside.png", "sub/../../outside.png"])
def test_asset_outside_brand_folder_refused(make_brand, value):
    folder = make_brand("b", FONTS + f'[logos]\nlight = "{value}"\n')
    (folder.parent / "outside.png").write_bytes(b"x")
    (folder / "sub").mkdir()
    with pytest.raises(BrandError, match="outside the brand folder"):
        load_brand(folder)


def test_absolute_asset_refused(make_brand, tmp_path):
    (tmp_path / "abs.png").write_bytes(b"x")
    folder = make_brand("b", FONTS + f'[logos]\nlight = "{tmp_path / "abs.png"}"\n')
    with pytest.raises(BrandError, match="outside the brand folder"):
        load_brand(folder)


def test_draft_refused(make_brand):
    folder = make_brand("b", "draft = true\n" + FONTS)
    with pytest.raises(BrandError, match="--confirm"):
        load_brand(folder)
    assert load_brand(folder, allow_draft=True).draft is True


def test_brand_overrides_preset(make_brand):
    folder = make_brand("b", 'style = "dark"\n' + FONTS + '[colors]\naccent = "FF0000"\n')
    b = load_brand(folder)
    assert b.colors["accent"] == "FF0000"
    assert b.colors["background"] == "1E2438"


def test_components_override(make_brand):
    folder = make_brand("b", FONTS + '[components]\nradius = 0.2\naccent_strip = "none"\n')
    b = load_brand(folder)
    assert b.components["radius"] == 0.2
    assert b.components["accent_strip"] is None
    assert b.components["card"] == STYLE_PRESETS["modern"]["components"]["card"]


def test_load_by_name_from_cwd(make_brand, tmp_path):
    make_brand("mine", FONTS)
    b = load_brand("mine", cwd=tmp_path)
    assert b.name == "mine"
    assert b.root == (tmp_path / "brands" / "mine").resolve()


def test_docx_defaults_and_tokens(make_brand):
    folder = make_brand("b", FONTS + '[docx]\nheading_color = "accent"\ncode_bg = "#eeeeee"\n')
    b = load_brand(folder)
    assert b.docx["reference"] is None
    assert b.docx["cover_band"] == b.colors["primary"]
    assert b.docx["company"] == ""
    assert b.docx["heading_color"] == b.colors["accent"]
    assert b.docx["code_bg"] == "EEEEEE"
