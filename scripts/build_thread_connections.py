#!/usr/bin/env python3
"""Add chapter-specific comparisons to the Centro mobile readers.

This is an additive post-build step. It imports the historical threads already
maintained for the Historic Center walk. The Templo Mayor reader remains
reachable at its existing chapter anchors while its outgoing comparisons are paused.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from html import escape
from pathlib import Path

from build_centro_walk import THREADS, STOPS, chapters, refs_from

ROOT = Path("site")
SLUGS = [stop["slug"] for stop in STOPS]
NAMES = {stop["slug"]: stop["name"] for stop in STOPS}
READERS_WITH_COMPARISONS = [slug for slug in SLUGS if slug != "templo-mayor"]
STYLE = """
<style id="historical-connections-styles">
.historical-connection{position:static;top:auto;display:block;margin:16px 0 24px;
  padding:16px;background:#edf5f4;border:1px solid #bfdbd7;border-radius:12px;
  color:#173c44;font:14px/1.5 system-ui,-apple-system,sans-serif}
.historical-connection .connection-label{cursor:pointer;font-weight:750;letter-spacing:.06em;
  text-transform:uppercase;font-size:12px;color:#126c69;margin:0 0 4px}
.historical-connection p{margin:6px 0 10px}
.historical-connection ul{padding:0;margin:0;list-style:none}
.historical-connection li{margin:7px 0}
.historical-connection a{display:block;color:#075d61;text-decoration:underline;
  text-underline-offset:3px;padding:8px;border-radius:6px;background:#fff}
.historical-connection a:focus-visible{outline:3px solid #0f7f8b;outline-offset:2px}
.historical-connection small{display:block;color:#526874;margin-top:10px}
</style>"""


def archival_chapter(slug: str, heading: str):
    matches = [(index, pt) for index, pt in enumerate(chapters(slug), 1)
               if pt["h"] == heading]
    assert len(matches) == 1, ("missing/ambiguous archive chapter", slug, heading)
    index, pt = matches[0]
    anchor = ("dossier-topic-" if slug == "templo-mayor" else "chapter-") + str(index)
    return anchor, pt


def target_url(slug: str, heading: str) -> str:
    anchor, _ = archival_chapter(slug, heading)
    return f"../../../poi/{slug}/review/#{anchor}"


def insert_after_heading(page: str, anchor: str, heading: str, panel: str):
    heading_html = escape(heading, quote=True)
    # The preserved Centro dossiers include a dated eyebrow between the section
    # opening and heading. Match only this section and the correct archived h2.
    pattern = (r'(<section class="chapter" id="' + re.escape(anchor)
               + r'">(?:(?!</section>).){0,500}?<h2>' +
               re.escape(heading_html) + r'</h2>)')
    page, count = re.subn(pattern, lambda m: m.group(1) + panel,
                          page, count=1, flags=re.DOTALL)
    assert count == 1, ("lost original Centro chapter anchor", anchor, heading)
    return page


def build():
    work = defaultdict(list)
    manifest = []
    for thread in THREADS:
        assert len(thread["entries"]) >= 3, thread["id"]
        for slug, heading in thread["entries"]:
            if slug not in READERS_WITH_COMPARISONS:
                continue
            anchor, chapter = archival_chapter(slug, heading)
            original_refs = refs_from(chapter)
            assert original_refs, ("historical chapter has no archived source ID", slug, heading)
            others = []
            for other_slug, other_heading in thread["entries"]:
                if other_slug == slug and other_heading == heading:
                    continue
                _, other_chapter = archival_chapter(other_slug, other_heading)
                other_refs = refs_from(other_chapter)
                assert other_refs, (other_slug, other_heading, "missing source IDs")
                others.append({
                    "slug": other_slug, "place": NAMES[other_slug],
                    "chapter": other_heading,
                    "url": target_url(other_slug, other_heading),
                    "original_source_ids": other_refs,
                })
            assert len(others) >= 2, thread["id"]
            links = "".join(
                f'<li><a href="{escape(other["url"], quote=True)}">'
                f'<strong>{escape(other["place"])}</strong> · '
                f'{escape(other["chapter"])}</a></li>'
                for other in others
            )
            panel = (
                f'<details class="historical-connection" '
                f'data-historical-thread="{escape(thread["id"], quote=True)}">'
                '<summary class="connection-label">Compare this history nearby</summary>'
                f'<p><strong>{escape(thread["title"])}</strong> — '
                f'{escape(thread["question"])}</p>'
                f'<ul>{links}</ul>'
                '<small>These links connect archived historical chapters. '
                'Source IDs are retained; page-level independent verification '
                'is still pending.</small></details>'
            )
            work[slug].append((anchor, heading, panel))
            manifest.append({
                "thread_id": thread["id"],
                "thread_title": thread["title"],
                "slug": slug, "chapter": heading,
                "anchor": anchor, "original_source_ids": original_refs,
                "related_readings": others,
            })

    outputs = {}
    for slug in READERS_WITH_COMPARISONS:
        path = ROOT / "poi" / slug / "review" / "index.html"
        page = path.read_text(encoding="utf-8")
        assert "Discover" in page and "Explore" in page and "Plan" in page
        assert 'src="../../../feedback/annotate.js"' in page
        assert "historical-connections-styles" not in page, "Builder called twice without a clean rebuild"
        assert "</head>" in page
        for anchor, heading, panel in work[slug]:
            page = insert_after_heading(page, anchor, heading, panel)
        page = page.replace("</head>", STYLE + "</head>", 1)
        assert page.count('class="historical-connection"') == len(work[slug]), slug
        outputs[path] = page

    for path, page in outputs.items():
        path.write_text(page, encoding="utf-8")
    outfile = ROOT / "data" / "historic-center-connections.json"
    outfile.write_text(json.dumps({
        "version": "historic-center-chapter-comparisons-1",
        "source": "Original archived Centro historic chapters and existing walk THREADS",
        "research_status": "archived_source_ids_pending_page_specific_review",
        "count": len(manifest),
        "comparisons": manifest,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"PASS: {len(manifest)} context-specific cross-site chapter comparisons "
          f"across {len(READERS_WITH_COMPARISONS)} readers")


if __name__ == "__main__":
    build()
