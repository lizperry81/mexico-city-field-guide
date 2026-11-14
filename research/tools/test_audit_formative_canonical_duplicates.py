#!/usr/bin/env python3
"""Regression tests for read-only canonical candidate scan."""
import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from audit_formative_canonical_duplicates import audit

class AuditTests(unittest.TestCase):
    def test_read_only_and_stale_baseline_rejection(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            db = root / "canonical.sqlite"
            conn = sqlite3.connect(db)
            conn.execute("CREATE TABLE sources (id TEXT, title TEXT, doi TEXT, url TEXT)")
            conn.execute("CREATE TABLE claims (id TEXT, claim_text TEXT)")
            conn.execute("CREATE TABLE canonical_findings (id TEXT, finding_text TEXT)")
            conn.execute("INSERT INTO sources VALUES ('s1', 'Tlatilco Acrobat object', '', '')")
            conn.execute("INSERT INTO claims VALUES ('c1', 'Tlatilco lies in Naucalpan')")
            conn.commit()
            conn.close()
            original = db.read_bytes()
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"database":{"sha256":hashlib.sha256(original).hexdigest(),
                "expected_counts":{"sources":1,"claims":1,"canonical_findings":0}}}))
            batch = root / "batch.json"
            batch.write_text(json.dumps({"batch_id":"fixture","findings":[{"finding_id":"F01",
                "subject":"Tlatilco lies in Naucalpan","assertion":"Tlatilco lies in Naucalpan"}],
                "sources":[{"id":"s1","title":"Tlatilco Acrobat object"}]}))
            report = audit(batch, db, manifest)
            self.assertEqual(report["promoted"],0)
            self.assertEqual(len(report["findings"]),1)
            self.assertEqual(len(report["sources"]),1)
            self.assertEqual(db.read_bytes(),original)
            db.write_bytes(original + b"tamper")
            with self.assertRaisesRegex(ValueError,"SHA-256 mismatch"):
                audit(batch,db,manifest)

if __name__=="__main__":
    unittest.main()
