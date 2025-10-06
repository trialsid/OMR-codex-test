from __future__ import annotations

import io
import json
from pathlib import Path

from omr import builder, template
from omr.webapp import create_app


def _load_template_bytes() -> bytes:
    template_path = Path(__file__).resolve().parent.parent / "template.json"
    return template_path.read_bytes()


def test_index_page_lists_workflows(tmp_path: Path) -> None:
    app = create_app(output_dir=tmp_path)
    app.config.update(TESTING=True)
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Available workflows" in response.data


def test_build_endpoint_renders_sheet(tmp_path: Path) -> None:
    app = create_app(output_dir=tmp_path)
    app.config.update(TESTING=True)
    client = app.test_client()

    data = {
        "dpi": "150",
        "show_option_guides": "on",
        "template_file": (io.BytesIO(_load_template_bytes()), "template.json"),
    }
    response = client.post("/build", data=data, content_type="multipart/form-data")

    assert response.status_code == 200
    assert b"Rendered sheet" in response.data
    saved = list(tmp_path.rglob("*.png"))
    assert saved, "expected rendered image to be written to disk"


def test_grade_endpoint_evaluates_scan(tmp_path: Path) -> None:
    app = create_app(output_dir=tmp_path)
    app.config.update(TESTING=True)
    client = app.test_client()

    tmpl = template.Template.from_json(_load_template_bytes().decode("utf-8"))
    sheet = builder.build_sheet(tmpl, dpi=120)
    buffer = io.BytesIO()
    sheet.save(buffer, format="PNG")
    sheet.close()
    buffer.seek(0)

    data = {
        "threshold": "0.6",
        "template_file": (io.BytesIO(_load_template_bytes()), "template.json"),
        "image_file": (buffer, "scan.png"),
    }
    response = client.post("/grade", data=data, content_type="multipart/form-data")

    assert response.status_code == 200
    assert b"Evaluation summary" in response.data
    assert b"No marks detected" in response.data
    saved = list(tmp_path.rglob("evaluation_results.json"))
    assert saved, "expected evaluation report to be saved"
    report = json.loads(saved[0].read_text())
    assert "Q1:A" in report


def test_demo_endpoint_generates_bundle(tmp_path: Path) -> None:
    app = create_app(output_dir=tmp_path)
    app.config.update(TESTING=True)
    client = app.test_client()

    response = client.post("/demo", data={"seed": "42"})

    assert response.status_code == 200
    assert b"Demo bundle ready" in response.data
    assert b"%5C" not in response.data
    artefacts = list(tmp_path.rglob("modern_exam_template.json"))
    assert artefacts, "expected demo artefacts to be written"
