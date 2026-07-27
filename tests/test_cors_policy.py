import unittest

from fastapi.middleware.cors import CORSMiddleware

from main import app


class CorsPolicyTests(unittest.TestCase):
    def test_default_wildcard_does_not_allow_credentials(self):
        middleware = next(
            item for item in app.user_middleware if item.cls is CORSMiddleware
        )

        self.assertEqual(middleware.kwargs["allow_origins"], ["*"])
        self.assertFalse(middleware.kwargs["allow_credentials"])


if __name__ == "__main__":
    unittest.main()
