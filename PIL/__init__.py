"""Lightweight stand-in for the Pillow API used in tests."""
from . import Image, ImageDraw, ImageFont, ImageStat

__all__ = [
    "Image",
    "ImageDraw",
    "ImageFont",
    "ImageStat",
]
