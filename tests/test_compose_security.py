from pathlib import Path
import unittest


COMPOSE_FILE = Path(__file__).parents[1] / "docker-compose.yml"
DOCKERIGNORE_FILE = Path(__file__).parents[1] / ".dockerignore"


class ComposeSecurityTests(unittest.TestCase):
    def test_database_requires_password_and_is_not_host_published(self):
        compose = COMPOSE_FILE.read_text()

        self.assertNotIn("POSTGRES_PASSWORD: changeme", compose)
        self.assertIn("POSTGRES_PASSWORD:?", compose)
        self.assertNotIn('"5432:5432"', compose)
        self.assertNotIn("DATABASE_URL:", compose)
        self.assertIn("DB_HOST: db", compose)

    def test_docker_build_context_excludes_local_secrets(self):
        dockerignore = DOCKERIGNORE_FILE.read_text().splitlines()

        self.assertIn(".env", dockerignore)
        self.assertIn(".env.*", dockerignore)
        self.assertIn("!.env.example", dockerignore)


if __name__ == "__main__":
    unittest.main()
