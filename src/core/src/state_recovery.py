from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class BackupRecord:
    name: str
    source: str
    backup: str
    sha256: str
    size: int


@dataclass(frozen=True)
class RestoreReport:
    restored: List[str]
    hashes_match: bool
    files_present: bool


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sqlite_checkpoint(path: str | Path) -> None:
    """Best-effort checkpoint for a live SQLite DB before file-level backup."""
    p = str(path)
    if not os.path.isfile(p):
        raise FileNotFoundError(p)
    conn = sqlite3.connect(p, timeout=10)
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.commit()
    finally:
        conn.close()


def backup_sqlite_files(source_dir: str | Path, backup_dir: str | Path, names: Iterable[str]) -> List[BackupRecord]:
    source = Path(source_dir)
    backup = Path(backup_dir)
    backup.mkdir(parents=True, exist_ok=True)
    records: List[BackupRecord] = []
    for name in names:
        src = source / name
        if not src.is_file():
            raise FileNotFoundError(str(src))
        sqlite_checkpoint(src)
        dst = backup / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_suffix(dst.suffix + ".tmp")
        shutil.copy2(src, tmp)
        os.replace(tmp, dst)
        records.append(BackupRecord(name=name, source=str(src), backup=str(dst), sha256=sha256_file(dst), size=dst.stat().st_size))
    manifest = {
        "version": "S40-v1",
        "records": [r.__dict__ for r in records],
    }
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return records


def restore_sqlite_files(backup_dir: str | Path, target_dir: str | Path, names: Iterable[str]) -> RestoreReport:
    backup = Path(backup_dir)
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    restored: List[str] = []
    files_present = True
    hashes_match = True
    manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    expected = {r["name"]: r for r in manifest.get("records", [])}
    for name in names:
        src = backup / name
        dst = target / name
        if not src.is_file():
            files_present = False
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_suffix(dst.suffix + ".restore_tmp")
        shutil.copy2(src, tmp)
        os.replace(tmp, dst)
        restored.append(name)
        if expected.get(name, {}).get("sha256") != sha256_file(dst):
            hashes_match = False
    return RestoreReport(restored=restored, hashes_match=hashes_match, files_present=files_present)


def snapshot_and_restore_roundtrip(source_dir: str | Path, work_dir: str | Path, names: Iterable[str]) -> Dict[str, object]:
    names = list(names)
    source = Path(source_dir)
    work = Path(work_dir)
    backup = work / "backup"
    restored = work / "restored"
    if work.exists():
        shutil.rmtree(work)
    restored.mkdir(parents=True)
    records = backup_sqlite_files(source, backup, names)
    # Delete the restored target files if any, then restore from backup.
    report = restore_sqlite_files(backup, restored, names)
    return {
        "status": "PASS" if report.files_present and report.hashes_match and len(report.restored) == len(names) else "FAIL",
        "backup_count": len(records),
        "restored_count": len(report.restored),
        "hashes_match": report.hashes_match,
        "files_present": report.files_present,
        "manifest": str(backup / "manifest.json"),
    }
