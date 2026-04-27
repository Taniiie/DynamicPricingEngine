"""policy_checker.py
Simple RAG policy checker using Pathway Document Store + LLM xPack or OpenAI fallback.
This module exposes `PolicyChecker.check_policy(sku, proposed_price, context)` which returns
{"allowed": bool, "violations": [...], "explanation": "..."}
"""
import os
from typing import Dict, Any
import requests
import json
from pathlib import Path

from rag.local_llm import run_local_llm

class PolicyChecker:
    def __init__(self):
        # load local policy files into memory for basic retrieval
        self.policies = []
        if POLICIES_DIR.exists():
            for f in POLICIES_DIR.glob('*'):
                try:
                    self.policies.append({'id': f.name, 'text': f.read_text(encoding='utf-8')})
                except Exception as e:
                    print(f"Error reading policy {f}: {e}")

    def retrieve_relevant(self, sku: str, proposed_price: float, context: Dict[str, Any]):
        # naive retrieval: return all policies containing keywords. Replace with vector+BM25 retrieval.
        hits = []
        # simple keyword checking
        for p in self.policies:
            if any(word in p['text'].lower() for word in ['price', 'margin', 'map', 'advertis']):
                hits.append(p)
        return hits[:5]

    def call_llm(self, prompt: str) -> str:
        # Using Local Ollama instead of OpenAI
        return run_local_llm(prompt)

    def check_policy(self, sku: str, proposed_price: float, context: Dict[str, Any]) -> Dict[str, Any]:
        passages = self.retrieve_relevant(sku, proposed_price, context)
        prompt = f"SKU: {sku}\nProposed price: {proposed_price}\nContext: {json.dumps(context)}\n\nPolicies:\n"
        for p in passages:
            prompt += f"--- {p['id']} ---\n{p['text']}\n\n"

        prompt += "\nReturn JSON with fields: allowed (bool), violations (list), suggested_price (number|null), explanation (string)."

        out = self.call_llm(prompt)
        try:
            # clean potential markdown fences
            out_clean = out.strip().replace('```json', '').replace('```', '')
            parsed = json.loads(out_clean)
        except Exception:
            # LLM returned text — attempt to extract JSON substring
            import re
            m = re.search(r"\{.*\}", out, re.S)
            if m:
                try:
                    parsed = json.loads(m.group(0))
                except:
                     parsed = {'allowed': True, 'violations': [], 'explanation': 'Could not parse LLM output (nested).'}
            else:
                parsed = {'allowed': True, 'violations': [], 'explanation': 'Could not parse LLM output (raw).'}

        # ensure keys exist
        parsed.setdefault('allowed', True)
        parsed.setdefault('violations', [])
        parsed.setdefault('explanation', '')
        parsed.setdefault('suggested_price', None)
        return parsed
