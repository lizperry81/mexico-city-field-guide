# Research pipeline (isolated branch)
Baseline: Library V97, SHA-256 ac5a245a6c28aaf288237ca232ed51b74c42fd6292bdff931d65abc45a626846.
GitHub staging works. Canonical SQLite is NOT YET uploaded to this branch. No production branch changes.
The workflow deliberately fails closed until research/canonical/CDMX_CANONICAL.sqlite and research/canonical/manifest.json are present and checksums match. This prevents misleading green success statuses. Historical records must be reconciled before merge. Do not import synthetic tests as historical findings.
