import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User, Chat, Message
from telegram.ext import ContextTypes

from rooms import create_room_handler, join_room_handler
from wishes import create_wish_handler, edit_wish_handler
from payment_handler import process_payment, successful_payment


@pytest.fixture
def update():
    """Фикстура для создания объекта Update"""
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
    """Фикстура для создания объекта Context"""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []
    context.user_data = {}
    return context


@pytest.mark.asyncio
async def test_create_room(update, context):
    """Тест создания комнаты"""
    with patch('rooms.create_room') as mock_create_room:
        await create_room_handler(update, context)
        mock_create_room.assert_called_once()
        update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_join_room(update, context):
    """Тест присоединения к комнате"""
    context.args = ["ABC123"]
    with patch('rooms.room_exists') as mock_exists, \
         patch('rooms.count_users_in_room') as mock_count, \
         patch('rooms.add_user_to_room') as mock_add:
        mock_exists.return_value = True
        mock_count.return_value = 3
        
        await join_room_handler(update, context)
        mock_add.assert_called_once()
        update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_create_wish(update, context):
    """Тест создания желания"""
    context.args = ["Хочу новый телефон"]
    context.user_data["current_room"] = "ABC123"
    
    with patch('wishes.get_room_details') as mock_details, \
         patch('wishes.count_user_wishes') as mock_count, \
         patch('wishes.add_wish') as mock_add:
        mock_details.return_value = {"is_paid": False}
        mock_count.return_value = 1
        
        await create_wish_handler(update, context)
        mock_add.assert_called_once()
        update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_edit_wish(update, context):
    """Тест редактирования желания"""
    context.args = ["1", "Обновленное желание"]
    
    with patch('wishes.edit_wish') as mock_edit:
        mock_edit.return_value = True
        await edit_wish_handler(update, context)
        mock_edit.assert_called_once()
        update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_process_payment(update, context):
    """Тест обработки платежа"""
    context.args = ["ABC123"]
    
    with patch('payment_handler.get_room_details') as mock_details:
        mock_details.return_value = {
            "creator_id": 123456789,
            "is_paid": False
        }
        
        await process_payment(update, context)
        update.message.reply_invoice.assert_called_once()


@pytest.mark.asyncio
async def test_successful_payment(update, context):
    """Тест успешного платежа"""
    update.message.successful_payment = MagicMock()
    
    with patch('payment_handler.grant_access') as mock_grant:
        await successful_payment(update, context)
        mock_grant.assert_called_once_with(123456789, 'paid')
        update.message.reply_text.assert_called_once() 