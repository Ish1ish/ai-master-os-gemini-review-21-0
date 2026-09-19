from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from pathlib import Path

from console_server import _build_adaptation_payload


def main() -> int:
    with tempfile.TemporaryDirectory(prefix='aios_ui_sai_') as td:
        db = Path(td) / 'strategy_feedback.sqlite3'
        con = sqlite3.connect(str(db))
        try:
            con.execute('CREATE TABLE strategy_feedback (feedback_id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
            base = {
                'project_id': 'demo',
                'analysis_id': 'SIA-DEMO',
                'selected_strategy_id': 'A',
                'outcome_quality': 'FULL_SUCCESS',
                'decision_quality': 'SOUND_DECISION',
                'attribution': 'DECISION',
                'evidence_sufficiency': 0.95,
                'sample_size': 6,
                'signal': 'POSITIVE_STRATEGY_SIGNAL',
                'advisory_route': 'MAINTAIN_STRATEGY',
                'confidence': 'high',
                'governance_authoritative': True,
                'external_action_executed': False,
                'o43_memory_mutated': False,
                'reasons': ['strategy_selection_supported'],
            }
            for idx in range(5):
                payload = dict(base, feedback_id=f'SFI-UI-{idx:02d}')
                con.execute(
                    'INSERT INTO strategy_feedback(feedback_id,payload) VALUES (?,?)',
                    (payload['feedback_id'], json.dumps(payload)),
                )
            con.commit()
        finally:
            con.close()

        os.environ['AI_OS_STRATEGY_FEEDBACK_DB'] = str(db)
        os.environ['AI_OS_PROJECT_ROOT'] = '/mnt/data/ui_work/patch20'
        result = _build_adaptation_payload({'project_id': ['demo'], 'strategy_id': ['A']})
        context = result.get('context', {}) if isinstance(result, dict) else {}
        checks = {
            'status_ok': result.get('status') == 'OK',
            'recommendation_maintain': context.get('recommendation') == 'MAINTAIN_STRATEGY',
            'confidence_high': context.get('confidence') == 'high',
            'evidence_sufficient': context.get('evidence_sufficiency') == 0.95,
            'no_external_action': context.get('external_action_executed') is False,
            'no_o43_mutation': context.get('o43_memory_mutated') is False,
            'governance_authoritative': context.get('governance_authoritative') is True,
        }
        if not all(checks.values()):
            raise SystemExit(f'UI ADAPTATION BRIDGE FAILED: {checks}\n{json.dumps(result, ensure_ascii=False, indent=2)}')
        print('STRATEGY ADAPTATION UI BRIDGE SMOKE PASS')
        print(json.dumps(context, ensure_ascii=False, indent=2))
        print('ALL UI ADAPTATION BRIDGE CHECKS PASSED.')
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
