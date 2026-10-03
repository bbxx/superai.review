from dataclasses import dataclass
from typing import Protocol

import jwt
from jwt import InvalidTokenError, PyJWKClient, PyJWKClientError


class IdentityVerificationError(RuntimeError):
    pass


class AuthNotConfiguredError(IdentityVerificationError):
    pass


class InvalidIdentityTokenError(IdentityVerificationError):
    pass


@dataclass(frozen=True)
class Identity:
    issuer: str
    subject: str
    email: str
    display_name: str | None = None


class IdentityVerifier(Protocol):
    def verify(self, token: str) -> Identity:
        ...


class DisabledIdentityVerifier:
    def verify(self, token: str) -> Identity:
        del token
        raise AuthNotConfiguredError("OIDC verification is not configured")


class OIDCIdentityVerifier:
    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        jwks_url: str,
        algorithms: tuple[str, ...] = ("RS256",),
        require_email_verified: bool = True,
    ) -> None:
        self._issuer = issuer
        self._audience = audience
        self._algorithms = algorithms
        self._require_email_verified = require_email_verified
        self._jwk_client = PyJWKClient(jwks_url)

    def verify(self, token: str) -> Identity:
        try:
            key = self._jwk_client.get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                key,
                algorithms=list(self._algorithms),
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["exp", "iat", "iss", "sub"]},
            )
        except (InvalidTokenError, PyJWKClientError) as exc:
            raise InvalidIdentityTokenError("invalid OIDC token") from exc

        email = claims.get("email")
        if not isinstance(email, str) or not email.strip():
            raise InvalidIdentityTokenError("OIDC token has no usable email")
        if self._require_email_verified and claims.get("email_verified") is not True:
            raise InvalidIdentityTokenError("OIDC email is not verified")

        name = claims.get("name")
        return Identity(
            issuer=str(claims["iss"]),
            subject=str(claims["sub"]),
            email=email,
            display_name=name if isinstance(name, str) and name.strip() else None,
        )
