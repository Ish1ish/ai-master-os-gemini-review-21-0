from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SECRET = "AI_OS_IDENTITY_SIGNING_SECRET"
ENV_MODE = "AI_OS_ENV"

def run_case(env_updates, expect_success: bool) -> bool:
    env = os.environ.copy()
    env.update(env_updates)
    cmd = [
        sys.executable,
        "-c",
        (
            "from core.src.identity import IdentityProvider;"
            "IdentityProvider();"
            "print('IDENTITY_INIT_OK')"
        ),
    ]
    p = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    ok = (p.returncode == 0)
    return ok is expect_success

def main() -> int:
    original_secret = os.environ.pop(SECRET, None)
    original_mode = os.environ.pop(ENV_MODE, None)
    try:
        if not run_case({ENV_MODE: "production"}, False):
            return 1

        if not run_case(
            {
                ENV_MODE: "production",
                SECRET: "S34_TEST_ONLY_SIGNING_SECRET_32_BYTES",
            },
            True,
        ):
            return 1

        if not run_case(
            {
                ENV_MODE: "staging",
                SECRET: "S34_TEST_ONLY_SIGNING_SECRET_32_BYTES",
            },
            True,
        ):
            return 1

        print("S34_IDENTITY_SECRET_CONTRACT_PASS")
        return 0
    finally:
        if original_secret is not None:
            os.environ[SECRET] = original_secret
        if original_mode is not None:
            os.environ[ENV_MODE] = original_mode

if __name__ == "__main__":
    raise SystemExit(main())
