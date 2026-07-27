from types import SimpleNamespace
import unittest

from main import talk_page


class FakeQuery:
    def __init__(self, assistant):
        self.assistant = assistant

    def filter(self, *args):
        return self

    def first(self):
        return self.assistant


class FakeDatabase:
    def __init__(self, assistant):
        self.assistant = assistant

    def query(self, model):
        return FakeQuery(self.assistant)


class TalkPageSecurityTests(unittest.TestCase):
    def test_tenant_content_cannot_inject_html_or_script(self):
        assistant = SimpleNamespace(
            name='</script><script>alert("name")</script>',
            slug='safe-slug</script><script>alert("slug")</script>',
            greeting='<img src=x onerror=alert("greeting")>',
            is_active=True,
        )

        page = talk_page(assistant.slug, db=FakeDatabase(assistant))

        self.assertNotIn('</script><script>', page)
        self.assertNotIn('<img src=x', page)
        self.assertNotIn("d.innerHTML", page)
        self.assertIn('&lt;img src=x onerror=alert(&quot;greeting&quot;)&gt;', page)
        self.assertIn(r'\u003c/script\u003e', page)
        self.assertIn("document.createTextNode(text)", page)


if __name__ == "__main__":
    unittest.main()
