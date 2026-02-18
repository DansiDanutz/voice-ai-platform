"""Database models for Voice AI Platform."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, Integer, Boolean, DateTime, ForeignKey, JSON, TypeDecorator
from sqlalchemy.ext.declarative import declarative_base


class UUIDStr(TypeDecorator):
    """UUID stored as string for SQLite compat."""
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        return value
from sqlalchemy.orm import relationship

Base = declarative_base()


class Tenant(Base):
    """A customer/organization using the platform."""
    __tablename__ = "tenants"

    id = Column(UUIDStr, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    api_key = Column(String(64), unique=True, nullable=False)
    plan = Column(String(50), default="free")  # free, starter, pro, enterprise
    stripe_customer_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    assistants = relationship("Assistant", back_populates="tenant", cascade="all, delete-orphan")


class Assistant(Base):
    """An AI voice assistant with custom personality."""
    __tablename__ = "assistants"

    id = Column(UUIDStr, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUIDStr, ForeignKey("tenants.id"), nullable=False)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    system_prompt = Column(Text, nullable=False)
    voice_id = Column(String(100), default="cjVigY5qzO86Huf0OWal")
    voice_name = Column(String(255), default="Eric")
    model = Column(String(100), default="gpt-4o-mini")
    language = Column(String(10), default="en")
    greeting = Column(Text, default="Hello! How can I help you today?")
    knowledge_base = Column(Text, nullable=True)  # Custom context/docs
    max_duration = Column(Integer, default=600)
    is_active = Column(Boolean, default=True)
    widget_config = Column(JSON, default=dict)  # Colors, position, branding
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="assistants")
    conversations = relationship("Conversation", back_populates="assistant", cascade="all, delete-orphan")


class Conversation(Base):
    """A voice conversation session."""
    __tablename__ = "conversations"

    id = Column(UUIDStr, primary_key=True, default=uuid.uuid4)
    assistant_id = Column(UUIDStr, ForeignKey("assistants.id"), nullable=False)
    visitor_id = Column(String(255), nullable=True)  # Anonymous visitor tracking
    visitor_name = Column(String(255), nullable=True)
    visitor_email = Column(String(255), nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, default=0)
    message_count = Column(Integer, default=0)
    sentiment_score = Column(Float, nullable=True)  # -1 to 1
    summary = Column(Text, nullable=True)  # AI-generated summary
    extra_data = Column(JSON, default=dict)  # IP, user-agent, referrer, etc.

    assistant = relationship("Assistant", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """A single message in a conversation (user or assistant)."""
    __tablename__ = "messages"

    id = Column(UUIDStr, primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUIDStr, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    text = Column(Text, nullable=False)
    audio_duration = Column(Float, nullable=True)  # seconds
    tokens_used = Column(Integer, default=0)
    latency_ms = Column(Integer, nullable=True)  # Response time
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")
