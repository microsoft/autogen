import asyncio
from typing import Any, ClassVar, Dict, List, Optional

import jwt
from autogen_core import Component, ComponentBase
from jwt import PyJWKClient
from pydantic import BaseModel


class TokenValidatorConfig(BaseModel):
    """
    Configuration model for JWT token validation.

    Attributes:
        validator_kind (str): The type of validator (e.g., "JwtValidator").
        jwks_uri (str): URI to the JSON Web Key Set (JWKS) containing the public keys.
        issuer (str): Expected issuer of the JWT token.
        audience (str): Expected audience of the JWT token.
        algorithms (List[str]): List of allowed signing algorithms (e.g., ["RS256"]).
        component_type (ClassVar[str]): The component type identifier.
        component_provider_override (ClassVar[str]): The component provider identifier.
    """

    validator_kind: str
    jwks_uri: str
    issuer: str
    audience: str
    algorithms: List[str]
    component_type: ClassVar[str] = "token_validator"
    component_provider_override: ClassVar[str] = "jwt_validator"


"""
JWT Token Validator Component for AutoGen.

This module provides a JWT (JSON Web Token) validator component for AutoGen.
It validates and decodes JWT tokens using the provided JWKS URI, issuer, audience,
and signing algorithms. The component can be used for OAuth token validation in
AutoGen-based applications.

Dependencies:
- PyJWT: For JWT token validation
- pydantic: For data validation and settings management
- autogen_core: For component base classes
"""


class JwtValidator(ComponentBase[TokenValidatorConfig], Component[TokenValidatorConfig]):
    """
    JWT Token Validator Component.

    This component validates and decodes JWT tokens using the specified JWKS URI,
    issuer, audience, and signing algorithms. It implements the AutoGen component
    interface and can be used for OAuth token validation in AutoGen-based applications.

    Attributes:
        component_type (str): The component type identifier.
        component_config_schema (Type): The configuration schema class.
        component_provider_override (str): The component provider identifier.
    """

    component_type = "token_validator"
    component_config_schema = TokenValidatorConfig
    component_provider_override = "jwt_validator"

    def __init__(self, jwks_uri: str, issuer: str, audience: str, algorithms: Optional[list[str]] = None, 
                 enabl_keys_cache: bool = False,
                 lifespan: int = 300) -> None:
        """
        Initialize the JWT validator.

        Args:
            jwks_uri (str): URI to the JSON Web Key Set containing the public keys.
            issuer (str): Expected issuer of the JWT token.
            audience (str): Expected audience of the JWT token.
            algorithms (List[str], optional): List of allowed signing algorithms.
                Defaults to ["RS256"].
            enabl_keys_cache (bool, optional): Whether to cache the result from the jwks_url. Caching key will be the issuer. 
                Defaults to False.
            lifespan (int, optional): Lifespan of the JWK set cache in seconds. Defaults to 300 seconds (5 minutes).
        """

        if algorithms is None:
            algorithms = ["RS256"]

        self.jwks_uri = jwks_uri
        self.issuer = issuer
        self.audience = audience
        self.algorithms = algorithms
        self.lifespan = lifespan
        self.jwk_client = PyJWKClient(jwks_uri, lifespan=lifespan, cache_jwk_set=enabl_keys_cache)

    async def async_get_signing_key(self, token: str) -> Any:
        """
        Asynchronous wrapper for getting the signing key from JWT.

        Since PyJWKClient doesn't have native async support, this method
        provides an async interface but internally uses synchronous methods.

        Args:
            token (str): The JWT token to extract the key ID from.

        Returns:
            Any: The signing key used to verify the token signature.
        """
        # Since PyJWKClient doesn't have native async support,
        # we're still using the synchronous method but in an async context
        
        loop = asyncio.get_running_loop()
        pyjwk = await loop.run_in_executor(None, self.jwk_client.get_signing_key_from_jwt, token)
        return pyjwk.key

    async def __call__(self, token: str, required_claims: Optional[list[str]] = None) -> Dict[str, Any]:
        """
        Asynchronously validate and decode the JWT token.

        This makes the JwtValidator instance callable. When called with a token,
        it validates and decodes the token, checking the signature, expiration,
        issuer, and audience claims, validating required custom claims according to the configured values.
    

        Args:
            token (str): The JWT token string to validate and decode.
            required_claims (Optional[list[str]]): List of required claims.

        Returns:
            Dict[str, Any]: The decoded token claims if validation succeeds.

        Raises:
            jwt.InvalidTokenError: If the token is invalid, expired, or has
                incorrect signature, issuer, or audience.
        """
        signing_key = await self.async_get_signing_key(token)

        claims = jwt.decode(token, signing_key, algorithms=self.algorithms, audience=self.audience, issuer=self.issuer, 
                            options=self._convert_to_required_options(required_claims))
        
        return claims  # type: ignore

    
    def _convert_to_required_options(self, required_claims: Optional[list[str]]) -> Dict[str, list[str]]:
        """
        Convert the required claims to JWT decode options.

        Args:
            required_claims (Optional[list[str]]): List of required claims.

        Returns:
            Dict[str, Any]: Options for JWT decode.
        """
        
        options: Dict[str, list[str]] = {}
        
        if not required_claims:
            options["require"] = []
            return options
        
        if required_claims:
            options["require"] = required_claims
            
        return options
    
    def to_config(self) -> TokenValidatorConfig:
        """
        Convert the validator instance to a configuration object.

        This method is used for serialization and persistence of the component.

        Returns:
            TokenValidatorConfig: A configuration object representing this validator.
        """
        return TokenValidatorConfig(
            validator_kind="JwtValidator",
            jwks_uri=self.jwks_uri,
            issuer=self.issuer,
            audience=self.audience,
            algorithms=self.algorithms,
        )

    @classmethod
    def from_config(cls, config: TokenValidatorConfig) -> "JwtValidator":
        """
        Create a validator instance from a configuration object.

        This class method is used for deserialization and restoration of
        the component from a saved configuration.

        Args:
            config (TokenValidatorConfig): The configuration object.

        Returns:
            JwtValidator: A new validator instance created from the configuration.

        Raises:
            ValueError: If the validator_kind is not supported.
        """
        if config.validator_kind == "JwtValidator":
            return cls(config.jwks_uri, config.issuer, config.audience, config.algorithms)
        raise ValueError(f"Unsupported validator_kind: {config.validator_kind}")
