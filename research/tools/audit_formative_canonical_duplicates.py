#!/usr/bin/env python3
"""Read-only, fail-closed comparison of a staged research batch to canonical V97."""
import argparse
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from difflib import SequenceMatcher

def normalize(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()

def rows(conn, table):
    quoted = '"' + table.replace('"', '""') + '"'
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM " + quoted)]
    except sqlite3.DatabaseError:
        return []

def best_match(query, records, fields):
    needle = normalize(query)
    if not needle:
        return None
    matches = []
    for rec in records:
        for field in fields:
            if field not in rec or not isinstance(rec[field], str):
                continue
            hay = normalize(rec[field])
            if len(hay) < 12:
                continue
            score = SequenceMatcher(None, needle, hay).ratio()
            if needle == hay or (len(needle) >= 30 and needle in hay):
                score = 1.0
            if score >= .67:
                matches.append((score, str(rec.get("id", rec.get("source_id", rec.get("claim_id", "")))), field))
    return dict(zip(("score", "record_id", "field"), max(matches))) if matches else None

def audit(batch, db, manifest):
    data = json.loads(Path(batch).read_text(encoding="utf-8"))
    baseline = json.loads(Path(manifest).read_text(encoding="utf-8"))["database"]
    raw_hash = hashlib.sha256(Path(db).read_bytes()).hexdigest()
    if raw_hash != baseline["sha256"]:
        raise ValueError("Canonical SHA-256 mismatch; refusing stale or altered baseline")
    uri = Path(db).resolve().as_uri() + "?mode=ro&immutable=1"
    con = sqlite3.connect(uri, uri=True)
    con.row_factory = sqlite3.Row
    try:
        if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("SQLite integrity check failed")
        expected = baseline["expected_counts"]
        for table, count in expected.items():
            actual = con.execute('SELECT count(*) FROM "' + table.replace('"', '""') + '"').fetchone()[0]
            if actual != count:
                raise ValueError(f"Canonical count mismatch for {table}: {actual} != {count}")
        sources = rows(con, "sources")
        claims = rows(con, "claims")
        findings = rows(con, "canonical_findings")
        review = []
        for item in data["findings"]:
            related = []
            for col in ("subject", "assertion"):
                m = best_match(item.get(col), claims + findings, ("claim_text", "text", "statement", "finding_text", "title", "subject", "description"))
                if m:
                    related.append({"query_field": col, **m})
            review.append({"finding_id": item["finding_id"], "possible_matches": related,
                           "disposition": "MANUAL_REVIEW_REQUIRED", "promoted": False})
        source_review = []
        for src in data["sources"]:
            matches = []
            for col in ("title", "doi", "url"):
                value = src.get(col)
                if value:
                    m = best_match(value, sources, ("title", "doi", "url", "source_title", "source_url"))
                    if m:
                        matches.append({"query_field": col, **m})
            source_review.append({"source_id": src["id"], "possible_matches": matches})
        return {"batch_id": data["batch_id"], "canonical_sha256": raw_hash,
                "canonical_counts_verified": True, "findings": review, "sources": source_review,
                "promoted": 0, "status": "READ_ONLY_CANDIDATE_SCAN_NOT_SOURCE_VERIFICATION"}
    finally:
        con.close()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--batch", required=True)
    p.add_argument("--canonical", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    report = audit(a.batch, a.canonical, a.manifest)
    Path(a.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Checked", len(report["findings"]), "findings and", len(report["sources"]), "sources; no canonical writes")

if __name__ == "__main__":
    main()
