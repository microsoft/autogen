from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Union, Literal
import os


class GithubAuthConfig(BaseModel):
    client_id: str
    client_secret: str
    callback_url: str
    scopes: List[str] = ["user:email"]


class MSALAuthConfig(BaseModel):
    tenant_id: str
    client_id: str
    client_secret: str
    callback_url: str
    scopes: List[str] = ["User.Read"]


class FirebaseAuthConfig(BaseModel):
    api_key: str
    auth_domain: str
    project_id: str


class AuthConfig(BaseModel):
    """Authentication configuration model for the application."""
    type: Literal["none", "github", "msal", "firebase"] = "none"
    github: Optional[GithubAuthConfig] = None
    msal: Optional[MSALAuthConfig] = None
    firebase: Optional[FirebaseAuthConfig] = None
    jwt_secret: Optional[str] = None
    token_expiry_minutes: int = 60
    exclude_paths: List[str] = [
        "/api/health", 
        "/api/version", 
        "/api/auth/login-url", 
        "/api/auth/callback-handler",
        "/api/auth/callback"
    ]

    @field_validator('github')
    def validate_github_config(cls, v, values):
        """Validate GitHub config is present when github type is selected."""
        if values.get('type') == 'github' and v is None:
            raise ValueError("GitHub configuration required when type is 'github'")
        return v

    @field_validator('msal')
    def validate_msal_config(cls, v, values):
        """Validate MSAL config is present when msal type is selected."""
        if values.get('type') == 'msal' and v is None:
            raise ValueError("MSAL configuration required when type is 'msal'")
        return v

    @field_validator('firebase')
    def validate_firebase_config(cls, v, values):
        """Validate Firebase config is present when firebase type is selected."""
        if values.get('type') == 'firebase' and v is None:
            raise ValueError("Firebase configuration required when type is 'firebase'")
        return v

    @field_validator('jwt_secret')
    def validate_jwt_secret(cls, v, values):
        """Validate JWT secret is present for auth types other than 'none'."""
        if values.get('type') != 'none' and not v:
            raise ValueError("JWT secret is required for authentication")
        return v

class User(BaseModel):
    """User model for authenticated users."""
    id: str
    name: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    provider: Optional[str] = None
    roles: List[str] = ["user"]
    metadata: Optional[Dict[str, Any]] = None