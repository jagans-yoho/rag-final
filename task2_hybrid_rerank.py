import re
import chromadb
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

chroma_client = chromadb.PersistentClient(path="./chroma_week5")
collection = chroma_client.get_or_create_collection(name="enterprise_docs")

data = collection.get()
doc_ids = data["ids"]
docs = data["documents"]
metas = data["metadatas"]

def tokenize(text: str):
    return re.findall(r"\w+", text.lower())

bm25 = BM25Okapi([tokenize(d) for d in docs])
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def bm25_search(query: str, k: int = 3):
    scores = bm25.get_scores(tokenize(query))
    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
    return [docs[i] for i in ranked]

def vector_search(query: str, k: int = 3):
    res = collection.query(query_texts=[query], n_results=min(k, len(docs)))
    return res["documents"][0] if res["documents"] else []

def hybrid_search(query: str, top_n: int = 20):
    b_scores = bm25.get_scores(tokenize(query))
    b_ranked = [docs[i] for i in sorted(range(len(b_scores)), key=lambda i: b_scores[i], reverse=True)]
    v_ranked = vector_search(query, k=len(docs))

    rrf = {}
    for rank, text in enumerate(b_ranked):
        rrf[text] = rrf.get(text, 0.0) + 0.5 * (1.0 / (60.0 + rank + 1))
    for rank, text in enumerate(v_ranked):
        rrf[text] = rrf.get(text, 0.0) + 0.5 * (1.0 / (60.0 + rank + 1))

    sorted_texts = sorted(rrf.items(), key=lambda x: x[1], reverse=True)
    return [t for t, _ in sorted_texts[:top_n]]

def hybrid_rerank_search(query: str, k: int = 5):
    candidates = hybrid_search(query, top_n=min(20, len(docs)))
    pairs = [[query, c] for c in candidates]
    scores = reranker.predict(pairs)
    reranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
    return [c for c, _ in reranked[:k]]

test_queries = [
    ("What does Policy HR-204 say about annual leave?", "HR-204"),
    ("Allowance limit under TRV-901 for metro cities?", "TRV-901"),
    ("Rules in ETH-501 regarding freelancing on laptops?", "ETH-501"),
    ("Notice period under OFF-109 protocol?", "OFF-109"),
    ("Executive bonus percentage in BON-77?", "BON-77"),
    ("How many days can unused leave be carried forward?", "10 days"),
    ("Maximum hotel room rate per night?", "4,000"),
    ("What is EMP101 remaining leave balance?", "EMP101"),
    ("Which department does EMP103 work in?", "EMP103"),
    ("When does annual salary revision cycle take place?", "April")
]

if __name__ == "__main__":
    hits = {"BM25": 0, "Vector": 0, "Hybrid": 0, "Hybrid+Rerank": 0}
    for q, keyword in test_queries:
        if any(keyword in d for d in bm25_search(q, k=3)):
            hits["BM25"] += 1
        if any(keyword in d for d in vector_search(q, k=3)):
            hits["Vector"] += 1
        if any(keyword in d for d in hybrid_search(q, top_n=3)):
            hits["Hybrid"] += 1
        if any(keyword in d for d in hybrid_rerank_search(q, k=3)):
            hits["Hybrid+Rerank"] += 1

    print("\n Task 2 Benchmark Output ")
    print(f"Hit rate @3: BM25 {hits['BM25']}/10 | Vector {hits['Vector']}/10 | Hybrid {hits['Hybrid']}/10 | Hybrid + rerank {hits['Hybrid+Rerank']}/10")