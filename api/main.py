from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import json

app = FastAPI()

class Rec(BaseModel):
    sku: str
    base_price: Optional[float] = None
    proposed_price: float
    confidence: float
    approved: bool
    violations: List[str] = []
    explanation: str = ''
    timestamp: Optional[str] = None

# naive storage for demo
RECS = []

@app.post('/recommendation')
async def post_rec(rec: Rec):
    RECS.append(rec.dict())
    # keep only last 1000
    if len(RECS) > 1000:
        RECS.pop(0)
    return {'status': 'ok'}

@app.get('/recommendations')
async def list_recs(limit: int = 100):
    return RECS[-limit:]

@app.get('/')
async def root():
    return {'msg': 'Dynamic Pricing Engine API', 'endpoints': ['/recommendations', '/recommendation']}
