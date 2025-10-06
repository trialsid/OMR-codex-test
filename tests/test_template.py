from omr import template


def test_template_round_trip():
    tmpl = template.Template(
        name="Sample",
        page_width_mm=210.0,
        page_height_mm=297.0,
        bubbles=[
            template.Bubble(
                question_id="Q1",
                option_id="A",
                center_x_mm=10.0,
                center_y_mm=20.0,
                radius_mm=3.0,
            )
        ],
    )

    json_data = tmpl.to_json()
    restored = template.Template.from_json(json_data)

    assert restored.name == tmpl.name
    assert restored.page_width_mm == tmpl.page_width_mm
    assert restored.page_height_mm == tmpl.page_height_mm
    assert len(restored.bubbles) == 1
    assert restored.bubbles[0].to_dict() == tmpl.bubbles[0].to_dict()
