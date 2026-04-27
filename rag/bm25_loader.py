import os
import re
from rank_bm25 import BM25Okapi
from nltk.tokenize import word_tokenize
import nltk

# Ensure nltk resources
import nltk
import os
local_nltk = os.path.abspath("nltk_data")
nltk.data.path.append(local_nltk)

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    print(f"Downloading nltk punkt to {local_nltk}...")
    nltk.download('punkt', download_dir=local_nltk)

try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    print(f"Downloading nltk punkt_tab to {local_nltk}...")
    nltk.download('punkt_tab', download_dir=local_nltk)

class BM25Retriever:
    def __init__(self, policy_path="docs/policies"):
        self.docs = []
        self.tokens = []
        self.ids = []

        if not os.path.exists(policy_path):
             print(f"Policy path {policy_path} does not exist.")
             self.bm25 = None
             return

        for filename in os.listdir(policy_path):
            if filename.endswith(".md"):
                file_path = os.path.join(policy_path, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
                paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
                for i, p in enumerate(paras):
                    pid = f"{filename}#p{i}"
                    self.ids.append(pid)
                    self.docs.append(p)
                    self.tokens.append(word_tokenize(p.lower()))

        if self.tokens:
            self.bm25 = BM25Okapi(self.tokens)
        else:
            self.bm25 = None

    def search(self, query, top_k=5):
        if not self.bm25:
             return []
        q_tokens = word_tokenize(query.lower())
        scores = self.bm25.get_scores(q_tokens)

        ranked = sorted(
            zip(scores, self.docs, self.ids), 
            key=lambda x: x[0], 
            reverse=True
        )[:top_k]

        return [
            {"id": doc_id, "score": float(score), "text": text}
            for score, text, doc_id in ranked
        ]
