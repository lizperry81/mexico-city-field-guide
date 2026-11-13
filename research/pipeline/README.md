# CDMX research reconciliation — non-destructive importer

The current authoritative pointer remains **V97** (616 sources, 422 claims, 403 claim-source links, 68 normalized findings; baseline SHA-256 `ac5a245a6c28aaf288237ca232ed51b74c42fd6292bdff931d65abc45a626846`). Do not silently promote research candidates.

Use `research/pipeline/reconcile_git_batches.py` on a checkout of `research-persistence` with an independently verified cumulative staging SQLite. It imports **all** JSON files under `research/batches` and creates a NEW, versioned research-only SQLite. It fails closed if any baseline table changes, checks the V97 hash and row counts, retains raw batch JSON, preserves candidate source IDs and inspections, records ID collisions, verifies SQLite integrity and foreign keys, and emits a reconciliation report.

```bash
python3 research/pipeline/reconcile_git_batches.py \
  --canonical research/canonical/CDMX_CANONICAL.sqlite \
  --staging /verified/previous/CDMX_STAGING.sqlite \
  --batch-dir research/batches \
  --output /safe/new/CDMX_RESEARCH_CUMULATIVE_vNEXT.sqlite \
  --report /safe/new/reconciliation.json
```

**The importer never changes the canonical input** and never sets editorial approval. It does not merge into `main`, publish claims, or change the canonical manifest. Binary output persistence requires separate GitHub or Library upload and verified download/readback. Existing staged metadata remain provisional; duplicate IDs and source-alias candidates require human audit.

2026-11-13 local test: baseline 88 tables unchanged; 118 inherited staged candidates plus 18 recovered/new candidates = 136 distinct locally verified staged IDs, SQLite integrity OK and foreign key violations 0. The local test imported three batch JSON inputs (10 Hospital de Jesús, eight Templo Mayor); **not all 53 GitHub batch files were replayed locally**. The repository importer is designed to replay all 53 on a checkout, after the current staging snapshot is supplied. Neither its GitHub deployment nor the local test establishes complete cross-version reconciliation.

Coverage: `research/coverage/coverage-matrix-20261113-compact.json` stores 16×12×11 provisional ratings. The automated labels do not establish chapter-level substantial coverage; the full evidence matrix remains in the research recovery artifact. Chapter evidence: `research/audits/templo-mayor-discover-20261113.json`, not an audit of the as-yet-inaccessible exact Discover prose.
