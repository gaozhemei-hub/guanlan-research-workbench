"""Candidate-only persistence and milestone regression. Uses synthetic material, no model calls.
GUANLAN_TEST_URL=http://127.0.0.1:8876/ python -m unittest tests.test_reliability_followup -v
Requires Python Playwright; the server must run with scheduling/AI disabled.
"""
import os, sys, unittest, json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'repro'))
import repro_frontend as R
from playwright.sync_api import sync_playwright
# The shared helper owns the target URL; importing this suite must not change it.

class Reliability(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.pw=sync_playwright().start();cls.browser=cls.pw.chromium.launch(args=['--no-proxy-server'])
 @classmethod
 def tearDownClass(cls):cls.browser.close();cls.pw.stop()
 def seeded(self):
  ctx,p=R.new_page(self.browser)
  p.evaluate("""loadDemo();readerStep=3;render();archive();closeDialog();
  state.companies.push({id:'test-company',name:'教学公司',code:'999001',role:'教学',reason:'测试',history:[],originEntryIds:[]});
  state.watches[0].milestones=[{title:'教学复核',rule:'人工核对',note:'原依据',dueDate:'2026-01-01',status:'待核查',history:[]}];save();""")
  return ctx,p
 def assert_failed_write(self,p,button):
  before=p.evaluate("JSON.stringify({...state,draft:null})")
  p.evaluate("window.originalSetter=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k===KEY)throw new DOMException('test quota','QuotaExceededError');return originalSetter.call(this,k,v)};true")
  p.click(button)
  p.wait_for_function("document.querySelector('#toast').textContent.includes('撤销') || document.querySelector('#restore-error')?.textContent || document.querySelector('#check-error')?.textContent")
  self.assertEqual(p.evaluate("JSON.stringify({...state,draft:null})"),before)
  self.assertEqual(p.evaluate("JSON.stringify({...JSON.parse(localStorage.getItem(KEY)),draft:null})"),before)
  self.assertIn('撤销',p.inner_text('#toast'))
  self.assertFalse(p.evaluate("$('#dialog').open"))
  p.evaluate('Storage.prototype.setItem=originalSetter;true')
 def test_company_watch_path_check_link_and_milestone_rollback(self):
  cases=[
   ("addCompany('','');$('#company-name').value='新教学公司';$('#company-code').value='999002';$('#company-role').value='教学';$('#company-reason').value='测试';",'#save-company'),
   ("editWatch(state.watches[0].id);$('#watch-title').value='修改后的主题';",'#save-watch'),
   ("researchDetail(state.entries[0].id);$('#research-path').value='新路径';",'#research-save'),
   ("researchDetail(state.entries[0].id);$('#link-company').value='test-company';",'#link-company-save'),
   ("editCheck(state.entries[0].id);$('#check-label').value='教学核查';$('#check-value').value='1';$('#check-unit').value='%';$('#check-period').value='2026-01';$('#check-reason').value='教学待核查';",'#check-save'),
   ("addMilestone(state.watches[0].id);$('#milestone-title').value='新里程碑';$('#milestone-rule').value='待核查';$('#milestone-due').value='2099-01-01';",'#milestone-add'),
   ("milestone(state.watches[0].id,0);$('#m-status').value='延期';$('#m-due').value='2099-01-01';$('#m-evidence').value='测试延期';",'#m-save'),
   ("editFocus();$('#focus-input').value='新关注词';",'#focus-save'),
  ]
  for action,button in cases:
   with self.subTest(button=button):
    ctx,p=self.seeded()
    try:p.evaluate(action);self.assert_failed_write(p,button)
    finally:ctx.close()
 def test_failed_company_can_be_retried_without_duplicate(self):
  ctx,p=self.seeded()
  try:
   action="addCompany('','');$('#company-name').value='新教学公司';$('#company-code').value='999002';$('#company-role').value='教学';$('#company-reason').value='测试';"
   p.evaluate(action);self.assert_failed_write(p,'#save-company');p.evaluate(action);p.click('#save-company');p.reload()
   self.assertEqual(p.evaluate("state.companies.filter(c=>c.code==='999002').length"),1)
  finally:ctx.close()
 def test_deferred_milestone_date_validation_and_recurring_due(self):
  ctx,p=self.seeded()
  try:
   p.evaluate("milestone(state.watches[0].id,0);$('#m-status').value='延期';$('#m-evidence').value='等待下一期数据';$('#m-due').value='';")
   p.click('#m-save');self.assertIn('复核日',p.inner_text('#m-error'))
   p.fill('#m-due','2026-01-01');p.click('#m-save');self.assertIn('晚于今天',p.inner_text('#m-error'))
   p.fill('#m-due','2099-01-01');p.click('#m-save');p.reload()
   r=p.evaluate("({m:state.watches[0].milestones[0],due:milestoneIsDue(state.watches[0],state.watches[0].milestones[0])})")
   self.assertEqual(r['m']['status'],'延期');self.assertFalse(r['due']);self.assertEqual(r['m']['history'][-1]['previousDueDate'],'2026-01-01')
   self.assertTrue(p.evaluate("localDay=()=> '2099-01-01';milestoneIsDue(state.watches[0],state.watches[0].milestones[0])"))
   self.assertIn('到期复核',p.evaluate('milestoneDueLabel(state.watches[0])'))
   self.assertIn('到期复核',p.evaluate('researchInbox()'))
   self.assertFalse(p.evaluate('state.watches[0].active=false;milestoneIsDue(state.watches[0],state.watches[0].milestones[0])'))
   self.assertFalse(p.evaluate("validResearchDate('2026-02-30')"))
  finally:ctx.close()
 def test_template_milestone_can_get_a_review_date(self):
  ctx,p=self.seeded()
  try:
   p.evaluate("delete state.watches[0].milestones[0].dueDate;save();milestone(state.watches[0].id,0)")
   p.fill('#m-due','2099-01-02');p.fill('#m-evidence','设定首次复核时间');p.click('#m-save');p.reload()
   self.assertEqual(p.evaluate('state.watches[0].milestones[0].dueDate'),'2099-01-02')
  finally:ctx.close()
 def test_standalone_contains_and_runs_same_fix(self):
  ctx=self.browser.new_context();p=ctx.new_page()
  try:
   path=Path(__file__).resolve().parents[1]/'prototype/观澜-可交互原型.html'
   p.goto(path.as_uri());p.evaluate("loadDemo();readerStep=3;render();archive();closeDialog();editFocus();$('#focus-input').value='不会保存';")
   self.assert_failed_write(p,'#focus-save')
   self.assertTrue(p.evaluate("milestoneIsDue({active:true},{status:'延期',dueDate:'2026-01-01'})"))
  finally:ctx.close()

 def test_failed_backup_does_not_leave_focus_or_partial_records(self):
  ctx,p=self.seeded()
  try:
   backup=p.evaluate("JSON.parse(JSON.stringify(state))")
   backup['focusKeywords']='不应残留的关注词';backup['companies'][0]['id']='other-company'
   p.evaluate('restore()');p.set_input_files('#backup-file',{'name':'test.json','mimeType':'application/json','buffer':json.dumps(backup).encode()})
   self.assert_failed_write(p,'#restore-confirm')
  finally:ctx.close()
 def test_unsaved_material_draft_survives_failure(self):
  ctx,p=self.seeded()
  try:
   p.evaluate("go('reader');readerStep=1;render();window.originalSetter=Storage.prototype.setItem;Storage.prototype.setItem=function(){throw new DOMException('quota','QuotaExceededError')};true")
   before=p.evaluate('state.entries.length')
   p.fill('#source-text','临时编辑的材料仍需保留')
   self.assertEqual(p.evaluate('draft.text'),'临时编辑的材料仍需保留')
   self.assertEqual(p.evaluate('state.entries.length'),before)
   self.assertNotEqual(p.evaluate('JSON.parse(localStorage.getItem(KEY)).draft.text'),'临时编辑的材料仍需保留')
   self.assertIn('草稿暂留内存',p.inner_text('#toast'))
  finally:ctx.close()

if __name__=='__main__':unittest.main(verbosity=2)
