import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.models import Assistant, Base, Conversation, Message, Tenant
from main import TextChatRequest, text_chat


class ConversationIsolationTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()

        tenant_a = Tenant(name="Tenant A", email="a@example.com", api_key="vai_a")
        tenant_b = Tenant(name="Tenant B", email="b@example.com", api_key="vai_b")
        self.db.add_all([tenant_a, tenant_b])
        self.db.flush()

        self.assistant_a = Assistant(
            tenant_id=tenant_a.id,
            name="Assistant A",
            slug="assistant-a",
            system_prompt="A only",
        )
        self.assistant_b = Assistant(
            tenant_id=tenant_b.id,
            name="Assistant B",
            slug="assistant-b",
            system_prompt="B only",
        )
        self.db.add_all([self.assistant_a, self.assistant_b])
        self.db.flush()

        self.foreign_conversation = Conversation(assistant_id=self.assistant_a.id)
        self.db.add(self.foreign_conversation)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_text_chat_rejects_foreign_assistant_conversation_context(self):
        request = TextChatRequest(
            message="hello",
            conversation_id=str(self.foreign_conversation.id),
        )
        llm_result = {"text": "response", "tokens": 1, "latency_ms": 2}

        with patch("main.llm_respond", new=AsyncMock(return_value=llm_result)):
            result = asyncio.run(text_chat(self.assistant_b.slug, request, db=self.db))

        self.assertNotEqual(result["conversation_id"], str(self.foreign_conversation.id))
        self.assertEqual(
            self.db.query(Message)
            .filter(Message.conversation_id == self.foreign_conversation.id)
            .count(),
            0,
        )
        created = self.db.query(Conversation).filter(
            Conversation.id == result["conversation_id"]
        ).one()
        self.assertEqual(created.assistant_id, self.assistant_b.id)


if __name__ == "__main__":
    unittest.main()
