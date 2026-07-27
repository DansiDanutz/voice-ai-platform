import os
import unittest
from unittest.mock import patch

from api.database import build_database_url


class DatabaseConfigurationTests(unittest.TestCase):
    def test_compose_password_preserves_reserved_characters(self):
        env = {
            "DB_HOST": "db",
            "POSTGRES_DB": "voice_ai",
            "POSTGRES_USER": "voice_ai",
            "POSTGRES_PASSWORD": "raw@password:/?#[]!",
        }

        with patch.dict(os.environ, env, clear=True):
            url = build_database_url()

        self.assertEqual(url.password, env["POSTGRES_PASSWORD"])
        self.assertEqual(url.host, "db")
        self.assertEqual(url.database, "voice_ai")


if __name__ == "__main__":
    unittest.main()
