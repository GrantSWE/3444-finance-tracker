import os
import smtplib
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from werkzeug.security import check_password_hash, generate_password_hash

import app as app_module


class PasswordRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_directory.name, "test.db")
        app_module.app.config.update(
            APP_BASE_URL="http://localhost",
            DATABASE=self.database_path,
            MAIL_SUPPRESS_SEND=False,
            PASSWORD_RESET_TOKEN_TTL=900,
            SECRET_KEY="test-secret-key",
            TESTING=True,
        )

        with app_module.app.app_context():
            app_module.init_db()
            database = app_module.get_db()
            database.execute(
                """
                INSERT INTO users (full_name, email, username, password_hash)
                VALUES (?, ?, ?, ?)
                """,
                (
                    "Test User",
                    "user@example.com",
                    "testuser",
                    generate_password_hash("OldPassword1!"),
                ),
            )
            database.commit()

        self.client = app_module.app.test_client()

    def tearDown(self):
        self.temp_directory.cleanup()

    def request_recovery_link(self):
        with patch.object(app_module, "send_recovery_email") as send_email:
            response = self.client.post(
                "/forgot-password",
                data={"identity": "user@example.com"},
            )
        self.assertEqual(response.status_code, 200)
        send_email.assert_called_once()
        return response, send_email.call_args.args[1]

    def test_unknown_account_gets_same_generic_response(self):
        with patch.object(app_module, "send_recovery_email") as send_email:
            response = self.client.post(
                "/forgot-password",
                data={"identity": "missing@example.com"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"If an account matches", response.data)
        send_email.assert_not_called()

    def test_recovery_request_stores_hash_and_sends_link(self):
        response, recovery_link = self.request_recovery_link()

        self.assertIn(b"If an account matches", response.data)
        self.assertTrue(recovery_link.startswith("http://localhost/reset-password/"))
        raw_token = recovery_link.rsplit("/", 1)[1]

        with app_module.app.app_context():
            record = app_module.get_db().execute(
                "SELECT token_hash, used FROM password_resets"
            ).fetchone()
        self.assertNotEqual(record["token_hash"], raw_token)
        self.assertEqual(record["token_hash"], app_module.hash_token(raw_token))
        self.assertEqual(record["used"], 0)

    def test_valid_link_resets_password_and_cannot_be_reused(self):
        _, recovery_link = self.request_recovery_link()
        path = recovery_link[len("http://localhost"):]

        self.assertEqual(self.client.get(path).status_code, 200)
        response = self.client.post(
            path,
            data={
                "password": "NewPassword2!",
                "confirm_password": "NewPassword2!",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/login?reset=success"))
        self.assertEqual(self.client.get(path).status_code, 400)

        with app_module.app.app_context():
            database = app_module.get_db()
            user = database.execute(
                "SELECT password_hash FROM users WHERE username = 'testuser'"
            ).fetchone()
            reset_record = database.execute(
                "SELECT used FROM password_resets"
            ).fetchone()
        self.assertFalse(check_password_hash(user["password_hash"], "OldPassword1!"))
        self.assertTrue(check_password_hash(user["password_hash"], "NewPassword2!"))
        self.assertEqual(reset_record["used"], 1)

        old_login = self.client.post(
            "/login",
            data={"username": "testuser", "password": "OldPassword1!"},
        )
        new_login = self.client.post(
            "/login",
            data={"username": "testuser", "password": "NewPassword2!"},
        )
        self.assertIn(b"Invalid username or password", old_login.data)
        self.assertEqual(new_login.status_code, 302)
        self.assertTrue(new_login.headers["Location"].endswith("/dashboard"))

    def test_expired_database_record_is_rejected(self):
        _, recovery_link = self.request_recovery_link()
        path = recovery_link[len("http://localhost"):]

        with app_module.app.app_context():
            database = app_module.get_db()
            database.execute(
                "UPDATE password_resets SET expires_at = ?",
                ((datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),),
            )
            database.commit()

        self.assertEqual(self.client.get(path).status_code, 400)

    def test_password_rules_and_confirmation_are_enforced(self):
        _, recovery_link = self.request_recovery_link()
        path = recovery_link[len("http://localhost"):]

        weak_response = self.client.post(
            path,
            data={"password": "short", "confirm_password": "short"},
        )
        mismatch_response = self.client.post(
            path,
            data={"password": "ValidPassword2!", "confirm_password": "Different2!"},
        )

        self.assertEqual(weak_response.status_code, 200)
        self.assertIn(b"at least 9 characters", weak_response.data)
        self.assertEqual(mismatch_response.status_code, 200)
        self.assertIn(b"Passwords do not match", mismatch_response.data)

    def test_email_failure_invalidates_created_token(self):
        with patch.object(
            app_module,
            "send_recovery_email",
            side_effect=smtplib.SMTPException("mail unavailable"),
        ):
            response = self.client.post(
                "/forgot-password",
                data={"identity": "testuser"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"If an account matches", response.data)
        with app_module.app.app_context():
            record = app_module.get_db().execute(
                "SELECT used FROM password_resets"
            ).fetchone()
        self.assertEqual(record["used"], 1)

    def test_email_helper_uses_tls_login_and_sends_message(self):
        with patch.object(app_module.smtplib, "SMTP") as smtp:
            server = smtp.return_value.__enter__.return_value
            app_module.send_recovery_email(
                "user@example.com",
                "http://localhost/reset-password/example-token",
            )

        smtp.assert_called_once_with("smtp.gmail.com", 587, timeout=10)
        server.starttls.assert_called_once_with()
        server.login.assert_called_once_with("your-email", "your-password")
        server.send_message.assert_called_once()

    def test_new_recovery_request_invalidates_older_link(self):
        _, first_link = self.request_recovery_link()
        _, second_link = self.request_recovery_link()

        first_path = first_link[len("http://localhost"):]
        second_path = second_link[len("http://localhost"):]
        self.assertEqual(self.client.get(first_path).status_code, 400)
        self.assertEqual(self.client.get(second_path).status_code, 200)


if __name__ == "__main__":
    unittest.main()
