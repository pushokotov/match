from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext

from app.bot.keyboards import main_keyboard
from app.bot.states import MainStates
from app.services.location import LocationService
from app.services.recommendations import RecommendationService
from app.services.session import TinderSessionManager


async def location_start(message: types.Message, state: FSMContext) -> None:
    await MainStates.waiting_location.set()
    await message.answer("Напиши город, в котором нужно искать анкеты.")


async def location_received(
    message: types.Message,
    state: FSMContext,
    sessions: TinderSessionManager,
) -> None:
    city = message.text.strip()
    if not city:
        await message.answer("Город не должен быть пустым.")
        return

    client = sessions.get_client(message.from_user.id)
    location_service = LocationService(client)

    try:
        location = location_service.set_city(city)
        recommendations = RecommendationService(client).get_batch()
    except Exception as exc:
        await message.answer(f"Не удалось установить город или получить рекомендации: {exc}")
        return

    await state.finish()
    await message.answer(
        f"Город установлен: {location.address or city}\n"
        f"Получено рекомендаций: {len(recommendations)}",
        reply_markup=main_keyboard(),
    )


def register(dp: Dispatcher, sessions: TinderSessionManager) -> None:
    dp.register_message_handler(
        location_start,
        lambda message: message.text == "Запустить AutoSwipe",
        state="*",
    )

    async def location_handler(message: types.Message, state: FSMContext):
        await location_received(message, state, sessions)

    dp.register_message_handler(
        location_handler,
        state=MainStates.waiting_location,
        content_types=types.ContentType.TEXT,
    )
