import ast
import os

from fastapi import Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from msal.oauth2cli.oidc import decode_id_token
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.routing import Match


class AuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request["type"] == "websocket":
            response = await call_next(request)
            return response
        locked_swagger, swagger_route = self.__protect_swagger(request=request)
        if locked_swagger and swagger_route:
            return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"message": "Swagger page disabled."})

        if not locked_swagger and swagger_route:
            response = await call_next(request)
            return response

        if "Authorization" not in request.headers:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED, content={"message": "Missing Authorization header."}
            )

        user_key = os.environ.get("AUTH_USER_KEY")
        group_key = os.environ.get("AUTH_ROLE_KEY")

        try:
            decoded_token = decode_id_token(request.headers["Authorization"].split("Bearer ")[-1])
        except Exception:
            return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"message": "Invalid token."})
        token_user = decoded_token.get("preferred_username", decoded_token.get("unique_name"))
        token_roles = decoded_token.get("roles", [])

        req_body = await request.body()
        if req_body:
            req_body = str(await request.json())
        else:
            req_body = "None"

        path_params = {}
        routes = request.app.router.routes
        for route in routes:
            match, scope = route.matches(request)
            if match == Match.FULL:
                path_params.update(scope["path_params"])

        query_user = request.query_params.get(user_key, "")
        path_user = path_params.get(user_key, "")

        query_group_name = request.query_params.get(group_key, "")
        path_group_name = path_params.get(group_key, "")

        user_matches = [user for user in [req_body, query_user, path_user] if token_user in user]
        group_matches = [
            group for group in [query_group_name, path_group_name] if group in ".".join(token_roles) and group != ""
        ]
        token_role_match = [role for role in token_roles if role in req_body]

        warn_message = "You are not authorized to be here. Log in attempt has been recorded."

        if user_key and group_key:
            if (
                len(user_matches) == 0 and (len(group_matches) == 0 and len(token_role_match) == 0)
            ) and not request.url.path.endswith("/version"):
                return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"message": warn_message})

        elif user_key:
            if len(user_matches) == 0:
                return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"message": warn_message})

        elif group_key:
            if len(group_matches) == 0 and len(token_role_match) == 0:
                return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"message": warn_message})

        request.state.identity = decoded_token

        response = await call_next(request)
        return response

    def __protect_swagger(self, request: Request):
        protect_swagger = os.environ.get("AUTH_LOCK_SWAGGER", False)
        if isinstance(protect_swagger, str):
            protect_swagger = ast.literal_eval(protect_swagger.lower().capitalize())
        swagger_route = "docs" in request.url.path or "openapi" in request.url.path
        if protect_swagger and swagger_route:
            return True, swagger_route
        return False, swagger_route
