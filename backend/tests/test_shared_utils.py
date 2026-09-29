from pathlib import Path

from backend.app.shared.path_safety import resolve_safe_file, safe_filename_stem
from backend.app.shared.text import normalize_whitespace


def test_safe_filename_stem() -> None:
    assert safe_filename_stem("report.pdf") == "report"
    assert safe_filename_stem("../etc/passwd") is None
    assert safe_filename_stem("") is None


def test_resolve_safe_file(tmp_path: Path) -> None:
    path = resolve_safe_file(output_dir=tmp_path, filename_stem="ok", suffix=".txt")
    assert path is not None
    assert path.parent == tmp_path.resolve()


def test_normalize_whitespace() -> None:
    assert normalize_whitespace("  a   b\tc  ") == "a b c"
