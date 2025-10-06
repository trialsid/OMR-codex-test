from PIL import Image, ImageDraw

from omr import evaluator, template


def _make_template() -> template.Template:
    return template.Template(
        name="Eval",
        page_width_mm=20.0,
        page_height_mm=20.0,
        bubbles=[
            template.Bubble("Q1", "A", 10.0, 10.0, 3.0),
        ],
    )


def _filled_image(fill: bool) -> Image.Image:
    size_px = 200
    image = Image.new("L", (size_px, size_px), 255)
    if fill:
        draw = ImageDraw.Draw(image)
        draw.ellipse((size_px / 2 - 30, size_px / 2 - 30, size_px / 2 + 30, size_px / 2 + 30), fill=0)
    return image


def test_evaluator_detects_filled_bubble():
    tmpl = _make_template()
    image = _filled_image(True)
    results = evaluator.evaluate(tmpl, image, threshold=0.6)
    assert results[("Q1", "A")] is True


def test_evaluator_detects_empty_bubble():
    tmpl = _make_template()
    image = _filled_image(False)
    results = evaluator.evaluate(tmpl, image, threshold=0.4)
    assert results[("Q1", "A")] is False
