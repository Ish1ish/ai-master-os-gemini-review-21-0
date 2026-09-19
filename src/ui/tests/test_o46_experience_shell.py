import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / 'ui'
CONTRACT = ROOT / 'contracts' / 'o46_experience_view.schema.json'
APP = UI / 'app.js'
HTML = UI / 'index.html'
CSS = UI / 'styles.css'
EX = UI / 'experience.js'

class TestO46ExperienceShell(unittest.TestCase):
    def test_contract_has_canonical_sections(self):
        data=json.loads(CONTRACT.read_text(encoding='utf-8'))
        for key in ['run','intent','research','decision','governance','approval','execution','outcome','learning','next_step','provenance']:
            self.assertIn(key,data['properties'])
    def test_experience_builder_exists(self):
        text=EX.read_text(encoding='utf-8')
        self.assertIn('buildO46ExperienceView',text)
        self.assertIn('window.buildO46ExperienceView',text)
    def test_shell_in_overview(self):
        text=HTML.read_text(encoding='utf-8')
        for token in ['o46ExperienceShell','experienceJourneyRail','experienceDecisionTitle','experienceGovernanceTitle','experienceOutcomeTitle']:
            self.assertIn(token,text)
    def test_experience_script_loaded(self):
        self.assertIn('experience.js?v=1.0.0',HTML.read_text(encoding='utf-8'))
    def test_backend_run_endpoint_used(self):
        text=APP.read_text(encoding='utf-8')
        self.assertIn("api('/runs?limit=10')",text)
        self.assertIn('api(`/runs/${encodeURIComponent(best.job_id)}`)',text)
    def test_learning_endpoint_used(self):
        self.assertIn('/learning/context?project_id=',APP.read_text(encoding='utf-8'))
    def test_experiment_endpoint_used(self):
        self.assertIn("api('/experiments')",APP.read_text(encoding='utf-8'))
    def test_approval_endpoint_indexed(self):
        self.assertIn("api('/approvals')",APP.read_text(encoding='utf-8'))
    def test_no_external_execution_added(self):
        text=APP.read_text(encoding='utf-8')
        start=text.find('async function refreshO46Experience()')
        end=text.find('\n/* O46 UI-1 boundary: experience read-only refresh ends here. */', start)
        block=text[start:end]
        self.assertNotIn("/execute",block)
        self.assertNotIn("/send",block)
        self.assertNotIn("/publish",block)
    def test_explainability_trace_present(self):
        text=HTML.read_text(encoding='utf-8')
        for token in ['experienceTraceChips','experienceExplainBtn','experienceJson']:
            self.assertIn(token,text)
    def test_responsive_rules_present(self):
        text=CSS.read_text(encoding='utf-8')
        self.assertIn('.experience-grid',text)
        self.assertIn('@media(max-width:1080px)',text)
    def test_visual_story_has_journey_stage_labels(self):
        text=APP.read_text(encoding='utf-8')
        for token in ["['intent','Intent'","['research','Research'","['decision','Decision'","['governance','Governance'","['learning','Learning'"]:
            self.assertIn(token,text)
    def test_contract_is_not_chat_dump(self):
        data=json.loads(CONTRACT.read_text(encoding='utf-8'))
        self.assertNotIn('raw_transcript',data['properties'])
    def test_build_identifier(self):
        self.assertIn("O46_EXPERIENCE_BUILD = '1.0.0'",EX.read_text(encoding='utf-8'))
    def test_ui_has_graceful_backend_fallback(self):
        text=APP.read_text(encoding='utf-8')
        self.assertIn("'Waiting for a run'",text)
        self.assertIn('Unavailable',text)

if __name__ == '__main__':
    unittest.main()
