from rag.local_rag import LocalRAG
from engine.rule_engine import rule_engine

class ViolationChecker:
    def __init__(self):
        self.rag = LocalRAG()

    def check(self, sku, cost, proposed, demand, competitor):
        # Step 1: Hard rules
        hard = rule_engine(sku, cost, proposed, demand, competitor)

        # Step 2: RAG policies
        rag_query = f"Check if proposed price {proposed} for {sku} violates any pricing policies."
        rag_result = self.rag.ask(rag_query)

        rag_violations = rag_result.get("violations", [])
        if isinstance(rag_violations, str):
            rag_violations = [rag_violations]
            
        all_violations = hard + rag_violations

        return {
            "allowed": len(all_violations) == 0,
            "violations": all_violations,
            "policy_evidence": rag_result.get("evidence_passages", []),
            "rag_info": rag_result,
        }
