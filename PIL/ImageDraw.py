from __future__ import annotations

import math
from typing import Iterable, Tuple

from .Image import Image


class _Draw:
    def __init__(self, image: Image):
        self.image = image

    def ellipse(
        self,
        bounding_box: Iterable[Tuple[float, float]] | Tuple[float, float, float, float],
        fill=None,
        outline=None,
        width: int = 1,
    ) -> None:
        if isinstance(bounding_box, tuple) and len(bounding_box) == 4:
            x0, y0, x1, y1 = bounding_box
        else:
            points = list(bounding_box)
            (x0, y0), (x1, y1) = points
        x0, y0, x1, y1 = float(x0), float(y0), float(x1), float(y1)
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2
        rx = max(1.0, abs(x1 - x0) / 2)
        ry = max(1.0, abs(y1 - y0) / 2)
        width = max(1, int(width))
        for y in range(int(math.floor(y0)), int(math.ceil(y1)) + 1):
            if y < 0 or y >= self.image.height:
                continue
            for x in range(int(math.floor(x0)), int(math.ceil(x1)) + 1):
                if x < 0 or x >= self.image.width:
                    continue
                value = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
                if fill is not None and value <= 1:
                    self.image.putpixel((x, y), fill)
                if outline is not None and 1 - (width / max(rx, ry)) <= value <= 1 + (width / max(rx, ry)):
                    self.image.putpixel((x, y), outline)


def Draw(image: Image) -> _Draw:
    return _Draw(image)


__all__ = ["Draw"]
