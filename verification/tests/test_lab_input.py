"""New malformed-input regressions for the fictional, throwaway lab only."""
import json
import pytest
from fastapi.testclient import TestClient
from actas.app import app, lab_limiter

@pytest.fixture
def client():
    lab_limiter.hits.clear()
    return TestClient(app, raise_server_exceptions=False)

@pytest.fixture
def payload():
    return {'user_scopes':['read:calendar'], 'hops':[{
        'actor':'planner-bot', 'audience':'calendar-api', 'scope':['read:calendar']}]}

@pytest.mark.parametrize('raw',[
    '['*1200+'0'+']'*1200,
    '{', b'\xff', 'null', '[]',
    '{"hops":[],"hops":[{"actor":"planner-bot","audience":"calendar-api","scope":["read:calendar"]}]}',
    '{"hops":[],"\\u0068ops":[{"actor":"planner-bot","audience":"calendar-api","scope":["read:calendar"]}]}',
    '{"hops":[{"actor":"planner-bot","actor":"summarizer-tool","audience":"calendar-api","scope":["read:calendar"]}]}',
])
def test_bad_lab_json_is_client_error_not_server_failure(client,raw):
    response=client.post('/demo/lab',content=raw)
    assert response.status_code==400
    assert response.json()['error']=='invalid_request'

@pytest.mark.parametrize('value',['false','true',0,1,None,[],{}])
def test_bind_flag_does_not_coerce_truthiness(client,payload,value):
    payload['bind_final']=value
    response=client.post('/demo/lab',json=payload)
    assert response.status_code==400
    assert response.json()['error_description']=='bind_final must be true or false'

@pytest.mark.parametrize('binding',[None,False,True])
def test_valid_lab_request_keeps_expected_binding(client,payload,binding):
    if binding is not None:payload['bind_final']=binding
    response=client.post('/demo/lab',json=payload)
    assert response.status_code==200
    report=response.json()
    assert report['reached_end'] and report['audit']['ok']
    assert report['steps'][-1]['bound']==(binding is True)
    assert report['outcome']['actions'][0]['allowed']
    if binding:
        assert report['outcome']['pop']==dict(holder_accepted=True,thief_accepted=False,first_use_accepted=True,replay_accepted=False)
    else:assert report['outcome']['pop'] is None

@pytest.mark.parametrize('size,expected',[(4096,200),(4097,400)])
def test_lab_body_cap_still_holds(client,payload,size,expected):
    raw=json.dumps(payload)
    response=client.post('/demo/lab',content=raw+' '*(size-len(raw)))
    assert response.status_code==expected
