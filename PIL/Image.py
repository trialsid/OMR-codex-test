from __future__ import annotations

import builtins
from dataclasses import dataclass
from typing import Iterable, List, Tuple


def new(mode: str, size: Tuple[int, int], color: int = 255) -> "Image":
    width, height = size
    pixels = [[int(color) for _ in range(width)] for _ in range(height)]
    return Image(mode=mode, width=width, height=height, pixels=pixels)


def open(path: str) -> "Image":
    with builtins.open(path, "r", encoding="utf-8") as handle:
        header = handle.readline().strip()
        if header != "P2":
            raise ValueError("Unsupported image format")
        dims = handle.readline().strip()
        while dims.startswith("#"):
            dims = handle.readline().strip()
        width, height = map(int, dims.split())
        max_value = int(handle.readline().strip())
        if max_value != 255:
            raise ValueError("Unsupported max value")
        data = []
        for line in handle:
            data.extend(int(value) for value in line.split())
        if len(data) != width * height:
            raise ValueError("Unexpected pixel count")
        pixels = [data[i * width : (i + 1) * width] for i in range(height)]
        return Image(mode="L", width=width, height=height, pixels=pixels)


def fromarray(array, mode: str | None = None) -> "Image":  # pragma: no cover - not used without numpy
    raise NotImplementedError("fromarray requires numpy and is not implemented in the stub")


@dataclass
class Image:
    mode: str
    width: int
    height: int
    pixels: List[List[int]]

    @property
    def size(self) -> Tuple[int, int]:
        return self.width, self.height

    def convert(self, mode: str) -> "Image":
        if mode != "L":
            raise ValueError("Only grayscale conversion is supported")
        return Image(mode="L", width=self.width, height=self.height, pixels=[row[:] for row in self.pixels])

    def crop(self, box: Tuple[int, int, int, int]) -> "Image":
        left, upper, right, lower = map(int, box)
        left = max(0, left)
        upper = max(0, upper)
        right = min(self.width, right)
        lower = min(self.height, lower)
        new_pixels = [row[left:right] for row in self.pixels[upper:lower]]
        return Image(mode=self.mode, width=right - left, height=lower - upper, pixels=new_pixels)

    def save(self, path: str) -> None:
        with builtins.open(path, "w", encoding="utf-8") as handle:
            handle.write("P2\n")
            handle.write(f"{self.width} {self.height}\n")
            handle.write("255\n")
            for row in self.pixels:
                handle.write(" ".join(str(min(255, max(0, int(value)))) for value in row) + "\n")

    def load(self) -> List[List[int]]:
        return self.pixels

    def getpixel(self, position: Tuple[int, int]) -> int:
        x, y = position
        return self.pixels[y][x]

    def putpixel(self, position: Tuple[int, int], value: int) -> None:
        x, y = position
        self.pixels[y][x] = int(value)

    def getdata(self) -> Iterable[int]:
        for row in self.pixels:
            for value in row:
                yield value
