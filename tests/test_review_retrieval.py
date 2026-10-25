"""Deterministic review regressions, no real models or network."""
import unittest
from unittest.mock import patch
from server import retrieval, semantic


def payload(text,query='库存',method='lexical'):
    return {'query':query,'method':method,'materials':[{'id':'source','text':text}]}


class LexicalReview(unittest.TestCase):
    def test_single_han(self):
        text='本季度铜价上涨，金价回落，银需求转弱。'
        for query in ('铜','金','银'):
            with self.subTest(query=query):self.assertTrue(retrieval.retrieve_selected(payload(text,query))['hits'])

    def test_unicode_normalization_preserves_original_offsets(self):
        text='🙂本期２０２６年ＥＴＦ观察，Ü 和 Straße 为原文。'
        for query in ('２０２６','2026','ＥＴＦ','etf','Ü','ü','STRASSE'):
            with self.subTest(query=query):
                hits=retrieval.retrieve_selected(payload(text,query))['hits']
                self.assertTrue(hits)
                for hit in hits:self.assertEqual(text[hit['start']:hit['end']],hit['text'])

    def test_empty_terms_rejected_with_actionable_message(self):
        for query in ('！？','🙂','👩\u200d🔬'):
            with self.subTest(query=query),self.assertRaisesRegex(ValueError,'没有可用于词法检索的词'):
                retrieval.retrieve_selected(payload('黄金库存',query))

    def test_boundary_bigram_really_exists_in_a_returned_chunk(self):
        text='甲'*599+'库存'+'乙'*50
        hits=retrieval.retrieve_selected(payload(text))['hits']
        self.assertTrue(any('库存' in hit['text'] for hit in hits))
        for hit in hits:self.assertEqual(text[hit['start']:hit['end']],hit['text'])

    def test_overlapping_chunks_cover_text_and_deduplicate(self):
        text='甲'*590+'库存'+'乙'*800
        index=retrieval.Index();self.addCleanup(index.close)
        # The product chunker is part of the regression contract.
        chunker=getattr(retrieval,'lexical_chunks',retrieval.bounded_chunks)
        chunks=list(chunker(text))
        self.assertTrue(any(a[2]>b[1] for a,b in zip(chunks,chunks[1:])))
        covered=set()
        for _,start,end,chunk in chunks:
            self.assertLessEqual(len(chunk),600);self.assertEqual(text[start:end],chunk)
            covered.update(range(start,end))
        self.assertEqual(covered,set(range(len(text))))
        hits=retrieval.retrieve_selected(payload(text))['hits']
        self.assertEqual(len(hits),1)
        self.assertIn('库存',hits[0]['text'])

    def test_adjacent_windows_keep_distinct_evidence(self):
        text='甲'*100+'库存下降'+'甲'*500+'现金流转负'+'乙'*400
        hits=retrieval.retrieve_selected(payload(text,'库存 现金流'))['hits']
        self.assertTrue(any('库存下降' in h['text'] for h in hits))
        self.assertTrue(any('现金流转负' in h['text'] for h in hits))
        for hit in hits:self.assertEqual(text[hit['start']:hit['end']],hit['text'])

    def test_match_crossing_overlap_edge_is_not_dropped(self):
        text='cash '*20+'甲'*498+'alpha'+'乙'*300
        hits=retrieval.retrieve_selected(payload(text,'cash alpha'))['hits']
        self.assertTrue(any('alpha' in h['text'] for h in hits))

    def test_non_string_method_is_validated(self):
        for method in (['x'], {'x':1},None):
            with self.subTest(method=method),self.assertRaisesRegex(ValueError,'不支持的检索方式'):
                retrieval.retrieve_selected(payload('黄金',method=method))

    def test_unpaired_surrogate_has_safe_chinese_error(self):
        for field in ('id','text'):
            p=payload('黄金');p['materials'][0][field]='bad\ud800'
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'材料含无法编码的字符'):
                retrieval.retrieve_selected(p)

    def test_101_paragraphs_rejected_before_worker(self):
        with patch.object(semantic,'retrieve',return_value={'hits':[]}) as worker:
            with self.assertRaisesRegex(ValueError,'段落.*100|100.*段'):
                retrieval.retrieve_selected(payload('\r\n'.join(['黄金库存']*101),method='vector'))
            worker.assert_not_called()


if __name__=='__main__':unittest.main()
