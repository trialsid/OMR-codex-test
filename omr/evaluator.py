"""Image grading utilities for scanned OMR sheets.

The evaluator expects bubble coordinates in millimetres measured from the
sheet's top-left corner, mirroring the template and builder modules. Scanned
images are mapped into that coordinate space by measuring pixels-per-millimetre
from the image dimensions.
"""
from __future__ import annotations

from typing import Dict, Iterable, Tuple

try:  # Optional dependency
    import numpy as _np
except Exception:  # pragma: no cover - numpy is optional at runtime
    _np = None

from PIL import Image, ImageDraw, ImageStat

from . import template


class EvaluationResult(Dict[Tuple[str, str], bool]):
    """Dictionary subclass mapping (question_id, option_id) to filled state."""

    def answers_for_question(self, question_id: str) -> Dict[str, bool]:
        return {
            option_id: filled
            for (question, option_id), filled in self.items()
            if question == question_id
        }


def _to_grayscale(image: object) -> Image.Image:
    if isinstance(image, Image.Image):
        return image.convert("L")
    if _np is not None:
        array = _np.asarray(image)
        if array.ndim == 2:
            mode = "L"
        elif array.ndim == 3 and array.shape[2] == 3:
            mode = "RGB"
        elif array.ndim == 3 and array.shape[2] == 4:
            mode = "RGBA"
        else:  # pragma: no cover - unsupported shapes
            raise ValueError("Unsupported numpy array shape for evaluation")
        return Image.fromarray(array.astype("uint8"), mode=mode).convert("L")
    raise TypeError("Unsupported image type for evaluation")


def evaluate(
    template_obj: template.Template,
    image: object,
    threshold: float = 0.5,
) -> EvaluationResult:
    """Grade a scanned sheet and report which bubbles are filled."""
    grayscale = _to_grayscale(image)
    width_px, height_px = grayscale.size
    px_per_mm_x = width_px / template_obj.page_width_mm
    px_per_mm_y = height_px / template_obj.page_height_mm

    results: EvaluationResult = EvaluationResult()
    for bubble in template_obj.bubbles:
        cx = int(round(bubble.center_x_mm * px_per_mm_x))
        cy = int(round(bubble.center_y_mm * px_per_mm_y))
        radius_x = max(1, int(round(bubble.radius_mm * px_per_mm_x)))
        radius_y = max(1, int(round(bubble.radius_mm * px_per_mm_y)))

        x_min = max(0, cx - radius_x)
        x_max = min(width_px, cx + radius_x + 1)
        y_min = max(0, cy - radius_y)
        y_max = min(height_px, cy + radius_y + 1)

        region = grayscale.crop((x_min, y_min, x_max, y_max))
        if region.size == (0, 0):
            results[bubble.key] = False
            continue

        mask = Image.new("1", region.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, region.width - 1, region.height - 1), fill=1)
        stat = ImageStat.Stat(region, mask=mask)
        count = stat.count[0] if stat.count else 0
        mean_value = stat.mean[0] if count else 255.0

        normalised = mean_value / 255.0
        results[bubble.key] = normalised < threshold
    return results
