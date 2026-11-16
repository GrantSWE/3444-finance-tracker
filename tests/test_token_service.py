import unittest

from token_service import (
    generate_auth_token,
    generate_recovery_token,
    hash_token,
    token_matches_hash,
    verify_auth_token,
    verify_recovery_token,
)


class TokenServiceTests(unittest.TestCase):
    secret = "test-secret-key"

    def test_auth_token_is_valid_before_expiration(self):
        token = generate_auth_token(42, self.secret, expires_in=60, now=1000)

        payload = verify_auth_token(token, self.secret, now=1059)

        self.assertEqual(payload["user_id"], 42)
        self.assertEqual(payload["exp"], 1060)

    def test_auth_token_expires_at_deadline(self):
        token = generate_auth_token(42, self.secret, expires_in=60, now=1000)

        self.assertIsNone(verify_auth_token(token, self.secret, now=1060))

    def test_tampered_token_is_rejected(self):
        token = generate_recovery_token(7, self.secret, now=1000)
        payload, signature = token.split(".", 1)
        replacement = "A" if payload[-1] != "A" else "B"
        tampered = f"{payload[:-1]}{replacement}.{signature}"

        self.assertIsNone(verify_recovery_token(tampered, self.secret, now=1001))

    def test_wrong_secret_is_rejected(self):
        token = generate_recovery_token(7, self.secret, now=1000)

        self.assertIsNone(verify_recovery_token(token, "wrong-secret", now=1001))

    def test_recovery_tokens_include_unique_nonce(self):
        first = generate_recovery_token(7, self.secret, now=1000)
        second = generate_recovery_token(7, self.secret, now=1000)

        self.assertNotEqual(first, second)
        self.assertEqual(verify_recovery_token(first, self.secret, now=1001)["user_id"], 7)

    def test_only_token_hash_needs_to_be_stored(self):
        token = generate_recovery_token(7, self.secret, now=1000)
        stored_hash = hash_token(token)

        self.assertNotEqual(token, stored_hash)
        self.assertTrue(token_matches_hash(token, stored_hash))
        self.assertFalse(token_matches_hash(f"{token}x", stored_hash))


if __name__ == "__main__":
    unittest.main()
