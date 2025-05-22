import time
from typing import Any, Generator
from unittest.mock import MagicMock, patch, AsyncMock

import jwt
import pytest
from autogen_ext.oauthtokenvalidation import JwtValidator, TokenValidatorConfig
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


@pytest.fixture
def private_key() -> rsa.RSAPrivateKey:
    """Generate a private key for signing JWT tokens in tests."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key


@pytest.fixture
def public_key(private_key: rsa.RSAPrivateKey) -> rsa.RSAPublicKey:
    """Extract public key from the private key."""
    return private_key.public_key()


@pytest.fixture
def mock_jwk_client() -> Generator[AsyncMock, None, None]:
    """Mock PyJWKClient to avoid real HTTP calls."""
    with patch("jwt.PyJWKClient") as mock:
        yield mock


@pytest.fixture
def valid_token_payload() -> dict[str, Any]:
    """Create a valid token payload."""
    return {
        "iss": "https://test-issuer.com",
        "sub": "test-subject",
        "aud": "test-audience",
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
    }


@pytest.fixture
def expired_token_payload() -> dict[str, Any]:
    """Create an expired token payload."""
    return {
        "iss": "https://test-issuer.com",
        "sub": "test-subject",
        "aud": "test-audience",
        "exp": int(time.time()) - 3600,  # Expired 1 hour ago
        "iat": int(time.time()) - 7200,
    }


@pytest.fixture
def wrong_audience_token_payload(valid_token_payload: dict[str, Any]) -> dict[str, Any]:
    """Create a token payload with wrong audience."""
    payload = valid_token_payload.copy()
    payload["aud"] = "wrong-audience"
    return payload


@pytest.fixture
def wrong_issuer_token_payload(valid_token_payload: dict[str, Any]) -> dict[str, Any]:
    """Create a token payload with wrong issuer."""
    payload = valid_token_payload.copy()
    payload["iss"] = "https://wrong-issuer.com"
    return payload


@pytest.fixture
def token_validator() -> JwtValidator:
    """Create a token validator instance with mock JWKS client."""
    validator = JwtValidator(
        jwks_uri="https://test-jwks-uri.com",
        issuer="https://test-issuer.com",
        audience="test-audience",
        algorithms=["RS256"],
    )
    return validator


def create_token(payload: dict[str, Any], private_key: rsa.RSAPrivateKey) -> str:
    """Helper to create a JWT token for testing."""
    return jwt.encode(
        payload,
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ),
        algorithm="RS256",
    )


@pytest.mark.asyncio
async def test_validate_valid_token(
    token_validator: JwtValidator,
    valid_token_payload: dict[str, Any],
    private_key: rsa.RSAPrivateKey,
    public_key: rsa.RSAPublicKey,
) -> None:
    """Test that a valid token is correctly validated."""
    # Create a valid token
    token = create_token(valid_token_payload, private_key)

    # Mock the signing key retrieval
    mock_signing_key = public_key.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    with patch.object(token_validator, "async_get_signing_key", return_value=mock_signing_key):
        # Validate the token
        claims = await token_validator(token)

        # Assert the claims are as expected
        assert claims["iss"] == valid_token_payload["iss"]
        assert claims["sub"] == valid_token_payload["sub"]
        assert claims["aud"] == valid_token_payload["aud"]


@pytest.mark.asyncio
async def test_validate_token_with_missing_claims(
    token_validator: JwtValidator,
    valid_token_payload: dict[str, Any],
    private_key: rsa.RSAPrivateKey,
    public_key: rsa.RSAPublicKey,
) -> None:
    """Test that a valid a token with required claims will fail."""
    # Create a valid token
    token = create_token(valid_token_payload, private_key)

    # Mock the signing key retrieval
    mock_signing_key = public_key.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    with patch.object(token_validator, "async_get_signing_key", return_value=mock_signing_key):
        # Validate the token
        with pytest.raises(jwt.MissingRequiredClaimError):
            await token_validator(token, required_claims=["claim1"])

        # Assert the claims are as expected


@pytest.mark.asyncio
async def test_validate_expired_token(
    token_validator: JwtValidator,
    expired_token_payload: dict[str, Any],
    private_key: rsa.RSAPrivateKey,
    public_key: rsa.RSAPublicKey,
) -> None:
    """Test that an expired token raises ExpiredSignatureError."""
    # Create an expired token
    token = create_token(expired_token_payload, private_key)

    # Mock the signing key retrieval with a proper public key
    mock_signing_key = public_key.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    with patch.object(token_validator, "async_get_signing_key", return_value=mock_signing_key):
        # Expect ExpiredSignatureError
        with pytest.raises(jwt.ExpiredSignatureError):
            await token_validator(token)


@pytest.mark.asyncio
async def test_validate_wrong_audience(
    token_validator: JwtValidator,
    wrong_audience_token_payload: dict[str, Any],
    private_key: rsa.RSAPrivateKey,
    public_key: rsa.RSAPublicKey,
) -> None:
    """Test that a token with wrong audience raises InvalidAudienceError."""
    # Create a token with wrong audience
    token = create_token(wrong_audience_token_payload, private_key)

    # Mock the signing key retrieval
    mock_signing_key = public_key.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    with patch.object(token_validator, "async_get_signing_key", return_value=mock_signing_key):
        # Expect InvalidAudienceError
        with pytest.raises(jwt.InvalidAudienceError):
            await token_validator(token)


@pytest.mark.asyncio
async def test_validate_wrong_issuer(
    token_validator: JwtValidator,
    wrong_issuer_token_payload: dict[str, Any],
    private_key: rsa.RSAPrivateKey,
    public_key: rsa.RSAPublicKey,
) -> None:
    """Test that a token with wrong issuer raises InvalidIssuerError."""
    # Create a token with wrong issuer
    token = create_token(wrong_issuer_token_payload, private_key)

    # Mock the signing key retrieval
    mock_signing_key = public_key.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    with patch.object(token_validator, "async_get_signing_key", return_value=mock_signing_key):
        # Expect InvalidIssuerError
        with pytest.raises(jwt.InvalidIssuerError):
            await token_validator(token)


@pytest.mark.asyncio
async def test_async_get_signing_key(token_validator: JwtValidator) -> None:
    """Test the async_get_signing_key method."""
    # Setup mock
    mock_key = MagicMock()
    mock_signing_key = MagicMock()
    mock_signing_key.key = mock_key
    token_validator.jwk_client.get_signing_key_from_jwt = MagicMock(return_value=mock_signing_key)  # type: ignore

    # Call the method
    result = await token_validator.async_get_signing_key("test-token")

    # Assert
    assert result == mock_key
    token_validator.jwk_client.get_signing_key_from_jwt.assert_called_once_with("test-token")


def test_to_config(token_validator: JwtValidator) -> None:
    """Test the to_config method."""
    config = token_validator.to_config()

    assert config.validator_kind == "JwtValidator"
    assert config.jwks_uri == "https://test-jwks-uri.com"
    assert config.issuer == "https://test-issuer.com"
    assert config.audience == "test-audience"
    assert config.algorithms == ["RS256"]


def test_from_config() -> None:
    """Test the from_config method."""
    config = TokenValidatorConfig(
        validator_kind="JwtValidator",
        jwks_uri="https://test-jwks-uri.com",
        issuer="https://test-issuer.com",
        audience="test-audience",
        algorithms=["RS256"],
    )

    validator = JwtValidator.from_config(config)

    assert validator.jwks_uri == "https://test-jwks-uri.com"
    assert validator.issuer == "https://test-issuer.com"
    assert validator.audience == "test-audience"
    assert validator.algorithms == ["RS256"]


def test_from_config_invalid_kind() -> None:
    """Test the from_config method with invalid validator_kind."""
    config = TokenValidatorConfig(
        validator_kind="InvalidValidator",
        jwks_uri="https://test-jwks-uri.com",
        issuer="https://test-issuer.com",
        audience="test-audience",
        algorithms=["RS256"],
    )

    with pytest.raises(ValueError, match="Unsupported validator_kind"):
        JwtValidator.from_config(config)
