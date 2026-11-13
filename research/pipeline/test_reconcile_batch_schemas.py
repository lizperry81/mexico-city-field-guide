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
    def test_legacy_subject_evidence_is_a_full_assertion(self):
        # Five TE28 2007 records were incorrectly counted as index-only, despite
        # retaining detailed sample dates and precise source locations.
        item={"id":"20261112T0700Z-auto09-F01","subject":"Area B posthole",
              "evidence":"Two dated samples occur in vertical order.",
              "loc":"pp.21-24 Tables 1-2"}
        self.assertEqual(importer.extract_claim(item),
                         "Area B posthole: Two dated samples occur in vertical order.")

    def test_provenance_repair_not_misclassified_as_historical_claim(self):
        item={"id":"STG20261111T1302Z-RECON-V87-PRIMARY-001",
              "category":"provenance_repair",
              "issue":"Secondary citation currently replaces primary record",
              "resolution":"Flag primary record for inspection"}
        self.assertEqual(importer.extract_claim(item), "")

    def test_existing_claim_text_takes_precedence_over_extracted_fallback(self):
        item={"id":"X","claim":"Original assertion","subject":"Subject","evidence":"E"}
        self.assertEqual(importer.extract_claim(item),"Original assertion")

    def test_compressed_batch_reader_preserves_inspections(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"detached.json.gz"
            raw=json.dumps({"row_count":2,"source_inspections":[{"id":"i1"},{"id":"i2"}]})
            with gzip.open(p,"wt",encoding="utf-8") as f:
                f.write(raw)
            obj, decoded=importer.load_batch_json(p)
            self.assertEqual(decoded,raw)
            self.assertEqual([x["id"] for x in importer.inspection_records(obj)],["i1","i2"])

    def test_inspection_url_matching_ignores_tracking_not_path(self):
        a={"url":"https://www.INAH.gob.mx/research/report/?utm_source=test"}
        b={"url":"http://inah.gob.mx/research/report"}
        c={"url":"http://inah.gob.mx/research/other"}
        self.assertEqual(importer.inspection_identity_fields(a)["url"],
                         importer.inspection_identity_fields(b)["url"])
        self.assertNotEqual(importer.inspection_identity_fields(a)["url"],
                            importer.inspection_identity_fields(c)["url"])

    def test_detached_crosswalk_flags_same_url_across_id_namespaces(self):
        import sqlite3
        db=sqlite3.connect(":memory:")
        db.execute("CREATE TABLE research_batch_inspections(source_path TEXT,inspection_id TEXT,payload_json TEXT)")
        old={"id":"old","source_id":"OLD-ID","url":"https://example.edu/source/a"}
        new={"id":"new","source_id":"NEW-ID","original_inspection":{"source_url":"https://example.edu/source/a","portion_examined":"another section"}}
        db.execute("INSERT INTO research_batch_inspections VALUES(?,?,?)",("old.json","old",json.dumps(old)))
        db.execute("INSERT INTO research_batch_inspections VALUES(?,?,?)",
                   ("20261113T0803Z-detached-original-inspections-37.json.gz","new",json.dumps(new)))
        self.assertEqual(importer.detached_inspection_crosswalk(db,"20261113T0803Z-detached-original-inspections-37.json.gz")[0]["status"],
                         "same_source_url_candidate")

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

    def test_nested_source_metadata_retains_identity_without_promoting_source(self):
        x={"source_inspection":{"source":{"id":"STG-SRC-HIRTH-2019-COMPOUND17",
             "title":"Obsidian workshop","doi":"10.1017/example"},
             "access":"selected passage"}}
        matches=importer.embedded_source_candidates(x)
        self.assertEqual(len(matches),1)
        self.assertEqual(matches[0]["source_id"],"STG-SRC-HIRTH-2019-COMPOUND17")
        self.assertEqual(matches[0]["identity_basis"],"embedded_source_object_id")
        self.assertEqual(matches[0]["original_inspection"]["access"],"selected passage")

    def test_unregistered_source_id_from_inspection_is_a_candidate(self):
        x={"source_inspections":[{"inspection_id":"insp-1","source_id":"SRC-1",
            "title":"Research article","url":"https://example.edu/article"}]}
        m=importer.embedded_source_candidates(x)
        self.assertEqual(len(m),1)
        self.assertEqual(m[0]["source_id"],"SRC-1")

    def test_historical_1985_source_ids_in_inspection_id_field_are_candidates(self):
        x={"source_inspections":[{"id":"stg-src-massolo-1986",
            "title":"Housing and earthquakes","url":"https://unam.mx/journal"}]}
        m=importer.embedded_source_candidates(x)
        self.assertEqual(m[0]["identity_basis"],"source_like_inspection_id_unconfirmed")

    def test_carballo_legacy_inspection_is_not_lost(self):
        obj={"inspection":{"id":"i1","source_id":"STG-SRC-CARBALLO-2011-MOON-PYRAMID",
                           "title":"Obsidian and the Teotihuacan State",
                           "url":"https://sites.pitt.edu/monograph.pdf"}}
        self.assertEqual(len(importer.inspection_records(obj)),1)
        matches=importer.embedded_source_candidates(obj)
        self.assertEqual(matches[0]["source_id"],
                         "STG-SRC-CARBALLO-2011-MOON-PYRAMID")
        self.assertEqual(matches[0]["origin_field"],"inspection")

    def test_generic_inspection_status_is_not_falsely_registered(self):
        self.assertEqual(importer.inspection_records(
            {"inspection":{"status":"PDF failed","error":"unavailable"}}),[])
        self.assertEqual(importer.embedded_source_candidates(
            {"inspection":{"status":"PDF failed","error":"unavailable"}}),[])

    def test_unknown_bare_inspection_id_not_mistaken_for_bibliographic_id(self):
        x={"source_inspections":[{"id":"inspection-001",
            "title":"An article","url":"https://example.edu"}]}
        self.assertEqual(importer.embedded_source_candidates(x),[])

    def test_scalar_inspection_count_creates_no_metadata(self):
        self.assertEqual(importer.embedded_source_candidates(
            {"new_source_inspections":27}),[])

    def test_no_source_examination_inferred_from_scalar_summary(self):
        self.assertEqual(importer.inspection_records({"new_source_inspections": 4}), [])


if __name__ == "__main__":
    unittest.main()
