"""Тесты для функциональности бота."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User, Chat, Message
from telegram.ext import ContextTypes

from rooms import create_room_handler, join_room_handler
from wishes import create_wish_handler, edit_wish_handler
from payment_handler import process_payment, successful_payment
from database import Session


@pytest.fixture
def update():
    """Фикстура для создания объекта Update."""
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 123456789
    update.effective_user.username = "test_user"
    update.message = MagicMock(spec=Message)
    update.message.chat = MagicMock(spec=Chat)
    update.message.chat.id = 123456789
    return update


@pytest.fixture
def context():
    """Фикстура для создания объекта Context."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []
    context.user_data = {}
    return context


@pytest.mark.asyncio
async def test_create_room(update, context, test_session):
    """Тест создания комнаты."""
    with patch('database.Session', return_value=test_session):
        await create_room_handler(update, context)
        room = test_session.query(Room).first()
        assert room is not None
        assert room.owner_id == update.effective_user.id
        update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_join_room(update, context, test_session, test_data):
    """Тест присоединения к комнате."""
    context.args = [test_data['room'].code]
    
    with patch('database.Session', return_value=test_session):
        await join_room_handler(update, context)
        user_room = test_session.query(UserRoom).filter_by(
            user_id=update.effective_user.id,
            room_id=test_data['room'].id
        ).first()
        assert user_room is not None
        assert not user_room.is_owner
        update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_create_wish(update, context, test_session, test_data):
    """Тест создания желания."""
    context.args = ["Хочу новый телефон"]
    context.user_data["current_room"] = test_data['room'].code
    
    with patch('database.Session', return_value=test_session):
        await create_wish_handler(update, context)
        wish = test_session.query(Wish).filter_by(
            user_id=update.effective_user.id,
            room_id=test_data['room'].id
        ).first()
        assert wish is not None
        assert wish.text == "Хочу новый телефон"
        update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_edit_wish(update, context, test_session, test_data):
    """Тест редактирования желания."""
    context.args = [str(test_data['wish'].id), "Обновленное желание"]
    
    with patch('database.Session', return_value=test_session):
        await edit_wish_handler(update, context)
        wish = test_session.query(Wish).get(test_data['wish'].id)
        assert wish.text == "Обновленное желание"
        update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_process_payment(update, context, test_session, test_data):
    """Тест обработки платежа."""
    context.args = [test_data['room'].code]
    
    with patch('database.Session', return_value=test_session):
        await process_payment(update, context)
        update.message.reply_invoice.assert_called_once()


@pytest.mark.asyncio
async def test_successful_payment(update, context, test_session, test_data):
    """Тест успешного платежа."""
    update.message.successful_payment = MagicMock()
    
    with patch('database.Session', return_value=test_session):
        await successful_payment(update, context)
        room = test_session.query(Room).get(test_data['room'].id)
        assert room.is_paid
        update.message.reply_text.assert_called_once() 