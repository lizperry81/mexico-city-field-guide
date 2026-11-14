"""Unattributed citations must remain private research hints, never page-checked sources."""
import copy
from handoff_new_audits import parse_new_audit

blob = "a" * 40
audit = {
    "kind": "chapter_level_claim_to_source_locator_audit",
    "branch": "research-persistence",
    "target_branch_read_only": "main",
    "target_path": "poi/templo-mayor/reader.html",
    "reader_re_read_this_run": True,
    "reader_blob_sha_verified": blob,
    "no_publication_of_unverified_claims": True,
    "ready_for_editorial_review": False,
    "publication_approved": False,
    "gates": [{
        "topic": "CUPA source criticism, outside the archaeological chapter",
        "reader_anchor": "A preserved reader anchor for testing",
        "status": "source_gate_open_not_editorially_approved",
        "source_locators": [{
            "locator": "Previous INAH reference: identity and exact page unverified"
        }],
        "uncertainty": "Primary source and locator need identification",
        "historical_addition": "Unapproved and not publishable",
    }],
}
items = parse_new_audit("research/audits/test-unattributed.json", audit, blob)
assert len(items) == 1
item = items[0]
assert item["source_locator_candidates_unverified"] == []
assert item["source_ids_unverified"] == []
assert item["source_id_confirmed"] is None
assert item["page_or_section_checked"] is None
assert item["publication_authorization"] is False
assert item["review_state"] == "awaiting_human_original_source_identification"
assert item["unattributed_locator_hints_unverified"] == [
    audit["gates"][0]["source_locators"][0]["locator"]]
stale = parse_new_audit("research/audits/test-unattributed.json", audit, "b" * 40)
assert stale[0]["review_state"] == (
    "awaiting_human_stale_reader_blob_reaudit_and_source_identification")
assert stale[0]["publication_authorization"] is False

for alter in (
    lambda d: d.update(no_publication_of_unverified_claims=False),
    lambda d: d["gates"][0].update(uncertainty=""),
    lambda d: d["gates"][0].update(source_locators=[{}]),
    lambda d: d.update(ready_for_editorial_review=True),
    lambda d: d["gates"][0].update(
        source_locators=[{"source_id": "source without a locator"}]),
):
    invalid = copy.deepcopy(audit)
    alter(invalid)
    try:
        parse_new_audit("research/audits/test-unattributed.json", invalid, blob)
    except ValueError:
        pass
    else:
        raise AssertionError("Malformed or falsely reviewed source hint accepted")

# Fully identified sources remain explicit source/locator candidates, still
# unapproved; a source cannot inherit approval from another research gate.
identified = copy.deepcopy(audit)
identified["gates"][0]["source_locators"] = [
    {"source_id": "SOURCE-X", "pages": "p. 17"}]
identified_task = parse_new_audit("research/audits/identified.json", identified, blob)[0]
assert identified_task["source_ids_unverified"] == ["SOURCE-X"]
assert identified_task["source_locator_candidates_unverified"] == [
    {"source": "SOURCE-X", "locator": "p. 17"}]
assert "unattributed_locator_hints_unverified" not in identified_task
assert identified_task["publication_authorization"] is False
print("PASS: missing source identity remains a private, unapproved research hint")
