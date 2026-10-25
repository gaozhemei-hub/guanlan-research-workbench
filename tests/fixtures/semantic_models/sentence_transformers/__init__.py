"""Fake models for running the real worker offline in CI. No model files/network."""
import json
import os


class Matrix(list):
    def __matmul__(self, vector):
        return [sum(a*b for a,b in zip(row,vector)) for row in self]


class Tokenizer:
    def __call__(self, text, pair=None, **kwargs):
        size=len(text)+2 if pair is None else len(text)+len(pair)+3
        return {'input_ids':list(range(size))}


class Base:
    def __init__(self, name, **kwargs):
        with open(os.environ['FAKE_MODEL_LOG'],'a') as log:
            log.write(json.dumps({'class':type(self).__name__,'name':name,'kwargs':kwargs})+'\n')
        failure=os.environ.get('FAKE_MODEL_FAILURE')
        if failure=='missing':raise OSError('private third-party detail must not escape')
        if failure=='other':raise RuntimeError('private third-party detail must not escape')
        self.tokenizer=Tokenizer()
        self.max_seq_length=512


class SentenceTransformer(Base):
    def encode(self, texts, **kwargs):
        return Matrix([[1.0, (sum(map(ord,text)) % 101)/101, len(text)/1000] for text in texts])


class CrossEncoder(Base):
    def predict(self, pairs, **kwargs):
        return [len(set(a)&set(b))/max(len(set(a)|set(b)),1) for a,b in pairs]
