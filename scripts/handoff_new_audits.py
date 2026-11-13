"""Normalize strictly unapproved, version-pinned research audits into private review tasks.

These are candidate source-check assignments, not approved Discover chapters,
public citations, geographic instructions, or historically corroborated facts.
"""
import re

HEX40 = re.compile(r"^[0-9a-f]{40}$")
KINDS = {
    "templo_mayor_discover_exact_prose_claim_to_source_locator_addendum",
    "1985_reconstruction_legal_text_to_site_locator_audit",
    "templo_mayor_discover_reading_mode_editorial_gate",
    "templo_mayor_discover_actual_reader_claim_to_source_locator_audit",
}


def require(ok, reason):
    if not ok:
        raise ValueError("New research audit: " + reason)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def review_item(path, ident, topic, *, anchor=None, reader_match=None,
                locators=None, source_ids=None, status=None, gap=None,
                proposed_addition=None):
    require(text(ident) and text(topic), "missing candidate ID or subject")
    require(anchor is None or text(anchor), "invalid proposed reader anchor")
    locators = locators if locators is not None else []
    source_ids = source_ids if source_ids is not None else []
    require(isinstance(locators, list) and bool(locators), "source locator absent")
    require(isinstance(source_ids, list) and all(text(x) for x in source_ids),
            "source identities malformed")
    require(all(isinstance(x, dict) and text(x.get("locator")) and
                (text(x.get("url")) or text(x.get("document")) or
                 text(x.get("source")) or text(x.get("source_ids")))
                for x in locators), "source locators must preserve source identity")
    return {
        "audit_path": path,
        "audit_claim_id": ident,
        "topic_for_review": topic,
        "reader_paragraph_index_proposed": None,
        "reader_anchor_proposed": anchor,
        "reader_audit_matches_main_blob": reader_match,
        "candidate_evidence_summary_unverified": None,
        "source_locator_candidates_unverified": locators,
        "proposed_editorial_addition_unapproved": proposed_addition,
        "candidate_finding_id": ident if ident.startswith("STG-") else None,
        "candidate_evidence_status": status,
        "source_url_proposed": None,
        "source_locator_proposed": None,
        "source_access_claimed": None,
        "remaining_source_check": gap,
        "read_before_context_proposed": None,
        "on_site_context_proposed": None,
        "source_ids_unverified": source_ids,
        "editorial_passage_id": None,
        "source_id_confirmed": None,
        "page_or_section_checked": None,
        "publication_authorization": False,
        "review_state": ("awaiting_human_stale_reader_blob_reaudit"
                         if reader_match is False else
                         "awaiting_human_source_and_passage_check"),
    }


def parse_new_audit(path, doc, current_reader_blob):
    """Return None for older audit formats, otherwise a private queue list.

    The format-specific publication flags and historical source limitations
    must be explicit. Never promote metadata simply because its paths exist.
    """
    kind = doc.get("kind")
    if kind not in KINDS:
        return None
    for flag in ("publication_approved", "editorial_approved",
                 "ready_for_publication", "canonical_promoted"):
        require(doc.get(flag) is not True, "audit claims editorial authority")
    if kind == "templo_mayor_discover_exact_prose_claim_to_source_locator_addendum":
        require(doc.get("publication_approved") is False and
                doc.get("ready_for_editorial_review") is False and
                doc.get("main_modified") is False and
                text(doc.get("claim_id")) and text(doc.get("reader_anchor")) and
                text(doc.get("proposed_unpublished_historical_addition")),
                "Triple Alliance chronology conflict lacks nonpublication safeguards")
        rows = doc.get("claim_to_source_locator_matrix")
        require(isinstance(rows, list) and rows, "missing dated-source comparison")
        for row in rows:
            require(isinstance(row, dict) and
                    text(row.get("source")) and text(row.get("locator")) and
                    text(row.get("url")), "incomplete chronological source locator")
        return [review_item(
            path, doc["claim_id"], doc.get("topic") or doc["reader_anchor"],
            anchor=doc["reader_anchor"],
            locators=[{"source": row["source"], "url": row["url"],
                       "locator": row["locator"],
                       "access_scope": row.get("access_scope"),
                       "does_not_establish": row.get("does_not_establish")}
                      for row in rows],
            status=doc.get("evidence_status"),
            gap=doc.get("next_verification"),
            proposed_addition=doc["proposed_unpublished_historical_addition"],
        )]
    if kind == "1985_reconstruction_legal_text_to_site_locator_audit":
        require(doc.get("evidence_status") ==
                "partial_source_based_chapter_audit_not_approved" and
                text(doc.get("site")), "legal source review is not provisionally labelled")
        clauses = doc.get("clauses")
        require(isinstance(clauses, list) and clauses,
                "legal paragraph-source checks absent")
        result = []
        for row in clauses:
            require(isinstance(row, dict) and text(row.get("finding_id")) and
                    isinstance(row.get("source_ids"), list) and
                    row["source_ids"] and all(text(x) for x in row["source_ids"]) and
                    text(row.get("locator")) and text(row.get("uncertainty")),
                    "legal clause lacks finding ID/source/uncertainty")
            result.append(review_item(
                path, row["finding_id"], "1985 reconstruction: " + row["locator"],
                locators=[{"source": sid, "locator": row["locator"]}
                          for sid in row["source_ids"]],
                source_ids=row["source_ids"], status=doc["evidence_status"],
                gap=row["uncertainty"]))
        return result
    if kind == "templo_mayor_discover_reading_mode_editorial_gate":
        require(doc.get("ready_for_editorial_review") is False and
                doc.get("publication_approved") is False and
                doc.get("main_modified") is False and
                doc.get("not_reverified_against_new_main_in_this_run") is True and
                HEX40.fullmatch(doc.get("verified_reader_blob_sha_from_previous_audit", "")),
                "reading-mode audit incorrectly implies fresh main reader review")
        gates = doc.get("claim_to_reading_gate")
        require(isinstance(gates, list) and gates, "reading-mode checks absent")
        result = []
        for idx, row in enumerate(gates, 1):
            require(isinstance(row, dict) and
                    all(text(row.get(key)) for key in
                        ("topic", "mode", "evidence", "locator",
                         "status", "editorial_action")),
                    "reading-mode check is incomplete")
            result.append(review_item(
                path, f"templo-reading-mode-{idx:02d}", row["topic"],
                reader_match=False,
                locators=[{"document": row["evidence"],
                           "locator": row["locator"]}],
                status=row["status"], gap=row["editorial_action"]))
        return result
    # A new seven-passage audit includes the ACTUAL reader Git blob identity.
    require(kind == "templo_mayor_discover_actual_reader_claim_to_source_locator_audit",
            "unexpected audit type")
    source_blob = doc.get("target_main_blob_sha")
    require(doc.get("target_path") == "poi/templo-mayor/reader.html" and
            isinstance(source_blob, str) and HEX40.fullmatch(source_blob) and
            isinstance(current_reader_blob, str) and
            HEX40.fullmatch(current_reader_blob) and
            doc.get("main_modified") is False and
            doc.get("canonical_modified") is False and
            doc.get("ready_for_editorial_review") is False and
            doc.get("ready_for_publication") is False,
            "seven-passage audit lacks pinned reader/nonpublication proof")
    rows = doc.get("passages")
    require(isinstance(rows, list) and rows, "pinned paragraph checks absent")
    result = []
    for row in rows:
        require(isinstance(row, dict) and
                all(text(row.get(k)) for k in
                    ("id", "anchor", "reader_section", "status",
                     "risk", "editorial_action", "learning_mode")) and
                row["learning_mode"] in
                    ("pre_read_history", "pre_read_discovery_history",
                     "pre_read_history_with_optional_on_site_locator",
                     "split_pre_read_myth_and_on_site_observation"),
                "exact-reader historical paragraph missing review details")
        locators = row.get("source_locator_matrix")
        require(isinstance(locators, list) and locators,
                "pinned paragraph is missing source comparators")
        result.append(review_item(
            path, row["id"], row["risk"], anchor=row["anchor"],
            reader_match=source_blob == current_reader_blob,
            locators=locators, status=row["status"], gap=row["editorial_action"]))
    return result
