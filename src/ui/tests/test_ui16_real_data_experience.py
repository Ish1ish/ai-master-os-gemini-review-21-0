import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
UI = ROOT / 'src' / 'ui' / 'ui'
INDEX = UI / 'index.html'
JS = UI / 'ux16_experience.js'

class TestUI16RealDataExperience(unittest.TestCase):
    def setUp(self):
        self.index = INDEX.read_text(encoding='utf-8')
        self.js = JS.read_text(encoding='utf-8')

    def test_experience_loader_is_present(self):
        self.assertIn('ux16_experience.js', self.index)

    def test_latest_run_is_timestamp_sorted(self):
        self.assertIn("sort((a,b)", self.js)
        self.assertIn('updated_at', self.js)
        self.assertIn('created_at', self.js)

    def test_existing_experience_ids_are_bound(self):
        for token in (
            'experienceSource','executiveRecommendation','executiveConfidence',
            'executiveOpportunity','executiveStrategy','executiveEvidenceCount',
            'executiveSourceCount','executiveGovernanceState','executiveNextAction',
            'experienceDecisionTitle','experienceEvidenceList','experienceGovernanceStatus',
            'experienceOutcomeTitle','experienceLearningSignal','experienceNextDecision'
        ):
            self.assertIn(token, self.js)

    def test_semantic_fields_remain_distinct(self):
        for token in ('customer','validation','longTerm','mvp','firstTest','threshold','rule'):
            self.assertIn(token, self.js)

    def test_backend_authority_is_preserved(self):
        self.assertIn('backend remains authoritative', self.js)
        self.assertNotIn('method:\'POST\'', self.js)
        self.assertNotIn('method: "POST"', self.js)

    def test_no_secret_rendering(self):
        for token in ('apiKey','tokenValue','secretValue'):
            self.assertNotIn(token, self.js)

    def test_loading_safe_error_copy_exists(self):
        self.assertIn('data unavailable', self.js)
        self.assertIn('could not be hydrated safely', self.js)

    def test_refresh_control_is_bound(self):
        self.assertIn('experienceRefresh', self.js)
        self.assertIn('ui16Bound', self.js)

if __name__ == '__main__':
    unittest.main()
