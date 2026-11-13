#!/usr/bin/env python3
"""Inventory EXISTING Templo Mayor history prose for human evidence review.

This module is deliberately read-only: it never changes historical prose or
publishes staged research. The output belongs only in private CI artifacts.
"""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path

READER = Path("poi/templo-mayor/reader.html")
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}


class HistoryPassages(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.pending = None
        self.parts = []
        self.counts = defaultdict(int)
        self.passages = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "p" and self.pending is None:
            in_history = any(t == "article" and a.get("id") == "history"
                             for t, a in self.stack)
            in_details = any(t == "details" for t, _ in self.stack)
            classes = attrs.get("class", "").split()
            if in_history and not in_details and "cdmx-no-comment" not in classes:
                section = next(
                    (a["id"] for t, a in reversed(self.stack)
                     if t == "section" and a.get("id", "").startswith("dossier-topic-")),
                    "history-introduction",
                )
                self.pending = section
                self.parts = []
        if tag not in VOID_TAGS:
            self.stack.append((tag, attrs))

    def handle_data(self, data):
        if self.pending is not None:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "p" and self.pending is not None:
            statement = re.sub(r"\s+", " ", "".join(self.parts)).strip()
            if statement:
                self.counts[self.pending] += 1
                self.passages.append({
                    "passage_id": f"{self.pending}:p{self.counts[self.pending]:02d}",
                    "section_id": self.pending,
                    "text_sha256": hashlib.sha256(statement.encode("utf-8")).hexdigest(),
                    "character_count": len(statement),
                    "excerpt_for_reviewer": statement[:180],
                    "human_review_status": "not_reviewed",
                    "source_id_confirmed": None,
                    "page_or_section_checked": None,
                    "audit_claim_ids_assigned": [],
                    "publication_authorization": False,
                })
            self.pending = None
            self.parts = []
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break


def inventory(path=READER):
    raw = path.read_bytes()
    parser = HistoryPassages()
    parser.feed(raw.decode("utf-8"))
    sections = {p["section_id"] for p in parser.passages}
    if len(parser.passages) < 10 or not {
        f"dossier-topic-{i}" for i in range(1, 7)
    }.issubset(sections):
        raise ValueError("The historical reader is missing expected prose sections")
    return {
        "schema_version": 1,
        "source_path": str(path),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "status": "private_passage_inventory_human_evidence_review_required",
        "publication_authorization": False,
        "passage_count": len(parser.passages),
        "section_ids": sorted(sections),
        "passages": parser.passages,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(inventory(), ensure_ascii=False, indent=2))
