import chromadb
import hashlib
import re
import math
import os
from chromadb import Documents, EmbeddingFunction, Embeddings
from typing import List, Dict


# ✅ Custom Embedding — internet ছাড়া কাজ করে
class TFIDFEmbeddingFunction(EmbeddingFunction):

    def __call__(self, input: Documents) -> Embeddings:
        return [self._vectorize(doc) for doc in input]

    def _vectorize(self, text: str, dim: int = 256) -> List[float]:
        words  = re.findall(r'\w+', text.lower())
        counts = {}
        for w in words:
            counts[w] = counts.get(w, 0) + 1

        total  = len(words) or 1
        vector = [0.0] * dim

        for word, count in counts.items():
            tf  = count / total
            idx = int(hashlib.md5(word.encode()).hexdigest(), 16) % dim
            vector[idx] += tf

        mag = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / mag for v in vector]


class DocumentRetriever:

    def __init__(self, persist_dir: str = "./chroma_db"):
        os.makedirs(persist_dir, exist_ok=True)
        self._embed_fn  = TFIDFEmbeddingFunction()
        self.client     = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name               = "legal_docs",
            embedding_function = self._embed_fn,
            metadata           = {"hnsw:space": "cosine"}
        )

    def index_document(self, doc_id: str, pages: list) -> int:
        chunks_added = 0
        for page in pages:
            if not page.get("text") or len(page["text"]) < 20:
                continue
            chunks = self._chunk_text(page["text"])
            for i, chunk in enumerate(chunks):
                chunk_id = hashlib.md5(
                    f"{doc_id}_p{page['page']}_c{i}".encode()
                ).hexdigest()

                existing = self.collection.get(ids=[chunk_id])
                if existing["ids"]:
                    continue

                self.collection.add(
                    documents = [chunk],
                    ids       = [chunk_id],
                    metadatas = [{
                        "doc_id": doc_id,
                        "page"  : page["page"],
                        "chunk" : i
                    }]
                )
                chunks_added += 1
        return chunks_added

    def retrieve(self, query: str, n_results: int = 5) -> List[Dict]:
        total = self.collection.count()
        if total == 0:
            return []
        results = self.collection.query(
            query_texts = [query],
            n_results   = min(n_results, total)
        )
        passages  = []
        docs      = results["documents"][0]
        metas     = results["metadatas"][0]
        distances = results["distances"][0]
        for doc, meta, dist in zip(docs, metas, distances):
            passages.append({
                "text"      : doc,
                "page"      : meta.get("page"),
                "doc_id"    : meta.get("doc_id"),
                "relevance" : round(max(0.0, 1 - dist), 3)
            })
        return passages

    def get_stats(self) -> dict:
        return {"total_chunks": self.collection.count()}

    def _chunk_text(self, text: str, size: int = 400, overlap: int = 40) -> List[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks    = []
        current   = []
        cur_len   = 0
        for s in sentences:
            words = s.split()
            if cur_len + len(words) > size and current:
                chunks.append(" ".join(current))
                current = current[-overlap:] + words
                cur_len = len(current)
            else:
                current.extend(words)
                cur_len += len(words)
        if current:
            chunks.append(" ".join(current))
        return [c for c in chunks if len(c) > 20]