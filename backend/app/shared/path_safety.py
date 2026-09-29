from __future__ import annotations

from pathlib import Path


def safe_filename_stem(raw_name: str, *, max_len: int = 120) -> str | None:
    """Возвращает безопасный stem имени файла или None."""

    raw = (raw_name or "").strip().replace("\\", "/")
    if not raw or "/" in raw:
        return None

    stem = Path(raw).name.strip()
    stem = Path(stem).stem.strip()
    if not stem:
        return None
    if stem in {".", ".."} or ".." in stem:
        return None
    if "\x00" in stem or "/" in stem or "\\" in stem:
        return None
    return stem[:max_len]


def resolve_safe_file(
    *,
    output_dir: Path,
    filename_stem: str,
    suffix: str,
) -> Path | None:
    """Собирает путь внутри `output_dir` без выхода за его пределы."""

    if not suffix.startswith("."):
        return None
    root = output_dir.resolve()
    candidate = (root / f"{filename_stem}{suffix}").resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate
