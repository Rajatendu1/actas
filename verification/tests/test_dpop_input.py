"""Malformed signed DPoP claim regressions, not protocol certification."""
import time
import jwt
import pytest
from fastapi.testclient import TestClient
from actas import dpop, errors


@pytest.mark.parametrize('iat', ['current', 1.5, True, None, [], {}])
def test_proof_iat_requires_integer(iat):
    key, jwk = dpop.generate_key()
    now = int(time.time())
    if iat == 'current':
        iat = str(now)
    elif iat == 1.5:
        iat = now + 0.5
    claims = dict(htm='POST', htu='http://testserver/oauth/token',
                  iat=iat, jti='malformed-iat')
    proof = jwt.encode(claims, key, algorithm='ES256',
                       headers={'jwk': jwk, 'typ': 'dpop+jwt'})
    with pytest.raises(errors.TokenExchangeError) as exc:
        dpop.verify_proof(proof, expected_jkt=dpop.thumbprint(jwk),
                          method='POST', uri=claims['htu'])
    assert exc.value.status_code == 401


def test_signed_string_iat_is_http_client_error():
    from actas.app import app
    c = TestClient(app, raise_server_exceptions=False)
    user = c.get('/demo/usertoken').text
    form = dict(grant_type='urn:ietf:params:oauth:grant-type:token-exchange',
                subject_token_type='urn:ietf:params:oauth:token-type:jwt',
                subject_token=user, client_id='planner-bot',
                scope='read:calendar', audience='calendar-api')
    key, jwk = dpop.generate_key()
    claims = dict(htm='POST', htu='http://testserver/oauth/token',
                  iat=str(int(time.time())), jti='http-malformed-iat')
    proof = jwt.encode(claims, key, algorithm='ES256',
                       headers={'jwk': jwk, 'typ': 'dpop+jwt'})
    response = c.post('/oauth/token', data=form, headers={'DPoP': proof})
    assert response.status_code == 401
    assert response.json()['error'] == 'invalid_token'
