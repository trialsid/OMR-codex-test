from __future__ import annotations

from typing import List

from .Image import Image


class Stat:
    def __init__(self, image: Image, mask: Image | None = None):
        if mask is not None and (mask.width != image.width or mask.height != image.height):
            raise ValueError("Mask must match image dimensions")
        values: List[int] = []
        pixels = image.pixels
        if mask is None:
            for row in pixels:
                values.extend(row)
        else:
            for y in range(image.height):
                for x in range(image.width):
                    if mask.pixels[y][x]:
                        values.append(pixels[y][x])
        self.count = [len(values)]
        self.mean = [sum(values) / len(values)] if values else [0.0]


__all__ = ["Stat"]
