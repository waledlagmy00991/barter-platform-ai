#!/usr/bin/env python3
"""Run local regression checks and a bounded in-process concurrency smoke test."""
import collections
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))

def main():
    completed=subprocess.run([sys.executable,'-m','pytest','tests/','integration/tests/','-q'],cwd=ROOT,capture_output=True,text=True)
    print(completed.stdout)
    if completed.returncode:
        print(completed.stderr,file=sys.stderr)
        raise SystemExit(completed.returncode)
    match=re.search(r'(\d+) passed in ([\d.]+)s',completed.stdout)
    if not match:
        raise RuntimeError('Unable to parse successful regression result')
    from fastapi.testclient import TestClient
    from integration.api import app
    from vision.integrity_guard import verify_snapshot
    verify_snapshot()
    client=TestClient(app)
    payload={'text':'عندي ٣٠ طن حديد تسليح جديد في العاشر من رمضان','asking_total_price':1900000}
    assert client.post('/analyze',json=payload).status_code==200
    def one(i):
        start=time.perf_counter()
        response=client.post('/analyze',json=payload)
        return response.status_code,time.perf_counter()-start
    start=time.perf_counter()
    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes=list(pool.map(one,range(32)))
    elapsed=time.perf_counter()-start
    assert {s for s,t in outcomes}<={200,429}
    verify_snapshot()
    paths=['integration/api.py','integration/pipeline.py','pricing/predict.py','tests/test_api_safety.py','tests/test_integration.py','integration/run_local_safety_check.py','chatbot/chatbot.py','chatbot/build_index.py','chatbot/generate_ads.py','tests/test_rag_safety.py']
    result=dict(status='LOCAL_REGRESSION_ONLY',production_ready=False,model_metrics_computed=False,
        test_command='python -m pytest tests/ integration/tests/ -q',tests_passed=int(match[1]),pytest_seconds=float(match[2]),
        local_asgi_concurrency_smoke=dict(requests=32,client_workers=4,inference_capacity=2,
            status_counts=dict(collections.Counter(str(s) for s,t in outcomes)),
            elapsed_seconds=round(elapsed,4),median_request_seconds=round(statistics.median(t for s,t in outcomes),4),
            caveat='In-process warmed synthetic requests. Not a network, adversarial security, production capacity or model-quality benchmark.'),
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        environment={p:importlib.metadata.version(p) for p in ['fastapi','pydantic','starlette','httpx','spacy','xgboost','numpy','pandas','ultralytics','torch','pytest']})
    (ROOT/'integration/safety_results.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
