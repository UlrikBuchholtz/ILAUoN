#!/usr/bin/env python3
"""Inventory generated artifacts and static HTML anchors, without validation."""

import argparse
from collections import Counter
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import sys


class Anchors(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = Counter()
        self.names = set()

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if attributes.get("id") is not None:
            self.ids[attributes["id"]] += 1
        if tag == "a" and attributes.get("name") is not None:
            self.names.add(attributes["name"])


def inventory(root):
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"Root is not a directory: {root}")
    paths = []

    def walk_error(error):
        raise error

    for directory, directories, files in os.walk(root, followlinks=False, onerror=walk_error):
        for name in directories + files:
            path = Path(directory) / name
            if path.is_symlink():
                raise ValueError(f"Symlinks are not supported: {path.relative_to(root)}")
        for name in files:
            path = Path(directory) / name
            if not path.is_file():
                raise ValueError(f"Not a regular file: {path.relative_to(root)}")
            paths.append(path)

    artifacts = []
    html_files = fragments = 0
    for path in sorted(paths, key=lambda path: path.relative_to(root).as_posix()):
        relative = path.relative_to(root)
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
                size += len(chunk)
        artifact = {"path": relative.as_posix(), "bytes": size, "sha256": digest.hexdigest()}
        if path.suffix.lower() in (".html", ".htm"):
            anchors = Anchors()
            with path.open(encoding="utf-8-sig") as stream:
                for chunk in iter(lambda: stream.read(65536), ""):
                    anchors.feed(chunk)
            anchors.close()
            fragment = relative.parts[0] == "knowl"
            artifact["html"] = {
                "kind": "knowl_fragment" if fragment else "page",
                "ids": sorted(anchors.ids),
                "named_anchors": sorted(anchors.names),
                "duplicate_ids": {name: count for name, count in anchors.ids.items() if count > 1},
            }
            html_files += 1
            fragments += fragment
        artifacts.append(artifact)
    return {
        "schema_version": 1,
        "limitations": [
            "Static generated-output inventory only; no runtime, rendering, accessibility or link validation.",
            "Paths are root-relative POSIX artifact paths, not deployment URLs; no full text is included.",
            "HTML is .html/.htm decoded as UTF-8; IDs and a[name] values are HTML-decoded and sorted uniquely.",
            "duplicate_ids counts element occurrences within each file, not across files.",
            "HTML under knowl/ is labeled knowl_fragment, not a standalone page.",
            "Symlinks and non-regular files are rejected; inventory an unchanged output tree.",
        ],
        "summary": {"files": len(artifacts), "html_files": html_files,
                    "html_pages": html_files - fragments, "knowl_fragments": fragments,
                    "bytes": sum(artifact["bytes"] for artifact in artifacts)},
        "artifacts": artifacts,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="generated output directory")
    parser.add_argument("--output", required=True, type=Path, help="JSON destination; parent must exist")
    args = parser.parse_args()
    try:
        root = args.root.resolve(strict=True)
        if args.output.resolve().is_relative_to(root):
            raise ValueError("JSON destination must be outside the inventory root")
        result = json.dumps(inventory(root), indent=2, sort_keys=True, ensure_ascii=True) + "\n"
        args.output.write_text(result, encoding="utf-8")
    except (OSError, ValueError) as error:
        parser.exit(1, f"Inventory failed: {error}\n")


if __name__ == "__main__":
    main()
