import unittest

from peccancy_partner import PartnerClient, safe_equal, sign
from peccancy_partner.signature import now_sec

SECRET = "test-secret"


def _money(n: float) -> str:
    return f"{float(n):.2f}"


def _signed_callback(tx="tx_1", status="success", amount=9.99, timestamp=None):
    ts = now_sec() if timestamp is None else timestamp
    cb = {"transaction_id": tx, "status": status, "amount": amount, "timestamp": ts}
    cb["signature"] = sign(f"{tx}:{status}:{_money(amount)}:{ts}", SECRET)
    return cb


class SmokeTest(unittest.TestCase):
    def test_sign_is_stable_and_hex(self):
        a = sign("partner:desc:123", SECRET)
        self.assertEqual(a, sign("partner:desc:123", SECRET))
        self.assertEqual(len(a), 64)
        int(a, 16)  # valid hex
        self.assertTrue(safe_equal(a, a))

    def test_verify_callback_roundtrip(self):
        cb = _signed_callback()
        self.assertTrue(PartnerClient.verify_callback(cb, SECRET))

    def test_verify_callback_rejects_tampered_amount(self):
        cb = _signed_callback()
        cb["amount"] = 1.00  # signature no longer matches
        self.assertFalse(PartnerClient.verify_callback(cb, SECRET))

    def test_verify_callback_rejects_stale_timestamp(self):
        cb = _signed_callback(timestamp=now_sec() - 10_000)
        self.assertFalse(PartnerClient.verify_callback(cb, SECRET))

    def test_verify_callback_rejects_wrong_secret(self):
        cb = _signed_callback()
        self.assertFalse(PartnerClient.verify_callback(cb, "other-secret"))


if __name__ == "__main__":
    unittest.main()
