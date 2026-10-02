from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import hashlib
import hmac
import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from backend.app.core.config import settings

security_scheme = HTTPBearer(auto_error=False)

READ_ONLY_ROLES = {"VIEWER", "DEMO_USER", "DEMO USER", "GUEST"}
READ_ONLY_OPERATORS = {"SIH26012_REVIEWER", "VIEWER", "DEMO_USER", "GUEST"}


def _get_signing_key() -> str:
    if settings.SECRET_KEY:
        return settings.SECRET_KEY
    # Derive deterministic environment runtime key if SECRET_KEY not set in env
    return hashlib.sha256(f"SIH26012_AEROCADASTRE_{settings.DATABASE_URL}".encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    salt = "sih26012_aerocadastre_salt"
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    ).hex()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hmac.compare_digest(hash_password(plain_password), hashed_password)


def create_access_token(
    subject: str,
    role: str = "SURVEYOR",
    expires_delta: Optional[timedelta] = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode: Dict[str, Any] = {
        "sub": subject,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(to_encode, _get_signing_key(), algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(
            token,
            _get_signing_key(),
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired.",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        ) from exc


def require_authenticated_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> Dict[str, Any]:
    """Strict authentication dependency for protected endpoints."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Bearer token required.",
        )
    return decode_access_token(credentials.credentials)


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    x_operator_role: Optional[str] = Header(default=None, alias="X-Operator-Role"),
) -> Dict[str, Any]:
    """
    Validates Bearer token if provided; if an invalid token is sent, raises 401.
    Also enforces RBAC so VIEWER / DEMO_USER roles receive 403 Forbidden on mutating endpoints.
    """
    user_ctx: Dict[str, Any]
    if credentials is not None and credentials.credentials:
        user_ctx = decode_access_token(credentials.credentials)
    elif settings.REQUIRE_AUTH_FOR_MUTATIONS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required when REQUIRE_AUTH_FOR_MUTATIONS is enabled.",
        )
    else:
        role_val = (x_operator_role or "SURVEYOR").strip().upper()
        user_ctx = {"sub": "Surveyor_Verifier_01", "role": role_val}

    role_upper = str(user_ctx.get("role", "SURVEYOR")).strip().upper()
    sub_upper = str(user_ctx.get("sub", "")).strip().upper()
    if role_upper in READ_ONLY_ROLES or sub_upper in READ_ONLY_OPERATORS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{user_ctx.get('role')}' is read-only and is not authorized to mutate cadastral records.",
        )
    return user_ctx


def assert_operator_can_mutate(operator_id: Optional[str]) -> None:
    """Rejects mutations when operator_id belongs to a read-only demo/viewer account."""
    if not operator_id:
        return
    op_upper = operator_id.strip().upper()
    if op_upper in READ_ONLY_OPERATORS or op_upper in READ_ONLY_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Operator '{operator_id}' has read-only viewer permissions and cannot modify records.",
        )
