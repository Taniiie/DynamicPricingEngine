"""pathway_pipeline.py
Main streaming pipeline: ingest simulated Kafka topics (or Pathway demo streams), compute features, run pricing logic and policy check, publish recommendations.
"""
import os
import time
import json
from datetime import datetime
from typing import Dict, Any

import pathway as pw
from engine.violation_checker import ViolationChecker
from online_model import OnlinePricingModel

# Configuration
KAFKA_BOOTSTRAP = os.getenv('KAFKA_BOOTSTRAP', 'localhost:9092')
# In a real scenario, we would read from Kafka topics:
# orders = pw.io.kafka.read(topic="orders", bootstrap_servers=KAFKA_BOOTSTRAP, value_columns=["sku", "price", "quantity"], format="json")
# For this demo, we will use a file-based stream or just a simple python loop since establishing a real Kafka connection in a dev env without Docker up might fail.
# However, the requirement asks for pathway_pipeline.py. We will make it runnable by reading the simulated jsonl file as a stream.

SIMULATED_STREAM_FILE = 'configs/features_stream.jsonl'

# Init components
model = OnlinePricingModel()
policy_checker = ViolationChecker()


def build_feature_vector(row: Dict[str, Any], price: float) -> Dict[str, Any]:
    # Basic features; expand as needed
    return {
        'sku': row['sku'],
        'price': price,
        'cost': row.get('cost', 0.0),
        'views_5m': row.get('views_5m', 0),
        'orders_15m': row.get('orders_15m', 0),
        'avg_comp_price': row.get('avg_comp_price', price),
        'stock': row.get('stock', 0)
    }


def pricing_logic(row: Dict[str, Any]):
    current_price = row.get('base_price', 1.0)
    cost = row.get('cost', 0.0)
    min_margin = row.get('min_margin', 0.1)

    candidates = [round(current_price * (1 + x / 100), 2) for x in range(-10, 11)]
    best = None
    for p in candidates:
        if p < cost * (1 + min_margin):
            continue
        fv = build_feature_vector(row, price=p)
        score = model.predict(fv)  # expected conversion prob or score
        expected_revenue = score * p
        if best is None or expected_revenue > best['rev']:
            best = {'price': p, 'rev': expected_revenue, 'score': score}

    if best is None:
        # Fallback if no valid price found (e.g. cost too high)
        best = {'price': current_price, 'rev': 0, 'score': 0}

    # RAG policy check
    rag = policy_checker.check(
        sku=row['sku'], 
        cost=cost, 
        proposed=best['price'], 
        demand=row.get('orders_15m', 0), 
        competitor=row.get('avg_comp_price', 0)
    )
    rec = {
        'sku': row['sku'],
        'base_price': current_price,
        'proposed_price': best['price'],
        'confidence': best['score'],
        'approved': rag['allowed'],
        'violations': rag.get('violations', []),
        'explanation': json.dumps(rag.get('rag_info', {})), # Store full info debug
        'timestamp': datetime.utcnow().isoformat()
    }
    return rec


def main():
    print('Starting pipeline (demo mode) ...')
    
    # In a full Pathway app we would define a table:
    # t = pw.io.fs.read(SIMULATED_STREAM_FILE, format="json", mode="streaming")
    # result = t.map(pricing_logic)
    # pw.io.kafka.write(result, topic="price_recommendations", bootstrap_servers=KAFKA_BOOTSTRAP, format="json")
    # pw.run()

    # For the hackathon starter template to be immediately runnable without Docker up:
    if not os.path.exists(SIMULATED_STREAM_FILE):
        print('No features file found:', SIMULATED_STREAM_FILE)
        print('Run simulate_data.py to generate streaming feature snapshots.')
        return

    print(f"Reading from {SIMULATED_STREAM_FILE} ...")
    # Naive tailing for demo purposes (python-native)
    # In production this loop is replaced by `pw.run()` with connector definitions.
    try:
        with open(SIMULATED_STREAM_FILE, 'r') as fh:
            # Go to end or start? For demo we just process what's there and then tail
            # But simulate_data.py overwrites or appends? It opens with 'w' in the provided code, so it resets.
            # We'll just read line by line.
            while True:
                line = fh.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                
                try:
                    row = json.loads(line)
                    rec = pricing_logic(row)
                    if rec:
                        print('Recommendation:', json.dumps(rec))
                        # Write to file for Streamlit dashboard
                        with open('configs/recommendations.jsonl', 'a') as f_out:
                            f_out.write(json.dumps(rec) + '\n')
                except json.JSONDecodeError:
                    pass
    except KeyboardInterrupt:
        print("Stopping pipeline.")

if __name__ == '__main__':
    main()
