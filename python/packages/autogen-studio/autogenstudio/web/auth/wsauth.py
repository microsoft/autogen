import jwt
from fastapi import WebSocket, WebSocketDisconnect, status
from loguru import logger

from .manager import AuthManager
from .models import User


class WebSocketAuthHandler:
    """
    Helper class for authenticating WebSocket connections.
    """

    def __init__(self, auth_manager: AuthManager):
        self.auth_manager = auth_manager

    async def authenticate(self, websocket: WebSocket) -> tuple[bool, User | None]:
        """
        Authenticate a WebSocket connection.
        Returns (success, user) tuple.
        """
        if self.auth_manager.config.type == "none":
            # No authentication required
            return True, User(id="admin@kagent.dev", name="Default User", provider="none")

        try:
            # Extract token from query params or headers query_params)
            token = None
            if "token" in websocket.query_params:
                token = websocket.query_params["token"]
            elif "authorization" in websocket.headers:
                auth_header = websocket.headers["authorization"]
                if auth_header.startswith("Bearer "):
                    token = auth_header.replace("Bearer ", "")

            if not token:
                logger.warning("No token found for WebSocket connection")
                return False, None

            # Validate token
            if not self.auth_manager.config.jwt_secret:
                # Development mode with no JWT secret
                return True, User(id="admin@kagent.dev", name="Default User", provider="none")

            try:
                # Decode and validate JWT
                if not self.auth_manager.config.jwt_secret:
                    logger.warning("Invalid token for WebSocket connection")
                    return False, None
                payload = jwt.decode(token, self.auth_manager.config.jwt_secret, algorithms=["HS256"])

                # Create User object from token payload
                user = User(
                    id=payload.get("sub"),
                    name=payload.get("name", "Unknown User"),
                    email=payload.get("email"),
                    provider=payload.get("provider", "jwt"),
                    roles=payload.get("roles", ["user"]),
                )

                return True, user

            except jwt.ExpiredSignatureError:
                logger.warning("Expired token for WebSocket connection")
                return False, None
            except jwt.InvalidTokenError:
                logger.warning("Invalid token for WebSocket connection")
                return False, None

        except Exception as e:
            logger.error(f"WebSocket auth error: {str(e)}")
            return False, None

    async def on_connect(self, websocket: WebSocket) -> User | None:
        """
        Handle WebSocket connection with authentication.
        Returns authenticated user if successful, otherwise closes the connection.
        """
        success, user = await self.authenticate(websocket)

        if not success:
            # Authentication failed, close the connection
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
            raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION)

        # Authentication successful, return the user
        return user
