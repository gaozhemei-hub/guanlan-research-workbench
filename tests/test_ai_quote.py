import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))
import ai

TEXT = '标题\n\n作者认为**某地区**的居民贷款增速连续两个月回升。\n\n另一段。'
def sug(quote, segment=2):
    return {'suggestions': [{'node': 'financial', 'segment': segment, 'quote': quote, 'claim': 'c', 'question': 'q', 'counter': 'c', 'keywords': 'k'}]}

class QuoteMatch(unittest.TestCase):
    def test_exact_quote_passes(self):
        ai.validate(sug('作者认为**某地区**的居民贷款增速'), TEXT)
    def test_quote_without_bold_markers_passes(self):
        ai.validate(sug('作者认为某地区的居民贷款增速'), TEXT)
    def test_quote_in_wrong_segment_still_fails(self):
        with self.assertRaises(ValueError): ai.validate(sug('作者认为某地区的居民贷款增速', 3), TEXT)
    def test_reworded_quote_still_fails(self):
        with self.assertRaises(ValueError): ai.validate(sug('作者认为某地区居民贷款增速回升'), TEXT)
    def test_markers_only_quote_fails(self):
        with self.assertRaises(ValueError): ai.validate(sug('****'), TEXT)

if __name__ == '__main__':
    unittest.main()
