#!/usr/bin/env python3
"""Check the reader's layout, anchors, and preservation of the research dossier."""
import json
import re
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from subprocess import run
from urllib.parse import urlsplit

ROOT = Path("site")
POI = ROOT / "poi/templo-mayor"


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.ids = set()
        self.urls = []
        self.images = []
        self.photo_zoom_links = []
        self.feed(path.read_text(encoding="utf-8"))

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if identifier := attributes.get("id"):
            assert identifier not in self.ids, f"Duplicate id: {identifier}"
            self.ids.add(identifier)
        if tag == "img":
            self.images.append(attributes.get("src"))
        if tag == "a" and attributes.get("class") == "photo-zoom":
            assert attributes.get("target") == "_blank"
            assert "noopener" in attributes.get("rel", "").split()
            self.photo_zoom_links.append(attributes["href"])
        for key in ("href", "src"):
            if url := attributes.get(key):
                self.urls.append(url)


for folder, feedback_path in (
    (POI, "../../feedback/annotate.js"),
    (POI / "review", "../../../feedback/annotate.js"),
):
    path = folder / "index.html"
    page = Page(path)
    text = path.read_text(encoding="utf-8")
    assert feedback_path in page.urls
    assert "@POI@" not in text and "@GUIDE@" not in text
    assert {"history", "explore", "plan", "plaza", "twin-stairs", "museum-stone"} <= page.ids
    assert all(f"dossier-topic-{n}" in page.ids for n in range(1, 7))
    assert all(f"walk-{n}" in page.ids for n in range(1, 9))
    for marker in (
        "Read before visiting", "Follow on site", "How can archaeologists date a wall?",
        "Offering 125", "Plaza Manuel Gamio", "Coyolxauhqui replica",
        "The original Coyolxauhqui stone", "photo-marker", "See a photograph of the 1978 excavation",
    ):
        assert marker in text, marker
    for marker in (
        "Eight recovered field chapters", "Field experience", "deep_dive_question",
        "How does the map distinguish", "historic-walk-crosslink", "data-historical-thread",
    ):
        assert marker not in text, marker
    # Discover's section index must link only to actual historical sections
    # in the current pre-visit article, in their existing narrative order.
    # It must never relabel Explore stops as Discover history chapters.
    history_html = text.split('<article id="history"', 1)[1].split('</article>', 1)[0]
    contents = re.search(r'<nav class="history-chapters[^"]*"[^>]*>(.*?)</nav>', history_html, re.DOTALL)
    assert contents, "Missing accessible Discover article contents"
    contents_html = contents.group(1)
    toc = re.findall(r'<a href="#([^"]+)">([^<]+)</a>', contents_html)
    assert [anchor for anchor, _ in toc] == [
        "dossier-topic-1", "dossier-topic-2", "dossier-topic-3",
        "dossier-topic-5", "dossier-topic-4", "dossier-topic-6",
    ], "Discover index must mirror the existing article, without claiming new approved chapters"
    for anchor, title in toc:
        section = re.search(
            r'<section id="' + re.escape(anchor) +
            r'" class="history-section">\s*<h3>([^<]+)</h3>', history_html
        )
        assert section and title == section.group(1), (anchor, title)
    assert history_html.index('history-chapters') < history_html.index('id="dossier-topic-1"')
    assert 'history-chapters' not in text.split('<section id="explore"', 1)[1]
    # Every physical stop must remain actionable on location, with a
    # standing position, a visible feature, and its existing photo reference.
    # Keep these field instructions separate from pre-visit Discover history.
    field_stops = re.findall(
        r'<section id="([^"]+)" class="walk-stop" data-stop>(.*?)</section>',
        text, flags=re.DOTALL,
    )
    assert len(field_stops) == 5, "A preserved Explore field stop disappeared"
    for stop_id, stop_html in field_stops:
        assert '<strong>Stand at</strong>' in stop_html, stop_id
        assert '<strong>Look for</strong>' in stop_html, stop_id
        assert 'class="field-photo"' in stop_html, stop_id
        assert 'alt="' in stop_html, stop_id
    # The two source plans were already in Explore. Plan now surfaces their
    # existing INAH URLs as explicit, accessible PDFs for mobile preparation.
    assert 'class="orientation-links"' in text
    assert 'Archaeological zone plan (INAH PDF, opens in a new tab)' in text
    assert 'Site museum floor plan (INAH PDF, opens in a new tab)' in text
    # Maps must be accessible from the physical walk at the moment of use,
    # while remaining separately available in Plan. Do not guess stop pins.
    assert text.count('templo_mayor_cdmx.pdf') == 3
    assert text.count('75_museo_sitio_templo_mayor.pdf') == 3
    assert text.index('id="explore"') < text.index('class="walk-map-note') < text.index('id="plaza"')
    museum_stop = next(html for stop_id, html in field_stops if stop_id == "museum-stone")
    assert 'INAH museum floor plan (PDF, opens in a new tab)' in museum_stop
    assert text.count('class="walk-map-note cdmx-no-comment"') == 2
    for label in ('INAH archaeological-zone plan (PDF, opens in a new tab)',
                  'INAH museum floor plan (PDF, opens in a new tab)'):
        assert label in text
        assert 'target="_blank" rel="noopener">' + label in text
    for url in page.urls:
        parts = urlsplit(url)
        if parts.scheme or parts.netloc:
            continue
        target = folder / parts.path
        if target.is_dir():
            target /= "index.html"
        assert target.is_file(), (folder, url)
        if parts.fragment:
            target_ids = page.ids if target == path else Page(target).ids
            assert parts.fragment in target_ids, (target, url)
    # Keep Discover history and Explore's on-site photo references separate.
    assert '<a href="#history">Discover <small>History · Read before visiting</small></a>' in text
    assert '<a href="#explore">Explore <small>Guided walk · Follow on site</small></a>' in text
    assert '<a href="#plan">Plan <small>Access and directions</small></a>' in text
    assert len(page.images) == 7, "One overview plus six preserved field photos"
    assert len(page.photo_zoom_links) == 6, "Every field photo must be enlargeable"
    assert sorted(page.photo_zoom_links) == sorted(
        image for image in page.images
        if not image.endswith("ruins-and-cathedral.webp")
    ), "Never link field stops to unrelated, invented, or nonlocal imagery"

archive = (POI / "archive/index.html").read_text(encoding="utf-8")
research = ROOT / "data/research"
for filename, key, field in (
    ("templo_walk_v63.json", "chapters", "core_text"),
    ("templo_mayor_pilot.json", "claims", "statement"),
    ("templo_verified_discoveries_v68.json", None, "title"),
):
    data = json.loads((research / filename).read_text(encoding="utf-8"))
    records = data[key] if key else data
    for record in records:
        assert escape(record[field], quote=True) in archive, record[field]

for js in (POI / "assets/reader.js", ROOT / "feedback/annotate.js"):
    run(["node", "--check", str(js)], check=True)
print("PASS: both Templo Mayor routes, local assets and anchors, and original research in the archive")
