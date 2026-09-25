from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext

from app.bot.keyboards import start_keyboard


async def start(message: types.Message, state: FSMContext) -> None:
    await state.finish()
    await message.answer(
        "Привет! Для работы бота сначала авторизуй Tinder.",
        reply_markup=start_keyboard(),
    )


def register(dp: Dispatcher) -> None:
    dp.register_message_handler(start, commands=["start"], state="*")
