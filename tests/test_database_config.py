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

    def test_default_database_url_is_a_sqlalchemy_sqlite_url(self):
        with patch.dict(os.environ, {}, clear=True):
            url = build_database_url()

        self.assertEqual(url.get_backend_name(), "sqlite")

    def test_compose_coordinates_override_legacy_database_url(self):
        env = {
            "DATABASE_URL": "postgresql://legacy:old@localhost/legacy",
            "DB_HOST": "db",
            "POSTGRES_DB": "voice_ai",
            "POSTGRES_USER": "voice_ai",
            "POSTGRES_PASSWORD": "new-password",
        }

        with patch.dict(os.environ, env, clear=True):
            url = build_database_url()

        self.assertEqual(url.host, "db")
        self.assertEqual(url.password, "new-password")


if __name__ == "__main__":
    unittest.main()
