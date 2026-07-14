from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Callable


_ALGORITHM = "scrypt-n16384-r8-p1" if hasattr(hashlib, "scrypt") else "pbkdf2-sha256-210000"
_SALT_BYTES = 16
_HASH_BYTES = 32
_ATTEMPTS = 3


class AccessGateError(ValueError):
    """Raised when the local access-gate configuration is invalid."""


def _password_hash(password: str, salt: bytes) -> bytes:
    if _ALGORITHM.startswith("scrypt"):
        return hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=16_384, r=8, p=1, dklen=_HASH_BYTES
        )
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 210_000, _HASH_BYTES)


def configure_gate(
    gate_path: Path, password: str, *, salt_factory: Callable[[int], bytes] = os.urandom
) -> None:
    """Store a salted password verifier; the plaintext password is never persisted."""
    if not isinstance(password, str) or not password:
        raise AccessGateError("Access-gate password must not be empty")
    salt = salt_factory(_SALT_BYTES)
    if not isinstance(salt, bytes) or len(salt) != _SALT_BYTES:
        raise AccessGateError("Access-gate salt factory returned an invalid salt")
    record = {
        "algorithm": _ALGORITHM,
        "salt": base64.b64encode(salt).decode("ascii"),
        "password_hash": base64.b64encode(_password_hash(password, salt)).decode("ascii"),
    }
    gate_path = Path(gate_path)
    gate_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(gate_path.parent, 0o700)
    gate_path.write_text(json.dumps(record, sort_keys=True) + "\n")
    os.chmod(gate_path, 0o600)


def default_gate_path() -> Path:
    return Path.home() / ".caelus" / "access-gate.json"


def gate_is_configured(gate_path: Path) -> bool:
    return Path(gate_path).is_file()


def _matches_password(gate_path: Path, password: str) -> bool:
    try:
        record = json.loads(Path(gate_path).read_text())
        if not isinstance(record, dict) or set(record) != {"algorithm", "salt", "password_hash"}:
            raise AccessGateError("Access-gate configuration is invalid")
        if record["algorithm"] != _ALGORITHM:
            raise AccessGateError("Access-gate configuration uses an unsupported algorithm")
        salt = base64.b64decode(record["salt"], validate=True)
        expected = base64.b64decode(record["password_hash"], validate=True)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        if isinstance(exc, AccessGateError):
            raise
        raise AccessGateError("Access-gate configuration is invalid") from exc
    if len(salt) != _SALT_BYTES or len(expected) != _HASH_BYTES:
        raise AccessGateError("Access-gate configuration is invalid")
    actual = _password_hash(password, salt)
    return hmac.compare_digest(actual, expected)


def require_access(
    gate_path: Path,
    *,
    prompt: Callable[[str], str],
    notify: Callable[[str], None],
) -> bool:
    """Prompt at most three times and return whether this invocation may proceed."""
    for attempt in range(1, _ATTEMPTS + 1):
        try:
            password = prompt("Caelus access password: ")
        except (EOFError, KeyboardInterrupt):
            notify("Access cancelled.")
            return False
        if _matches_password(gate_path, password):
            return True
        remaining = _ATTEMPTS - attempt
        if remaining:
            notify(f"Incorrect password. {remaining} attempt{'s' if remaining != 1 else ''} remaining.")
    notify("Access denied after 3 attempts.")
    return False
