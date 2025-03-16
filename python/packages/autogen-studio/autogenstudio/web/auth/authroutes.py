import html
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from loguru import logger

from .exceptions import ProviderAuthException
from .manager import AuthManager
from .models import User

router = APIRouter()


def get_auth_manager(request: Request) -> AuthManager:
    """Get the auth manager from app state."""
    if not hasattr(request.app.state, "auth_manager"):
        raise HTTPException(status_code=500, detail="Authentication system not initialized")
    return request.app.state.auth_manager


def get_current_user(request: Request) -> User:
    """Get the current authenticated user."""
    if hasattr(request.state, "user"):
        return request.state.user

    # This shouldn't normally happen as middleware should set user
    logger.warning("User not found in request state")
    return User(id="anonymous", name="Anonymous User")


@router.get("/login-url")
async def get_login_url(auth_manager: AuthManager = Depends(get_auth_manager)):
    """Get the URL for the frontend to redirect to for login."""
    try:
        login_url = await auth_manager.provider.get_login_url()
        return {"login_url": login_url}
    except Exception as e:
        logger.error(f"Error getting login URL: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate login URL: {str(e)}") from e


@router.get("/callback")
async def oauth_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    auth_manager: AuthManager = Depends(get_auth_manager),
):
    """
    OAuth callback handler - used by OAuth providers to redirect after auth. This endpoint renders an HTML page that communicates with the parent window
    to pass the token back to the main application.
    """
    if error:
        logger.error(f"OAuth callback error: {error}")
        # Return HTML that sends error to parent window
        escaped_error = html.escape(error)
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Result</title>
            <script>
                window.onload = function() {{
                    if (window.opener) {{
                        // Send error to parent window
                        window.opener.postMessage({{
                            type: 'auth-error',
                            error: '{escaped_error}'
                        }}, '*');
                        // Close this window
                        window.close();
                    }} else {{
                        // Redirect to main app with error
                        window.location.href = '/?auth_error={escaped_error}';
                    }}
                }};
            </script>
        </head>
        <body>
            <p>Authentication failed. This window should close automatically.</p>
        </html>
        """
        return Response(content=html_content, media_type="text/html")

    # Add guard for code parameter
    if not code:
        logger.error("OAuth callback missing required 'code' parameter")
        raise HTTPException(status_code=400, detail="Missing required 'code' parameter")

    try:
        # Process the authentication callback
        user = await auth_manager.provider.process_callback(code, state)

        # Create JWT token
        token = auth_manager.create_token(user)

        # Return HTML that sends token to parent window
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Complete</title>
            <script>
                window.onload = function() {{
                    const authResult = {{
                        type: 'auth-success',
                        token: '{token}',
                        user: {{
                            id: '{user.id}',
                            name: '{user.name}',
                            email: '{user.email or ""}',
                            provider: '{user.provider}'
                        }}
                    }};
                    if (window.opener) {{
                        // Send token to parent window
                        window.opener.postMessage(authResult, '*');
                        // Close this window
                        window.close();
                    }} else {{
                        // Redirect to main app with token
                        localStorage.setItem('auth_token', '{token}');
                        window.location.href = '/';
                    }}
                }};
            </script>
        </head>
        <body>
            <p>Authentication successful. This window should close automatically.</p>
        </body>
        </html>
        """
        return Response(content=html_content, media_type="text/html")

    except ProviderAuthException as e:
        logger.error(f"OAuth callback provider error: {str(e)}")
        raise HTTPException(status_code=401, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Unexpected OAuth callback error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}") from e


@router.post("/callback-handler")
async def handle_callback(request: Request, auth_manager: AuthManager = Depends(get_auth_manager)):
    """
    Handle authentication code/token from frontend.This endpoint is used when the frontend handles the OAuth flow and
    needs to exchange the code for a token.
    """
    try:
        data = await request.json()
        code = data.get("code")
        state = data.get("state")

        if not code:
            raise HTTPException(status_code=400, detail="Authorization code is required")

        # Process the authentication code
        user = await auth_manager.provider.process_callback(code, state)

        # Create JWT token
        token = auth_manager.create_token(user)

        # Return token and user info
        return {
            "token": token,
            "user": {"id": user.id, "name": user.name, "email": user.email, "provider": user.provider},
        }

    except ProviderAuthException as e:
        logger.error(f"Callback handler provider error: {str(e)}")
        raise HTTPException(status_code=401, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Unexpected callback handler error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}") from e


@router.get("/me")
async def get_user_info(current_user: User = Depends(get_current_user)):
    """Get information about the currently authenticated user."""
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "provider": current_user.provider,
        "roles": current_user.roles,
    }


@router.get("/type")
async def get_auth_type(auth_manager: AuthManager = Depends(get_auth_manager)):
    """Get the configured authentication type."""
    return {"type": auth_manager.config.type, "exclude_paths": auth_manager.config.exclude_paths}
