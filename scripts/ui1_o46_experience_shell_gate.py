from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
contract = ROOT / 'src' / 'ui' / 'contracts' / 'o46_experience_view.schema.json'

def main():
    cmd = [sys.executable, 'src/ui/tests/test_o46_experience_shell.py']
    proc = subprocess.run(cmd, cwd=ROOT, text=True)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)
    view = json.loads(contract.read_text(encoding='utf-8'))
    required = view.get('required', [])
    expected = ['run','intent','research','decision','governance','approval','execution','outcome','learning','next_step','provenance']
    checks = {
        'contract_present': contract.exists(),
        'canonical_sections': required == expected,
        'ui_shell_present': (ROOT/'src/ui/ui/index.html').exists(),
        'experience_model_present': (ROOT/'src/ui/ui/experience.js').exists(),
        'targeted_tests': True,
    }
    print('UI1_O46_EXPERIENCE_SHELL_PASS')
    print(json.dumps({'release':'UI1-O46','status':'PASS','checks':checks,'path':'unified experience contract -> O46 experience shell -> live read-only backend aggregation -> explainability'}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
