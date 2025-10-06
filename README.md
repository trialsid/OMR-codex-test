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
3. After collecting responses, scan the sheet at 300 DPI or higher with even
   lighting and minimal skew. Ensure bubbles are clearly filled with dark ink.
4. Grade the scan and inspect the results:
   ```bash
   python -m omr.cli grade template.json scan.png --threshold 0.5
   ```

High-quality scans should maintain bubble edges without heavy compression to
ensure the evaluator can distinguish filled and unfilled bubbles.
