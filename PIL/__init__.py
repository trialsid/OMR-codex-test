"""Lightweight stand-in for the Pillow API used in tests."""
from . import Image, ImageDraw, ImageStat

__all__ = [
    "Image",
    "ImageDraw",
    "ImageStat",
]
