from omr import builder, template
from omr.config import mm_to_pixels


def test_builder_dimensions():
    tmpl = template.Template(
        name="Sheet",
        page_width_mm=100.0,
        page_height_mm=150.0,
        bubbles=[],
    )

    dpi = 200
    image = builder.build_sheet(tmpl, dpi=dpi)
    expected_size = (
        mm_to_pixels(tmpl.page_width_mm, dpi),
        mm_to_pixels(tmpl.page_height_mm, dpi),
    )
    assert image.size == expected_size


def test_builder_hides_option_guides():
    bubble = template.Bubble("Q1", "A", 15.0, 15.0, 4.0)
    tmpl = template.Template(
        name="Sheet",
        page_width_mm=40.0,
        page_height_mm=40.0,
        bubbles=[bubble],
    )

    dpi = 300
    with_guides = builder.build_sheet(tmpl, dpi=dpi)
    without_guides = builder.build_sheet(tmpl, dpi=dpi, show_option_guides=False)

    cx = mm_to_pixels(bubble.center_x_mm, dpi)
    cy = mm_to_pixels(bubble.center_y_mm, dpi)
    region = (cx - 5, cy - 5, cx + 5, cy + 5)

    with_guides_crop = with_guides.crop(region)
    without_guides_crop = without_guides.crop(region)

    with_sum = sum(with_guides_crop.getdata())
    without_sum = sum(without_guides_crop.getdata())

    assert with_sum < without_sum


def test_draw_question_labels_assigns_numeric_sequence():
    tmpl = template.Template(
        name="Sheet",
        page_width_mm=80.0,
        page_height_mm=120.0,
        bubbles=[
            template.Bubble("Q10", "A", 30.0, 30.0, 4.0),
            template.Bubble("Q10", "B", 40.0, 30.0, 4.0),
            template.Bubble("Q2", "A", 30.0, 60.0, 4.0),
            template.Bubble("Q2", "B", 40.0, 60.0, 4.0),
        ],
    )

    captured = []

    class DummyDraw:
        def text(self, position, text, *, font=None, fill=None):
            captured.append(text)

    builder._draw_question_labels(DummyDraw(), tmpl, dpi=150)
    assert captured == ["1", "2"]
