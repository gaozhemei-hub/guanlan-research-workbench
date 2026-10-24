"""Validate experiment scoring without downloading a model."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('comparison', Path(__file__).resolve().parents[1]/'scripts/compare-retrieval.py')
comparison = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)


class RetrievalMetrics(unittest.TestCase):
    def test_fusion_rewards_agreement_and_has_fixed_depth(self):
        self.assertEqual(comparison.fuse([['a', 'b'], ['b', 'c']])[0], 'b')
        self.assertNotIn('tail', comparison.fuse([['a', 'tail']], depth=1))

    def test_partial_evidence_is_not_full_coverage(self):
        rows = []
        for split in ('dev', 'evaluation'):
            rows.extend([
                dict(split=split, expected=['a','b'], retrieved=['a'], recall=.5, rr=1, ms=2),
                dict(split=split, expected=[], retrieved=['c'], recall=None, rr=0, ms=4),
            ])
        result = comparison.metrics(rows)['evaluation']
        self.assertEqual(result['mean_paragraph_recall_at_3'], .5)
        self.assertEqual(result['all_required_evidence_at_3'], 0)
        self.assertEqual(result['unanswerable_with_candidates'], 1)
        self.assertEqual(result['mean_query_ms'], 3)


if __name__ == '__main__':
    unittest.main()
