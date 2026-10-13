"""任务07 候选回归测试（前端，Playwright + Chromium）。
前提：副本根目录已运行 `python server/app.py --no-schedule`（127.0.0.1:8765）。AI 场景为模拟响应。
python -m unittest tests.test_ui_regressions -v
"""
import json, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'repro'))
from playwright.sync_api import sync_playwright
import repro_frontend as R

class UI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch(args=['--no-proxy-server'])
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def test_periodic_refresh_keeps_focus_while_typing(self):
        R.f1_focus_loss(self.browser); r = R.RESULTS['F1_focus_loss']
        self.assertEqual(r['activeAfterLoadRemote'], 'claim')

    def test_archive_under_full_storage_is_not_reported_as_archived(self):
        R.f2_quota_archive(self.browser); r = R.RESULTS['F2_quota_archive']
        self.assertEqual(r['entriesInMemory'], 0)
        self.assertNotIn('已经归档', r['messageOnSecondClick']); self.assertIn('没有归档', r['messageOnSecondClick'])

    def test_failed_revision_shows_no_success_and_is_rolled_back(self):
        R.f3_false_success(self.browser); r = R.RESULTS['F3_false_success_toast']
        self.assertNotIn('已保存新版本', r['toastShown']); self.assertIn('撤销', r['toastShown'])

    def test_backup_cannot_inject_markup(self):
        R.f4_backup_xss(self.browser); r = R.RESULTS['F4_backup_attribute_injection']
        self.assertFalse(r['backupAccepted']); self.assertFalse(r['scriptExecuted'])

    def test_escape_holds_even_if_bad_value_already_in_storage(self):
        ctx, page = R.new_page(self.browser)
        page.evaluate("""state.companies.push({id:'x1',name:'n',code:'000001',role:'r',reason:'r',history:[],valuation:{pe:1,pb:null,date:'"><img src=x onerror="window.__xss=1">',period:'2026-06-30',currency:'CNY',source:'s'}});save();companyValues('x1')""")
        page.wait_for_timeout(400)
        self.assertFalse(page.evaluate('window.__xss===1')); self.assertEqual(page.locator('#dialog img').count(), 0); ctx.close()

    def test_late_ai_response_does_not_overwrite_manual_edit(self):
        R.f5_ai_late_overwrite(self.browser); r = R.RESULTS['F5_ai_late_response_overwrites_manual_edit']
        self.assertEqual(r['claimAfterResponse'], '我在等待期间手写的观点'); self.assertIn('未自动覆盖', r['toast'])

    def test_changed_segment_drops_verified_label(self):
        R.f6_ai_provenance_drift(self.browser); r = R.RESULTS['F6_ai_provenance_label_drift']
        self.assertNotIn('引用位置已校验', r['mode']); self.assertIsNone(r.get('aiQuote'))

    def test_unedited_ai_suggestion_keeps_verified_label(self):
        def ok(route): route.fulfill(json={'suggestions': [{'node': 'policy', 'segment': 2, 'quote': '可能进入政策议程', 'claim': 'AI 建议', 'question': 'Q', 'counter': 'C', 'keywords': 'policy'}], 'model': 'MOCK'})
        ctx, page = R.new_page(self.browser, mock_ai=ok); R.to_review(page)
        page.click('[data-action="ai"]'); page.wait_for_timeout(800)
        page.click('[data-action="reader-check"]'); page.click('[data-action="reader-save"]'); page.wait_for_timeout(300)
        e = page.evaluate('({mode:state.entries[0].mode,q:state.entries[0].aiQuote})')
        self.assertIn('引用位置已校验', e['mode']); self.assertEqual(e['q'], '可能进入政策议程'); ctx.close()

if __name__ == '__main__': unittest.main(verbosity=2)
