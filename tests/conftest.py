"""Конфигурация тестов и фикстуры."""
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base

# Устанавливаем тестовое окружение
os.environ['ENVIRONMENT'] = 'testing'


@pytest.fixture(scope="session")
def test_engine():
    """Создает тестовый движок базы данных."""
    engine = create_engine("sqlite:///test_santa_bot.db")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="session")
def test_session_factory(test_engine):
    """Создает фабрику сессий для тестов."""
    return sessionmaker(bind=test_engine)


@pytest.fixture
def test_session(test_session_factory):
    """Создает тестовую сессию."""
    session = test_session_factory()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def test_data(test_session):
    """Создает тестовые данные."""
    from test_data import setup_test_data
    return setup_test_data(test_session) 