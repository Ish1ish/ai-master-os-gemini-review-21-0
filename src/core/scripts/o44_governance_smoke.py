import os
import tempfile
from src.governance_intelligence import GovernanceIntelligence


def main():
    with tempfile.TemporaryDirectory() as td:
        g = GovernanceIntelligence(os.path.join(td, 'governance.sqlite3'))
        base = {
            'confidence': 'high',
            'evidence_refs': ['SRC-001', 'SRC-002'],
            'evidence_boundary': 'local_evidence_supported',
        }
        low = g.evaluate('PROJ-O44', 'read_only_inspection', base, run_id='RUN-O44-LOW', requested_by='operator-01', create_approval=False)
        high = g.evaluate('PROJ-O44', 'publish_public_content', base, run_id='RUN-O44-HIGH', requested_by='operator-01', create_approval=True)
        assert low['decision'] == 'AUTO_ALLOW' and low['execution_allowed'] is True
        assert high['decision'] == 'REVIEW' and high['approval_required'] is True and high['approval_id']
        denied = g.decide(high['approval_id'], {'principal_id': 'operator-01', 'roles': ['operator']}, 'APPROVED', 'not allowed')
        assert denied['status'] == 'DENY'
        approved = g.decide(high['approval_id'], {'principal_id': 'approver-01', 'roles': ['approver']}, 'APPROVED', 'reviewed')
        assert approved['status'] == 'APPROVED'
        saved = g.get(high['decision_id'])
        assert saved['decision'] == 'REVIEW'
        print({'status':'PASS','low_risk':'AUTO_ALLOW','high_risk':'REVIEW','approval':'APPROVED','decision_id':high['decision_id']})
        g.close()


if __name__ == '__main__':
    main()
