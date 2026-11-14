# Long-form Discover manuscripts: human approval required

This folder is an **editorial staging area**, not the existing eight-stop field
walk or the preserved Centro historical dossier. The automated build must not
publish draft narratives or infer approval from inherited source identifiers.

A manuscript is named `<poi_slug>.json`. The `templo-mayor.json` placeholder
contains no new historical prose. Keep `status: "draft"` or `"in_review"`
while drafting. Only a deliberate editorial change to `"approved"` may enable
the separate long-form Discover page. This does **not** modify or replace the
homepage, canonical POI, review reader, field walk, sources, or saved comments.

To publish an approved manuscript, supply:

- `schema_version: 1`, `poi_slug`, `status: "approved"`.
- `approval` with named `editor`, `evidence_auditor`, `approved_on`,
  `editorial_review_complete: true`, and
  `page_specific_evidence_checked: true`.
- A nonempty `chapters` array, each with a unique lower-case hyphenated `id`,
  `title`, and `paragraphs`.
- Each paragraph as `{"text": "...", "evidence": [{"source_id": "...",
  "page_or_section": "...", "audit_status": "page_checked"}]}`.
  Do not use unverified identifiers or fabricated page locators.
- Optional `deep_dives` on each chapter, using `title`, `text`, and a nonempty
  `evidence` array with the same page-checked source-ID/locator contract as a
  narrative paragraph. Their full text must also appear verbatim in the
  chapter’s approved Markdown archive. A sidebar with no independently checked
  source must stay in draft and cannot be published.

**Verbatim preservation gate:** Before an approved manuscript can be built,
each chapter also needs a user-approved, exact Markdown archive at
`editorial/approved/<poi_slug>--<chapter_id>.md` and a companion
`<filename>.md.sha256`. Every paragraph in the manuscript must occur
verbatim and in order in that archived text. Both files must contain the real
approved chapter and checksum, with approval date and original conversation
or document provenance; never reconstruct missing text from a summary.
The build fails closed if archives are missing, have been changed, or disagree
with the paragraphs. The separate Discover JSON manuscripts are protected
by the editorial guard on both pull requests and direct pushes to `main`.

The builder checks the editorial gate and HTML-escapes content; it cannot
independently prove that a citation is accurate. A human research editor must
check page locators, provenance, Indigenous scholarship, and contested facts.

`python scripts/build_discover_editorial.py` stages reviewed HTML in
`site/poi/<poi_slug>/discover/index.html` and writes a public status manifest.
This is the separate manuscript route. The Templo Mayor review reader at
`/poi/templo-mayor/review/` contains the cited article prepared for reader feedback.
`python scripts/test_discover_editorial.py` guards the unpublished draft state
and verifies the gate against a synthetic nonhistorical manuscript.
