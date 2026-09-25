from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext

from app.bot.keyboards import main_keyboard
from app.bot.states import MainStates
from app.services.auto_swipe import AutoSwipeService
from app.services.location import LocationService
from app.services.matches import MatchService
from app.services.recommendations import RecommendationService
from app.services.session import TinderSessionManager
from app.services.swipe import SwipeService


async def swipe_start(message: types.Message, state: FSMContext) -> None:
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

    await MainStates.swiping.set()
    client = sessions.get_client(message.from_user.id)

    service = AutoSwipeService(
        location_service=LocationService(client),
        recommendation_service=RecommendationService(client),
        match_service=MatchService(client),
        swipe_service=SwipeService(client, RecommendationService(client)),
    )

    await message.answer("Запускаю AutoSwipe...")

    try:
        result = service.run(city)
    except Exception as exc:
        await state.finish()
        await message.answer(
            f"AutoSwipe не удалось завершить: {exc}",
            reply_markup=main_keyboard(),
        )
        return

    await state.finish()
    swipe = result.swipe_result
    matches = result.match_stats
    status = "Лимит достигнут" if swipe.limit_reached else "Рекомендации закончились"

    await message.answer(
        f"AutoSwipe завершён.\n\n"
        f"Город: {result.location.address or city}\n"
        f"Получено рекомендаций в первой порции: {result.recommendations_received}\n"
        f"Свайпов выполнено: {swipe.swipes}\n"
        f"Лайков: {swipe.likes}\n"
        f"Дизлайков: {swipe.dislikes}\n"
        f"Новых матчей: {matches.new_matches}\n"
        f"Всего матчей: {matches.after}\n"
        f"Статус: {status}",
        reply_markup=main_keyboard(),
    )


def register(dp: Dispatcher, sessions: TinderSessionManager) -> None:
    dp.register_message_handler(
        swipe_start,
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
