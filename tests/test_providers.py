import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import pandas as pd
import ak_worker as worker
import app
from providers import AK_SOURCES
class ProviderContracts(unittest.TestCase):
 def test_monthly_period_not_fake_day(self):
  df=pd.DataFrame([{'月份':'2026年01月份','同比':2.1},{'月份':'2026年02月份','同比':0.8},{'月份':'2026年03月份','同比':float('nan')}])
  p=worker.series_points(df,'月份','同比',True)['points']
  self.assertEqual(p,[{'date':'2026-01','value':2.1},{'date':'2026-02','value':0.8}])
 def test_compact_month_and_invalid_month(self):
  df=pd.DataFrame([{'月份':'202508','值':1},{'月份':'202513','值':2}])
  self.assertEqual(worker.series_points(df,'月份','值',True)['points'],[{'date':'2025-08','value':1}])
 def test_financial_identity_dates_missing_and_raw_units(self):
  row={'SECUCODE':'600547.SH','REPORT_DATE':'2025-06-30','NOTICE_DATE':'2025-08-29','CURRENCY':'CNY','TOTALOPERATEREVE':1e9,'MGJYXJJE':0,'ROEJQ':float('nan')}
  wrong={**row,'SECUCODE':'000603.SZ'}
  future={**row,'NOTICE_DATE':'2099-01-01'}
  reports=worker.financial_reports(pd.DataFrame([row,wrong,future]),'600547.SH')['reports']
  self.assertEqual(len(reports),1);self.assertEqual(reports[0]['values']['revenue'],1e9)
  self.assertEqual(reports[0]['values']['cashPerShare'],0);self.assertIsNone(reports[0]['values']['roe'])
 def test_failed_financial_refresh_preserves_report(self):
  from unittest.mock import patch
  source=next(s for s in AK_SOURCES if s['id']=='finance_600547')
  old=app.STATE['sources'].get(source['id'])
  try:
   app.STATE['sources'][source['id']]={**source,'reports':[{'period':'2025-06-30'}],'fetchedAt':'2025-08-30'}
   with patch('app.subprocess.run',side_effect=TimeoutError('test')):out=app.fetch(source)
   self.assertEqual(out['status'],'stale');self.assertEqual(out['reports'][0]['period'],'2025-06-30')
  finally:
   if old is None:app.STATE['sources'].pop(source['id'],None)
   else:app.STATE['sources'][source['id']]=old
 def test_keyword_routes_do_not_assume_every_news_is_gold(self):
  nodes,reason=worker.classify('公司公布光伏单位耗银新进展','尚需进一步验证',[])
  self.assertIn('silver',nodes);self.assertIn('business',nodes);self.assertNotIn('gold',nodes)
  self.assertIn('耗银',reason)
 def test_collection_link_is_not_fabricated_article(self):
  s=next(s for s in AK_SOURCES if s['id']=='news_sina')
  i=worker.news_item(s,'','【测试黄金标题】正文。','2026-01-01 10:00:00')
  self.assertEqual(i['url'],s['url']);self.assertEqual(i['linkKind'],'collection');self.assertNotIn('body',i)
  self.assertTrue(i['publishedAt'].endswith('+08:00'))
 def test_cross_source_exact_headline_dedup_identity(self):
  sources=[next(s for s in AK_SOURCES if s['id']==key) for key in ['news_sina','news_cls']]
  items=[worker.news_item(s,'测试用的同一个足够长的财经新闻标题','',f'2026-01-01 1{i}:00:00') for i,s in enumerate(sources)]
  self.assertNotEqual(items[0]['id'],items[1]['id']);self.assertEqual(items[0]['dedupKey'],items[1]['dedupKey'])
 def test_refresh_keeps_history_and_first_seen(self):
  old=[{'id':'old','publishedAt':'2026-01-01','firstFetchedAt':'old-time'},{'id':'same','publishedAt':'2026-01-02','firstFetchedAt':'first-time'}]
  current=[{'id':'same','publishedAt':'2026-01-02','title':'updated'}]
  out=app.merge_items(current,old)
  self.assertEqual(len(out),2);self.assertEqual(out[0]['firstFetchedAt'],'first-time')
if __name__=='__main__':unittest.main(verbosity=2)
