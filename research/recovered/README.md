# Templo Mayor research recovery — provenance and publishing

This folder preserves three original UTF-8 research files from CDMX_Recovery_Integrated_V81_V97.zip, under cdmx-fieldguide-build/data/research/. The previous older redesign ZIP lacked these historical files.

Because the GitHub connector handles text file uploads, templo_v81_original_json.zlib.b64 is a lossless base64/zlib archive of an object containing the original full file texts, including whitespace, citations and verification fields.

| File | Bytes | SHA-256 | Records |
| --- | ---: | --- | ---: |
| templo_walk_v63.json | 8690 | 5f0aa7f8a57511e3277f90aba7c6a6eb4fca12bf0b6ed5981a35fca359c2b63a | 8 chapters |
| templo_mayor_pilot.json | 13521 | 778ac52157b1d76558134937f739f9b97e1cab70c3f128892462b6df4c8c6596 | 21 claims |
| templo_verified_discoveries_v68.json | 9090 | bdd54da92729a087de3016e2aa8255f5e5cb3126f47e87c9e80855bd5cbaf98a | 12 source records |

## Publishing

From the repository root, extract the existing redesign app into site/, then run:

    python scripts/recover_templo.py site
    python scripts/build_poi.py
    python scripts/test_poi.py

The recovery script validates every original SHA-256 and refuses to overwrite an existing different research file. The tests require all 8 chapters, all 21 claims, all 12 source records, the six substantive historical dossier entries from the existing Centro guide, museum material, navigational tabs, and machine-readable POI planning information.

The new generated route /poi/templo-mayor/ is additive, not a replacement of the old /templo-mayor/ page. The main homepage is preserved from recovered/mexico-city-field-guide.html; the workflow adds only an entry link.

## Editorial and release status

Source identifiers and editorial review flags are retained exactly. No unreviewed research is automatically promoted to verified. Older hour/price information in Centro data is not presented as live fact. The post-deployment step checks HTTP status and substantive on-page content, but a committed workflow does not itself prove the Pages URL is live.

Remaining: reconcile remaining V81 research registers and bibliography, conduct source-page and editorial review, integrate historical photographs subject to rights, then extend the system to the other Historic Center POIs.