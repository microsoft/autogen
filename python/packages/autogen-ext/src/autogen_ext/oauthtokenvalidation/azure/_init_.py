from typing import List, ClassVar, Any, Dict
import jwt
from jwt import PyJWKClient
from pydantic import BaseModel
from autogen_core import ComponentBase, Component

class TokenValidatorConfig(BaseModel):
    validator_kind: str
    jwks_uri: str
    issuer: str
    audience: str
    algorithms: List[str]
    component_type: ClassVar[str] = "token_validator"
    component_provider_override: ClassVar[str] = "azure_jwt_validator"

class AzureJwtValidator(ComponentBase[TokenValidatorConfig], Component[TokenValidatorConfig]):
    component_type = "token_validator"
    component_config_schema = TokenValidatorConfig
    component_provider_override = "azure_jwt_validator"

    def __init__(self, jwks_uri: str, issuer: str, audience: str, algorithms: List[str] = ["RS256"]):
        self.jwks_uri = jwks_uri
        self.issuer = issuer
        self.audience = audience
        self.algorithms = algorithms
        self.jwk_client = PyJWKClient(jwks_uri)

    def __call__(self, token: str) -> Dict[str, Any]:
        signing_key = self.jwk_client.get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=self.algorithms,
            audience=self.audience,
            issuer=self.issuer
        )
        return claims

    def _to_config(self) -> TokenValidatorConfig:
        return TokenValidatorConfig(
            validator_kind="AzureJwtValidator",
            jwks_uri=self.jwks_uri,
            issuer=self.issuer,
            audience=self.audience,
            algorithms=self.algorithms
        )

    @classmethod
    def _from_config(cls, config: TokenValidatorConfig) -> "AzureJwtValidator":
        if config.validator_kind == "AzureJwtValidator":
            return cls(
                config.jwks_uri,
                config.issuer,
                config.audience,
                config.algorithms
            )
        raise ValueError("Unsupported validator_kind: {config.validator_kind}")
