"""Regression checks for non-destructive cross-schema batch ingestion.

Run: python3 -m unittest discover -s research/pipeline -p 'test_*.py'
"""
import unittest
import gzip
import json
import tempfile
from pathlib import Path
import reconcile_git_batches as importer


class ReplaySchemaTests(unittest.TestCase):
    def test_compressed_batch_reader_preserves_inspections(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"detached.json.gz"
            raw=json.dumps({"row_count":2,"source_inspections":[{"id":"i1"},{"id":"i2"}]})
            with gzip.open(p,"wt",encoding="utf-8") as f:
                f.write(raw)
            obj, decoded=importer.load_batch_json(p)
            self.assertEqual(decoded,raw)
            self.assertEqual([x["id"] for x in importer.inspection_records(obj)],["i1","i2"])

    def test_detached_inspection_crosswalk_does_not_auto_merge(self):
        import sqlite3
        db=sqlite3.connect(":memory:")
        db.execute("CREATE TABLE research_batch_inspections(source_path TEXT,inspection_id TEXT,payload_json TEXT)")
        old={"id":"first","source_id":"SRC","portion_examined":"abstract"}
        new={"id":"second","source_id":"SRC","original_inspection":{"source_id":"SRC","portion_examined":"chapter two"}}
        db.execute("INSERT INTO research_batch_inspections VALUES(?,?,?)",("older.json","first",json.dumps(old)))
        db.execute("INSERT INTO research_batch_inspections VALUES(?,?,?)",
                   ("20261113T0803Z-detached-original-inspections-37.json.gz","second",json.dumps(new)))
        x=importer.detached_inspection_crosswalk(db,"20261113T0803Z-detached-original-inspections-37.json.gz")
        self.assertEqual(x[0]["status"],"same_source_identity_scope_unverified")

    def test_keyed_sources_keep_ids(self):
        d = {"sources": {"s1": {"url": "https://example.org/a", "scope": "abstract"},
                         "s2": {"title": "Historical manuscript transcription"}}}
        rows = importer.source_records(d)
        self.assertEqual([x["id"] for x in rows], ["s1", "s2"])

    def test_arrays_are_not_dropped(self):
        d = {"source_register": [{"id": "A"}], "sources": [{"source_id": "B"}]}
        rows = importer.source_records(d)
        self.assertEqual({x.get("id", x.get("source_id")) for x in rows}, {"A", "B"})

    def test_conflicting_key_and_id_fails_closed(self):
        with self.assertRaises(SystemExit):
            importer.source_records({"sources": {"registered-A": {"id": "B"}}})

    def test_inspection_variants_are_additive(self):
        d = {"source_inspections": [{"id": "old"}],
             "new_source_inspections": 7,
             "combined_source_inspections": 31,
             "source_material_accessed": [{"id": "new", "scope": "selected section"}]}
        rows = importer.inspection_records(d)
        self.assertEqual([x["id"] for x in rows], ["old", "new"])

    def test_inspection_arrays_all_retained(self):
        d = {"source_inspections": [{"id": "one"}],
             "new_source_inspections": [{"id": "two"}],
             "combined_source_inspections": [{"id": "three"}]}
        self.assertEqual(len(importer.inspection_records(d)), 3)

    def test_no_source_examination_inferred_from_scalar_summary(self):
        self.assertEqual(importer.inspection_records({"new_source_inspections": 4}), [])


if __name__ == "__main__":
    unittest.main()
