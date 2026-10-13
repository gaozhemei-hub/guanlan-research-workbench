import unittest,sys,json,subprocess
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import prices
import tempfile
class Prices(unittest.TestCase):
 def setUp(self):
  self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
  self.patch=patch.object(prices,'CACHE_DIR',Path(self.directory.name));self.patch.start();self.addCleanup(self.patch.stop)
 def payload(self):return {'code':'300750','start':'2026-01-01','end':'2026-09-10','adjustment':'前复权'}
 def test_validation(self):
  s,a,b,adj=prices.validate(self.payload());self.assertEqual(s['company'],'宁德时代')
  for changes in [{'code':'000001'},{'code':'300750;echo x'},{'adjustment':'unknown'},{'start':'2027-01-01'},{'end':'2099-01-01'},{'start':'2020-01-01'},{'start':None}]:
   with self.assertRaises(ValueError):prices.validate({**self.payload(),**changes})
 def test_worker_failure(self):
  with patch.object(prices.subprocess,'run',side_effect=subprocess.TimeoutExpired('worker',40)):
   with self.assertRaisesRegex(ValueError,'超时'):prices.fetch(self.payload())
 def test_invalid_code_never_spawns(self):
  with patch.object(prices.subprocess,'run') as run:
   with self.assertRaises(ValueError):prices.fetch({**self.payload(),'code':'bad'})
   run.assert_not_called()
 def test_upstream_error(self):
  with patch.object(prices.subprocess,'run',return_value=subprocess.CompletedProcess([],1,json.dumps({'error':'所选区间没有有效行情'}))):
   with self.assertRaisesRegex(ValueError,'没有有效行情'):prices.fetch(self.payload())

 def test_same_day_cache_and_stale_fallback(self):
  from datetime import datetime,timezone
  result={'csv':'date,close\n2026-09-10,100\n','fetchedAt':datetime.now(timezone.utc).isoformat()}
  with patch.object(prices.subprocess,'run',return_value=subprocess.CompletedProcess([],0,json.dumps(result))) as run:
   self.assertEqual(prices.fetch(self.payload())['cacheState'],'fresh')
   self.assertEqual(prices.fetch(self.payload())['cacheState'],'same-day-cache')
   self.assertEqual(run.call_count,1)
  with patch.object(prices.subprocess,'run',side_effect=subprocess.TimeoutExpired('worker',40)):
   old=prices.fetch({**self.payload(),'force':True})
   self.assertEqual(old['cacheState'],'stale');self.assertEqual(old['fetchedAt'],result['fetchedAt'])

if __name__=='__main__':unittest.main(verbosity=2)
