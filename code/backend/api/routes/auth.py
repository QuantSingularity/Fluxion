"""
Authentication API Routes for Fluxion Backend
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, field_validator
from services.auth.jwt_service import DeviceInfo, JWTService
from services.user.user_service import UserService, UserType

router = APIRouter()
security = HTTPBearer(auto_error=False)

# Module-level singletons.
#
# These services keep their state (registered users, sessions, token
# blacklists) in memory. Instantiating them per request - as the previous
# `return UserService()` factories did - meant a user registered in one
# request no longer existed by the time the login request arrived, and
# revoked tokens were never actually revoked.
_jwt_service = JWTService()
_user_service = UserService()
# UserService builds its own JWTService internally; point it at the shared
# instance so session/token revocations are visible to route authentication.
_user_service.jwt_service = _jwt_service


def get_jwt_service() -> JWTService:
    return _jwt_service


def get_user_service() -> UserService:
    return _user_service


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    jwt_service: JWTService = Depends(get_jwt_service),
) -> Dict[str, Any]:
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authorization required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    try:
        import jwt as _jwt

        payload = _jwt.decode(
            token,
            jwt_service.secret_key,
            algorithms=[jwt_service.algorithm],
            issuer=jwt_service.issuer,
            audience=jwt_service.audience,
        )
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Reject access tokens that were revoked (logout / session revocation).
    try:
        if await jwt_service._is_token_blacklisted(token):
            raise HTTPException(
                status_code=401,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except HTTPException:
        raise
    except Exception:
        # Blacklist backend unavailable - fall through with a valid signature.
        pass
    # Tokens minted by create_token_pair carry the user id in the standard
    # "sub" claim only; downstream routes read current_user["user_id"], which
    # previously raised KeyError (HTTP 500) for every real login token.
    if "user_id" not in payload and "sub" in payload:
        payload["user_id"] = payload["sub"]
    payload["_raw_token"] = token
    return payload


# --- Request schemas ---


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    confirm_password: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    country_of_residence: Optional[str] = None
    user_type: str = "individual"
    terms_accepted: bool
    privacy_accepted: bool

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        import re

        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search("[A-Z]", v):
            raise ValueError("Password must contain uppercase letter")
        if not re.search("[a-z]", v):
            raise ValueError("Password must contain lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain a digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain a special character")
        return v

    @field_validator("terms_accepted")
    @classmethod
    def validate_terms(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Terms and conditions must be accepted")
        return v

    def model_post_init(self, __context: Any) -> None:
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: str

    def model_post_init(self, __context: Any) -> None:
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")


class VerifyEmailRequest(BaseModel):
    token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str


# --- Routes ---


@router.post("/register", status_code=201, summary="Register a new user")
async def register_user(
    request: RegisterRequest,
    http_request: Request,
    user_service: UserService = Depends(get_user_service),
):
    try:
        device_info = DeviceInfo(
            ip_address=http_request.client.host if http_request.client else "unknown",
            user_agent=http_request.headers.get("user-agent", ""),
            device_id=http_request.headers.get("x-device-id"),
        )
        profile_data = {
            "username": request.username,
            "first_name": request.first_name,
            "last_name": request.last_name,
            "phone_number": request.phone_number,
            "country_of_residence": request.country_of_residence,
        }
        # Map the requested account type instead of always registering
        # individuals (admin cannot be self-assigned at registration).
        try:
            requested_type = UserType(request.user_type.lower())
        except ValueError:
            requested_type = UserType.INDIVIDUAL
        if requested_type == UserType.ADMIN:
            requested_type = UserType.INDIVIDUAL
        result = await user_service.register_user(
            email=request.email,
            password=request.password,
            user_type=requested_type,
            profile_data=profile_data,
            device_info=device_info,
        )
        return {
            "success": True,
            "data": {
                "user": {
                    "email": result.get("email"),
                    "username": request.username,
                    "user_id": result.get("user_id"),
                    "status": result.get("status"),
                },
                "verification_token": result.get("verification_token"),
            },
            "message": "User registered successfully",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Registration failed")


@router.post("/login", summary="Authenticate user")
async def login_user(
    request: LoginRequest,
    http_request: Request,
    user_service: UserService = Depends(get_user_service),
):
    try:
        device_info = DeviceInfo(
            ip_address=http_request.client.host if http_request.client else "unknown",
            user_agent=http_request.headers.get("user-agent", ""),
        )
        result = await user_service.authenticate_user(
            email=request.email,
            password=request.password,
            device_info=device_info,
        )
        return {"success": True, "data": result, "message": "Authentication successful"}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Authentication failed")


@router.post("/refresh", summary="Refresh access token")
async def refresh_token(
    request: RefreshTokenRequest,
    jwt_service: JWTService = Depends(get_jwt_service),
):
    try:
        payload = jwt_service.verify_refresh_token(request.refresh_token)
        # Carry the validated claims forward instead of resetting every
        # account to the hardcoded "user" role on refresh.
        token_data = {
            "user_id": payload.get("sub", ""),
            "session_id": payload.get("sid", ""),
            "email": payload.get("email", ""),
            "roles": payload.get("roles", ["user"]),
            "permissions": payload.get("permissions", []),
            "mfa_verified": payload.get("mfa", False),
        }
        new_access_token = jwt_service.create_access_token(token_data)
        new_refresh_token = jwt_service.create_refresh_token(token_data)
        return {
            "success": True,
            "data": {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
            },
            "message": "Token refreshed",
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Token refresh failed")


@router.post("/logout", summary="Logout user")
async def logout_user(
    current_user: Dict = Depends(get_current_user),
    jwt_service: JWTService = Depends(get_jwt_service),
):
    token = current_user.get("_raw_token")
    if token:
        try:
            await jwt_service.revoke_token(token, reason="User logout")
        except Exception:
            pass  # Logout should not fail even if revocation storage is down
    return {"success": True, "message": "Logged out successfully"}


@router.post("/verify-email", summary="Verify email address")
async def verify_email(
    request: VerifyEmailRequest,
    user_service: UserService = Depends(get_user_service),
):
    try:
        result = await user_service.verify_email(request.token)
        return {"success": True, "data": result, "message": "Email verified"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Verification failed")


@router.post("/change-password", summary="Change password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: Dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    try:
        user_id = current_user.get("sub", "")
        result = await user_service.change_password(
            user_id=user_id,
            current_password=request.current_password,
            new_password=request.new_password,
        )
        return {"success": True, "data": result, "message": "Password changed"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Password change failed")


@router.post("/password-reset", summary="Request password reset")
async def request_password_reset(
    request: PasswordResetRequest,
    user_service: UserService = Depends(get_user_service),
):
    # Always respond identically to avoid account enumeration. In production
    # the token is delivered out-of-band (email); it is never returned here.
    try:
        await user_service.request_password_reset(request.email)
    except Exception:
        pass
    return {"success": True, "message": "Password reset email sent if account exists"}


@router.post("/password-reset/confirm", summary="Confirm password reset")
async def confirm_password_reset(
    request: PasswordResetConfirmRequest,
    user_service: UserService = Depends(get_user_service),
):
    try:
        result = await user_service.confirm_password_reset(
            reset_token=request.token,
            new_password=request.new_password,
        )
        return {
            "success": True,
            "data": result,
            "message": "Password reset successfully",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Password reset failed")


@router.get("/me", summary="Get current user")
async def get_current_user_info(current_user: Dict = Depends(get_current_user)):
    return {
        "success": True,
        "data": {
            "user_id": current_user.get("sub"),
            "email": current_user.get("email"),
        },
    }


@router.get("/sessions", summary="Get user sessions")
async def get_sessions(
    current_user: Dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    try:
        user_id = current_user.get("user_id") or current_user.get("sub", "")
        sessions = await user_service.get_user_sessions(user_id)
        return {"success": True, "data": sessions}
    except ValueError:
        return {"success": True, "data": {"active_sessions": [], "login_history": []}}
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to retrieve sessions")


@router.delete("/sessions/{session_id}", summary="Revoke session")
async def revoke_session(
    session_id: str,
    current_user: Dict = Depends(get_current_user),
    jwt_service: JWTService = Depends(get_jwt_service),
):
    # Only allow users to revoke their own sessions.
    user_id = current_user.get("user_id") or current_user.get("sub", "")
    session_data = jwt_service.active_sessions.get(session_id)
    if session_data and session_data.get("user_id") != user_id:
        raise HTTPException(
            status_code=403, detail="Cannot revoke another user's session"
        )
    try:
        await jwt_service._revoke_session(session_id, "Revoked by user")
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to revoke session")
    return {"success": True, "message": "Session revoked"}


class VerifyMFARequest(BaseModel):
    mfa_code: str


class DisableMFARequest(BaseModel):
    password: str


@router.post("/mfa/setup", summary="Setup MFA")
async def setup_mfa(
    current_user: Dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    try:
        user_id = current_user.get("user_id") or current_user.get("sub", "")
        result = await user_service.enable_mfa(user_id)
        return {"success": result.get("success", True), "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="MFA setup failed")


@router.post("/mfa/verify", summary="Verify MFA")
async def verify_mfa(
    request: VerifyMFARequest,
    current_user: Dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    try:
        user_id = current_user.get("user_id") or current_user.get("sub", "")
        result = await user_service.verify_mfa_setup(user_id, request.mfa_code)
        return {"success": True, "data": result, "message": "MFA verified"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="MFA verification failed")


@router.post("/mfa/disable", summary="Disable MFA")
async def disable_mfa(
    request: DisableMFARequest,
    current_user: Dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    try:
        user_id = current_user.get("user_id") or current_user.get("sub", "")
        result = await user_service.disable_mfa(user_id, request.password)
        return {"success": True, "data": result, "message": "MFA disabled"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="MFA disable failed")


@router.post("/api-keys", summary="Create API key")
async def create_api_key(current_user: Dict = Depends(get_current_user)):
    from uuid import uuid4

    return {
        "success": True,
        "data": {
            "api_key_id": str(uuid4()),
            "key": "flx_" + str(uuid4()).replace("-", ""),
        },
    }


@router.get("/api-keys", summary="List API keys")
async def list_api_keys(current_user: Dict = Depends(get_current_user)):
    return {"success": True, "data": {"api_keys": []}}


@router.delete("/api-keys/{key_id}", summary="Revoke API key")
async def revoke_api_key(key_id: str, current_user: Dict = Depends(get_current_user)):
    return {"success": True, "message": "API key revoked"}
