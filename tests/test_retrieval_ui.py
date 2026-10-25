"""Real browser and local retrieval endpoint; original fixtures only."""
import os
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE=os.environ.get('GUANLAN_TEST_URL','http://127.0.0.1:8765/').rstrip('/')+'/'


class RetrievalUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw=sync_playwright().start()
        cls.browser=cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close();cls.pw.stop()

    def setUp(self):
        self.context=self.browser.new_context()
        self.addCleanup(self.context.close)
        self.page=self.context.new_page()
        self.page.goto(BASE)
        self.page.wait_for_function('online')

    def seed(self):
        self.page.evaluate("""state.entries=[{id:'teaching',title:'原创教学材料',node:'gold',text:'黄金🙂库存需要核实。\\n\\n白银工业需求存在反向条件。'}];save();go('retrieval')""")
        self.page.locator('[data-evidence-id]').check()
        self.page.locator('#evidence-query').fill('黄金库存')

    def test_archive_search_and_return_to_source(self):
        p=self.page
        p.get_by_role('button',name='走一遍材料归档 →').click()
        p.locator('[data-action="reader-next"]').click()
        p.locator('[data-action="reader-check"]').click()
        p.locator('[data-action="reader-save"]').click()
        p.get_by_role('button',name='关闭',exact=True).click()
        p.locator('[data-route="retrieval"]').click()
        p.locator('[data-evidence-id]').check()
        p.locator('#evidence-query').fill('政策议程')
        p.locator('#evidence-search').click()
        p.wait_for_selector('[data-evidence-open]')
        p.locator('[data-evidence-open]').first.click()
        self.assertIn('政策',p.locator('#evidence-highlight').inner_text())
        self.assertEqual(p.evaluate('state.entries.length'),1)
        p.get_by_role('button',name='关闭',exact=True).click()
        p.locator('#evidence-clear').click()
        self.assertEqual(p.locator('[data-evidence-open]').count(),0)
        self.assertEqual(p.locator('[data-evidence-id]:checked').count(),0)

    def test_unicode_offsets_and_changed_source(self):
        self.seed();p=self.page
        p.locator('#evidence-search').click();p.wait_for_selector('[data-evidence-open]')
        p.locator('[data-evidence-open]').first.click()
        self.assertIn('🙂',p.locator('#evidence-highlight').inner_text())
        p.get_by_role('button',name='关闭',exact=True).click()
        p.evaluate("state.entries[0].text='正文已改';save();render()")
        self.assertEqual(p.locator('[data-evidence-open]').count(),0)
        self.assertIn('修改或删除',p.locator('#evidence-error').inner_text())

    def test_changed_question_discards_late_response(self):
        self.seed();p=self.page;pending=[]
        p.route('**/api/retrieve',lambda route:pending.append(route))
        p.locator('#evidence-search').click()
        p.wait_for_timeout(100)
        self.assertEqual(len(pending),1)
        p.locator('#evidence-query').fill('新的问题')
        pending[0].fulfill(json={'hits':[{'source':'teaching','text':'不应出现的旧结果','start':0,'end':1}]})
        p.wait_for_timeout(100)
        self.assertEqual(p.locator('[data-evidence-open]').count(),0)
        self.assertNotIn('不应出现的旧结果',p.locator('#page').inner_text())

    def test_offline_html_disables_search(self):
        path=Path(__file__).resolve().parents[1]/'prototype/观澜-可交互原型.html'
        self.page.goto(path.as_uri()+'#retrieval')
        self.assertTrue(self.page.locator('#evidence-search').is_disabled())

    def test_semantic_error_does_not_fall_back(self):
        self.seed();p=self.page;calls=[]
        def fail(route):
            calls.append(route.request.post_data_json)
            route.fulfill(status=400,json={'error':'本地模型不可用，没有自动降级。'})
        p.route('**/api/retrieve',fail)
        p.locator('#evidence-method').select_option('vector')
        p.locator('#evidence-search').click()
        p.wait_for_function("document.querySelector('#evidence-error').textContent.includes('模型不可用')")
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0]['method'],'vector')
        self.assertEqual(p.locator('[data-evidence-open]').count(),0)

    def test_method_change_clears_old_results(self):
        self.seed();p=self.page
        p.locator('#evidence-search').click();p.wait_for_selector('[data-evidence-open]')
        p.locator('#evidence-method').select_option('reranked')
        self.assertEqual(p.locator('[data-evidence-open]').count(),0)


if __name__=='__main__':unittest.main()
