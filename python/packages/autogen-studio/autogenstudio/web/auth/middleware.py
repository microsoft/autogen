from fastapi import Request, Response, WebSocket
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_401_UNAUTHORIZED
import json
from loguru import logger

from .manager import AuthManager
from .exceptions import AuthException, MissingTokenException, InvalidTokenException


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling authentication for all routes.
    """
    
    def __init__(self, app, auth_manager: AuthManager):
        super().__init__(app)
        self.auth_manager = auth_manager
    
    async def dispatch(self, request: Request, call_next):
        """Process each request, authenticating as needed."""
        # Skip auth for excluded paths
        if request.url.path in self.auth_manager.config.exclude_paths:
            return await call_next(request)
            
        # Skip auth if disabled
        if self.auth_manager.config.type == "none":
            request.state.user = await self.auth_manager.authenticate_request(request)
            return await call_next(request)
        
        # WebSocket handling (special case)
        if request.url.path.startswith("/api/ws"):
            # For WebSockets, we'll add auth in the WebSocket accept handler
            # Just pass through here
            return await call_next(request)
        
        # Handle authentication for all other requests
        try:
            user = await self.auth_manager.authenticate_request(request)
            # Add user to request state for use in route handlers
            request.state.user = user
            return await call_next(request)
            
        except AuthException as e:
            # Handle authentication errors
            return Response(
                status_code=HTTP_401_UNAUTHORIZED,
                content=json.dumps({
                    "status": False,
                    "detail": e.detail
                }),
                media_type="application/json",
                headers=e.headers or {}
            )
        except Exception as e:
            # Log unexpected errors
            logger.error(f"Unexpected error in auth middleware: {str(e)}")
            return Response(
                status_code=HTTP_401_UNAUTHORIZED,
                content=json.dumps({
                    "status": False,
                    "detail": "Authentication failed"
                }),
                media_type="application/json"
            )


class WebSocketAuthMiddleware:
    """
    Helper for authenticating WebSocket connections.
    Not a middleware in the traditional sense - used in WebSocket endpoint.
    """
    
    def __init__(self, auth_manager: AuthManager):
        self.auth_manager = auth_manager
    
    async def authenticate(self, websocket: WebSocket) -> bool:
        """
        Authenticate a WebSocket connection.
        Returns True if authenticated, False otherwise.
        """
        if self.auth_manager.config.type == "none":
            return True
            
        try:
            # Extract token from query params or cookies
            token = None
            if "token" in websocket.query_params:
                token = websocket.query_params["token"]
            elif "authorization" in websocket.headers:
                auth_header = websocket.headers["authorization"]
                if auth_header.startswith("Bearer "):
                    token = auth_header.replace("Bearer ", "")
            
            if not token:
                logger.warning(f"No token found for WebSocket connection")
                return False
                
            # Validate token
            valid = self.auth_manager.is_valid_token(token)
            if not valid:
                logger.warning(f"Invalid token for WebSocket connection")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"WebSocket auth error: {str(e)}")
            return False