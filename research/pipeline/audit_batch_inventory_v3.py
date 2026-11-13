#!/usr/bin/env python3
"""Non-mutating batch/ID/source audit for a COMPLETE research-persistence checkout.
python research/pipeline/audit_batch_inventory_v3.py research/batches report.json 55
Never writes canonical SQLite, application data, or publication status.
"""
import hashlib, json, pathlib, sys
FINDING_KEYS=("findings","new_findings","candidate_findings","findings_candidate","documentary_findings","records")
SOURCE_KEYS=("sources","new_sources","source_register","proposed_bibliography","source_proposals")
INSPECTION_KEYS=("source_inspections","source_inspection","inspected_passages")
def canon(x): return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(",",":"))
def sha(raw): return hashlib.sha256(raw).hexdigest()
def rows(doc,keys):
    if isinstance(doc,list):return [("root_list",x) for x in doc if isinstance(x,dict)] if keys==FINDING_KEYS else []
    if not isinstance(doc,dict):return []
    out=[]
    for k in keys:
        v=doc.get(k)
        if isinstance(v,dict):out.append((k,v))
        elif isinstance(v,list):out.extend((k,x) for x in v if isinstance(x,dict))
    return out
def field(obj,keys):
    return next((obj[k] for k in keys if obj.get(k) not in (None,"",[])),None)
def audit(directory,min_files):
    files=sorted(directory.rglob("*.json"))
    if len(files)<min_files:raise ValueError("FAIL-CLOSED missing research batch files")
    seen_ids={};seen_sources={};inventory=[];issues=[];references=set();registered=set()
    count=0;substantive=0;index_only=0;inspections=0
    for path in files:
        raw=path.read_bytes();rel=path.relative_to(directory).as_posix()
        try:doc=json.loads(raw)
        except (ValueError,UnicodeError) as e:raise ValueError("FAIL-CLOSED bad JSON "+rel) from e
        one={"path":rel,"sha256":sha(raw),"git_blob_sha1":hashlib.sha1(("blob "+str(len(raw))+"\0").encode()+raw).hexdigest(),"finding_entries":0,"text_entries":0,"index_only_entries":0}
        for key,item in rows(doc,FINDING_KEYS):
            ident=field(item,("id","finding_id","staged_id","record_id"))
            digest=sha(canon(item).encode());rid=str(ident) if ident is not None else "sha256:"+digest
            statement=field(item,("assertion","statement","claim","finding","text"))
            valid=isinstance(statement,str) and bool(statement.strip())
            one["finding_entries"]+=1;one["text_entries"]+=int(valid);one["index_only_entries"]+=int(not valid)
            count+=1;substantive+=int(valid);index_only+=int(not valid)
            prior=seen_ids.get(rid)
            if prior and prior["sha256"]!=digest:issues.append({"type":"ID_COLLISION","id":rid,"first":prior["path"],"second":rel})
            else:seen_ids.setdefault(rid,{"sha256":digest,"path":rel})
            sr=field(item,("source_ids","sources","source_id"))
            if isinstance(sr,str):references.add(sr)
            elif isinstance(sr,list):references.update(x for x in sr if isinstance(x,str) and x)
        for key,item in rows(doc,SOURCE_KEYS):
            ident=field(item,("id","source_id","source_candidate_id","canonical_id"))
            if ident is None:continue
            ident=str(ident);registered.add(ident);digest=sha(canon(item).encode())
            prior=seen_sources.get(ident)
            if prior and prior["sha256"]!=digest:issues.append({"type":"SOURCE_ID_CONFLICT","id":ident,"first":prior["path"],"second":rel})
            else:seen_sources.setdefault(ident,{"sha256":digest,"path":rel})
        inspections+=len(rows(doc,INSPECTION_KEYS))
        inventory.append(one)
    return {"schema_version":1,"status":"AUDIT_ONLY_NO_CANONICAL_PROMOTION",
            "files":len(files),"file_inventory":inventory,"finding_like_entries":count,
            "substantive_statement_entries":substantive,"index_only_entries":index_only,
            "distinct_finding_ids":len(seen_ids),"source_inspection_entries":inspections,
            "source_id_conflicts_and_finding_collisions":issues,
            "source_refs_not_registered_in_batch_json":sorted(references-registered),
            "primary_source_inspection_not_inferred":True,"ready_for_editorial_review":False}
def main():
    if len(sys.argv)!=4:raise SystemExit("usage: audit_batch_inventory_v3.py BATCH_DIR OUTPUT_JSON MIN_FILES")
    directory=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2]);min_files=int(sys.argv[3])
    if out.exists():raise SystemExit("FAIL-CLOSED: output exists; use unique filename")
    result=audit(directory,min_files);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({k:result[k] for k in ("files","finding_like_entries","substantive_statement_entries","index_only_entries","distinct_finding_ids")}))
if __name__=="__main__":main()
