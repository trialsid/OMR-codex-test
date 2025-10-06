# OMR-codex-test

## Usage

1. Create a template JSON file describing your sheet layout.
2. Render a printable sheet:
   ```bash
   python -m omr.cli build template.json sheet.png
   ```
   The renderer inspects the destination extension: ``.png`` writes a
   standards-compliant 8-bit grayscale PNG, while other suffixes fall back to an
   ASCII PGM stream for compatibility with minimal environments.
   Add ``--hide-option-guides`` to omit the letter guides inside each bubble when
   printing practice or production sheets.
3. After collecting responses, scan the sheet at 300 DPI or higher with even
   lighting and minimal skew. Ensure bubbles are clearly filled with dark ink.
4. Grade the scan and inspect the results:
   ```bash
   python -m omr.cli grade template.json scan.png --threshold 0.5
   ```

High-quality scans should maintain bubble edges without heavy compression to
ensure the evaluator can distinguish filled and unfilled bubbles.

## Web dashboard

A browser-based dashboard is available for non-technical users who prefer
interacting with the toolkit visually. Install the dependencies and launch the
server with:

```bash
python -m omr.webapp
```

The application exposes three workflows from a single page:

- **Render** – upload a template JSON file, pick a DPI, and download the rendered sheet.
- **Grade** – upload a template and scanned response to see detected answers and save the JSON summary.
- **Demo** – produce the sample template, filled sheet, and evaluation overlay with one click.

Generated artefacts are written under `artifacts/webapp/` and are available via
download links directly in the UI.

## Modern demo workflow

To explore the full pipeline end-to-end, including a modern styled sheet,
synthetic responses, and an annotated evaluation image, run the demo command:

```bash
python -m omr.cli demo artifacts/modern_omr --seed 2024
```

The command writes artefacts to a structured directory:

```
artifacts/modern_omr/
├── data/modern_exam_template.json      # JSON template used for rendering
├── sheets/modern_exam_sheet.png        # Printable blank sheet (generated)
├── filled/modern_exam_random_fill.png  # Synthetic responses filled in (generated)
└── evaluations/
    ├── modern_exam_evaluated.png       # Visual overlay of detected marks (generated)
    └── modern_exam_results.json        # Machine-readable evaluation summary
```

To keep the repository light-weight, the generated PNG assets are ignored by
Git. Run the demo locally if you would like to inspect the images. All generated
images use a modern layout with alignment markers, a structured header, and
clearly labelled question rows to make manual review and automated grading
easier.
