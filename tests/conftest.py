import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.config import settings
from backend.database import Base
from backend.telegram import telegram_notifier
from tests.client_wrapper import DirectTestClient

test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

TestSessionLocal = sessionmaker(
    bind=test_engine,
    autocommit=False,
    autoflush=False
)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)

@pytest.fixture(scope="function")
def test_client(db_session):
    return DirectTestClient(db_session)

@pytest.fixture(autouse=True)
def mock_telegram_env(monkeypatch):
    """Ensure Telegram notifications are mocked so tests don't reach out to internet"""
    monkeypatch.setattr(telegram_notifier, "send_message", lambda *args, **kwargs: True)
