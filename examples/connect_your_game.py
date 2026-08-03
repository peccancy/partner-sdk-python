"""Connect-your-game example: the full dispute lifecycle for one match.

Run:  PECCANCY_PARTNER_ID=... PECCANCY_PARTNER_SECRET=... python examples/connect_your_game.py
"""

import os
import sys
from datetime import datetime, timedelta, timezone

from peccancy_partner import PartnerClient, PartnerApiError


def require_env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        sys.exit(f"missing env {name}")
    return v


def main() -> None:
    client = PartnerClient(
        os.environ.get("PECCANCY_BASE_URL", "https://disputes.online/partner"),
        partner_id=require_env("PECCANCY_PARTNER_ID"),
        secret=require_env("PECCANCY_PARTNER_SECRET"),
    )

    now = datetime.now(timezone.utc)
    try:
        # 1) A new match starts -> open a dispute.
        dispute = client.create_dispute(
            description="Who wins the Alias round?",
            variants=["Red Team", "Blue Team"],
            stop_date=now + timedelta(minutes=2),
            finish_date=now + timedelta(minutes=20),
            min_bet=1,
        )
        print("created dispute:", dispute["id"])

        # 2) The round begins -> close betting and mark in-progress.
        client.stop_bets(dispute["id"])
        client.start_game(dispute["id"])
        print("betting closed, game in progress")

        # 3) The round ends -> declare the winner by its name.
        client.set_winner(dispute["id"], "Red Team")
        print("winner set: Red Team")
    except PartnerApiError as e:
        sys.exit(f"API error {e.status_code}: {e.body}")


if __name__ == "__main__":
    main()
