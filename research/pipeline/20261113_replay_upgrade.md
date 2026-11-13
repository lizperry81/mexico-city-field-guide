# Full-batch replay corrective update (2026-11-13)

The existing `reconcile_git_batches.py` was upgraded on `research-persistence` to prevent a real data-loss issue: many historical GitHub files use `staged_id`, `candidate_findings`, `findings_candidate`, `documentary_findings`, or legacy `records`, while the prior importer read only one candidate array and synthesized IDs for `staged_id`. The upgraded importer collects every recognized array and preserves staged IDs. It also accepts single source-inspection objects, selected source-register proposals, and `source_id_raw` identifiers. Unparseable JSON now blocks replay rather than being silently skipped.

Run against a **complete branch checkout** and a verified staging SQLite, never against `main`:

```bash
python3 research/pipeline/reconcile_git_batches.py \
  --canonical /path/to/verified/CDMX_CANONICAL.sqlite \
  --staging /path/to/verified/CDMX_RESEARCH_CUMULATIVE_v20261113T0310Z_RESEARCH_ONLY.sqlite \
  --batch-dir research/batches --min-files 54 \
  --output /path/to/NEW_VERSIONED_RESEARCH_ONLY.sqlite \
  --report /path/to/replay-report.json
```

This command is **not claimed to have completed the full replay during this run**. The repository had 53 JSON research batches before the new 11-finding urban breadth batch, now 54. The current locally validated versioned staging SQLite contains 147 distinct staged finding IDs (118 inherited + 18 earlier additions + 11 new); it has not replayed all 54 GitHub JSONs and therefore is not the authoritative count for the entire GitHub historical backlog.

A separate tested local `replay_batches_v2.py` implementation and four passing unit tests are preserved inside the downloadable research recovery ZIP. The on-GitHub importer has been read-back verified as text, but its full 54-file execution is still outstanding. The versioned SQLite is not merged into V97 and does not authorize publication.

The research batch includes a possible repeat of an existing San Francisco convent 1861 finding: `cdmx-stg-20261113-urban-05` should be cross-linked to `stg-20261112-reforma-11` rather than counted as independently corroborated. All nine newly examined source records are at webpage/abstract level, not full publication inspection.

Canonical V97 remains pinned to SHA-256 `ac5a245a6c28aaf288237ca232ed51b74c42fd6292bdff931d65abc45a626846`; 616 sources, 422 claims, 403 claim-source links, 68 findings and 9 source inspections unchanged. No `main` modification, no automatic promotion.
