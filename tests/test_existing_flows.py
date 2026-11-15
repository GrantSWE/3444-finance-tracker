import os
import tempfile
import unittest

import app as app_module


class ExistingFlowRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        app_module.app.config.update(
            DATABASE=os.path.join(self.temp_directory.name, "test.db"),
            SECRET_KEY="test-secret-key",
            TESTING=True,
        )
        with app_module.app.app_context():
            app_module.init_db()
        self.client = app_module.app.test_client()

    def tearDown(self):
        self.temp_directory.cleanup()

    def test_registration_dashboard_and_transaction_crud_still_work(self):
        registration = self.client.post(
            "/register",
            data={
                "full_name": "Regression User",
                "email": "regression@example.com",
                "username": "regression_user",
                "password": "ValidPassword1!",
            },
        )
        self.assertEqual(registration.status_code, 302)
        self.assertTrue(registration.headers["Location"].endswith("/dashboard"))
        self.assertEqual(self.client.get("/dashboard").status_code, 200)

        created = self.client.post(
            "/api/transactions",
            json={
                "amount": 25.50,
                "category": "Food",
                "date": "2026-11-14",
                "description": "Regression test",
                "title": "Groceries",
                "type": "expense",
            },
        )
        self.assertEqual(created.status_code, 201)
        transaction_id = created.get_json()["transaction"]["id"]

        listed = self.client.get("/api/transactions")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.get_json()["transactions"]), 1)

        updated = self.client.put(
            f"/api/transactions/{transaction_id}",
            json={"amount": 30.00, "title": "Updated groceries"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.get_json()["transaction"]["amount"], 30)

        deleted = self.client.delete(f"/api/transactions/{transaction_id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(self.client.get("/api/transactions").get_json()["transactions"], [])


if __name__ == "__main__":
    unittest.main()
