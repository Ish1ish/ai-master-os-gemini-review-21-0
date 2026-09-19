#!/usr/bin/env python3
"""Fail-closed final release evidence gate for AI Master OS O40.

Local checks never print secret values and never perform external writes.
Target-environment checks remain explicitly MANUAL unless evidence files are supplied.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys, tempfile, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'release'/'manifest.json'

REQUIRED_RUNTIME=(
 'AI_OS_ENV','AI_OS_MODEL_BASE_URL','AI_OS_MODEL_API_KEY','AI_OS_MODEL_NAME',
 'AI_OS_SEARCH_BASE_URL','AI_OS_SEARCH_API_KEY','AI_OS_IDENTITY_SIGNING_SECRET',
 'AI_OS_MEMORY_DB_PATH','AI_OS_AUDIT_DB_PATH','AI_OS_JOBS_DB_PATH',
)

def s(name,state,detail,**extra):
    out={'name':name,'status':state,'detail':detail}; out.update(extra); return out

def sha(path):
    h=hashlib.sha256();
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def manifest():
    if not MANIFEST.exists(): return s('manifest','FAIL','release/manifest.json missing'),None
    try: d=json.loads(MANIFEST.read_text())
    except Exception as e: return s('manifest','FAIL',f'unreadable: {type(e).__name__}'),None
    if d.get('release')!='O40-v1.0.0': return s('manifest','FAIL',f'wrong release={d.get("release")!r}'),d
    return s('manifest','PASS','O40 manifest verified'),d

def env():
    if os.getenv('AI_OS_ENV','').lower() not in {'prod','production'}:
        return s('production_environment','FAIL','AI_OS_ENV must be production')
    missing=[n for n in REQUIRED_RUNTIME if not os.getenv(n)]
    if missing: return s('production_environment','FAIL','required variables missing',missing=missing)
    sec=os.getenv('AI_OS_IDENTITY_SIGNING_SECRET','')
    if len(sec.encode())<16 or sec in {'o36-local-development-only-secret','verification-secret-32-bytes-min','REPLACE_WITH_32_PLUS_BYTE_RANDOM_SECRET'}:
        return s('production_secret','FAIL','production identity signing secret is absent or unsafe')
    return s('production_environment','PASS','production environment configured; secret values not printed')

def static_deploy():
    checks=[]
    api=(ROOT/'deploy'/'o38-api.service.example').read_text()
    ng=(ROOT/'deploy'/'o38-nginx.example.conf').read_text()
    checks.append(s('loopback_api','PASS' if '--host 127.0.0.1' in api else 'FAIL','service binds API to loopback'))
    checks.append(s('tls_edge','PASS' if 'listen 443 ssl' in ng and 'proxy_pass http://127.0.0.1:8080' in ng else 'FAIL','TLS reverse proxy example present'))
    checks.append(s('public_8080_guard','PASS' if not re.search(r'0\.0\.0\.0:8080|listen\s+8080',ng,re.I) else 'FAIL','public app port is not exposed by nginx example'))
    return checks

def rollback_rehearsal():
    script=ROOT/'scripts'/'restore_verify.py'
    if not script.exists(): return s('rollback_rehearsal','FAIL','restore_verify.py missing')
    # Pure local rehearsal: create tiny sqlite DB, backup, restore, integrity-check.
    import sqlite3, shutil
    with tempfile.TemporaryDirectory() as td:
        td=Path(td); src=td/'source.sqlite3'; bak=td/'backup.sqlite3'; dst=td/'restore.sqlite3'
        con=sqlite3.connect(src); con.execute('create table t(k text primary key,v text)'); con.execute('insert into t values(?,?)',('release','O40')); con.commit(); con.close()
        try:
            import importlib.util
            mod_path = ROOT / 'scripts' / 'backup_sqlite.py'
            spec = importlib.util.spec_from_file_location('backup_sqlite_o40', mod_path)
            mod = importlib.util.module_from_spec(spec)
            assert spec and spec.loader
            spec.loader.exec_module(mod)
            mod.backup(src,bak); shutil.copy2(bak,dst)
            if not mod.verify(bak) or not mod.verify(dst): raise RuntimeError('integrity_check failed')
        except Exception as e:
            return s('rollback_rehearsal','FAIL',f'{type(e).__name__}: {e}')
    return s('rollback_rehearsal','PASS','isolated backup/restore rollback rehearsal passed')

def provider():
    req=['AI_OS_MODEL_BASE_URL','AI_OS_MODEL_API_KEY','AI_OS_MODEL_NAME','AI_OS_SEARCH_BASE_URL','AI_OS_SEARCH_API_KEY']
    if any(not os.getenv(x) for x in req): return s('staging_provider_smoke','MANUAL','live provider smoke requires staging credentials')
    script=ROOT/'scripts'/'staging_provider_smoke.py'
    p=subprocess.run([sys.executable,str(script)],cwd=ROOT,capture_output=True,text=True,timeout=90)
    safe='\n'.join(l for l in (p.stdout+'\n'+p.stderr).splitlines() if not any(k in l.lower() for k in ('api_key','authorization','secret','token')))
    return s('staging_provider_smoke','PASS' if p.returncode==0 and 'STAGING_PROVIDER_SMOKE_PASS' in safe else 'FAIL','staging model/search smoke',output_tail=safe[-1000:])

def target_evidence(path):
    required=['firewall_public_port.txt','tls_certificate.txt','backup_restore.txt','rollback_execution.txt']
    if path is None: return s('target_environment_evidence','MANUAL','supply --evidence-dir after performing target-environment checks',required=required)
    missing=[x for x in required if not (path/x).exists()]
    if missing: return s('target_environment_evidence','FAIL','required evidence files missing',missing=missing)
    return s('target_environment_evidence','PASS','target-environment evidence bundle present',files=required)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--skip-provider',action='store_true'); ap.add_argument('--evidence-dir',type=Path)
    a=ap.parse_args(); results=[]
    r,m=manifest(); results.append(r); results.append(env()); results.extend(static_deploy()); results.append(rollback_rehearsal())
    results.append(s('staging_provider_smoke','MANUAL','provider smoke skipped by operator') if a.skip_provider else provider())
    results.append(target_evidence(a.evidence_dir))
    failed=[x for x in results if x['status']=='FAIL']; manual=[x for x in results if x['status']=='MANUAL']
    overall='NOT_READY' if failed else ('CONDITIONAL' if manual else 'READY')
    report={'product':'AI Master OS','release':m.get('release') if m else None,'gate':'O40_FINAL_GO_LIVE','overall':overall,'results':results,'note':'MANUAL target-environment checks must be evidenced; this gate never guesses network, certificate, retention, or rollback execution state.'}
    print(json.dumps(report,indent=2,ensure_ascii=False))
    return 2 if overall=='NOT_READY' else 3 if overall=='CONDITIONAL' else 0
if __name__=='__main__': raise SystemExit(main())
