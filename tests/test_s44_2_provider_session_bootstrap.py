from __future__ import annotations
import importlib.util, os
from pathlib import Path

p=Path(__file__).resolve().parents[1]/'scripts'/'s44_provider_session_bootstrap.py'
s=importlib.util.spec_from_file_location('s44_bootstrap',p)
m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
assert all(name in m.REQUIRED for name in ['AI_OS_MODEL_BASE_URL','AI_OS_MODEL_API_KEY','AI_OS_MODEL_NAME','AI_OS_SEARCH_BASE_URL','AI_OS_SEARCH_API_KEY'])
print('S44_2_BOOTSTRAP_TEST_PASS')
