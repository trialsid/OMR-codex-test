from __future__ import annotations

import math
from typing import Iterable, Sequence, Tuple

from .Image import Image
from . import ImageFont


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

    def rectangle(
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
        x0, y0, x1, y1 = map(float, (x0, y0, x1, y1))
        if fill is not None:
            for y in range(int(math.floor(y0)), int(math.ceil(y1)) + 1):
                if 0 <= y < self.image.height:
                    for x in range(int(math.floor(x0)), int(math.ceil(x1)) + 1):
                        if 0 <= x < self.image.width:
                            self.image.putpixel((x, y), fill)
        if outline is not None:
            self.line((x0, y0, x1, y0), fill=outline, width=width)
            self.line((x1, y0, x1, y1), fill=outline, width=width)
            self.line((x0, y1, x1, y1), fill=outline, width=width)
            self.line((x0, y0, x0, y1), fill=outline, width=width)

    def line(
        self,
        coordinates: Sequence[float] | Iterable[Tuple[float, float]],
        fill=None,
        width: int = 1,
    ) -> None:
        if isinstance(coordinates, Iterable) and not isinstance(coordinates, (tuple, list)):
            points = list(coordinates)
        else:
            points = list(coordinates)
        if len(points) == 4:
            x0, y0, x1, y1 = points
            points = [(x0, y0), (x1, y1)]
        width = max(1, int(width))
        for start, end in zip(points[:-1], points[1:]):
            x0, y0 = start
            x1, y1 = end
            x0, y0, x1, y1 = map(float, (x0, y0, x1, y1))
            dx = abs(x1 - x0)
            dy = -abs(y1 - y0)
            sx = 1 if x0 < x1 else -1
            sy = 1 if y0 < y1 else -1
            err = dx + dy
            x, y = x0, y0
            while True:
                for ix in range(int(x) - width // 2, int(x) + width // 2 + 1):
                    for iy in range(int(y) - width // 2, int(y) + width // 2 + 1):
                        if 0 <= ix < self.image.width and 0 <= iy < self.image.height and fill is not None:
                            self.image.putpixel((ix, iy), fill)
                if int(x) == int(x1) and int(y) == int(y1):
                    break
                e2 = 2 * err
                if e2 >= dy:
                    err += dy
                    x += sx
                if e2 <= dx:
                    err += dx
                    y += sy

    def text(
        self,
        position: Tuple[float, float],
        text: str,
        *,
        font: ImageFont.ImageFont | None = None,
        fill=None,
    ) -> None:
        font = font or ImageFont.load_default()
        x, y = position
        bbox = font.getbbox(text)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        for yi in range(int(y), int(y + height)):
            if 0 <= yi < self.image.height:
                for xi in range(int(x), int(x + width)):
                    if 0 <= xi < self.image.width and fill is not None:
                        self.image.putpixel((xi, yi), fill)


def Draw(image: Image) -> _Draw:
    return _Draw(image)


__all__ = ["Draw"]
