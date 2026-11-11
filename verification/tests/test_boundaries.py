"""New recovery regression coverage, never the lost original tests."""
from copy import deepcopy
from itertools import product
import json,time
import jwt
import pytest
from fastapi.testclient import TestClient
from actas import demo_fixture as world,dpop,tokens,errors
from actas.policy import PolicyEngine,AgentPolicy
from actas.workbench import run_pack,compare_pack,load_pack_json
from actas.keys import KeyStore

@pytest.fixture
def pack():
 return json.loads((__import__('pathlib').Path(__file__).parents[1]/'samples/baseline.json').read_text())


def test_policy_decision_cartesian_boundaries():
 engine=PolicyEngine({'agent':AgentPolicy('agent',frozenset({'r','w'}),frozenset({'api'}),2,300)})
 for cid,scope,subject,aud,depth,ttl in product(['agent','unknown'],[set(),{'r'},{'w'},{'r','x'}],[{'r'},{'r','w','x'}],['api','wrong'],[1,2,3],[1,300,301]):
  decision=engine.decide(client_id=cid,requested_scope=frozenset(scope),subject_scope=frozenset(subject),audience=aud,delegation_depth=depth,requested_ttl=ttl)
  expected=cid=='agent' and scope<=subject and scope<={'r','w'} and aud=='api' and depth<=2 and ttl<=300
  assert decision.allowed==expected
  assert decision.granted_scope==(frozenset(scope) if expected else frozenset())


def test_workbench_intent_never_hides_changed_decision(pack):
 before=deepcopy(pack['policies']);pack['policies'][0]['allowed_scopes'].append('forbidden:probe');pack['cases'][4]['expect_allowed']=True
 report=compare_pack({'baseline_policies':before,'candidate':pack})
 assert report['candidate']['matched']==report['total']==8 and report['newly_allowed']==1
 assert report['changes'][4]['name']=='outside-policy'

@pytest.mark.parametrize('edit',[lambda p:p.update(schema_version=True),lambda p:p.update(extra=1),lambda p:p.update(cases=[]),lambda p:p.update(cases=p['cases']*9),lambda p:p['cases'][0].update(expect_allowed='false'),lambda p:p['policies'][0].update(max_token_ttl=True),lambda p:p['cases'][0].update(unknown=1)])
def test_strict_pack_invalidity(pack,edit):
 edit(pack)
 with pytest.raises(errors.TokenExchangeError):run_pack(pack)

@pytest.mark.parametrize('raw',[r'{"a":1,"a":2}',r'{"a":1,"\u0061":2}',r'{"n":[{"a":1,"a":2}]}'])
def test_duplicate_json_not_normalized(raw):
 with pytest.raises(errors.TokenExchangeError):load_pack_json(raw)

def test_nonduplicate_json_scopes():
 assert load_pack_json('{"n":[{"a":1},{"a":2}]}')['n'][1]['a']==2

@pytest.fixture(scope='module')
def ks():return KeyStore()

@pytest.mark.parametrize('extra',[{'sub':[]},{'aud':[]},{'scope':[]},{'exp':True},{'cnf':{'jkt':'short'}},{'act':{'sub':[]}}])
def test_malformed_signed_claims_reject(ks,extra):
 token,_=tokens.issue_token(ks,issuer=world.ISSUER,subject='u',scope='r',audience=['api'],expires_in=300,extra=extra)
 with pytest.raises(errors.TokenExchangeError):tokens.verify_token(ks,token,issuer=world.ISSUER)

@pytest.mark.parametrize('kid',[[],{},None,1,'x'*129])
def test_structured_kid_rejects_cleanly(ks,kid):
 import base64
 enc=lambda d:base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b'=').decode()
 with pytest.raises(errors.TokenExchangeError):tokens.verify_token(ks,enc({'alg':'RS256','kid':kid})+'.e30.AA',issuer=world.ISSUER)


def test_signature_issuer_audience_expiry(ks):
 token,_=tokens.issue_token(ks,issuer=world.ISSUER,subject='u',scope='r',audience=['api'],expires_in=300)
 assert tokens.verify_token(ks,token,issuer=world.ISSUER,audience='api')['scope']=='r'
 for store,issuer,audience in [(KeyStore(),'other','api'),(ks,'other','api'),(ks,world.ISSUER,'wrong')]:
  with pytest.raises(errors.TokenExchangeError):tokens.verify_token(store,token,issuer=issuer,audience=audience)
 expired,_=tokens.issue_token(ks,issuer=world.ISSUER,subject='u',scope='r',audience=['api'],expires_in=1,now=time.time()-10)
 with pytest.raises(errors.TokenExchangeError):tokens.verify_token(ks,expired,issuer=world.ISSUER)


def test_rotation_overlap_uses_retirement_not_creation():
 ks=KeyStore();old=ks.current;old.created_at=time.time()-100000;ks.rotate();assert ks.retire_older_than(3600)==[]
 assert old.kid in ks.retire_older_than(3600,now=time.time()+3601)
 for v in [-1,float('nan'),float('inf'),True]:
  with pytest.raises(ValueError):ks.retire_older_than(v)


def test_proof_binding_context_replay_and_capacity():
 key,jwk=dpop.generate_key();wrong,_=dpop.generate_key();cache=dpop.ReplayCache(max_entries=1);uri='https://example.invalid/events'
 proof=dpop.make_proof(key,method='GET',uri=uri,access_token='token')
 args=dict(expected_jkt=dpop.thumbprint(jwk),method='GET',uri=uri,access_token='token',replay=cache)
 assert dpop.verify_proof(proof,**args)
 with pytest.raises(errors.TokenExchangeError):dpop.verify_proof(proof,**args)
 for patch in [{'method':'POST'},{'uri':uri+'/other'},{'access_token':'other'}]:
  with pytest.raises(errors.TokenExchangeError):dpop.verify_proof(dpop.make_proof(key,method='GET',uri=uri,access_token='token'),**{**args,**patch})
 with pytest.raises(errors.TokenExchangeError):dpop.verify_proof(dpop.make_proof(wrong,method='GET',uri=uri),**args)
 with pytest.raises(errors.TokenExchangeError) as exc:dpop.verify_proof(dpop.make_proof(key,method='GET',uri=uri,access_token='token'),**args)
 assert exc.value.status_code==503


def test_http_holder_child_binding_and_actor_identity(monkeypatch):
 import actas.app as module
 from actas.app import app,client_auth,proof_replay,keystore
 monkeypatch.setattr(client_auth,'required',True)
 # Fictional test-only secret, never an account credential.
 client_auth.register('planner-bot','fictional-testing-only-secret')
 c=TestClient(app);user=c.get('/demo/usertoken').text
 form=dict(grant_type='urn:ietf:params:oauth:grant-type:token-exchange',subject_token_type='urn:ietf:params:oauth:token-type:jwt',subject_token=user,client_id='planner-bot',client_secret='fictional-testing-only-secret',scope='read:calendar',audience='calendar-api')
 assert c.post('/oauth/token',data={**form,'client_secret':'wrong'}).status_code==401
 actor,_=tokens.issue_token(keystore,issuer=world.ISSUER,subject='summarizer-tool',scope='read:calendar',audience=[world.ISSUER],expires_in=300)
 assert c.post('/oauth/token',data={**form,'actor_token':actor,'actor_token_type':form['subject_token_type']}).status_code==400
 key,jwk=dpop.generate_key();wrong,_=dpop.generate_key()
 def proof(k):return {'DPoP':dpop.make_proof(k,method='POST',uri='http://testserver/oauth/token')}
 r=c.post('/oauth/token',data=form,headers=proof(key));assert r.status_code==200;bound=r.json()['access_token'];form['subject_token']=bound
 assert c.post('/oauth/token',data=form).status_code==400
 assert c.post('/oauth/token',data={**form,'cnf_jwk':json.dumps(jwk)}).status_code==400
 assert c.post('/oauth/token',data=form,headers=proof(wrong)).status_code==400
 h=proof(key);r=c.post('/oauth/token',data=form,headers=h);assert r.status_code==200
 assert c.post('/oauth/token',data=form,headers=h).status_code==401
 child=r.json()['access_token'];assert jwt.decode(child,options={'verify_signature':False})['cnf']['jkt']==dpop.thumbprint(jwk)
 assert c.get('/api/calendar/events',headers={'Authorization':'Bearer '+child}).status_code==401
 h={'Authorization':'Bearer '+child,'DPoP':dpop.make_proof(key,method='GET',uri='http://testserver/api/calendar/events',access_token=child)}
 assert c.get('/api/calendar/events',headers=h).status_code==200
 assert c.get('/api/calendar/events',headers=h).status_code==401
