"""Command-line interface for building and grading OMR sheets.

Bubble coordinates follow the shared convention: origin at the sheet's top-left
corner with millimetre units. CLI commands rely on that coordinate system when
rendering templates or evaluating scans.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from PIL import Image

from . import builder, evaluator, template


def _add_build_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("build", help="Render a template to an image")
    parser.add_argument("template", type=Path, help="Path to the template JSON file")
    parser.add_argument("output", type=Path, help="Destination path for the rendered image")
    parser.add_argument("--dpi", type=int, default=300, help="Target DPI for rendering (default: 300)")
    parser.set_defaults(func=_handle_build)


def _add_grade_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("grade", help="Grade a scanned sheet against a template")
    parser.add_argument("template", type=Path, help="Path to the template JSON file")
    parser.add_argument("image", type=Path, help="Path to the scanned image file")
    parser.add_argument("--threshold", type=float, default=0.5, help="Normalised fill threshold (default: 0.5)")
    parser.add_argument("--output", type=Path, help="Write results to a JSON file instead of stdout")
    parser.set_defaults(func=_handle_grade)


def _handle_build(args: argparse.Namespace) -> int:
    template_obj = template.Template.load(str(args.template))
    image = builder.build_sheet(template_obj, dpi=args.dpi)
    image.save(str(args.output))
    return 0


def _handle_grade(args: argparse.Namespace) -> int:
    template_obj = template.Template.load(str(args.template))
    image = Image.open(str(args.image))
    results = evaluator.evaluate(template_obj, image, threshold=args.threshold)
    payload = {
        f"{question}:{option}": filled for (question, option), filled in results.items()
    }
    output_data = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(output_data, encoding="utf-8")
    else:
        print(output_data)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="omr", description="OMR sheet utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_build_parser(subparsers)
    _add_grade_parser(subparsers)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.error("No command provided")
    return func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
