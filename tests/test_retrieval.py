import tempfile
import unittest
from pathlib import Path
from server.retrieval import Index


class RetrievalLifecycle(unittest.TestCase):
    def setUp(self):
        self.index = Index()
        self.addCleanup(self.index.close)
        self.text = '  黄金库存是教学指标。\n\n居民信贷需要统一统计口径。'
        self.index.replace('a', 'note', 'v1', self.text)

    def test_offsets_and_idempotence(self):
        first = self.index.search('a', '黄金库存')
        self.index.replace('a', 'note', 'v1', self.text)
        self.assertEqual(first, self.index.search('a', '黄金库存'))
        for item in self.index.search('a', '黄金库存 居民信贷'):
            self.assertEqual(self.text[item['start']:item['end']], item['text'])
            self.assertTrue(self.index.citation_valid('a', item['chunk_id'], item['text']))

    def test_revision_and_delete_invalidate_citations(self):
        item = self.index.search('a', '黄金库存')[0]
        self.index.replace('a', 'note', 'v2', '白银供需仍待核验。')
        self.assertEqual(self.index.search('a', '黄金库存'), [])
        self.assertFalse(self.index.citation_valid('a', item['chunk_id'], item['text']))
        new = self.index.search('a', '白银供需')[0]
        self.index.delete('a', 'note')
        self.assertEqual(self.index.search('a', '白银供需'), [])
        self.assertFalse(self.index.citation_valid('a', new['chunk_id'], new['text']))

    def test_failed_revision_retains_stale_data_then_recovers(self):
        with self.assertRaises(ValueError):
            self.index.replace('a', 'note', 'v2', '')
        item = self.index.search('a', '黄金库存')[0]
        self.assertEqual(item['stale'], 1)
        self.assertFalse(self.index.citation_valid('a', item['chunk_id'], item['text']))
        self.index.replace('a', 'note', 'v1', self.text)
        self.assertTrue(self.index.citation_valid('a', item['chunk_id'], item['text']))

    def test_transaction_failure_rolls_back(self):
        self.index.db.execute("CREATE TRIGGER fail_new BEFORE INSERT ON chunks WHEN NEW.version='v2' BEGIN SELECT RAISE(ABORT, 'injected'); END")
        with self.assertRaises(Exception):
            self.index.replace('a', 'note', 'v2', '白银供需仍待核验。')
        item = self.index.search('a', '黄金库存')[0]
        self.assertEqual(item['version'], 'v1')
        self.assertEqual(item['stale'], 1)

    def test_workspace_isolation(self):
        self.index.replace('b', 'note', 'v1', '黄金库存是另一个工作区的记录。')
        a = self.index.search('a', '黄金库存')[0]
        self.assertFalse(self.index.citation_valid('b', a['chunk_id'], a['text']))
        self.index.delete('b', 'note')
        self.assertEqual(len(self.index.search('a', '黄金库存')), 1)
        self.assertEqual(self.index.search('b', '黄金库存'), [])

    def test_version_collision_and_invalid_citation(self):
        item = self.index.search('a', '黄金库存')[0]
        for quote in ('', '并不存在的原句'):
            self.assertFalse(self.index.citation_valid('a', item['chunk_id'], quote))
        with self.assertRaises(ValueError):
            self.index.replace('a', 'note', 'v1', '变更内容')

    def test_no_overlap_and_empty_query(self):
        self.assertEqual(self.index.search('a', '火星轨道'), [])
        self.assertEqual(self.index.search('a', ''), [])

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'index.sqlite'
            first = Index(path)
            first.replace('a', 'one', 'v1', '白银供需')
            first.close()
            second = Index(path)
            try:
                self.assertEqual(second.search('a', '白银')[0]['source'], 'one')
            finally:
                second.close()


if __name__ == '__main__':
    unittest.main()
