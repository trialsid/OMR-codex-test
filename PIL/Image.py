from __future__ import annotations

import builtins
import os
import struct
import zlib
from dataclasses import dataclass
from typing import Iterable, List, Tuple


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def new(mode: str, size: Tuple[int, int], color: int = 255) -> "Image":
    width, height = size
    pixels = [[int(color) for _ in range(width)] for _ in range(height)]
    return Image(mode=mode, width=width, height=height, pixels=pixels)


def open(path: str) -> "Image":
    with builtins.open(path, "rb") as handle:
        signature = handle.read(len(PNG_SIGNATURE))
        if signature == PNG_SIGNATURE:
            return _open_png(handle)

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
        _, ext = os.path.splitext(path)
        if ext.lower() == ".png":
            with builtins.open(path, "wb") as handle:
                _save_png(self, handle)
            return

        with builtins.open(path, "w", encoding="utf-8") as handle:
            handle.write("P2\n")
            handle.write(f"{self.width} {self.height}\n")
            handle.write("255\n")
            for row in self.pixels:
                handle.write(" ".join(str(_clamp_to_byte(value)) for value in row) + "\n")

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


def _clamp_to_byte(value: int) -> int:
    return max(0, min(255, int(value)))


def _write_png_chunk(handle, chunk_type: bytes, data: bytes) -> None:
    handle.write(struct.pack(">I", len(data)))
    handle.write(chunk_type)
    handle.write(data)
    crc = zlib.crc32(chunk_type)
    crc = zlib.crc32(data, crc) & 0xFFFFFFFF
    handle.write(struct.pack(">I", crc))


def _save_png(image: Image, handle) -> None:
    handle.write(PNG_SIGNATURE)
    ihdr = struct.pack(">IIBBBBB", image.width, image.height, 8, 0, 0, 0, 0)
    _write_png_chunk(handle, b"IHDR", ihdr)

    raw_data = bytearray()
    for row in image.pixels:
        raw_data.append(0)
        raw_data.extend(_clamp_to_byte(value) for value in row)
    compressed = zlib.compress(bytes(raw_data))
    _write_png_chunk(handle, b"IDAT", compressed)
    _write_png_chunk(handle, b"IEND", b"")


def _open_png(handle) -> Image:
    width = height = None
    bit_depth = color_type = None
    idat_data = bytearray()

    while True:
        length_bytes = handle.read(4)
        if len(length_bytes) != 4:
            raise ValueError("Truncated PNG file")
        length = struct.unpack(">I", length_bytes)[0]
        chunk_type = handle.read(4)
        if len(chunk_type) != 4:
            raise ValueError("Truncated PNG file")
        data = handle.read(length)
        if len(data) != length:
            raise ValueError("Truncated PNG file")
        crc_bytes = handle.read(4)
        if len(crc_bytes) != 4:
            raise ValueError("Truncated PNG file")
        expected_crc = struct.unpack(">I", crc_bytes)[0]
        crc = zlib.crc32(chunk_type)
        crc = zlib.crc32(data, crc) & 0xFFFFFFFF
        if crc != expected_crc:
            raise ValueError("Corrupted PNG file")

        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(
                ">IIBBBBB", data
            )
            if bit_depth != 8 or color_type != 0:
                raise ValueError("Unsupported PNG color type")
            if compression != 0 or filter_method != 0 or interlace != 0:
                raise ValueError("Unsupported PNG compression settings")
        elif chunk_type == b"IDAT":
            idat_data.extend(data)
        elif chunk_type == b"IEND":
            break

    if width is None or height is None or bit_depth is None or color_type is None:
        raise ValueError("Incomplete PNG file")

    decompressed = zlib.decompress(bytes(idat_data))
    stride = width
    expected_length = (stride + 1) * height
    if len(decompressed) != expected_length:
        raise ValueError("Unexpected PNG data length")

    pixels: List[List[int]] = []
    offset = 0
    for _ in range(height):
        filter_type = decompressed[offset]
        offset += 1
        if filter_type != 0:
            raise ValueError("Unsupported PNG filter type")
        row = list(decompressed[offset : offset + stride])
        offset += stride
        pixels.append(row)

    return Image(mode="L", width=width, height=height, pixels=pixels)
