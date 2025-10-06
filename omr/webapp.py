"""Flask web interface for the OMR toolkit."""
from __future__ import annotations

import io
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List

from flask import Flask, Response, jsonify, render_template, request, url_for
from PIL import Image
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from . import builder, demo, evaluator, template

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "artifacts" / "webapp"


def create_app(output_dir: Path | None = None) -> Flask:
    """Create and configure the Flask application."""

    app = Flask(__name__)
    app.config["SECRET_KEY"] = "omr-webapp"
    resolved_output = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    resolved_output.mkdir(parents=True, exist_ok=True)
    app.config["OUTPUT_DIR"] = resolved_output

    def _create_run_dir(feature: str) -> Path:
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")
        run_dir = resolved_output / feature / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def _relative_to_output(path: Path) -> str:
        return path.relative_to(resolved_output).as_posix()

    def _serve_path(filename: str, *, as_attachment: bool = False) -> Response:
        from flask import send_from_directory

        return send_from_directory(
            resolved_output,
            filename,
            as_attachment=as_attachment,
            max_age=0,
        )

    def _parse_template(upload: FileStorage) -> template.Template:
        data = upload.read()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Template must be UTF-8 encoded JSON") from exc
        return template.Template.from_json(text)

    def _build_question_summary(
        tmpl: template.Template, result: evaluator.EvaluationResult
    ) -> List[Dict[str, Iterable[str]]]:
        summary: List[Dict[str, Iterable[str]]] = []
        for question in tmpl.iter_questions():
            answers = result.answers_for_question(question)
            filled = sorted(option for option, marked in answers.items() if marked)
            summary.append({"question": question, "options": filled})
        return summary

    def _normalise_options(raw: object) -> List[str]:
        options: List[str]
        if isinstance(raw, list):
            options = [str(option).strip() for option in raw]
        elif isinstance(raw, str):
            separators = [",", "\n", "\r"]
            cleaned = raw
            for sep in separators:
                cleaned = cleaned.replace(sep, ",")
            options = [part.strip() for part in cleaned.split(",")]
        else:
            options = []
        filtered = [option for option in options if option]
        if not filtered:
            return ["A", "B", "C", "D"]
        return filtered

    def _auto_template_from_config(
        *,
        name: str,
        page_width_mm: float,
        page_height_mm: float,
        question_count: int,
        options: List[str],
    ) -> template.Template:
        base_template = demo.create_modern_template(
            num_questions=question_count, options=options
        )
        base_template.name = name or base_template.name
        base_template.page_width_mm = page_width_mm
        base_template.page_height_mm = page_height_mm
        return base_template

    def _template_from_manual_payload(
        *,
        name: str,
        page_width_mm: float,
        page_height_mm: float,
        payload: object,
    ) -> template.Template:
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Manual bubble JSON is invalid: {exc}") from exc

        if isinstance(payload, dict):
            try:
                manual_template = template.Template.from_dict(payload)
            except Exception as exc:  # pragma: no cover - surfaced to user
                raise ValueError(f"Manual template data is invalid: {exc}") from exc
        elif isinstance(payload, list):
            try:
                bubbles = [template.Bubble.from_dict(entry) for entry in payload]
            except Exception as exc:  # pragma: no cover - surfaced to user
                raise ValueError(f"Manual bubble entry is invalid: {exc}") from exc
            manual_template = template.Template(
                name=name or "Custom Template",
                page_width_mm=page_width_mm,
                page_height_mm=page_height_mm,
                bubbles=bubbles,
            )
        else:
            raise ValueError("Manual bubble data must be a JSON list or object.")

        if name:
            manual_template.name = name
        manual_template.page_width_mm = page_width_mm
        manual_template.page_height_mm = page_height_mm
        return manual_template

    @app.route("/")
    def index() -> str:
        return render_template(
            "index.html", title="OMR Toolkit Dashboard", active_page="home"
        )

    @app.route("/designer")
    def designer() -> str:
        return render_template(
            "designer.html",
            title="Template Designer",
            active_page="designer",
        )

    @app.route("/api/template/preview", methods=["POST"])
    def template_preview() -> Response:
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return jsonify({"error": "JSON object expected."}), 400

        name = str(payload.get("name") or "Custom Template")
        try:
            page_width_mm = float(payload.get("page_width_mm", 210.0))
            page_height_mm = float(payload.get("page_height_mm", 297.0))
        except (TypeError, ValueError) as exc:
            return jsonify({"error": f"Page dimensions must be numbers: {exc}"}), 400

        manual_payload = payload.get("manual_bubbles")

        if manual_payload:
            try:
                tmpl = _template_from_manual_payload(
                    name=name,
                    page_width_mm=page_width_mm,
                    page_height_mm=page_height_mm,
                    payload=manual_payload,
                )
            except ValueError as exc:
                return jsonify({"error": str(exc)}), 400
        else:
            try:
                question_count = int(payload.get("question_count", 20))
            except (TypeError, ValueError):
                return jsonify({"error": "Question count must be an integer."}), 400
            if question_count <= 0:
                return jsonify({"error": "Question count must be positive."}), 400
            options = _normalise_options(payload.get("options"))
            tmpl = _auto_template_from_config(
                name=name,
                page_width_mm=page_width_mm,
                page_height_mm=page_height_mm,
                question_count=question_count,
                options=options,
            )

        try:
            tmpl.ensure_unique_bubbles()
        except ValueError as exc:  # pragma: no cover - surfaced to user
            return jsonify({"error": str(exc)}), 400

        try:
            image = builder.build_sheet(tmpl, dpi=300)
        except Exception as exc:  # pragma: no cover - surfaced to user
            return jsonify({"error": f"Failed to build preview: {exc}"}), 500

        run_dir = _create_run_dir("designer")
        template_filename = secure_filename(name) or "template"
        template_path = run_dir / f"{template_filename}.json"
        template_json = tmpl.to_json()
        template_path.write_text(template_json, encoding="utf-8")

        preview_path = run_dir / "preview.png"
        try:
            image.save(preview_path)
        finally:
            image.close()

        template_rel = _relative_to_output(template_path)
        preview_rel = _relative_to_output(preview_path)

        response_payload = {
            "template_json": template_json,
            "template_url": url_for("serve_file", filename=template_rel),
            "template_download_url": url_for("download_file", filename=template_rel),
            "preview_url": url_for("serve_file", filename=preview_rel),
            "preview_download_url": url_for("download_file", filename=preview_rel),
        }
        return jsonify(response_payload)

    @app.route("/build", methods=["GET", "POST"])
    def build_sheet() -> str:
        errors: List[str] = []
        result_context: Dict[str, object] | None = None
        dpi_value = request.form.get("dpi", "300")
        show_guides = request.form.get("show_option_guides") == "on"

        if request.method == "POST":
            upload = request.files.get("template_file")
            if upload is None or upload.filename == "":
                errors.append("A template JSON file is required.")
            try:
                dpi = int(dpi_value)
                if dpi <= 0:
                    raise ValueError
            except ValueError:
                errors.append("DPI must be a positive integer.")
                dpi = 300

            if not errors and upload is not None:
                try:
                    template_obj = _parse_template(upload)
                    image = builder.build_sheet(
                        template_obj,
                        dpi=dpi,
                        show_option_guides=show_guides,
                    )
                    run_dir = _create_run_dir("build")
                    filename = secure_filename(f"rendered_{dpi}dpi.png") or "rendered.png"
                    image_path = run_dir / filename
                    image.save(image_path)
                    rel_path = _relative_to_output(image_path)
                    result_context = {
                        "path": str(image_path),
                        "download_url": url_for("download_file", filename=rel_path),
                        "preview_url": url_for("serve_file", filename=rel_path),
                        "dpi": dpi,
                        "template_name": template_obj.name,
                    }
                except Exception as exc:  # pragma: no cover - caught for user feedback
                    errors.append(f"Failed to render template: {exc}")

        return render_template(
            "build.html",
            title="Render a Template",
            active_page="build",
            errors=errors,
            result=result_context,
            form_values={
                "dpi": dpi_value,
                "show_option_guides": show_guides,
            },
        )

    @app.route("/grade", methods=["GET", "POST"])
    def grade_sheet() -> str:
        errors: List[str] = []
        result_context: Dict[str, object] | None = None
        threshold_value = request.form.get("threshold", "0.5")

        if request.method == "POST":
            template_upload = request.files.get("template_file")
            image_upload = request.files.get("image_file")
            try:
                threshold = float(threshold_value)
            except ValueError:
                errors.append("Threshold must be a number between 0 and 1.")
                threshold = 0.5

            if template_upload is None or template_upload.filename == "":
                errors.append("A template JSON file is required.")
            if image_upload is None or image_upload.filename == "":
                errors.append("A scanned sheet image is required.")

            if not errors and template_upload is not None and image_upload is not None:
                try:
                    template_obj = _parse_template(template_upload)
                    image_data = image_upload.read()
                    pil_image = Image.open(io.BytesIO(image_data))
                except Exception as exc:  # pragma: no cover - surfaced to user
                    errors.append(f"Failed to read inputs: {exc}")
                else:
                    try:
                        try:
                            results = evaluator.evaluate(
                                template_obj, pil_image, threshold=threshold
                            )
                        finally:
                            pil_image.close()
                        run_dir = _create_run_dir("grade")
                        json_path = run_dir / "evaluation_results.json"
                        serialised = {
                            f"{question}:{option}": filled
                            for (question, option), filled in results.items()
                        }
                        json_path.write_text(json.dumps(serialised, indent=2, sort_keys=True), encoding="utf-8")
                        rel_path = _relative_to_output(json_path)
                        result_context = {
                            "summary": _build_question_summary(template_obj, results),
                            "download_url": url_for("download_file", filename=rel_path),
                            "raw_url": url_for("serve_file", filename=rel_path),
                            "threshold": threshold,
                            "total_marked": sum(results.values()),
                            "total_bubbles": len(results),
                            "template_name": template_obj.name,
                        }
                    except Exception as exc:  # pragma: no cover - surfaced to user
                        errors.append(f"Failed to evaluate scan: {exc}")

        return render_template(
            "grade.html",
            title="Grade a Scan",
            active_page="grade",
            errors=errors,
            result=result_context,
            form_values={"threshold": threshold_value},
        )

    @app.route("/demo", methods=["GET", "POST"])
    def demo_assets() -> str:
        errors: List[str] = []
        result_context: Dict[str, object] | None = None
        seed_value = request.form.get("seed", "1234")

        if request.method == "POST":
            try:
                seed = int(seed_value)
            except ValueError:
                errors.append("Seed must be an integer.")
                seed = 1234

            if not errors:
                run_dir = _create_run_dir("demo")
                try:
                    artefacts = demo.generate_demo_assets(run_dir, seed=seed)
                    files = [
                        ("Template JSON", artefacts.template_path),
                        ("Blank Sheet", artefacts.sheet_path),
                        ("Filled Sheet", artefacts.filled_sheet_path),
                        ("Evaluation Overlay", artefacts.evaluation_image_path),
                        ("Evaluation Report", artefacts.evaluation_report_path),
                    ]
                    file_entries = [
                        {
                            "label": label,
                            "path": str(path),
                            "preview_url": url_for("serve_file", filename=_relative_to_output(path)),
                            "download_url": url_for("download_file", filename=_relative_to_output(path)),
                        }
                        for label, path in files
                    ]
                    result_context = {
                        "files": file_entries,
                        "seed": seed,
                        "base_dir": str(artefacts.base_dir),
                    }
                except Exception as exc:  # pragma: no cover - surfaced to user
                    errors.append(f"Failed to generate demo artefacts: {exc}")

        return render_template(
            "demo.html",
            title="Generate Demo Artefacts",
            active_page="demo",
            errors=errors,
            result=result_context,
            form_values={"seed": seed_value},
        )

    @app.route("/files/<path:filename>")
    def serve_file(filename: str) -> Response:
        return _serve_path(filename, as_attachment=False)

    @app.route("/download/<path:filename>")
    def download_file(filename: str) -> Response:
        return _serve_path(filename, as_attachment=True)

    return app


app = create_app()


if __name__ == "__main__":  # pragma: no cover
    app.run(debug=True)
