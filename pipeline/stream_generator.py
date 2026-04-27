"""stream_generator.py
Simulates a real-time data stream by writing demand and competitor signals to a file.
"""
import json
import time
import random
import os
from pathlib import Path

# Config
DATA_DIR = Path("data")
CATALOG_FILE = DATA_DIR / "catalog.csv"
STREAM_FILE = DATA_DIR / "stream_sample.jsonl"
INTERVAL = 2.0  # seconds

def load_catalog():
    import csv
    if not CATALOG_FILE.exists():
        # Create a dummy catalog if it doesn't exist for demo safety
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(CATALOG_FILE, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["sku", "base_price", "cost", "stock"])
            writer.writeheader()
            writer.writerow({"sku": "SKU_001", "base_price": 100.0, "cost": 70.0, "stock": 50})
            writer.writerow({"sku": "SKU_002", "base_price": 50.0, "cost": 30.0, "stock": 200})
        
    skus = []
    with open(CATALOG_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["base_price"] = float(row["base_price"])
            row["cost"] = float(row["cost"])
            row["stock"] = int(row["stock"])
            skus.append(row)
    return skus

def main():
    print(f"Starting stream generator... Interval: {INTERVAL}s")
    skus = load_catalog()
    
    # Ensure stream file is fresh
    if STREAM_FILE.exists():
        try:
            # On Windows, os.remove() fails if another process (like the pipeline) is reading it.
            # Opening in 'w' mode and closing is safer as it truncates the file.
            open(STREAM_FILE, "w").close()
        except PermissionError:
            print(f"⚠️ Could not truncate {STREAM_FILE} (locked by another process). Appending instead.")

    try:
        while True:
            # Pick a random SKU to update or update all? 
            # Real-time systems usually receive updates one by one.
            s = random.choice(skus)
            
            event = {
                "sku": s["sku"],
                "base_price": s["base_price"],
                "cost": s["cost"],
                "stock": s["stock"],
                "views_5m": random.randint(10, 500),
                "orders_15m": random.randint(0, 50),
                "avg_comp_price": round(s["base_price"] * random.uniform(0.9, 1.1), 2),
                "timestamp": time.time()
            }
            
            with open(STREAM_FILE, "a") as f:
                f.write(json.dumps(event) + "\n")
            
            print(f"Generated event for {s['sku']}: Price {event['avg_comp_price']}")
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print("Stream generator stopped.")

if __name__ == "__main__":
    main()
