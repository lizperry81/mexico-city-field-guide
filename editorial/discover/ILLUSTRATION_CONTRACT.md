# Discover illustration publishing contract

Discover manuscripts remain unpublished until explicit human editorial approval, page-level evidence review, verbatim Markdown archives, and matching SHA-256 checksums. The recovered homepage and the distinct Explore physical stops stay intact.

The existing `editorial/discover/templo-mayor.json` remains **draft with zero approved chapters**. Do not auto-populate or approve it. The publication builder creates a separate `poi/<slug>/discover/` page only for an approved manuscript, leaving Explore untouched.

An approved chapter may carry an optional `visuals` array. Each item must supply `kind` (`historical_photo`, `artifact`, `map` or `timeline`), `after_paragraph` (1-based position), `asset_path` (a safe POI-relative `assets/discover/<name>.webp/png/jpg/svg`), `alt`, `caption`, `credit`, `rights_status` (`cleared` or `public_domain_verified`), `rights_basis` (permission or public-domain determination), and `evidence` (nonempty array containing `source_id`, `page_or_section` and `audit_status: page_checked`).

The asset must exist in the generated POI assets when the builder runs. No remote image, unidentified artifact, unlicensed catalog thumbnail, unverified caption, or unreviewed source locator may appear on the published page. Credits, source locators and rights basis are visible alongside the image. Visuals are inserted after their referenced paragraphs, preserving the approved prose verbatim and in order.

Any proposed historical correction still needs a separate before/after paragraph diff, citations and explicit user editorial approval. Neither an audit report nor a staged research batch grants that approval. The November 13 approved chapters *The Basin Before the Mexica* and *The Heart of Tenochtitlan* are not archival Markdown until their exact original bytes with provenance have been recovered.
