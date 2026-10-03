from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_configured_email(value: str) -> str:
    return value.strip().casefold()


class AuthSettings(BaseSettings):
    issuer: str = ""
    audience: str = ""
    jwks_url: str = ""
    algorithms: str = "RS256"
    require_email_verified: bool = True
    bootstrap_admin_emails: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SUPERAI_AUTH_",
        extra="ignore",
    )

    @property
    def configured(self) -> bool:
        return bool(self.issuer and self.audience and self.jwks_url)

    @property
    def allowed_algorithms(self) -> tuple[str, ...]:
        values = tuple(item.strip() for item in self.algorithms.split(",") if item.strip())
        return values or ("RS256",)

    @property
    def bootstrap_admin_email_set(self) -> frozenset[str]:
        return frozenset(
            normalize_configured_email(item)
            for item in self.bootstrap_admin_emails.split(",")
            if item.strip()
        )


@lru_cache
def get_auth_settings() -> AuthSettings:
    return AuthSettings()
