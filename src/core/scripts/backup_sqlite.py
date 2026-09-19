import argparse
import sqlite3
from pathlib import Path


def backup(src, dst):
    src = Path(src); dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(src)
    cursor = None
    try:
        cursor = conn.execute("PRAGMA wal_checkpoint(FULL)")
        cursor.fetchall()
        cursor.close()
        cursor = conn.execute("VACUUM INTO ?", (str(dst),))
        cursor.fetchall()
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        conn.close()
    return dst


def verify(path):
    conn = sqlite3.connect(path)
    cursor = None
    try:
        cursor = conn.execute("PRAGMA integrity_check")
        row = cursor.fetchone()
        return bool(row and row[0] == "ok")
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        conn.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("destination")
    args = ap.parse_args()
    out = backup(args.source, args.destination)
    if not verify(out):
        raise SystemExit("backup integrity check failed")
    print(f"BACKUP_OK {out}")


if __name__ == "__main__":
    main()
