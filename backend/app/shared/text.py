"""Нормализация строк без бизнес-смысла проекта."""


def normalize_whitespace(value: str) -> str:
    return " ".join(value.split())
