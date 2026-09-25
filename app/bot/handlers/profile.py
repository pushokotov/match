from aiogram import Dispatcher, types

from app.services.profile import ProfileService
from app.services.session import TinderSessionManager


async def profile(message: types.Message, sessions: TinderSessionManager) -> None:
    client = sessions.get_client(message.from_user.id)
    service = ProfileService(client)

    try:
        tinder_profile = service.get_profile()
    except Exception as exc:
        await message.answer(f"Не удалось получить профиль Tinder: {exc}")
        return

    await message.answer(
        f"Имя: {tinder_profile.name}\n"
        f"Город: {tinder_profile.city}\n"
        f"Страна: {tinder_profile.country}"
    )


def register(dp: Dispatcher, sessions: TinderSessionManager) -> None:
    async def profile_handler(message: types.Message):
        await profile(message, sessions)

    dp.register_message_handler(
        profile_handler,
        lambda message: message.text == "Мой профиль",
        state="*",
    )
