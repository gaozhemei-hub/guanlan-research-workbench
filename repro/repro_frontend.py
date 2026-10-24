"""任务07 · 前端缺陷复现（Playwright + Chromium，基于 v0.8 交接副本）。

前提：在副本根目录启动服务 `python server/app.py --no-schedule`（固定 127.0.0.1:8765）。
运行：python repro/repro_frontend.py [--only F1,F2] → 打印每个场景的观察结果（JSON）。
AI 场景用 page.route 拦截 /api/state 与 /api/analyze，属于**模拟响应**，不调用真实模型。
所有场景使用全新浏览器上下文（独立 localStorage），不读取个人数据。
"""
import json, sys, time, argparse, os
from playwright.sync_api import sync_playwright

BASE = os.environ.get('GUANLAN_TEST_URL', 'http://127.0.0.1:8765/').rstrip('/') + '/'
RESULTS = {}

def new_page(browser, mock_ai=None):
    ctx = browser.new_context(); page = ctx.new_page()
    page.on('dialog', lambda d: d.accept())
    if mock_ai:
        def state_route(route):
            resp = route.fetch(); body = resp.json(); body['ai'] = {'configured': True, 'host': 'mock.invalid', 'model': 'MOCK'}
            route.fulfill(response=resp, json=body)
        page.route('**/api/state', state_route)
        page.route('**/api/analyze', mock_ai)
    page.goto(BASE + '#home'); page.wait_for_function('typeof loadRemote==="function"')
    page.evaluate('loadRemote()'); page.wait_for_timeout(300)
    return ctx, page

def to_review(page):
    page.evaluate("loadDemo()"); page.wait_for_selector('#source-text')
    page.click('[data-action="reader-next"]'); page.wait_for_selector('#claim')

def fill_quota(page, headroom):
    """Fill this origin's localStorage with filler so that only ~headroom UTF-16 chars remain free."""
    return page.evaluate("""(headroom)=>{
      let lo=0, hi=20_000_000;
      while(lo<hi){const mid=Math.floor((lo+hi+1)/2);try{localStorage.setItem('__probe','x'.repeat(mid));localStorage.removeItem('__probe');lo=mid;}catch{hi=mid-1;}}
      const free=lo; const filler=Math.max(0,free-headroom);
      localStorage.setItem('__filler','x'.repeat(filler)); return {freeCharsBefore:free, filler};
    }""", headroom)

def f1_focus_loss(browser):
    ctx, page = new_page(browser); to_review(page)
    page.fill('#claim', ''); page.click('#claim'); page.keyboard.type('正在输入的观点')
    before = page.evaluate('document.activeElement.id')
    page.evaluate('loadRemote()'); page.wait_for_timeout(400)  # the same call setInterval makes every 60 s
    after = page.evaluate('document.activeElement.id||document.activeElement.tagName')
    kept = page.input_value('#claim')
    # news filter text is not bound to state; check whether typed-but-unapplied text survives
    page.evaluate("go('macro','inflation')"); page.evaluate("subtab='news';render()")
    has_q = page.locator('#news-query').count() > 0
    lost_query = None
    if has_q:
        page.fill('#news-query', '油价'); page.evaluate('loadRemote()'); page.wait_for_timeout(400)
        lost_query = page.input_value('#news-query')
    RESULTS['F1_focus_loss'] = {'activeBefore': before, 'activeAfterLoadRemote': after, 'claimTextKept': kept, 'newsQueryAfterLoadRemote': lost_query}
    ctx.close()

def f2_quota_archive(browser):
    ctx, page = new_page(browser); to_review(page)
    page.click('[data-action="reader-check"]'); page.wait_for_selector('[data-action="reader-save"]')
    q = fill_quota(page, 200)
    page.click('[data-action="reader-save"]'); page.wait_for_timeout(300)
    toast1 = page.inner_text('#toast'); pill = page.inner_text('#save-state')
    in_memory = page.evaluate('state.entries.length')
    page.click('[data-action="reader-save"]'); page.wait_for_timeout(300)
    retry_msg = page.inner_text('#reader-error')
    page.reload(); page.wait_for_function('typeof state==="object"')
    after_reload = page.evaluate('state.entries.length')
    RESULTS['F2_quota_archive'] = {**q, 'toastAfterFirstClick': toast1, 'savePill': pill, 'entriesInMemory': in_memory,
                                   'messageOnSecondClick': retry_msg, 'entriesAfterReload': after_reload}
    ctx.close()

def f3_false_success(browser):
    ctx, page = new_page(browser); to_review(page)
    page.click('[data-action="reader-check"]'); page.click('[data-action="reader-save"]'); page.wait_for_timeout(200)
    page.evaluate('closeDialog()')
    eid = page.evaluate('state.entries[0].id'); v0 = page.evaluate('state.entries[0].version')
    fill_quota(page, 50)
    page.evaluate(f"editEntry('{eid}')"); page.fill('#edit-claim', '修订后的观点（长度足以让整份状态超出剩余空间）' * 3); page.fill('#edit-reason', '新依据')
    page.click('#review-change'); page.click('#accept-change'); page.wait_for_timeout(300)
    toast = page.inner_text('#toast'); pill = page.inner_text('#save-state')
    page.reload(); page.wait_for_function('typeof state==="object"')
    RESULTS['F3_false_success_toast'] = {'versionBefore': v0, 'toastShown': toast, 'savePill': pill,
                                         'versionAfterReload': page.evaluate('state.entries[0].version')}
    ctx.close()

def f4_backup_xss(browser):
    ctx, page = new_page(browser)
    backup = {'schema': 2, 'entries': [], 'watches': [], 'companies': [{
        'id': 'xss-demo', 'name': '测试公司', 'code': '000001', 'role': '测试', 'reason': '复现', 'history': [],
        'valuation': {'pe': 10, 'pb': None, 'date': '"><img src=x onerror="window.__xss=1">', 'period': '2026-06-30', 'currency': 'CNY', 'source': '测试'}}]}
    page.evaluate('restore()'); page.set_input_files('#backup-file', files=[{'name': 'b.json', 'mimeType': 'application/json', 'buffer': json.dumps(backup).encode()}])
    page.click('#restore-confirm'); page.wait_for_timeout(300)
    accepted = page.evaluate("state.companies.some(c=>c.id==='xss-demo')")
    if accepted: page.evaluate("companyValues('xss-demo')"); page.wait_for_timeout(500)
    err = page.inner_text('#restore-error') if page.locator('#restore-error').count() else ''
    RESULTS['F4_backup_attribute_injection'] = {'backupAccepted': accepted, 'injectedImgInDialog': page.locator('#dialog img[src="x"]').count(),
                                               'scriptExecuted': page.evaluate('window.__xss===1'), 'restoreError': err}
    ctx.close()

def f5_ai_late_overwrite(browser):
    # Delay is injected inside the page (wrapping fetch), so the test thread can keep typing meanwhile.
    def ok(route):
        route.fulfill(json={'suggestions': [{'node': 'policy', 'segment': 2, 'quote': '可能进入政策议程', 'claim': 'AI 建议的观点', 'question': 'AI 问题', 'counter': 'AI 反证', 'keywords': 'policy'}], 'model': 'MOCK'})
    ctx, page = new_page(browser, mock_ai=ok); to_review(page)
    page.evaluate("""()=>{const f=window.fetch;window.fetch=async(u,o)=>{const r=await f(u,o);if(String(u).includes('/api/analyze'))await new Promise(z=>setTimeout(z,1500));return r;};}""")
    page.click('[data-action="ai"]'); page.wait_for_timeout(200)
    page.fill('#claim', '我在等待期间手写的观点'); page.fill('#question', '我的问题')
    typed = page.evaluate('draft.claim')
    page.wait_for_timeout(2500)
    RESULTS['F5_ai_late_response_overwrites_manual_edit'] = {'claimWhileWaiting': typed, 'claimAfterResponse': page.evaluate('draft.claim'),
        'questionAfterResponse': page.evaluate('draft.question'), 'toast': page.inner_text('#toast')}
    ctx.close()

def f6_ai_provenance_drift(browser):
    def ok(route):
        route.fulfill(json={'suggestions': [{'node': 'policy', 'segment': 2, 'quote': '可能进入政策议程', 'claim': 'AI 建议', 'question': 'Q', 'counter': 'C', 'keywords': 'policy'}], 'model': 'MOCK'})
    ctx, page = new_page(browser, mock_ai=ok); to_review(page)
    page.click('[data-action="ai"]'); page.wait_for_timeout(800)
    page.select_option('#source-segment', '3'); page.wait_for_timeout(200)
    page.fill('#claim', '完全改写的观点，与 AI 引文无关')
    page.click('[data-action="reader-check"]'); page.click('[data-action="reader-save"]'); page.wait_for_timeout(300)
    e = page.evaluate('({mode:state.entries[0].mode, segment:state.entries[0].segment, aiQuote:state.entries[0].aiQuote, claim:state.entries[0].claim})')
    seg_text = page.evaluate('state.entries[0].text.split(/\\n\\s*\\n/).filter(s=>s.trim())[state.entries[0].segment-1]')
    RESULTS['F6_ai_provenance_label_drift'] = {**e, 'aiQuoteInArchivedSegment': (e.get('aiQuote') or '') in seg_text if e.get('aiQuote') else None}
    ctx.close()

def f7_duplicate_company_merge(browser):
    ctx, page = new_page(browser)
    page.evaluate("state.companies.push({id:'local-1',name:'宁德时代',code:'300750',role:'电池',reason:'本机',history:[]});save()")
    backup = {'schema': 2, 'entries': [], 'watches': [], 'companies': [{'id': 'other-browser-9', 'name': '宁德时代', 'code': '300750', 'role': '电池', 'reason': '另一台电脑', 'history': []}]}
    page.evaluate('restore()'); page.set_input_files('#backup-file', files=[{'name': 'b.json', 'mimeType': 'application/json', 'buffer': json.dumps(backup).encode()}])
    page.click('#restore-confirm'); page.wait_for_timeout(300)
    RESULTS['F7_same_code_duplicate_after_merge'] = {'companiesWithCode300750': page.evaluate("state.companies.filter(c=>c.code==='300750').length")}
    ctx.close()

SCENARIOS = {'F1': f1_focus_loss, 'F2': f2_quota_archive, 'F3': f3_false_success, 'F4': f4_backup_xss, 'F5': f5_ai_late_overwrite, 'F6': f6_ai_provenance_drift, 'F7': f7_duplicate_company_merge}

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--only', default=','.join(SCENARIOS)); a = ap.parse_args()
    with sync_playwright() as p:
        browser = p.chromium.launch(args=['--no-proxy-server'])
        for k in a.only.split(','):
            try: SCENARIOS[k](browser)
            except Exception as e: RESULTS[k + '_ERROR'] = f'{type(e).__name__}: {str(e)[:300]}'
        RESULTS['_browser'] = browser.version
        browser.close()
    print(json.dumps(RESULTS, ensure_ascii=False, indent=1))
