import argparse
import shutil
import sqlite3
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("backup")
    ap.add_argument("restore_target")
    args = ap.parse_args()
    backup = Path(args.backup); target = Path(args.restore_target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup, target)
    conn = sqlite3.connect(target)
    try:
        row = conn.execute("PRAGMA integrity_check").fetchone()
        ok = bool(row and row[0] == "ok")
    finally:
        conn.close()
    if not ok:
        raise SystemExit("restore integrity check failed")
    print(f"RESTORE_VERIFY_OK {target}")


if __name__ == "__main__":
    main()
