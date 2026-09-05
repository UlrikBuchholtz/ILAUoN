#!/usr/bin/env python3
"""Audit static local HTML references; findings do not make the CLI fail."""

import argparse
from collections import Counter
from html.parser import HTMLParser
import json
import os
from pathlib import Path
from urllib.parse import unquote, urlsplit


class Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = Counter()
        self.names = set()
        self.refs = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if attributes.get("id") is not None:
            self.ids[attributes["id"]] += 1
        if tag == "a" and attributes.get("name") is not None:
            self.names.add(attributes["name"])
        for attr, ref in attrs:
            if attr in ("href", "src", "knowl", "xlink:href") and ref is not None:
                self.refs.append({"line": self.getpos()[0], "tag": tag,
                                  "attribute": attr, "ref": ref})


def audit(root):
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"Root is not a directory: {root}")
    documents = {}

    def walk_error(error):
        raise error

    for directory, directories, files in os.walk(root, onerror=walk_error):
        for name in directories + files:
            path = Path(directory) / name
            if path.is_symlink():
                raise ValueError(f"Symlinks are not supported: {path.relative_to(root)}")
        for name in files:
            path = Path(directory) / name
            if not path.is_file():
                raise ValueError(f"Not a regular file: {path.relative_to(root)}")
            if path.suffix.lower() in (".html", ".htm"):
                document = Document()
                document.feed(path.read_text(encoding="utf-8-sig"))
                document.close()
                documents[path.relative_to(root).as_posix()] = document

    findings = {key: [] for key in (
        "missing_files", "missing_fragments", "root_escapes", "invalid_urls",
        "contextual_unverifiable", "duplicate_ids")}
    counts = Counter(dict(html_files=len(documents), knowl_fragments=0,
                          references=0, excluded_urls=0, checked_files=0,
                          checked_fragments=0, skipped_fragments=0))
    for source, document in sorted(documents.items()):
        knowl = source.startswith("knowl/")
        counts["knowl_fragments"] += knowl
        for identifier, count in sorted(document.ids.items()):
            if count > 1:
                findings["duplicate_ids"].append(
                    {"source": source, "id": identifier, "count": count})
        for reference in document.refs:
            counts["references"] += 1
            record = {"source": source, **reference}
            try:
                url = urlsplit(reference["ref"].strip())
                if url.scheme or url.netloc:
                    counts["excluded_urls"] += 1
                    continue
                path = unquote(url.path, errors="strict")
                fragment = unquote(url.fragment, errors="strict")
                if "\x00" in path or "\\" in path:
                    raise ValueError("NUL or ambiguous backslash in URL path")
            except ValueError as error:
                findings["invalid_urls"].append({**record, "reason": str(error)})
                continue

            if (not path and fragment and reference["attribute"] in ("href", "xlink:href")
                    and reference["tag"] != "a"):
                counts["skipped_fragments"] += 1
                continue
            # Loaded knowls inherit the root-level host page's URL, not knowl/.
            if knowl and not path:
                findings["contextual_unverifiable"].append(
                    {**record, "target": None, "fragment": fragment,
                     "reason": "Host page needed for pathless knowl reference"})
                continue
            base = root if knowl or path.startswith("/") else (root / source).parent
            target = (base / path.lstrip("/")).resolve() if path else root / source
            if not target.is_relative_to(root):
                findings["root_escapes"].append(
                    {**record, "target": os.path.relpath(target, root), "fragment": fragment})
                continue
            if target.is_dir():
                target = target / "index.html"
            relative = target.relative_to(root).as_posix()
            record.update(target=relative, fragment=fragment)
            counts["checked_files"] += 1
            if not target.is_file():
                findings["missing_files"].append(record)
                continue
            if not fragment:
                continue
            if (reference["tag"] != "a" or reference["attribute"] != "href"
                    or relative not in documents):
                counts["skipped_fragments"] += 1
                continue
            anchors = documents[relative]
            counts["checked_fragments"] += 1
            if fragment not in anchors.ids and fragment not in anchors.names:
                # HTML defines an ASCII-case-insensitive top-of-document fallback.
                if fragment.lower() == "top":
                    continue
                findings["missing_fragments"].append(record)

    counts.update({key: len(value) for key, value in findings.items()})
    counts["html_pages"] = counts["html_files"] - counts["knowl_fragments"]
    return {
        "schema_version": 1,
        "limitations": [
            "Static UTF-8 .html/.htm only; no browser, JS-generated links/IDs, CSS URLs, srcset, redirects or external requests.",
            "Audits href, src, knowl and xlink:href; all schemes and network-path URLs are excluded.",
            "HTML fragments checked only for a[href] targeting HTML; SVG symbol/resource fragments are not validated.",
            "knowl/ URLs resolve from the root-level containing page; pathless knowl references need runtime host context and are not failures.",
            "Root-relative URLs use the output root; directories use index.html; queries are ignored and paths/fragments percent-decoded once.",
            "No base-element or deployment-prefix handling; ambiguous backslashes are invalid; root escapes are reported separately without reading outside root.",
            "Counts are reference occurrences, not unique targets; duplicate_ids counts per-file repeated IDs, not composed knowl DOMs.",
            "Symlinks and non-regular files are rejected; audit an unchanged output tree. CLI exits successfully even with findings.",
        ],
        "summary": dict(counts),
        **findings,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="generated output directory")
    parser.add_argument("--output", required=True, type=Path, help="JSON destination; parent must exist")
    args = parser.parse_args()
    try:
        root = args.root.resolve(strict=True)
        if args.output.resolve().is_relative_to(root):
            raise ValueError("JSON destination must be outside the audit root")
        result = audit(root)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
                               encoding="utf-8")
        print(json.dumps(result["summary"], sort_keys=True))
    except (OSError, ValueError) as error:
        parser.exit(1, f"Link audit failed: {error}\n")


if __name__ == "__main__":
    main()
