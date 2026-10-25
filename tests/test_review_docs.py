"""Deterministic checks for the specific contradictory review statements."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class ReviewDocs(unittest.TestCase):
    def test_current_capability_and_historical_counts_are_explicit(self):
        cases=[('README.md','产品尚未接入 RAG',False),
               ('README.md','初始值',True),
               ('docs/PRD-v0.4.md','原版本结果',True),
               ('ARCHITECTURE.md','(not integrated)',False),
               ('docs/历史证据检索-使用说明-v0.2.md','当时',True),
               ('docs/PRD-v0.4.md','最坏',True)]
        for name,phrase,expected in cases:
            with self.subTest(file=name):
                self.assertEqual(phrase in (ROOT/name).read_text(),expected)


if __name__=='__main__':unittest.main()
