from pathlib import Path
import unittest


COMPOSE_FILE = Path(__file__).parents[1] / "docker-compose.yml"
DOCKERIGNORE_FILE = Path(__file__).parents[1] / ".dockerignore"
ROTATION_SCRIPT = Path(__file__).parents[1] / "scripts" / "rotate-postgres-password.sh"
README_FILE = Path(__file__).parents[1] / "README.md"
DOCKERFILE = Path(__file__).parents[1] / "Dockerfile"
WORKFLOW_FILE = Path(__file__).parents[1] / ".github" / "workflows" / "quality.yml"
LOCK_FILE = Path(__file__).parents[1] / "requirements.lock"


class ComposeSecurityTests(unittest.TestCase):
    def test_database_requires_password_and_is_only_loopback_published(self):
        compose = COMPOSE_FILE.read_text()

        self.assertNotIn("POSTGRES_PASSWORD: changeme", compose)
        self.assertIn("POSTGRES_PASSWORD:?", compose)
        self.assertIn('"127.0.0.1:5432:5432"', compose)
        self.assertNotIn('- "5432:5432"', compose)
        self.assertNotIn("DATABASE_URL:", compose)
        self.assertIn("DB_HOST: db", compose)

    def test_docker_build_context_excludes_local_secrets(self):
        dockerignore = DOCKERIGNORE_FILE.read_text().splitlines()

        self.assertIn(".env", dockerignore)
        self.assertIn(".env.*", dockerignore)
        self.assertIn("!.env.example", dockerignore)

    def test_existing_volume_has_an_explicit_password_rotation_path(self):
        script = ROTATION_SCRIPT.read_text()
        readme = README_FILE.read_text()

        self.assertIn("ALTER ROLE voice_ai", script)
        self.assertIn(":'new_password'", script)
        self.assertIn("rotate-postgres-password.sh", readme)

    def test_ci_and_image_use_the_same_exact_dependency_lock(self):
        lock = LOCK_FILE.read_text()
        dockerfile = DOCKERFILE.read_text()
        workflow = WORKFLOW_FILE.read_text()

        self.assertIn("fastapi==", lock)
        self.assertNotIn(">=", lock)
        self.assertIn("requirements.lock", dockerfile)
        self.assertIn("requirements.lock", workflow)


if __name__ == "__main__":
    unittest.main()
