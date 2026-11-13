"""Regression checks for non-destructive cross-schema batch ingestion.

Run: python3 -m unittest discover -s research/pipeline -p 'test_*.py'
"""
import unittest
import reconcile_git_batches as importer


class ReplaySchemaTests(unittest.TestCase):
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
