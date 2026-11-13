#!/usr/bin/env python3
"""Non-destructive CDMX GitHub batch importer; stdlib only.

Reads an immutable V97 canonical snapshot, a verified cumulative staging
snapshot, and EVERY JSON file from a GitHub research/batches checkout.
Creates a NEW versioned research-only SQLite, preserving originals and raw
provenance. No canonical promotion, editorial approval, or merge is performed.
"""
import argparse, gzip, hashlib, json, re, sqlite3
from urllib.parse import urlsplit, parse_qsl, urlencode
from pathlib import Path

PIN = "ac5a245a6c28aaf288237ca232ed51b74c42fd6292bdff931d65abc45a626846"
EXPECTED = {"sources":616,"claims":422,"claim_sources":403,
            "canonical_findings":68,"canonical_source_inspections":9}
def enc(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def hashbytes(x): return hashlib.sha256(x).hexdigest()
def hashfile(p): return hashbytes(Path(p).read_bytes())
def rowhash(c,t):
    cols=[x[1] for x in c.execute('PRAGMA table_info("'+t+'")')]
    arr=[enc(dict(zip(cols,x))) for x in c.execute('SELECT * FROM "'+t+'"')]
    return hashbytes("\n".join(sorted(arr)).encode())
def tables(c):
    return [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
def listify(x):
    if isinstance(x,list):return x
    if isinstance(x,dict):return [x]
    return []
def source_records(obj):
    """Preserve source arrays AND named source maps (e.g. {'s1': {'url': ...}}).

    Source IDs embedded in map keys were silently dropped by earlier imports.
    Each original raw batch remains stored independently of this normalized index.
    """
    result=[]
    for field in ("sources","new_sources","source_register","source_proposals","proposed_bibliography","source"):
        val=obj.get(field)
        if isinstance(val,list):
            result.extend(x for x in val if isinstance(x,dict))
        elif isinstance(val,dict):
            if any(k in val for k in ("id","source_id","title","url","author","creator")):
                result.append(val)
            else:
                for sid,record in val.items():
                    if isinstance(record,dict):
                        if record.get("id") and str(record["id"])!=str(sid):
                            raise SystemExit("BLOCKED: conflicting source-map key and source ID")
                        result.append({"id":str(sid),**record})
    return result
def inspection_records(obj):
    """Capture all actual inspection payloads, never scalar summary counts."""
    result = key(obj, ("source_inspections", "source_inspection",
                       "new_source_inspections", "combined_source_inspections",
                       "source_material_accessed"))
    # Some batches (e.g. Carballo 2011) use singular "inspection".
    # Only accept it when it carries a source identity; do not consume generic
    # review/status notes using the same label.
    for record in listify(obj.get("inspection")):
        if isinstance(record, dict) and (
            isinstance(record.get("source_id"), str)
            or isinstance(record.get("source"), dict)
        ):
            result.append(record)
    return result
def key(obj,keys):
    # Preserve every array and singleton; earlier version read only first matching key.
    result=[]
    for k in keys:
        value=obj.get(k)
        if isinstance(value,list):result.extend(value)
        elif isinstance(value,dict):result.append(value)
    return result
def extract_claim(item):
    """Extract a research assertion without pretending an audit note is one.

    Older TE28 research uses a 'subject' and a substantive 'evidence' paragraph,
    instead of the later 'claim'/'assertion' schema. Retain this material in the
    finding index, while preserving the original payload and its caveats.
    Provenance-only issue/resolution records intentionally remain index-only.
    """
    claim = next((item[k] for k in ("assertion", "statement", "claim", "finding", "text")
                  if isinstance(item.get(k), str) and item[k].strip()), "")
    if claim:
        return claim
    subject, evidence = item.get("subject"), item.get("evidence")
    if isinstance(subject, str) and subject.strip() and isinstance(evidence, str) and evidence.strip():
        return subject.strip() + ": " + evidence.strip()
    return ""

def load_batch_json(path):
    """Read UTF-8 JSON or immutable gzip-compressed UTF-8 JSON without losing raw content."""
    with (gzip.open(path, "rt", encoding="utf-8") if path.name.endswith(".json.gz")
          else path.open("rt", encoding="utf-8")) as stream:
        raw = stream.read()
    return json.loads(raw), raw


def embedded_source_candidates(obj):
    """Index bibliographic identity *candidates* buried in inspection envelopes.

    Historical batch formats put real titles/URLs in source_inspection or
    source_material_accessed rather than a dedicated source_register. Preserve
    the entire original inspection separately; this function does NOT register
    a scholarly source, establish source equivalence, or confer corroboration.
    """
    if not isinstance(obj, dict):
        return []
    result = []
    for field in ("source_inspections", "source_inspection", "source_material_accessed", "inspection"):
        for item in listify(obj.get(field)):
            if not isinstance(item, dict):
                continue
            nested = item.get("source")
            source = nested if isinstance(nested, dict) else item
            if not isinstance(source, dict):
                continue
            sid = source.get("source_id")
            basis = "explicit_inspection_source_id"
            if not sid and isinstance(nested, dict):
                sid = source.get("id")
                basis = "embedded_source_object_id"
            if not sid and field == "source_material_accessed":
                sid = source.get("id")
                basis = "material_access_record_id_unconfirmed"
            if not sid and str(source.get("id") or "").lower().startswith(("stg-src-", "stage-src-")):
                sid = source.get("id")
                basis = "source_like_inspection_id_unconfirmed"
            if not isinstance(sid, str) or not sid.strip():
                continue
            has_locator = any(isinstance(source.get(k), str) and source[k].strip()
                              for k in ("title", "source_title", "url", "source_url",
                                        "publisher_url", "doi", "author", "authors"))
            if not has_locator:
                continue
            result.append({"source_id": sid.strip(), "origin_field": field,
                           "identity_basis": basis, "original_inspection": item})
    return result

def inspection_source_id(item):
    if item.get("source_id"):
        return str(item["source_id"])
    original = item.get("original_inspection")
    if isinstance(original, dict):
        return str(original.get("source_id") or original.get("id") or "")
    return ""

def inspection_identity_fields(item):
    """Weak candidate keys, never automatic source-identity equivalence."""
    raw = item.get("original_inspection") if isinstance(item.get("original_inspection"),dict) else item
    def pick(*names):
        return next((str(raw[n]).strip() for n in names if isinstance(raw.get(n),str) and raw[n].strip()),"")
    url=pick("source_url","url","link","web_url","landing_page")
    if not url:
        url=next((str(item[n]).strip() for n in ("source_url","url") if isinstance(item.get(n),str) and item[n].strip()),"")
    if url:
        try:
            parts=urlsplit(url)
            if parts.scheme not in ("https","http"): url=""
            else:
                host=parts.netloc.lower().removeprefix("www.")
                # Preserve substantive query parameters; discard only tracking.
                query=urlencode(sorted((k,v) for k,v in parse_qsl(parts.query,keep_blank_values=True)
                                       if not k.lower().startswith(("utm_","fbclid","gclid"))))
                url=(host+parts.path.rstrip("/").lower()+("?"+query if query else ""))
        except ValueError: url=""
    doi=pick("doi","DOI")
    if not doi and "doi.org/" in url:
        doi=url.split("doi.org/",1)[1]
    doi=doi.lower().removeprefix("https://doi.org/").removeprefix("http://doi.org/")
    title=re.sub(r"\\s+"," ",pick("source_title","title")).strip().casefold()
    return {"url":url,"doi":doi,"title":title}

def detached_inspection_crosswalk(conn, detached_batch):
    """Status is strictly possible identity overlap, never editorial equivalence."""
    rows = [(p, i, json.loads(raw))
            for p, i, raw in conn.execute(
                "SELECT source_path, inspection_id, payload_json FROM research_batch_inspections")]
    base = [(p, i, x) for p, i, x in rows if p != detached_batch]
    detached = [(p, i, x) for p, i, x in rows if p == detached_batch]
    result = []
    for _, iid, wrapped in detached:
        sid = inspection_source_id(wrapped)
        exact = sorted({bid for _, bid, existing in base
                        if (existing == wrapped.get("original_inspection")
                            or existing.get("original_inspection") == wrapped.get("original_inspection"))
                        and isinstance(wrapped.get("original_inspection"), dict)})
        same_source = sorted({bid for _, bid, existing in base
                              if sid and inspection_source_id(existing) == sid})
        key=inspection_identity_fields(wrapped)
        same_url=sorted({bid for _, bid, existing in base
                         if key["url"] and inspection_identity_fields(existing)["url"]==key["url"]})
        same_doi=sorted({bid for _, bid, existing in base
                         if key["doi"] and inspection_identity_fields(existing)["doi"]==key["doi"]})
        same_title=sorted({bid for _, bid, existing in base
                           if len(key["title"])>=20 and inspection_identity_fields(existing)["title"]==key["title"]})
        if exact: status = "same_structured_payload_candidate"
        elif same_source: status = "same_source_identity_scope_unverified"
        elif same_doi: status = "same_doi_candidate"
        elif same_url: status = "same_source_url_candidate"
        elif same_title: status = "same_title_candidate"
        else: status = "no_existing_candidate_match"
        result.append({"detached_inspection_id":iid, "source_id":sid,
                       "status":status,"exact_candidates":exact,
                       "same_source_candidates":same_source,
                       "same_url_candidates":same_url,"same_doi_candidates":same_doi,
                       "same_title_candidates":same_title})
    return result

def main():
    p=argparse.ArgumentParser()
    for a in ("canonical","batch-dir","output","report"):
        p.add_argument("--"+a,required=True)
    p.add_argument("--staging",help="Optional previously validated cumulative staging SQLite; omitted runs from unchanged V97")
    p.add_argument('--min-files',type=int,default=53,help='Fail closed if fewer than verified historical GitHub files')
    a=p.parse_args()
    canonical=Path(a.canonical);staging=Path(a.staging) if a.staging else canonical;dest=Path(a.output)
    if dest.exists():raise SystemExit("BLOCKED: output exists; choose a new versioned name")
    if not canonical.is_file() or not staging.is_file():raise SystemExit("BLOCKED: inputs absent")
    if hashfile(canonical)!=PIN:raise SystemExit("BLOCKED: V97 baseline hash mismatch")
    c=sqlite3.connect("file:"+str(canonical)+"?mode=ro",uri=True)
    s=sqlite3.connect("file:"+str(staging)+"?mode=ro",uri=True)
    baseline=tables(c)
    if not set(baseline)<=set(tables(s)):raise SystemExit("BLOCKED: missing V97 tables")
    for t,expected in EXPECTED.items():
        if c.execute('SELECT COUNT(*) FROM "'+t+'"').fetchone()[0]!=expected:
            raise SystemExit("BLOCKED: canonical count changed in "+t)
    drift=[t for t in baseline if rowhash(c,t)!=rowhash(s,t)]
    if drift:raise SystemExit("BLOCKED: historical records changed in "+",".join(drift))
    dest.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(dest) as o:s.backup(o)
    s.close()
    db=sqlite3.connect(dest)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS research_batch_raw_documents(
           path TEXT PRIMARY KEY,content_sha256 TEXT NOT NULL,raw_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS research_batch_index_only(
           path TEXT NOT NULL,record_key TEXT NOT NULL,finding_id TEXT NOT NULL,
           payload_json TEXT NOT NULL,PRIMARY KEY(path,record_key));
        CREATE TABLE IF NOT EXISTS research_batch_files(
           path TEXT PRIMARY KEY,content_sha256 TEXT NOT NULL,ingest_status TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS research_batch_findings(
           finding_id TEXT NOT NULL,payload_sha256 TEXT NOT NULL,source_path TEXT NOT NULL,
           assertion TEXT NOT NULL,payload_json TEXT NOT NULL,
           editorial_status TEXT NOT NULL DEFAULT 'not_publication_ready',
           PRIMARY KEY(finding_id,payload_sha256,source_path));
        CREATE TABLE IF NOT EXISTS research_batch_sources(
           source_id TEXT NOT NULL,payload_sha256 TEXT NOT NULL,source_path TEXT NOT NULL,
           payload_json TEXT NOT NULL,identity_status TEXT NOT NULL DEFAULT 'unreconciled',
           PRIMARY KEY(source_id,payload_sha256,source_path));
        CREATE TABLE IF NOT EXISTS research_batch_inspections(
           inspection_id TEXT NOT NULL,payload_sha256 TEXT NOT NULL,source_path TEXT NOT NULL,
           payload_json TEXT NOT NULL,PRIMARY KEY(inspection_id,payload_sha256,source_path));
        CREATE TABLE IF NOT EXISTS research_batch_embedded_source_metadata(
           source_id TEXT NOT NULL,metadata_sha256 TEXT NOT NULL,source_path TEXT NOT NULL,
           origin_field TEXT NOT NULL,identity_basis TEXT NOT NULL,payload_json TEXT NOT NULL,
           review_status TEXT NOT NULL DEFAULT 'candidate_metadata_not_registered',
           PRIMARY KEY(source_id,metadata_sha256,source_path,origin_field));
        CREATE TABLE IF NOT EXISTS research_batch_conflicts(
           conflict_sha256 TEXT PRIMARY KEY,reason TEXT NOT NULL,details_json TEXT NOT NULL);
    """)
    baseline_ids={r[0] for r in db.execute("SELECT id FROM canonical_findings")}
    staged={r[0]:r[1] for r in db.execute("SELECT finding_id,assertion FROM staged_findings")} if "staged_findings" in tables(db) else {}
    known_sources={r[0] for r in db.execute("SELECT id FROM sources")}
    if "staged_source_register" in tables(db):
        known_sources.update(r[0] for r in db.execute("SELECT id FROM staged_source_register"))
    conflicts=[];pending=set();missing_source_ids=set();file_count=0;inspection_count=0
    # Track cross-batch identity conflicts; never collapse distinct assertions.
    github_assertions={};source_metadata={};changed_input_paths=[]
    paths=sorted([*Path(a.batch_dir).rglob("*.json"), *Path(a.batch_dir).rglob("*.json.gz")])
    if len(paths)<a.min_files:raise SystemExit(f'BLOCKED: only {len(paths)} batch files; expected at least {a.min_files}')
    for f in paths:
        try:v,raw_text=load_batch_json(f)
        except (ValueError,UnicodeError,OSError) as e:
            raise SystemExit(f'BLOCKED: unreadable or invalid JSON batch {f}: {e}')
        if isinstance(v,dict) and "row_count" in v and "source_inspections" in v:
            actual=len(listify(v["source_inspections"]))
            if int(v["row_count"])!=actual:
                raise SystemExit(f"BLOCKED: declared source inspection count differs in {f}")
        rel=f.relative_to(Path(a.batch_dir)).as_posix()
        # A previously ingested path changing bytes is a provenance conflict.
        old=db.execute("SELECT content_sha256 FROM research_batch_files WHERE path=?",(rel,)).fetchone()
        if old and old[0]!=hashfile(f):
            changed_input_paths.append({"path":rel,"old_sha256":old[0],"incoming_sha256":hashfile(f)})
            raise SystemExit("BLOCKED: previously ingested research batch modified: "+rel)
        db.execute("INSERT OR IGNORE INTO research_batch_files VALUES(?,?,?)",
                   (rel,hashfile(f),"raw_source_preserved_in_checkout"))
        file_count+=1
        db.execute("INSERT OR IGNORE INTO research_batch_raw_documents VALUES(?,?,?)",
                   (rel,hashfile(f),raw_text))
        if isinstance(v,dict) and isinstance(v.get("finding_ids"),list):
            for ix,fid in enumerate(v["finding_ids"]):
                if isinstance(fid,str) and fid.strip():
                    db.execute("INSERT OR IGNORE INTO research_batch_index_only VALUES(?,?,?,?)",
                               (rel,"finding_ids:"+str(ix),fid,enc({"id":fid})))
        if isinstance(v,list):findings=v;sources=[];inspections=[];embedded=[]
        elif isinstance(v,dict):
            findings=key(v,("findings","records","new_findings","candidate_findings","findings_candidate","documentary_findings"))
            sources=source_records(v)
            inspections=inspection_records(v)
            embedded=embedded_source_candidates(v)
        else:continue
        for candidate in embedded:
            payload=enc(candidate["original_inspection"])
            db.execute("INSERT OR IGNORE INTO research_batch_embedded_source_metadata VALUES(?,?,?,?,?,?,?)",
                       (candidate["source_id"],hashbytes(payload.encode()),rel,
                        candidate["origin_field"],candidate["identity_basis"],payload,
                        "candidate_metadata_not_registered"))
        for item in sources:
            if not isinstance(item,dict):continue
            sid=str(item.get("id") or item.get("source_id") or "").strip()
            if not sid:continue
            h=hashbytes(enc(item).encode())
            if sid in source_metadata and source_metadata[sid]!=h:
                conflicts.append({"source_id":sid,"source_path":rel,"reason":"cross_batch_source_metadata_collision"})
            source_metadata.setdefault(sid,h)
            db.execute("INSERT OR IGNORE INTO research_batch_sources VALUES(?,?,?,?,?)",
                       (sid,h,rel,enc(item),"identity_pending"))
            pending.add(sid)
        for item in inspections:
            if not isinstance(item,dict):continue
            iid=str(item.get("id") or item.get("inspection_id") or item.get("source_id") or hashbytes(enc(item).encode())[:20])
            h=hashbytes(enc(item).encode())
            db.execute("INSERT OR IGNORE INTO research_batch_inspections VALUES(?,?,?,?)",
                       (iid,h,rel,enc(item)))
            inspection_count+=1
        for item in findings:
            if not isinstance(item,dict):continue
            claim=extract_claim(item)
            if not claim:
                fid=str(item.get("id") or item.get("finding_id") or item.get("staged_id") or item.get("record_id") or "anon-"+hashbytes(enc(item).encode())[:20])
                db.execute("INSERT OR IGNORE INTO research_batch_index_only VALUES(?,?,?,?)",
                           (rel,"item:"+str(len(pending))+":"+hashbytes(enc(item).encode())[:16],fid,enc(item)))
                continue
            fid=str(item.get("id") or item.get("finding_id") or item.get("staged_id") or item.get("record_id") or "anon-"+hashbytes(enc(item).encode())[:20])
            if fid in github_assertions and github_assertions[fid]!=claim:
                conflicts.append({"finding_id":fid,"source_path":rel,"reason":"cross_batch_assertion_collision"})
            github_assertions.setdefault(fid,claim)
            if fid in baseline_ids or (fid in staged and claim!=staged[fid]):
                conflicts.append({"finding_id":fid,"source_path":rel,"reason":"identity_collision_needs_manual_review"})
            sid=item.get("source_ids") or ([item["source_id"]] if item.get("source_id") else [item["source_id_raw"]] if item.get("source_id_raw") else [item["source_candidate_id"]] if item.get("source_candidate_id") else [])
            if isinstance(sid,str):sid=[sid]
            for x in sid:
                if isinstance(x,str) and x not in known_sources and x not in pending:missing_source_ids.add(x)
            h=hashbytes(enc(item).encode())
            db.execute("INSERT OR IGNORE INTO research_batch_findings VALUES(?,?,?,?,?,?)",
                       (fid,h,rel,claim,enc(item),"not_publication_ready"))
    # Source records may appear in LATER batch files. Resolve only after full replay.
    missing_source_ids.difference_update(known_sources | pending)
    for item in conflicts:
        h=hashbytes(enc(item).encode())
        db.execute("INSERT OR IGNORE INTO research_batch_conflicts VALUES(?,?,?)",
                   (h,item["reason"],enc(item)))
    db.commit()
    integrity=db.execute("PRAGMA integrity_check").fetchone()[0]
    fk=db.execute("PRAGMA foreign_key_check").fetchall()
    preserved=all(rowhash(c,t)==rowhash(db,t) for t in baseline)
    ids={r[0] for r in db.execute("SELECT finding_id FROM research_batch_findings")}
    index_ids={r[0] for r in db.execute("SELECT DISTINCT finding_id FROM research_batch_index_only")}
    unresolved_index_only=sorted(index_ids-ids-set(staged)-baseline_ids)
    total=ids|set(staged)
    detached_file="20261113T0803Z-detached-original-inspections-37.json.gz"
    detached_crosswalk=detached_inspection_crosswalk(db,detached_file)
    if detached_file in {p.name for p in paths} and len(detached_crosswalk)!=37:
        raise SystemExit("BLOCKED: detached inspection record count was not exactly 37")
    detached_status_counts={k:sum(x["status"]==k for x in detached_crosswalk)
                            for k in ("same_structured_payload_candidate",
                                      "same_source_identity_scope_unverified",
                                      "same_doi_candidate","same_source_url_candidate",
                                      "same_title_candidate","no_existing_candidate_match")}
    report={"schema_version":2,"canonical_sha256":PIN,
       "staging_sha256":hashfile(staging),"output_sha256":hashfile(dest),
       "canonical_tables_preserved":len(baseline),"canonical_rows_unchanged":preserved,
       "canonical_counts":EXPECTED,"existing_staged_findings":len(staged),
       "github_batch_json_files_examined":file_count,
       "github_candidate_finding_ids":len(ids),
       "index_only_finding_refs":db.execute("SELECT COUNT(*) FROM research_batch_index_only").fetchone()[0],
       "index_only_distinct_ids":len(index_ids),
       "index_only_resolved_by_substantive_findings":len(index_ids)-len(unresolved_index_only),
       "unresolved_index_only_ids":unresolved_index_only,
       "unresolved_index_only_count":len(unresolved_index_only),
       "raw_batch_documents_in_sqlite":db.execute("SELECT COUNT(*) FROM research_batch_raw_documents").fetchone()[0],
       "batch_file_inventory":[{"path":p.relative_to(Path(a.batch_dir)).as_posix(),
           "sha256":hashfile(p)} for p in paths],
       "combined_distinct_candidate_ids":len(total),
       "github_inspection_entries":inspection_count,
       "detached_inspection_crosswalk":{"incoming_rows":len(detached_crosswalk),
           "status_counts":detached_status_counts, "entries":detached_crosswalk,
           "semantics":"Same source is NOT a duplicate inspection; retain all records pending manual comparison"},
       "unique_inspection_payload_rows":db.execute("SELECT COUNT(*) FROM research_batch_inspections").fetchone()[0],
       "inspection_count_semantics":"Metadata/partial scopes as recorded; not verified direct full-source inspections",
       "candidate_source_identities":len(pending),
       "unknown_source_ids":sorted(missing_source_ids),
       "unknown_source_id_count":len(missing_source_ids),
       "embedded_inspection_source_metadata_rows":db.execute(
           "SELECT COUNT(*) FROM research_batch_embedded_source_metadata").fetchone()[0],
       "unknown_source_refs_with_inspection_metadata":sorted(
           missing_source_ids & {x[0] for x in db.execute(
               "SELECT DISTINCT source_id FROM research_batch_embedded_source_metadata")}),
       "unknown_source_refs_without_inspection_metadata":sorted(
           missing_source_ids - {x[0] for x in db.execute(
               "SELECT DISTINCT source_id FROM research_batch_embedded_source_metadata")}),
       "metadata_only_resolution_policy":"Inspection citation candidates do not equal registered sources or independent corroboration",
       "conflicts":conflicts,
       "cross_batch_conflict_count":len(conflicts),"changed_input_paths":changed_input_paths,
       "sqlite_integrity":integrity,"foreign_key_violations":len(fk),
       "status":"research_database_staging_only_NOT_CANONICAL",
       "ready_for_editorial_review":False,"ready_for_publication":False}
    db.close();c.close()
    if integrity!="ok" or fk or not preserved:
        dest.unlink(missing_ok=True)
        raise SystemExit("BLOCKED: validation failed, new output deleted")
    Path(a.report).write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
