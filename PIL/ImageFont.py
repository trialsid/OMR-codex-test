"""Minimal ImageFont stand-in for drawing text in tests."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ImageFont:
    size: int = 10

    def getbbox(self, text: str) -> tuple[int, int, int, int]:
        width = max(1, int(len(text) * self.size * 0.6))
        height = max(1, int(self.size))
        return (0, 0, width, height)


def load_default() -> ImageFont:
    return ImageFont(size=10)


def truetype(_font: str, size: int = 10, **_kwargs) -> ImageFont:  # pragma: no cover - signature compatibility
    return ImageFont(size=size)


__all__ = ["ImageFont", "load_default", "truetype"]

