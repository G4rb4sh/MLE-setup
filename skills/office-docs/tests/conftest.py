import sys
from collections.abc import Callable
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))


@pytest.fixture
def make_brand(tmp_path: Path) -> Callable[[str, str], Path]:
    """Write `tmp_path/brands/NAME/brand.toml` with the given text; return the folder."""

    def _make(name: str, toml: str) -> Path:
        folder = tmp_path / "brands" / name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "brand.toml").write_text(toml, encoding="utf-8")
        return folder

    return _make
