#!/usr/bin/env python3
"""Capture selected physical PDF pages with Poppler; not a conformance test."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--pages", type=int, nargs="+",
                        default=[1, 30, 50, 180, 245, 296, 426, 458])
    args = parser.parse_args()
    try:
        info = subprocess.check_output(["pdfinfo", str(args.pdf)], text=True)
        total = int(next(line.split(":", 1)[1] for line in info.splitlines()
                         if line.startswith("Pages:")))
        if any(page < 1 or page > total for page in args.pages):
            raise ValueError(f"Physical pages must be between 1 and {total}")
        args.artifacts.mkdir(parents=True, exist_ok=True)
        captures = []
        for page in args.pages:
            prefix = args.artifacts / f"physical-page-{page:03}"
            image_run = subprocess.run(
                ["pdftoppm", "-f", str(page), "-l", str(page), "-singlefile",
                 "-scale-to", "1600", "-png", str(args.pdf), str(prefix)],
                check=True, capture_output=True, text=True)
            text_run = subprocess.run(
                ["pdftotext", "-f", str(page), "-l", str(page), "-layout",
                 str(args.pdf), "-"], check=True, capture_output=True, text=True)
            prefix.with_suffix(".txt").write_text(text_run.stdout, encoding="utf-8")
            image = prefix.with_suffix(".png")
            captures.append({"physical_page": page, "image": str(image),
                             "sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
                             "text_characters": len(text_run.stdout),
                             "diagnostics": image_run.stderr + text_run.stderr})
        result = {
            "pdf_sha256": hashlib.sha256(args.pdf.read_bytes()).hexdigest(),
            "pdfinfo": info,
            "poppler_version": subprocess.run(["pdftoppm", "-v"], check=True,
                                               capture_output=True, text=True).stderr,
            "limitations": ["Physical PDF page numbers, not printed page labels.",
                            "Selected pages only; text extraction is not semantic math validation.",
                            "No PDF/UA or assistive-technology test."],
            "captures": captures,
        }
        args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, StopIteration, subprocess.CalledProcessError) as error:
        parser.exit(1, f"PDF capture failed: {error}\n")


if __name__ == "__main__":
    main()
