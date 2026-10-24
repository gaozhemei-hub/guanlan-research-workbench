import unittest
import json
from server.retrieval import bounded_chunks, retrieve_selected
from tests.test_deploy import Server


class RequestRetrieval(unittest.TestCase):
    def test_http_endpoint_and_origin_boundary(self):
        with Server() as server:
            body={'query':'黄金', 'materials':[{'id':'one','text':'黄金库存待核实。'}]}
            self.assertEqual(server.req('/api/retrieve', 'POST', origin='http://evil.example', body=body)[0], 403)
            origin=f'http://127.0.0.1:{server.port}'
            status, headers, raw = server.req('/api/retrieve', 'POST', origin=origin, body=body)
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(raw)['hits'][0]['source'], 'one')
            self.assertEqual(headers['Cache-Control'], 'no-store')
            self.assertEqual(server.req('/api/retrieve', 'POST', origin=origin, body={})[0], 400)

    def test_long_text_preserves_offsets_and_complete_paragraph(self):
        text = '黄金🙂' * 900
        chunks = list(bounded_chunks(text, 31))
        self.assertEqual(''.join(c[3] for c in chunks), text)
        self.assertTrue(all(len(c[3]) <= 31 and text[c[1]:c[2]] == c[3] for c in chunks))
        self.assertEqual(len({c[0] for c in chunks}), 1)

    def test_token_counter_budget_and_impossible_budget(self):
        count = lambda text: 2 + len(text)*2
        chunks = list(bounded_chunks('黄金白银'*50, 20, count))
        self.assertTrue(all(count(c[3]) <= 20 for c in chunks))
        with self.assertRaises(ValueError):
            list(bounded_chunks('金', 1, count))

    def test_request_does_not_retain_previous_material(self):
        a = retrieve_selected({'query':'黄金', 'materials':[{'id':'one','text':'黄金🙂库存待核实。'}]})
        b = retrieve_selected({'query':'黄金', 'materials':[{'id':'two','text':'白银工业需求待核实。'}]})
        self.assertEqual(a['hits'][0]['source'], 'one')
        self.assertEqual(b['hits'], [])
        self.assertEqual(a['scope'], 'request-memory-only')

    def test_request_validation(self):
        for payload in ({}, {'query':'黄金','materials':[]},
                        {'query':'黄金','materials':[{'id':'a','text':'金'}]*2},
                        {'query':'黄金','materials':[{'id':'a','text':'金'*100001}]}):
            with self.assertRaises(ValueError):
                retrieve_selected(payload)


if __name__ == '__main__':
    unittest.main()
