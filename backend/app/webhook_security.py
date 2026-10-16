import hashlib
import hmac
from dataclasses import dataclass, field
from threading import Lock


def verify_hmac_signature(
    *,
    payload: bytes,
    signature: str,
    secret: str,
    prefix: str = "sha256=",
) -> bool:
    if not signature or not secret:
        return False

    supplied = signature.removeprefix(prefix).strip()
    if len(supplied) != 64:
        return False

    expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(supplied, expected)


@dataclass
class IdempotencyLedger:
    _seen: set[str] = field(default_factory=set)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False, compare=False)

    def accept(self, event_id: str) -> bool:
        normalized = event_id.strip()
        if not normalized:
            return False
        # Atomic check-and-insert prevents duplicate callbacks being accepted
        # concurrently in one process. Production still requires durable
        # idempotency across workers and restarts.
        with self._lock:
            if normalized in self._seen:
                return False
            self._seen.add(normalized)
            return True
