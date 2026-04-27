import pathway as pw
import os
import json
import sys
import time
from pathlib import Path

# Add the root directory to sys.path to allow importing from 'pipeline'
sys.path.append(str(Path(__file__).parent.parent))

from pricing_engine import calculate_price

# Config
STREAM_FILE = "data/stream_sample.jsonl"
REC_FILE = "configs/recommendations.jsonl"

def main():
    print("🚀 Starting Real-Time Pricing Pipeline...")
    
    if not os.path.exists(STREAM_FILE):
        print(f"⚠️ Warning: {STREAM_FILE} not found. Start stream_generator.py first.")
        # Create empty file to allow Pathway to start watching
        os.makedirs(os.path.dirname(STREAM_FILE), exist_ok=True)
        open(STREAM_FILE, "a").close()

    # Pathway Stream Ingestion
    # NOTE: Pathway natively supports Linux and macOS. 
    # For Windows users, we provide a "Demo Fallback" that simulates the pipeline logic.
    
    try:
        # Attempt real Pathway initialization
        table = pw.io.fs.read(
            "data/",
            format="json",
            mode="streaming",
            with_filename=True
        )
        
        # Filter for our specific stream file
        table = table.filter(pw.this.filename == "stream_sample.jsonl")

        # Apply Pricing Logic
        recommendations = table.select(
            rec = pw.apply(calculate_price, pw.this)
        ).flatten("rec")

        # Output to file
        pw.io.jsonlines.write(recommendations, REC_FILE)
        
        print(f"📡 Pathway Pipeline is LIVE (Native Mode). Monitoring {STREAM_FILE}...")
        pw.run()

    except (ImportError, Exception) as e:
        print(f"⚠️ Pathway Native Engine not available or failed: {e}")
        print("💡 Falling back to 'Python-Native Demo Mode' (Tail & Map)...")
        print(f"📡 Monitoring {STREAM_FILE} for new events...")
        
        # Manually tail the file and apply our engine logic
        # This simulates Pathway's behavior for local Windows development
        try:
            with open(STREAM_FILE, "r") as f:
                # Seek to end
                f.seek(0, 2)
                while True:
                    line = f.readline()
                    if not line:
                        time.sleep(0.5)
                        continue
                    
                    try:
                        data = json.loads(line)
                        rec = calculate_price(data)
                        print(f"✨ Recommendation for {rec['sku']}: ${rec['proposed_price']} (Approved: {rec['approved']})")
                        
                        # Write to recommendations file
                        with open(REC_FILE, "a") as out:
                            out.write(json.dumps(rec) + "\n")
                    except Exception as ex:
                        print(f"❌ Error processing event: {ex}")
        except KeyboardInterrupt:
            print("\nPipeline stopped.")

if __name__ == "__main__":
    main()
