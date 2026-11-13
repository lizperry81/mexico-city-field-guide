#!/usr/bin/env python3
"""Gate long-form Discover publication behind explicit human review and evidence checks.

Never rewrites the original POIs, field stops, or browser feedback. Draft chapters
are not deployed. A separate page is generated only for an approved manuscript.
"""
from __future__ import annotations

import hashlib
import json
import re
from html import escape
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EDITORIAL = REPO / "editorial/discover"
SITE = Path("site")
SAFE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
STATUSES = {"draft", "in_review", "approved"}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def validate(record, slug):
    require(isinstance(record, dict), "Manuscript must be an object")
    require(record.get("schema_version") == 1, "Unsupported manuscript schema")
    require(record.get("poi_slug") == slug and SAFE_ID.fullmatch(slug),
            "Manuscript slug mismatch")
    status = record.get("status")
    require(status in STATUSES, "Invalid editorial status")
    chapters = record.get("chapters")
    require(isinstance(chapters, list), "Chapters must be an array")
    if status != "approved":
        # Draft prose may exist, but may NEVER leak into the published site.
        return False
    approval = record.get("approval")
    require(isinstance(approval, dict), "Approved manuscript needs approval")
    for name in ("editor", "evidence_auditor", "approved_on"):
        require(isinstance(approval.get(name), str) and approval[name].strip(),
                "Missing human review field: " + name)
    require(approval.get("editorial_review_complete") is True,
            "Editorial review is not complete")
    require(approval.get("page_specific_evidence_checked") is True,
            "Source-page audit is not complete")
    require(len(chapters) >= 1, "Approved manuscript needs chapters")
    seen = set()
    for chapter in chapters:
        require(isinstance(chapter, dict), "Chapter must be an object")
        cid = chapter.get("id")
        require(isinstance(cid, str) and SAFE_ID.fullmatch(cid) and cid not in seen,
                "Invalid or duplicate chapter ID")
        seen.add(cid)
        require(isinstance(chapter.get("title"), str) and chapter["title"].strip(),
                "Chapter title required")
        paragraphs = chapter.get("paragraphs")
        require(isinstance(paragraphs, list) and len(paragraphs) >= 1,
                "Approved chapter needs narrative paragraphs")
        for paragraph in paragraphs:
            require(isinstance(paragraph, dict) and
                    isinstance(paragraph.get("text"), str) and
                    len(paragraph["text"].strip()) >= 40,
                    "Approved paragraph needs substantive text")
            evidence = paragraph.get("evidence")
            require(isinstance(evidence, list) and evidence,
                    "Each published paragraph needs traceable evidence")
            for ref in evidence:
                require(isinstance(ref, dict), "Evidence must be an object")
                for field in ("source_id", "page_or_section"):
                    require(isinstance(ref.get(field), str) and ref[field].strip(),
                            "Evidence missing " + field)
                require(ref.get("audit_status") == "page_checked",
                        "Source-page verification pending")
        for deep_dive in chapter.get("deep_dives", []):
            require(isinstance(deep_dive, dict), "Invalid deep dive")
            require(isinstance(deep_dive.get("title"), str) and
                    isinstance(deep_dive.get("text"), str) and
                    deep_dive["title"].strip() and deep_dive["text"].strip(),
                    "Incomplete optional deep dive")
    return True


def render(record):
    """Only call after validate() returns True; escape all editorial content."""
    slug = record["poi_slug"]
    chunks = []
    toc = []
    for i, chapter in enumerate(record["chapters"], 1):
        cid = chapter["id"]
        toc.append(f'<a href="#{cid}">{i}. {escape(chapter["title"])}</a>')
        parts = [f'<article id="{cid}" class="chapter"><p class="count">CHAPTER {i}</p>',
                 f'<h2>{escape(chapter["title"])}</h2>']
        for paragraph in chapter["paragraphs"]:
            parts.append("<p>" + escape(paragraph["text"]) + "</p>")
            refs = "; ".join(escape(ref["source_id"]) + " · " +
                             escape(ref["page_or_section"])
                             for ref in paragraph["evidence"])
            parts.append('<p class="references">Verified source locators: ' + refs + "</p>")
        for dive in chapter.get("deep_dives", []):
            parts.append("<details><summary>" + escape(dive["title"]) +
                         "</summary><p>" + escape(dive["text"]) + "</p></details>")
        # Adjacent chapter links use only the approved manuscript sequence.
        # A Discover page never points to or rewrites the Explore field chapters.
        pager = []
        if i > 1:
            previous = record["chapters"][i - 2]
            pager.append('<a rel="prev" href="#' + previous["id"] +
                         '">← Previous chapter: ' + escape(previous["title"]) + '</a>')
        if i < len(record["chapters"]):
            following = record["chapters"][i]
            pager.append('<a rel="next" href="#' + following["id"] +
                         '">Next chapter: ' + escape(following["title"]) + ' →</a>')
        if pager:
            parts.append('<nav class="chapter-pager" aria-label="Continue reading">' +
                         "".join(pager) + '</nav>')
        parts.append("</article>")
        chunks.append("".join(parts))
    title = "Templo Mayor" if slug == "templo-mayor" else slug.replace("-", " ").title()
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} · Approved Discover narrative</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#f6f8fa;color:#16303b;font:18px/1.7 Georgia,serif}}
header,main{{max-width:850px;margin:auto;padding:18px 22px}}
header{{font:15px system-ui}}a{{color:#126c69}}
h1{{font:700 clamp(34px,6vw,58px)/1.12 Georgia,serif}}h2{{font:700 32px/1.2 Georgia,serif}}
nav{{display:grid;gap:10px;padding:18px;background:#e9f2f1;border-radius:12px;font:16px system-ui}}
.chapter-pager{{display:flex;flex-wrap:wrap;justify-content:space-between;gap:18px;margin-top:26px;border-top:1px solid #d5e1e3;padding:16px 0 0}}
.chapter-pager a{{display:inline-flex;min-height:44px;align-items:center}}
.skip-link{{position:absolute;left:-9999px;top:8px;padding:12px;background:white;z-index:2}}
.skip-link:focus{{left:8px}}
.chapter{{background:white;padding:22px;margin:26px 0;border:1px solid #d5e1e3;border-radius:14px;scroll-margin-top:20px}}
.references{{font:13px/1.5 system-ui;color:#445d66}}
.count{{font:700 13px system-ui;letter-spacing:.08em;color:#126c69}}
details{{border-top:1px solid #d5e1e3;padding:14px 0}}summary{{cursor:pointer;font:700 16px system-ui}}
a:focus-visible,summary:focus-visible{{outline:3px solid #126c69;outline-offset:3px}}
</style></head><body>
<a class="skip-link" href="#chapter-navigation">Skip to chapters</a>
<header><a href="../review/">← Back to the complete research dossier and field guide</a></header>
<main><p class="count">EDITORIALLY APPROVED · DISCOVER</p><h1>{escape(title)}</h1>
<p>This narrative has passed the recorded editorial and page-specific evidence review. For field stops, museum information, and visit planning, use Explore and Plan in the original reader.</p>
<nav id="chapter-navigation" aria-label="Chapters">{''.join(toc)}</nav>
{''.join(chunks)}
</main></body></html>"""



def verify_verbatim_archives(record, root=REPO):
    """Require a checksum-pinned verbatim archive for every published chapter.

    This is an additional fail-closed publication gate. Human approval and
    page-specific evidence review remain mandatory; an archive alone is not
    an approval. The source Markdown stays private in editorial/approved/.
    """
    slug = record["poi_slug"]
    for chapter in record["chapters"]:
        # Derive the path from validated IDs; no path comes from JSON input.
        archive = root / "editorial" / "approved" / f"{slug}--{chapter['id']}.md"
        checksum = archive.with_suffix(".md.sha256")
        require(archive.is_file() and checksum.is_file(),
                f"Missing exact approved chapter archive or checksum: {archive.name}")
        raw = archive.read_bytes()
        require(not archive.is_symlink() and not checksum.is_symlink(),
                "Archived Discover files must be ordinary committed files")
        expected = checksum.read_text(encoding="utf-8").strip().split()
        require(len(expected) >= 1 and re.fullmatch(r"[0-9a-fA-F]{64}", expected[0]),
                f"Invalid SHA-256 record: {checksum.name}")
        require(hashlib.sha256(raw).hexdigest() == expected[0].lower(),
                f"Archived Discover chapter checksum mismatch: {archive.name}")
        archived_text = raw.decode("utf-8")
        offset = 0
        # Preserve every published paragraph verbatim and in the same order
        # as the immutable chapter. Any proposed edit needs a new approval.
        for number, paragraph in enumerate(chapter["paragraphs"], 1):
            found = archived_text.find(paragraph["text"], offset)
            require(found >= 0,
                    f"Discover chapter {chapter['id']} paragraph {number} "
                    "is not verbatim in the approved archive")
            offset = found + len(paragraph["text"])


def build():
    statuses = []
    for manuscript in sorted(EDITORIAL.glob("*.json")):
        slug = manuscript.stem
        data = json.loads(manuscript.read_text(encoding="utf-8"))
        approved = validate(data, slug)
        statuses.append({"poi_slug": slug, "status": data["status"],
                         "published": approved,
                         "chapter_count_published": len(data["chapters"]) if approved else 0})
        if approved:
            verify_verbatim_archives(data)
            destination = SITE / "poi" / slug / "discover/index.html"
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(render(data), encoding="utf-8")
            print("PUBLISHED reviewed Discover manuscript:", slug, len(data["chapters"]))
        else:
            print("NOT published — manuscript awaiting editorial approval:", slug)
    output = SITE / "data/discover-editorial-status.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"version": 1, "manuscripts": statuses}, indent=2),
                      encoding="utf-8")


if __name__ == "__main__":
    build()
