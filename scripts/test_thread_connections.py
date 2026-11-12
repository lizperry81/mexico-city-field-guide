#!/usr/bin/env python3
"""Regression tests for contextual historical connections in generated readers."""
import json
import posixpath
from collections import Counter
from html import escape
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from build_centro_walk import THREADS, STOPS, chapters, refs_from

root=Path("site")
manifest=json.loads((root/"data/historic-center-connections.json").read_text(encoding="utf-8"))
assert manifest["research_status"]=="archived_source_ids_pending_page_specific_review"
rows=manifest["comparisons"]
assert len(rows)==manifest["count"]==sum(len(t["entries"]) for t in THREADS)==12
assert {r["thread_id"] for r in rows}=={t["id"] for t in THREADS}
assert {r["slug"] for r in rows}=={s["slug"] for s in STOPS}
page_map={s["slug"]:(root/"poi"/s["slug"]/"review/index.html").read_text(encoding="utf-8")
          for s in STOPS}
per_page=Counter(r["slug"] for r in rows)
for slug,page in page_map.items():
    assert page.count('class="historical-connection"')==per_page[slug],slug
    assert page.count('id="historical-connections-styles"')==1,slug
    assert 'src="../../../feedback/annotate.js"' in page,slug
    assert "Discover" in page and "Explore" in page and "Plan" in page,slug
    assert "page-level independent verification" in page
    assert "location.hash" in page, "Review reader must support incoming chapter deep links"
    assert "history.replaceState" in page, "Reader must remember current chapter when following cross-site links"
for row in rows:
    slug=row["slug"]
    source_page=page_map[slug]
    assert f'data-historical-thread="{escape(row["thread_id"], quote=True)}"' in source_page
    assert f'id="{row["anchor"]}"' in source_page,(slug,row["anchor"])
    matches=[x for x in chapters(slug) if x["h"]==row["chapter"]]
    assert len(matches)==1,(slug,row["chapter"])
    assert row["original_source_ids"]==refs_from(matches[0])
    assert len(row["related_readings"])==2,(slug,row["thread_id"])
    for related in row["related_readings"]:
        href=related["url"]
        assert f'href="{escape(href,quote=True)}"' in source_page,(slug,href)
        assert href.startswith("../../../poi/"),(slug,href)
        path,anchor=href.split("#")
        assert anchor
        resolved=posixpath.normpath(posixpath.join("/poi",slug,"review",path))
        assert resolved==f"/poi/{related['slug']}/review",resolved
        assert f'id="{anchor}"' in page_map[related["slug"]],(href,"broken chapter target")
        matches=[p for p in chapters(related["slug"]) if p["h"]==related["chapter"]]
        assert len(matches)==1,(related["slug"],related["chapter"])
        assert related["original_source_ids"]==refs_from(matches[0])
assert (root/"index.html").stat().st_size>500_000, "Original rich homepage was replaced"
print("PASS: 12 evidence-ID-backed comparisons; 24 deep links resolve to existing preserved chapters in all four mobile readers; full homepage retained")
