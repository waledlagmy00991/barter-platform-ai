"""Local safety regression tests. Not independent model evaluation."""
import asyncio
import math
import pytest
from fastapi.testclient import TestClient
from integration import api
from integration.pipeline import analyze_ad, parse_quantity, verify_image, detect_condition
from pricing.predict import evaluate_ask, fair_price

client=TestClient(api.app)


def test_body_limit_before_json_parsing():
    response=client.post('/analyze',content=b'x'*65537,headers={'Content-Type':'application/json'})
    assert response.status_code==413


def test_chunked_body_limit_does_not_trust_content_length():
    async def exercise():
        called=False
        async def downstream(scope,receive,send):
            nonlocal called
            called=True
        incoming=iter([
            {'type':'http.request','body':b'x'*40000,'more_body':True},
            {'type':'http.request','body':b'x'*30000,'more_body':False},
        ])
        sent=[]
        async def receive(): return next(incoming)
        async def send(message): sent.append(message)
        middleware=api.BodyLimitMiddleware(downstream)
        await middleware({'type':'http','method':'POST','path':'/analyze','headers':[(b'content-length',b'10')]},receive,send)
        assert called is False
        assert sent[0]['status']==413
    asyncio.run(exercise())


def test_liveness_is_not_readiness():
    assert client.get('/health').json()['production_ready'] is False
    response=client.get('/ready')
    assert response.status_code==503
    assert response.json()['production_ready'] is False


@pytest.mark.parametrize('text',['','   ','\n\t','x'*10001,5,None])
def test_invalid_text_rejected(text):
    assert client.post('/analyze',json={'text':text}).status_code==422


@pytest.mark.parametrize('price',[-1,0,True,'500','NaN','Infinity'])
def test_invalid_price_rejected(price):
    assert client.post('/analyze',json={'text':'حديد','asking_total_price':price}).status_code==422


@pytest.mark.parametrize('token',['NaN','Infinity','-Infinity','1e999'])
def test_nonfinite_json_rejected_without_serialization_error(token):
    response=client.post('/analyze',content='{"text":"حديد","asking_total_price":'+token+'}',headers={'Content-Type':'application/json'})
    assert response.status_code==422
    assert 'input' not in response.json()['detail'][0]


def test_file_path_cannot_be_smuggled_into_public_request():
    assert client.post('/analyze',json={'text':'حديد','image_path':'/etc/passwd'}).status_code==422


@pytest.mark.parametrize('text',[
    'حديد مش جديد', 'مواسير غير مستعمل', 'صاج مفيش صدأ',
    'خشب بدون صدأ', 'حديد جديد ومستعمل', 'صاج صدأ ومستعمل',
    'حديد جديد من غير صدأ',
])
def test_negated_or_conflicting_conditions_are_unknown(text):
    assert detect_condition(text) is None


def test_longest_condition_phrase_survives_conservative_guard():
    assert detect_condition('خشب شبه جديد')=='مستعمل'


def test_unknown_condition_cannot_become_new_price_verdict():
    result=analyze_ad('عندي ٣٠ طن حديد تسليح في العاشر من رمضان',asking_total_price=1900000)
    assert result['entities']['condition_detected'] is None
    assert result['pricing']['reason']=='condition_unknown'
    assert result['pricing']['verdict'] is None
    assert result['pricing']['is_fair'] is None
    assert result['pricing']['fair_total_price_egp'] is None
    assert result['pricing']['reference_price_unit']=='طن'
    assert result['production_ready'] is False


def test_bag_weight_is_not_assumed():
    result=evaluate_ask('أسمنت','جديد',None,50,150000,quantity_unit='شيكارة')
    assert result['verdict'] is None
    assert result['fair_total_price_egp'] is None
    assert result['reason']=='quantity_unit_missing_or_unsupported'


def test_missing_unit_is_not_assumed():
    result=evaluate_ask('حديد تسليح','جديد',None,10,400000)
    assert result['verdict'] is None


def test_cubic_metres_not_linear_metres():
    result=evaluate_ask('خشب زان','جديد',None,10,400000,quantity_unit='متر')
    assert result['verdict'] is None


def test_kg_to_tonne_conversion_is_explicit():
    unit=fair_price('حديد تسليح','جديد')
    result=evaluate_ask('حديد تسليح','جديد',None,1000,unit,quantity_unit='كيلو')
    assert result['pricing_quantity']==1.0
    assert result['price_unit']=='طن'
    assert result['input_quantity_unit']=='كيلو'
    assert result['verdict']=='عادل'


def test_generic_material_assumption_cannot_issue_verdict():
    result=evaluate_ask('حديد تسليح','جديد',None,10,400000,quantity_unit='طن',material_confirmed=False)
    assert result['reason']=='material_assumed'
    assert result['verdict'] is None


@pytest.mark.parametrize('condition',[None,'مستعمل','صدأ'])
def test_unsupported_condition_cannot_bypass_low_level_guard(condition):
    with pytest.raises(ValueError):
        fair_price('حديد تسليح',condition)


@pytest.mark.parametrize('quantity',[0,-5,True,float('inf'),float('nan')])
def test_invalid_quantity_rejected(quantity):
    with pytest.raises(ValueError):
        evaluate_ask('حديد تسليح','جديد',None,quantity,5000,quantity_unit='طن')


@pytest.mark.parametrize('text',['-٥ طن','5e10 طن','1,000 طن','1٬000 طن','9'*400+' طن'])
def test_ambiguous_or_nonfinite_quantity_not_silently_misread(text):
    assert parse_quantity(text)[0] is None


def test_vision_is_blocked_without_reading_file_or_loading_model():
    result=verify_image('/does/not/exist.jpg','حديد تسليح')
    assert result['status']=='blocked_integrity_review'
    assert result['match'] is None
    assert result['confidence'] is None
    assert result['visual_condition_supported'] is False


def test_local_capacity_limit_returns_429(monkeypatch):
    class Full:
        def acquire(self,blocking=False): return False
    monkeypatch.setattr(api,'_INFERENCE_SLOTS',Full())
    response=client.post('/analyze',json={'text':'حديد'})
    assert response.status_code==429
    assert response.headers['Retry-After']=='1'


def test_backend_value_error_becomes_422(monkeypatch):
    def bad(*args,**kwargs): raise ValueError('private value must not be echoed')
    monkeypatch.setattr(api,'analyze_ad',bad)
    response=client.post('/analyze',json={'text':'حديد'})
    assert response.status_code==422
    assert 'private value' not in response.text
