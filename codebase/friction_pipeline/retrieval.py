import math
from collections import Counter, defaultdict

from .text import tokens, cosine


class TranscriptIndex:
    def __init__(self, segments):
        self.segments = segments
        docs = [Counter(tokens(s["text"])) for s in segments]
        document_frequency = Counter(word for doc in docs for word in doc)
        self.idf = {word: math.log((1 + len(docs)) / (1 + count)) + 1 for word, count in document_frequency.items()}
        self.vectors = [self._vector(doc) for doc in docs]

    def _vector(self, counts):
        return Counter({word: count * self.idf.get(word, 1.0) for word, count in counts.items()})

    def search(self, query, limit=3):
        vector = self._vector(Counter(tokens(query)))
        ranked = sorted(((cosine(vector, doc), segment) for doc, segment in zip(self.vectors, self.segments)), reverse=True, key=lambda x: x[0])
        return [{**segment, "score": round(score, 4)} for score, segment in ranked[:limit]]

