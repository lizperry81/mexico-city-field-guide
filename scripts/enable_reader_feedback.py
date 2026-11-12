#!/usr/bin/env python3
"""Enable non-destructive paragraph annotation on all Historic Center pages.

Generated pages retain their original source files and historical content.
Run after all POI and walk builders; safe to run twice.
"""
from pathlib import Path

SITE = Path("site")
PAGES = [
    SITE / "poi/templo-mayor/index.html",
    SITE / "poi/zocalo/index.html",
    SITE / "poi/metropolitan-cathedral/index.html",
    SITE / "poi/national-palace/index.html",
    SITE / "walks/historic-center/index.html",
]
SCRIPT = '<script src="../../feedback/annotate.js" defer></script>'

def main():
    asset = SITE / "feedback/annotate.js"
    assert asset.is_file() and asset.stat().st_size > 6000, "Feedback script missing or truncated"
    for path in PAGES:
        assert path.is_file(), f"Missing historical guide: {path}"
        page = path.read_text(encoding="utf-8")
        assert len(page) > 9000 and "</body>" in page, f"Truncated page: {path}"
        if SCRIPT not in page:
            page = page.replace("</body>", SCRIPT + "</body>", 1)
            path.write_text(page, encoding="utf-8")
        assert page.count(SCRIPT) == 1, f"Duplicate annotation script: {path}"
        print("Comment-enabled:", path, "chars:", len(page))

if __name__ == "__main__":
    main()
