import json
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union

from .errors import PartnerApiError
from .signature import now_sec, safe_equal, sign

DateInput = Union[datetime, str]
VariantInput = Union[str, Mapping[str, Any]]


def _to_iso(d: Optional[DateInput]) -> Optional[str]:
    if d is None:
        return None
    if isinstance(d, datetime):
        return d.isoformat()
    return str(d)


def _money(n: float) -> str:
    return f"{float(n):.2f}"


class PartnerClient:
    """Entry point of the SDK. Construct once with your credentials and reuse.

    Every call is authenticated for you via HMAC-SHA256 + a fresh timestamp::

        client = PartnerClient("https://disputes.online/partner", partner_id, secret)
        dispute = client.create_dispute(description="...", variants=["A", "B"],
                                        stop_date=..., finish_date=...)
    """

    def __init__(self, base_url: str, partner_id: str, secret: str, timeout: float = 15.0):
        if not base_url:
            raise ValueError("base_url is required")
        if not partner_id:
            raise ValueError("partner_id is required")
        if not secret:
            raise ValueError("secret is required")
        self._base_url = base_url.rstrip("/")
        self._partner_id = partner_id
        self._secret = secret
        self._timeout = timeout

    # ---- Disputes ----

    def create_dispute(
        self,
        description: str,
        variants: Sequence[VariantInput],
        finish_date: DateInput,
        stop_date: DateInput,
        *,
        min_bet: Optional[int] = None,
        max_bet: Optional[int] = None,
        lang: Optional[str] = None,
        is_closed: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Create a dispute (question + 2–100 outcomes). ``variants`` may be strings or
        ``{"description": ...}`` mappings. Returns the created dispute."""
        ts = now_sec()
        payload = f"{self._partner_id}:{description}:{ts}"
        norm: List[Dict[str, Any]] = [
            dict(v) if isinstance(v, Mapping) else {"description": v} for v in variants
        ]
        body: Dict[str, Any] = {
            "description": description,
            "variants": norm,
            "finish_date": _to_iso(finish_date),
            "stop_date": _to_iso(stop_date),
        }
        if min_bet is not None:
            body["min_bet"] = min_bet
        if max_bet is not None:
            body["max_bet"] = max_bet
        if lang is not None:
            body["lang"] = lang
        if is_closed is not None:
            body["is_closed"] = is_closed

        data = self._header_signed("POST", "/api/v1/partner/disputes", payload, ts, body)
        return data.get("data", {})

    def stop_bets(self, dispute_id: str) -> None:
        """Close betting on a dispute."""
        ts = now_sec()
        payload = f"{self._partner_id}:{dispute_id}:{ts}"
        self._header_signed("PUT", f"/api/v1/partner/disputes/{dispute_id}/stopbet", payload, ts, None)

    def start_game(self, dispute_id: str) -> None:
        """Mark a dispute in-progress."""
        ts = now_sec()
        payload = f"{self._partner_id}:{dispute_id}:{ts}"
        self._header_signed("PUT", f"/api/v1/partner/disputes/{dispute_id}/startgame", payload, ts, None)

    def set_winner(self, dispute_id: str, winner_team_name: str) -> None:
        """Declare the winning outcome by its variant description (team name)."""
        ts = now_sec()
        payload = f"{self._partner_id}:{dispute_id}:{winner_team_name}:{ts}"
        self._header_signed(
            "POST",
            f"/api/v1/partner/disputes/{dispute_id}/winner",
            payload,
            ts,
            {"winner_team_name": winner_team_name},
        )

    # ---- Payments ----

    def init_payment(self, amount: float, user_identifier: Mapping[str, str], description: str) -> Dict[str, Any]:
        """Charge a known user. ``user_identifier`` is ``{"type": "email"|"phone"|"id", "value": ...}``."""
        ts = now_sec()
        value = user_identifier.get("value", "")
        payload = f"{self._partner_id}:{_money(amount)}:{value}:{ts}"
        return self._body_signed(
            "/partner/api/v1/init",
            {
                "id": self._partner_id,
                "amount": amount,
                "user_identifier": {"type": user_identifier.get("type", ""), "value": value},
                "description": description,
                "signature": sign(payload, self._secret),
                "timestamp": ts,
            },
        )

    def create_invoice(self, amount: float, description: str) -> Dict[str, Any]:
        """Create a hosted payment link (invoice)."""
        ts = now_sec()
        payload = f"{self._partner_id}:{_money(amount)}:{description}:{ts}"
        return self._body_signed(
            "/partner/api/v1/invoice",
            {
                "amount": amount,
                "description": description,
                "signature": sign(payload, self._secret),
                "timestamp": ts,
            },
        )

    # ---- Webhooks ----

    @staticmethod
    def verify_callback(cb: Mapping[str, Any], secret: str, max_skew_sec: int = 120) -> bool:
        """Verify a callback POSTed to your callback_url. True when the signature is valid
        and the timestamp is fresh (default ±120s). Always verify before acting on it."""
        sig = cb.get("signature")
        if not isinstance(sig, str):
            return False
        amount = float(cb.get("amount", 0))
        payload = f"{cb.get('transaction_id', '')}:{cb.get('status', '')}:{_money(amount)}:{cb.get('timestamp', '')}"
        if not safe_equal(sign(payload, secret), sig):
            return False
        age = abs(now_sec() - int(cb.get("timestamp", 0)))
        return age <= max_skew_sec

    # ---- internals ----

    def _header_signed(self, method: str, path: str, payload: str, ts: int, body: Optional[dict]) -> Dict[str, Any]:
        return self._request(
            method,
            path,
            {
                "X-Partner-ID": self._partner_id,
                "X-Partner-Timestamp": str(ts),
                "X-Partner-Signature": sign(payload, self._secret),
            },
            body,
        )

    def _body_signed(self, path: str, body: dict) -> Dict[str, Any]:
        return self._request("POST", path, {"X-Partner-ID": self._partner_id}, body)

    def _request(self, method: str, path: str, headers: Dict[str, str], body: Optional[dict]) -> Dict[str, Any]:
        url = self._base_url + path
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", **headers},
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", "replace")
            raise PartnerApiError(f"Peccancy API {method} {path} -> {e.code}", e.code, text) from None
        except urllib.error.URLError as e:
            raise PartnerApiError(f"request failed: {e.reason}", 0, "") from None
