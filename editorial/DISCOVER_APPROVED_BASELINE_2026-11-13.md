# Discover editorial baseline — approved 2026-11-13

Status: **EDITORIAL BASELINE LOCKED**. Applies to all automated and manual work on Discover. Approval in the ChatGPT editorial conversation on 2026-11-13: user described the chapter **“The Basin Before the Mexica”** as “much better” and requested using it as the baseline. The previous **“The Heart of Tenochtitlan”** opening chapter was also positively approved as the model for Discover.

## Scope and preservation

- Discover is a substantial, illustrated, chronological historical reading experience, with precise claims, dates, places, material culture, political processes, and careful distinctions between evidence and interpretation.
- Preserve the complete approved narrative prose, chronology, section order, and substantive depth. Keep photographs, artifacts, maps, diagrams, and explanatory captions integral to the experience. Any public image requires identity, accurate caption, rights assessment, and attribution.
- **Discover** tells the larger historical story; **Explore** provides situated, observational, on-site guidance. Do not move Explore-style prompts or site directions into Discover.
- Use direct, positive, specific prose. Avoid repetitive “not X but Y”, “not merely”, “not simply”, vague filler, and shallow visitor-guide summaries.
- The approved chapter “The Basin Before the Mexica” moves through: ancient lake system; Pleistocene inhabitants and mammoths; lakeshore communities and Zohapilco; Formative villages and Tlatilco; Cuicuilco and Xitle; Teotihuacan; post-Teotihuacan politics, Tula and Toltec inheritance; Culhuacan and Tepanec Azcapotzalco; the political, ecological and religious world inherited by the Mexica.
- The 2026-11-13 approved chapter text **exists in the editorial conversation**. This file records the approval and acceptance criteria; it does **not** purport to contain an exact verbatim archival copy of that chapter. Before any prose replacement, commit a verbatim archival snapshot and a working copy to the repository, preserving provenance and approval date.

## Research-to-publication protocol

1. Claude and ChatGPT research agents may append evidence records to staged research branches; research imports never rewrite Discover prose automatically.
2. Match new findings to relevant chapters and paragraphs, with exact citations, evidence quality, confidence, and a proposed editorial change.
3. Keep proposed changes in a separate draft branch or PR. Preserve original text and show a human-readable before/after diff and reason for every substantive edit.
4. Corrections to demonstrable factual errors receive priority, but require evidence and transparent review. New discoveries may justify added passages, images, sidebars, or citations.
5. Do not delete, truncate, simplify, or replace approved historical content merely to satisfy UI constraints, token limits, automation quotas, or new research batch counts.
6. Only merge substantial changes to approved Discover prose after explicit user editorial approval. No automation may silently reapprove itself.
7. Maintain a dated revision log: section, finding/source, change rationale, approval, commit SHA.
8. Keep Discover's historical narrative readable without requiring the reader to open panels; optional deep dives should add meaningful depth rather than repeat the main text.

## Regression checks for developers and QA

- Verify approved chapter presence, section coverage, historical depth, narrative readability, English captions/labels, and image provenance.
- Check that Discover has not been replaced by construction-only, on-site observation, generic site-summary, placeholder, or research-metrics content.
- Check that Explore remains distinct and the home page and existing features are preserved.
- Fail/review any pull request that removes an approved section or sharply reduces chapter length without explicit approval.
- The baseline policy is a safeguard, **not an automated enforcement mechanism by itself**; implement repository tests and branch protection to enforce it.

## Next implementation action

Archive the exact approved 2026-11-13 Discover chapter text in a versioned file, add a SHA-256 checksum, and compare all subsequent revisions against that archival file. Do not claim the verbatim snapshot exists until committed and verified.
