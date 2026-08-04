# peccancy-partner-sdk (Python)

[![CI](https://github.com/peccancy/partner-sdk-python/actions/workflows/ci.yml/badge.svg)](https://github.com/peccancy/partner-sdk-python/actions/workflows/ci.yml)
[![Partner API docs](https://img.shields.io/badge/docs-Partner%20API-blue)](https://docs.disputes.online/swagger/index.html)

Official Python SDK for the **Peccancy** disputes/betting platform.

Connect your game or app once and let your users bet on outcomes: create disputes, control
their lifecycle, declare winners, take payments, and verify signed result webhooks. Every
request is authenticated for you with HMAC-SHA256 — you never build a signature by hand.

- Pure standard library (no dependencies), Python 3.8+
- Same surface as our Node / PHP / Go SDKs

## Install

```bash
pip install peccancy-partner-sdk
```

## Get credentials

1. Register as a partner at **https://disputes.online/profile?tab=partners** and open your partner.
2. Copy your **`partner_id`** (UUID) and **`secret`**.
3. Set a **`callback_url`** on your partner if you want result/payment webhooks.

## Quickstart

```python
from datetime import datetime, timedelta, timezone
from peccancy_partner import PartnerClient

client = PartnerClient(
    "https://disputes.online/partner",  # the partner API base
    partner_id=os.environ["PECCANCY_PARTNER_ID"],
    secret=os.environ["PECCANCY_PARTNER_SECRET"],
)

now = datetime.now(timezone.utc)
dispute = client.create_dispute(
    description="Who wins Round 5?",
    variants=["Alice", "Bob"],
    stop_date=now + timedelta(minutes=5),
    finish_date=now + timedelta(minutes=30),
)
print(dispute["id"])
```

## Disputes

```python
dispute = client.create_dispute(
    description="Who wins?",
    variants=["Team A", "Team B"],       # or [{"description": "Team A"}, ...]
    stop_date="2026-01-01T12:00:00Z",
    finish_date="2026-01-01T13:00:00Z",
    min_bet=1,          # optional
    max_bet=100,        # optional
    lang="en",          # optional (default "en")
    is_closed=False,    # optional — if True, only you resolve the winner
)

client.stop_bets(dispute["id"])            # close betting
client.start_game(dispute["id"])           # mark in-progress (optional)
client.set_winner(dispute["id"], "Team A") # declare winner by variant description
```

## Payments

```python
# Charge a known user by email / phone / id:
tx = client.init_payment(9.99, {"type": "email", "value": "user@example.com"}, "Coins pack")

# Or a hosted payment link (invoice):
invoice = client.create_invoice(19.99, "Tournament entry")
print(invoice["invoice_url"])
```

## Webhooks (results & payments)

The platform POSTs a signed JSON callback to your `callback_url`. **Always verify it**:

```python
from peccancy_partner import PartnerClient

# body = json.loads(request_body)
if not PartnerClient.verify_callback(body, os.environ["PECCANCY_PARTNER_SECRET"]):
    return 401, "bad signature"

# ... credit the user / mark the order paid ...
return 200, "ok"
```

Callback body: `{ "transaction_id", "status", "amount", "timestamp", "signature" }`.
`verify_callback` checks the HMAC signature **and** timestamp freshness (±120s).

## Authentication (under the hood)

The SDK adds `X-Partner-ID`, `X-Partner-Timestamp`, `X-Partner-Signature` headers (payment
endpoints put signature/timestamp in the body). The signature is
`hmac.new(secret, payload, sha256).hexdigest()`, where `payload` is a colon-joined string:

| Operation | Signed payload |
|-----------|----------------|
| create_dispute | `partner_id:description:timestamp` |
| stop_bets / start_game | `partner_id:dispute_id:timestamp` |
| set_winner | `partner_id:dispute_id:winner_team_name:timestamp` |
| init_payment | `partner_id:amount(2dp):user_value:timestamp` |
| create_invoice | `partner_id:amount(2dp):description:timestamp` |
| callback (inbound) | `transaction_id:status:amount(2dp):timestamp` |

Keep your server clock in sync (NTP) — the platform rejects timestamps more than 120s off.

## Errors

Non-2xx responses raise `peccancy_partner.PartnerApiError` with `.status_code` and `.body`.

## Examples

- [`examples/connect_your_game.py`](./examples/connect_your_game.py)
- [`examples/webhook_receiver.py`](./examples/webhook_receiver.py)

## Links

- **Register / get credentials:** https://disputes.online/profile?tab=partners
- **Partner API reference:** https://docs.disputes.online/swagger/index.html
- **Other SDKs:** [Node](https://github.com/peccancy/partner-sdk-node) · [PHP](https://github.com/peccancy/partner-sdk-php) · [Python](https://github.com/peccancy/partner-sdk-python) · [Go](https://github.com/peccancy/partner-sdk-go)

## License

MIT
