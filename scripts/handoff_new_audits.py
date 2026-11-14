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
    "templo_mayor_actual_reader_targeted_claim_evidence_addendum",
    "templo_mayor_discover_cross_period_and_current_reader_evidence_gate",
    "templo_mayor_discover_exact_reader_seven_topic_source_locator_audit",
    "templo_mayor_exact_reader_blob_and_urban_chronology_boundary",
    "chapter_level_claim_to_source_locator_audit",
    "templo_mayor_chapter_evidence_maintenance_and_1910_chronology_boundary",
    "templo_mayor_discover_opening_chapter_source_locator_matrix_and_cross_period_boundary",
    "templo_mayor_discover_opening_narrative_claim_to_source_locator_matrix",
}


def require(ok, reason):
    if not ok:
        raise ValueError("New research audit: " + reason)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def review_item(path, ident, topic, *, anchor=None, reader_match=None,
                locators=None, source_ids=None, status=None, gap=None,
                proposed_addition=None, allow_missing_sources=False):
    require(text(ident) and text(topic), "missing candidate ID or subject")
    require(anchor is None or text(anchor), "invalid proposed reader anchor")
    locators = locators if locators is not None else []
    source_ids = source_ids if source_ids is not None else []
    require(isinstance(locators, list) and (bool(locators) or allow_missing_sources),
            "source locator absent")
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
                         "awaiting_human_missing_original_source"
                         if not locators else
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
    if kind == "templo_mayor_chapter_evidence_maintenance_and_1910_chronology_boundary":
        require(doc.get("branch") == "research-persistence" and
                doc.get("target_branch_read_only") == "main" and
                doc.get("target_path") == "poi/templo-mayor/reader.html" and
                doc.get("publication_approved") is False and
                doc.get("ready_for_editorial_review") is False and
                doc.get("original_text_was_re_read") is True and
                HEX40.fullmatch(doc.get("target_main_blob_sha", "")),
                "1910 chronological boundary lacks verified immutable reader scope")
        rows = doc.get("claim_source_locator_matrix")
        require(isinstance(rows, list) and bool(rows) and text(doc.get("boundary")),
                "1910 chronological boundary lacks archived source checks")
        result = []
        for index, row in enumerate(rows, 1):
            require(isinstance(row, dict) and
                    all(text(row.get(k)) for k in
                        ("topic", "reader_anchor", "source_locator", "status", "next")) and
                    row["source_locator"].startswith("research/audits/") and
                    row["source_locator"].endswith(".json"),
                    "1910 boundary has an untraceable prior audit")
            result.append(review_item(
                path, f"centenario-boundary-{index:02d}", row["topic"],
                anchor=row["reader_anchor"],
                reader_match=doc["target_main_blob_sha"] == current_reader_blob,
                locators=[{"document": row["source_locator"],
                           "locator": "Prior audit pointer; original historical source pending"}],
                status=row["status"], gap=row["next"]))
        return result
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
                    (text(row.get("url")) or
                     (row.get("repository_path") ==
                      "poi/templo-mayor/reader.html" and
                      isinstance(row.get("blob_sha"), str) and
                      HEX40.fullmatch(row["blob_sha"]))),
                    "incomplete chronological source locator")
        return [review_item(
            path, doc["claim_id"], doc.get("topic") or doc["reader_anchor"],
            anchor=doc["reader_anchor"],
            locators=[{"source": row["source"], "url": row.get("url"),
                       "locator": row["locator"],
                       "repository_path": row.get("repository_path"),
                       "blob_sha": row.get("blob_sha"),
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
    # Later dated research batches use two forms of source-located gates
    # plus an explicit boundary record. All remain PRIVATE proposals. Pin
    # the historical reader blob and mark its stale/current status on every
    # item; nothing in these documents establishes editorial approval.
    gate_kinds = {
        "templo_mayor_actual_reader_targeted_claim_evidence_addendum",
        "templo_mayor_discover_cross_period_and_current_reader_evidence_gate",
        "templo_mayor_discover_exact_reader_seven_topic_source_locator_audit",
        "chapter_level_claim_to_source_locator_audit",
        "templo_mayor_discover_opening_chapter_source_locator_matrix_and_cross_period_boundary",
        "templo_mayor_discover_opening_narrative_claim_to_source_locator_matrix",
    }
    boundary_kind = "templo_mayor_exact_reader_blob_and_urban_chronology_boundary"
    if kind in gate_kinds | {boundary_kind}:
        blob = (doc.get("target_main_blob_sha") or doc.get("reader_blob_sha")
                or doc.get("previous_reader_blob_sha")
                or doc.get("reader_blob_sha_last_verified")
                or doc.get("reader_blob_sha_verified"))
        require(doc.get("branch") == "research-persistence" and
                doc.get("target_branch_read_only") == "main" and
                doc.get("target_path") == "poi/templo-mayor/reader.html" and
                isinstance(blob, str) and HEX40.fullmatch(blob) and
                isinstance(current_reader_blob, str) and
                HEX40.fullmatch(current_reader_blob) and
                doc.get("publication_approved") is False and
                doc.get("ready_for_editorial_review") is False,
                "dated reader audit lacks pinned main blob/nonpublication status")
        if kind == "chapter_level_claim_to_source_locator_audit":
            reread = doc.get("reader_re_read_this_run")
            require(type(reread) is bool and
                    doc.get("no_publication_of_unverified_claims") is True,
                    "cross-period audit lacks explicit readback/nonpublication status")
            if reread is False:
                # A recent research batch can reference a *previously* audited
                # main reader. Keep its gates in the private queue while
                # explicitly marking the reader comparison stale, even when
                # the historical blob still equals the current main blob.
                require(doc.get("reader_blob_sha_last_verified") == blob and
                        doc.get("reader_blob_sha") in (None, blob) and
                        doc.get("target_main_blob_sha") in (None, blob),
                        "stale reader audit has no consistent historical blob pin")
            else:
                # Merely renaming an old SHA to 'last verified' cannot turn a
                # stale research audit into a freshly checked main reader.
                require(doc.get("reader_blob_sha") == blob or
                        doc.get("target_main_blob_sha") == blob or
                        doc.get("reader_blob_sha_verified") == blob,
                        "fresh reader audit lacks an independently pinned main blob")
        if kind in ("templo_mayor_discover_opening_chapter_source_locator_matrix_and_cross_period_boundary",
                    "templo_mayor_discover_opening_narrative_claim_to_source_locator_matrix"):
            require(doc.get("no_publication_of_unverified_claims") is True,
                    "opening narrative audit lacks explicit nonpublication restriction")
            if doc.get("reader_re_read_this_run") is False:
                require(doc.get("previous_reader_blob_sha") == blob,
                        "stale opening audit must declare its previous reader identity")
        matches = (blob == current_reader_blob and
                   doc.get("reader_re_read_this_run") is not False)
        if kind == boundary_kind:
            anchors = doc.get("reader_anchors")
            locators = doc.get("source_locator_matrix")
            require(text(doc.get("boundary")) and isinstance(anchors, list)
                    and bool(anchors) and isinstance(locators, list)
                    and bool(locators), "urban-period boundary is missing its sources")
            for item in anchors:
                require(isinstance(item, dict) and
                        all(text(item.get(k)) for k in ("topic", "anchor", "status", "needs")),
                        "incomplete preserved earlier historical gate")
            checked_locators = []
            for row in locators:
                require(isinstance(row, dict) and
                        isinstance(row.get("source_ids"), list) and
                        row["source_ids"] and
                        all(text(v) for v in row["source_ids"]) and
                        text(row.get("locator")) and text(row.get("use")),
                        "modern-city boundary lacks source locators")
                checked_locators.append({
                    "source": "; ".join(row["source_ids"]),
                    "locator": row["locator"], "restricted_use": row["use"]})
            return [review_item(
                path, "modern-city-hall-1928-boundary",
                "1928–29 municipal reforms: separate Modern City chapter",
                reader_match=matches, locators=checked_locators,
                status="separate_chapter_pending_evidence_audit",
                gap=doc["boundary"])]
        rows = doc.get("gates")
        require(isinstance(rows, list) and bool(rows),
                "dated reader audit lacks paragraph-specific gates")
        result = []
        for index, row in enumerate(rows, 1):
            require(isinstance(row, dict) and text(row.get("reader_anchor")),
                    "dated reader gate lacks an exact prose anchor")
            ident = row.get("id") or f"dated-reader-gate-{index:02d}"
            topic = (row.get("topic") or row.get("historical_correction")
                     or row["reader_anchor"])
            require(text(topic) and text(ident),
                    "dated reader gate has no identifiable historical question")
            source_rows = (row["source_locator_matrix"]
                           if "source_locator_matrix" in row
                           else row.get("source_locators", row.get("locators")))
            require(isinstance(source_rows, list) and
                    (bool(source_rows) or
                     kind == "templo_mayor_discover_cross_period_and_current_reader_evidence_gate"),
                    "dated reader gate has no traceable source comparison")
            locators = []
            unattributed_hints = []
            for source_row in source_rows:
                require(isinstance(source_row, dict),
                        "dated reader source locator is malformed")
                prior_audit = source_row.get("prior_audit")
                if prior_audit is not None:
                    require(text(prior_audit) and
                            prior_audit.startswith("research/audits/") and
                            prior_audit.endswith(".json"),
                            "previous evidence audit reference is unsafe")
                    # This is a pointer to earlier work, not new corroboration.
                    locators.append({"document": prior_audit,
                                     "locator": "prior audit only; original source check pending"})
                    continue
                source = (source_row.get("source_id") or source_row.get("source")
                          or source_row.get("path") or source_row.get("url"))
                locator = (source_row.get("pages") or source_row.get("locator")
                           or source_row.get("detail"))
                if (kind == "chapter_level_claim_to_source_locator_audit" and
                        not text(source) and text(locator) and
                        doc.get("no_publication_of_unverified_claims") is True and
                        text(row.get("uncertainty"))):
                    # The 90-batch producer supplies unattributed research
                    # hints, not actual source/page pairs. Keep the wording
                    # for human discovery but never launder it into a locator.
                    unattributed_hints.append(locator)
                    continue
                require(text(source) and text(locator),
                        "dated reader gate has no source identity and page locator")
                locators.append({"source": source, "locator": locator})
            require(text(row.get("hold") or row.get("uncertainty")),
                    "dated reader gate must preserve its evidence limitation")
            item = review_item(
                path, ident, topic, anchor=row["reader_anchor"],
                reader_match=matches, locators=locators,
                source_ids=[x["source"] for x in locators if x.get("source")],
                status=row.get("status") or row.get("disposition") or "unapproved",
                gap=row.get("hold") or row.get("uncertainty"),
                proposed_addition=row.get("draft_candidate") or
                                  row.get("historical_addition"),
                allow_missing_sources=not bool(locators))
            if unattributed_hints:
                item["unattributed_locator_hints_unverified"] = unattributed_hints
                item["review_state"] = "awaiting_human_original_source_identification"
            result.append(item)
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
                     "pre_read_museum_history",
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
