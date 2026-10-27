import sys
import warnings
from collections.abc import Callable
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

# PyMuPDF's SWIG bindings warn on import (and again at interpreter exit) under Python 3.12+.
SWIG_WARNING = r"builtin type (SwigPyPacked|SwigPyObject|swigvarlink) has no __module__ attribute"
warnings.filterwarnings("ignore", message=SWIG_WARNING, category=DeprecationWarning)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("filterwarnings", f"ignore:{SWIG_WARNING}:DeprecationWarning")


@pytest.fixture
def make_brand(tmp_path: Path) -> Callable[[str, str], Path]:
    """Write `tmp_path/brands/NAME/brand.toml` with the given text; return the folder."""

    def _make(name: str, toml: str) -> Path:
        folder = tmp_path / "brands" / name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "brand.toml").write_text(toml, encoding="utf-8")
        return folder

    return _make
