from datetime import UTC, datetime, timedelta

import jwt
import pytest

from superai_review.auth.identity import InvalidIdentityTokenError, OIDCIdentityVerifier


class _SigningKey:
    def __init__(self, key: str) -> None:
        self.key = key


class _StaticJWKClient:
    def __init__(self, key: str) -> None:
        self._key = key

    def get_signing_key_from_jwt(self, token: str) -> _SigningKey:
        del token
        return _SigningKey(self._key)


def token(secret: str, *, email_verified: bool = True) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "iss": "https://issuer.example",
            "aud": "superai",
            "sub": "subject-1",
            "email": "person@example.com",
            "email_verified": email_verified,
            "name": "Person",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        secret,
        algorithm="HS256",
    )


def verifier(secret: str) -> OIDCIdentityVerifier:
    result = OIDCIdentityVerifier(
        issuer="https://issuer.example",
        audience="superai",
        jwks_url="https://issuer.example/jwks",
        algorithms=("HS256",),
    )
    result._jwk_client = _StaticJWKClient(secret)
    return result


def test_oidc_verifier_validates_claims_and_identity() -> None:
    identity = verifier("secret").verify(token("secret"))

    assert identity.subject == "subject-1"
    assert identity.email == "person@example.com"
    assert identity.issuer == "https://issuer.example"


def test_oidc_verifier_rejects_unverified_email() -> None:
    with pytest.raises(InvalidIdentityTokenError):
        verifier("secret").verify(token("secret", email_verified=False))


def test_oidc_verifier_rejects_bad_signature() -> None:
    with pytest.raises(InvalidIdentityTokenError):
        verifier("right-secret").verify(token("wrong-secret"))
