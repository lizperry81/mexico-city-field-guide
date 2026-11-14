"""88-batch private-only handoff rejection tests."""
import copy
from handoff_88_history import validate_frozen, validate_ledger

canonical = {"sources":616,"claims":422,"claim_sources":403,
             "canonical_findings":68,"canonical_source_inspections":9}
staged = {"github_batches_replayed":88,
 "github_distinct_substantive_finding_ids":574,"github_source_candidates":249,
 "github_inspection_entries":287,"source_metadata_collisions":2,
 "unknown_source_refs":1,"unknown_source_refs_without_inspection_metadata":["unknown"],
 "detached_source_identity_review_pending":37,"github_index_only_refs_unresolved":1,
 "new_historical_finding_candidates_this_run":11,
 "new_source_candidates_all_types_this_run":8,
 "new_source_inspection_metadata_this_run":8}
m = {"schema_version":4,"kind":"research_to_app_handoff",
 "handoff_contract_status":"88_batch_sqlite_integrity_github_full_binary_sha256_verified_noncanonical_unapproved",
 "canonical":canonical,"canonical_version":"V97",
 "canonical_status":"unchanged_provisional_V97_not_promoted",
 "research_commit_sha":"a"*40,"verified_replay_commit_sha":"a"*40,
 "canonical_hash":"b"*64,"versioned_research_sqlite_gz_path":"research/db.gz",
 "versioned_research_sha256":"c"*64,"compressed_sha256":"d"*64,
 "replay_report_path":"research/report.json",
 "immutable_handoff_path":"research/history.json",
 "latest_handoff_history_path":"research/history.json",
 "handoff_history_paths":["research/history.json"],
 "latest_reconciliation_ledger_path":"research/ledger.json",
 "reconciliation_artifact_paths":["research/ledger.json"],
 "replay_evidence":{"verification_ledger":"research/ledger.json",
   "snapshot_commit_sha":"a"*40,"compressed_checksum_path":"research/checksum",
   "readback_binary_git_blob_sha":"1"*40,"readback_report_git_blob_sha":"2"*40},
 "verified_binary_readback":{"git_blob_sha":"1"*40,"report_blob_sha":"2"*40,
   "compress_digest_recomputed_independently_from_github_fetched_base64":True},
 "research_batch_artifact_paths":["research/batch"],
 "coverage_artifact_paths":["research/coverage"],
 "chapter_audit_artifact_paths":["research/audit"],
 "staged_counts":staged,
 "evidence_status":"research_database_integrated_noncanonical_not_editorially_corroborated",
 "ready_for_editorial_review":False,"ready_for_publication":False,
 "canonical_promoted":False,"publication_approved":False,
 "auto_merge_permitted":False,"blockers":["unreviewed"]}
f = {k:copy.deepcopy(v) for k,v in m.items() if k in (
 "schema_version","canonical","canonical_version","canonical_status",
 "research_commit_sha","verified_replay_commit_sha","canonical_hash",
 "versioned_research_sqlite_gz_path","versioned_research_sha256",
 "compressed_sha256","replay_report_path","evidence_status",
 "ready_for_editorial_review","ready_for_publication","canonical_promoted",
 "publication_approved","blockers")}
f.update(kind="append_only_research_to_app_verified_history",
  branch="research-persistence",no_auto_merge=True,
  verification_ledger_path="research/ledger.json",
  source_batch_artifact_paths=["research/batch"],
  coverage_artifact_paths=["research/coverage"],
  chapter_audit_artifact_paths=["research/audit"],
  staged_counts={"github_batches":88,"findings":574,"sources":249,"source_inspections":287},
  source_identity_conflicts=[{"source":"A"},{"source":"B"}],
  unknown_source_ids=["unknown"],detached_inspections_pending=37)
actual={"sqlite":"1"*40,"report":"2"*40,"input":"3"*40,
        "coverage":"4"*40,"chapter":"5"*40,"compressed":"6"*40}
l = {"schema_version":2,"kind":"github_research_reconciliation_full_binary_readback",
 "branch":"research-persistence","repository":"lizperry81/mexico-city-field-guide",
 "input_research_commit_sha":"a"*40,"replay_snapshot_commit_sha":"a"*40,
 "verified_file_blobs":{name:{"path":path,"blob_sha":actual[name]} for name,path in (
     ("input","research/batch"),("coverage","research/coverage"),
     ("chapter","research/audit"),("report","research/report.json"),
     ("compressed","research/checksum"))},
 "versioned_sqlite_gz_path":"research/db.gz",
 "github_readback_sqlite_gz_git_blob_sha":"1"*40,
 "github_readback_compressed_size_bytes":100,
 "github_readback_hash_matches":True,
 "github_readback_compressed_sha256_independently_recomputed":"d"*64,
 "committed_compressed_sha256":"d"*64,
 "uncompressed_sqlite_sha256_from_workflow_report":"c"*64,
 "canonical_counts":canonical,"canonical_version":"V97",
 "canonical_hash":"b"*64,"canonical_tables_preserved":88,
 "canonical_rows_unchanged":True,"sqlite_integrity":"ok","foreign_key_violations":0,
 "staged_before":{"github_batches":87,"findings":563,
                  "sources":241,"source_inspections":279},
 "staged_after":f["staged_counts"],
 "unresolved_source_ids":["unknown"],
 "source_metadata_collisions":f["source_identity_conflicts"],
 "unresolved_index_only_finding_ids":["id"],"detached_inspection_count":37,
 "source_identity_auto_merges":0,"workflow_runs_success":True,
 "canonical_promoted":False,"publication_approved":False,
 "ready_for_editorial_review":False,"no_main_modification":True,
 "warnings":["unverified"]}
validate_frozen(m,f)
validate_ledger(m,f,l,actual)
for key,value in (("ready_for_publication",True),("canonical_promoted",True),
                  ("no_auto_merge",False),
                  ("staged_counts",dict(f["staged_counts"],findings=575)),
                  ("verification_ledger_path","research/other")):
    bad=copy.deepcopy(f);bad[key]=value
    try: validate_frozen(m,bad)
    except ValueError: pass
    else: raise AssertionError("Accepted unsafe frozen field: "+key)
for key,value in (("publication_approved",True),
                  ("github_readback_hash_matches",False),
                  ("canonical_rows_unchanged",False),
                  ("staged_after",dict(l["staged_after"],findings=575)),
                  ("verified_file_blobs",{**l["verified_file_blobs"],
                       "report":{"path":"research/report.json","blob_sha":"0"*40}})):
    bad=copy.deepcopy(l);bad[key]=value
    try: validate_ledger(m,f,bad,actual)
    except ValueError: pass
    else: raise AssertionError("Accepted unsafe ledger field: "+key)
print("PASS: 88-batch private-only provenance rejection tests")
