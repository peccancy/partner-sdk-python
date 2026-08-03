"""HMAC-SHA256 signing primitives, matching the Peccancy platform's scheme.

You normally don't call these directly — :class:`PartnerClient` does it for you.
"""

import hashlib
import hmac
import time


def sign(payload: str, secret: str) -> str:
    """Return the lowercase hex HMAC-SHA256 of ``payload`` keyed by ``secret``."""
    return hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def safe_equal(a: str, b: str) -> bool:
    """Constant-time comparison of two hex signatures."""
    return hmac.compare_digest(a, b)


def now_sec() -> int:
    """Current unix time in seconds."""
    return int(time.time())
