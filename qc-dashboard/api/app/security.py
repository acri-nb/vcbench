import secrets
import hashlib
import os
from enum import Enum
from typing import Optional

from fastapi import Depends, Header, HTTPException, status

from api.app import settings


class Role(str, Enum):
    OPERATOR = "operator"
    REVIEWER = "reviewer"
    ADMIN = "admin"


ROLE_ORDER = {
    Role.OPERATOR: 1,
    Role.REVIEWER: 2,
    Role.ADMIN: 3,
}


def _configured_keys() -> dict[str, Role]:
    keys: dict[str, Role] = {}
    for raw_entry in settings.API_KEYS.split(","):
        entry = raw_entry.strip()
        if not entry:
            continue
        if ":" not in entry:
            continue
        role_name, key = entry.split(":", 1)
        role_name = role_name.strip().lower()
        key = key.strip()
        if not key:
            continue
        try:
            keys[key] = Role(role_name)
        except ValueError:
            continue
    return keys


def get_current_role(
    x_vcbench_api_key: Optional[str] = Header(default=None, alias="X-VCBench-API-Key"),
) -> Role:
    keys = _configured_keys()
    if settings.AUTH_DISABLED or not settings.API_KEYS.strip():
        return Role.ADMIN
    if not keys:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="VCBENCH_API_KEYS is set but contains no valid role:key entries",
        )

    if not x_vcbench_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-VCBench-API-Key header",
        )

    for configured_key, role in keys.items():
        if secrets.compare_digest(x_vcbench_api_key, configured_key):
            return role

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid API key",
    )


def require_role(*allowed_roles: Role):
    minimum = max(ROLE_ORDER[role] for role in allowed_roles)

    def dependency(role: Role = Depends(get_current_role)) -> Role:
        if ROLE_ORDER[role] < minimum:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role for this action",
            )
        return role

    return dependency


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600_000)
    return f"pbkdf2_sha256$600000${salt.hex()}${digest.hex()}"
