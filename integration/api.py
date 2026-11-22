# -*- coding: utf-8 -*-
"""
FastAPI service exposing the integration pipeline to the backend.

    uvicorn integration.api:app --host 0.0.0.0 --port 8000

POST /analyze  {"text": "...", "asking_total_price": 1500000}
    -> the final JSON from integration.pipeline.analyze_ad
GET  /health
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from pydantic import BaseModel

from integration.pipeline import analyze_ad

app = FastAPI(title="Barter Platform AI", version="1.0.0")


class AnalyzeRequest(BaseModel):
    text: str
    asking_total_price: float | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    return analyze_ad(req.text, asking_total_price=req.asking_total_price)
