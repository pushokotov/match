import phonenumbers

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext

from app.bot.keyboards import main_keyboard
from app.bot.states import AuthStates
from app.services.auth import AuthService
from app.services.profile import ProfileService
from app.services.session import TinderSessionManager


def _services(message: types.Message, sessions: TinderSessionManager):
    client = sessions.get_client(message.from_user.id)
    return AuthService(client), ProfileService(client)


async def phone_start(
    callback: types.CallbackQuery,
    state: FSMContext,
) -> None:
    await AuthStates.waiting_phone.set()
    await callback.message.answer("Отправь номер телефона в международном формате, например +31612345678.")
    await callback.answer()


async def token_start(
    callback: types.CallbackQuery,
    state: FSMContext,
) -> None:
    await AuthStates.waiting_test_token.set()
    await callback.message.answer("Отправь Tinder token. Этот способ нужен только для тестирования.")
    await callback.answer()


async def phone_received(
    message: types.Message,
    state: FSMContext,
    sessions: TinderSessionManager,
) -> None:
    raw_phone = message.text.strip()
    try:
        parsed = phonenumbers.parse(raw_phone, None)
        if not phonenumbers.is_valid_number(parsed):
            raise ValueError
        phone = phonenumbers.format_number(
            parsed, phonenumbers.PhoneNumberFormat.E164
        )
    except (phonenumbers.NumberParseException, ValueError):
        await message.answer("Не удалось распознать номер. Отправь его в международном формате, например +31612345678.")
        return

    auth, _ = _services(message, sessions)
    try:
        auth.request_phone_code(phone)
    except Exception as exc:
        await message.answer(f"Не удалось запросить код Tinder: {exc}")
        return

    await state.update_data(phone=phone)
    await AuthStates.waiting_code.set()
    await message.answer("Код отправлен. Теперь отправь код из Tinder.")


async def code_received(
    message: types.Message,
    state: FSMContext,
    sessions: TinderSessionManager,
) -> None:
    data = await state.get_data()
    phone = data.get("phone")
    code = message.text.strip()

    if not phone:
        await state.finish()
        await message.answer("Сессия авторизации потеряна. Начни заново через /start.")
        return

    auth, profile = _services(message, sessions)
    try:
        auth.authenticate_with_code(phone, code)
        tinder_profile = profile.get_profile()
    except Exception as exc:
        await message.answer(f"Не удалось завершить авторизацию: {exc}")
        return

    await state.finish()
    await message.answer(
        f"Авторизация успешна!
"
        f"Профиль: {tinder_profile.name}
"
        f"Город: {tinder_profile.city}
"
        f"Страна: {tinder_profile.country}",
        reply_markup=main_keyboard(),
    )


async def token_received(
    message: types.Message,
    state: FSMContext,
    sessions: TinderSessionManager,
) -> None:
    token = message.text.strip()
    if not token:
        await message.answer("Token не должен быть пустым.")
        return

    auth, profile = _services(message, sessions)
    try:
        auth.authenticate_with_token(token)
        tinder_profile = profile.get_profile()
    except Exception as exc:
        await message.answer(f"Token не подошёл или Tinder API недоступен: {exc}")
        return

    await state.finish()
    await message.answer(
        f"Авторизация успешна!
"
        f"Профиль: {tinder_profile.name}
"
        f"Город: {tinder_profile.city}
"
        f"Страна: {tinder_profile.country}",
        reply_markup=main_keyboard(),
    )


def register(dp: Dispatcher, sessions: TinderSessionManager) -> None:
    dp.register_callback_query_handler(
        phone_start, lambda c: c.data == "auth:phone", state="*"
    )
    dp.register_callback_query_handler(
        token_start, lambda c: c.data == "auth:token", state="*"
    )
    dp.register_message_handler(
        phone_received, state=AuthStates.waiting_phone, content_types=types.ContentType.TEXT
    )
    dp.register_message_handler(
        code_received, state=AuthStates.waiting_code, content_types=types.ContentType.TEXT
    )
    dp.register_message_handler(
        token_received, state=AuthStates.waiting_test_token, content_types=types.ContentType.TEXT
    )

    for handler in (phone_received, code_received, token_received):
        handler.__aiogram_extra__ = {"sessions": sessions}
