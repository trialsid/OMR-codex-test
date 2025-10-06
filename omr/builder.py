"""Sheet rendering utilities for OMR templates.

Bubble coordinates follow the template convention: origin at the top-left of the
page, with positions specified in millimetres. Rendered sheets convert those
values into pixels using the requested DPI.
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, Tuple

from PIL import Image, ImageDraw, ImageFont

from . import config, template


def sheet_dimensions(template_obj: template.Template, dpi: int) -> Tuple[int, int]:
    """Return the (width, height) in pixels for the rendered sheet."""
    width_px = config.mm_to_pixels(template_obj.page_width_mm, dpi)
    height_px = config.mm_to_pixels(template_obj.page_height_mm, dpi)
    return width_px, height_px


def _load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Return a truetype font when available, otherwise fall back to default."""

    font_name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:  # Pillow ships DejaVu fonts by default.
        return ImageFont.truetype(font_name, size=size)
    except OSError:  # pragma: no cover - exercised only when fonts missing.
        return ImageFont.load_default()


def _group_bubbles_by_question(
    template_obj: template.Template,
) -> Dict[str, Iterable[template.Bubble]]:
    grouped: Dict[str, list[template.Bubble]] = {}
    for bubble in template_obj.bubbles:
        grouped.setdefault(bubble.question_id, []).append(bubble)
    for bubbles in grouped.values():
        bubbles.sort(key=lambda b: (b.center_x_mm, b.option_id))
    return grouped


def bubble_bounds_px(bubble: template.Bubble, dpi: int) -> Tuple[int, int, int, int]:
    """Return the bounding box for a bubble in pixel coordinates."""

    cx = config.mm_to_pixels(bubble.center_x_mm, dpi)
    cy = config.mm_to_pixels(bubble.center_y_mm, dpi)
    radius = max(1, config.mm_to_pixels(bubble.radius_mm, dpi))
    return (cx - radius, cy - radius, cx + radius, cy + radius)


def _draw_registration_markers(draw: ImageDraw.ImageDraw, width: int, height: int, dpi: int) -> None:
    marker_size = config.mm_to_pixels(8, dpi)
    offset = config.mm_to_pixels(5, dpi)
    inset = max(1, marker_size // 3)
    positions = (
        (offset, offset),
        (width - offset - marker_size, offset),
        (offset, height - offset - marker_size),
        (width - offset - marker_size, height - offset - marker_size),
    )
    for x, y in positions:
        outer = (x, y, x + marker_size, y + marker_size)
        inner = (x + inset, y + inset, x + marker_size - inset, y + marker_size - inset)
        draw.rectangle(outer, fill=0)
        draw.rectangle(inner, fill=255)
        draw.line((outer[0], y + marker_size // 2, outer[2], y + marker_size // 2), fill=0, width=2)
        draw.line((x + marker_size // 2, outer[1], x + marker_size // 2, outer[3]), fill=0, width=2)


def _draw_header(draw: ImageDraw.ImageDraw, template_obj: template.Template, width: int, dpi: int) -> int:
    """Draw the sheet header and return its pixel height."""

    header_height = config.mm_to_pixels(36, dpi)
    draw.rectangle([(0, 0), (width, header_height)], fill=235)

    title_font = _load_font(size=max(18, config.mm_to_pixels(6, dpi)), bold=True)
    label_font = _load_font(size=max(14, config.mm_to_pixels(4, dpi)))
    small_font = _load_font(size=max(12, config.mm_to_pixels(3, dpi)))

    padding = config.mm_to_pixels(10, dpi)
    text_y = padding // 2
    draw.text((padding, text_y), template_obj.name, font=title_font, fill=0)

    info_top = header_height - padding
    line_y = info_top
    line_length = config.mm_to_pixels(65, dpi)
    line_spacing = config.mm_to_pixels(6, dpi)

    draw.text((padding, info_top - line_spacing), "Candidate Name", font=label_font, fill=0)
    draw.line((padding, line_y, padding + line_length, line_y), fill=0, width=2)

    id_offset = padding + line_length + config.mm_to_pixels(12, dpi)
    draw.text((id_offset, info_top - line_spacing), "Candidate ID", font=label_font, fill=0)
    draw.line((id_offset, line_y, id_offset + line_length // 2, line_y), fill=0, width=2)

    instructions = (
        "Use a dark pen or pencil.",
        "Fill bubbles completely.",
        "Do not fold the sheet.",
    )
    instructions_x = width - padding - config.mm_to_pixels(70, dpi)
    bullet_y = padding // 2
    draw.text((instructions_x, bullet_y), "Instructions", font=label_font, fill=0)
    bullet_y += config.mm_to_pixels(8, dpi)
    for line in instructions:
        draw.text((instructions_x, bullet_y), f"• {line}", font=small_font, fill=0)
        bullet_y += config.mm_to_pixels(6, dpi)

    return header_height


def _draw_question_labels(
    draw: ImageDraw.ImageDraw,
    template_obj: template.Template,
    dpi: int,
) -> None:
    label_font = _load_font(size=max(12, config.mm_to_pixels(3.5, dpi)), bold=True)
    grouped = _group_bubbles_by_question(template_obj)
    for question_id, bubbles in grouped.items():
        min_x_mm = min(b.center_x_mm - b.radius_mm for b in bubbles)
        min_y_mm = min(b.center_y_mm for b in bubbles)
        text_x = config.mm_to_pixels(min_x_mm - 8, dpi)
        text_y = config.mm_to_pixels(min_y_mm, dpi)
        text_bbox = label_font.getbbox(question_id)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        draw.text(
            (text_x - text_width, text_y - text_height // 2),
            question_id,
            font=label_font,
            fill=0,
        )


def _draw_bubbles(draw: ImageDraw.ImageDraw, template_obj: template.Template, dpi: int) -> None:
    option_font = _load_font(size=max(12, config.mm_to_pixels(3, dpi)))
    stroke_width = max(1, config.mm_to_pixels(0.5, dpi))
    half_stroke = stroke_width / 2.0
    for bubble in template_obj.bubbles:
        bbox = bubble_bounds_px(bubble, dpi)
        padded_bbox = (
            math.floor(bbox[0] - half_stroke),
            math.floor(bbox[1] - half_stroke),
            math.ceil(bbox[2] + half_stroke),
            math.ceil(bbox[3] + half_stroke),
        )
        draw.ellipse(padded_bbox, outline=0, width=stroke_width)

        cx = (bbox[0] + bbox[2]) // 2
        cy = (bbox[1] + bbox[3]) // 2
        text = bubble.option_id
        text_bbox = option_font.getbbox(text)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        draw.text(
            (cx - text_width // 2, cy - text_height // 2),
            text,
            font=option_font,
            fill=0,
        )


def build_sheet(template_obj: template.Template, dpi: int = 300) -> Image.Image:
    """Render the template into a printable grayscale PIL image."""

    width_px, height_px = sheet_dimensions(template_obj, dpi)
    image = Image.new("L", (width_px, height_px), color=255)
    draw = ImageDraw.Draw(image)

    _draw_header(draw, template_obj, width_px, dpi)
    _draw_registration_markers(draw, width_px, height_px, dpi)
    _draw_bubbles(draw, template_obj, dpi)
    _draw_question_labels(draw, template_obj, dpi)
    return image
