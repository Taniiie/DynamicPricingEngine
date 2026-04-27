"""simulate_data.py
Simple simulator to produce streaming `features_stream.jsonl` used by pathway_pipeline.py demo loop.
It reads `configs/catalog.csv` and emits snapshots (one line per sku) containing current base_price, cost, stock, and simulated features.
"""
import csv
import json
import time
import random
from pathlib import Path

OUT = Path('data/stream_sample.jsonl')
CATALOG = Path('data/catalog.csv')


def load_catalog():
    rows = []
    if not CATALOG.exists():
        print(f"Catalog file not found: {CATALOG}")
        return []
    with open(CATALOG, 'r') as fh:
        r = csv.DictReader(fh)
        for row in r:
            row['base_price'] = float(row.get('base_price', 10.0))
            row['cost'] = float(row.get('cost', 5.0))
            row['stock'] = int(row.get('stock', 100))
            rows.append(row)
    return rows


def emit_stream(delay=0.2, rounds=1000):
    skus = load_catalog()
    if not skus:
        print("No SKUs found. Exiting.")
        return

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, 'w') as fh:
        print(f"Simulating data to {OUT}...")
        for i in range(rounds):
            for s in skus:
                row = {
                    'sku': s['sku'],
                    'base_price': s['base_price'],
                    'cost': s['cost'],
                    'stock': s['stock'],
                    'views_5m': random.randint(0, 200),
                    'orders_15m': random.randint(0, 20),
                    'avg_comp_price': float(s['base_price'] * (1 + random.uniform(-0.05, 0.08)))
                }
                fh.write(json.dumps(row) + '\n')
            fh.flush()
            if i % 10 == 0:
                print(f"Round {i}/{rounds} completed.")
            time.sleep(delay)


if __name__ == '__main__':
    emit_stream()
