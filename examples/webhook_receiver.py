"""Webhook receiver example: verify signed callbacks from the platform.

Point your partner's callback_url at http(s)://your-host/peccancy/callback

Run:  PECCANCY_PARTNER_SECRET=... python examples/webhook_receiver.py
"""

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

from peccancy_partner import PartnerClient

SECRET = os.environ.get("PECCANCY_PARTNER_SECRET")
if not SECRET:
    raise SystemExit("missing env PECCANCY_PARTNER_SECRET")


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        if self.path != "/peccancy/callback":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            self.send_response(400)
            self.end_headers()
            return

        if not PartnerClient.verify_callback(body, SECRET):
            self.send_response(401)
            self.end_headers()
            return

        # Verified & fresh — safe to act on.
        print("callback:", body.get("transaction_id"), body.get("status"), body.get("amount"))
        # ... credit the user / mark the order paid ...

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")


if __name__ == "__main__":
    print("listening on :3000/peccancy/callback")
    HTTPServer(("", 3000), Handler).serve_forever()
