import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class TestO39Operations(unittest.TestCase):
    def test_manifest_is_o39_and_has_freeze_metadata(self):
        data=json.loads((ROOT/'release'/'manifest.json').read_text(encoding='utf-8'))
        self.assertIn(data['release'], {'O39-v1.0.0','O40-v1.0.0'})
        self.assertEqual(data['o38_base_release'],'O38-v1.8.0')
        self.assertIn(data['decision'], {'PRODUCTION-OPERATIONS / WINDOWS-VERIFICATION-REQUIRED','FINAL RELEASE CANDIDATE / TARGET-ENVIRONMENT-EVIDENCE-REQUIRED'})

    def test_go_live_gate_is_manifest_driven(self):
        text=(ROOT/'scripts'/'go_live_gate.py').read_text(encoding='utf-8')
        self.assertNotIn('O38-v1.4.0', text)
        self.assertIn('manifest.json', text)

    def test_ops_snapshot_never_emits_secret_values(self):
        env=os.environ.copy()
        env.update({
            'AI_OS_ENV':'production',
            'AI_OS_MODEL_BASE_URL':'https://example.invalid/v1/chat',
            'AI_OS_MODEL_API_KEY':'SENTINEL_MODEL_SECRET',
            'AI_OS_MODEL_NAME':'test-model',
            'AI_OS_SEARCH_BASE_URL':'https://example.invalid/search',
            'AI_OS_SEARCH_API_KEY':'SENTINEL_SEARCH_SECRET',
            'AI_OS_IDENTITY_SIGNING_SECRET':'SENTINEL_SIGNING_SECRET_32_BYTES',
            'AI_OS_MEMORY_DB_PATH':str(ROOT/'data'/'memory.sqlite3'),
            'AI_OS_AUDIT_DB_PATH':str(ROOT/'data'/'audit.sqlite3'),
            'AI_OS_JOBS_DB_PATH':str(ROOT/'data'/'jobs.sqlite3'),
        })
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'snapshot.json'
            proc=subprocess.run([sys.executable,str(ROOT/'scripts'/'ops_snapshot.py'),'--api','http://127.0.0.1:9','--output',str(out)],cwd=ROOT,env=env,capture_output=True,text=True,check=True)
            combined=proc.stdout + out.read_text(encoding='utf-8')
            self.assertNotIn('SENTINEL_MODEL_SECRET',combined)
            self.assertNotIn('SENTINEL_SEARCH_SECRET',combined)
            self.assertNotIn('SENTINEL_SIGNING_SECRET_32_BYTES',combined)
            self.assertIn('"provider_calls": "NONE"',combined)
            self.assertIn('"secrets_printed": false',combined)

    def test_windows_o39_script_has_fail_closed_commands(self):
        text=(ROOT/'scripts'/'windows_verify_o39.cmd').read_text(encoding='utf-8')
        for marker in ['windows_offline_quality_verify_o38.cmd','compileall','ALL O39 WINDOWS VERIFICATION CHECKS PASSED.']:
            self.assertIn(marker,text)

if __name__ == '__main__':
    unittest.main()
