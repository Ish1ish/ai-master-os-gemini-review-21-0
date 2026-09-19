import sys


def api_command():
    return [sys.executable, "-m", "src.cli", "health"]


def worker_smoke_command():
    # Controlled process that stays alive long enough for supervisor tests.
    return [sys.executable, "-c", "import time; time.sleep(30)"]
