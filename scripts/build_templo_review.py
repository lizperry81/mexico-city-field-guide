#!/usr/bin/env python3
"""Publish the Templo Mayor reader and retain the recovered research dossier."""
from pathlib import Path
import re
from shutil import copytree

ROOT = Path("site")
POI = ROOT / "poi/templo-mayor"
SOURCE = Path("poi/templo-mayor")
FEEDBACK = '<script src="../../feedback/annotate.js" defer></script>'


def build():
    original = (POI / "index.html").read_text(encoding="utf-8")
    for marker in (
        'id="story"', 'id="dossier"', 'id="museum"', 'id="claimlist"',
        'id="walk-8"', 'id="dossier-topic-6"', FEEDBACK,
    ):
        assert marker in original, f"Missing from the Templo Mayor research dossier: {marker}"

    # The existing dossier remains browsable at a route one level deeper.
    archive = re.sub(r'((?:href|src)=")(?=\.\./)', r"\1../", original)
    archive = archive.replace(
        '<div class="tabs"',
        '<p><a href="../">← Templo Mayor history and guided walk</a></p><div class="tabs"',
        1,
    )
    archive_dir = POI / "archive"
    archive_dir.mkdir(exist_ok=True)
    (archive_dir / "index.html").write_text(archive, encoding="utf-8")

    template = (SOURCE / "reader.html").read_text(encoding="utf-8")
    copytree(SOURCE / "assets", POI / "assets", dirs_exist_ok=True)
    for destination, poi_path, guide_path in (
        (POI, "", "../../"),
        (POI / "review", "../", "../../../"),
    ):
        destination.mkdir(exist_ok=True)
        page = template.replace("@POI@", poi_path).replace("@GUIDE@", guide_path)
        (destination / "index.html").write_text(page, encoding="utf-8")
    print("Built the Templo Mayor reader and preserved the research dossier at archive/.")


if __name__ == "__main__":
    build()
