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
