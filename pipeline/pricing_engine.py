"""pricing_engine.py
Core logic for calculating dynamic prices and performing policy checks.
"""
import json
import sys
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

# Add the root directory to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from online_model import OnlinePricingModel
from engine.violation_checker import ViolationChecker

# Initialize components
model = OnlinePricingModel()
policy_checker = ViolationChecker()

def calculate_price(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Takes a data row and returns a pricing recommendation.
    """
    current_price = row.get('base_price', 1.0)
    cost = row.get('cost', 0.0)
    min_margin = 0.1  # 10% minimum margin

    # Simple optimization: try prices from -10% to +10%
    candidates = [round(current_price * (1 + x / 100), 2) for x in range(-10, 11)]
    best = None
    
    for p in candidates:
        if p < cost * (1 + min_margin):
            continue
            
        # Build feature vector for model
        fv = {
            'sku': row['sku'],
            'price': p,
            'cost': cost,
            'views_5m': row.get('views_5m', 0),
            'orders_15m': row.get('orders_15m', 0),
            'avg_comp_price': row.get('avg_comp_price', p),
            'stock': row.get('stock', 0)
        }
        
        score = model.predict(fv)  # Prob of conversion
        expected_revenue = score * p
        
        if best is None or expected_revenue > best['rev']:
            best = {'price': p, 'rev': expected_revenue, 'score': score}

    if best is None:
        best = {'price': current_price, 'rev': 0, 'score': 0}

    # RAG policy check
    rag_result = policy_checker.check(
        sku=row['sku'], 
        cost=cost, 
        proposed=best['price'], 
        demand=row.get('orders_15m', 0), 
        competitor=row.get('avg_comp_price', 0)
    )
    
    recommendation = {
        'sku': row['sku'],
        'base_price': current_price,
        'proposed_price': best['price'],
        'confidence': round(best['score'], 4),
        'approved': rag_result['allowed'],
        'violations': rag_result.get('violations', []),
        'explanation': rag_result.get('rag_info', {}).get('explanation', ''),
        'timestamp': datetime.utcnow().isoformat()
    }
    
    return recommendation
