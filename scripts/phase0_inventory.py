#!/usr/bin/env python3
"""Inventory the active legacy book source without running its publisher."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET


XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
XML_BASE = "{http://www.w3.org/XML/1998/namespace}base"
XI_INCLUDE = "{http://www.w3.org/2001/XInclude}include"


def load_active_source(root):
    """Expand src/ila.xml's XInclude graph, recording file hashes and element origins."""
    root = Path(root).resolve()
    files = {}
    origins = {}
    includes = []

    def load(path, stack=()):
        path = path.resolve()
        name = path.relative_to(root).as_posix()
        if path in stack:
            raise ValueError(f"Cyclic XInclude: {name}")
        data = path.read_bytes()
        tree = ET.fromstring(data)  # The default parser discards comments.
        files[name] = {"file": name, "sha256": hashlib.sha256(data).hexdigest()}
        for index, element in enumerate(tree.iter(), 1):
            origins[element] = {"file": name, "source_element": index}
            if XML_BASE in element.attrib:
                raise ValueError(f"Unsupported xml:base in {name}")

        def expand(element):
            if element.tag == XI_INCLUDE:
                href = element.get("href", "")
                uri = urlsplit(href)
                if uri.scheme or uri.netloc or Path(unquote(uri.path)).is_absolute():
                    raise ValueError(f"Non-relative/network XInclude refused in {name}: {href}")
                if (not uri.path or uri.query or uri.fragment
                        or "xpointer" in element.attrib
                        or element.get("parse", "xml") != "xml" or len(element)):
                    raise ValueError(f"Unsupported XInclude in {name}: {href}")
                target = (path.parent / unquote(uri.path)).resolve()
                target_name = target.relative_to(root).as_posix()
                includes.append({"file": name, "href": href, "target": target_name})
                replacement = load(target, stack + (path,))
                replacement.tail = element.tail
                return replacement
            for index, child in enumerate(element):
                element[index] = expand(child)
            return element

        return expand(tree)

    return load(root / "src/ila.xml"), files, origins, includes


def inventory(root):
    root = Path(root).resolve()
    book, files, origins, includes = load_active_source(root)
    counts = Counter()
    ids = defaultdict(list)
    xrefs = []
    mathboxes = []
    divisions = []

    def text(element):
        return " ".join("".join(element.itertext()).split()) if element is not None else None

    def walk(element, ancestors=()):
        location = {**origins[element], "element": element.tag}
        counts[element.tag] += 1
        if XML_ID in element.attrib:
            ids[element.attrib[XML_ID]].append(location)
        context = next((a.get(XML_ID) for a in reversed(ancestors + (element,))
                        if XML_ID in a.attrib), None)
        if element.tag == "xref":
            targets = []
            for attribute in ("ref", "first", "last"):
                if attribute in element.attrib:
                    for target in re.split(r"[\s,]+", element.attrib[attribute].strip()):
                        if target:
                            targets.append({"attribute": attribute, "id": target})
            xrefs.append({**location, "context_id": context,
                          "attributes": dict(element.attrib), "targets": targets})
        if element.tag == "mathbox":
            caption = next((a.find("caption") for a in reversed(ancestors + (element,))
                            if a.find("caption") is not None), None)
            mathboxes.append({**location, "context_id": context, "caption": text(caption),
                              "attributes": dict(element.attrib)})
        if element.tag in ("chapter", "section", "subsection", "subsubsection", "appendix"):
            parent = next((a for a in reversed(ancestors)
                           if a.tag in ("chapter", "section", "subsection", "subsubsection", "appendix")), None)
            divisions.append({**location, "id": element.get(XML_ID),
                              "title": text(element.find("title")),
                              "parent_id": parent.get(XML_ID) if parent is not None else None})
        for child in element:
            walk(child, ancestors + (element,))

    walk(book)
    unresolved = []
    for xref in xrefs:
        for target in xref["targets"]:
            target["status"] = ("unresolved" if target["id"] not in ids else
                                "ambiguous" if len(ids[target["id"]]) > 1 else "resolved")
            if target["status"] == "unresolved":
                unresolved.append({"file": xref["file"], "source_element": xref["source_element"],
                                   "context_id": xref["context_id"], **target})
    duplicates = {key: locations for key, locations in ids.items() if len(locations) > 1}
    inactive = sorted(path.relative_to(root).as_posix() for path in (root / "src").glob("*.xml")
                      if path.relative_to(root).as_posix() not in files)
    revision = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                              check=True, capture_output=True, text=True).stdout.strip()
    return {
        "schema_version": 1,
        "git_revision": revision,
        "entrypoint": "src/ila.xml",
        "limitations": [
            "Source inventory only: no generated page URLs, anchors, numbering, or rendering claims.",
            "Active means reachable by XML XInclude, not conditional publisher output; comments are ignored.",
            "Only relative local whole-document XML includes are supported; network, root escapes, "
            "xml:base, XPointer, text includes and fallback are rejected.",
            "Counts and ID occurrences describe the expanded tree; source XML files are unique and sorted.",
            "source_element is a one-based preorder index in the original parsed file, not a line number.",
            "Xref ref/first/last are split on commas and whitespace and checked against active xml:ids only; "
            "range interiors are not expanded. Provisional and other attributes are preserved, not resolved.",
            "Titles/captions are whitespace-normalized XML text, not rendered mathematics or cross-references.",
            "Mathbox attributes are XML-decoded source configuration; demo assets/runtime are not validated.",
            "Inactive XML lists only src/*.xml outside the include graph; their contents are not inventoried.",
            "Git revision identifies HEAD, not worktree cleanliness; active source SHA-256 hashes record actual bytes.",
        ],
        "summary": {
            "source_xml_files": len(files), "active_includes": len(includes),
            "elements": sum(counts.values()), "xml_id_occurrences": sum(map(len, ids.values())),
            "unique_xml_ids": len(ids), "duplicate_xml_ids": len(duplicates),
            "xrefs": len(xrefs), "xref_targets": sum(len(x["targets"]) for x in xrefs),
            "unresolved_xref_targets": len(unresolved),
            "xrefs_without_checked_targets": sum(not x["targets"] for x in xrefs),
            "mathboxes": len(mathboxes), "chapters": counts["chapter"],
            "sections": counts["section"], "inactive_top_level_xml": len(inactive),
        },
        "source_xml": [files[name] for name in sorted(files)],
        "includes": includes,
        "element_counts": dict(counts),
        "xml_ids": dict(ids),
        "duplicate_xml_ids": duplicates,
        "xrefs": xrefs,
        "unresolved_xref_targets": unresolved,
        "mathboxes": mathboxes,
        "ordered_divisions": divisions,
        "inactive_top_level_xml": inactive,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True,
                        help="source Git checkout containing src/ila.xml")
    parser.add_argument("--output", type=Path,
                        help="write generated JSON here instead of stdout; parent must exist")
    args = parser.parse_args()
    try:
        result = json.dumps(inventory(args.root), indent=2, sort_keys=True, ensure_ascii=True) + "\n"
        if args.output:
            args.output.write_text(result, encoding="utf-8")
        else:
            sys.stdout.write(result)
    except (OSError, ValueError, ET.ParseError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Inventory failed: {error}\n")


if __name__ == "__main__":
    main()
