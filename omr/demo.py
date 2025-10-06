"""Utilities to generate demonstration OMR artefacts.

The module builds a modern-looking OMR template, renders a pristine sheet,
creates a synthetic response sheet with randomly filled bubbles, evaluates that
sheet, and produces a visual overlay illustrating the detected marks.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence

from PIL import Image, ImageDraw, ImageFont

from . import builder, evaluator, template

DPI = 300


@dataclass
class DemoArtefacts:
    """Paths written to disk when generating demo artefacts."""

    base_dir: Path
    template_path: Path
    sheet_path: Path
    filled_sheet_path: Path
    evaluation_image_path: Path
    evaluation_report_path: Path


def _option_labels(options: Sequence[str] | None) -> Sequence[str]:
    return options if options is not None else ("A", "B", "C", "D")


def _load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    font_name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(font_name, size=size)
    except OSError:  # pragma: no cover - triggered when fonts unavailable.
        return ImageFont.load_default()


def create_modern_template(
    *,
    num_questions: int = 20,
    options: Sequence[str] | None = None,
) -> template.Template:
    """Return a template with two columns of questions and tracking margins."""

    option_labels = _option_labels(options)
    page_width_mm = 210.0
    page_height_mm = 297.0
    column_count = 2
    rows_per_column = (num_questions + column_count - 1) // column_count

    column_width_mm = 85.0
    column_gutter_mm = 10.0
    start_y_mm = 60.0
    row_spacing_mm = 11.5
    option_spacing_mm = 12.0
    radius_mm = 4.5

    bubbles: List[template.Bubble] = []
    question_number = 1
    for column in range(column_count):
        column_start_x = 25.0 + column * (column_width_mm + column_gutter_mm)
        for row in range(rows_per_column):
            if question_number > num_questions:
                break
            center_y = start_y_mm + row * row_spacing_mm
            for index, option_id in enumerate(option_labels):
                center_x = column_start_x + index * option_spacing_mm
                bubbles.append(
                    template.Bubble(
                        question_id=f"Q{question_number:02d}",
                        option_id=str(option_id),
                        center_x_mm=center_x,
                        center_y_mm=center_y,
                        radius_mm=radius_mm,
                    )
                )
            question_number += 1

    tmpl = template.Template(
        name="Modern Assessment OMR",  # header uses this name directly
        page_width_mm=page_width_mm,
        page_height_mm=page_height_mm,
        bubbles=bubbles,
    )
    tmpl.ensure_unique_bubbles()
    return tmpl


def _group_by_question(
    tmpl: template.Template,
) -> Dict[str, List[template.Bubble]]:
    grouped: Dict[str, List[template.Bubble]] = {}
    for bubble in tmpl.bubbles:
        grouped.setdefault(bubble.question_id, []).append(bubble)
    for bubbles in grouped.values():
        bubbles.sort(key=lambda b: b.option_id)
    return grouped


def _fill_bubbles(
    image: Image.Image,
    tmpl: template.Template,
    selections: Dict[str, str],
    *,
    dpi: int,
) -> None:
    draw = ImageDraw.Draw(image)
    grouped = _group_by_question(tmpl)
    for question_id, option_id in selections.items():
        bubble_map = {b.option_id: b for b in grouped[question_id]}
        bubble = bubble_map[option_id]
        bbox = builder.bubble_bounds_px(bubble, dpi)
        draw.ellipse(bbox, fill=0)


def _build_evaluation_overlay(
    base_image: Image.Image,
    tmpl: template.Template,
    results: evaluator.EvaluationResult,
    *,
    dpi: int,
) -> Image.Image:
    overlay = base_image.copy()
    draw = ImageDraw.Draw(overlay)

    total_marked = 0
    for bubble in tmpl.bubbles:
        bbox = builder.bubble_bounds_px(bubble, dpi)
        pad = max(3, (bbox[2] - bbox[0]) // 6)
        padded = (
            bbox[0] - pad,
            bbox[1] - pad,
            bbox[2] + pad,
            bbox[3] + pad,
        )
        filled = bool(results.get(bubble.key))
        if filled:
            total_marked += 1
            draw.ellipse(padded, outline=0, width=4)
        else:
            draw.ellipse(padded, outline=128, width=2)

    summary_font = _load_font(size=20, bold=True)
    draw.text((20, 20), f"Detected marks: {total_marked} of {len(tmpl.bubbles)}", font=summary_font, fill=0)
    return overlay


def _serialise_results(
    tmpl: template.Template,
    selections: Dict[str, str],
    results: evaluator.EvaluationResult,
    destination: Path,
) -> None:
    per_question: Dict[str, List[str]] = {}
    for question in tmpl.iter_questions():
        question_results = results.answers_for_question(question)
        per_question[question] = [option for option, filled in question_results.items() if filled]

    payload = {
        "selected_answers": selections,
        "detected_answers": per_question,
        "raw": {f"{q}:{o}": filled for (q, o), filled in results.items()},
    }
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def generate_demo_assets(base_dir: Path, *, seed: int = 1234) -> DemoArtefacts:
    """Generate modern OMR demo artefacts under ``base_dir``."""

    sheet_dir = base_dir / "sheets"
    filled_dir = base_dir / "filled"
    evaluation_dir = base_dir / "evaluations"
    data_dir = base_dir / "data"

    for path in (sheet_dir, filled_dir, evaluation_dir, data_dir):
        path.mkdir(parents=True, exist_ok=True)

    tmpl = create_modern_template()
    template_path = data_dir / "modern_exam_template.json"
    tmpl.dump(str(template_path))

    sheet_image = builder.build_sheet(tmpl, dpi=DPI)
    sheet_path = sheet_dir / "modern_exam_sheet.png"
    sheet_image.save(sheet_path)

    random.seed(seed)
    grouped = _group_by_question(tmpl)
    selections = {
        question: random.choice([bubble.option_id for bubble in bubbles])
        for question, bubbles in grouped.items()
    }

    filled_sheet = sheet_image.copy()
    _fill_bubbles(filled_sheet, tmpl, selections, dpi=DPI)
    filled_sheet_path = filled_dir / "modern_exam_random_fill.png"
    filled_sheet.save(filled_sheet_path)

    results = evaluator.evaluate(tmpl, filled_sheet, threshold=0.55)
    evaluation_image = _build_evaluation_overlay(filled_sheet, tmpl, results, dpi=DPI)
    evaluation_image_path = evaluation_dir / "modern_exam_evaluated.png"
    evaluation_image.save(evaluation_image_path)

    evaluation_report_path = evaluation_dir / "modern_exam_results.json"
    _serialise_results(tmpl, selections, results, evaluation_report_path)

    return DemoArtefacts(
        base_dir=base_dir,
        template_path=template_path,
        sheet_path=sheet_path,
        filled_sheet_path=filled_sheet_path,
        evaluation_image_path=evaluation_image_path,
        evaluation_report_path=evaluation_report_path,
    )

