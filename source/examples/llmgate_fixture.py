"""Example fixture for an llmgate-style embedded integration (topology A).

Runnable: `python3 examples/llmgate_fixture.py`

Builds one in-process trust domain: a parent agent and a sub-agent with
narrowing policies over fictional model scopes. Shows the story the gateway
demo would render: parent token issued, exchanged down for the sub-agent
(scope shrinks, TTL clamped), a widening attempt denied, and the audit
entries for all three outcomes. All parties are fictional; scopes are
placeholders the gateway maps to its own model policy.

This is actas-side example code. It makes no gateway edits and assumes no
particular gateway internals.
"""

from actas.audit import AuditLog
from actas.errors import TokenExchangeError
from actas.exchange import GRANT_TYPE, TOKEN_TYPE_JWT, TokenExchangeService
from actas.keys import KeyStore
from actas.policy import AgentPolicy, PolicyEngine
from actas.registry import TokenRegistry
from actas import tokens

ISSUER = "https://llmgate.demo.example"  # the embedded issuer, not the public actas demo
PARENT = "parent-agent"
SUBAGENT = "sub-agent"

# Parent may use completion at all, including expensive models; the sub-agent
# is capped at plain completion and a shorter TTL, so delegation narrows.
POLICIES = [
    AgentPolicy(client_id=PARENT,
                allowed_scopes=frozenset({"llm:complete", "llm:expensive-models"}),
                allowed_audiences=frozenset({"llmgate"}),
                max_delegation_depth=2, max_token_ttl=900),
    AgentPolicy(client_id=SUBAGENT,
                allowed_scopes=frozenset({"llm:complete"}),
                allowed_audiences=frozenset({"llmgate"}),
                max_delegation_depth=2, max_token_ttl=300),
]


def main() -> None:
    keystore = KeyStore()
    audit = AuditLog()
    service = TokenExchangeService(
        keystore=keystore, policy=PolicyEngine({p.client_id: p for p in POLICIES}),
        audit=audit, issuer=ISSUER, registry=TokenRegistry())

    user_token, _ = tokens.issue_token(
        keystore, issuer=ISSUER, subject="u-demo",
        scope="llm:complete llm:expensive-models", audience=[ISSUER], expires_in=3600)

    # the parent agent acts for the user, then delegates to the sub-agent
    parent = service.exchange(
        grant_type=GRANT_TYPE, subject_token=user_token,
        subject_token_type=TOKEN_TYPE_JWT, client_id=PARENT,
        scope="llm:complete llm:expensive-models", audience="llmgate")

    narrowed = service.exchange(
        grant_type=GRANT_TYPE, subject_token=parent.access_token,
        subject_token_type=TOKEN_TYPE_JWT, client_id=SUBAGENT,
        scope="llm:complete", audience="llmgate")
    print("sub-agent granted scope:", narrowed.claims["scope"],
          "| ttl:", narrowed.expires_in, "s (clamped by policy)")
    print("delegation chain:", tokens.act_chain(narrowed.claims.get("act")))

    # the same sub-agent asking for expensive models is denied, not narrowed
    try:
        service.exchange(
            grant_type=GRANT_TYPE, subject_token=parent.access_token,
            subject_token_type=TOKEN_TYPE_JWT, client_id=SUBAGENT,
            scope="llm:complete llm:expensive-models", audience="llmgate")
    except TokenExchangeError as exc:
        print("widening denied:", exc.error, "-", exc.description)

    for e in audit.tail(10):
        print("audit:", e["event"], e["detail"])
    ok, bad = audit.verify()
    print("audit chain verifies:", ok)


if __name__ == "__main__":
    main()
