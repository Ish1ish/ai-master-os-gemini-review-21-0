import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class TestO40FinalRelease(unittest.TestCase):
    def test_manifest_is_o40(self):
        d=json.loads((ROOT/'release'/'manifest.json').read_text())
        self.assertEqual(d['release'],'O40-v1.0.0')
        self.assertEqual(d['o39_base_release'],'O39-v1.0.0')
    def test_final_gate_is_fail_closed_and_manifest_driven(self):
        t=(ROOT/'scripts'/'final_release_gate.py').read_text()
        self.assertIn("O40-v1.0.0",t)
        self.assertIn("overall='NOT_READY' if failed",t)
        self.assertIn('--evidence-dir',t)
    def test_windows_final_gate_markers(self):
        t=(ROOT/'scripts'/'windows_final_release_gate.cmd').read_text()
        self.assertIn('ALL O40 WINDOWS FINAL RELEASE CHECKS PASSED.',t)
        self.assertIn('windows_offline_quality_verify_o38.cmd',t)
    def test_checklist_mentions_target_evidence(self):
        t=(ROOT/'docs'/'FINAL_RELEASE_CHECKLIST.md').read_text()
        for x in ['firewall_public_port.txt','tls_certificate.txt','backup_restore.txt','rollback_execution.txt']:
            self.assertIn(x,t)
    def test_final_gate_local_skip_is_conditional_not_ready(self):
        env=os.environ.copy(); env['AI_OS_ENV']='production'
        env.update({
            'AI_OS_MODEL_BASE_URL':'https://example.invalid/model','AI_OS_MODEL_API_KEY':'x','AI_OS_MODEL_NAME':'x',
            'AI_OS_SEARCH_BASE_URL':'https://example.invalid/search','AI_OS_SEARCH_API_KEY':'x',
            'AI_OS_IDENTITY_SIGNING_SECRET':'0123456789abcdef0123456789abcdef',
            'AI_OS_MEMORY_DB_PATH':str(ROOT/'data/memory.sqlite3'),'AI_OS_AUDIT_DB_PATH':str(ROOT/'data/audit.sqlite3'),'AI_OS_JOBS_DB_PATH':str(ROOT/'data/jobs.sqlite3')})
        p=subprocess.run([sys.executable,str(ROOT/'scripts'/'final_release_gate.py'),'--skip-provider'],cwd=ROOT,env=env,capture_output=True,text=True)
        self.assertEqual(p.returncode,3)
        self.assertIn('CONDITIONAL',p.stdout)
if __name__=='__main__': unittest.main()
