from rag.bm25_loader import BM25Retriever
from rag.local_llm import run_local_llm
import json

class LocalRAG:
    def __init__(self):
        self.retriever = BM25Retriever()

    def ask(self, query):
        passages = self.retriever.search(query)

        context = "\n\n".join(
            [f"[{p['id']}] {p['text']}" for p in passages]
        )

        prompt = f"""
You are a compliance officer.
Use ONLY the following retrieved policies to answer.

Policies:
{context}

User question:
{query}

Return response strictly in JSON:
{{
  "allowed": true/false,
  "violations": ["..."],
  "explanation": "...",
  "evidence_passages": ["id1", "id2"]
}}
"""

        out = run_local_llm(prompt)
        try:
            # More robust JSON extraction
            import re
            m = re.search(r"\{.*\}", out, re.S)
            if m:
                clean_out = m.group(0)
                return json.loads(clean_out)
            
            # Fallback for clean markdown
            clean_out = out.strip()
            if clean_out.startswith("```json"):
                clean_out = clean_out[7:]
            if clean_out.startswith("```"):
                 clean_out = clean_out[3:]
            if clean_out.endswith("```"):
                clean_out = clean_out[:-3]
            
            return json.loads(clean_out)
        except Exception as e:
            print(f"JSON Parse Error: {e} | Raw: {out}")
            return {"allowed": False, "violations": ["LLM parse error"], "explanation": out}
