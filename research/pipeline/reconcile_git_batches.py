#!/usr/bin/env python3
"""Non-destructive CDMX GitHub batch importer; stdlib only.

Reads an immutable V97 canonical snapshot, a verified cumulative staging
snapshot, and EVERY JSON file from a GitHub research/batches checkout.
Creates a NEW versioned research-only SQLite, preserving originals and raw
provenance. No canonical promotion, editorial approval, or merge is performed.
"""
import argparse, hashlib, json, re, sqlite3
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
def key(obj,keys):
    # Preserve every array and singleton; earlier version read only first matching key.
    result=[]
    for k in keys:
        value=obj.get(k)
        if isinstance(value,list):result.extend(value)
        elif isinstance(value,dict):result.append(value)
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
    paths=sorted(Path(a.batch_dir).rglob("*.json"))
    if len(paths)<a.min_files:raise SystemExit(f'BLOCKED: only {len(paths)} batch files; expected at least {a.min_files}')
    for f in paths:
        try:v=json.loads(f.read_text())
        except (ValueError,UnicodeDecodeError) as e:raise SystemExit(f'BLOCKED: unparseable batch file {f}: {e}')
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
                   (rel,hashfile(f),f.read_text(encoding="utf-8")))
        if isinstance(v,dict) and isinstance(v.get("finding_ids"),list):
            for ix,fid in enumerate(v["finding_ids"]):
                if isinstance(fid,str) and fid.strip():
                    db.execute("INSERT OR IGNORE INTO research_batch_index_only VALUES(?,?,?,?)",
                               (rel,"finding_ids:"+str(ix),fid,enc({"id":fid})))
        if isinstance(v,list):findings=v;sources=[];inspections=[]
        elif isinstance(v,dict):
            findings=key(v,("findings","records","new_findings","candidate_findings","findings_candidate","documentary_findings"))
            sources=key(v,("sources","new_sources","source_register","source_proposals","proposed_bibliography"))
            if not sources:sources=listify(v.get("source"))
            inspections=key(v,("source_inspections","source_inspection"))
            if not inspections:inspections=listify(v.get("source_inspection"))
        else:continue
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
            iid=str(item.get("id") or item.get("source_id") or hashbytes(enc(item).encode())[:20])
            h=hashbytes(enc(item).encode())
            db.execute("INSERT OR IGNORE INTO research_batch_inspections VALUES(?,?,?,?)",
                       (iid,h,rel,enc(item)))
            inspection_count+=1
        for item in findings:
            if not isinstance(item,dict):continue
            claim=str(item.get("assertion") or item.get("statement") or item.get("claim") or item.get("finding") or item.get("text") or "")
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
    report={"schema_version":1,"canonical_sha256":PIN,
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
       "combined_distinct_candidate_ids":len(total),
       "github_inspection_entries":inspection_count,
       "candidate_source_identities":len(pending),
       "unknown_source_ids":sorted(missing_source_ids),"conflicts":conflicts,
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
