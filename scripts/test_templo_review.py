#!/usr/bin/env python3
"""Check the reader's layout, anchors, and preservation of the research dossier."""
import json
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
