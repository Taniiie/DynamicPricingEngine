# Demonstration Pipeline Guide

Follow these steps to observe the real-time capabilities of the Dynamic Pricing Engine.

## Prerequisites
- Ensure all dependencies are installed (`pip install -r requirements.txt`).
- **Ollama**: Ensure Ollama is running (`ollama serve`) and you have the `llama3.2` model installed (`ollama pull llama3.2`). The system uses this for Local RAG.

## Step 1: Start the Stream Generator
Open a terminal and run:
```bash
python pipeline/stream_generator.py
```
**Observation**: You will see logs of market events being generated for random SKUs every 2 seconds. These are written to `data/stream_sample.jsonl`.

## Step 2: Start the Pathway Pipeline
Open a **new** terminal and run:
```bash
python pipeline/pipeline_runner.py
```
**Observation**: The pipeline will start monitoring the data file. As soon as a new event arrives, it recalculates the optimal price and checks for policy violations via **Local RAG (Ollama)**. Recommendations are saved to `configs/recommendations.jsonl`.

## Step 3: Launch the Dashboard
Open a **third** terminal and run:
```bash
streamlit run app.py
```
**Observation**:
1.  **Overview Page**: Watch the "Recommendations" and "Policy Violations" metrics update live.
2.  **Price Trends**: Go to "SKU Dashboard" to see the price history for specific items.
3.  **AI Agent**: Ask the assistant "Why was the price for SKU_001 changed?" or "What are the pricing policies?". This uses the local Ollama model.

## Key Demonstration Scenarios

### 1. Real-Time Price Adjustment
Observe how a change in "Avg Comp Price" in the `stream_generator` log immediately results in a new `proposed_price` in the Dashboard.

### 2. Policy Violation Tracking
The `ViolationChecker` uses a hard-coded rule (e.g., minimum margin) and **Local RAG** to block unsafe prices. If a price is too low, it will appear as "Not Approved" in the dashboard with a red highlight.

### 3. RAG-Powered Insights
Use the "AI Agent" tab to query the pricing policies. The system will retrieve the relevant section from `docs/policies/pricing_policy.md` and use Ollama to answer.
