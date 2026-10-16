"""Extract evidence, never execute scripts from uploaded guides. Standard library only."""

import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile


class GuideParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.capture = None
        self.parts = []
        self.sections = []
        self.section_id = ""
        self.section_title = ""
        self.title = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "").split()
        if tag == "meta" and attrs.get("property") == "og:title":
            self.title = attrs.get("content", "").replace("Сообщество Steam :: Руководство :: ", "")
        if tag == "div":
            self.depth += 1
            if "subSection" in classes:
                self.section_id = attrs.get("id", "")
            if "subSectionTitle" in classes or "subSectionDesc" in classes:
                self.capture = (self.depth, "title" if "subSectionTitle" in classes else "body")
                self.parts = []
        if self.capture and tag in ("br", "div", "p", "li", "tr"):
            self.parts.append("\n")

    def handle_data(self, data):
        if self.capture:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "div":
            if self.capture and self.depth == self.capture[0]:
                text = "\n".join(line.strip() for line in "".join(self.parts).splitlines() if line.strip())
                if self.capture[1] == "title":
                    self.section_title = text
                else:
                    self.sections.append({"id": self.section_id, "title": self.section_title, "text": text})
                self.capture = None
            self.depth -= 1
        if self.capture and tag in ("div", "p", "li", "tr"):
            self.parts.append("\n")


def ods_childhood(path):
    ns = {"t": "urn:oasis:names:tc:opendocument:xmlns:table:1.0", "x": "urn:oasis:names:tc:opendocument:xmlns:text:1.0"}
    root = ET.fromstring(zipfile.ZipFile(path).read("content.xml"))
    rows = []
    # Rows are nested in collapsible groups. Direct-child traversal loses most data.
    for index, row in enumerate(root.findall(".//t:table-row", ns)):
        cells = []
        for cell in row:
            if cell.tag.rsplit("}", 1)[-1] not in ("table-cell", "covered-table-cell"):
                continue
            text = " ".join("".join(p.itertext()) for p in cell.findall(".//x:p", ns))
            repeat = int(cell.get("{" + ns["t"] + "}number-columns-repeated", "1"))
            cells.extend([text] * min(repeat, 64))
        while cells and not cells[-1]:
            cells.pop()
        if cells and cells[0] == "Adolescence":
            break
        if cells:
            rows.append({"row": index + 1, "cells": cells})
    return rows


def extract(input_dir, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for path in sorted(input_dir.rglob("*.html")):
        raw = path.read_bytes()
        html = raw.decode("utf-8")
        parser = GuideParser()
        parser.feed(html)
        match = re.search(r"var publishedfileid\s*=\s*['\"](\d+)", html)
        if not match:
            raise ValueError(f"Steam guide ID not found: {path.name}")
        guide_id = match[1]
        sections = []
        for section in parser.sections:
            title = section["title"].lower()
            if "детство" in title or "childhood" in title:
                sections.append(section)
            elif title == "walkthrough" and "Chapter 1" in section["text"]:
                section["text"] = section["text"].split("Chapter 2", 1)[0].strip()
                sections.append(section)
        entry = {"id": guide_id, "title": parser.title, "file": path.name,
                 "url": f"https://steamcommunity.com/sharedfiles/filedetails/?id={guide_id}",
                 "sha256": hashlib.sha256(raw).hexdigest(), "childhood_sections": len(sections)}
        manifest.append(entry)
        if sections:
            (output_dir / f"steam-{guide_id}.json").write_text(
                json.dumps({**entry, "sections": sections}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for path in sorted(input_dir.rglob("*.ods")):
        rows = ods_childhood(path)
        manifest.append({"id": "ods", "file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        (output_dir / "ods-childhood.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    args = argparse.ArgumentParser()
    args.add_argument("input", type=Path)
    args.add_argument("output", type=Path)
    options = args.parse_args()
    extract(options.input, options.output)
