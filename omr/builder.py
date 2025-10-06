"""Sheet rendering utilities for OMR templates.

Bubble coordinates follow the template convention: origin at the top-left of the
page, with positions specified in millimetres. Rendered sheets convert those
values into pixels using the requested DPI.
"""
from __future__ import annotations

from typing import Tuple

from PIL import Image, ImageDraw

from . import config, template


def sheet_dimensions(template_obj: template.Template, dpi: int) -> Tuple[int, int]:
    """Return the (width, height) in pixels for the rendered sheet."""
    width_px = config.mm_to_pixels(template_obj.page_width_mm, dpi)
    height_px = config.mm_to_pixels(template_obj.page_height_mm, dpi)
    return width_px, height_px


def build_sheet(template_obj: template.Template, dpi: int = 300) -> Image.Image:
    """Render the template into a printable grayscale PIL image."""
    width_px, height_px = sheet_dimensions(template_obj, dpi)
    image = Image.new("L", (width_px, height_px), color=255)
    draw = ImageDraw.Draw(image)

    for bubble in template_obj.bubbles:
        cx = config.mm_to_pixels(bubble.center_x_mm, dpi)
        cy = config.mm_to_pixels(bubble.center_y_mm, dpi)
        radius = max(1, config.mm_to_pixels(bubble.radius_mm, dpi))
        bounding_box = [
            (cx - radius, cy - radius),
            (cx + radius, cy + radius),
        ]
        draw.ellipse(bounding_box, outline=0, width=max(1, radius // 8))
    return image
