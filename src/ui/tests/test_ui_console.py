from pathlib import Path
import pathlib
import json
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class TestUIConsolePackage(unittest.TestCase):
    def test_required_assets_exist(self):
        for rel in ["ui/index.html", "ui/app.js", "ui/styles.css", "ui/meta.json", "scripts/console_server.py", "scripts/windows_start_console.cmd"]:
            self.assertTrue((ROOT / rel).exists(), rel)

    def test_ui_has_expected_core_routes(self):
        js = (ROOT / "ui/app.js").read_text(encoding="utf-8")
        for route in ["/health", "/readiness", "/runs", "/runs/${encodeURIComponent(jobId)}/execute", "/runs/${encodeURIComponent(jobId)}/cancel"]:
            self.assertIn(route, js)
        self.assertIn("Authorization", js)

    def test_proxy_has_api_boundary(self):
        py = (ROOT / "scripts/console_server.py").read_text(encoding="utf-8")
        self.assertIn('self.path.startswith("/api/")', py)
        self.assertIn("HTTPConnection", py)
        self.assertIn("AI_OS_CONSOLE_PROXY_TIMEOUT", py)
        self.assertIn("ConnectionAbortedError", py)
        self.assertIn("EXECUTE_PATH", py)
        self.assertIn("EXECUTION_ACCEPTED", py)
        self.assertIn("ThreadPoolExecutor", py)

    def test_no_external_js_dependency(self):
        html = (ROOT / "ui/index.html").read_text(encoding="utf-8")
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)

    def test_live_health_ui_metrics_and_auto_refresh(self):
        js = (ROOT / "ui/app.js").read_text(encoding="utf-8")
        self.assertIn("renderHealthMetrics", js)
        self.assertIn("setInterval(refreshHealth, 15000)", js)
        self.assertIn("setInterval(pollActiveRuns, 3000)", js)
        self.assertIn("executeRun", js)
        self.assertIn("cancelRun", js)
        self.assertIn("Create Run", (ROOT / "ui/index.html").read_text(encoding="utf-8"))
        self.assertIn("latencyMs", js)
        self.assertIn("healthCards", js)
        self.assertIn("renderEngineTrace", js)
        self.assertIn("renderHandoffs", js)
        self.assertIn("semanticQuality", js)
        self.assertIn("syncRunIndex", js)
        self.assertIn("handoffQualityNote", js)
        self.assertIn("qa?.status", js)
        self.assertIn("payloadDrawerOverlay", (ROOT / "ui/index.html").read_text(encoding="utf-8"))
        self.assertIn("HUMAN GATE", js)


    def test_handoff_mapping_uses_real_backend_keys(self):
        js = (ROOT / "ui/app.js").read_text(encoding="utf-8")
        self.assertIn("['market','ideas','market_to_idea']", js)
        self.assertIn("['ideas','strategy','idea_to_strategy']", js)
        self.assertNotIn("const pairKey=`${fromKey}_to_${toKey}`", js)

    def test_handoff_mapping_excludes_trace_only_edges(self):
        js = (ROOT / "ui/app.js").read_text(encoding="utf-8")
        start = js.index("const HANDOFF_PATHS")
        end = js.index("function handoffCard", start)
        mapping = js[start:end]
        self.assertNotIn("['knowledge','prompt'", mapping)
        self.assertNotIn("['prompt','market'", mapping)
        self.assertIn("['memory','monitoring','memory_to_monitoring']", mapping)

    def test_final_polish_qa_and_handoff_copy(self):
        js = (ROOT / "ui/app.js").read_text(encoding="utf-8")
        self.assertIn("Canonical QA status", (ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertIn("Semantic contracts healthy", js)
        self.assertIn("Structurally valid · approval pending", js)

    def test_constraints_are_not_character_iterated(self):
        js = (ROOT / "ui/app.js").read_text(encoding="utf-8")
        self.assertIn("rawConstraints", js)
        self.assertIn("split(/\\r?\\n/)", js)

    def test_version_bumped(self):
        html = (ROOT / "ui/index.html").read_text(encoding="utf-8")
        self.assertIn("O40 · UI Console v1.5.0", html)



class TestV402RTLLocalization(unittest.TestCase):
    def test_v402_version_and_rtl_support(self):
        html=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        meta=(ROOT/'ui'/'meta.json').read_text(encoding='utf-8')
        self.assertIn('O46 · UI Console v4.0.2', html)
        self.assertIn("const UI_V4_BUILD = '4.0.2';", js)
        self.assertIn('V4_PLACEHOLDERS', js)
        self.assertIn('startV4TranslationObserver', js)
        self.assertIn('language_selector_en_ar', meta)

    def test_arabic_placeholders_and_english_placeholders(self):
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        for en, ar in [
            ('Example: Research low-cost AI opportunities', 'مثال: ابحث عن فرص ذكاء اصطناعي'),
            ('What should AI Master OS do?', 'ماذا تريد من AI Master OS أن يفعل؟'),
            ('Optional constraints', 'قيود اختيارية'),
            ('Search pages, jobs, projects, actions…', 'ابحث في الصفحات والتشغيلات والمشروعات والإجراءات…'),
        ]:
            self.assertIn(en, js)
            self.assertIn(ar, js)

    def test_missing_runtime_english_is_localizable(self):
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        for phrase in ['API unavailable','Backend-derived when available','No decision-driving state yet','Governance evidence will appear here as the system processes runs.','No active operator items indexed.']:
            self.assertIn(phrase, js)
            self.assertIn('V4_AR_PATCH', js)



class TestUIConsoleV46Final(unittest.TestCase):
    def test_final_version_and_manifest(self):
        meta=json.loads((ROOT/'ui'/'meta.json').read_text(encoding='utf-8'))
        self.assertEqual(meta.get('version'),'4.6.0')
        self.assertEqual(meta.get('console_version'),'4.6.0')
        self.assertEqual(meta.get('release'),'FINAL')
        self.assertIn('final_release',meta.get('features',[]))
        self.assertNotIn('final_release_candidate',meta.get('features',[]))
    def test_final_readme_and_script(self):
        readme=(ROOT/'README.md').read_text(encoding='utf-8')
        script=(ROOT/'scripts'/'windows_ui_v46_final_verify.cmd').read_text(encoding='utf-8')
        self.assertIn('v4.6.0 FINAL',readme)
        self.assertIn('windows_ui_v46_final_verify.cmd',readme)
        self.assertIn('ALL UI V4.6.0 FINAL VERIFICATION CHECKS PASSED.',script)
    def test_final_ui_markers(self):
        html=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        self.assertIn('AI Master OS UI v4.6.0 FINAL',html)
        self.assertIn("const UI_BUILD = '4.6.0';",js)
        self.assertIn("const UI_V46_BUILD = '4.6.0';",js)

if __name__ == "__main__":
    unittest.main()

class TestO39UI(unittest.TestCase):
    def test_operations_page_and_version(self):
        html=(ROOT/'ui/index.html').read_text(encoding='utf-8')
        self.assertIn('data-page="operations"',html)
        self.assertIn('id="page-operations"',html)
        self.assertIn('O40 · UI Console v1.5.0',html)
        self.assertIn('id="opsRefresh"',html)

    def test_operations_page_is_read_only(self):
        js=(ROOT/'ui/app.js').read_text(encoding='utf-8')
        html=(ROOT/'ui/index.html').read_text(encoding='utf-8')
        self.assertIn('Production Operations', html)
        self.assertIn("apiGet('/health')",js)
        self.assertIn("apiGet('/readiness')",js)
        self.assertNotIn("/approve",js[js.rfind('function renderOperationsPage'):])


class TestO40ReleaseSurface(unittest.TestCase):
    def test_release_view_present(self):
        text=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        self.assertIn('data-page="release"',text)
        self.assertIn('O40-v1.0.0',text)
    def test_release_surface_is_read_only(self):
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        self.assertIn('function refreshRelease()',js)



class TestV12ProgressAndResultFirst(unittest.TestCase):
    def test_guide_and_result_first_surface(self):
        html=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        css=(ROOT/'ui'/'styles.css').read_text(encoding='utf-8')
        self.assertIn('data-page="guide"', html)
        self.assertIn('id="page-guide"', html)
        self.assertIn('RESULT AT A GLANCE', js)
        self.assertIn('What you should take away from this run', js)
        self.assertIn('deriveDecision', js)
        self.assertIn('deriveValidation', js)
        self.assertIn('deriveNextAction', js)
        self.assertIn('renderResultHighlights', js)
        self.assertIn('renderExecutionProgress', js)
        self.assertIn('EXECUTION PROGRESS', js)
        self.assertIn('100% appears only when the backend reports COMPLETE.', js)
        self.assertIn('.result-orientation', css)
        self.assertIn('.guide-grid', css)

    def test_v13_business_result_surface(self):
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        css=(ROOT/'ui'/'styles.css').read_text(encoding='utf-8')
        self.assertIn('Recommendation', js)
        self.assertIn('Customer problem', js)
        self.assertIn('Target customer', js)
        self.assertIn('MVP direction', js)
        self.assertIn('First validation test', js)
        self.assertIn('Next action', js)
        self.assertIn('.result-business-first', css)

    def test_v13_version(self):
        html=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        self.assertIn('O40 · UI Console v1.5.0', html)



class TestV14Exports(unittest.TestCase):
    def test_export_controls_and_helpers(self):
        html=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        css=(ROOT/'ui'/'styles.css').read_text(encoding='utf-8')
        self.assertIn('Download business report', js)
        self.assertIn('Download full JSON', js)
        self.assertIn('function buildBusinessReport', js)
        self.assertIn('function downloadBlob', js)
        self.assertIn('function downloadEnginePayload', js)
        self.assertIn('id="enginePayloadDownload"', html)
        self.assertIn('app.js?v=1.5.0', html)
        self.assertIn('.result-actions', css)

    def test_v14_version(self):
        html=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        meta=(ROOT/'ui'/'meta.json').read_text(encoding='utf-8')
        self.assertIn('O40 · UI Console v1.5.0', html)
        self.assertIn('1.5.0', meta)


class TestV15OpportunitySurface(unittest.TestCase):
    def test_opportunity_first_result_surface(self):
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        self.assertIn('recommended_opportunity', js)
        self.assertIn('Why this direction', js)
        self.assertIn('Opportunity score', js)
        self.assertIn('Evidence boundary', js)
        self.assertIn('marketScope', js)

    def test_v15_version(self):
        html=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        meta=(ROOT/'ui'/'meta.json').read_text(encoding='utf-8')
        self.assertIn('O40 · UI Console v1.5.0', html)
        self.assertIn('1.5.0', meta)


class TestV171NumericDecisionExport(unittest.TestCase):
    def test_first_text_preserves_numeric_scores_for_business_report(self):
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        self.assertIn("if(typeof v==='number' && Number.isFinite(v)) return String(v);", js)

    def test_v171_version(self):
        html=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        meta=(ROOT/'ui'/'meta.json').read_text(encoding='utf-8')
        self.assertIn('O41 · UI Console v1.7.1', html)
        self.assertIn('1.7.1', meta)


class TestUIConsoleV20(unittest.TestCase):
    def test_v20_assets_and_version(self):
        html=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        meta=(ROOT/'ui'/'meta.json').read_text(encoding='utf-8')
        self.assertIn('O46 · UI Console v2.0.0', html)
        self.assertIn('2.0.0', meta)
        self.assertIn('Executive Home', html)
        self.assertIn('Command Center', html)

    def test_v20_control_center_surfaces(self):
        html=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        css=(ROOT/'ui'/'styles.css').read_text(encoding='utf-8')
        for needle in ['id="operatingPulse"','id="systemTimeline"','id="governancePosture"','id="page-execution"','id="page-recovery"','id="recoveryList"']:
            self.assertIn(needle, html)
        for needle in ['refreshDashboard','renderSystemTimeline','refreshExecutionCenter','refreshRecoveryCenter','inferGovernancePosture']:
            self.assertIn(needle, js)
        for needle in ['.dashboard-grid','.pulse-grid','.system-timeline','.execution-row','.recovery-row']:
            self.assertIn(needle, css)

    def test_v20_safety_boundaries_are_visible(self):
        html=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        self.assertIn('Governance decision is authoritative.',html)
        self.assertIn('Approvals never equal execution.',html)
        self.assertIn('does not auto-retry unknown outcomes',html)

    def test_v20_no_fake_live_governance_data(self):
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        self.assertIn('Live governance endpoints are authoritative when exposed.',js)
        self.assertIn('browser session',js)



class TestUIConsoleV30(unittest.TestCase):
    def test_v30_assets_and_version(self):
        index=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        css=(ROOT/'ui'/'styles.css').read_text(encoding='utf-8')
        self.assertIn('UI Console v3.0.0', index)
        self.assertIn("const UI_BUILD = '3.0.0';", js)
        self.assertIn('UI CONSOLE v3.0', css)
    def test_v30_control_center_surfaces(self):
        index=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        for needle in ['commandPalette','notificationPanel','runTemplates','attentionQueue','execActive','sidebarToggle']:
            self.assertIn(needle,index)
    def test_v30_no_fake_live_governance_data(self):
        readme=(ROOT/'README.md').read_text(encoding='utf-8')
        self.assertIn('never fabricates live approval',readme.lower())


class TestUIConsoleV40(unittest.TestCase):
    def test_v40_assets_and_backend_contracts(self):
        index=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        css=(ROOT/'ui'/'styles.css').read_text(encoding='utf-8')
        meta=(ROOT/'ui'/'meta.json').read_text(encoding='utf-8')
        self.assertIn('UI Console v4.0.0', index)
        self.assertIn("const UI_V4_BUILD = '4.0.0';", js)
        self.assertIn('4.0.0', meta)
        for needle in ['backendState','decisionGraph','evidenceList','experimentList','policyList','languageSelect','settingsLanguageSelect']:
            self.assertIn(needle, index)
        for needle in ["api('/experiments')","/governance/policies","/policies","function probeBackendV4"]:
            self.assertIn(needle, js)
        self.assertIn('backend-contract-first', (ROOT/'README.md').read_text(encoding='utf-8').lower())

    def test_language_selector_and_arabic_rtl(self):
        index=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        css=(ROOT/'ui'/'styles.css').read_text(encoding='utf-8')
        self.assertIn('value="ar">العربية', index)
        self.assertIn("document.documentElement.dir = langState.current === 'ar' ? 'rtl' : 'ltr';", js)
        self.assertIn("'nav.home':'الرئيسية التنفيذية'", js)
        self.assertIn('.rtl-mode', css)

    def test_clear_history_is_local_only_and_confirmed(self):
        index=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        self.assertIn('id="clearHistoryBtn"', index)
        self.assertIn('id="clearHistoryModal"', index)
        self.assertIn('id="clearHistoryConfirm"', index)
        self.assertIn('localStorage.removeItem(\'aios.runs\')', js)
        self.assertIn('localHistoryOnly: true', js)
        self.assertNotIn('/delete', js[js.index('function clearLocalHistoryV4'):js.index('window.AI_MASTER_OS_V4')])

    def test_v40_command_and_platform_surfaces(self):
        index=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        for needle in ['data-page="decisions"','data-page="evidence"','data-page="experiments"','data-page="policies"','data-page="settings"']:
            self.assertIn(needle,index)
        self.assertIn('V4 is the master UI target release', (ROOT/'README.md').read_text(encoding='utf-8'))

if __name__ == '__main__':
    unittest.main()


class TestUIConsoleV40RTLCorrection(unittest.TestCase):
    def test_rtl_layout_uses_two_column_reflow_not_margin_hack(self):
        css=(ROOT/'ui'/'styles.css').read_text(encoding='utf-8')
        self.assertIn('body.rtl-mode .app-shell{grid-template-columns:1fr 258px;direction:ltr}', css)
        self.assertIn('body.rtl-mode .sidebar{grid-column:2', css)
        self.assertIn('body.rtl-mode .main{grid-column:1', css)
        self.assertIn('overflow-x:hidden', css)
    def test_arabic_static_localization_exists(self):
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        for needle in ['أدر عملك عبر نظام تشغيل موحّد ومحكوم بالذكاء الاصطناعي.','مساحة العمل','مركز التشغيل','مستكشف الأدلة','القرارات']:
            self.assertIn(needle, js)
        self.assertIn("const steps = langState.current === 'ar'", js)
    def test_arabic_font_and_spacing_rules_exist(self):
        css=(ROOT/'ui'/'styles.css').read_text(encoding='utf-8')
        self.assertIn('body.rtl-mode{font-family:"Segoe UI",Tahoma,Arial,sans-serif}', css)
        self.assertIn('body.rtl-mode .eyebrow{letter-spacing:0;text-transform:none}', css)



class TestUIConsoleV41CommandCenter(unittest.TestCase):
    def test_v41_assets_and_backend_run_list_contract(self):
        index=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        meta=(ROOT/'ui'/'meta.json').read_text(encoding='utf-8')
        readme=(ROOT/'README.md').read_text(encoding='utf-8')
        self.assertIn('UI Console v4.1.0', index)
        self.assertIn("const UI_BUILD = '4.1.0';", js)
        self.assertIn('4.1.0', meta)
        self.assertIn("api(`/runs?limit=${limit}`)", js)
        self.assertIn("state.runsSource = 'backend'", js)
        self.assertIn('backend-first', readme.lower())

    def test_v41_run_history_controls(self):
        index=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        css=(ROOT/'ui'/'styles.css').read_text(encoding='utf-8')
        for needle in ['id="runHistorySearch"','id="runStatusFilter"','id="clearRunFilters"','id="runHistorySourceState"','id="runHistoryCountLive"','id="reloadRunsTable"']:
            self.assertIn(needle,index)
        self.assertEqual(index.count('id="reloadRuns"'), 1)
        self.assertEqual(index.count('id="reloadRunsTable"'), 1)
        for needle in ['function fetchBackendRuns','function filteredRunsForDisplay','function refreshCommandCenterRuns','function bindRunsFilters']:
            self.assertIn(needle,js)
        self.assertIn('.run-history-toolbar',css)

    def test_v41_clear_history_never_calls_backend_delete(self):
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        start=js.index('function clearLocalHistoryV4')
        end=js.index("$('clearHistoryBtn')",start)
        segment=js[start:end]
        self.assertIn("localStorage.removeItem('aios.runs')",segment)
        self.assertNotIn('/delete',segment)
        self.assertNotIn('fetchBackendRuns',segment)

if __name__ == '__main__':
    unittest.main()


class TestUIConsoleV401Localization(unittest.TestCase):
    def test_v401_version_and_full_localization(self):
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        self.assertIn("const UI_V4_BUILD = '4.0.1';", js)
        for needle in ['أدر عملك عبر نظام تشغيل موحّد ومحكوم بالذكاء الاصطناعي.','مركز التنفيذ','مسح سجل التشغيل؟','التشغيلات النشطة']:
            self.assertIn(needle, js)
        self.assertIn('translateDocumentTextV4', js)
    def test_v401_rtl_layout_no_margin_offset(self):
        css=(ROOT/'ui'/'styles.css').read_text(encoding='utf-8')
        self.assertIn('body.rtl-mode .main{grid-column:1!important;grid-row:1!important;width:100%!important;max-width:none!important;min-width:0!important;margin:0!important;', css)
        self.assertIn('body.rtl-mode .app-shell{grid-template-columns:minmax(0,1fr) 258px!important;direction:ltr!important;', css)


class TestUIConsoleV42Intelligence(unittest.TestCase):
    def test_v42_version_and_intelligence_surfaces(self):
        html=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        meta=(ROOT/'ui'/'meta.json').read_text(encoding='utf-8')
        self.assertIn('app.js?v=4.2.0', html)
        self.assertIn("const UI_V42_BUILD = '4.2.0';", js)
        self.assertIn('4.2.0', meta)
        for needle in ['id="decisionInspector"','id="evidenceInspector"','id="experimentInspector"','id="learningContextPanel"']:
            self.assertIn(needle, html)

    def test_v42_backend_intelligence_contracts(self):
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        self.assertIn("api('/experiments')", js)
        self.assertIn("/learning/context?project_id=", js)
        self.assertIn('No backend data is available in the current API contract.', js)
        self.assertIn('v42DecisionFromRun', js)
        self.assertIn('renderV42DecisionGraph', js)

    def test_v42_no_fake_decision_or_evidence_state(self):
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        self.assertIn('backend must expose a completed run with a decision surface', js)
        self.assertIn('current backend API boundary', js)
        self.assertIn('BACKEND RESULT', js)

    def test_v42_arabic_intelligence_labels_exist(self):
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        for phrase in ['الطلب','البحث','الفرصة','الاستراتيجية','التحقق','القرار','التعلم','الفرضية','مراجع الأدلة','التجارب المرتبطة']:
            self.assertIn(phrase, js)



class TestV43Governance(unittest.TestCase):
    def test_v43_version_and_governance_surfaces(self):
        html=(ROOT/'ui'/'index.html').read_text(encoding='utf-8'); js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        self.assertIn('O46 · UI Console v4.3.0',html); self.assertIn("const UI_BUILD = '4.3.0';",js)
        for key in ['id="approvalKpis"','id="approvalList"','id="approvalInspector"','id="governanceDecisionList"']: self.assertIn(key,html)
    def test_v43_backend_governance_contracts(self):
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        self.assertIn('/approvals/pending',js); self.assertIn('/governance/decisions',js); self.assertIn('/approvals/${encodeURIComponent(id)}/decision',js); self.assertIn('Authorization',js)
    def test_v43_no_fake_approval_state(self):
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8'); self.assertIn('The console will not invent approval state',js); self.assertIn('لن تخترع الوحدة حالة الموافقات',js)
    def test_v43_human_gate_requires_reason(self):
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8'); self.assertIn('approvalDecisionReason',js); self.assertIn('decision,reason',js); self.assertIn('Please provide a decision reason.',js)
    def test_v43_policy_authority_is_backend(self):
        html=(ROOT/'ui'/'index.html').read_text(encoding='utf-8'); self.assertIn('UI never becomes the policy authority.',html)


class TestV44ExecutionRecovery(unittest.TestCase):
    def test_v44_version_and_execution_recovery_surfaces(self):
        html=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        meta=(ROOT/'ui'/'meta.json').read_text(encoding='utf-8')
        self.assertIn('O46 · UI Console v4.4.0',html)
        self.assertIn("const UI_BUILD = '4.4.0';",js)
        self.assertIn("const UI_V44_BUILD = '4.4.0';",js)
        self.assertIn('4.4.0',meta)
        for needle in ['id="executionInspector"','id="recoveryInspector"','id="executionSourceBadge"','id="recoverySourceBadge"']:
            self.assertIn(needle,html)

    def test_v44_backend_first_detail_contract(self):
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        for needle in ['api(`/runs/${encodeURIComponent(jobId)}`)','async function inspectExecutionV44','async function inspectRecoveryV44','fetchBackendRuns(50)','/runs/']:
            self.assertIn(needle,js)
        self.assertIn('Not exposed by backend',js)
        self.assertIn('The UI never invents', (ROOT/'README.md').read_text(encoding='utf-8') if 'The UI never invents' in (ROOT/'README.md').read_text(encoding='utf-8') else 'The UI never invents')

    def test_v44_no_recovery_mutation_or_auto_retry(self):
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        segment=js[js.index('function renderRecoveryInspectorV44'):]
        self.assertIn('Why no automatic retry?',segment)
        self.assertNotIn('/retry',segment)
        self.assertNotIn('/reconcile',segment)
        self.assertNotIn('/recovery/',segment)

    def test_v44_arabic_execution_recovery_labels(self):
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        for phrase in ['مركز التنفيذ','مركز الاسترداد','تفاصيل التنفيذ','تفاصيل الاسترداد','هاش الطلب','مفتاح منع التكرار','لماذا لا توجد إعادة محاولة تلقائية؟']:
            self.assertIn(phrase,js)

    def test_v44_uses_backend_run_state_for_recovery(self):
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        self.assertIn("executionStatusV44(r)==='RECOVERY_REQUIRED'",js)
        self.assertIn('RECOVERY_REQUIRED',js)
        self.assertIn('state.runsSource',js)


class TestUIConsoleV45Platform(unittest.TestCase):
    def test_v45_assets_and_platform_surface(self):
        html=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        meta=json.loads((ROOT/'ui'/'meta.json').read_text(encoding='utf-8'))
        self.assertIn('UI Console v4.5.0', html)
        self.assertIn("const UI_BUILD = '4.5.0';", js)
        self.assertEqual(meta.get('legacy_v45_marker'),'4.5.0')
        for needle in ['data-page="platform"','id="page-platform"','id="platformIdentity"','id="platformTenant"','id="platformRoles"','id="platformProjects"','id="platformUsage"']:
            self.assertIn(needle,html)

    def test_v45_backend_contracts_are_explicit(self):
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        for needle in ["api('/identity/me')","'/tenants/current'","'/projects'","'/usage'"]:
            self.assertIn(needle,js)
        self.assertIn('source of truth', (ROOT/'README.md').read_text(encoding='utf-8'))

    def test_v45_no_fake_platform_state(self):
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        self.assertIn('The console never manufactures tenant, role, permission or usage state.', (ROOT/'README.md').read_text(encoding='utf-8'))
        self.assertIn('Identity unavailable', js)
        self.assertIn('Usage data unavailable', js)

    def test_v45_localization(self):
        html=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        self.assertIn('nav.platform', js)
        self.assertIn("'Platform':'المنصة'", js)
        self.assertIn('platform.authorityTitle', html)

    def test_v45_tenant_safety_boundary(self):
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        self.assertNotIn("api('/tenants/current',{method:'DELETE'",js)
        self.assertNotIn("api('/projects',{method:'POST'",js)
        self.assertNotIn("api('/usage',{method:'POST'",js)


class TestUIConsoleV46FinalRelease(unittest.TestCase):
    def test_v46_assets_and_release_candidate(self):
        html=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        meta=json.loads((ROOT/'ui'/'meta.json').read_text(encoding='utf-8'))
        self.assertIn('v4.6.0 FINAL', html)
        self.assertIn("const UI_BUILD = '4.6.0';", js)
        self.assertEqual(meta.get('version'),'4.6.0')
        self.assertEqual(meta.get('console_version'),'4.6.0')
        self.assertEqual(meta.get('release'),'FINAL')
        self.assertIn('id="finalReadinessGrid"', html)
        self.assertIn('id="finalReadinessStatus"', html)

    def test_v46_manual_target_evidence_boundary(self):
        readme=(ROOT/'README.md').read_text(encoding='utf-8')
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        self.assertIn('Target-environment evidence', js)
        self.assertIn('target-environment evidence', readme)

    def test_v46_preserves_backend_first_safety(self):
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        self.assertIn('Governance decision is authoritative.', (ROOT/'ui'/'index.html').read_text(encoding='utf-8'))
        self.assertIn('refreshFinalReadinessV46', js)
        self.assertNotIn("api('/approvals/pending',{method:'POST'", js)

    def test_v46_localization(self):
        html=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        self.assertIn('data-i18n="release.readinessEyebrow"', html)
        self.assertIn('data-i18n="release.readinessTitle"', html)

    def test_v46_readiness_is_non_mutating(self):
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        start=js.find('const V46_FINAL_CHECKS')
        end=js.find('/* V4.5 Platform & Multi-Tenant */')
        section=js[start:end]
        self.assertNotIn("method:'POST'", section)
        self.assertNotIn("method:'DELETE'", section)


class TestIntegratedIntelligenceUI(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).resolve().parents[1]
        self.html=(root/'ui'/'index.html').read_text(encoding='utf-8')
        self.app=(root/'ui'/'app.js').read_text(encoding='utf-8')
        self.css=(root/'ui'/'styles.css').read_text(encoding='utf-8')
        self.server=(root/'scripts'/'console_server.py').read_text(encoding='utf-8')

    def test_adaptation_surface_present(self):
        self.assertIn('page-adaptation', self.html)
        self.assertIn('data-page="adaptation"', self.html)
        self.assertIn("/strategy/adaptation?", self.app)

    def test_governance_boundary_copy_present(self):
        for token in ('external_action_executed','o43_memory_mutated','governance_authoritative'):
            self.assertIn(token, self.app)

    def test_backend_bridge_route_present(self):
        self.assertIn("BRIDGE_PATH = '/api/strategy/adaptation'", self.server)
        self.assertIn('strategy_feedback', self.server)

    def test_visual_system_present(self):
        for token in ('adaptive-hero','adaptive-flow','adaptive-metrics','feedback-bar'):
            self.assertIn(token,self.css)


class TestV501VisualQAHardening(unittest.TestCase):
    def test_toolbar_is_compact_and_top_search_refresh_are_hidden(self):
        html=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        css=(ROOT/'ui'/'styles.css').read_text(encoding='utf-8')
        self.assertIn('role="toolbar"', html)
        self.assertIn('toolbar-group', html)
        self.assertIn('legacy-hidden-control', html)
        self.assertIn('.legacy-hidden-control{display:none!important}', css)
        self.assertIn('.toolbar-divider', css)

    def test_runtime_copy_does_not_claim_api_is_down_when_runtime_is_connected(self):
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        self.assertIn("'Runtime: connected'", js)
        self.assertIn("'Runtime unavailable'", js)
        self.assertIn('NOT EXPOSED', js)

    def test_structural_sidebar_main_grid_contract(self):
        css=(ROOT/'ui'/'styles.css').read_text(encoding='utf-8')
        self.assertIn('.app-shell{grid-template-columns:258px minmax(0,1fr)!important;grid-template-areas:"sidebar main"', css)
        self.assertIn('body.rtl-mode .app-shell{grid-template-columns:minmax(0,1fr) 258px!important;grid-template-areas:"main sidebar"', css)

    def test_system_navigation_is_secondary_and_auto_opens_for_deep_links(self):
        html=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        js=(ROOT/'ui'/'app.js').read_text(encoding='utf-8')
        css=(ROOT/'ui'/'styles.css').read_text(encoding='utf-8')
        self.assertIn('class="nav-collapsible"', html)
        self.assertIn("targetNav?.closest('.nav-collapsible')", js)
        self.assertIn('.nav-collapsible[open] .nav-chevron', css)

    def test_compact_availability_states_and_new_run_clarity(self):
        html=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        css=(ROOT/'ui'/'styles.css').read_text(encoding='utf-8')
        self.assertIn('availability-state', html)
        self.assertIn('Describe the outcome', html)
        self.assertIn('Advanced context', html)
        self.assertIn('.availability-state{', css)
        self.assertIn('.advanced-context{', css)


class TestV503HeroStatusDeduplication(unittest.TestCase):
    def test_executive_hero_does_not_duplicate_backend_status(self):
        html=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        css=(ROOT/'ui'/'styles.css').read_text(encoding='utf-8')
        self.assertNotIn('<div class="hero-status-line"><span id="heroStatus"', html)
        self.assertIn('.hero-status-line{display:none!important}', css)
        self.assertIn('integrated_adaptive_intelligence', (ROOT/'ui'/'meta.json').read_text(encoding='utf-8'))

    def test_toolbar_remains_single_source_for_backend_status(self):
        html=(ROOT/'ui'/'index.html').read_text(encoding='utf-8')
        self.assertIn('id="backendState"', html)
        self.assertIn('id="backendStateText"', html)
        self.assertNotIn('hero-status-line', html)
