import json
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from omr import builder, cli, template


def _write_template(path: Path) -> None:
    tmpl = template.Template(
        name="CLI",
        page_width_mm=20.0,
        page_height_mm=20.0,
        bubbles=[template.Bubble("Q1", "A", 10.0, 10.0, 3.0)],
    )
    tmpl.dump(str(path))


def _create_scan(path: Path) -> None:
    size_px = 200
    image = Image.new("L", (size_px, size_px), 255)
    draw = ImageDraw.Draw(image)
    draw.ellipse((size_px / 2 - 30, size_px / 2 - 30, size_px / 2 + 30, size_px / 2 + 30), fill=0)
    image.save(path)


def test_cli_requires_command():
    parser = cli.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_cli_build_command(tmp_path):
    template_path = tmp_path / "template.json"
    output_path = tmp_path / "sheet.png"
    _write_template(template_path)

    exit_code = cli.main(["build", str(template_path), str(output_path), "--dpi", "150"])
    assert exit_code == 0
    assert output_path.exists()

    payload = output_path.read_bytes()
    assert payload.startswith(b"\x89PNG\r\n\x1a\n")

    reopened = Image.open(str(output_path))
    template_obj = template.Template.load(str(template_path))
    expected_size = builder.sheet_dimensions(template_obj, dpi=150)
    assert reopened.size == expected_size


def test_cli_grade_command(tmp_path, capsys):
    template_path = tmp_path / "template.json"
    image_path = tmp_path / "scan.png"
    _write_template(template_path)
    _create_scan(image_path)

    exit_code = cli.main(["grade", str(template_path), str(image_path), "--threshold", "0.6"])
    assert exit_code == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["Q1:A"] is True


def test_cli_demo_command(tmp_path):
    output_dir = tmp_path / "demo"
    exit_code = cli.main(["demo", str(output_dir), "--seed", "99"])
    assert exit_code == 0

    sheet_files = list((output_dir / "sheets").glob("*.png"))
    filled_files = list((output_dir / "filled").glob("*.png"))
    evaluation_images = list((output_dir / "evaluations").glob("*.png"))
    evaluation_reports = list((output_dir / "evaluations").glob("*.json"))

    assert sheet_files, "expected at least one rendered sheet"
    assert filled_files, "expected a synthetic filled sheet"
    assert evaluation_images, "expected an evaluated overlay"
    assert evaluation_reports, "expected a JSON evaluation report"
