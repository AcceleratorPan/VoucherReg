from __future__ import annotations


def to_camel(snake: str) -> str:
    parts = snake.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])
