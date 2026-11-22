# -*- coding: utf-8 -*-
"""Local development API. Liveness is not production readiness."""
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator
from integration.pipeline import analyze_ad

app = FastAPI(title='Barter Platform AI, development', version='0.2.0-dev')


class BodyLimitMiddleware:
    """Bound request bodies before JSON parsing, including chunked requests."""
    def __init__(self, app, max_bytes=65536):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        chunks=[]
        size=0
        while True:
            message=await receive()
            if message['type']=='http.disconnect':
                return
            chunk=message.get('body',b'')
            size+=len(chunk)
            if size>self.max_bytes:
                response=JSONResponse(status_code=413,content={'detail':'Request body exceeds 65536 bytes'})
                return await response(scope,receive,send)
            chunks.append(chunk)
            if not message.get('more_body',False):
                break
        body=b''.join(chunks)
        delivered=False
        async def replay_receive():
            nonlocal delivered
            if not delivered:
                delivered=True
                return {'type':'http.request','body':body,'more_body':False}
            return await receive()
        await self.app(scope,replay_receive,send)


app.add_middleware(BodyLimitMiddleware)
_INFERENCE_SLOTS = threading.BoundedSemaphore(2)


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    text: StrictStr = Field(min_length=1, max_length=10000)
    asking_total_price: float | None = Field(default=None, gt=0, allow_inf_nan=False, strict=True)

    @field_validator('text')
    @classmethod
    def nonblank_text(cls, value):
        if not value.strip():
            raise ValueError('text must not be blank')
        return value


@app.exception_handler(RequestValidationError)
async def safe_validation_error(request, exc):
    # Do not echo raw input, which can include non-finite values or private text.
    return JSONResponse(status_code=422, content={'detail': [
        {'loc': list(e['loc']), 'type': e['type'], 'msg': e['msg']}
        for e in exc.errors()
    ]})


@app.get('/health')
def health():
    return {'status': 'ok', 'production_ready': False, 'scope': 'liveness_only'}


@app.get('/ready')
def ready():
    return JSONResponse(status_code=503, content={
        'status': 'not_ready', 'production_ready': False,
        'blockers': ['vision_integrity_review_open', 'independent_real_world_validation_incomplete',
                     'deployment_security_and_operations_not_approved'],
    })


@app.post('/analyze')
def analyze(req: AnalyzeRequest):
    if not _INFERENCE_SLOTS.acquire(blocking=False):
        raise HTTPException(status_code=429, detail='Local inference capacity reached', headers={'Retry-After':'1'})
    try:
        return analyze_ad(req.text, asking_total_price=req.asking_total_price)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail='Input cannot be evaluated safely') from exc
    finally:
        _INFERENCE_SLOTS.release()
